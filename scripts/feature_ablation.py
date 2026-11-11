"""Do Teeth and Beard actually help? Ablation on the real 80 patients.

Method
------
Same patients, same folds (5-fold x 10 repeats). Train once with the feature,
once without, and compare. If the score does not drop when the feature is
removed, the feature is not contributing.

    Teeth_Abnormal : available for all 80 patients (64 intact / 16 abnormal)
    Beard_Yes      : available for only patients 1-45 (patients 46-80 were
                     never asked), so it is evaluated on that 45-row subset
                     and on the full 80 with an explicit Unknown indicator.

Usage
-----
    py -3.12 scripts/feature_ablation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_laryngoscopy_datasets as base  # noqa: E402
import train_tabular_baseline as tab  # noqa: E402

CLASS_NAMES = ["Easy", "Moderate", "Difficult"]


def read_sheet(name: str):
    grid = base.read_sheet(tab.ONEHOT, name)
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
    return header, rows


def to_matrix(rows, features):
    return np.array(
        [[float(r[f]) if r.get(f, "") != "" else np.nan for f in features] for r in rows],
        dtype=float,
    )


def models():
    return {
        "logreg": Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("model", LogisticRegression(max_iter=3000, class_weight="balanced")),
        ]),
        "forest": Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("model", RandomForestClassifier(
                n_estimators=400, min_samples_leaf=2,
                class_weight="balanced_subsample", random_state=42, n_jobs=-1)),
        ]),
    }


def evaluate(X, y):
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=42)
    out = {}
    for name, model in models().items():
        acc, bacc, f1, rec = [], [], [], []
        for tr, te in cv.split(X, y):
            model.fit(X[tr], y[tr])
            pred = model.predict(X[te])
            acc.append(accuracy_score(y[te], pred))
            bacc.append(balanced_accuracy_score(y[te], pred))
            f1.append(f1_score(y[te], pred, average="macro", zero_division=0))
            rec.append(recall_score(y[te], pred, labels=[0, 1, 2], average=None, zero_division=0))
        rec = np.array(rec)
        out[name] = {
            "acc": float(np.mean(acc)),
            "acc_std": float(np.std(acc)),
            "bal": float(np.mean(bacc)),
            "f1": float(np.mean(f1)),
            "diff_recall": float(rec[:, 2].mean()),
        }
    return out


def show(title, base_m, feat_m):
    print(f"\n{title}")
    print(f"  {'model':<8} {'without':>18} {'with':>18} {'delta acc':>10} {'delta Diff recall':>18}")
    for name in base_m:
        b, f = base_m[name], feat_m[name]
        print(
            f"  {name:<8} "
            f"{b['acc']:.3f}+/-{b['acc_std']:.3f}   "
            f"{f['acc']:.3f}+/-{f['acc_std']:.3f}   "
            f"{f['acc'] - b['acc']:+.3f}     "
            f"{f['diff_recall'] - b['diff_recall']:+.2f}"
        )


def crosstab(rows, feature, label_key="Target_Name"):
    table: dict[str, dict[str, int]] = {}
    for row in rows:
        value = row.get(feature, "")
        label = row.get(label_key, "")
        if value == "" or label == "":
            continue
        table.setdefault(value, {}).setdefault(label, 0)
        table[value][label] += 1
    return table


def main() -> int:
    print("=" * 78)
    print("TEETH  (all 80 patients)")
    print("=" * 78)
    _, rows = read_sheet("Train_OneHot_Labeled")
    y = np.array([int(r["Target"]) for r in rows])
    features = [h for h in rows[0] if h not in tab.ID_COLUMNS | tab.TARGET_COLUMNS]

    no_teeth = [f for f in features if f != "Teeth_Abnormal"]
    X_without = to_matrix(rows, no_teeth)
    X_with = to_matrix(rows, features)

    print("  Teeth cross-tab:")
    for value, counts in crosstab(rows, "Teeth_Abnormal").items():
        print(f"    Teeth_Abnormal={value}: {counts}")

    show("  Ablation result:", evaluate(X_without, y), evaluate(X_with, y))

    print("\n" + "=" * 78)
    print("BEARD  (only patients 1-45 have a value)")
    print("=" * 78)
    _, full = read_sheet("Train_OneHot_Full")
    labelled = [r for r in full if r["Label_Available"] == "1"]
    with_beard = [r for r in labelled if r["Beard_Unknown"] == "0"]
    print(f"  rows with a recorded beard value: {len(with_beard)}")
    print(f"  Beard cross-tab (recorded rows):")
    for value, counts in crosstab(with_beard, "Beard_Yes").items():
        print(f"    Beard_Yes={value}: {counts}")

    y45 = np.array([int(r["Target"]) for r in with_beard])
    common = [f for f in tab.__dict__.get("COMMON_COLUMNS", [])]  # populated below
    if not common:
        common = [
            "Age", "Gender_Male", "Neck_Circumference_cm", "Chest_Size_cm",
            "Mouth_Opening_Fingers", "Mallampati_Score", "Mallampati_Unknown",
            "TMD_cm", "SMD_cm", "Jaw_Movement_Inadequate", "Teeth_Abnormal",
        ]
    X45_without = to_matrix(with_beard, common)
    X45_with = to_matrix(with_beard, common + ["Beard_Yes"])
    show(f"  Ablation on {len(with_beard)} patients:", evaluate(X45_without, y45), evaluate(X45_with, y45))

    # full 80 with the Unknown indicator
    X80_without = to_matrix(labelled, common)
    X80_with = to_matrix(labelled, common + ["Beard_Yes", "Beard_Unknown"])
    print("\n  Same, but on all 80 including Beard_Unknown (35 rows unknown):")
    show("  Ablation result:", evaluate(X80_without, y), evaluate(X80_with, y))

    print("\nNOTE: on the 45-row subset the fold metrics are very noisy "
          "(8 Difficult cases split across 5 folds). Treat the delta as a direction, not a fact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
