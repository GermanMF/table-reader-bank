#!/usr/bin/env python3
"""
Ground Truth Exporter for Tesseract Fine-Tuning
================================================
Renders every date and amount cell from a bank statement PDF and saves them
as TIFF + ground truth text pairs ready for `tesstrain`.

Usage:
    python tasks/export_ground_truth.py "Estado de cuenta mayo.pdf"
    python tasks/export_ground_truth.py "Estado de cuenta mayo.pdf" --out tasks/ground_truth

After running:
  1. Open tasks/ground_truth/ and review the PNG previews alongside the .gt.txt files.
  2. Correct any wrong .gt.txt files (these are the ground truth labels Tesseract learns from).
  3. Run tesstrain (see tasks/TRAINING.md for exact commands).

Output structure:
    tasks/ground_truth/
        page1_t0_r5_c0_date.tif      <- cell image (TIFF, required by tesstrain)
        page1_t0_r5_c0_date.gt.txt   <- correct text for that cell
        page1_t0_r5_c0_date.png      <- visual preview (for you to inspect)
        ...
"""

import argparse
import re
import sys
from pathlib import Path

import pdfplumber
import pytesseract
from PIL import Image

# Make sure we can import the project's own modules regardless of CWD
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from table_reader.constants import RENDER_DPI
from table_reader.lib.image import crop_cell_image, prepare_for_ocr, SCALE
from table_reader.data_cleaning import classify_table
from table_reader.ocr import ocr_region


# ── Helpers ─────────────────────────────────────────────────────────────────

def _ocr_best_guess(cell_img: Image.Image, psm: int = 7, lang: str = "spa") -> str:
    """OCR a prepared cell image and return the raw best-guess string."""
    config = f"--psm {psm} --oem 3"
    return pytesseract.image_to_string(cell_img, lang=lang, config=config).strip()


def _save_pair(cell_img: Image.Image, gt_text: str, base_path: Path) -> None:
    """Save TIFF + gt.txt pair (and PNG preview) for one cell."""
    # tesstrain requires TIFF
    tif_path = base_path.with_suffix(".tif")
    gt_path = base_path.with_suffix(".gt.txt")
    png_path = base_path.with_suffix(".png")

    cell_img.save(tif_path, format="TIFF")
    cell_img.save(png_path, format="PNG")
    gt_path.write_text(gt_text, encoding="utf-8")


def _segment_header(page_img: Image.Image, table) -> str:
    """Return OCR header text for the first merged-cell row(s)."""
    text = ""
    for row in table.rows:
        non_none = [c for c in row.cells if c is not None]
        if len(non_none) <= 1:
            if non_none:
                text += " " + ocr_region(page_img, non_none[0])
        else:
            break
    return text


# ── Main export ─────────────────────────────────────────────────────────────

def export_ground_truth(pdf_path: Path, out_dir: Path) -> int:
    """
    Extract cell images from all regular-table date and amount columns.
    Returns count of pairs written.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    table_settings = {"vertical_strategy": "lines", "horizontal_strategy": "lines"}

    total = 0
    with pdfplumber.open(pdf_path) as pdf:
        doc_name = pdf_path.stem.replace(" ", "_")
        for pi, page in enumerate(pdf.pages):
            page_img = page.to_image(resolution=RENDER_DPI).original
            print(f"  Page {pi + 1}: rendering…")

            for ti, table in enumerate(page.find_tables(table_settings)):
                header = _segment_header(page_img, table)
                category, _ = classify_table(header)
                if category != "regular":
                    continue  # skip MSI and unknown tables

                data_start = 0
                for ri, row in enumerate(table.rows):
                    non_none = [c for c in row.cells if c is not None]
                    if len(non_none) <= 1:
                        data_start = ri + 1
                    else:
                        break

                for ri, row in enumerate(table.rows[data_start:], start=data_start):
                    cells = row.cells
                    if len([c for c in cells if c is not None]) < 3:
                        continue

                    # We care about cols 0 (date1), 1 (date2), and 4 (amount)
                    for ci, label in [(0, "date1"), (1, "date2"), (4, "amount")]:
                        if ci >= len(cells) or cells[ci] is None:
                            continue
                        
                        cell = cells[ci]
                        # Defensive check: ensure cell is a valid bounding box
                        if not isinstance(cell, (tuple, list)) or len(cell) < 4:
                            continue
                        if cell[0] is None or cell[2] is None or cell[1] is None or cell[3] is None:
                            continue

                        cell_width = cell[2] - cell[0]
                        if cell_width < 15:
                            continue

                        raw = crop_cell_image(page_img, cell)
                        if raw is None:
                            continue
                        prepared = prepare_for_ocr(raw)

                        # For amounts, restrict OCR chars
                        if label == "amount":
                            guess = pytesseract.image_to_string(
                                prepared, lang="spa",
                                config="--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789.,$- "
                            ).strip()
                        else:
                            guess = _ocr_best_guess(prepared)

                        stem = f"{doc_name}_p{pi+1}_t{ti}_r{ri}_c{ci}_{label}"
                        base = out_dir / stem
                        _save_pair(prepared, guess, base)
                        total += 1

    return total


# ── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export date/amount cell images + ground truth text for Tesseract training"
    )
    parser.add_argument("pdf_path", help="Bank statement PDF")
    parser.add_argument(
        "--out", "-o",
        default="tasks/ground_truth",
        help="Output directory (default: tasks/ground_truth)",
    )
    args = parser.parse_args()

    pdf = Path(args.pdf_path)
    if not pdf.exists():
        print(f"❌ File not found: {pdf}")
        sys.exit(1)

    out = Path(args.out)
    print(f"📄 Processing: {pdf}")
    print(f"📁 Output dir: {out.resolve()}")

    n = export_ground_truth(pdf, out)
    print(f"\n✅ Exported {n} cell pairs to: {out.resolve()}")
    print("\nNext steps:")
    print("  1. Open the folder and review each .png + its .gt.txt")
    print("  2. Fix any wrong .gt.txt files (these are what Tesseract learns)")
    print("  3. Run: python tasks/correct_ground_truth.py")
    print("  4. See docs/TESSERACT_TRAINING_WORKFLOW.md for tesstrain commands")

if __name__ == "__main__":
    main()
