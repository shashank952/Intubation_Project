"""
Merge AI laryngoscopy (part 1) + AI laryngoscopy2 (part 2) into a single seed set,
augment to 2500 rows, integer-encode, and write the training dataset in the exact
dataset.xlsx schema (31 columns: Patient_ID + 29 features + Target).

Data sources (DATASET/):
  - AI laryngoscopy.xlsx   -> part 1, row-oriented, 45 patients, full 29 features
  - AI laryngoscopy2.xlsx  -> part 2, column-oriented, 80 patients, subset of
                              features (missing BMI + attribute flags)

Encoding: categoricals are INTEGER-encoded (0..k-1) to match the reference
dataset.xlsx and the TabTransformer's learned-embedding input (embedding over
integer indices — this is what the model actually consumes, not one-hot).

Part 2 is missing BMI and the "attributes" block (previous airway, disease,
symptoms, injury, ICU, beard, neck structure, tissue flexibility). Handling:
  - BMI: imputed via a linear fit neck_circumference -> BMI calibrated on part 1.
  - categoricals: the augmentation resamples categoricals from the EMPIRICAL
    distribution of the complete records (part 1) with a floor, so missing
    categoricals in part 2 do not bias the distribution toward zero.
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
DATASET = ROOT / "DATASET"
P1 = DATASET / "AI laryngoscopy.xlsx"
P2 = DATASET / "AI laryngoscopy2.xlsx"
N = 2500

# 29 features in the exact order of dataset.xlsx (Patient_ID + these + Target)
FEATURE_COLS = [
    "Gender", "Age", "Previous_Airway_Records",
    "Disease_Arthritis", "Disease_Diabetes", "Disease_Down_Syndrome",
    "Breathing_Snoring", "Breathing_Sleep_Apnea",
    "Symptom_Voice_Changes", "Symptom_Difficulty_Swallowing", "Symptom_Cant_Lie_Flat",
    "Injury_Swelling", "Injury_Previous_Neck_Fracture",
    "Previous_Emergencies_ICU",
    "BMI", "BMI_Category", "Neck_Circumference_cm", "Beard", "Chest_Size",
    "Neck_Structure", "Mouth_Opening_mm", "Mallampati_Score",
    "Thyromental_Distance_TMD_cm", "TMD_Category", "Sternomental_Distance_SMD_cm",
    "Jaw_Movement", "Neck_Movement_Degrees", "Neck_Movement_Category",
    "Tissue_Flexibility",
]

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


# ---- value parsers (mirror scripts/generate_dataset45.py, the established
#      precedent for converting raw clinical text -> standard schema) ---------

def _yesno(val) -> int:
    s = str(val).strip().upper()
    return 1 if s in ("YES", "Y") else 0


def _gender(val) -> int:
    return 1 if str(val).strip().upper() == "MALE" else 0


def _prev_airway(val) -> int:
    s = str(val).strip().upper()
    if s in ("NOT KNOWN", "NONE", "NO", ""):
        return 0
    return 1  # any known history (e.g. "10 YEARS AGO")


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


def _cell(vals, i, default):
    v = vals[i] if i < len(vals) else None
    return default if v is None or str(v).strip() == "" else v


# ---- parsing -----------------------------------------------------------------

def parse_part1() -> pd.DataFrame:
    """45 patients, row-oriented. Explicit row indices (verified against the file)."""
    wb = openpyxl.load_workbook(P1)
    ws = wb["Sheet1"]

    def vals(r):
        return [ws.cell(row=r, column=c).value for c in range(4, 49)]  # cols 4..48

    gender = vals(2)
    age = vals(3)
    prev_airway = vals(4)
    disease = vals(5)
    comorbidities = vals(6)
    snoring = vals(8)
    apnea = vals(9)
    voice = vals(11)
    swallow = vals(12)
    lie_flat = vals(13)
    swelling = vals(15)
    fracture = vals(16)
    emergencies = vals(17)
    bmi = vals(19)
    neck_circ = vals(20)
    beard = vals(21)
    chest = vals(22)
    neck_struct = vals(23)
    mouth = vals(24)
    mallampati = vals(25)
    tmd = vals(26)
    smd = vals(27)
    jaw = vals(28)
    neck_mov = vals(29)
    tissue = vals(30)
    wb.close()

    records = []
    for i in range(45):
        bmi_v = float(_cell(bmi, i, 28.0))
        tmd_v = float(_cell(tmd, i, 6.5))
        nm_v = float(_neck_movement_deg(_cell(neck_mov, i, 85.0)))
        # disease flags derived from DISEASE + COMORBIDITIES combined text
        dis_text = f"{_cell(disease, i, '')} {_cell(comorbidities, i, '')}"
        arth, diab, down = _disease_flags(dis_text)
        records.append({
            "Gender": _gender(_cell(gender, i, "FEMALE")),
            "Age": int(float(_cell(age, i, 45))),
            "Previous_Airway_Records": _prev_airway(_cell(prev_airway, i, "NOT KNOWN")),
            "Disease_Arthritis": arth,
            "Disease_Diabetes": diab,
            "Disease_Down_Syndrome": down,
            "Breathing_Snoring": _yesno(_cell(snoring, i, "NO")),
            "Breathing_Sleep_Apnea": _yesno(_cell(apnea, i, "NO")),
            "Symptom_Voice_Changes": _yesno(_cell(voice, i, "NO")),
            "Symptom_Difficulty_Swallowing": _yesno(_cell(swallow, i, "NO")),
            "Symptom_Cant_Lie_Flat": _yesno(_cell(lie_flat, i, "NO")),
            "Injury_Swelling": _yesno(_cell(swelling, i, "NO")),
            "Injury_Previous_Neck_Fracture": _yesno(_cell(fracture, i, "NO")),
            "Previous_Emergencies_ICU": _yesno(_cell(emergencies, i, "NO")),
            "BMI": round(bmi_v, 1),
            "BMI_Category": bmi_category(bmi_v),
            "Neck_Circumference_cm": round(float(_cell(neck_circ, i, 38.0)), 1),
            "Beard": _yesno(_cell(beard, i, "NO")),
            "Chest_Size": _chest_size(_cell(chest, i, 90)),
            "Neck_Structure": _neck_structure(_cell(neck_struct, i, "NORMAL")),
            "Mouth_Opening_mm": round(_mouth_opening(_cell(mouth, i, 40.0)), 1),
            "Mallampati_Score": _mallampati(_cell(mallampati, i, 2)),
            "Thyromental_Distance_TMD_cm": round(tmd_v, 1),
            "TMD_Category": tmd_category(tmd_v),
            "Sternomental_Distance_SMD_cm": round(min(20.0, float(_cell(smd, i, 14.0))), 1),
            "Jaw_Movement": _jaw_movement(_cell(jaw, i, "ADEQUATE")),
            "Neck_Movement_Degrees": round(nm_v, 1),
            "Neck_Movement_Category": neck_movement_category(nm_v),
            "Tissue_Flexibility": _tissue_flexibility(_cell(tissue, i, "EASY")),
        })
    return pd.DataFrame(records)


def parse_part2(bmi_predictor=None) -> pd.DataFrame:
    """80 patients, column-oriented (features in rows, patients in cols 4..83).

    Only records a subset of features; BMI and the 'attributes' block are absent.
    BMI is filled by `bmi_predictor` (fit on part 1); missing categoricals are
    left at 0 (they are resampled from the part-1 empirical distribution during
    augmentation, so their seed value is irrelevant).
    """
    wb = openpyxl.load_workbook(P2)
    ws = wb["Sheet1"]

    def vals(r):
        return [ws.cell(row=r, column=c).value for c in range(4, 84)]  # cols 4..83

    gender = vals(2)
    age = vals(3)
    neck_circ = vals(4)
    chest = vals(5)
    mouth = vals(6)
    mallampati = vals(7)
    tmd = vals(8)
    smd = vals(9)
    jaw = vals(10)
    neck_mov = vals(11)
    wb.close()

    records = []
    for i in range(80):
        nc_v = float(_cell(neck_circ, i, 38.0))
        tmd_v = float(_cell(tmd, i, 6.5))
        nm_v = float(_neck_movement_deg(_cell(neck_mov, i, 85.0)))
        bmi_v = float(bmi_predictor(nc_v)) if bmi_predictor else 28.0
        records.append({
            "Gender": _gender(_cell(gender, i, "FEMALE")),
            "Age": int(float(_cell(age, i, 45))),
            "Previous_Airway_Records": 0,  # not recorded in part 2
            "Disease_Arthritis": 0,
            "Disease_Diabetes": 0,
            "Disease_Down_Syndrome": 0,
            "Breathing_Snoring": 0,
            "Breathing_Sleep_Apnea": 0,
            "Symptom_Voice_Changes": 0,
            "Symptom_Difficulty_Swallowing": 0,
            "Symptom_Cant_Lie_Flat": 0,
            "Injury_Swelling": 0,
            "Injury_Previous_Neck_Fracture": 0,
            "Previous_Emergencies_ICU": 0,
            "BMI": round(bmi_v, 1),
            "BMI_Category": bmi_category(bmi_v),
            "Neck_Circumference_cm": round(nc_v, 1),
            "Beard": 0,
            "Chest_Size": _chest_size(_cell(chest, i, 90)),
            "Neck_Structure": 1,
            "Mouth_Opening_mm": round(_mouth_opening(_cell(mouth, i, 40.0)), 1),
            "Mallampati_Score": _mallampati(_cell(mallampati, i, 2)),
            "Thyromental_Distance_TMD_cm": round(tmd_v, 1),
            "TMD_Category": tmd_category(tmd_v),
            "Sternomental_Distance_SMD_cm": round(min(20.0, float(_cell(smd, i, 14.0))), 1),
            "Jaw_Movement": _jaw_movement(_cell(jaw, i, "ADEQUATE")),
            "Neck_Movement_Degrees": round(nm_v, 1),
            "Neck_Movement_Category": neck_movement_category(nm_v),
            "Tissue_Flexibility": 0,
        })
    return pd.DataFrame(records)


# ---- augmentation ------------------------------------------------------------

def _fit_bmi_predictor(part1: pd.DataFrame):
    """Nearest-neighbour imputation: for a missing BMI, use the BMI of the
    part-1 patient whose neck circumference is closest. Non-parametric and safe
    (a linear fit on only 45 noisy real points yields a spurious slope)."""
    nc = part1["Neck_Circumference_cm"].values.astype(float)
    bmi = part1["BMI"].values.astype(float)

    def predict(nc_val: float) -> float:
        j = int(np.argmin(np.abs(nc - nc_val)))
        return float(bmi[j])

    return predict


def _category_probs(seeds: pd.DataFrame, col: str, n_classes: int, floor: float = 0.03) -> np.ndarray:
    counts = seeds[col].value_counts()
    probs = np.full(n_classes, floor)
    for v, c in counts.items():
        if 0 <= int(v) < n_classes:
            probs[int(v)] = max(probs[int(v)], c / len(seeds))
    probs = np.clip(probs, floor, 1.0)
    return probs / probs.sum()


def augment(seeds: pd.DataFrame, cat_source: pd.DataFrame, n: int = N) -> pd.DataFrame:
    """Bootstrap-resample a seed, jitter numerics, resample categoricals from the
    complete-record (part 1) empirical distribution, then assign Target."""
    cat_probs = {col: _category_probs(cat_source, col, k) for col, k in CAT_LEVELS.items()}
    out = []
    for i in range(n):
        row = seeds.iloc[random.randrange(len(seeds))].copy()
        for col, probs in cat_probs.items():
            row[col] = int(np.random.choice(len(probs), p=probs))
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
    print(f"Parsing {P1.name} (part 1, 45 patients)...")
    p1 = parse_part1()
    print(f"  -> {len(p1)} records")

    predictor = _fit_bmi_predictor(p1)
    print(f"  BMI imputation: nearest-neighbour by neck circumference (from {len(p1)} part-1 records)")

    print(f"Parsing {P2.name} (part 2, 80 patients)...")
    p2 = parse_part2(bmi_predictor=predictor)
    print(f"  -> {len(p2)} records")

    seeds = pd.concat([p1, p2], ignore_index=True)
    seeds.insert(0, "Patient_ID", [f"P-{i+1:04d}" for i in range(len(seeds))])
    print(f"Merged seeds: {len(seeds)} records")

    # write merged seed file (reference / traceability)
    merged_out = DATASET / "merged_laryngoscopy.xlsx"
    seeds.to_excel(merged_out, index=False)
    print(f"Saved merged seeds -> {merged_out}")

    print(f"Augmenting to {N} rows (bootstrap + jitter + categorical resample)...")
    df = augment(seeds, p1, N)

    # final column order must match dataset.xlsx exactly (Target last)
    col_order = ["Patient_ID"] + FEATURE_COLS + ["Target"]
    df = df[col_order]

    out_path = ROOT / "dataset.xlsx"
    df.to_excel(out_path, index=False)
    print(f"Saved training dataset -> {out_path}")
    print(f"\nShape: {df.shape}")
    print(f"\nTarget distribution:")
    print(df["Target"].value_counts().sort_index().to_dict())
    print(f"\nSeed target distribution (125 seeds, before augmentation):")
    seed_targets = _assign_target(seeds[FEATURE_COLS].copy())["Target"]
    print(seed_targets.value_counts().sort_index().to_dict())


if __name__ == "__main__":
    main()
