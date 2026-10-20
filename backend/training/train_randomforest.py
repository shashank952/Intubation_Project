"""
Train Random Forest baseline on dataset.xlsx and compare with XGBoost + TabTransformer.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, classification_report, roc_auc_score
import warnings, time
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = ROOT / "data" / "dataset.xlsx"
MODEL_PATH = ROOT / "checkpoints" / "randomforest_best.pkl"

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
    print("Random Forest Baseline — Difficult Airway Prediction")
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

    model = RandomForestClassifier(
        n_estimators=500,
        max_depth=12,
        min_samples_leaf=4,
        class_weight="balanced",
        n_jobs=-1,
        random_state=42,
    )

    print(f"\nTraining Random Forest ({len(X_train)} samples)...")
    start = time.time()
    model.fit(X_train, y_train)
    elapsed = time.time() - start
    print(f"Training time: {elapsed:.1f}s ({elapsed/60:.1f} min)")

    import joblib
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, str(MODEL_PATH))
    print(f"Model saved to {MODEL_PATH}")

    y_preds = model.predict(X_test)
    y_probs = model.predict_proba(X_test)

    print("\n" + "=" * 60)
    print("Random Forest TEST SET RESULTS")
    print("=" * 60)
    print(classification_report(y_test, y_preds, target_names=["Easy", "Moderate", "Difficult"], digits=3))

    cm = confusion_matrix(y_test, y_preds)
    print("Confusion Matrix:")
    print(f"{'':>12} {'Easy':>6} {'Mod':>6} {'Diff':>6}")
    print(f"{'Easy':>12} {cm[0,0]:>6} {cm[0,1]:>6} {cm[0,2]:>6}")
    print(f"{'Moderate':>12} {cm[1,0]:>6} {cm[1,1]:>6} {cm[1,2]:>6}")
    print(f"{'Difficult':>12} {cm[2,0]:>6} {cm[2,1]:>6} {cm[2,2]:>6}")

    acc = (y_preds == y_test).mean()

    try:
        auc = roc_auc_score(y_test, y_probs, multi_class="ovr")
    except Exception:
        auc = 0.0

    print(f"\nAccuracy:  {acc:.4f}")
    print(f"AUC-ROC:   {auc:.4f}")

    print("\nFeature Importance (Top 10):")
    sorted_idx = np.argsort(model.feature_importances_)[::-1][:10]
    for i in sorted_idx:
        print(f"  {X_train.columns[i]}: {model.feature_importances_[i]:.3f}")

    print("\n" + "=" * 60)
    print("COMPARISON TABLE")
    print("=" * 60)
    print(f"  {'Model':<20} {'Accuracy':<12} {'AUC-ROC':<12} {'Train Time':<12}")
    print(f"  {'Random Forest':<20} {acc:<12.4f} {auc:<12.4f} {elapsed:<12.1f}s")
    print(f"  {'XGBoost':<20} {'0.845':<12} {'0.962':<12} {'1.1s':<12}")
    print(f"  {'TabTransformer':<20} {'0.859':<12} {'0.970':<12} {'~180s':<12}")


if __name__ == "__main__":
    main()
