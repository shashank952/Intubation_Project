"""Extract quality + geometry features from the redacted airway photos.

Why
---
The dashboard needs "upload a photo -> the system reads something useful".
This script produces that first version: per-photo quality and face geometry,
using the same YOLO face model the redaction step already uses.

What is a real measurement vs a proxy
-------------------------------------
REAL (from the 5 face keypoints: 2 eyes, nose, 2 mouth corners):
    * inter-ocular distance (IOD)
    * face box width/height
    * mouth width (corner to corner)
    * mouth width / IOD, mouth width / face width
    * head yaw and roll proxies

PROXY (image analysis, not a clinical measurement):
    * mouth_dark_frac / mouth_open_extent - darkness inside the mouth region.
      An open mouth exposes a dark interior, but a beard, shadow, or teeth can
      fool it. Do not present this as "mouth opening in mm".

NOT MEASURED:
    * Mallampati class (needs tongue out, standardised view)
    * millimetres of anything (a photo has no scale reference)

Inputs
------
    data/raw/redacted_images/*.jpg        (redacted only, never the originals)

Outputs
-------
    data/temp/image_features.csv               one row per photo
    data/temp/image_features_by_patient.csv    one row per patient

Usage
-----
    py -3.12 scripts/extract_image_features.py
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_laryngoscopy_datasets as base  # noqa: E402
import redact_eyes as redact  # noqa: E402

IMAGE_DIR = base.ROOT / "data" / "raw" / "redacted_images"
OUT_PHOTO = base.TEMP / "image_features.csv"
OUT_PATIENT = base.TEMP / "image_features_by_patient.csv"

NAME_RE = re.compile(r"^(\d+)(?:\((\d+)\))?$", re.IGNORECASE)
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

PRIMARY_CONF = 0.35
FALLBACK_CONF = 0.10
MIN_FACE_AREA_FRAC = 0.02
MIN_BLUR = 40.0
BRIGHT_LOW, BRIGHT_HIGH = 35.0, 235.0
BLUR_WORKING_WIDTH = 800


def blur_score(gray: np.ndarray) -> float:
    height, width = gray.shape[:2]
    if width > BLUR_WORKING_WIDTH:
        scale = BLUR_WORKING_WIDTH / width
        gray = cv2.resize(gray, (BLUR_WORKING_WIDTH, max(1, int(height * scale))))
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def mouth_darkness(bgr: np.ndarray, face: dict, mouth_width: float, face_height: float):
    """Dark-pixel statistics inside the mouth region (proxy for an open mouth)."""
    keypoints = face.get("keypoints")
    if not keypoints or len(keypoints) < 5:
        return "", ""
    left_corner, right_corner = keypoints[3], keypoints[4]
    cx = (left_corner[0] + right_corner[0]) / 2.0
    cy = (left_corner[1] + right_corner[1]) / 2.0
    half_w = max(mouth_width * 0.75, 8.0)
    top = cy - 0.18 * face_height
    bottom = cy + 0.22 * face_height
    x1, x2 = int(max(0, cx - half_w)), int(min(bgr.shape[1], cx + half_w))
    y1, y2 = int(max(0, top)), int(min(bgr.shape[0], bottom))
    if x2 - x1 < 4 or y2 - y1 < 4:
        return "", ""
    roi = bgr[y1:y2, x1:x2]
    value = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)[:, :, 2]
    dark = value < 70
    dark_frac = float(dark.mean())
    row_dark = dark.mean(axis=1) > 0.2
    open_extent = float(row_dark.mean())
    return round(dark_frac, 4), round(open_extent, 4)


def features_for(path: Path, model) -> dict:
    bgr = cv2.imread(str(path))
    if bgr is None:
        return {"photo_file": path.name, "usable": 0, "reason": "unreadable"}

    height, width = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    record: dict = {
        "photo_file": path.name,
        "width": width,
        "height": height,
        "megapixels": round(width * height / 1e6, 2),
        "blur_score": round(blur_score(gray), 1),
        "brightness_mean": round(float(hsv[:, :, 2].mean()), 1),
        "brightness_std": round(float(hsv[:, :, 2].std()), 1),
        "faces": 0,
        "face_score": "",
        "face_area_frac": "",
        "detection_stage": "none",
        "iod_px": "",
        "face_w": "",
        "face_h": "",
        "mouth_width_px": "",
        "mouth_to_iod": "",
        "mouth_to_face_w": "",
        "yaw_proxy": "",
        "roll_proxy": "",
        "mouth_dark_frac": "",
        "mouth_open_extent": "",
        "usable": 0,
        "reason": "",
    }

    faces = redact.detect_faces(model, bgr, PRIMARY_CONF)
    stage = "primary"
    if not faces:
        faces = [
            f
            for f in redact.detect_faces(model, bgr, FALLBACK_CONF)
            if (f["box"][3] - f["box"][1]) >= redact.MIN_FALLBACK_FACE_FRAC * height
        ]
        stage = "low_conf" if faces else "none"

    reasons = []
    if not faces:
        reasons.append("no_face")
        record["reason"] = ",".join(reasons)
        return record

    # largest face wins; extra faces are recorded but not measured
    faces.sort(key=lambda f: (f["box"][2] - f["box"][0]) * (f["box"][3] - f["box"][1]), reverse=True)
    face = faces[0]
    x1, y1, x2, y2 = face["box"]
    face_w = max(1.0, x2 - x1)
    face_h = max(1.0, y2 - y1)
    area_frac = (face_w * face_h) / (width * height)

    record.update(
        {
            "faces": len(faces),
            "face_score": round(face["score"], 3),
            "face_area_frac": round(area_frac, 4),
            "detection_stage": stage,
            "face_w": round(face_w, 1),
            "face_h": round(face_h, 1),
        }
    )

    keypoints = face.get("keypoints")
    if keypoints and len(keypoints) >= 5:
        eye_a, eye_b = keypoints[0], keypoints[1]
        nose = keypoints[2]
        mouth_a, mouth_b = keypoints[3], keypoints[4]
        iod = max(abs(eye_b[0] - eye_a[0]), abs(eye_b[1] - eye_a[1]), 1.0)
        mouth_w = max(abs(mouth_b[0] - mouth_a[0]), abs(mouth_b[1] - mouth_a[1]), 1.0)
        eye_mid_x = (eye_a[0] + eye_b[0]) / 2.0
        record.update(
            {
                "iod_px": round(iod, 1),
                "mouth_width_px": round(mouth_w, 1),
                "mouth_to_iod": round(mouth_w / iod, 3),
                "mouth_to_face_w": round(mouth_w / face_w, 3),
                "yaw_proxy": round(abs(nose[0] - eye_mid_x) / iod, 3),
                "roll_proxy": round(abs(eye_a[1] - eye_b[1]) / iod, 3),
            }
        )
        dark_frac, open_extent = mouth_darkness(bgr, face, mouth_w, face_h)
        record["mouth_dark_frac"] = dark_frac
        record["mouth_open_extent"] = open_extent
    else:
        reasons.append("no_keypoints")

    if len(faces) > 1:
        reasons.append("multiple_faces")
    if area_frac < MIN_FACE_AREA_FRAC:
        reasons.append("face_too_small")
    if record["blur_score"] < MIN_BLUR:
        reasons.append("blurry")
    if not (BRIGHT_LOW <= record["brightness_mean"] <= BRIGHT_HIGH):
        reasons.append("bad_brightness")

    record["usable"] = 0 if reasons else 1
    record["reason"] = ",".join(reasons)
    return record


def patient_no_and_copy(name: str):
    match = NAME_RE.match(Path(name).stem)
    if not match:
        return "", ""
    return int(match.group(1)), int(match.group(2)) if match.group(2) else 0


def main() -> int:
    if not IMAGE_DIR.is_dir():
        raise SystemExit(f"Missing image folder: {IMAGE_DIR}")

    from ultralytics import YOLO

    model = YOLO(str(redact.DEFAULT_MODEL))
    paths = [p for p in sorted(IMAGE_DIR.iterdir(), key=lambda p: p.name.lower())
             if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    if not paths:
        raise SystemExit("No photos found.")

    records = []
    for index, path in enumerate(paths, start=1):
        record = features_for(path, model)
        number, copy = patient_no_and_copy(path.name)
        record["patient_no"] = number
        record["patient_id"] = f"P-{number:04d}" if number != "" else ""
        record["copy_index"] = copy
        records.append(record)
        if index % 40 == 0 or index == len(paths):
            print(f"  {index}/{len(paths)}")

    fields = [
        "photo_file", "patient_id", "patient_no", "copy_index",
        "width", "height", "megapixels", "blur_score",
        "brightness_mean", "brightness_std",
        "faces", "face_score", "face_area_frac", "detection_stage",
        "iod_px", "face_w", "face_h", "mouth_width_px",
        "mouth_to_iod", "mouth_to_face_w", "yaw_proxy", "roll_proxy",
        "mouth_dark_frac", "mouth_open_extent",
        "usable", "reason",
    ]
    with OUT_PHOTO.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    # per-patient summary
    by_patient: dict[str, list[dict]] = {}
    for record in records:
        if record["patient_id"]:
            by_patient.setdefault(record["patient_id"], []).append(record)

    def mean_of(rows, key):
        values = [row[key] for row in rows if isinstance(row.get(key), (int, float))]
        return round(float(np.mean(values)), 3) if values else ""

    summary = []
    for patient_id in sorted(by_patient):
        rows = by_patient[patient_id]
        usable = [r for r in rows if r["usable"] == 1]
        summary.append(
            {
                "patient_id": patient_id,
                "photos": len(rows),
                "usable_photos": len(usable),
                "usable_rate": round(len(usable) / len(rows), 2),
                "mean_blur": mean_of(rows, "blur_score"),
                "mean_brightness": mean_of(rows, "brightness_mean"),
                "mean_face_area_frac": mean_of(rows, "face_area_frac"),
                "mean_mouth_to_iod": mean_of(rows, "mouth_to_iod"),
                "mean_mouth_open_extent": mean_of(rows, "mouth_open_extent"),
                "reasons": ", ".join(sorted({r["reason"] for r in rows if r["reason"]})),
            }
        )

    with OUT_PATIENT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

    usable = sum(1 for r in records if r["usable"] == 1)
    no_face = sum(1 for r in records if "no_face" in str(r["reason"]))
    reasons: dict[str, int] = {}
    for record in records:
        for reason in filter(None, str(record["reason"]).split(",")):
            reasons[reason] = reasons.get(reason, 0) + 1

    print(f"\nPhotos processed : {len(records)}")
    print(f"Usable           : {usable} ({usable / len(records):.1%})")
    print(f"No face detected : {no_face}")
    print(f"Reasons          : {reasons}")
    print(f"Patients covered : {len(summary)}")
    print(f"Patients with >=1 usable photo: {sum(1 for s in summary if s['usable_photos'] > 0)}")
    print(f"\nWrote {OUT_PHOTO.name} and {OUT_PATIENT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
