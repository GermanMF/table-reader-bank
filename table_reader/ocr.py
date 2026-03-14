"""
OCR utilities for table extraction (Tesseract wrappers and sign detection).
"""

import numpy as np
import pytesseract
from PIL import Image

from table_reader.constants import AMOUNT_CHAR_WHITELIST
from table_reader.lib.image import crop_cell_image, prepare_for_ocr

# Re-export for extraction module
__all__ = ["ocr_cell", "detect_sign_cell", "ocr_region", "AMOUNT_CHAR_WHITELIST"]


def ocr_cell(
    page_img: Image.Image,
    bbox: tuple[float, float, float, float],
    psm: int = 7,
    lang: str = "spa",
    char_whitelist: str | None = None,
) -> str:
    """OCR a single cell. PSM 7 = single line. char_whitelist improves digit accuracy."""
    cell_img = crop_cell_image(page_img, bbox)
    if cell_img is None:
        return ""
    cell_img = prepare_for_ocr(cell_img)
    config = f"--psm {psm} --oem 3"
    if char_whitelist:
        config += f" -c tessedit_char_whitelist={char_whitelist}"
    text = pytesseract.image_to_string(cell_img, lang=lang, config=config)
    return text.strip()


def detect_sign_cell(page_img: Image.Image, bbox: tuple[float, float, float, float]) -> str:
    """Detect +/- sign using pixel analysis in the inner region of the cell."""
    cell_img = crop_cell_image(page_img, bbox, pad=0)
    if cell_img is None:
        return "+"
    gray = cell_img.convert("L")
    w, h = gray.size
    if w < 6 or h < 6:
        return "+"
    margin_x = int(w * 0.20)
    margin_y = int(h * 0.20)
    inner = gray.crop((margin_x, margin_y, w - margin_x, h - margin_y))
    iw, ih = inner.size
    if iw < 3 or ih < 3:
        return "+"
    pixels = np.array(inner)
    dark_mask = pixels < 100
    dark_count = dark_mask.sum()
    if dark_count < 2:
        return "+"
    rows_with_dark = dark_mask.any(axis=1)
    dark_row_count = rows_with_dark.sum()
    vertical_coverage = dark_row_count / ih
    return "-" if vertical_coverage < 0.40 else "+"


def ocr_region(
    page_img: Image.Image, bbox: tuple[float, float, float, float], lang: str = "spa"
) -> str:
    """OCR a larger region (e.g. section header)."""
    cell_img = crop_cell_image(page_img, bbox, pad=4)
    if cell_img is None:
        return ""
    cell_img = prepare_for_ocr(cell_img, min_height=60)
    text = pytesseract.image_to_string(cell_img, lang=lang, config="--psm 6 --oem 3")
    return text.strip()
