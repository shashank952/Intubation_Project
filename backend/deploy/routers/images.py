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
from datetime import datetime, timezone
from collections import defaultdict

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from .. import image_analysis
from ..auth import require_role
from ..database import get_db
from ..schemas import ImageAnalyzeOut

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
        await get_db().audit_logs.insert_one(
            {
                "actor": user["sub"],
                "action": "analyze",
                "resource": "image",
                "resource_id": patient_id or "-",
                "detail": f"status={status}",
                "created_at": datetime.now(timezone.utc),
            }
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
