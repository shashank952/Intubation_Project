"""
Refit and save the StandardScaler that train_tabular.py uses on the 7
numerical columns of dataset.xlsx.

This reproduces the exact same train/val/test split as train_tabular.py
(random_state=42, stratify=y, test_size=0.15, val_size=0.15) so the
fitted scaler matches what the model was trained with.
"""
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib

ROOT = Path(__file__).resolve().parent.parent
NUMERICAL_COLS = [
    "Age", "BMI", "Neck_Circumference_cm",
    "Mouth_Opening_mm", "Thyromental_Distance_TMD_cm",
    "Sternomental_Distance_SMD_cm", "Neck_Movement_Degrees",
]
TARGET_COL = "Target"
ID_COL = "Patient_ID"

df = pd.read_excel(ROOT / "dataset.xlsx")
ids = df[ID_COL].to_numpy()  # .to_numpy() (not .values) -> plain ndarray for arrow-backed str
y = df[TARGET_COL].values

train_ids, temp_ids, _, _ = train_test_split(
    ids, y, test_size=0.30, random_state=42, stratify=y
)
train_df = df[df[ID_COL].isin(train_ids)].copy()

scaler = StandardScaler()
scaler.fit(train_df[NUMERICAL_COLS])

out = ROOT / "checkpoints" / "tabular_scaler.pkl"
out.parent.mkdir(parents=True, exist_ok=True)
joblib.dump(scaler, out)

print(f"Fitted scaler on {len(train_df)} training rows")
print(f"Means:    {dict(zip(NUMERICAL_COLS, scaler.mean_.round(3)))}")
print(f"Stds:     {dict(zip(NUMERICAL_COLS, scaler.scale_.round(3)))}")
print(f"Saved to: {out}")
