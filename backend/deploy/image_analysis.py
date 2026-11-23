"""In-memory analysis for uploaded airway photos.

Design rules
------------
* The image is processed in memory and never written to disk.
* The eyes are redacted BEFORE anything is returned, using the same YOLO face
  model and the same strip geometry as scripts/redact_eyes.py. If no face is
  found, no preview is returned at all - an unredacted image must never leave
  the server.
* The output is a quality report plus geometry. It does NOT auto-fill clinical
  fields: tests on this dataset showed photo-derived numbers carry no usable
  signal for the difficulty label. Claiming otherwise would be dishonest.
* Heavy work (torch) is imported lazily so the rest of the API still imports
  cleanly if the optional ML stack is missing.

This module is deliberately free of FastAPI and database code so it can be
unit-tested on its own.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import threading
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageOps

logger = logging.getLogger("airway.image_analysis")

# Detection / quality thresholds mirror scripts/extract_image_features.py so the
# online numbers match the offline analysis that was validated.
PRIMARY_CONF = 0.35
FALLBACK_CONF = 0.10
FALLBACK_FACE_FRAC = 0.15
MIN_FACE_AREA_FRAC = 0.02
MIN_BLUR = 40.0
BRIGHT_LOW, BRIGHT_HIGH = 35.0, 235.0
BLUR_WORKING_WIDTH = 800
DETECT_MAX_SIDE = 768
DETECT_IMGSZ = 384
PREVIEW_WIDTH = 640
BLACK = (0, 0, 0)

STRIP_HEIGHT = 0.80
STRIP_RISE = 0.10
STRIP_PAD_X = 0.06
FALLBACK_TOP = 0.28
FALLBACK_BOTTOM = 0.52

# NDMS (Normalized Difficulty Morphometric Score).
# Per-component weights renormalize over whichever components are available.
NDMS_WEIGHTS = {
    "mouth_opening": 0.30,
    "teeth_visibility": 0.20,
    "tongue_protrusion": 0.30,
    "jaw_neck": 0.20,
}
NDMS_MAX_CONTRIBUTION = 5.0
NDMS_MIN_COMPONENTS = 2
NDMS_VIEWS = ("frontal", "teeth", "tongue", "jawline")
TEETH_MIN_VALUE = 140.0
TEETH_MAX_SAT = 90.0
TONGUE_SAT_MIN = 90.0
TONGUE_VALUE_MIN = 50.0

_model = None
_model_lock = threading.Lock()

cv2.setNumThreads(1)


def default_model_path() -> Path:
    override = os.getenv("FACE_MODEL_PATH")
    if override:
        return Path(override)
    bundled = Path(__file__).resolve().parents[2] / "checkpoints" / "yolo26n-face.pt"
    if bundled.exists():
        return bundled
    return Path.home() / ".cache" / "yolo-face" / "yolo26n-face.pt"


def get_model():
    """Load the face model once. Raises (no silent fallback) if it is missing."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from ultralytics import YOLO

                path = default_model_path()
                if not path.exists():
                    raise RuntimeError(
                        f"Face model not found: {path}. Set FACE_MODEL_PATH or download "
                        "yolo26n-face.pt from https://github.com/akanametov/yolo-face/releases"
                    )
                _model = YOLO(str(path))
                logger.info("Face model loaded: %s", path.name)
    return _model


# ------------------------------------------------------------------ decoding


def decode(raw: bytes) -> np.ndarray:
    """Decode uploaded bytes to a BGR array, applying EXIF orientation.

    Raises ValueError for anything that is not a decodable image.
    """
    if not raw:
        raise ValueError("Empty upload")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            image.draft("RGB", (DETECT_MAX_SIDE, DETECT_MAX_SIDE))
            upright = ImageOps.exif_transpose(image).convert("RGB")
            if max(upright.size) > DETECT_MAX_SIDE:
                upright.thumbnail((DETECT_MAX_SIDE, DETECT_MAX_SIDE))
            array = np.array(upright)
    except Exception as exc:  # PIL raises several unrelated exception types
        raise ValueError(f"Not a decodable image: {exc.__class__.__name__}") from exc
    return np.ascontiguousarray(array[:, :, ::-1])


def _resize_for_work(bgr: np.ndarray) -> np.ndarray:
    height, width = bgr.shape[:2]
    longest = max(height, width)
    if longest <= DETECT_MAX_SIDE:
        return bgr
    scale = DETECT_MAX_SIDE / longest
    return cv2.resize(bgr, (int(width * scale), int(height * scale)))


# ---------------------------------------------------------------- detection


def detect_faces(model, bgr: np.ndarray, conf: float) -> list[dict]:
    result = model.predict(bgr, conf=conf, iou=0.5, imgsz=DETECT_IMGSZ, verbose=False)[0]
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return []

    coords = boxes.xyxy.cpu().numpy()
    scores = boxes.conf.cpu().numpy()

    keypoints = None
    keypoint_conf = None
    kp_obj = getattr(result, "keypoints", None)
    if kp_obj is not None:
        keypoints = kp_obj.xy.cpu().numpy()
        if getattr(kp_obj, "conf", None) is not None:
            keypoint_conf = kp_obj.conf.cpu().numpy()
        else:
            keypoint_conf = np.ones(keypoints.shape[:2], dtype=np.float32)

    faces = []
    for index, (box, score) in enumerate(zip(coords, scores)):
        faces.append(
            {
                "box": box.astype(float).tolist(),
                "score": float(score),
                "keypoints": keypoints[index].astype(float).tolist() if keypoints is not None else None,
                "keypoint_conf": keypoint_conf[index].astype(float).tolist() if keypoint_conf is not None else None,
            }
        )
    return faces


def eye_strip(face: dict, width: int, height: int) -> tuple[int, int, int, int]:
    """Compute the black bar over the eyes. Same geometry as the redaction script."""
    x1, y1, x2, y2 = face["box"]
    left, right = x1, x2
    face_h = max(1.0, y2 - y1)

    keypoints = face.get("keypoints")
    conf = face.get("keypoint_conf") or [1.0, 1.0]
    if keypoints and len(keypoints) >= 2 and min(conf[0], conf[1]) >= 0.5:
        eye_a, eye_b = keypoints[0], keypoints[1]
        iod = max(abs(eye_b[0] - eye_a[0]), abs(eye_b[1] - eye_a[1]), 1.0)
        center_x = (eye_a[0] + eye_b[0]) / 2.0
        center_y = (eye_a[1] + eye_b[1]) / 2.0
        pad = STRIP_PAD_X * (x2 - x1)
        span = max(x2 - x1 + 2 * pad, 1.6 * iod)
        left = center_x - span / 2.0
        right = center_x + span / 2.0
        bar = min(max(STRIP_HEIGHT * iod, 0.11 * face_h), 0.30 * face_h)
        top = center_y - bar / 2.0 - STRIP_RISE * bar
        bottom = top + bar
    else:
        top = y1 + FALLBACK_TOP * face_h
        bottom = y1 + FALLBACK_BOTTOM * face_h

    sx1 = int(max(0, round(left)))
    sx2 = int(min(width, round(right)))
    sy1 = int(max(0, round(top)))
    sy2 = int(min(height, round(bottom)))
    if sx2 <= sx1 or sy2 <= sy1:
        return (0, 0, 0, 0)
    return (sx1, sy1, sx2, sy2)


def redact_faces(bgr: np.ndarray, faces: list[dict]) -> int:
    """Draw a black bar over each detected face's eyes, in place. Returns count."""
    height, width = bgr.shape[:2]
    drawn = 0
    for face in faces:
        x1, y1, x2, y2 = eye_strip(face, width, height)
        if x2 <= x1 or y2 <= y1:
            continue
        cv2.rectangle(bgr, (x1, y1), (x2, y2), BLACK, thickness=-1)
        drawn += 1
    return drawn


# ------------------------------------------------------------------ scoring


def quality_metrics(bgr: np.ndarray) -> dict:
    height, width = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    working = gray
    if width > BLUR_WORKING_WIDTH:
        scale = BLUR_WORKING_WIDTH / width
        working = cv2.resize(gray, (BLUR_WORKING_WIDTH, max(1, int(height * scale))))
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    value = hsv[:, :, 2]
    return {
        "width": int(width),
        "height": int(height),
        "megapixels": round(width * height / 1e6, 2),
        "blur_score": round(float(cv2.Laplacian(working, cv2.CV_64F).var()), 1),
        "brightness_mean": round(float(value.mean()), 1),
        "brightness_std": round(float(value.std()), 1),
    }


def geometry(face: dict, bgr: np.ndarray) -> Optional[dict]:
    keypoints = face.get("keypoints")
    if not keypoints or len(keypoints) < 5:
        return None

    x1, y1, x2, y2 = face["box"]
    face_w = max(1.0, x2 - x1)
    face_h = max(1.0, y2 - y1)
    eye_a, eye_b = keypoints[0], keypoints[1]
    nose = keypoints[2]
    mouth_a, mouth_b = keypoints[3], keypoints[4]

    iod = max(abs(eye_b[0] - eye_a[0]), abs(eye_b[1] - eye_a[1]), 1.0)
    mouth_w = max(abs(mouth_b[0] - mouth_a[0]), abs(mouth_b[1] - mouth_a[1]), 1.0)
    eye_mid_x = (eye_a[0] + eye_b[0]) / 2.0
    mouth_cx = (mouth_a[0] + mouth_b[0]) / 2.0
    mouth_cy = (mouth_a[1] + mouth_b[1]) / 2.0

    dark_frac, open_extent = None, None
    half_w = max(mouth_w * 0.75, 8.0)
    left = int(max(0, mouth_cx - half_w))
    right = int(min(bgr.shape[1], mouth_cx + half_w))
    top = int(max(0, mouth_cy - 0.18 * face_h))
    bottom = int(min(bgr.shape[0], mouth_cy + 0.22 * face_h))
    if right - left >= 4 and bottom - top >= 4:
        roi = bgr[top:bottom, left:right]
        value = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)[:, :, 2]
        dark = value < 70
        dark_frac = round(float(dark.mean()), 4)
        open_extent = round(float((dark.mean(axis=1) > 0.2).mean()), 4)

    return {
        "iod_px": round(iod, 1),
        "mouth_width_px": round(mouth_w, 1),
        "mouth_to_iod": round(mouth_w / iod, 3),
        "mouth_to_face_w": round(mouth_w / face_w, 3),
        "yaw_proxy": round(abs(nose[0] - eye_mid_x) / iod, 3),
        "roll_proxy": round(abs(eye_a[1] - eye_b[1]) / iod, 3),
        "mouth_dark_frac": dark_frac,
        "mouth_open_extent": open_extent,
    }


# ---------------------------------------------------------------- view metrics


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def mouth_roi(bgr: np.ndarray, face: dict) -> Optional[tuple[np.ndarray, tuple[int, int, int, int], float]]:
    """Return (roi, (left, right, top, bottom), face_height); mirrors geometry()'s ROI."""
    keypoints = face.get("keypoints")
    if not keypoints or len(keypoints) < 5:
        return None
    x1, y1, x2, y2 = face["box"]
    face_h = max(1.0, y2 - y1)
    mouth_a, mouth_b = keypoints[3], keypoints[4]
    mouth_w = max(abs(mouth_b[0] - mouth_a[0]), abs(mouth_b[1] - mouth_a[1]), 1.0)
    cx = (mouth_a[0] + mouth_b[0]) / 2.0
    cy = (mouth_a[1] + mouth_b[1]) / 2.0
    half_w = max(mouth_w * 0.75, 8.0)
    left = int(max(0, cx - half_w))
    right = int(min(bgr.shape[1], cx + half_w))
    top = int(max(0, cy - 0.18 * face_h))
    bottom = int(min(bgr.shape[0], cy + 0.22 * face_h))
    if right - left < 4 or bottom - top < 4:
        return None
    return bgr[top:bottom, left:right], (left, right, top, bottom), face_h


def view_metrics(bgr: np.ndarray, face: dict, view: str) -> dict:
    """View-specific colour/geometry proxies. These are proxies, not clinical measurements."""
    metrics: dict[str, Optional[float]] = {}
    region = mouth_roi(bgr, face)

    if region is not None and view in ("teeth", "tongue"):
        roi = region[0]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
        if view == "teeth":
            teeth = ((val >= TEETH_MIN_VALUE) & (sat <= TEETH_MAX_SAT)).mean()
            metrics["teeth_visibility"] = round(float(teeth), 4)
        else:
            reddish = (((hue <= 10) | (hue >= 170)) & (sat >= TONGUE_SAT_MIN) & (val >= TONGUE_VALUE_MIN)).mean()
            metrics["tongue_visibility"] = round(float(reddish), 4)

    if view == "jawline":
        x1, y1, x2, y2 = face["box"]
        face_w = max(1.0, x2 - x1)
        face_h = max(1.0, y2 - y1)
        metrics["profile_aspect"] = round(face_h / face_w, 3)
        if region is not None:
            _, bounds, region_face_h = region
            left, right, _, bottom = bounds
            sub_top = min(bgr.shape[0] - 1, bottom)
            sub_bottom = min(bgr.shape[0], bottom + int(0.25 * region_face_h))
            if sub_bottom - sub_top >= 2 and right - left >= 2:
                value = cv2.cvtColor(bgr[sub_top:sub_bottom, left:right], cv2.COLOR_BGR2HSV)[:, :, 2]
                metrics["submental_brightness"] = round(float(value.mean()), 1)

    return metrics


# --------------------------------------------------------------------- scoring


def compute_ndms(views: dict) -> dict:
    """Combine per-view analyze() results into a bounded NDMS score.

    Pure (no OpenCV/torch) so it can be unit-tested. ``views`` maps a view name
    to an analyze() result dict, or None when the view was not uploaded.
    """

    def usable(name: str) -> Optional[dict]:
        result = views.get(name)
        if result and (result.get("quality") or {}).get("usable"):
            return result
        return None

    def geom(result: Optional[dict]) -> dict:
        return (result or {}).get("geometry") or {}

    def metrics(result: Optional[dict]) -> dict:
        return (result or {}).get("view_metrics") or {}

    components: list[dict] = []

    def add(name: str, value: Optional[float], note: str) -> None:
        if value is None:
            return
        components.append(
            {
                "name": name,
                "value": round(_clamp(float(value)), 3),
                "weight": NDMS_WEIGHTS[name],
                "note": note,
            }
        )

    mouth_opening: Optional[float] = None
    for name in ("teeth", "tongue", "frontal"):
        result = usable(name)
        extent = geom(result).get("mouth_open_extent") if result else None
        if extent is not None:
            mouth_opening = float(extent) / 0.5
            break
    add("mouth_opening", mouth_opening, "Open-mouth extent from the mouth-region darkness proxy.")

    teeth = usable("teeth")
    add(
        "teeth_visibility",
        metrics(teeth).get("teeth_visibility") if teeth else None,
        "Bright, low-saturation pixels in the mouth region (teeth-like).",
    )

    tongue = usable("tongue")
    add(
        "tongue_protrusion",
        metrics(tongue).get("tongue_visibility") if tongue else None,
        "Reddish, saturated pixels in the mouth region (tongue-like).",
    )

    jaw = usable("jawline")
    jaw_value: Optional[float] = None
    if jaw:
        jaw_metrics = metrics(jaw)
        aspect = jaw_metrics.get("profile_aspect")
        submental = jaw_metrics.get("submental_brightness")
        if aspect is not None:
            jaw_value = _clamp(1.0 - abs(float(aspect) - 1.35) / 0.6)
        if submental is not None:
            sub_value = _clamp((float(submental) - 30.0) / 120.0)
            jaw_value = sub_value if jaw_value is None else 0.5 * jaw_value + 0.5 * sub_value
    add("jaw_neck", jaw_value, "Low-confidence profile/jawline proxy (aspect ratio + submental brightness).")

    usable_views = [name for name in NDMS_VIEWS if usable(name) is not None]
    missing_views = [name for name in NDMS_VIEWS if name not in usable_views]
    result: dict = {
        "score": None,
        "confidence": round(len(usable_views) / len(NDMS_VIEWS), 2),
        "views_used": usable_views,
        "missing_views": missing_views,
        "components": components,
        "risk_contribution": None,
    }
    if len(components) < NDMS_MIN_COMPONENTS:
        return result

    total_weight = sum(component["weight"] for component in components)
    favorability = sum(component["value"] * component["weight"] for component in components) / total_weight
    score = _clamp(1.0 - favorability)
    # Conservative on purpose: photos may raise concern but must never lower the
    # tabular risk, so the contribution is capped to [0, NDMS_MAX_CONTRIBUTION].
    contribution = 0.0 if score <= 0.5 else NDMS_MAX_CONTRIBUTION * (score - 0.5) * 2.0
    result["score"] = round(score, 3)
    result["risk_contribution"] = round(min(NDMS_MAX_CONTRIBUTION, contribution), 1)
    return result


def blend_risk(base_risk: Optional[float], contribution: Optional[float]) -> Optional[float]:
    if base_risk is None or contribution is None:
        return None
    return round(max(0.0, min(100.0, float(base_risk) + float(contribution))), 1)


def preview_data_uri(bgr: np.ndarray, width: int = PREVIEW_WIDTH) -> str:
    height = max(1, int(bgr.shape[0] * width / bgr.shape[1]))
    resized = cv2.resize(bgr, (width, height))
    ok, buffer = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not ok:
        raise RuntimeError("Failed to encode preview")
    return "data:image/jpeg;base64," + base64.b64encode(buffer.tobytes()).decode()


# ------------------------------------------------------------------- public


def analyze(raw: bytes, view: Optional[str] = None) -> dict:
    """Analyze one upload. Returns a dict matching ImageAnalyzeOut (plus view_metrics when view is set)."""
    bgr = decode(raw)
    bgr = _resize_for_work(bgr)
    height, width = bgr.shape[:2]

    model = get_model()
    faces = detect_faces(model, bgr, PRIMARY_CONF)
    stage = "primary"
    if not faces:
        faces = [
            f
            for f in detect_faces(model, bgr, FALLBACK_CONF)
            if (f["box"][3] - f["box"][1]) >= FALLBACK_FACE_FRAC * height
        ]
        stage = "low_conf" if faces else "none"

    warnings: list[str] = []
    issues: list[str] = []

    if not faces:
        quality = quality_metrics(bgr)
        quality.update({"faces": 0, "face_area_frac": None, "usable": False, "issues": ["no_face"]})
        return {
            "status": "no_face",
            "redacted": False,
            "faces_redacted": 0,
            "quality": quality,
            "geometry": None,
            "view_metrics": {},
            "auto_fill": {},
            "auto_fill_note": "No face detected, so no measurements were taken.",
            "preview_data_uri": None,
            "warnings": ["No face detected. No preview is returned because the image is not redacted."],
        }

    faces.sort(key=lambda f: (f["box"][2] - f["box"][0]) * (f["box"][3] - f["box"][1]), reverse=True)
    faces_redacted = redact_faces(bgr, faces)
    redacted_ok = faces_redacted == len(faces)

    primary = faces[0]
    x1, y1, x2, y2 = primary["box"]
    face_area_frac = ((x2 - x1) * (y2 - y1)) / float(width * height)

    measures = quality_metrics(bgr)
    measures.update(
        {
            "faces": len(faces),
            "face_area_frac": round(face_area_frac, 4),
            "usable": False,
            "issues": [],
        }
    )

    if len(faces) > 1:
        issues.append("multiple_faces")
        warnings.append("More than one face detected; only the largest was measured.")
    if face_area_frac < MIN_FACE_AREA_FRAC:
        issues.append("face_too_small")
    if measures["blur_score"] < MIN_BLUR:
        issues.append("blurry")
    if not (BRIGHT_LOW <= measures["brightness_mean"] <= BRIGHT_HIGH):
        issues.append("bad_brightness")
    if not redacted_ok:
        issues.append("redaction_incomplete")
        warnings.append("Could not redact every detected face; no preview returned.")

    measures["issues"] = issues
    measures["usable"] = not issues

    geom = geometry(primary, bgr)

    return {
        "status": "ok",
        "redacted": redacted_ok,
        "faces_redacted": faces_redacted,
        "quality": measures,
        "geometry": geom,
        "view_metrics": view_metrics(bgr, primary, view) if view else {},
        "auto_fill": {},
        "auto_fill_note": (
            "No clinical field is auto-filled. On this dataset, photo geometry did not "
            "carry usable signal for the difficulty label, so the doctor's measurements "
            "remain the input to the prediction."
        ),
        "preview_data_uri": preview_data_uri(bgr) if redacted_ok else None,
        "warnings": warnings,
    }
