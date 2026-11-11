"""Tabular-only baseline on the 80 labelled real patients.

Question this answers
---------------------
Do the Excel features alone predict Easy / Moderate / Difficult, and by how
much do they beat "always guess Moderate"?

Design
------
* Input: data/temp/AI_laryngoscopy_ONEHOT.xlsx, sheet Train_OneHot_Labeled
  (80 patients, 11 features, one row per patient).
* No images. No synthetic rows. No duplicates.
* Repeated stratified 5-fold CV (5 folds x 10 repeats = 50 fits) because one
  split of 80 patients is meaningless.
* Three models: majority-class dummy (the floor), logistic regression,
  random forest.
* Metrics: accuracy, balanced accuracy, macro-F1, per-class recall.
* Missing values (2 Mallampati rows) are median-imputed INSIDE each fold, so
  the test fold never influences the imputer.

Output
------
    data/temp/baseline_results.json   (numbers, reusable)
    console table

Usage
-----
    py -3.12 scripts/train_tabular_baseline.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    recall_score,
)
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_laryngoscopy_datasets as base  # noqa: E402

ONEHOT = base.TEMP / "AI_laryngoscopy_ONEHOT.xlsx"
SHEET = "Train_OneHot_Labeled"
OUT_JSON = base.TEMP / "baseline_results.json"

CLASS_NAMES = ["Easy", "Moderate", "Difficult"]
ID_COLUMNS = {"Patient_ID", "Patient_No", "Image_ID"}
TARGET_COLUMNS = {"Target", "Target_Name"}


def load_data():
    grid = base.read_sheet(ONEHOT, SHEET)
    header = []
    col = 1
    while grid.get((1, col), ""):
        header.append(grid[(1, col)])
        col += 1

    rows = []
    row = 2
    while grid.get((row, 1), ""):
        rows.append([grid.get((row, i + 1), "") for i in range(len(header))])
        row += 1

    feature_names = [h for h in header if h not in ID_COLUMNS | TARGET_COLUMNS]
    feature_idx = [header.index(h) for h in feature_names]
    target_idx = header.index("Target")

    X = np.full((len(rows), len(feature_names)), np.nan, dtype=float)
    for r, values in enumerate(rows):
        for c, idx in enumerate(feature_idx):
            raw = values[idx]
            if raw != "":
                X[r, c] = float(raw)
    y = np.array([int(values[target_idx]) for values in rows], dtype=int)
    return X, y, feature_names


def build_models(random_state: int = 42) -> dict:
    return {
        "dummy_majority": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": Pipeline(
            [
                ("impute", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        random_state=random_state,
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("impute", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=400,
                        min_samples_leaf=2,
                        class_weight="balanced_subsample",
                        random_state=random_state,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
    }


def evaluate(model, X, y, cv) -> dict:
    per_fold = {"accuracy": [], "balanced_accuracy": [], "f1_macro": []}
    recalls = np.zeros((3, 0))
    oof_pred = []
    oof_true = []

    for train_idx, test_idx in cv.split(X, y):
        model.fit(X[train_idx], y[train_idx])
        pred = model.predict(X[test_idx])
        per_fold["accuracy"].append(accuracy_score(y[test_idx], pred))
        per_fold["balanced_accuracy"].append(balanced_accuracy_score(y[test_idx], pred))
        per_fold["f1_macro"].append(f1_score(y[test_idx], pred, average="macro", zero_division=0))
        rec = recall_score(y[test_idx], pred, labels=[0, 1, 2], average=None, zero_division=0)
        recalls = np.concatenate([recalls, rec.reshape(3, 1)], axis=1)
        oof_pred.append(pred)
        oof_true.append(y[test_idx])

    cm = confusion_matrix(np.concatenate(oof_true), np.concatenate(oof_pred), labels=[0, 1, 2])
    folds = len(per_fold["accuracy"])
    return {
        "accuracy_mean": float(np.mean(per_fold["accuracy"])),
        "accuracy_std": float(np.std(per_fold["accuracy"])),
        "balanced_accuracy_mean": float(np.mean(per_fold["balanced_accuracy"])),
        "f1_macro_mean": float(np.mean(per_fold["f1_macro"])),
        "f1_macro_std": float(np.std(per_fold["f1_macro"])),
        "recall_mean": {
            name: float(recalls[i].mean()) for i, name in enumerate(CLASS_NAMES)
        },
        "recall_std": {
            name: float(recalls[i].std()) for i, name in enumerate(CLASS_NAMES)
        },
        "confusion_matrix_over_repeats": (cm / (folds / 5)).round(1).tolist(),
        "folds": folds,
    }


def main() -> int:
    if not ONEHOT.exists():
        raise SystemExit(f"Missing {ONEHOT}. Run onehot_laryngoscopy.py first.")

    X, y, feature_names = load_data()
    counts = {name: int((y == i).sum()) for i, name in enumerate(CLASS_NAMES)}
    print(f"Patients: {len(y)}   Features: {len(feature_names)}")
    print(f"Classes : {counts}")
    print(f"Majority-class floor: {max(counts.values()) / len(y):.3f}\n")

    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=42)
    results = {"n_patients": len(y), "features": feature_names, "classes": counts, "models": {}}

    for name, model in build_models().items():
        print(f"--- {name} ---")
        metrics = evaluate(model, X, y, cv)
        results["models"][name] = metrics
        print(
            f"  accuracy      {metrics['accuracy_mean']:.3f} +/- {metrics['accuracy_std']:.3f}"
        )
        print(f"  balanced acc  {metrics['balanced_accuracy_mean']:.3f}")
        print(
            f"  macro F1      {metrics['f1_macro_mean']:.3f} +/- {metrics['f1_macro_std']:.3f}"
        )
        print(
            "  recall        "
            + "  ".join(
                f"{c}={metrics['recall_mean'][c]:.2f}" for c in CLASS_NAMES
            )
        )
        print("  confusion (rows=true Easy/Mod/ Diff, cols=pred):")
        for label, row in zip(CLASS_NAMES, metrics["confusion_matrix_over_repeats"]):
            print(f"    {label:<10} {row}")
        print()

    # feature importance from a forest fit on all 80 patients (insight only)
    forest = RandomForestClassifier(
        n_estimators=800,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )
    forest.fit(SimpleImputer(strategy="median").fit_transform(X), y)
    order = np.argsort(forest.feature_importances_)[::-1]
    print("Random-forest feature importance (all 80 patients):")
    importance = {}
    for i in order:
        importance[feature_names[i]] = round(float(forest.feature_importances_[i]), 4)
        print(f"  {feature_names[i]:<26} {forest.feature_importances_[i]:.3f}")
    results["feature_importance"] = importance

    OUT_JSON.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
