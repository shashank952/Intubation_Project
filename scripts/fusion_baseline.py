"""Does adding photo features improve on the Excel-only baseline?

Compares three feature sets on the SAME patients and the SAME folds:

    tabular  : the 11 one-hot features (Excel measurements)
    image    : 6 per-patient photo summaries
    fusion   : both concatenated

Target = the doctor's decision (Easy / Moderate / Difficult). This is NOT a
claim about real intubation outcome; it measures whether photos help reproduce
the recorded decision.

Method: repeated stratified 5-fold (5 x 10). Preprocessing lives inside each
fold, so the imputer/scaler never sees the test fold.

Usage
-----
    py -3.12 scripts/fusion_baseline.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_laryngoscopy_datasets as base  # noqa: E402
import train_tabular_baseline as tab  # noqa: E402

IMAGE_SUMMARY = base.TEMP / "image_features_by_patient.csv"
OUT_JSON = base.TEMP / "fusion_results.json"

CLASS_NAMES = ["Easy", "Moderate", "Difficult"]
IMAGE_FEATURES = [
    "usable_rate",
    "mean_blur",
    "mean_brightness",
    "mean_face_area_frac",
    "mean_mouth_to_iod",
    "mean_mouth_open_extent",
]


def load_image_summary() -> dict[str, dict]:
    with IMAGE_SUMMARY.open(encoding="utf-8") as handle:
        return {row["patient_id"]: row for row in csv.DictReader(handle)}


def build_matrices():
    grid = base.read_sheet(tab.ONEHOT, tab.SHEET)
    header = []
    col = 1
    while grid.get((1, col), ""):
        header.append(grid[(1, col)])
        col += 1

    rows = []
    row = 2
    while grid.get((row, 1), ""):
        rows.append({h: grid.get((row, i + 1), "") for i, h in enumerate(header)})
        row += 1

    image_summary = load_image_summary()
    tab_features = [h for h in header if h not in tab.ID_COLUMNS | tab.TARGET_COLUMNS]

    patient_ids, X_tab, X_img, y = [], [], [], []
    for record in rows:
        pid = record["Patient_ID"]
        summary = image_summary.get(pid)
        if summary is None:
            continue
        patient_ids.append(pid)
        X_tab.append([float(record[f]) if record[f] != "" else np.nan for f in tab_features])
        X_img.append(
            [float(summary[f]) if summary.get(f, "") != "" else np.nan for f in IMAGE_FEATURES]
        )
        y.append(int(record["Target"]))

    return (
        patient_ids,
        np.array(X_tab, dtype=float),
        np.array(X_img, dtype=float),
        np.array(y, dtype=int),
        tab_features,
    )


def make_model():
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("model", LogisticRegression(max_iter=3000, class_weight="balanced")),
        ]
    )


def evaluate(X, y, cv) -> dict:
    acc, bacc, f1 = [], [], []
    recalls = []
    for train_idx, test_idx in cv.split(X, y):
        model = make_model()
        model.fit(X[train_idx], y[train_idx])
        pred = model.predict(X[test_idx])
        acc.append(accuracy_score(y[test_idx], pred))
        bacc.append(balanced_accuracy_score(y[test_idx], pred))
        f1.append(f1_score(y[test_idx], pred, average="macro", zero_division=0))
        recalls.append(
            recall_score(y[test_idx], pred, labels=[0, 1, 2], average=None, zero_division=0)
        )
    recalls = np.array(recalls)
    return {
        "accuracy_mean": float(np.mean(acc)),
        "accuracy_std": float(np.std(acc)),
        "balanced_accuracy_mean": float(np.mean(bacc)),
        "f1_macro_mean": float(np.mean(f1)),
        "f1_macro_std": float(np.std(f1)),
        "recall_mean": {n: float(recalls[:, i].mean()) for i, n in enumerate(CLASS_NAMES)},
    }


def main() -> int:
    patient_ids, X_tab, X_img, y, tab_features = build_matrices()
    print(f"Patients: {len(y)}   tabular={X_tab.shape[1]}  image={X_img.shape[1]}")
    print(f"Classes : { {n: int((y == i).sum()) for i, n in enumerate(CLASS_NAMES)} }\n")

    X_fusion = np.hstack([X_tab, X_img])
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=42)

    results = {}
    for name, X in (("tabular_only", X_tab), ("image_only", X_img), ("fusion", X_fusion)):
        metrics = evaluate(X, y, cv)
        results[name] = metrics
        print(f"--- {name} ---")
        print(f"  accuracy    {metrics['accuracy_mean']:.3f} +/- {metrics['accuracy_std']:.3f}")
        print(f"  balanced    {metrics['balanced_accuracy_mean']:.3f}")
        print(f"  macro F1    {metrics['f1_macro_mean']:.3f} +/- {metrics['f1_macro_std']:.3f}")
        print(
            "  recall      "
            + "  ".join(f"{c}={metrics['recall_mean'][c]:.2f}" for c in CLASS_NAMES)
        )
        print()

    delta = results["fusion"]["accuracy_mean"] - results["tabular_only"]["accuracy_mean"]
    print(f"Fusion minus tabular accuracy: {delta:+.3f}")
    print(f"Fusion minus tabular Difficult recall: "
          f"{results['fusion']['recall_mean']['Difficult'] - results['tabular_only']['recall_mean']['Difficult']:+.2f}")

    OUT_JSON.write_text(
        json.dumps(
            {
                "n_patients": len(y),
                "tabular_features": tab_features,
                "image_features": IMAGE_FEATURES,
                "results": results,
                "fusion_minus_tabular_accuracy": delta,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nSaved {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
