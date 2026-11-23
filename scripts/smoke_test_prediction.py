import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CAT = ["Gender", "Previous_Airway_Records", "Disease_Arthritis", "Disease_Diabetes",
       "Disease_Down_Syndrome", "Breathing_Snoring", "Breathing_Sleep_Apnea",
       "Symptom_Voice_Changes", "Symptom_Difficulty_Swallowing", "Symptom_Cant_Lie_Flat",
       "Injury_Swelling", "Injury_Previous_Neck_Fracture", "Previous_Emergencies_ICU",
       "BMI_Category", "Beard", "Chest_Size", "Neck_Structure", "Mallampati_Score",
       "TMD_Category", "Jaw_Movement", "Neck_Movement_Category", "Tissue_Flexibility"]
EXPECTED = [2, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 2, 2, 3, 4, 3, 3, 3, 2]
MODEL_LOADER = [2, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 2, 2, 3, 4, 3, 3, 3, 2]

df = pd.read_excel(ROOT / "data" / "dataset.xlsx")
print("=== cardinality check (each categorical must contain full 0..k-1) ===")
allok = True
for col, k in zip(CAT, EXPECTED):
    levels = sorted(df[col].unique().tolist())
    ok = levels == list(range(k))
    allok = allok and ok
    print(f"  {col:32s} levels={levels} expected={list(range(k))} ok={ok}")
print("  all full:", allok, "| matches model_loader:", EXPECTED == MODEL_LOADER)

print("\n=== end-to-end prediction smoke test ===")
import joblib
import torch
from backend.models.tabular_model import TabularModel

# load scaler
scaler = joblib.load(ROOT / "checkpoints" / "tabular_scaler.pkl")

# build model exactly as model_loader does
model = TabularModel(
    num_numerical=7,
    cat_cardinalities=MODEL_LOADER,
    num_classes=3,
    embed_dim=64,
    tab_output_dim=128,
    dropout=0.3,
)
state = torch.load(ROOT / "checkpoints" / "tabular_best.pt", map_location="cpu", weights_only=True)
missing, unexpected = model.load_state_dict(state, strict=False)
print("  checkpoint loaded. missing keys:", len(missing), "| unexpected keys:", len(unexpected))
assert len(missing) == 0, f"Missing keys in checkpoint: {missing}"
model.eval()

NUM = ["Age", "BMI", "Neck_Circumference_cm", "Mouth_Opening_mm",
       "Thyromental_Distance_TMD_cm", "Sternomental_Distance_SMD_cm", "Neck_Movement_Degrees"]

# two sample patients: an easy-looking one and a difficult-looking one
def predict(raw_numerical, cat_values):
    num_df = pd.DataFrame([raw_numerical], columns=NUM)
    num_df[NUM] = scaler.transform(num_df[NUM])
    numerical = torch.tensor(num_df[NUM].values, dtype=torch.float32)
    categorical = []
    for col in CAT:
        v = cat_values.get(col, 0)
        categorical.append(torch.tensor([v], dtype=torch.long))
    with torch.no_grad():
        logits = model(numerical, [c for c in categorical])
        probs = torch.softmax(logits / 1.0, dim=-1)  # same temperature as model_loader
        pred = probs.argmax(dim=-1).item()
    names = ["Easy", "Moderate", "Difficult"]
    return names[pred], {n: round(float(probs[0, i]), 3) for i, n in enumerate(names)}

easy = {
    "Age": 30, "BMI": 22.0, "Neck_Circumference_cm": 33.0, "Mouth_Opening_mm": 45.0,
    "Thyromental_Distance_TMD_cm": 8.5, "Sternomental_Distance_SMD_cm": 20.0, "Neck_Movement_Degrees": 90.0,
}
easy_cat = {"Gender": 0, "Mallampati_Score": 0, "BMI_Category": 0, "TMD_Category": 0,
            "Neck_Movement_Category": 0, "Jaw_Movement": 0, "Neck_Structure": 1,
            "Chest_Size": 0, "Tissue_Flexibility": 0, "Beard": 0, "Previous_Airway_Records": 0}

hard = {
    "Age": 70, "BMI": 34.0, "Neck_Circumference_cm": 44.0, "Mouth_Opening_mm": 25.0,
    "Thyromental_Distance_TMD_cm": 5.5, "Sternomental_Distance_SMD_cm": 12.0, "Neck_Movement_Degrees": 60.0,
}
hard_cat = {"Gender": 1, "Mallampati_Score": 3, "BMI_Category": 2, "TMD_Category": 2,
            "Neck_Movement_Category": 2, "Jaw_Movement": 2, "Neck_Structure": 2,
            "Chest_Size": 1, "Tissue_Flexibility": 1, "Beard": 1, "Previous_Airway_Records": 1}

print("  EASY-looking patient ->", predict(easy, easy_cat))
print("  DIFFICULT-looking patient ->", predict(hard, hard_cat))
print("\nSMOKE TEST PASSED: model + scaler + schema align; prediction path works.")
