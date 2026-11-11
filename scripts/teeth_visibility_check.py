"""Can teeth be assessed from these photos?

What this does
--------------
1. Finds the face in every redacted photo (YOLO face model, same as redaction).
2. Crops the mouth region using the mouth-corner keypoints.
3. Scores the crop for "teeth-like" content:
       white_frac  - bright, low-saturation pixels (enamel)
       dark_frac   - dark pixels (open mouth interior)
       edge_density- Canny edge density (tooth boundaries)
4. Reports how many photos / patients have an assessable mouth.
5. Tests whether any of it separates intact vs abnormal teeth at patient level.

Outputs
-------
    data/temp/teeth_crops.csv     one row per photo
    data/temp/teeth_check.html    contact sheet of mouth crops (open in browser)
    data/temp/teeth_signal.json   whether the scores carry any signal

Everything is computed from data/raw/redacted_images only.

Usage
-----
    py -3.12 scripts/teeth_visibility_check.py
"""

from __future__ import annotations

import base64
import csv
import io
import json
import sys
import warnings
from pathlib import Path

import cv2
import numpy as np

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_laryngoscopy_datasets as base  # noqa: E402
import redact_eyes as redact  # noqa: E402
import train_tabular_baseline as tab  # noqa: E402

IMAGE_DIR = base.ROOT / "data" / "raw" / "redacted_images"
OUT_CSV = base.TEMP / "teeth_crops.csv"
OUT_HTML = base.TEMP / "teeth_check.html"
OUT_JSON = base.TEMP / "teeth_signal.json"

PRIMARY_CONF = 0.35
FALLBACK_CONF = 0.10

# heuristic thresholds; the report shows the distribution so they can be argued with
TEETH_WHITE_MIN = 0.03
TEETH_EDGE_MIN = 0.015
MIN_CROP_WIDTH = 60


def load_teeth_labels() -> dict[str, tuple[int, str]]:
    grid = base.read_sheet(tab.ONEHOT, "Train_OneHot_Labeled")
    header = []
    col = 1
    while grid.get((1, col), ""):
        header.append(grid[(1, col)])
        col += 1
    labels = {}
    row = 2
    while grid.get((row, 1), ""):
        record = {h: grid.get((row, i + 1), "") for i, h in enumerate(header)}
        labels[record["Patient_ID"]] = (int(record["Teeth_Abnormal"]), record["Target_Name"])
        row += 1
    return labels


def mouth_crop(bgr: np.ndarray, face: dict):
    keypoints = face.get("keypoints")
    conf = face.get("keypoint_conf")
    if not keypoints or len(keypoints) < 5:
        return None
    if conf and min(conf[3], conf[4]) < 0.3:
        return None

    x1, y1, x2, y2 = face["box"]
    face_w = max(1.0, x2 - x1)
    face_h = max(1.0, y2 - y1)
    m1, m2 = keypoints[3], keypoints[4]
    mouth_w = max(abs(m2[0] - m1[0]), 8.0)
    cx = (m1[0] + m2[0]) / 2.0
    cy = (m1[1] + m2[1]) / 2.0

    half_w = 0.75 * mouth_w + 0.08 * face_w
    left = int(max(0, cx - half_w))
    right = int(min(bgr.shape[1], cx + half_w))
    top = int(max(0, cy - 0.30 * face_h))
    bottom = int(min(bgr.shape[0], cy + 0.30 * face_h))
    if right - left < 20 or bottom - top < 12:
        return None
    return bgr[top:bottom, left:right], (left, top, right, bottom)


def score_crop(crop: np.ndarray) -> dict:
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    value, saturation = hsv[:, :, 2], hsv[:, :, 1]
    white = ((value >= 130) & (saturation <= 80)).mean()
    dark = (value <= 60).mean()
    edges = cv2.Canny(gray, 60, 160) > 0
    return {
        "white_frac": float(white),
        "dark_frac": float(dark),
        "edge_density": float(edges.mean()),
        "crop_w": int(crop.shape[1]),
        "crop_h": int(crop.shape[0]),
    }


def detect_largest(bgr: np.ndarray, model):
    faces = redact.detect_faces(model, bgr, PRIMARY_CONF)
    if not faces:
        faces = [
            f for f in redact.detect_faces(model, bgr, FALLBACK_CONF)
            if (f["box"][3] - f["box"][1]) >= redact.MIN_FALLBACK_FACE_FRAC * bgr.shape[0]
        ]
    if not faces:
        return None
    faces.sort(key=lambda f: (f["box"][2] - f["box"][0]) * (f["box"][3] - f["box"][1]), reverse=True)
    return faces[0]


def crop_data_uri(crop: np.ndarray, width: int = 220) -> str:
    height = max(1, int(crop.shape[0] * width / crop.shape[1]))
    resized = cv2.resize(crop, (width, height))
    ok, buffer = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, 72])
    return "data:image/jpeg;base64," + base64.b64encode(buffer.tobytes()).decode()


def main() -> int:
    labels = load_teeth_labels()
    from ultralytics import YOLO
    model = YOLO(str(redact.DEFAULT_MODEL))

    paths = [p for p in sorted(IMAGE_DIR.iterdir(), key=lambda p: p.name.lower())
             if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}]

    rows, crops_by_patient = [], {}
    for index, path in enumerate(paths, start=1):
        bgr = cv2.imread(str(path))
        if bgr is None:
            continue
        face = detect_largest(bgr, model)
        if face is None:
            rows.append({"photo_file": path.name, "patient_id": "", "white_frac": "",
                         "dark_frac": "", "edge_density": "", "crop_w": 0, "crop_h": 0,
                         "teeth_visible": 0, "reason": "no_face"})
            continue
        result = mouth_crop(bgr, face)
        if result is None:
            rows.append({"photo_file": path.name, "patient_id": "", "white_frac": "",
                         "dark_frac": "", "edge_density": "", "crop_w": 0, "crop_h": 0,
                         "teeth_visible": 0, "reason": "no_mouth_crop"})
            continue
        crop, box = result
        scores = score_crop(crop)
        visible = int(
            scores["white_frac"] >= TEETH_WHITE_MIN
            and scores["edge_density"] >= TEETH_EDGE_MIN
            and scores["crop_w"] >= MIN_CROP_WIDTH
        )
        number = path.stem.split("(")[0]
        patient_id = f"P-{int(number):04d}" if number.isdigit() else ""
        rows.append({
            "photo_file": path.name,
            "patient_id": patient_id,
            **{k: round(v, 4) if isinstance(v, float) else v for k, v in scores.items()},
            "teeth_visible": visible,
            "reason": "" if visible else "not_visible",
        })
        if visible and patient_id:
            crops_by_patient.setdefault(patient_id, []).append((path.name, crop, scores))
        if index % 50 == 0:
            print(f"  {index}/{len(paths)}")

    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    scored = [r for r in rows if r["white_frac"] != ""]
    visible = [r for r in rows if r["teeth_visible"] == 1]
    patients_with = {r["patient_id"] for r in visible if r["patient_id"]}
    print(f"\nPhotos processed        : {len(rows)}")
    print(f"Mouth crop obtained     : {len(scored)} ({len(scored)/len(rows):.1%})")
    print(f"Teeth-visible by rule   : {len(visible)} ({len(visible)/len(rows):.1%})")
    print(f"Patients with >=1 clear : {len(patients_with)} / {len(labels)}")

    intact_vis = [p for p in patients_with if labels.get(p, (None,))[0] == 0]
    abnormal_vis = [p for p in patients_with if labels.get(p, (None,))[0] == 1]
    print(f"  ...of 64 intact   : {len(intact_vis)}")
    print(f"  ...of 16 abnormal : {len(abnormal_vis)}")

    # distribution, so the threshold can be judged
    for key in ("white_frac", "dark_frac", "edge_density"):
        values = np.array([r[key] for r in scored], dtype=float)
        print(f"  {key:<13} p10={np.percentile(values,10):.3f} "
              f"median={np.median(values):.3f} p90={np.percentile(values,90):.3f}")

    # --- does any of it separate intact vs abnormal teeth? (patient level)
    per_patient = {}
    for patient_id, items in crops_by_patient.items():
        if patient_id not in labels:
            continue
        per_patient[patient_id] = {
            "white": float(np.mean([s["white_frac"] for _, _, s in items])),
            "dark": float(np.mean([s["dark_frac"] for _, _, s in items])),
            "edge": float(np.mean([s["edge_density"] for _, _, s in items])),
            "count": len(items),
            "y": labels[patient_id][0],
        }

    signal = {"patients_with_crops": len(per_patient)}
    if len(per_patient) >= 20 and len({v["y"] for v in per_patient.values()}) == 2:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_score
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        X = np.array([[v["white"], v["dark"], v["edge"], v["count"]] for v in per_patient.values()])
        y = np.array([v["y"] for v in per_patient.values()])
        cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=42)
        for name, model_obj in (
            ("logreg", Pipeline([("s", StandardScaler()), ("m", LogisticRegression(max_iter=2000, class_weight="balanced"))])),
            ("forest", RandomForestClassifier(n_estimators=300, class_weight="balanced_subsample", random_state=42)),
        ):
            acc = cross_val_score(model_obj, X, y, cv=cv, scoring="accuracy")
            auc = cross_val_score(model_obj, X, y, cv=cv, scoring="roc_auc")
            signal[name] = {"accuracy": round(float(acc.mean()), 3), "roc_auc": round(float(auc.mean()), 3)}
            print(f"  signal {name:<7}: accuracy={acc.mean():.3f}  roc_auc={auc.mean():.3f}  (n={len(y)})")
    else:
        print("  not enough patients with visible teeth to test signal")

    OUT_JSON.write_text(json.dumps(signal, indent=2), encoding="utf-8")

    # --- contact sheet for the human eye
    cards = []
    for patient_id in sorted(labels):
        items = crops_by_patient.get(patient_id, [])
        abnormal, difficulty = labels[patient_id]
        tag = "ABNORMAL" if abnormal else "intact"
        colour = "#b91c1c" if abnormal else "#15803d"
        tiles = "".join(
            f'<figure><img src="{crop_data_uri(crop)}" alt="{name}">'
            f'<figcaption>{name}<br>white={s["white_frac"]:.2f} edge={s["edge_density"]:.3f}</figcaption></figure>'
            for name, crop, s in items[:4]
        ) or '<p class="none">no clear mouth crop</p>'
        cards.append(
            f'<section class="card"><header><h2>{patient_id}</h2>'
            f'<span class="tag" style="background:{colour}">{tag}</span>'
            f'<span class="meta">{difficulty} &middot; {len(items)} clear crop(s)</span></header>'
            f'<div class="row">{tiles}</div></section>'
        )

    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Teeth visibility check</title><style>
body{{font-family:ui-sans-serif,system-ui,sans-serif;margin:0;padding:24px;background:#f5f5f4;color:#111}}
h1{{font-size:19px;margin:0 0 4px}}p.sub{{margin:0 0 18px;color:#555;font-size:13px}}
.card{{background:#fff;border:1px solid #d6d3d1;border-radius:8px;padding:10px 12px;margin-bottom:12px}}
.card header{{display:flex;align-items:center;gap:10px;margin-bottom:8px}}
.card h2{{font-size:13px;margin:0;font-variant-numeric:tabular-nums}}
.tag{{color:#fff;font-size:10px;font-weight:700;padding:2px 7px;border-radius:999px;letter-spacing:.04em}}
.meta{{margin-left:auto;font-size:11px;color:#777}}
.row{{display:flex;flex-wrap:wrap;gap:8px}}figure{{margin:0;width:220px}}
figure img{{width:220px;border-radius:4px;border:1px solid #e7e5e4;display:block}}
figcaption{{font-size:10px;color:#666;margin-top:2px;line-height:1.35}}
.none{{font-size:12px;color:#b45309;margin:0}}
</style></head><body>
<h1>Teeth visibility check</h1>
<p class="sub">{len(scored)} mouth crops &middot; green = intact, red = abnormal (from the Excel label) &middot; white/edge are the heuristic scores</p>
{''.join(cards)}
</body></html>"""
    OUT_HTML.write_text(html, encoding="utf-8")

    print(f"\nWrote {OUT_CSV.name}, {OUT_HTML.name}, {OUT_JSON.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
