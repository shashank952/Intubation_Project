"""Merge the two laryngoscopy workbooks in data/temp into one Excel workbook.

Inputs
------
    data/temp/AI laryngoscopy.xlsx   45 patients, wide layout, NO difficulty label
    data/temp/AI laryngoscopy2.xlsx  80 patients, wide layout, WITH difficulty label

Verified fact: the 45 patients in file 1 are exactly patients 1-45 of file 2
(all 11 shared fields match 45/45), so they are NOT a separate cohort. File 1
only adds extra columns (BMI, beard, neck structure, disease/symptom history,
tissue flexibility, tongue thickness) that file 2 lacks.

Output
------
    data/temp/AI_laryngoscopy_COMBINED.xlsx

Sheets
------
    Combined_Wide        Block A = 80 patients (with Difficulty), then
                         Block B = 45 patients from file 1 below it (as requested)
    Combined_Long        One row per unique patient (80). Patients 1-45 are
                         enriched with file 1's extra fields. No duplicates.
    Laryngoscopy_1_Only  File 1 preserved as its own 45-row table (no difficulty)
    Notes                Merge rules, normalisation, caveats

Stdlib only (zipfile + XML) because the project venv is broken and pandas is
not installed for the system interpreter.

Usage
-----
    python scripts/merge_laryngoscopy_datasets.py
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
TEMP = ROOT / "data" / "temp"
FILE1 = TEMP / "AI laryngoscopy.xlsx"
FILE2 = TEMP / "AI laryngoscopy2.xlsx"
OUT = TEMP / "AI_laryngoscopy_COMBINED.xlsx"
IMAGE_DIR = ROOT / "data" / "raw" / "redacted_images"

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

# ---------------------------------------------------------------- reading xlsx


def _col_num(ref: str) -> int:
    n = 0
    for ch in "".join(c for c in ref if c.isalpha()):
        n = n * 26 + (ord(ch) - 64)
    return n


def _col_letter(n: int) -> str:
    out = ""
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def read_sheet(path: Path, name: str | None = None) -> dict[tuple[int, int], str]:
    """Return {(row, col): text} for a worksheet (by name, or the first one)."""
    with zipfile.ZipFile(path) as z:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        relmap = {r.get("Id"): r.get("Target") for r in rels}
        shared: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            ss = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in ss.findall(NS + "si"):
                shared.append("".join(t.text or "" for t in si.iter(NS + "t")))
        sheets = wb.find(NS + "sheets")
        if name is None:
            rid = [s.get(REL + "id") for s in sheets][0]
        else:
            matches = [s.get(REL + "id") for s in sheets if s.get("name") == name]
            if not matches:
                raise SystemExit(f"Sheet {name!r} not found in {path}")
            rid = matches[0]
        sheet = ET.fromstring(z.read("xl/" + relmap[rid].lstrip("/")))

    grid: dict[tuple[int, int], str] = {}
    for row in sheet.findall(".//" + NS + "sheetData/" + NS + "row"):
        ri = int(row.get("r"))
        for cell in row.findall(NS + "c"):
            v = cell.find(NS + "v")
            t = cell.get("t")
            if v is None:
                isel = cell.find(NS + "is")
                text = (
                    "".join(x.text or "" for x in isel.iter(NS + "t"))
                    if isel is not None
                    else ""
                )
            elif t == "s":
                text = shared[int(v.text)]
            else:
                text = v.text or ""
            grid[(ri, _col_num(cell.get("r")))] = text.strip()
    return grid


def read_first_sheet(path: Path) -> dict[tuple[int, int], str]:
    """Backwards-compatible alias for the first worksheet."""
    return read_sheet(path)


# ------------------------------------------------------------ normalisation


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def num(value: str):
    """Parse a number, tolerating float noise like 18.600000000000001."""
    text = clean_text(value)
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    return round(parsed, 2)


MOUTH_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*FINGER", re.IGNORECASE)


def mouth_fingers(value: str):
    match = MOUTH_RE.match(clean_text(value))
    return float(match.group(1)) if match else None


DIFFICULTY_MAP = {"EASY": "Easy", "MEDIUM": "Moderate", "MEIDUM": "Moderate", "HARD": "Difficult"}


def normalise_difficulty(value: str) -> tuple[str, str]:
    raw = clean_text(value)
    return DIFFICULTY_MAP.get(raw.upper(), ""), raw


def photo_stats(patient_no: int) -> tuple[int, str]:
    """Count photos whose filename stem is exactly 'N' or 'N(k)'."""
    if not IMAGE_DIR.is_dir():
        return 0, ""
    pattern = re.compile(rf"^{patient_no}(?:\(\d+\))?$")
    names = sorted(
        p.name
        for p in IMAGE_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
        and pattern.match(p.stem)
    )
    return len(names), (names[0] if names else "")


# ---------------------------------------------------------------- extraction


def extract_file2(grid) -> list[dict]:
    rows = {
        "Gender": (2, "text"),
        "Age": (3, "num"),
        "Neck_Circumference_cm": (4, "num"),
        "Chest_Size_cm": (5, "num"),
        "Mouth_Opening_Raw": (6, "text"),
        "Mallampati_Score": (7, "num"),
        "TMD_cm": (8, "num"),
        "SMD_cm": (9, "num"),
        "Jaw_Movement": (10, "text"),
        "Neck_Movement": (11, "text"),
        "Teeth": (12, "text"),
        "Difficulty_Raw": (13, "text"),
    }
    patients = []
    for p in range(1, 81):
        col = 3 + p
        rec: dict = {"Patient_No": p}
        for field, (row, kind) in rows.items():
            cell = grid.get((row, col), "")
            if kind == "num":
                val = num(cell)
                rec[field] = "" if val is None else val
            else:
                rec[field] = clean_text(cell)
        rec["Difficulty"], rec["Difficulty_Raw"] = normalise_difficulty(
            rec.pop("Difficulty_Raw")
        )
        rec["Mouth_Opening_Fingers"] = mouth_fingers(rec["Mouth_Opening_Raw"])
        patients.append(rec)
    return patients


def extract_file1(grid) -> list[dict]:
    rows = {
        "Gender": (2, "text"),
        "Age": (3, "num"),
        "Previous_Airway_Records": (4, "text"),
        "Disease": (5, "text"),
        "Comorbidities": (6, "text"),
        "Breathing_Snoring": (8, "text"),
        "Breathing_Sleep_Apnea": (9, "text"),
        "Symptom_Voice_Changes": (11, "text"),
        "Symptom_Difficulty_Swallowing": (12, "text"),
        "Symptom_Cant_Lie_Flat": (13, "text"),
        "Injury_Swelling": (15, "text"),
        "Injury_Previous_Neck_Fracture": (16, "text"),
        "Previous_Emergencies_ICU": (17, "text"),
        "BMI": (19, "num"),
        "Neck_Circumference_cm": (20, "num"),
        "Beard": (21, "text"),
        "Chest_Size_cm": (22, "num"),
        "Neck_Structure": (23, "text"),
        "Mouth_Opening_Raw": (24, "text"),
        "Mallampati_Score": (25, "num"),
        "TMD_cm": (26, "num"),
        "SMD_cm": (27, "num"),
        "Jaw_Movement": (28, "text"),
        "Neck_Movement": (29, "text"),
        "Tissue_Flexibility": (30, "text"),
        "Teeth": (31, "text"),
        "Tongue_Thickness_cm": (32, "num"),
    }
    patients = []
    for p in range(1, 46):
        col = 3 + p
        rec: dict = {"Patient_No": p}
        for field, (row, kind) in rows.items():
            cell = grid.get((row, col), "")
            if kind == "num":
                val = num(cell)
                rec[field] = "" if val is None else val
            else:
                rec[field] = clean_text(cell)
        rec["Mouth_Opening_Fingers"] = mouth_fingers(rec["Mouth_Opening_Raw"])
        patients.append(rec)
    return patients


# ------------------------------------------------------------- xlsx writing


def cell(ref: str, value, style: int = 0) -> str:
    if value is None or value == "":
        if style:
            return f'<c r="{ref}" s="{style}"/>'
        return ""
    style_attr = f' s="{style}"' if style else ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return f'<c r="{ref}"{style_attr}><v>{value}</v></c>'
    return (
        f'<c r="{ref}"{style_attr} t="inlineStr"><is>'
        f'<t xml:space="preserve">{escape(str(value))}</t></is></c>'
    )


def sheet_xml(rows: list[list], widths: list[tuple[int, int]], freeze: str = "") -> str:
    """rows = list of (values, style) tuples; style applies to non-empty cells."""
    parts: list[str] = []
    for r_idx, (values, style) in enumerate(rows, start=1):
        cells = "".join(
            cell(f"{_col_letter(c_idx)}{r_idx}", val, style)
            for c_idx, val in enumerate(values, start=1)
        )
        parts.append(f'<row r="{r_idx}">{cells}</row>')
    max_col = max((len(v) for v, _ in rows), default=1)
    max_row = len(rows)
    cols = "".join(
        f'<col min="{lo}" max="{hi}" width="{w}" customWidth="1"/>'
        for lo, hi, w in widths
    )
    pane = (
        f'<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        if freeze
        else ""
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:{_col_letter(max_col)}{max_row}"/>'
        f'<sheetViews><sheetView workbookViewId="0">{pane}</sheetView></sheetViews>'
        f"<cols>{cols}</cols>"
        f"<sheetData>{''.join(parts)}</sheetData>"
        "</worksheet>"
    )


STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="3">
<font><sz val="11"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>
</fonts>
<fills count="4">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF1F3864"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFFFF2CC"/><bgColor indexed="64"/></patternFill></fill>
</fills>
<borders count="2">
<border><left/><right/><top/><bottom/><diagonal/></border>
<border><left style="thin"><color rgb="FFBFBFBF"/></left><right style="thin"><color rgb="FFBFBFBF"/></right><top style="thin"><color rgb="FFBFBFBF"/></top><bottom style="thin"><color rgb="FFBFBFBF"/></bottom><diagonal/></border>
</borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="6">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/>
<xf numFmtId="0" fontId="2" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/>
<xf numFmtId="0" fontId="1" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1"/>
<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"/>
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
</cellXfs>
</styleSheet>"""

# 1 = title (bold, yellow), 2 = header (bold, white on navy), 3 = bold label,
# 4 = body with thin border.

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
{sheet_overrides}
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""


def write_workbook(path: Path, sheets: list[tuple[str, str]]) -> None:
    overrides = "\n".join(
        f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, len(sheets) + 1)
    )
    sheet_entries = "".join(
        f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>'
        for i, (name, _) in enumerate(sheets, start=1)
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheet_entries}</sheets></workbook>"
    )
    rels = "".join(
        f'<Relationship Id="rId{i}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, len(sheets) + 1)
    )
    rels += (
        f'<Relationship Id="rId{len(sheets) + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{rels}</Relationships>"
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES.format(sheet_overrides=overrides))
        z.writestr("_rels/.rels", ROOT_RELS)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        z.writestr("xl/styles.xml", STYLES)
        for i, (_, xml) in enumerate(sheets, start=1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", xml)


# -------------------------------------------------------------------- build


FILE2_FIELDS = [
    ("Gender", "Gender"),
    ("Age", "Age"),
    ("Neck_Circumference_cm", "Neck circumference (cm)"),
    ("Chest_Size_cm", "Chest size (cm)"),
    ("Mouth_Opening_Raw", "Mouth opening"),
    ("Mallampati_Score", "Mallampati score"),
    ("TMD_cm", "Thyromental distance (cm)"),
    ("SMD_cm", "Sternomental distance (cm)"),
    ("Jaw_Movement", "Jaw movement"),
    ("Neck_Movement", "Neck movement"),
    ("Teeth", "Teeth"),
    ("Difficulty", "DIFFICULTY"),
]

FILE1_FIELDS = [
    ("Gender", "GENDER"),
    ("Age", "AGE (YEARS)"),
    ("Previous_Airway_Records", "A) PREVIOUS AIRWAY RECORDS"),
    ("Disease", "B) DISEASE"),
    ("Comorbidities", "C) COMORBIDITIES"),
    ("Breathing_Snoring", "SNORING"),
    ("Breathing_Sleep_Apnea", "SLEEP APNEA"),
    ("Symptom_Voice_Changes", "VOICE CHANGES"),
    ("Symptom_Difficulty_Swallowing", "DIFFICULTY IN SWALLOWING"),
    ("Symptom_Cant_Lie_Flat", "CAN'T LIE FLAT"),
    ("Injury_Swelling", "SWELLING"),
    ("Injury_Previous_Neck_Fracture", "PREVIOUS NECK FRACTURE"),
    ("Previous_Emergencies_ICU", "PREVIOUS EMERGENCIES"),
    ("BMI", "BODY MASS INDEX kg/m2"),
    ("Neck_Circumference_cm", "B) NECK CIRCUMFERENCE cm"),
    ("Beard", "C) BEARD"),
    ("Chest_Size_cm", "D) CHEST SIZE cm"),
    ("Neck_Structure", "E) NECK STRUCTURE"),
    ("Mouth_Opening_Raw", "A) MOUTH OPENING"),
    ("Mallampati_Score", "B) MALLAMPATI SCORE"),
    ("TMD_cm", "C) THYROMENTAL DISTANCE cm"),
    ("SMD_cm", "D) STERNOMENTAL DISTANCE cm"),
    ("Jaw_Movement", "E) JAW MOVEMENT"),
    ("Neck_Movement", "F) NECK MOVEMENT"),
    ("Tissue_Flexibility", "G) TISSUE FLEXIBILITY"),
    ("Teeth", "H) TEETH"),
    ("Tongue_Thickness_cm", "TONGUE THICKNESS cm"),
]


def build_wide(p2: list[dict], p1: list[dict]) -> str:
    rows: list[tuple[list, int]] = []
    rows.append((["AI LARYNGOSCOPY 2 - 80 PATIENTS (IMAGE-CORRELATED, WITH DIFFICULTY)"], 1))
    rows.append((["Patient no.", "CATEGORY", "PARAMETER"] + [str(i) for i in range(1, 81)], 2))
    for field, label in FILE2_FIELDS:
        rows.append((["", "", label] + [p[field] for p in p2], 4))
    rows.append(([""], 0))
    rows.append(([""], 0))
    rows.append(
        (
            ["AI LARYNGOSCOPY 1 - SAME 45 PATIENTS AS ABOVE (EXTRA FIELDS, NO DIFFICULTY LABEL)"],
            1,
        )
    )
    rows.append((["Patient no.", "CATEGORY", "PARAMETER"] + [str(i) for i in range(1, 46)], 2))
    for field, label in FILE1_FIELDS:
        rows.append((["", "", label] + [p[field] for p in p1], 4))
    rows.append(
        (
            [
                "Patients 46-80 of AI laryngoscopy 2 have no matching rows in AI laryngoscopy 1. "
                "See the Combined_Long sheet for the de-duplicated 80-patient master table."
            ],
            5,
        )
    )
    return sheet_xml(rows, [(1, 3, 38), (4, 90, 12)])


LONG_COLUMNS = [
    ("Patient_ID", "text"),
    ("Patient_No", "int"),
    ("Image_ID", "text"),
    ("Photo_Count", "int"),
    ("Photo_Example", "text"),
    ("Difficulty", "text"),
    ("Difficulty_Raw", "text"),
    ("Source_Dataset", "text"),
    ("Gender", "text"),
    ("Age", "num"),
    ("Previous_Airway_Records", "text"),
    ("Disease", "text"),
    ("Comorbidities", "text"),
    ("Breathing_Snoring", "text"),
    ("Breathing_Sleep_Apnea", "text"),
    ("Symptom_Voice_Changes", "text"),
    ("Symptom_Difficulty_Swallowing", "text"),
    ("Symptom_Cant_Lie_Flat", "text"),
    ("Injury_Swelling", "text"),
    ("Injury_Previous_Neck_Fracture", "text"),
    ("Previous_Emergencies_ICU", "text"),
    ("BMI", "num"),
    ("Neck_Circumference_cm", "num"),
    ("Beard", "text"),
    ("Chest_Size_cm", "num"),
    ("Neck_Structure", "text"),
    ("Mouth_Opening_Raw", "text"),
    ("Mouth_Opening_Fingers", "num"),
    ("Mallampati_Score", "num"),
    ("TMD_cm", "num"),
    ("SMD_cm", "num"),
    ("Jaw_Movement", "text"),
    ("Neck_Movement", "text"),
    ("Tissue_Flexibility", "text"),
    ("Teeth", "text"),
    ("Tongue_Thickness_cm", "num"),
    ("Notes", "text"),
]


def build_long(p2: list[dict], p1_by_no: dict[int, dict]) -> str:
    rows: list[tuple[list, int]] = []
    rows.append(([label for label, _ in LONG_COLUMNS], 2))
    for rec in p2:
        no = rec["Patient_No"]
        merged = dict(rec)
        if no in p1_by_no:
            extra = p1_by_no[no]
            for field, _ in LONG_COLUMNS:
                if field in extra and extra[field] not in ("", None):
                    merged[field] = extra[field]
            source = "AI laryngoscopy 2 + AI laryngoscopy 1 (same patient, enriched)"
            note = "Rows 1-45 are present in both files; file 1 supplied the extra clinical fields."
        else:
            source = "AI laryngoscopy 2"
            note = "Only in AI laryngoscopy 2 (no matching row in file 1)."
        count, example = photo_stats(no)
        if count == 0:
            note += " No numeric-named photo found in redacted_images."
        values = []
        for field, kind in LONG_COLUMNS:
            if field == "Patient_ID":
                values.append(f"P-{no:04d}")
            elif field == "Image_ID":
                values.append(str(no))
            elif field == "Photo_Count":
                values.append(count)
            elif field == "Photo_Example":
                values.append(example)
            elif field == "Source_Dataset":
                values.append(source)
            elif field == "Notes":
                values.append(note)
            else:
                val = merged.get(field, "")
                if kind in ("num", "int") and val in ("", None):
                    values.append("")
                else:
                    values.append(val)
        rows.append((values, 4))
    return sheet_xml(rows, [(1, 1, 12), (2, 2, 10), (3, 37, 20)], freeze="A2")


def build_file1_only(p1: list[dict]) -> str:
    cols = ["Patient_ID", "Patient_No"] + [f for f, _ in FILE1_FIELDS]
    rows: list[tuple[list, int]] = [(cols, 2)]
    for rec in p1:
        values = [f"P-{rec['Patient_No']:04d}", rec["Patient_No"]]
        values += [rec[f] for f, _ in FILE1_FIELDS]
        rows.append((values, 4))
    return sheet_xml(rows, [(1, 1, 12), (2, 2, 10), (3, 30, 24)], freeze="A2")


def build_notes(p2: list[dict], p1: list[dict]) -> str:
    diff_counts: dict[str, int] = {}
    for rec in p2:
        diff_counts[rec["Difficulty"] or "(blank)"] = diff_counts.get(rec["Difficulty"] or "(blank)", 0) + 1
    lines = [
        ("Merge summary", ""),
        ("Output file", OUT.name),
        ("File 1 (no difficulty)", FILE1.name),
        ("File 2 (with difficulty)", FILE2.name),
        ("Patients in file 1", len(p1)),
        ("Patients in file 2", len(p2)),
        ("Unique patients in output", len(p2)),
        ("", ""),
        ("KEY FINDING", ""),
        (
            "The 45 patients in file 1 are EXACTLY patients 1-45 of file 2. "
            "All 11 shared fields (gender, age, neck circumference, chest size, mouth opening, "
            "Mallampati, TMD, SMD, jaw movement, neck movement, teeth) matched 45/45.",
            "",
        ),
        (
            "Therefore file 1 is not a separate cohort. It only adds columns that file 2 lacks: "
            "BMI, beard, neck structure, disease, comorbidities, snoring, sleep apnea, voice changes, "
            "difficulty swallowing, cannot lie flat, swelling, previous neck fracture, previous "
            "emergencies, tissue flexibility, tongue thickness.",
            "",
        ),
        ("", ""),
        ("Sheet layout", ""),
        ("Combined_Wide", "Block A = 80 patients with Difficulty. Block B = 45 patients from file 1 below it (as requested)."),
        ("Combined_Long", "80 unique patients, one row each. Rows 1-45 enriched from file 1. Use this for ML."),
        ("Laryngoscopy_1_Only", "File 1 preserved on its own, 45 rows, no difficulty column."),
        ("", ""),
        ("Difficulty distribution (80 patients)", ""),
    ]
    for name in ("Easy", "Moderate", "Difficult", "(blank)"):
        if name in diff_counts:
            lines.append((name, diff_counts[name]))
    lines += [
        ("", ""),
        ("Normalisation rules", ""),
        ("MEDIUM / MEIDUM", "Moderate  (patient 38 was typed MEIDUM in the source)"),
        ("HARD", "Difficult"),
        ("EASY", "Easy"),
        ("Mallampati NA", "left blank"),
        ("Mouth opening", "text kept, plus numeric fingers parsed (3 FINGERS -> 3.0)"),
        ("Float noise", "rounded to 2 decimals (18.600000000000001 -> 18.6)"),
        ("", ""),
        ("Image correlation", ""),
        (
            "Image_ID = patient number. Photos whose filename stem is N or N(k) belong to patient N "
            "(e.g. 7.jpg, 7(1).jpg, 7(2).jpg). Photo_Count / Photo_Example come from data/raw/redacted_images.",
            "",
        ),
        (
            "Patients with no numeric-named photo may still have photos named IMG-*.jpg or by date "
            "(20260928 ...). Those need a manual assignment before training.",
            "",
        ),
        ("", ""),
        ("Warning", ""),
        ("This workbook contains real patient clinical data. It must never be committed to git.", ""),
    ]
    rows = [([a, b], 4) for a, b in lines]
    rows[0] = (["Merge notes - read this first"], 1)
    return sheet_xml(rows, [(1, 1, 42), (2, 2, 110)])


def main() -> int:
    if not FILE1.exists() or not FILE2.exists():
        raise SystemExit(f"Missing input. Expected:\n  {FILE1}\n  {FILE2}")

    p2 = extract_file2(read_first_sheet(FILE2))
    p1 = extract_file1(read_first_sheet(FILE1))
    p1_by_no = {rec["Patient_No"]: rec for rec in p1}

    # sanity checks before writing anything
    assert len(p2) == 80, f"expected 80 patients in file 2, got {len(p2)}"
    assert len(p1) == 45, f"expected 45 patients in file 1, got {len(p1)}"
    for rec in p2:
        if not rec["Difficulty"]:
            print(f"  WARN patient {rec['Patient_No']}: difficulty is blank/unknown")
    missing = [rec["Patient_No"] for rec in p2[:45] if rec["Patient_No"] not in p1_by_no]
    assert not missing, f"patients {missing} missing from file 1"

    sheets = [
        ("Combined_Wide", build_wide(p2, p1)),
        ("Combined_Long", build_long(p2, p1_by_no)),
        ("Laryngoscopy_1_Only", build_file1_only(p1)),
        ("Notes", build_notes(p2, p1)),
    ]
    write_workbook(OUT, sheets)

    counts = {}
    for rec in p2:
        counts[rec["Difficulty"] or "(blank)"] = counts.get(rec["Difficulty"] or "(blank)", 0) + 1
    print(f"Wrote {OUT}")
    print(f"  sheets        : {', '.join(name for name, _ in sheets)}")
    print(f"  patients      : {len(p2)} unique (1-45 enriched from file 1)")
    print(f"  difficulty    : {counts}")
    print(f"  size          : {OUT.stat().st_size / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
