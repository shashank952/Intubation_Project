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
DETECT_MAX_SIDE = 1600
PREVIEW_WIDTH = 640
BLACK = (0, 0, 0)

STRIP_HEIGHT = 0.80
STRIP_RISE = 0.10
STRIP_PAD_X = 0.06
FALLBACK_TOP = 0.28
FALLBACK_BOTTOM = 0.52

_model = None


def default_model_path() -> Path:
    override = os.getenv("FACE_MODEL_PATH")
    if override:
        return Path(override)
    return Path.home() / ".cache" / "yolo-face" / "yolo26n-face.pt"


def get_model():
    """Load the face model once. Raises (no silent fallback) if it is missing."""
    global _model
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
            upright = ImageOps.exif_transpose(image).convert("RGB")
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
    result = model.predict(bgr, conf=conf, iou=0.5, verbose=False)[0]
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


def preview_data_uri(bgr: np.ndarray, width: int = PREVIEW_WIDTH) -> str:
    height = max(1, int(bgr.shape[0] * width / bgr.shape[1]))
    resized = cv2.resize(bgr, (width, height))
    ok, buffer = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not ok:
        raise RuntimeError("Failed to encode preview")
    return "data:image/jpeg;base64," + base64.b64encode(buffer.tobytes()).decode()


# ------------------------------------------------------------------- public


def analyze(raw: bytes) -> dict:
    """Analyze one upload. Returns a dict matching ImageAnalyzeOut."""
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
        "auto_fill": {},
        "auto_fill_note": (
            "No clinical field is auto-filled. On this dataset, photo geometry did not "
            "carry usable signal for the difficulty label, so the doctor's measurements "
            "remain the input to the prediction."
        ),
        "preview_data_uri": preview_data_uri(bgr) if redacted_ok else None,
        "warnings": warnings,
    }
