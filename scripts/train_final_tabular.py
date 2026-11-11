"""Train and freeze the real-data tabular model.

This replaces nothing in the repo yet: the served checkpoint is still the
synthetic-trained TabTransformer. This script produces the *real-patient*
model as a separate, versioned artifact so the dashboard has something honest
to call.

Model choice
------------
Logistic regression with balanced class weights. Random forest scores higher
accuracy (0.901 vs 0.854) but only recalls 0.46 of the Difficult cases, while
logistic regression recalls 0.95. For a triage aid, missing a difficult airway
is the expensive error, so logistic regression wins.

Target
------
0 = Easy, 1 = Moderate, 2 = Difficult
This is the doctor's recorded decision, NOT a post-hoc intubation outcome.

Outputs
-------
    checkpoints/tabular_real_v1.joblib     pipeline + feature list + classes
    checkpoints/tabular_real_v1.json       metrics, data hash, caveats

Usage
-----
    py -3.12 scripts/train_final_tabular.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import sklearn
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_laryngoscopy_datasets as base  # noqa: E402
import train_tabular_baseline as tab  # noqa: E402

MODEL_PATH = base.ROOT / "checkpoints" / "tabular_real_v1.joblib"
META_PATH = base.ROOT / "checkpoints" / "tabular_real_v1.json"

CLASS_NAMES = ["Easy", "Moderate", "Difficult"]


def make_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(max_iter=3000, class_weight="balanced", random_state=42),
            ),
        ]
    )


def cross_validate(X, y):
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=42)
    acc, bal, f1 = [], [], []
    recall_by_class = []
    precision_by_class = []
    oof_true, oof_pred = [], []

    for fold, (train_idx, test_idx) in enumerate(cv.split(X, y)):
        model = make_pipeline()
        model.fit(X[train_idx], y[train_idx])
        pred = model.predict(X[test_idx])
        acc.append(accuracy_score(y[test_idx], pred))
        bal.append(balanced_accuracy_score(y[test_idx], pred))
        f1.append(f1_score(y[test_idx], pred, average="macro", zero_division=0))
        recall_by_class.append(
            recall_score(y[test_idx], pred, labels=[0, 1, 2], average=None, zero_division=0)
        )
        precision_by_class.append(
            precision_score(y[test_idx], pred, labels=[0, 1, 2], average=None, zero_division=0)
        )
        if fold < 5:  # one clean out-of-fold pass for the confusion matrix
            oof_true.extend(y[test_idx].tolist())
            oof_pred.extend(pred.tolist())

    recall_by_class = np.array(recall_by_class)
    precision_by_class = np.array(precision_by_class)
    return {
        "scheme": "RepeatedStratifiedKFold(n_splits=5, n_repeats=10)",
        "folds": len(acc),
        "accuracy_mean": round(float(np.mean(acc)), 3),
        "accuracy_std": round(float(np.std(acc)), 3),
        "balanced_accuracy_mean": round(float(np.mean(bal)), 3),
        "f1_macro_mean": round(float(np.mean(f1)), 3),
        "f1_macro_std": round(float(np.std(f1)), 3),
        "recall_mean": {
            name: round(float(recall_by_class[:, i].mean()), 3)
            for i, name in enumerate(CLASS_NAMES)
        },
        "recall_std": {
            name: round(float(recall_by_class[:, i].std()), 3)
            for i, name in enumerate(CLASS_NAMES)
        },
        "precision_mean": {
            name: round(float(precision_by_class[:, i].mean()), 3)
            for i, name in enumerate(CLASS_NAMES)
        },
        "confusion_matrix_single_pass": confusion_matrix(
            np.array(oof_true), np.array(oof_pred), labels=[0, 1, 2]
        ).tolist(),
    }


def data_hash(X: np.ndarray, y: np.ndarray) -> str:
    payload = np.round(np.nan_to_num(X, nan=-999.0), 4).tobytes() + y.tobytes()
    return "sha256:" + hashlib.sha256(payload).hexdigest()[:16]


def main() -> int:
    import joblib

    if not tab.ONEHOT.exists():
        raise SystemExit(f"Missing {tab.ONEHOT}")

    X, y, features = tab.load_data()
    print(f"Patients: {len(y)}   Features: {len(features)}")
    print("Classes :", {n: int((y == i).sum()) for i, n in enumerate(CLASS_NAMES)})

    metrics = cross_validate(X, y)
    print("\nCross-validation (5-fold x 10 repeats):")
    print(f"  accuracy      {metrics['accuracy_mean']:.3f} +/- {metrics['accuracy_std']:.3f}")
    print(f"  balanced acc  {metrics['balanced_accuracy_mean']:.3f}")
    print(f"  macro F1      {metrics['f1_macro_mean']:.3f} +/- {metrics['f1_macro_std']:.3f}")
    for name in CLASS_NAMES:
        print(
            f"  {name:<10} recall={metrics['recall_mean'][name]:.2f}  "
            f"precision={metrics['precision_mean'][name]:.2f}"
        )
    print("  confusion (rows=true, cols=pred, one 5-fold pass):")
    for label, row in zip(CLASS_NAMES, metrics["confusion_matrix_single_pass"]):
        print(f"    {label:<10} {row}")

    final_model = make_pipeline()
    final_model.fit(X, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "pipeline": final_model,
            "features": features,
            "classes": CLASS_NAMES,
            "target_definition": "doctor's recorded decision (not intubation outcome)",
        },
        MODEL_PATH,
    )

    meta = {
        "model_file": MODEL_PATH.name,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_patients": int(len(y)),
        "n_features": len(features),
        "features": features,
        "classes": CLASS_NAMES,
        "class_counts": {n: int((y == i).sum()) for i, n in enumerate(CLASS_NAMES)},
        "target_definition": (
            "Doctor's recorded decision in AI laryngoscopy2.xlsx. "
            "This is NOT a post-hoc intubation outcome."
        ),
        "model": "LogisticRegression(class_weight=balanced) + median imputer + standard scaler",
        "why_this_model": (
            "Random forest had higher accuracy (0.901) but Difficult recall 0.46; "
            "logistic regression recalls 0.95. Missing a difficult airway is the costly error."
        ),
        "cv": metrics,
        "data_hash": data_hash(X, y),
        "sklearn_version": sklearn.__version__,
        "caveats": [
            "80 patients only; prototype, not a clinical device.",
            "Labels are the doctor's decision, so performance measures agreement with that decision.",
            "Underlying data is not a random sample; do not report as clinical accuracy.",
        ],
    }
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # reload and prove it works
    loaded = joblib.load(MODEL_PATH)
    pipeline = loaded["pipeline"]
    sample = X[:1]
    probabilities = pipeline.predict_proba(sample)[0]
    print("\nReload check (patient 1):")
    print(f"  prediction  : {CLASS_NAMES[int(np.argmax(probabilities))]}")
    print("  probabilities:", {n: round(float(p), 3) for n, p in zip(CLASS_NAMES, probabilities)})

    print(f"\nWrote {MODEL_PATH}")
    print(f"Wrote {META_PATH}")
    print(f"  size : {MODEL_PATH.stat().st_size / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
