"""
Augment Dataset_45.xlsx (45 real patient records) into the standard 2500-row
dataset.xlsx schema, then retrain the same pipeline.

Methodology is identical to scripts/generate_synthetic_data.py:
  - same 31 columns (Patient_ID + 29 features + Target)
  - same integer encoding for categoricals
  - same _assign_target weighted clinical score (reused directly)

The 45 records are converted to the standard schema, then augmented to 2500
rows by bootstrap-resampling a seed record and adding small Gaussian jitter to
numeric features (categoricals keep their seed class). Derived categories and
Target are recomputed after jittering.
"""

import random
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

from generate_synthetic_data import _assign_target

random.seed(42)
np.random.seed(42)

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "Dataset_45.xlsx"
N = 2500

FINGER_TO_MM = {"3": 45.0, "2.5": 37.5, "2": 30.0, "1.5": 22.5, "1": 15.0}

NUMERIC_JITTER = {
    "Age": (3.0, 18, 85),
    "BMI": (1.5, 15, 55),
    "Neck_Circumference_cm": (1.5, 28, 55),
    "Mouth_Opening_mm": (4.0, 15, 65),
    "Thyromental_Distance_TMD_cm": (0.5, 3.5, 11.0),
    "Sternomental_Distance_SMD_cm": (1.0, 8, 20),
    "Neck_Movement_Degrees": (5.0, 40, 110),
}


def _yesno(val) -> int:
    s = str(val).strip().upper()
    return 1 if s in ("YES", "Y") else 0


def _gender(val) -> int:
    return 1 if str(val).strip().upper() == "MALE" else 0


def _prev_airway(val) -> int:
    s = str(val).strip().upper()
    if s in ("NOT KNOWN", "NONE", "NO", ""):
        return 0
    return 1  # any known history


def _disease_flags(val) -> tuple:
    s = str(val).strip().upper()
    return (
        1 if "ARTHRITIS" in s else 0,
        1 if "DIABET" in s else 0,
        1 if "DOWN" in s else 0,
    )


def _chest_size(val) -> int:
    s = str(val).strip()
    try:
        cm = float(s)
        return 1 if cm >= 95 else 0  # 0=Large, 1=Barrel (matches generator)
    except ValueError:
        return 0


def _neck_structure(val) -> int:
    return 1 if str(val).strip().upper() == "NORMAL" else 2


def _mouth_opening(val) -> float:
    s = str(val).strip().upper()
    if "FINGER" in s:
        num = s.split(" ")[0]
        return FINGER_TO_MM.get(num, 40.0)
    try:
        return float(s)
    except ValueError:
        return 40.0


def _mallampati(val) -> int:
    try:
        return max(0, min(3, int(float(str(val).strip())) - 1))
    except (ValueError, TypeError):
        return 0


def _jaw_movement(val) -> int:
    return 0 if str(val).strip().upper() == "ADEQUATE" else 1


def _neck_movement_deg(val) -> float:
    s = str(val).strip().upper()
    if s in ("NORMAL", "", "NOT KNOWN"):
        return 85.0
    try:
        return float(s)
    except ValueError:
        return 85.0


def _tissue_flexibility(val) -> int:
    return 0 if str(val).strip().upper() == "EASY" else 1


def bmi_category(b: float) -> int:
    return 0 if b < 25 else (1 if b < 30 else 2)


def tmd_category(t: float) -> int:
    return 0 if t >= 6.5 else (1 if t >= 6.0 else 2)


def neck_movement_category(nm: float) -> int:
    return 0 if nm >= 80 else (1 if nm >= 70 else 2)


def parse_dataset45() -> pd.DataFrame:
    """Parse the row-oriented Dataset_45.xlsx into 45 records of the standard schema."""
    wb = openpyxl.load_workbook(SOURCE, read_only=True)
    ws = wb["Sheet1"]

    # rows 2..31 define the 45-record parameter block (columns 4..48 = records 1..45)
    rows = []
    for row in ws.iter_rows(min_row=2, max_row=31, min_col=2, max_col=48, values_only=True):
        b, c = row[0], row[1]
        label = str(b).strip() if b is not None else ""
        sub = str(c).strip() if c is not None else ""
        values = list(row[2:])
        rows.append((label.upper(), sub.upper(), values))

    def get_row(*needles) -> list:
        for label, sub, values in rows:
            if any(n in label or n in sub for n in needles):
                return values
        return [None] * 45

    gender = get_row("GENDER")
    age = get_row("AGE")
    prev_airway = get_row("PREVIOUS AIRWAY RECORDS")
    disease = get_row("B) DISEASE")
    snoring = get_row("SNORING")
    apnea = get_row("SLEEP APNEA")
    voice = get_row("VOICE CHANGES")
    swallow = get_row("DIFFICULTY IN SWALLOWING")
    lie_flat = get_row("CAN'T LIE FLAT")
    swelling = get_row("SWELLING")
    fracture = get_row("NECK FRACTURE")
    emergencies = get_row("PREVIOUS EMERGENCIES")
    bmi = get_row("BODY MASS INDEX")
    neck_circ = get_row("NECK CIRCUMFERENCE")
    beard = get_row("BEARD")
    chest = get_row("CHEST SIZE")
    neck_struct = get_row("NECK STRUCTURE")
    mouth = get_row("MOUTH OPENING")
    mallampati = get_row("MALLAMPATI SCORE")
    tmd = get_row("THYROMENTAL DISTANCE")
    smd = get_row("STERNOMENTAL DISTANCE")
    jaw = get_row("JAW MOVEMENT")
    neck_mov = get_row("NECK MOVEMENT")
    tissue = get_row("TISSUE FLEXIBILITY")

    records = []
    for i in range(45):
        def cell(vals, default):
            v = vals[i] if i < len(vals) else None
            return default if v is None or str(v).strip() == "" else v

        bmi_v = float(cell(bmi, 28.0))
        tmd_v = float(cell(tmd, 6.5))
        nm_v = float(_neck_movement_deg(cell(neck_mov, 85.0)))
        arth, diab, down = _disease_flags(cell(disease, "NONE"))

        records.append({
            "Patient_ID": f"P-{i+1:04d}",
            "Gender": _gender(cell(gender, "FEMALE")),
            "Age": int(float(cell(age, 45))),
            "Previous_Airway_Records": _prev_airway(cell(prev_airway, "NOT KNOWN")),
            "Disease_Arthritis": arth,
            "Disease_Diabetes": diab,
            "Disease_Down_Syndrome": down,
            "Breathing_Snoring": _yesno(cell(snoring, "NO")),
            "Breathing_Sleep_Apnea": _yesno(cell(apnea, "NO")),
            "Symptom_Voice_Changes": _yesno(cell(voice, "NO")),
            "Symptom_Difficulty_Swallowing": _yesno(cell(swallow, "NO")),
            "Symptom_Cant_Lie_Flat": _yesno(cell(lie_flat, "NO")),
            "Injury_Swelling": _yesno(cell(swelling, "NO")),
            "Injury_Previous_Neck_Fracture": _yesno(cell(fracture, "NO")),
            "Previous_Emergencies_ICU": _yesno(cell(emergencies, "NO")),
            "BMI": round(bmi_v, 1),
            "BMI_Category": bmi_category(bmi_v),
            "Neck_Circumference_cm": round(float(cell(neck_circ, 38.0)), 1),
            "Beard": _yesno(cell(beard, "NO")),
            "Chest_Size": _chest_size(cell(chest, 90)),
            "Neck_Structure": _neck_structure(cell(neck_struct, "NORMAL")),
            "Mouth_Opening_mm": round(_mouth_opening(cell(mouth, 40.0)), 1),
            "Mallampati_Score": _mallampati(cell(mallampati, 2)),
            "Thyromental_Distance_TMD_cm": round(tmd_v, 1),
            "TMD_Category": tmd_category(tmd_v),
            "Sternomental_Distance_SMD_cm": round(min(20.0, float(cell(smd, 14.0))), 1),
            "Jaw_Movement": _jaw_movement(cell(jaw, "ADEQUATE")),
            "Neck_Movement_Degrees": round(nm_v, 1),
            "Neck_Movement_Category": neck_movement_category(nm_v),
            "Tissue_Flexibility": _tissue_flexibility(cell(tissue, "EASY")),
        })

    return pd.DataFrame(records)


CAT_LEVELS = {
    "Gender": 2,
    "Previous_Airway_Records": 3,
    "Disease_Arthritis": 2,
    "Disease_Diabetes": 2,
    "Disease_Down_Syndrome": 2,
    "Breathing_Snoring": 2,
    "Breathing_Sleep_Apnea": 2,
    "Symptom_Voice_Changes": 2,
    "Symptom_Difficulty_Swallowing": 2,
    "Symptom_Cant_Lie_Flat": 2,
    "Injury_Swelling": 2,
    "Injury_Previous_Neck_Fracture": 2,
    "Previous_Emergencies_ICU": 2,
    "Beard": 2,
    "Chest_Size": 2,
    "Neck_Structure": 3,
    "Mallampati_Score": 4,
    "Jaw_Movement": 3,
    "Tissue_Flexibility": 2,
}


def _category_probs(seeds: pd.DataFrame, col: str, n_classes: int, floor: float = 0.03) -> np.ndarray:
    """Empirical class distribution from the seed records, floored so degenerate
    classes stay represented (keeps model cardinalities aligned with deploy)."""
    counts = seeds[col].value_counts()
    probs = np.full(n_classes, floor)
    for v, c in counts.items():
        if 0 <= int(v) < n_classes:
            probs[int(v)] = max(probs[int(v)], c / len(seeds))
    probs = np.clip(probs, floor, 1.0)
    return probs / probs.sum()


def augment(seeds: pd.DataFrame, n: int = N) -> pd.DataFrame:
    """Sample categoricals from seed-empirical distributions (floored), jitter
    numerics around a bootstrap-resampled seed, then assign Target."""
    cat_probs = {col: _category_probs(seeds, col, k) for col, k in CAT_LEVELS.items()}
    out = []
    for i in range(n):
        row = seeds.iloc[random.randrange(len(seeds))].copy()
        for col, n_classes in CAT_LEVELS.items():
            row[col] = int(np.random.choice(n_classes, p=cat_probs[col]))
        for col, (sigma, lo, hi) in NUMERIC_JITTER.items():
            row[col] = float(np.clip(row[col] + np.random.normal(0, sigma), lo, hi))
        row["BMI_Category"] = bmi_category(row["BMI"])
        row["TMD_Category"] = tmd_category(row["Thyromental_Distance_TMD_cm"])
        row["Neck_Movement_Category"] = neck_movement_category(row["Neck_Movement_Degrees"])
        row["Patient_ID"] = f"P-{i+1:04d}"
        out.append(row)
    df = pd.DataFrame(out)
    for col in NUMERIC_JITTER:
        df[col] = df[col].round(1)
    df[["Age", "BMI_Category", "TMD_Category", "Neck_Movement_Category"]] = df[
        ["Age", "BMI_Category", "TMD_Category", "Neck_Movement_Category"]
    ].astype(int)
    return _assign_target(df)


def main():
    print(f"Parsing {SOURCE.name}...")
    seeds = parse_dataset45()
    print(f"Seeds: {len(seeds)} records")

    print(f"Augmenting to {N} rows (bootstrap + jitter)...")
    df = augment(seeds, N)

    # column order must match the original dataset.xlsx exactly (Target last)
    col_order = list(seeds.columns) + ["Target"]
    df = df[col_order]

    backup = ROOT / "data" / "dataset_original_2500.xlsx"
    if not backup.exists():
        (ROOT / "data" / "dataset.xlsx").rename(backup)
        print(f"Backed up original to {backup.name}")

    out_path = ROOT / "data" / "dataset.xlsx"
    df.to_excel(out_path, index=False)
    print(f"Saved to {out_path}")
    print(f"\nShape: {df.shape}")
    print(f"\nTarget distribution: {df['Target'].value_counts().sort_index().to_dict()}")
    print("\nFirst 3 rows:")
    print(df.head(3).to_string())


if __name__ == "__main__":
    main()