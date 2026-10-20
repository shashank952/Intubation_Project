"""
Generate 1000 synthetic patient records with clinically correlated target labels.
Columns match dataset.xlsx schema exactly (30 columns).
Target (Easy/Moderate/Difficult) is derived from a weighted difficulty score
based on known airway predictors.
"""

import numpy as np
import pandas as pd
from pathlib import Path
import random

random.seed(42)
np.random.seed(42)

N = 2500


def generate_patient_data(n: int) -> pd.DataFrame:
    data = {}

    # --- Demographics ---
    data["Patient_ID"] = [f"P-{i+1:04d}" for i in range(n)]
    data["Gender"] = np.random.choice([0, 1], n, p=[0.5, 0.5])

    # Age: 18-85, skewed toward 40-65 (typical airway surgery population)
    age = np.random.beta(2, 2, n) * 50 + 30
    age = np.clip(np.round(age).astype(int), 18, 85)
    data["Age"] = age

    # --- Previous airway records ---
    data["Previous_Airway_Records"] = np.random.choice(
        [0, 1, 2], n, p=[0.80, 0.05, 0.15]
    )

    # --- Comorbidities (correlated with age and BMI) ---
    def prob_age(age_val, base, slope, max_prob=0.8):
        return min(base + age_val * slope, max_prob)

    arthritis = []
    diabetes = []
    down_syndrome = []
    for a in age:
        arthritis.append(1 if random.random() < prob_age(a, 0.02, 0.004) else 0)
        diabetes.append(1 if random.random() < prob_age(a, 0.03, 0.005) else 0)
        down_syndrome.append(1 if random.random() < 0.005 else 0)
    data["Disease_Arthritis"] = arthritis
    data["Disease_Diabetes"] = diabetes
    data["Disease_Down_Syndrome"] = down_syndrome

    # --- Breathing (snoring + sleep apnea, correlated with BMI) ---
    bmi_values = np.random.normal(28, 7, n)
    bmi_values = np.clip(bmi_values, 15, 55)

    snoring = []
    sleep_apnea = []
    for bmi_val in bmi_values:
        snoring.append(1 if random.random() < min(0.2 + (bmi_val - 15) * 0.015, 0.85) else 0)
        sleep_apnea.append(1 if random.random() < min(0.05 + (bmi_val - 15) * 0.008, 0.6) else 0)
    data["Breathing_Snoring"] = snoring
    data["Breathing_Sleep_Apnea"] = sleep_apnea

    # --- Symptoms ---
    data["Symptom_Voice_Changes"] = np.random.choice([0, 1], n, p=[0.9, 0.1])
    data["Symptom_Difficulty_Swallowing"] = np.random.choice([0, 1], n, p=[0.85, 0.15])
    data["Symptom_Cant_Lie_Flat"] = np.random.choice([0, 1], n, p=[0.88, 0.12])

    # --- Injury ---
    data["Injury_Swelling"] = np.random.choice([0, 1], n, p=[0.92, 0.08])
    data["Injury_Previous_Neck_Fracture"] = np.random.choice([0, 1], n, p=[0.97, 0.03])

    # --- ICU history ---
    data["Previous_Emergencies_ICU"] = np.random.choice([0, 1], n, p=[0.88, 0.12])

    # --- BMI + BMI Category ---
    bmi_rounded = np.round(bmi_values, 1)
    data["BMI"] = bmi_rounded

    bmi_cat = []
    for b in bmi_rounded:
        if b < 25:
            bmi_cat.append(0)  # Normal
        elif b < 30:
            bmi_cat.append(1)  # Overweight
        else:
            bmi_cat.append(2)  # Obese
    data["BMI_Category"] = bmi_cat

    # --- Neck circumference (correlated with BMI) ---
    neck_circ = 30 + (bmi_values - 15) * 0.4 + np.random.normal(0, 2, n)
    neck_circ = np.clip(neck_circ, 28, 55)
    data["Neck_Circumference_cm"] = np.round(neck_circ, 1)

    # --- Beard ---
    beard = []
    for gender in data["Gender"]:
        if gender == 1:  # Male
            beard.append(1 if random.random() < 0.35 else 0)
        else:
            beard.append(0)
    data["Beard"] = beard

    # --- Chest size ---
    chest = []
    for b in bmi_rounded:
        if b < 25:
            chest.append(0)  # Large
        elif b < 30:
            chest.append(0 if random.random() < 0.6 else 1)  # Barrel
        else:
            chest.append(1 if random.random() < 0.6 else 0)  # Barrel if obese
    data["Chest_Size"] = chest

    # --- Neck structure (correlated with BMI) ---
    neck_struct = []
    for b in bmi_rounded:
        if b < 25:
            neck_struct.append(0)  # Short
        elif b < 30:
            neck_struct.append(np.random.choice([0, 1], p=[0.5, 0.5]))
        else:
            neck_struct.append(np.random.choice([1, 2], p=[0.4, 0.6]))  # Heavy/Thick
    data["Neck_Structure"] = neck_struct

    # --- Mouth opening ---
    mouth_op = np.random.normal(40, 8, n)
    mouth_op = np.clip(mouth_op, 15, 65)
    data["Mouth_Opening_mm"] = np.round(mouth_op, 1)

    # --- Mallampati Score ---
    mallampati = []
    for b in bmi_rounded:
        if b < 25:
            probs = [0.4, 0.35, 0.18, 0.07]
        elif b < 30:
            probs = [0.25, 0.35, 0.28, 0.12]
        else:
            probs = [0.10, 0.25, 0.38, 0.27]
        mallampati.append(np.random.choice([0, 1, 2, 3], p=probs))
    data["Mallampati_Score"] = mallampati

    # --- Thyromental Distance (TMD) -- correlated with Mallampati ---
    tmd_values = []
    for mall in mallampati:
        base = 8.0 - mall * 0.6
        noise = np.random.normal(0, 0.8)
        tmd = base + noise
        tmd = max(tmd, 3.5)
        tmd = min(tmd, 11.0)
        tmd_values.append(tmd)
    tmd_rounded = np.round(tmd_values, 1)
    data["Thyromental_Distance_TMD_cm"] = tmd_rounded

    tmd_cat = []
    for t in tmd_rounded:
        if t >= 6.5:
            tmd_cat.append(0)  # Easy
        elif t >= 6.0:
            tmd_cat.append(1)  # Medium
        else:
            tmd_cat.append(2)  # Difficult
    data["TMD_Category"] = tmd_cat

    # --- Sternomental Distance (SMD) ---
    smd = np.random.normal(14, 2.5, n)
    smd = np.clip(smd, 8, 20)
    data["Sternomental_Distance_SMD_cm"] = np.round(smd, 1)

    # --- Jaw Movement ---
    jaw = np.random.choice([0, 1, 2], n, p=[0.6, 0.25, 0.15])
    data["Jaw_Movement"] = jaw

    # --- Neck Movement ---
    neck_mov = np.random.normal(85, 10, n)
    neck_mov = np.clip(neck_mov, 40, 110)

    neck_mov_cat = []
    for nm in neck_mov:
        if nm >= 80:
            neck_mov_cat.append(0)  # Normal
        elif nm >= 70:
            neck_mov_cat.append(1)  # Borderline
        else:
            neck_mov_cat.append(2)  # Risky
    data["Neck_Movement_Degrees"] = np.round(neck_mov, 1)
    data["Neck_Movement_Category"] = neck_mov_cat

    # --- Tissue Flexibility ---
    tissue = np.random.choice([0, 1], n, p=[0.65, 0.35])
    data["Tissue_Flexibility"] = tissue

    df = pd.DataFrame(data)

    # --- Assign Target based on weighted clinical difficulty score ---
    df = _assign_target(df)

    return df


def _assign_target(df: pd.DataFrame) -> pd.DataFrame:
    scores = np.zeros(len(df))

    # Mallampati: 0-3 → weight 3.0
    scores += df["Mallampati_Score"] * 3.0

    # TMD Category: 0/1/2 → weight 2.5
    scores += df["TMD_Category"] * 2.5

    # Neck Circumference:
    nc = df["Neck_Circumference_cm"].values
    nc_scores = np.where(nc < 40, 0, np.where(nc <= 43, 1, 2))
    scores += nc_scores * 2.0

    # Neck Movement Category: 0/1/2 → weight 1.5
    scores += df["Neck_Movement_Category"] * 1.5

    # BMI Category: 0/1/2 → weight 1.0
    scores += df["BMI_Category"] * 1.0

    # Age (older = slightly harder)
    age_scores = (df["Age"] - 18) / (85 - 18)
    scores += age_scores * 1.0

    # Previous difficult airway → big boost
    scores += (df["Previous_Airway_Records"] == 1) * 3.0

    # Comorbidities
    scores += df["Disease_Arthritis"] * 0.5
    scores += df["Disease_Diabetes"] * 0.5
    scores += df["Disease_Down_Syndrome"] * 1.0

    # Snoring / Sleep apnea
    scores += df["Breathing_Snoring"] * 0.3
    scores += df["Breathing_Sleep_Apnea"] * 0.5

    # Sleep apnea + obesity interaction
    scores += (df["BMI_Category"] >= 1) & (df["Breathing_Sleep_Apnea"] == 1) * 1.0

    # Jaw movement limitation
    scores += df["Jaw_Movement"] * 0.5

    # Tissue flexibility
    scores += df["Tissue_Flexibility"] * 0.5

    # Add small random noise
    scores += np.random.normal(0, 1.0, len(df))

    # Map scores to classes using quantile-based balancing
    # Equal thirds: ~33% each Easy / Moderate / Difficult
    targets = np.zeros(len(df), dtype=int)
    q33 = np.percentile(scores, 33.33)
    q66 = np.percentile(scores, 66.67)
    targets[scores >= q33] = 1  # Moderate (middle third)
    targets[scores >= q66] = 2  # Difficult (top third)
    # Rest = 0 → Easy (bottom third)

    df["Target"] = targets
    return df


if __name__ == "__main__":
    print(f"Generating {N} synthetic patient records...")
    df = generate_patient_data(N)
    out_path = Path(__file__).parent.parent / "data" / "dataset.xlsx"
    df.to_excel(out_path, index=False)
    print(f"Saved to {out_path}")
    print(f"\nShape: {df.shape}")
    print(f"\nTarget distribution:")
    print(df["Target"].value_counts().sort_index().to_dict())
    print("\nColumn types:")
    print(df.dtypes)
    print(f"\nFirst 3 rows:")
    print(df.head(3).to_string())
