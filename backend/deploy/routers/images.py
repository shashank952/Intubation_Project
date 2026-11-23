"""Image upload endpoint.

POST /api/images/analyze
    multipart/form-data:
        file        JPEG or PNG, max 8 MB
        patient_id  optional, used only for the audit log

What the caller gets back
-------------------------
    quality    blur / brightness / face size / usable flag / issues
    geometry   mouth and face ratios, measured on the redacted image
    preview    data URI of the REDACTED image (never the original)
    auto_fill  always empty on purpose - see image_analysis.py

Safety
------
* The upload is decoded in memory, the eyes are redacted, and the image is
  discarded. Nothing is written to disk or to MongoDB.
* If no face is found, no preview is returned: an unredacted image must not
  leave the server.
* Doctor role required, per-user rate limit, audit-logged (best effort).
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from .. import image_analysis
from ..auth import require_role
from ..database import audit_log, get_db
from ..schemas import ImageAnalyzeOut, ImageNdmsOut

logger = logging.getLogger("airway.images")

router = APIRouter(prefix="/api/images", tags=["images"])

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png"}
PATIENT_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

_WINDOW_SECONDS = 60
_MAX_PER_WINDOW = 20
_hits: dict[str, list[float]] = defaultdict(list)


def _enforce_rate_limit(user: dict) -> None:
    now = time.time()
    key = user["sub"]
    _hits[key] = [t for t in _hits[key] if now - t < _WINDOW_SECONDS]
    if len(_hits[key]) >= _MAX_PER_WINDOW:
        raise HTTPException(status_code=429, detail="Too many image analyses. Try again shortly.")
    _hits[key].append(now)


async def _audit(user: dict, patient_id: str, status: str) -> None:
    try:
        await audit_log(
            get_db(),
            user["sub"],
            "analyze",
            "image",
            patient_id or "-",
            detail=f"status={status}",
        )
    except Exception:  # audit must never break the request
        logger.exception("Audit log failed for image analysis")


@router.post("/analyze", response_model=ImageAnalyzeOut)
async def analyze_image(
    file: UploadFile = File(...),
    patient_id: str = Form(""),
    user: dict = Depends(require_role("doctor")),
):
    _enforce_rate_limit(user)

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Only JPEG or PNG images are accepted.")

    if patient_id and not PATIENT_ID_RE.match(patient_id):
        raise HTTPException(status_code=400, detail="Invalid patient_id format.")

    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if not contents:
        raise HTTPException(status_code=400, detail="Empty upload.")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds the 8 MB limit.")

    try:
        result = await asyncio.to_thread(image_analysis.analyze, contents)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        # face model missing / unloadable: a server problem, not a client problem
        logger.error("Image analysis unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="Image analysis is unavailable.") from exc

    await _audit(user, patient_id, result["status"])
    return result


NDMS_NOTE = (
    "NDMS is a heuristic, non-validated morphometric score derived from photo geometry "
    "and colour proxies. On this dataset photo features did not carry validated signal "
    "for the difficulty label, so its risk contribution is small, capped at +5 points, "
    "and never lowers the tabular risk."
)

NDMS_UPLOAD_FIELDS = ("frontal", "teeth", "tongue", "jawline")


@router.post("/ndms", response_model=ImageNdmsOut)
async def analyze_ndms(
    frontal: Optional[UploadFile] = File(None),
    teeth: Optional[UploadFile] = File(None),
    tongue: Optional[UploadFile] = File(None),
    jawline: Optional[UploadFile] = File(None),
    patient_id: str = Form(""),
    base_risk: Optional[float] = Form(None),
    user: dict = Depends(require_role("doctor")),
):
    _enforce_rate_limit(user)

    if patient_id and not PATIENT_ID_RE.match(patient_id):
        raise HTTPException(status_code=400, detail="Invalid patient_id format.")
    if base_risk is not None and not (0.0 <= base_risk <= 100.0):
        raise HTTPException(status_code=400, detail="base_risk must be between 0 and 100.")

    uploads = {"frontal": frontal, "teeth": teeth, "tongue": tongue, "jawline": jawline}
    if not any(upload is not None for upload in uploads.values()):
        raise HTTPException(status_code=400, detail="Provide at least one image.")

    results: dict[str, Optional[dict]] = {}
    for view, upload in uploads.items():
        if upload is None:
            results[view] = None
            continue
        if upload.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(status_code=415, detail="Only JPEG or PNG images are accepted.")
        contents = await upload.read(MAX_UPLOAD_BYTES + 1)
        if not contents:
            raise HTTPException(status_code=400, detail=f"Empty upload for {view}.")
        if len(contents) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Image exceeds the 8 MB limit.")
        try:
            results[view] = await asyncio.to_thread(image_analysis.analyze, contents, view)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            logger.error("Image analysis unavailable: %s", exc)
            raise HTTPException(status_code=503, detail="Image analysis is unavailable.") from exc

    ndms = image_analysis.compute_ndms(results)
    blended = image_analysis.blend_risk(base_risk, ndms.get("risk_contribution"))
    await _audit(user, patient_id, "ndms_ok")

    views_out = {}
    for view in NDMS_UPLOAD_FIELDS:
        result = results.get(view)
        if result is None:
            views_out[view] = None
            continue
        views_out[view] = {
            "status": result["status"],
            "usable": bool(result["quality"]["usable"]),
            "issues": result["quality"].get("issues", []),
            "quality": result["quality"],
            "geometry": result.get("geometry"),
            "preview_data_uri": result.get("preview_data_uri"),
            "view_metrics": result.get("view_metrics") or {},
        }

    return {
        **ndms,
        "blended_risk": blended,
        "max_contribution": image_analysis.NDMS_MAX_CONTRIBUTION,
        "views": views_out,
        "note": NDMS_NOTE,
    }
