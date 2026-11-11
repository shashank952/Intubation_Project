"""Redact patient eyes with an opaque black strip using a YOLO face-keypoint model.

The detector (`yolo26n-face.pt`) returns one box per face plus 5 landmarks:
left eye, right eye, nose, left mouth corner, right mouth corner. Only the two
eye landmarks are used to place the strip, so the nose and mouth (which carry
the clinically relevant Mallampati / airway information) stay visible.

Safety properties
-----------------
* The input folder is never written to. Outputs go to a separate --out-dir
  that must not be the input folder and must not be its parent.
* Exactly --limit images are processed (default 5) in natural filename order.
  The full dataset needs --all (or --limit N --confirm-batch).
* Byte-identical source images are detected by SHA-256 and processed once, so
  the output folder never contains duplicate images.
* Every input file is hashed before and after processing; the run aborts if any
  input byte changed.
* Outputs are re-encoded without EXIF / metadata.
* No image data is uploaded anywhere; the model weights must already be local.

Usage
-----
    python scripts/redact_eyes.py
    python scripts/redact_eyes.py --limit 5 --dry-run
    python scripts/redact_eyes.py --all
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "raw" / "Image Dataset" / "AI Intubation"
DEFAULT_OUTPUT = ROOT / "data" / "raw" / "redacted_images"
DEFAULT_MODEL = Path.home() / ".cache" / "yolo-face" / "yolo26n-face.pt"

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

# Strip geometry, expressed as multiples of the inter-ocular distance (IOD).
STRIP_HEIGHT = 0.80  # bar thickness
STRIP_RISE = 0.10  # shift up so the brow line is covered as well
STRIP_PAD_X = 0.06  # horizontal padding beyond the detected face box

# Fallback band inside the face box, used when eye landmarks are unreliable.
FALLBACK_TOP = 0.28
FALLBACK_BOTTOM = 0.52

# Tight mouth/eye crops hide most of the face, so the primary pass finds nothing.
# A second, lower-confidence pass runs only for those images, and only keeps
# faces tall enough to avoid smearing a bar over unrelated anatomy.
FALLBACK_CONF = 0.10
MIN_FALLBACK_FACE_FRAC = 0.15

BLACK = (0, 0, 0)


def natural_key(path: Path) -> tuple:
    """Sort '1.jpg' < '1(1).jpg' < '2.jpg' < '10.jpg' instead of lexicographically."""
    stem = path.stem
    match = re.fullmatch(r"(\d+)((?:\(\d+\))*)", stem)
    if match:
        copies = [int(n) for n in re.findall(r"\((\d+)\)", match.group(2))]
        return (0, int(match.group(1)), copies, "")
    return (1, 0, [], stem.lower())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def list_images(folder: Path, limit: int | None) -> list[Path]:
    if not folder.is_dir():
        raise SystemExit(f"Input folder not found: {folder}")
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    files.sort(key=natural_key)
    if not files:
        raise SystemExit(f"No images found in: {folder}")
    return files if limit is None else files[:limit]


def previous_outputs(out_dir: Path) -> list[Path]:
    manifest_path = out_dir / "redaction_manifest.json"
    if not manifest_path.exists():
        return []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [Path(e["output"]) for e in data.get("images", []) if e.get("output")]


def load_rgb(path: Path) -> tuple[np.ndarray, tuple[int, int]]:
    """Read an image upright (EXIF applied) as an RGB uint8 array."""
    with Image.open(path) as raw:
        upright = ImageOps.exif_transpose(raw).convert("RGB")
        array = np.array(upright)
    return array, (upright.width, upright.height)


def detect_faces(model, bgr: np.ndarray, conf: float) -> list[dict]:
    result = model.predict(bgr, conf=conf, iou=0.5, verbose=False)[0]
    if result.boxes is None or len(result.boxes) == 0:
        return []

    boxes = result.boxes.xyxy.cpu().numpy()
    scores = result.boxes.conf.cpu().numpy()

    kpts = kconf = None
    if result.keypoints is not None:
        kpts = result.keypoints.xy.cpu().numpy()
        # Some exports omit per-keypoint confidence; fall back to the raw
        # (x, y, conf) tensor, then to full confidence.
        if result.keypoints.conf is not None:
            kconf = result.keypoints.conf.cpu().numpy()
        elif result.keypoints.data is not None and result.keypoints.data.shape[-1] >= 3:
            kconf = result.keypoints.data[..., 2].cpu().numpy()
        else:
            kconf = np.ones(kpts.shape[:2], dtype=np.float32)

    faces = []
    for idx, (box, score) in enumerate(zip(boxes, scores)):
        faces.append(
            {
                "box": box.astype(float).tolist(),
                "score": float(score),
                "keypoints": kpts[idx].astype(float).tolist() if kpts is not None else None,
                "keypoint_conf": kconf[idx].astype(float).tolist() if kconf is not None else None,
            }
        )
    return faces


def eye_strip(
    face: dict, width: int, height: int, min_kconf: float, cropped_face: bool = False
) -> tuple[tuple[int, int, int, int], str]:
    """Return (x1, y1, x2, y2) of the black strip plus how it was derived."""
    x1, y1, x2, y2 = face["box"]
    left, right = x1, x2

    kpts = face["keypoints"]
    kconf = face["keypoint_conf"] or [1.0, 1.0]
    if kpts and len(kpts) >= 2 and min(kconf[0], kconf[1]) >= min_kconf:
        eye_a, eye_b = kpts[0], kpts[1]
        iod = max(abs(eye_b[0] - eye_a[0]), abs(eye_b[1] - eye_a[1]), 1.0)
        center_x = (eye_a[0] + eye_b[0]) / 2.0
        center_y = (eye_a[1] + eye_b[1]) / 2.0
        # A keypoint model can return a tight face box; keep the bar at least
        # wide enough to span both eye corners.
        pad = STRIP_PAD_X * (x2 - x1)
        span = max(x2 - x1 + 2 * pad, 1.6 * iod)
        left = center_x - span / 2.0
        right = center_x + span / 2.0

        # In profile shots both landmarks collapse onto the visible eye, which
        # makes IOD useless; clamp the bar against face height instead.
        face_h = y2 - y1
        bar = min(max(STRIP_HEIGHT * iod, 0.11 * face_h), 0.30 * face_h)
        if cropped_face:
            # Cropped/profile landmarks drift both ways, and a small face in a
            # wide frame yields a bar too thin to cover the eye, so widen the
            # band symmetrically and anchor it to the top edge on tight crops.
            half = max(bar, 0.06 * height)
            top = center_y - half
            bottom = center_y + half
            if center_y < 0.25 * height:
                top = 0.0
        else:
            top = center_y - bar / 2.0 - STRIP_RISE * bar
            bottom = top + bar
        source = "keypoints"
    else:
        face_h = y2 - y1
        top = y1 + FALLBACK_TOP * face_h
        bottom = y1 + FALLBACK_BOTTOM * face_h
        source = "bbox_fallback"

    sx1 = int(max(0, round(left)))
    sx2 = int(min(width, round(right)))
    sy1 = int(max(0, round(top)))
    sy2 = int(min(height, round(bottom)))
    if sx2 <= sx1 or sy2 <= sy1:
        return (0, 0, 0, 0), "invalid"
    return (sx1, sy1, sx2, sy2), source


def write_image(path: Path, bgr: np.ndarray) -> Path:
    out_path = path.with_suffix(".png" if path.suffix.lower() == ".png" else ".jpg")
    if out_path.suffix == ".png":
        ok = cv2.imwrite(str(out_path), bgr, [cv2.IMWRITE_PNG_COMPRESSION, 6])
    else:
        ok = cv2.imwrite(str(out_path), bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if not ok or not out_path.exists() or out_path.stat().st_size == 0:
        raise OSError(f"Failed to write output for {path.name}")
    return out_path


def redact(args: argparse.Namespace) -> int:
    input_dir = Path(args.input_dir).resolve()
    out_dir = Path(args.out_dir).resolve()

    if out_dir == input_dir or out_dir in input_dir.parents:
        raise SystemExit("Refusing to write into the input folder or one of its parents.")
    if args.all:
        limit = None
    else:
        if args.limit < 1:
            raise SystemExit("--limit must be >= 1.")
        if args.limit > 5 and not args.confirm_batch:
            raise SystemExit(
                f"Refusing to process {args.limit} images without --confirm-batch. "
                "The review step is meant to stay at 5 images."
            )
        limit = args.limit

    images = list_images(input_dir, limit)
    model_path = Path(args.model).expanduser()
    if not model_path.exists():
        raise SystemExit(
            f"Model weights not found: {model_path}\n"
            "Download yolo26n-face.pt from "
            "https://github.com/akanametov/yolo-face/releases/tag/1.0.0 first."
        )

    from ultralytics import YOLO

    model = YOLO(str(model_path))

    before = {p: sha256(p) for p in images}
    seen: dict[str, Path] = {}
    duplicates: list[tuple[Path, Path]] = []
    unique: list[Path] = []
    for path in images:
        digest = before[path]
        if digest in seen:
            duplicates.append((path, seen[digest]))
        else:
            seen[digest] = path
            unique.append(path)

    out_dir.mkdir(parents=True, exist_ok=True)
    stale = previous_outputs(out_dir)
    manifest: dict = {
        "model": str(model_path),
        "model_name": model_path.name,
        "confidence_threshold": args.conf,
        "limit": limit,
        "input_dir": str(input_dir),
        "output_dir": str(out_dir),
        "images": [],
        "duplicates_skipped": [],
        "errors": [],
    }

    written = 0
    used_names: set[str] = set()
    total = len(unique)
    for index, path in enumerate(unique, start=1):
        digest = before[path]
        try:
            rgb, (width, height) = load_rgb(path)
            bgr = np.ascontiguousarray(rgb[:, :, ::-1])
            faces = detect_faces(model, bgr, args.conf)
            detection_stage = "primary"
            if not faces:
                faces = [
                    f
                    for f in detect_faces(model, bgr, FALLBACK_CONF)
                    if (f["box"][3] - f["box"][1]) >= MIN_FALLBACK_FACE_FRAC * height
                ]
                detection_stage = "low_conf" if faces else "none"

            strips = []
            for face in faces:
                rect, source = eye_strip(
                    face, width, height, args.min_kpt_conf, cropped_face=detection_stage == "low_conf"
                )
                face["strip"] = {"rect": list(rect), "source": source}
                if source == "invalid":
                    continue
                x1, y1, x2, y2 = rect
                cv2.rectangle(bgr, (x1, y1), (x2, y2), BLACK, thickness=-1)
                strips.append(rect)

            entry = {
                "input": str(path),
                "input_sha256": digest,
                "width": width,
                "height": height,
                "faces_detected": len(faces),
                "strips_drawn": len(strips),
                "detection_stage": detection_stage,
                "status": "redacted" if strips else "no_face_detected",
                "faces": faces,
                "output": None,
            }

            if not args.dry_run:
                target = path.with_suffix(".png" if path.suffix.lower() == ".png" else ".jpg")
                if target.name in used_names:
                    raise OSError(f"Output name collision for {target.name}")
                entry["output"] = str(write_image(out_dir / target.name, bgr))
                used_names.add(target.name)
                written += 1
        except Exception as exc:  # isolate one bad file from the batch
            entry = {
                "input": str(path),
                "input_sha256": digest,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
                "output": None,
            }
            manifest["errors"].append({"input": str(path), "error": entry["error"]})

        manifest["images"].append(entry)
        print(
            f"[{index:>3}/{total}] {path.name:<22} "
            f"{entry.get('width', '?')}x{entry.get('height', '?')}  "
            f"strips={entry.get('strips_drawn', 0)}  status={entry['status']}"
        )

    for dup, original in duplicates:
        manifest["duplicates_skipped"].append({"input": str(dup), "identical_to": str(original)})

    after = {p: sha256(p) for p in images}
    if before != after:
        raise SystemExit("ABORT: an input file changed during processing.")

    manifest["inputs_unchanged"] = True
    manifest["outputs_written"] = written
    manifest["total_inputs"] = len(images)
    manifest["unique_inputs"] = len(unique)
    manifest["duplicates_skipped_count"] = len(duplicates)

    if not args.dry_run:
        current = {Path(e["output"]) for e in manifest["images"] if e["output"]}
        for path in stale:
            if path not in current and path.parent == out_dir and path.exists():
                path.unlink()
        manifest_path = out_dir / "redaction_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"\nManifest: {manifest_path}")

    no_face = [e["input"] for e in manifest["images"] if e["status"] == "no_face_detected"]
    print(
        f"\nInputs: {len(images)}  unique: {len(unique)}  duplicate inputs skipped: {len(duplicates)}  "
        f"outputs written: {written}  errors: {len(manifest['errors'])}"
    )
    print("Inputs unchanged: yes")
    if duplicates:
        print("\nDuplicate source images (not written twice):")
        for dup, original in duplicates:
            print(f"  - {dup.name} == {original.name}")
    if no_face:
        print(f"\nWARNING - no face detected in {len(no_face)} image(s), review manually:")
        for name in no_face:
            print(f"  - {Path(name).name}")
    for err in manifest["errors"]:
        print(f"ERROR {Path(err['input']).name}: {err['error']}")

    return 2 if (no_face or manifest["errors"]) else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--model", default=str(DEFAULT_MODEL))
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--all", action="store_true", help="Process every image in the input folder")
    parser.add_argument("--conf", type=float, default=0.35, help="Face detection confidence threshold")
    parser.add_argument(
        "--min-kpt-conf",
        type=float,
        default=0.50,
        help="Minimum confidence for both eye landmarks before falling back to a proportional band",
    )
    parser.add_argument("--dry-run", action="store_true", help="Detect and report only; write nothing")
    parser.add_argument(
        "--confirm-batch",
        action="store_true",
        help="Required to process more than the review batch of 5 images",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(redact(parse_args()))
