"""Build a one-hot encoded training workbook from the merged laryngoscopy data.

Input
-----
    data/temp/AI_laryngoscopy_COMBINED.xlsx
        sheet Combined_Long       80 image-correlated patients (with Difficulty)
        sheet Laryngoscopy_1_Only 45 Excel-only patients (no Difficulty)

Output
------
    data/temp/AI_laryngoscopy_ONEHOT.xlsx

Row order in the output (as requested)
--------------------------------------
    1-80    image-correlated patients, with Target
    81-125  Excel-only patients, no Target, numbered sequentially
            (Image_ID blank, Has_Image=0, Label_Available=0)

IMPORTANT
---------
The 45 Excel-only patients are the SAME people as patients 1-45 (verified:
11 shared fields matched 45/45). They are appended for completeness and
numbering continuity, not as a second cohort. Every appended row carries
Duplicate_Of so they can be dropped before training.

Sheets
------
    Train_OneHot         125 rows, 11 features (the file you asked for)
    Train_OneHot_Labeled  80 rows only - drop-in for supervised training
    Train_OneHot_Full    125 rows, 23 features (adds BMI/beard/disease...)
    Feature_Dictionary   every output column
    Encoding_Notes       rules, duplicates, caveats

Usage
-----
    python scripts/onehot_laryngoscopy.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_laryngoscopy_datasets as base  # noqa: E402

OUT = base.TEMP / "AI_laryngoscopy_ONEHOT.xlsx"
IMAGE_SHEET = "Combined_Long"
EXCEL_ONLY_SHEET = "Laryngoscopy_1_Only"

TARGET_MAP = {"Easy": 0, "Moderate": 1, "Difficult": 2}

# ---------------------------------------------------------------- helpers


def blank(value: str) -> bool:
    return value is None or str(value).strip() == ""


def upper(value: str) -> str:
    return str(value or "").strip().upper()


def num(value: str):
    if blank(value):
        return ""
    try:
        parsed = float(value)
    except ValueError:
        return ""
    return int(parsed) if parsed.is_integer() else round(parsed, 2)


def prev_airway_group(value: str) -> str:
    text = upper(value)
    if not text or text == "NOT KNOWN":
        return "Unknown"
    if text == "NONE":
        return "None"
    return "Prior"


def disease_group(value: str) -> str:
    text = upper(value)
    if not text:
        return "Unknown"
    if text == "NONE":
        return "None"
    return "Yes"


def comorbidity_flags(value: str) -> tuple[int, int, int, int]:
    """(diabetes, hypertension, other, unknown)"""
    text = upper(value)
    if not text:
        return 0, 0, 0, 1
    if text == "NONE":
        return 0, 0, 0, 0
    diabetes = 1 if "DIABETES" in text else 0
    hypertension = 1 if ("HYPERTENSION" in text or "HYPERTENSIVE" in text) else 0
    simple = {"DIABETES", "HYPERTENSION", "HYPERTENSIVE"}
    other = 1 if text not in simple else 0
    return diabetes, hypertension, other, 0


def encode(record: dict) -> dict:
    features: dict = {}

    # --- available for all 125 rows
    features["Age"] = num(record.get("Age", ""))
    features["Gender_Male"] = 1 if upper(record.get("Gender")) == "MALE" else 0
    features["Neck_Circumference_cm"] = num(record.get("Neck_Circumference_cm", ""))
    features["Chest_Size_cm"] = num(record.get("Chest_Size_cm", ""))
    features["Mouth_Opening_Fingers"] = num(record.get("Mouth_Opening_Fingers", ""))
    mallampati = num(record.get("Mallampati_Score", ""))
    features["Mallampati_Score"] = mallampati
    features["Mallampati_Unknown"] = 1 if mallampati == "" else 0
    features["TMD_cm"] = num(record.get("TMD_cm", ""))
    features["SMD_cm"] = num(record.get("SMD_cm", ""))
    features["Jaw_Movement_Inadequate"] = (
        1 if "INADEQUATE" in upper(record.get("Jaw_Movement")) else 0
    )
    features["Teeth_Abnormal"] = 0 if upper(record.get("Teeth")) == "INTACT" else 1

    # --- only recorded for patients 1-45 (file 1)
    bmi = num(record.get("BMI", ""))
    features["BMI"] = bmi
    features["BMI_Missing"] = 1 if bmi == "" else 0

    beard = upper(record.get("Beard"))
    features["Beard_Yes"] = 1 if beard == "YES" else 0
    features["Beard_Unknown"] = 1 if not beard else 0

    airway = prev_airway_group(record.get("Previous_Airway_Records", ""))
    features["Prev_Airway_Prior"] = 1 if airway == "Prior" else 0
    features["Prev_Airway_Unknown"] = 1 if airway == "Unknown" else 0

    disease = disease_group(record.get("Disease", ""))
    features["Disease_Any"] = 1 if disease == "Yes" else 0
    features["Disease_Unknown"] = 1 if disease == "Unknown" else 0

    diabetes, hypertension, other, unknown = comorbidity_flags(
        record.get("Comorbidities", "")
    )
    features["Comorb_Diabetes"] = diabetes
    features["Comorb_Hypertension"] = hypertension
    features["Comorb_Other"] = other
    features["Comorb_Unknown"] = unknown

    return features


COMMON_COLUMNS = [
    "Age",
    "Gender_Male",
    "Neck_Circumference_cm",
    "Chest_Size_cm",
    "Mouth_Opening_Fingers",
    "Mallampati_Score",
    "Mallampati_Unknown",
    "TMD_cm",
    "SMD_cm",
    "Jaw_Movement_Inadequate",
    "Teeth_Abnormal",
]

FULL_EXTRA_COLUMNS = [
    "BMI",
    "BMI_Missing",
    "Beard_Yes",
    "Beard_Unknown",
    "Prev_Airway_Prior",
    "Prev_Airway_Unknown",
    "Disease_Any",
    "Disease_Unknown",
    "Comorb_Diabetes",
    "Comorb_Hypertension",
    "Comorb_Other",
    "Comorb_Unknown",
]

FULL_COLUMNS = COMMON_COLUMNS + FULL_EXTRA_COLUMNS

META_COLUMNS = [
    "Patient_ID",
    "Patient_No",
    "Image_ID",
    "Has_Image",
    "Label_Available",
    "Duplicate_Of",
    "Source_Dataset",
]

CONSTANT_COLUMNS = [
    ("Breathing_Snoring", "NO"),
    ("Breathing_Sleep_Apnea", "NO"),
    ("Symptom_Voice_Changes", "NO"),
    ("Symptom_Difficulty_Swallowing", "NO"),
    ("Symptom_Cant_Lie_Flat", "YES"),
    ("Injury_Swelling", "NO"),
    ("Injury_Previous_Neck_Fracture", "NO"),
    ("Previous_Emergencies_ICU", "NO"),
    ("Neck_Structure", "NORMAL"),
    ("Neck_Movement", "NORMAL"),
    ("Tissue_Flexibility", "EASY"),
]

SPARSE_DROPPED = [("Tongue_Thickness_cm", "recorded for 10 of 80 patients (87% missing)")]

METADATA_DROPPED = [
    ("Photo_Count", "dataset artefact, not a clinical feature"),
    ("Photo_Example", "dataset artefact"),
    ("Difficulty_Raw", "raw text of the target (leaks the label)"),
    ("Notes", "free text"),
]


# ---------------------------------------------------------------- loading


def read_table(sheet_name: str) -> list[dict]:
    grid = base.read_sheet(base.OUT, sheet_name)
    header = []
    col = 1
    while True:
        name = grid.get((1, col), "")
        if not name:
            break
        header.append(name)
        col += 1

    rows = []
    row = 2
    while grid.get((row, 1), ""):
        rows.append({name: grid.get((row, i + 1), "") for i, name in enumerate(header)})
        row += 1
    return rows


def build_cohort() -> list[dict]:
    """125 records: 80 image-correlated first, then 45 Excel-only."""
    image_rows = read_table(IMAGE_SHEET)
    excel_rows = read_table(EXCEL_ONLY_SHEET)

    if len(image_rows) != 80:
        raise SystemExit(f"Expected 80 image rows in {IMAGE_SHEET}, got {len(image_rows)}")
    if len(excel_rows) != 45:
        raise SystemExit(f"Expected 45 Excel-only rows in {EXCEL_ONLY_SHEET}, got {len(excel_rows)}")

    cohort: list[dict] = []

    for record in image_rows:
        label = record.get("Difficulty", "")
        cohort.append(
            {
                "Patient_ID": record["Patient_ID"],
                "Patient_No": int(record["Patient_No"]),
                "Image_ID": record.get("Image_ID", ""),
                "Has_Image": 1,
                "Label_Available": 1 if label else 0,
                "Duplicate_Of": "",
                "Source_Dataset": "AI laryngoscopy 2 (image-correlated, labelled)",
                "record": record,
                "Target": TARGET_MAP.get(label, ""),
                "Target_Name": label,
            }
        )

    for offset, record in enumerate(excel_rows, start=1):
        number = 80 + offset
        record = dict(record)
        record["Mouth_Opening_Fingers"] = base.mouth_fingers(
            record.get("Mouth_Opening_Raw", "")
        )
        cohort.append(
            {
                "Patient_ID": f"P-{number:04d}",
                "Patient_No": number,
                "Image_ID": "",
                "Has_Image": 0,
                "Label_Available": 0,
                "Duplicate_Of": f"P-{offset:04d}",
                "Source_Dataset": "AI laryngoscopy 1 (Excel only, no label, duplicate of patients 1-45)",
                "record": record,
                "Target": "",
                "Target_Name": "",
            }
        )

    return cohort


# ---------------------------------------------------------------- sheets


def training_rows(cohort: list[dict], columns: list[str], full_meta: bool) -> list[tuple[list, int]]:
    if full_meta:
        header = META_COLUMNS + columns + ["Target", "Target_Name"]
    else:
        header = ["Patient_ID", "Patient_No", "Image_ID"] + columns + ["Target", "Target_Name"]

    rows: list[tuple[list, int]] = [(header, 2)]
    for entry in cohort:
        features = encode(entry["record"])
        if full_meta:
            values = [entry[column] for column in META_COLUMNS]
        else:
            values = [entry["Patient_ID"], entry["Patient_No"], entry["Image_ID"]]
        values += [features[column] for column in columns]
        values += [entry["Target"], entry["Target_Name"]]
        rows.append((values, 4))
    return rows


def build_dictionary() -> list[tuple[list, int]]:
    rows: list[tuple[list, int]] = [
        (
            [
                "Output_Column",
                "Source_Column(s)",
                "Encoding",
                "Values",
                "Type",
                "Used_In",
                "Notes",
            ],
            2,
        )
    ]

    def add(out, src, enc, values, kind, used, note):
        rows.append(([out, src, enc, values, kind, used, note], 4))

    add("Patient_ID", "Patient_ID", "identifier", "P-0001 ... P-0125", "text", "all", "Patients 81-125 are re-numbered copies of P-0001..P-0045. Join key only.")
    add("Patient_No", "sequence", "identifier", "1 ... 125", "int", "all", "Stable row order: 1-80 image-correlated, 81-125 Excel-only.")
    add("Image_ID", "Image_ID", "identifier", "1 ... 80 (blank from row 81)", "text", "all", "Photo filename stem (1.jpg, 1(1).jpg). Blank when no image exists.")
    add("Has_Image", "derived", "binary flag", "1=has correlated image, 0=Excel only", "int", "all", "Rows 1-80 = 1, rows 81-125 = 0.")
    add("Label_Available", "Difficulty", "binary flag", "1=Target present, 0=no label", "int", "all", "Rows 81-125 = 0 because those patients have no Difficulty.")
    add("Duplicate_Of", "derived", "reference", "P-0001 ... P-0045 (blank for 1-80)", "text", "all", "Rows 81-125 are the same people as 1-45. Drop before training.")
    add("Source_Dataset", "derived", "text", "file description", "text", "all", "Which source workbook the row came from.")
    add("Target", "Difficulty", "label encoding", "0=Easy, 1=Moderate, 2=Difficult, blank=unlabelled", "int", "all", "Blank for rows 81-125.")
    add("Target_Name", "Difficulty", "label encoding", "Easy / Moderate / Difficult", "text", "all", "Human-readable target. Exclude from training.")

    add("Age", "Age", "numeric", "years", "float", "all", "No missing.")
    add("Gender_Male", "Gender", "binary (k-1)", "1=Male, 0=Female (reference)", "int", "all", "Female is the reference level.")
    add("Neck_Circumference_cm", "Neck_Circumference_cm", "numeric", "cm", "float", "all", "No missing.")
    add("Chest_Size_cm", "Chest_Size_cm", "numeric", "cm", "float", "all", "Recorded as a number in the source form.")
    add("Mouth_Opening_Fingers", "Mouth_Opening_Raw", "ordinal to numeric", "1.5 / 2 / 2.5 / 3 fingers", "float", "all", "Most are exactly 3. Convert to mm before using the existing TabTransformer.")
    add("Mallampati_Score", "Mallampati_Score", "ordinal kept numeric", "1-4 (blank = unknown)", "float", "all", "2 image rows had 'NA' in the source.")
    add("Mallampati_Unknown", "Mallampati_Score", "missing indicator", "1=unknown, 0=known", "int", "all", "Only 2 positive rows.")
    add("TMD_cm", "TMD_cm", "numeric", "cm", "float", "all", "No missing.")
    add("SMD_cm", "SMD_cm", "numeric", "cm", "float", "all", "No missing.")
    add("Jaw_Movement_Inadequate", "Jaw_Movement", "binary (k-1)", "1=Inadequate, 0=Adequate (reference)", "int", "all", "Few positive rows.")
    add("Teeth_Abnormal", "Teeth", "grouped binary", "1=any abnormality, 0=Intact", "int", "all", "Collapsed 13 free-text values into Intact vs Abnormal.")

    add("BMI", "BMI", "numeric", "kg/m2 (blank for patients 46-80)", "float", "full", "Only recorded for patients 1-45.")
    add("BMI_Missing", "BMI", "missing indicator", "1=missing, 0=present", "int", "full", "35 positive rows.")
    add("Beard_Yes", "Beard", "binary (k-1)", "1=Yes, 0=No", "int", "full", "Beard present is an airway-difficulty risk factor.")
    add("Beard_Unknown", "Beard", "missing indicator", "1=unknown, 0=known", "int", "full", "35 positive rows.")
    add("Prev_Airway_Prior", "Previous_Airway_Records", "grouped binary", "1=any prior record, 0=None", "int", "full", "9 free-text values collapsed to None / Prior / Unknown.")
    add("Prev_Airway_Unknown", "Previous_Airway_Records", "grouped binary", "1=unknown, 0=known", "int", "full", "Includes 'NOT KNOWN' and blanks.")
    add("Disease_Any", "Disease", "grouped binary", "1=any disease listed, 0=None", "int", "full", "34 free-text values collapsed: one-hot would give 1-sample columns.")
    add("Disease_Unknown", "Disease", "grouped binary", "1=unknown, 0=known", "int", "full", "35 positive rows.")
    add("Comorb_Diabetes", "Comorbidities", "keyword flag", "1=diabetes mentioned", "int", "full", "Parsed from free text.")
    add("Comorb_Hypertension", "Comorbidities", "keyword flag", "1=hypertension/hypertensive mentioned", "int", "full", "Parsed from free text.")
    add("Comorb_Other", "Comorbidities", "keyword flag", "1=other/complex combination", "int", "full", "e.g. diabetes + multiple myeloma, IHD + hypertension.")
    add("Comorb_Unknown", "Comorbidities", "missing indicator", "1=unknown, 0=known", "int", "full", "35 positive rows.")
    return rows


def build_notes(cohort: list[dict]) -> list[tuple[list, int]]:
    counts: dict[str, int] = {}
    for entry in cohort:
        name = entry["Target_Name"] or "(unlabelled)"
        counts[name] = counts.get(name, 0) + 1

    lines = [
        ("ONE-HOT ENCODING NOTES - READ BEFORE TRAINING", ""),
        ("", ""),
        ("Input", base.OUT.name),
        ("Output", OUT.name),
        ("Total rows", len(cohort)),
        ("Rows 1-80", "image-correlated patients, labelled (image file 1-80)"),
        ("Rows 81-125", "Excel-only patients, unlabelled (AI laryngoscopy 1)"),
        ("Class balance (rows 1-80)", f"Easy={counts.get('Easy', 0)}  Moderate={counts.get('Moderate', 0)}  Difficult={counts.get('Difficult', 0)}"),
        ("", ""),
        ("WHY ROWS 81-125 EXIST", ""),
        ("Numbering you asked for", "1-80 image-correlated first, then 81-125 Excel-only, so the sequence never jumbles."),
        ("Important", "The 45 Excel-only patients are the SAME people as patients 1-45. In the source, 11 shared fields matched 45/45. They are appended for completeness, not as a second cohort."),
        ("Proof column", "Duplicate_Of on rows 81-125 points back to P-0001..P-0045."),
        ("Where 125 comes from", "data/raw/merged_laryngoscopy.xlsx is built as pd.concat([45-part, 80-part]) in scripts/generate_laryngoscopy_dataset.py, so it has 125 rows but only 80 unique people."),
        ("", ""),
        ("WHICH SHEET SHOULD I TRAIN ON?", ""),
        ("Train_OneHot_Labeled", "RECOMMENDED. 80 labelled rows, 11 features, no duplicates. Train here."),
        ("Train_OneHot", "125 rows in your requested order. 45 rows have a blank Target, so most libraries will silently drop them."),
        ("Train_OneHot_Full", "23 features. Adds BMI / beard / disease / comorbidity, but only patients 1-45 have them."),
        ("", ""),
        ("Target encoding", ""),
        ("Easy", "0"),
        ("Moderate", "1"),
        ("Difficult", "2"),
        ("Why this order", "matches backend/deploy/model_loader.py class_names = ['Easy','Moderate','Difficult']"),
        ("Blank Target", "rows 81-125 (no outcome recorded in the source)"),
        ("", ""),
        ("Reference levels (binary columns are k-1)", ""),
        ("Gender_Male", "reference = Female"),
        ("Jaw_Movement_Inadequate", "reference = Adequate"),
        ("Teeth_Abnormal", "reference = Intact"),
        ("Beard_Yes", "reference = No"),
        ("Prev_Airway_Prior", "reference = None"),
        ("Disease_Any", "reference = None"),
        ("Comorb_*", "reference = none recorded"),
        ("", ""),
        ("DROPPED: constant columns (zero information)", ""),
    ]
    for name, only_value in CONSTANT_COLUMNS:
        lines.append((name, f"every filled row = {only_value}"))
    lines += [
        ("", ""),
        ("DROPPED: too sparse", ""),
    ]
    for name, reason in SPARSE_DROPPED:
        lines.append((name, reason))
    lines += [
        ("", ""),
        ("DROPPED: free text replaced by grouped/binary columns", ""),
        ("Disease", "34 distinct values -> Disease_Any + Disease_Unknown"),
        ("Comorbidities", "6 distinct values -> 4 keyword flags"),
        ("Previous_Airway_Records", "9 distinct values -> Prior / Unknown indicators"),
        ("Teeth", "13 distinct values -> Teeth_Abnormal"),
        ("Mouth_Opening_Raw", "text '3 FINGERS' -> numeric Mouth_Opening_Fingers"),
        ("", ""),
        ("DROPPED: metadata / leakage", ""),
    ]
    for name, reason in METADATA_DROPPED:
        lines.append((name, reason))
    lines += [
        ("", ""),
        ("MISSING VALUES", ""),
        ("Policy", "Never imputed. Structural missingness is real: the field was not collected."),
        ("How to detect it", "Mallampati_Unknown, BMI_Missing, Beard_Unknown, Prev_Airway_Unknown, Disease_Unknown, Comorb_Unknown"),
        ("", ""),
        ("HONEST WARNING", ""),
        ("Sample size", "80 labelled patients, 8 of them Difficult. A single 80/20 split is meaningless here."),
        ("Do this instead", "Stratified 5-fold cross-validation, report mean +/- std."),
        ("Do not", "train on rows 81-125: they have no label and they duplicate patients 1-45."),
        ("", ""),
        ("Loading example", ""),
        ("pandas", 'df = pd.read_excel("AI_laryngoscopy_ONEHOT.xlsx", sheet_name="Train_OneHot_Labeled")'),
        ("features", 'X = df.drop(columns=["Patient_ID","Patient_No","Image_ID","Target","Target_Name"])'),
        ("target", 'y = df["Target"]'),
        ("", ""),
        ("Data warning", "Real patient clinical data. data/temp/ is gitignored - keep it that way."),
    ]
    rows: list[tuple[list, int]] = []
    for i, (left, right) in enumerate(lines):
        rows.append(([left, right], 1 if i == 0 else 4))
    return rows


def main() -> int:
    if not base.OUT.exists():
        raise SystemExit(f"Missing input: {base.OUT}\nRun scripts/merge_laryngoscopy_datasets.py first.")

    cohort = build_cohort()

    numbers = [entry["Patient_No"] for entry in cohort]
    if numbers != list(range(1, len(cohort) + 1)):
        raise SystemExit("Patient numbering is not sequential 1..125")

    labelled = [entry for entry in cohort if entry["Target"] != ""]
    unlabelled = [entry for entry in cohort if entry["Target"] == ""]
    if len(labelled) != 80 or len(unlabelled) != 45:
        raise SystemExit(f"Expected 80 labelled / 45 unlabelled, got {len(labelled)} / {len(unlabelled)}")

    if set(COMMON_COLUMNS) & set(FULL_EXTRA_COLUMNS):
        raise SystemExit("COMMON_COLUMNS and FULL_EXTRA_COLUMNS overlap")

    all_columns = META_COLUMNS + FULL_COLUMNS + ["Target", "Target_Name"]
    if len(all_columns) != len(set(all_columns)):
        raise SystemExit("Duplicate output column names")

    sheets = [
        (
            "Train_OneHot",
            base.sheet_xml(
                training_rows(cohort, COMMON_COLUMNS, full_meta=True),
                [(1, 1, 12), (2, 2, 9), (3, 9, 20), (10, 40, 22)],
                freeze="A2",
            ),
        ),
        (
            "Train_OneHot_Labeled",
            base.sheet_xml(
                training_rows(labelled, COMMON_COLUMNS, full_meta=False),
                [(1, 1, 12), (2, 2, 9), (3, 3, 9), (4, 30, 22)],
                freeze="A2",
            ),
        ),
        (
            "Train_OneHot_Full",
            base.sheet_xml(
                training_rows(cohort, FULL_COLUMNS, full_meta=True),
                [(1, 1, 12), (2, 2, 9), (3, 9, 20), (10, 50, 22)],
                freeze="A2",
            ),
        ),
        (
            "Feature_Dictionary",
            base.sheet_xml(
                build_dictionary(),
                [(1, 1, 26), (2, 2, 26), (3, 3, 24), (4, 4, 40), (5, 5, 9), (6, 6, 9), (7, 7, 70)],
                freeze="A2",
            ),
        ),
        ("Encoding_Notes", base.sheet_xml(build_notes(cohort), [(1, 1, 38), (2, 2, 120)])),
    ]
    base.write_workbook(OUT, sheets)

    print(f"Wrote {OUT}")
    print(f"  sheets              : {', '.join(name for name, _ in sheets)}")
    print(f"  Train_OneHot        : {len(cohort)} rows (1-80 labelled, 81-125 unlabelled) x {len(META_COLUMNS) + len(COMMON_COLUMNS) + 2} cols")
    print(f"  Train_OneHot_Labeled: {len(labelled)} rows x {3 + len(COMMON_COLUMNS) + 2} cols ({len(COMMON_COLUMNS)} features)")
    print(f"  Train_OneHot_Full   : {len(cohort)} rows x {len(META_COLUMNS) + len(FULL_COLUMNS) + 2} cols ({len(FULL_COLUMNS)} features)")
    print(f"  target              : Easy={sum(1 for e in cohort if e['Target'] == 0)} "
          f"Moderate={sum(1 for e in cohort if e['Target'] == 1)} "
          f"Difficult={sum(1 for e in cohort if e['Target'] == 2)} "
          f"unlabelled={len(unlabelled)}")
    print(f"  size                : {OUT.stat().st_size / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
