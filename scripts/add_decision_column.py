"""Add a rule-based airway risk Decision column to data/dataset.xlsx.

This produces an explicitly written clinical checklist, not a learned model and
not a recorded outcome. It exists so each row can be judged from its own
measurements in a way a clinician can read, argue with and change.

The rule has two parts: a points total, and a set of major findings. Difficult
needs both a high total and at least one major finding, so a pile of mild
factors alone cannot push a structurally normal airway into Difficult.

Points

    Mallampati      I=0  II=1  III=2  IV=4
    Mouth opening   >=40mm=0  30-39=1  <30=2
    Thyromental     >=6.5cm=0  6.0-6.4=1  <6.0=2
    Neck movement   >=80deg=0  70-79=1  <70=2
    Jaw movement    0=0  1=1  2=2
    Short/thick neck (Neck_Structure=2) = 2
    Down syndrome   present = 2
    Acute anatomy   swelling / neck fracture / prior ICU emergency = 2

    Sternomental <12.5cm = 1
    BMI 30-34.9 = 1, >=35 = 2
    Neck circ. 40-43cm = 1, >43cm = 2
    Reduced tissue flexibility = 1
    Any prior airway record = 1

    Beard = 0.5
    Barrel chest = 0.5
    Age >=65 = 0.5
    Snoring = 0.5, sleep apnoea = 0.5, arthritis = 0.5

Major findings

    Mallampati IV, mouth opening <35mm, thyromental <6.0cm, neck movement
    <70deg, jaw movement grade 2, short/thick neck, Down syndrome, swelling,
    previous neck fracture, or a prior ICU airway emergency.

Decision

    Difficult   points >= 5.5 AND at least one major finding
    Moderate    points >= 4.0 (including high totals with no major finding)
    Easy        otherwise

This split lands near 60 / 31 / 9, close to real difficult-airway prevalence,
instead of the equal thirds the existing Target column uses.

Circularity warning: this label is a function of the same measurements the
model is trained on. Use it to inspect and sanity-check rows, never as an
independent outcome and never to claim clinical accuracy.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "dataset.xlsx"
TARGET = ROOT / "data" / "dataset_with_decision.xlsx"

MODERATE_AT = 4.0
DIFFICULT_AT = 5.5

ARCHETYPE_BASE = {
    "Mallampati_Score": 1, "Mouth_Opening_mm": 47.0, "Thyromental_Distance_TMD_cm": 8.0,
    "Sternomental_Distance_SMD_cm": 18.0, "Neck_Movement_Degrees": 90.0, "BMI": 23.0,
    "Neck_Circumference_cm": 37.0, "Jaw_Movement": 0, "Neck_Structure": 1,
    "Tissue_Flexibility": 0, "Beard": 0, "Previous_Airway_Records": 0,
    "Disease_Down_Syndrome": 0, "Injury_Swelling": 0, "Injury_Previous_Neck_Fracture": 0,
    "Previous_Emergencies_ICU": 0, "Chest_Size": 0, "Age": 40, "Breathing_Snoring": 0,
    "Breathing_Sleep_Apnea": 0, "Disease_Arthritis": 0,
}

ARCHETYPES = [
    ("all normal", {}, ("Easy",)),
    (
        "many mild factors, no major finding",
        {
            "BMI": 31.0, "Neck_Circumference_cm": 42.0, "Sternomental_Distance_SMD_cm": 12.0,
            "Beard": 1, "Age": 70, "Breathing_Snoring": 1, "Breathing_Sleep_Apnea": 1,
            "Previous_Airway_Records": 1, "Disease_Arthritis": 1,
        },
        ("Moderate",),
    ),
    (
        "severe anatomy",
        {
            "Mallampati_Score": 3, "Mouth_Opening_mm": 24.0, "Thyromental_Distance_TMD_cm": 5.2,
            "Neck_Movement_Degrees": 60.0, "Jaw_Movement": 2, "Neck_Structure": 2,
        },
        ("Difficult",),
    ),
]


def risk_points(df: pd.DataFrame) -> pd.Series:
    score = pd.Series(0.0, index=df.index)

    score += df["Mallampati_Score"].map({0: 0, 1: 1, 2: 2, 3: 4}).astype(float)

    mouth = df["Mouth_Opening_mm"]
    score += np.where(mouth < 30, 2, np.where(mouth < 40, 1, 0))

    tmd = df["Thyromental_Distance_TMD_cm"]
    score += np.where(tmd < 6.0, 2, np.where(tmd < 6.5, 1, 0))

    neck_move = df["Neck_Movement_Degrees"]
    score += np.where(neck_move < 70, 2, np.where(neck_move < 80, 1, 0))

    score += df["Jaw_Movement"].astype(float)
    score += (df["Neck_Structure"] == 2).astype(float) * 2
    score += df["Disease_Down_Syndrome"].astype(float) * 2
    score += acute_anatomy(df).astype(float) * 2

    score += np.where(df["Sternomental_Distance_SMD_cm"] < 12.5, 1, 0)
    score += np.where(df["BMI"] >= 35, 2, np.where(df["BMI"] >= 30, 1, 0))

    neck_circ = df["Neck_Circumference_cm"]
    score += np.where(neck_circ > 43, 2, np.where(neck_circ >= 40, 1, 0))

    score += df["Tissue_Flexibility"].astype(float)
    score += (df["Previous_Airway_Records"] > 0).astype(float)

    score += df["Beard"].astype(float) * 0.5
    score += df["Chest_Size"].astype(float) * 0.5
    score += (df["Age"] >= 65).astype(float) * 0.5
    score += df["Breathing_Snoring"].astype(float) * 0.5
    score += df["Breathing_Sleep_Apnea"].astype(float) * 0.5
    score += df["Disease_Arthritis"].astype(float) * 0.5

    return score


def acute_anatomy(df: pd.DataFrame) -> pd.Series:
    return (
        (df["Injury_Swelling"] == 1)
        | (df["Injury_Previous_Neck_Fracture"] == 1)
        | (df["Previous_Emergencies_ICU"] == 1)
    )


def has_major_finding(df: pd.DataFrame) -> pd.Series:
    return (
        (df["Mallampati_Score"] >= 3)
        | (df["Mouth_Opening_mm"] < 35)
        | (df["Thyromental_Distance_TMD_cm"] < 6.0)
        | (df["Neck_Movement_Degrees"] < 70)
        | (df["Jaw_Movement"] == 2)
        | (df["Neck_Structure"] == 2)
        | (df["Disease_Down_Syndrome"] == 1)
        | acute_anatomy(df)
    )


def decide(points: pd.Series, major: pd.Series) -> pd.Series:
    return pd.Series(
        np.where(
            (points >= DIFFICULT_AT) & major,
            "Difficult",
            np.where(points >= MODERATE_AT, "Moderate", "Easy"),
        ),
        index=points.index,
    )


def check_archetypes() -> None:
    """Fail loudly if a weight change ever breaks the obvious clinical ordering."""
    for name, overrides, allowed in ARCHETYPES:
        row = pd.DataFrame([{**ARCHETYPE_BASE, **overrides}])
        got = decide(risk_points(row), has_major_finding(row)).iloc[0]
        if got not in allowed:
            raise SystemExit(f"Archetype check failed: {name} expected one of {allowed}, got {got}")


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Missing dataset: {SOURCE}")

    check_archetypes()

    df = pd.read_excel(SOURCE)
    if "Decision" in df.columns:
        df = df.drop(columns=["Decision"])

    points = risk_points(df)
    major = has_major_finding(df)
    out = df.copy()
    out["Decision"] = decide(points, major)

    if out["Decision"].isna().any():
        raise SystemExit("Decision has empty values")
    if len(out) != len(df):
        raise SystemExit("Row count changed while adding Decision")

    out.to_excel(TARGET, index=False)

    print(f"Wrote {TARGET}")
    print(f"  rows    : {len(out)}")
    print(f"  columns : {len(out.columns)} (Decision added last)")
    print(f"  rows with a major finding: {int(major.sum())} ({major.mean():.1%})")
    print("\nDecision distribution:")
    counts = out["Decision"].value_counts()
    for name in ("Easy", "Moderate", "Difficult"):
        c = int(counts.get(name, 0))
        print(f"  {name:10s} {c:5d}  {c / len(out):6.1%}")

    print("\nScore distribution:")
    print("  " + "  ".join(f"{k:g}:{v}" for k, v in points.value_counts().sort_index().items()))

    if "Target" in out.columns:
        target_name = out["Target"].map({0: "Easy", 1: "Moderate", 2: "Difficult"})
        print(f"\nAgreement with existing Target column: {(target_name == out['Decision']).mean():.1%}")
        print("\nCross-tab (rows = existing Target, columns = new Decision):")
        print(pd.crosstab(target_name, out["Decision"]).to_string())


if __name__ == "__main__":
    main()
