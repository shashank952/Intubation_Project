"""
Train XGBoost baseline on dataset.xlsx and compare with TabTransformer.
"""

import numpy as np
import pandas as pd
import xgboost as xgb
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import confusion_matrix, classification_report, roc_auc_score
import warnings, json, time
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = ROOT / "data" / "dataset.xlsx"
MODEL_PATH = ROOT / "checkpoints" / "xgboost_best.json"
TT_PATH = ROOT / "checkpoints" / "tabular_best.pt"

CATEGORICAL_COLS = [
    "Gender", "Previous_Airway_Records",
    "Disease_Arthritis", "Disease_Diabetes", "Disease_Down_Syndrome",
    "Breathing_Snoring", "Breathing_Sleep_Apnea",
    "Symptom_Voice_Changes", "Symptom_Difficulty_Swallowing", "Symptom_Cant_Lie_Flat",
    "Injury_Swelling", "Injury_Previous_Neck_Fracture",
    "Previous_Emergencies_ICU",
    "BMI_Category", "Beard", "Chest_Size", "Neck_Structure",
    "Mallampati_Score", "TMD_Category",
    "Jaw_Movement", "Neck_Movement_Category", "Tissue_Flexibility",
]
NUMERICAL_COLS = [
    "Age", "BMI", "Neck_Circumference_cm",
    "Mouth_Opening_mm", "Thyromental_Distance_TMD_cm",
    "Sternomental_Distance_SMD_cm", "Neck_Movement_Degrees",
]
TARGET_COL = "Target"
ID_COL = "Patient_ID"


def main():
    print("=" * 60)
    print("XGBoost Baseline — Difficult Airway Prediction")
    print("=" * 60)

    df = pd.read_excel(DATA_PATH)
    print(f"\nDataset: {df.shape[0]} rows, {df.shape[1]} cols")

    X = df.drop(columns=[ID_COL, TARGET_COL])
    y = df[TARGET_COL].values

    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
    )
    print(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

    for col in CATEGORICAL_COLS:
        le = LabelEncoder()
        combined = pd.concat([X_train[col], X_val[col], X_test[col]]).astype(str)
        le.fit(combined)
        X_train[col] = le.transform(X_train[col].astype(str))
        X_val[col] = le.transform(X_val[col].astype(str))
        X_test[col] = le.transform(X_test[col].astype(str))

    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)
    dtest = xgb.DMatrix(X_test, label=y_test)

    params = {
        "objective": "multi:softprob",
        "num_class": 3,
        "max_depth": 6,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "eval_metric": "mlogloss",
        "seed": 42,
        "device": "cuda",
    }

    print(f"\nTraining XGBoost ({len(X_train)} samples)...")
    start = time.time()
    model = xgb.train(
        params,
        dtrain,
        num_boost_round=1000,
        evals=[(dtrain, "train"), (dval, "val")],
        early_stopping_rounds=20,
        verbose_eval=50,
    )
    elapsed = time.time() - start
    print(f"Training time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"Best iteration: {model.best_iteration}")

    model.save_model(str(MODEL_PATH))
    print(f"Model saved to {MODEL_PATH}")

    y_probs = model.predict(dtest)
    y_preds = np.argmax(y_probs, axis=1)

    print("\n" + "=" * 60)
    print("XGBoost TEST SET RESULTS")
    print("=" * 60)
    print(classification_report(y_test, y_preds, target_names=["Easy", "Moderate", "Difficult"], digits=3))

    cm = confusion_matrix(y_test, y_preds)
    print("Confusion Matrix:")
    print(f"{'':>12} {'Easy':>6} {'Mod':>6} {'Diff':>6}")
    print(f"{'Easy':>12} {cm[0,0]:>6} {cm[0,1]:>6} {cm[0,2]:>6}")
    print(f"{'Moderate':>12} {cm[1,0]:>6} {cm[1,1]:>6} {cm[1,2]:>6}")
    print(f"{'Difficult':>12} {cm[2,0]:>6} {cm[2,1]:>6} {cm[2,2]:>6}")

    auc = roc_auc_score(y_test, y_probs, multi_class="ovr")
    acc = (y_preds == y_test).mean()
    print(f"\nAccuracy:  {acc:.4f}")
    print(f"AUC-ROC:   {auc:.4f}")

    print("\nFeature Importance (Top 10):")
    importance = model.get_score(importance_type="gain")
    sorted_imp = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10]
    for name, score in sorted_imp:
        print(f"  {name}: {score:.1f}")

    if TT_PATH.exists():
        print("\n" + "=" * 60)
        print("COMPARISON: XGBoost vs TabTransformer")
        print("=" * 60)
        print(f"  {'Metric':<25} {'XGBoost':<15} {'TabTransformer':<15}")
        print(f"  {'Accuracy':<25} {acc:<15.4f} {'0.859 (from last run)':<15}")
        print(f"  {'AUC-ROC':<25} {auc:<15.4f} {'0.970 (from last run)':<15}")


if __name__ == "__main__":
    main()
