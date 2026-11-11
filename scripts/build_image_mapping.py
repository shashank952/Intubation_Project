"""Build the photo -> patient mapping for the redacted airway image set.

What this does
--------------
Reads every redacted photo, works out which patient it belongs to from the
filename (``52.jpg`` and ``52(3).jpg`` -> patient 52), joins it to the patient
table, and writes three things:

    data/temp/image_mapping.csv          one row per photo (machine readable)
    data/temp/image_patient_review.xlsx  one row per patient (human readable)
    data/temp/image_review.html          thumbnail contact sheet (visual check)

Only ``data/raw/redacted_images`` is read. The original, unredacted folder is
never touched.

Rows are never dropped silently: a patient without photos, a photo without a
patient row, or a filename that cannot be parsed is written to the Problems
sheet with an explicit status.

Usage
-----
    py -3.12 scripts/build_image_mapping.py
"""

from __future__ import annotations

import base64
import csv
import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_laryngoscopy_datasets as base  # noqa: E402

IMAGE_DIR = base.ROOT / "data" / "raw" / "redacted_images"
OUT_CSV = base.TEMP / "image_mapping.csv"
OUT_XLSX = base.TEMP / "image_patient_review.xlsx"
OUT_HTML = base.TEMP / "image_review.html"

SOURCE_SHEET = "Combined_Long"
NAME_RE = re.compile(r"^(\d+)(?:\((\d+)\))?$", re.IGNORECASE)
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

# ------------------------------------------------------------------ loading


def load_patients() -> dict[int, dict]:
    grid = base.read_sheet(base.OUT, SOURCE_SHEET)
    header = []
    col = 1
    while grid.get((1, col), ""):
        header.append(grid[(1, col)])
        col += 1

    patients: dict[int, dict] = {}
    row = 2
    while grid.get((row, 1), ""):
        record = {h: grid.get((row, i + 1), "") for i, h in enumerate(header)}
        patients[int(record["Patient_No"])] = record
        row += 1
    return patients


def scan_photos() -> tuple[list[dict], list[str]]:
    """Return (parsed photos, unparsed filenames)."""
    photos: list[dict] = []
    unparsed: list[str] = []
    for path in sorted(IMAGE_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS:
            continue
        match = NAME_RE.match(path.stem)
        if not match:
            unparsed.append(path.name)
            continue
        photos.append(
            {
                "file": path.name,
                "patient_no": int(match.group(1)),
                "copy_index": int(match.group(2)) if match.group(2) else 0,
            }
        )
    photos.sort(key=lambda p: (p["patient_no"], p["copy_index"], p["file"]))
    return photos, unparsed


# ------------------------------------------------------------------- build


def build(patients: dict[int, dict], photos: list[dict], unparsed: list[str]) -> dict:
    by_patient: dict[int, list[dict]] = {}
    for photo in photos:
        by_patient.setdefault(photo["patient_no"], []).append(photo)

    max_no = max(max(by_patient, default=0), max(patients, default=0))
    review_rows: list[dict] = []
    problems: list[dict] = []

    for number in range(1, max_no + 1):
        patient = patients.get(number)
        files = by_patient.get(number, [])
        has_row = patient is not None
        label = patient.get("Difficulty", "") if patient else ""

        if has_row and files:
            status = "OK"
            note = ""
        elif has_row and not files:
            status = "NO_PHOTO"
            note = "Excel row exists but no redacted photo has this number."
        elif not has_row and files:
            status = "NO_EXCEL_ROW"
            note = "Photos exist but there is no patient row; left unused."
        else:
            status = "NO_ROW_NO_PHOTO"
            note = "Gap in numbering."

        review_rows.append(
            {
                "Patient_ID": f"P-{number:04d}",
                "Patient_No": number,
                "Difficulty": label,
                "Photo_Count": len(files),
                "Photo_List": ", ".join(p["file"] for p in files),
                "Status": status,
                "Usable_For_Training": 1 if (has_row and files and label) else 0,
                "Notes": note,
            }
        )

        if status != "OK":
            problems.append(
                {
                    "Kind": status,
                    "Patient_ID": f"P-{number:04d}",
                    "Detail": note,
                    "Files": ", ".join(p["file"] for p in files) or "-",
                }
            )

    for name in unparsed:
        problems.append(
            {
                "Kind": "UNPARSED_FILENAME",
                "Patient_ID": "-",
                "Detail": "Filename is not N.jpg or N(k).jpg, so no patient could be assigned.",
                "Files": name,
            }
        )

    # consistency check against Photo_Count written by the merge script
    mismatches = []
    for row in review_rows:
        patient = patients.get(row["Patient_No"])
        if patient is None:
            continue
        expected = int(patient.get("Photo_Count") or 0)
        if expected != row["Photo_Count"]:
            mismatches.append(
                {
                    "Kind": "COUNT_MISMATCH",
                    "Patient_ID": row["Patient_ID"],
                    "Detail": f"Combined_Long says {expected}, actual files {row['Photo_Count']}",
                    "Files": row["Photo_List"] or "-",
                }
            )
    problems.extend(mismatches)

    photo_map = []
    for photo in photos:
        patient = patients.get(photo["patient_no"])
        photo_map.append(
            {
                "photo_file": photo["file"],
                "patient_no": photo["patient_no"],
                "patient_id": f"P-{photo['patient_no']:04d}",
                "copy_index": photo["copy_index"],
                "has_excel_row": 1 if patient else 0,
                "difficulty": patient.get("Difficulty", "") if patient else "",
                "usable_for_training": 1 if (patient and patient.get("Difficulty")) else 0,
            }
        )

    return {
        "review_rows": review_rows,
        "photo_map": photo_map,
        "problems": problems,
        "by_patient": by_patient,
        "unparsed": unparsed,
        "mismatches": mismatches,
    }


# ------------------------------------------------------------------ output


def write_csv(photo_map: list[dict]) -> None:
    fields = list(photo_map[0].keys())
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(photo_map)


def write_xlsx(result: dict) -> None:
    review_header = [
        "Patient_ID",
        "Patient_No",
        "Difficulty",
        "Photo_Count",
        "Photo_List",
        "Status",
        "Usable_For_Training",
        "Notes",
    ]
    review_rows = [(review_header, 2)]
    for row in result["review_rows"]:
        review_rows.append(([row[h] for h in review_header], 4))

    map_header = [
        "photo_file",
        "patient_no",
        "patient_id",
        "copy_index",
        "has_excel_row",
        "difficulty",
        "usable_for_training",
    ]
    map_rows = [(map_header, 2)]
    for row in result["photo_map"]:
        map_rows.append(([row[h] for h in map_header], 4))

    problem_header = ["Kind", "Patient_ID", "Detail", "Files"]
    problem_rows = [(problem_header, 2)]
    for row in result["problems"]:
        problem_rows.append(([row[h] for h in problem_header], 4))
    if not result["problems"]:
        problem_rows.append((["(none)", "", "", ""], 4))

    total = len(result["photo_map"])
    usable = sum(1 for r in result["photo_map"] if r["usable_for_training"])
    by_status: dict[str, int] = {}
    for row in result["review_rows"]:
        by_status[row["Status"]] = by_status.get(row["Status"], 0) + 1

    notes = [
        ("PHOTO -> PATIENT MAPPING - READ THIS FIRST", ""),
        ("", ""),
        ("Rule", "The filename IS the patient number. 52.jpg and 52(3).jpg both belong to patient 52."),
        ("The (n) suffix", "Copy number of the same patient: (1), (2), (3)... 52.jpg itself has copy index 0."),
        ("Image folder", "data/raw/redacted_images (redacted only)"),
        ("", ""),
        ("Totals", ""),
        ("Photos on disk", total),
        ("Photos mapped to a patient row", usable),
        ("Photos left aside (no Excel row)", total - usable),
        ("Patients with a row", len(result["review_rows"])),
        ("", ""),
        ("Status counts", ""),
    ]
    for name in ("OK", "NO_PHOTO", "NO_EXCEL_ROW", "NO_ROW_NO_PHOTO"):
        if name in by_status:
            notes.append((name, by_status[name]))
    notes += [
        ("", ""),
        ("What each status means", ""),
        ("OK", "Has an Excel row, has photos, has a difficulty label. Usable."),
        ("NO_PHOTO", "Has an Excel row but no redacted photo. Left in the table so the gap is visible."),
        ("NO_EXCEL_ROW", "Photos exist but no row in the Excel. Left unused on purpose."),
        ("", ""),
        ("How to use the mapping", ""),
        ("For training", "image_mapping.csv, filter usable_for_training == 1, group by patient_id."),
        ("Split rule", "Split train/val/test by patient_id, never by photo. All photos of one patient stay in one split."),
        ("", ""),
        ("Visual check", ""),
        ("Open", "image_review.html in a browser"),
        ("Why", "It shows each patient's photos side by side so you can confirm the filename really is the right person."),
        ("", ""),
        ("Warning", "This workbook and the review page contain real patient photos (redacted). data/temp/ is gitignored. Never commit or share."),
    ]
    note_rows: list[tuple[list, int]] = []
    for i, (left, right) in enumerate(notes):
        note_rows.append(([left, right], 1 if i == 0 else 4))

    sheets = [
        ("Patient_Review", base.sheet_xml(review_rows, [(1, 1, 12), (2, 2, 10), (3, 3, 11), (4, 4, 11), (5, 5, 70), (6, 6, 16), (7, 7, 18), (8, 8, 60)], freeze="A2")),
        ("Photo_Map", base.sheet_xml(map_rows, [(1, 1, 18), (2, 2, 10), (3, 3, 12), (4, 4, 11), (5, 5, 13), (6, 6, 12), (7, 7, 18)], freeze="A2")),
        ("Problems", base.sheet_xml(problem_rows, [(1, 1, 20), (2, 2, 12), (3, 3, 70), (4, 4, 50)], freeze="A2")),
        ("Notes", base.sheet_xml(note_rows, [(1, 1, 42), (2, 2, 110)])),
    ]
    base.write_workbook(OUT_XLSX, sheets)


def thumb_data_uri(path: Path, width: int = 150) -> str:
    from PIL import Image

    with Image.open(path) as image:
        image = image.convert("RGB")
        height = max(1, int(image.height * width / image.width))
        image = image.resize((width, height))
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=65, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def write_html(result: dict) -> None:
    colours = {"Easy": "#15803d", "Moderate": "#b45309", "Difficult": "#b91c1c"}
    total = len(result["photo_map"])
    cards = []
    for row in result["review_rows"]:
        number = row["Patient_No"]
        files = result["by_patient"].get(number, [])
        label = row["Difficulty"]
        badge = f'<span class="badge" style="background:{colours.get(label, "#6b7280")}">{label or "no label"}</span>'
        status = "" if row["Status"] == "OK" else f'<span class="status">{row["Status"]}</span>'
        tiles = "".join(
            f'<figure><img src="{thumb_data_uri(IMAGE_DIR / p["file"])}" alt="{p["file"]}">'
            f'<figcaption>{p["file"]}</figcaption></figure>'
            for p in files
        ) or '<p class="empty">no photos</p>'
        cards.append(
            f'<section class="card"><header><h2>{row["Patient_ID"]}</h2>{badge}{status}'
            f'<span class="count">{len(files)} photo(s)</span></header><div class="grid">{tiles}</div></section>'
        )

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Photo to patient mapping - visual check</title>
<style>
:root {{ color-scheme: light; }}
body {{ font-family: ui-sans-serif, system-ui, sans-serif; margin: 0; padding: 24px; background:#f5f5f4; color:#111; }}
h1 {{ font-size: 20px; margin: 0 0 4px; }}
p.sub {{ margin: 0 0 20px; color:#555; font-size: 13px; }}
.card {{ background:#fff; border:1px solid #d6d3d1; border-radius:8px; padding:12px 14px; margin-bottom:14px; }}
.card header {{ display:flex; align-items:center; gap:10px; margin-bottom:10px; }}
.card h2 {{ font-size:14px; margin:0; font-variant-numeric: tabular-nums; }}
.badge {{ color:#fff; font-size:10px; font-weight:700; padding:2px 7px; border-radius:999px; text-transform:uppercase; letter-spacing:.04em; }}
.status {{ font-size:10px; font-weight:700; color:#b91c1c; border:1px solid #fca5a5; background:#fef2f2; padding:2px 7px; border-radius:999px; }}
.count {{ margin-left:auto; font-size:11px; color:#777; }}
.grid {{ display:flex; flex-wrap:wrap; gap:8px; }}
figure {{ margin:0; width:150px; }}
figure img {{ width:150px; height:auto; border-radius:4px; border:1px solid #e7e5e4; display:block; }}
figcaption {{ font-size:10px; color:#666; margin-top:2px; word-break:break-all; }}
.empty {{ font-size:12px; color:#b91c1c; margin:0; }}
</style></head><body>
<h1>Photo &rarr; patient mapping (visual check)</h1>
<p class="sub">{total} redacted photos &middot; filename stem = patient number &middot; (n) = copy number of the same patient</p>
{''.join(cards)}
</body></html>"""
    OUT_HTML.write_text(html, encoding="utf-8")


# -------------------------------------------------------------------- main


def main() -> int:
    if not IMAGE_DIR.is_dir():
        raise SystemExit(f"Missing image folder: {IMAGE_DIR}")
    if not base.OUT.exists():
        raise SystemExit(f"Missing: {base.OUT}\nRun merge_laryngoscopy_datasets.py first.")

    patients = load_patients()
    photos, unparsed = scan_photos()
    if not photos:
        raise SystemExit("No photos found.")

    result = build(patients, photos, unparsed)
    write_csv(result["photo_map"])
    write_xlsx(result)
    write_html(result)

    total = len(result["photo_map"])
    usable = sum(1 for r in result["photo_map"] if r["usable_for_training"])
    statuses: dict[str, int] = {}
    for row in result["review_rows"]:
        statuses[row["Status"]] = statuses.get(row["Status"], 0) + 1

    print(f"Wrote {OUT_CSV.name}, {OUT_XLSX.name}, {OUT_HTML.name}")
    print(f"  photos on disk        : {total}")
    print(f"  mapped to a patient   : {usable}")
    print(f"  left aside            : {total - usable}")
    print(f"  patients in table     : {len(result['review_rows'])}")
    print(f"  statuses              : {statuses}")
    print(f"  problems              : {len(result['problems'])}")
    for problem in result["problems"]:
        print(f"    - {problem['Kind']}: {problem['Patient_ID']} {problem['Files'][:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
