import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "raw" / "merged_laryngoscopy.xlsx"
TARGET = ROOT / "data" / "raw" / "annotation_template.xlsx"

RULE_VERSION = "1.0"

HEADER_FILL_REQUIRED = PatternFill("solid", fgColor="FFD966")
HEADER_FILL_AUTO = PatternFill("solid", fgColor="D9D9D9")
HEADER_FILL_OPTIONAL = PatternFill("solid", fgColor="B4C7E7")
HEADER_FILL_META = PatternFill("solid", fgColor="C6E0B4")
AUTO_FILL = PatternFill("solid", fgColor="F2F2F2")
THIN = Side(style="thin", color="808080")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

COLUMNS = [
    ("Patient_ID", 13, "required", "Pre-filled. Do not edit. Must match the measurements sheet."),
    ("CL_grade", 10, "required", "Cormack-Lehane view at best attempt: 1, 2, 3 or 4."),
    ("Attempts", 10, "required", "Number of laryngoscopy attempts: 1, 2, 3, or 4 (4 means 4 or more)."),
    ("Adjunct", 10, "required", "Y/N. Was an adjunct used? bougie, stylet, BURP, cricoid pressure."),
    ("Rescue_device", 14, "required", "Y/N. Was a rescue device needed? video laryngoscope, fiberoptic, LMA, surgical airway."),
    ("Decision", 12, "auto", "AUTO-CALCULATED from CL_grade, Attempts, Adjunct, Rescue_device. Do not type here."),
    ("Clinician_Assessment", 20, "required", "Your own overall judgement, independent of the columns to the left: Easy, Moderate or Difficult."),
    ("Agreement", 11, "auto", "AUTO. 'match' or 'differs' between Decision and Clinician_Assessment."),
    ("Device_first", 18, "optional", "Device used on the first attempt: Macintosh, Video laryngoscope, Fiberoptic, Other."),
    ("Operator_grade", 16, "optional", "Who performed it: Consultant, Senior trainee, Junior trainee. Difficulty depends on skill."),
    ("Intubation_time_sec", 18, "optional", "Seconds from laryngoscope insertion to tube in trachea."),
    ("SpO2_nadir_pct", 14, "optional", "Lowest oxygen saturation during the attempt, percent."),
    ("ASA_grade", 11, "optional", "ASA physical status: 1, 2, 3 or 4."),
    ("Source_record", 15, "meta", "Where the outcome was read from: Theatre notes, EMR, Register, Other."),
    ("Annotator", 12, "meta", "Your initials."),
    ("Annotated_on", 13, "meta", "Date you filled this row."),
    ("Blinded", 10, "meta", "Y/N. Did you fill this WITHOUT looking at any model prediction? Must be Y."),
    ("Record_complete", 16, "meta", "Y/N. Was the theatre record complete enough to judge?"),
    ("Notes", 40, "optional", "Anything unusual: failed videolaryngoscopy, awake fibreoptic, patient position, etc."),
]

VALIDATIONS = {
    "CL_grade": ("B", '"1,2,3,4"', "CL grade must be 1, 2, 3 or 4."),
    "Attempts": ("C", '"1,2,3,4"', "Attempts must be 1, 2, 3 or 4 (use 4 for four or more)."),
    "Adjunct": ("D", '"Y,N"', "Enter Y or N."),
    "Rescue_device": ("E", '"Y,N"', "Enter Y or N."),
    "Clinician_Assessment": ("G", '"Easy,Moderate,Difficult"', "Choose Easy, Moderate or Difficult."),
    "Device_first": ("I", '"Macintosh,Video laryngoscope,Fiberoptic,Other"', "Choose from the list."),
    "Operator_grade": ("J", '"Consultant,Senior trainee,Junior trainee"', "Choose from the list."),
    "ASA_grade": ("M", '"1,2,3,4"', "ASA grade must be 1, 2, 3 or 4."),
    "Source_record": ("N", '"Theatre notes,EMR,Register,Other"', "Choose from the list."),
    "Blinded": ("Q", '"Y,N"', "Enter Y or N."),
    "Record_complete": ("R", '"Y,N"', "Enter Y or N."),
}


def decision_formula(row):
    b, c, d, e = f"$B{row}", f"$C{row}", f"$D{row}", f"$E{row}"
    cl = f'IFERROR(VALUE({b}),0)'
    at = f'IFERROR(VALUE({c}),0)'
    return (
        f'=IF(OR({b}="",{c}="",{d}="",{e}=""),"",'
        f'IF(OR({at}>=3,{cl}=4,{e}="Y"),"Difficult",'
        f'IF(OR({d}="Y",{cl}=3,{at}=2),"Moderate","Easy")))'
    )


def agreement_formula(row):
    f, g = f"$F{row}", f"$G{row}"
    return f'=IF(OR({f}="",{g}=""),"",IF(LEFT({f},1)=LEFT({g},1),"match","differs"))'


def build_instructions(ws):
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 112

    rows = [
        ("h1", "Airway difficulty annotation template"),
        ("p", f"Label rule version {RULE_VERSION}. One row per patient. Fill only the yellow (required), blue (optional) and green (audit) columns."),
        ("blank", ""),
        ("h2", "The one rule you must not break"),
        ("p", "Label the patient from WHAT ACTUALLY HAPPENED during intubation. Never label from the measurements (Mallampati, BMI, neck circumference...). If you derive the answer from the same numbers the model sees, the model learns nothing and every score it reports is meaningless."),
        ("blank", ""),
        ("h2", "How Decision is calculated (do not type in that column)"),
        ("code", "Difficult  if  Attempts >= 3  OR  CL_grade = 4  OR  Rescue_device = Y"),
        ("code", "Moderate   if  Adjunct = Y      OR  CL_grade = 3  OR  Attempts = 2"),
        ("code", "Easy       otherwise"),
        ("p", "The Decision column fills itself the moment all four evidence columns are filled. If it stays blank, a required evidence cell is still empty."),
        ("blank", ""),
        ("h2", "What each column is for"),
        ("blank", ""),
        ("h2", "Yellow - required. The model cannot be trained without these."),
        ("p", "Patient_ID, CL_grade, Attempts, Adjunct, Rescue_device, Clinician_Assessment."),
        ("blank", ""),
        ("h2", "Grey - automatic. Never type here."),
        ("p", "Decision is computed from the four evidence columns. Agreement compares Decision against your Clinician_Assessment."),
        ("blank", ""),
        ("h2", "Blue - optional, but strongly recommended."),
        ("p", "Device_first and Operator_grade matter because difficulty is partly about who is holding the laryngoscope: a consultant succeeds where a junior fails. Recording them lets you show the model is not just learning operator skill."),
        ("p", "Intubation_time_sec and SpO2_nadir_pct give you a severity measure that does not depend on the three-class rule, so you can sanity-check the labels later."),
        ("p", "ASA_grade captures baseline sickness, a common confounder."),
        ("blank", ""),
        ("h2", "Green - audit trail. Fill these so the labels can be defended."),
        ("p", "Source_record: where you read the outcome. Annotator: your initials. Annotated_on: the date."),
        ("p", "Blinded: Y only if you filled this row without looking at any model prediction. This must be Y for the metrics to mean anything."),
        ("p", "Record_complete: N if the theatre note was too vague to judge. Better to mark it incomplete than to guess."),
        ("blank", ""),
        ("h2", "Why Clinician_Assessment is separate from Decision"),
        ("p", "Decision is mechanical: the same four facts always give the same class. Clinician_Assessment is your overall impression. Comparing them is the point - if they disagree on many rows, either the rule is too crude or the records are unclear, and you want to know that before training."),
        ("p", "Aim for the Agreement column to say 'match' on most rows. Investigate every 'differs'."),
        ("blank", ""),
        ("h2", "Vocabulary"),
        ("p", "Use exactly Easy / Moderate / Difficult. Do not mix in Medium or Hard - the app and the training code expect the first set, and mixed spellings silently break the mapping."),
        ("blank", ""),
        ("h2", "Sanity checks before you hand this over"),
        ("p", "1. No blank cells in the yellow columns."),
        ("p", "2. The Decision column is filled on every row."),
        ("p", "3. Agreement says 'match' on most rows; every 'differs' has a note explaining why."),
        ("p", "4. Blinded is Y everywhere."),
        ("p", "5. The class counts on the Label_Rule sheet look plausible (Difficult should be a small minority, not a third)."),
    ]

    r = 2
    for kind, text in rows:
        cell = ws.cell(row=r, column=2, value=text)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        if kind == "h1":
            cell.font = Font(bold=True, size=16)
        elif kind == "h2":
            cell.font = Font(bold=True, size=12, color="1F3864")
        elif kind == "code":
            cell.font = Font(name="Consolas", size=10, bold=True)
            cell.fill = AUTO_FILL
        else:
            cell.font = Font(size=10)
        r += 1


def build_rule_sheet(ws, n_rows):
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 26
    ws.column_dimensions["C"].width = 60

    ws["A1"] = "Label rule and live data-quality checks"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f"Rule version {RULE_VERSION}"
    ws["A2"].font = Font(italic=True, size=10)

    ws["A4"] = "Class"
    ws["B4"] = "Count"
    ws["C4"] = "Share"
    for c in ("A4", "B4", "C4"):
        ws[c].font = Font(bold=True)
        ws[c].fill = HEADER_FILL_AUTO
        ws[c].border = BORDER

    for i, name in enumerate(["Easy", "Moderate", "Difficult"]):
        row = 5 + i
        ws.cell(row=row, column=1, value=name)
        ws.cell(row=row, column=2, value=f'=COUNTIF(Annotation!$F$2:$F${n_rows + 1},A{row})')
        ws.cell(row=row, column=3, value=f'=IF(SUM($B$5:$B$7)=0,"",B{row}/SUM($B$5:$B$7))')
        ws.cell(row=row, column=3).number_format = "0.0%"

    checks = [
        ("Rows in template", n_rows),
        ("Rows annotated", f'=COUNTA(Annotation!$B$2:$B${n_rows + 1})'),
        ("Rows still blank on Decision", f'=COUNTBLANK(Annotation!$F$2:$F${n_rows + 1})'),
        ("BLANK CELLS IN REQUIRED COLUMNS (must be 0)", f'=COUNTBLANK(Annotation!$B$2:$B${n_rows + 1})+COUNTBLANK(Annotation!$C$2:$C${n_rows + 1})+COUNTBLANK(Annotation!$D$2:$D${n_rows + 1})+COUNTBLANK(Annotation!$E$2:$E${n_rows + 1})+COUNTBLANK(Annotation!$G$2:$G${n_rows + 1})'),
        ("Agreement: match", f'=COUNTIF(Annotation!$H$2:$H${n_rows + 1},"match")'),
        ("Agreement: differs", f'=COUNTIF(Annotation!$H$2:$H${n_rows + 1},"differs")'),
        ("Rows not blinded (must be 0)", f'=COUNTIF(Annotation!$Q$2:$Q${n_rows + 1},"N")'),
        ("Records marked incomplete", f'=COUNTIF(Annotation!$R$2:$R${n_rows + 1},"N")'),
    ]

    ws["A10"] = "Check"
    ws["B10"] = "Value"
    for c in ("A10", "B10"):
        ws[c].font = Font(bold=True)
        ws[c].fill = HEADER_FILL_AUTO
        ws[c].border = BORDER

    for i, (label, value) in enumerate(checks):
        row = 11 + i
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=value)

    ws["A20"] = "Reminder"
    ws["A20"].font = Font(bold=True)
    ws["A21"] = (
        "If 'Difficult' comes out near a third of the rows, the labels are not real outcomes. "
        "Real difficult intubation is roughly 5-15 percent, so expect a small minority."
    )
    ws["A21"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells("A21:C23")


def build_annotation_sheet(ws, patient_ids):
    for idx, (name, width, _group, _help) in enumerate(COLUMNS, start=1):
        letter = get_column_letter(idx)
        ws.column_dimensions[letter].width = width
        cell = ws.cell(row=1, column=idx, value=name)
        cell.font = Font(bold=True, size=10)
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        cell.border = BORDER
        group = COLUMNS[idx - 1][2]
        cell.fill = {
            "required": HEADER_FILL_REQUIRED,
            "auto": HEADER_FILL_AUTO,
            "optional": HEADER_FILL_OPTIONAL,
            "meta": HEADER_FILL_META,
        }[group]

    ws.row_dimensions[1].height = 42

    for i, pid in enumerate(patient_ids, start=2):
        ws.cell(row=i, column=1, value=pid)
        ws.cell(row=i, column=6, value=decision_formula(i))
        ws.cell(row=i, column=8, value=agreement_formula(i))
        ws.cell(row=i, column=17, value="Y")
        for col in range(1, len(COLUMNS) + 1):
            ws.cell(row=i, column=col).border = BORDER
        ws.cell(row=i, column=6).fill = AUTO_FILL
        ws.cell(row=i, column=8).fill = AUTO_FILL

    last = len(patient_ids) + 1
    for name, (letter, formula, message) in VALIDATIONS.items():
        dv = DataValidation(type="list", formula1=formula, allow_blank=True, showErrorMessage=True)
        dv.error = message
        dv.errorTitle = "Invalid value"
        dv.prompt = message
        dv.promptTitle = COLUMNS[[c[0] for c in COLUMNS].index(name)][3]
        ws.add_data_validation(dv)
        dv.add(f"{letter}2:{letter}{last}")

    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{last}"

    red = PatternFill("solid", fgColor="F8CBAD")
    yellow = PatternFill("solid", fgColor="FFF2CC")
    green = PatternFill("solid", fgColor="D9EAD3")
    ws.conditional_formatting.add(
        f"F2:F{last}", CellIsRule(operator="equal", formula=['"Difficult"'], fill=red)
    )
    ws.conditional_formatting.add(
        f"F2:F{last}", CellIsRule(operator="equal", formula=['"Moderate"'], fill=yellow)
    )
    ws.conditional_formatting.add(
        f"F2:F{last}", CellIsRule(operator="equal", formula=['"Easy"'], fill=green)
    )
    ws.conditional_formatting.add(
        f"H2:H{last}", CellIsRule(operator="equal", formula=['"differs"'], fill=red)
    )


def main():
    if not SOURCE.exists():
        sys.exit(f"Missing source sheet: {SOURCE}")

    ids = pd.read_excel(SOURCE)["Patient_ID"].astype(str).tolist()
    if len(ids) != len(set(ids)):
        sys.exit("Duplicate Patient_ID values in the measurements sheet.")

    wb = Workbook()
    instructions = wb.active
    instructions.title = "Instructions"
    build_instructions(instructions)

    annotation = wb.create_sheet("Annotation")
    build_annotation_sheet(annotation, ids)

    rule = wb.create_sheet("Label_Rule")
    build_rule_sheet(rule, len(ids))

    wb.save(TARGET)
    print(f"Wrote {TARGET}")
    print(f"  patients prefilled : {len(ids)}")
    print(f"  columns            : {len(COLUMNS)}")
    print(f"  rule version       : {RULE_VERSION}")


if __name__ == "__main__":
    main()
