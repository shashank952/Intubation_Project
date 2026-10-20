import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

print("=" * 70)
print("1) IMPORT the full FastAPI app (catches broken routers/schemas/imports)")
print("=" * 70)
try:
    from backend.deploy.api import app
    from backend.deploy import model_loader
    from backend.deploy.routers import predictions
    from backend.deploy.schemas import PredictionInput
    print("  OK - app + routers + schemas import cleanly")
    routes = sorted({r.path for r in app.routes if hasattr(r, "path")})
    print("  routes registered:", len(routes))
    for r in routes:
        print("    ", r)
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit("FAILED IMPORT")

print()
print("=" * 70)
print("2) Load the model via the REAL model_loader path (load_model + predict_tabular)")
print("=" * 70)
try:
    model_loader.load_model()
    print("  OK - load_model() succeeded")
    m = model_loader.get_model()
    print("  model device:", next(m.parameters()).device)
    print("  checkpoint path used:", Path("checkpoints/tabular_best.pt").resolve())
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit("FAILED MODEL LOAD")

print()
print("=" * 70)
print("3) Predict via the REAL predict_tabular() (same call the endpoint makes)")
print("=" * 70)
try:
    from backend.data.preprocessing import CATEGORICAL_COLS, NUMERICAL_COLS
    import numpy as np
    import pandas as pd
    import joblib

    scaler = joblib.load(ROOT / "checkpoints" / "tabular_scaler.pkl")

    def predict(raw_numerical, cat_values):
        df = pd.DataFrame([raw_numerical], columns=NUMERICAL_COLS)
        df[NUMERICAL_COLS] = scaler.transform(df[NUMERICAL_COLS])
        numerical = torch.tensor(df[NUMERICAL_COLS].values, dtype=torch.float32)
        categorical = [torch.tensor([cat_values.get(c, 0)], dtype=torch.long) for c in CATEGORICAL_COLS]
        return model_loader.predict_tabular(numerical, categorical)

    easy_cat = {"Gender": 0, "Mallampati_Score": 0, "BMI_Category": 0, "TMD_Category": 0,
                "Neck_Movement_Category": 0, "Jaw_Movement": 0, "Neck_Structure": 1}
    hard_cat = {"Gender": 1, "Mallampati_Score": 3, "BMI_Category": 2, "TMD_Category": 2,
                "Neck_Movement_Category": 2, "Jaw_Movement": 2, "Neck_Structure": 2,
                "Tissue_Flexibility": 1, "Beard": 1, "Previous_Airway_Records": 1}
    easy_raw = {"Age": 30, "BMI": 22.0, "Neck_Circumference_cm": 33.0, "Mouth_Opening_mm": 45.0,
                "Thyromental_Distance_TMD_cm": 8.5, "Sternomental_Distance_SMD_cm": 20.0,
                "Neck_Movement_Degrees": 90.0}
    hard_raw = {"Age": 70, "BMI": 34.0, "Neck_Circumference_cm": 44.0, "Mouth_Opening_mm": 25.0,
                "Thyromental_Distance_TMD_cm": 5.5, "Sternomental_Distance_SMD_cm": 12.0,
                "Neck_Movement_Degrees": 60.0}
    r1 = predict(easy_raw, easy_cat)
    r2 = predict(hard_raw, hard_cat)
    print("  EASY input   ->", r1)
    print("  DIFFICULT    ->", r2)
    print("  OK - predict_tabular returns probabilities + class")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit("FAILED PREDICT")

print()
print("=" * 70)
print("4) Verify the prediction router's _prepare_input builds correct tensors")
print("=" * 70)
try:
    sample = PredictionInput(
        patient_id="TEST-001", age=45, gender="male", bmi=28.0,
        mallampati_score=2, tmd=7.0, neck_circumference=40.0,
        mouth_opening=40.0, smd=16.0, neck_movement=80.0,
    )
    numerical, categorical = predictions._prepare_input(sample)
    print("  numerical shape:", tuple(numerical.shape))
    print("  categorical tensors:", len(categorical))
    print("  OK - _prepare_input produced", len(categorical), "categorical +", tuple(numerical.shape), "numerical")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit("FAILED PREPARE INPUT")

print()
print("=" * 70)
print("ALL DETERMINISTIC CHECKS PASSED")
print("=" * 70)
