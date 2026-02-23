"""
OCR utilities for table extraction.
"""

import numpy as np
import pytesseract
from PIL import Image, ImageFilter

SCALE = 300 / 72.0

def crop_cell_image(page_img: Image.Image, bbox: tuple, pad: int = 5) -> Image.Image:
    """Crop a cell region from the page image with padding."""
    x0 = max(0, int(bbox[0] * SCALE) - pad)
    top = max(0, int(bbox[1] * SCALE) - pad)
    x1 = min(page_img.width, int(bbox[2] * SCALE) + pad)
    bottom = min(page_img.height, int(bbox[3] * SCALE) + pad)
    if x1 <= x0 or bottom <= top:
        return None
    return page_img.crop((x0, top, x1, bottom))

def prepare_for_ocr(img: Image.Image, min_height: int = 50) -> Image.Image:
    """Upscale and sharpen an image for better OCR results."""
    w, h = img.size
    if h < min_height:
        factor = max(2, (min_height + h - 1) // h)
        img = img.resize((w * factor, h * factor), Image.LANCZOS)
    # Convert to grayscale and sharpen
    img = img.convert("L")
    img = img.filter(ImageFilter.SHARPEN)
    return img

def ocr_cell(page_img: Image.Image, bbox: tuple, psm: int = 7,
             lang: str = "spa") -> str:
    """OCR a single cell. PSM 7 = single line; PSM 6 = block of text."""
    cell_img = crop_cell_image(page_img, bbox)
    if cell_img is None:
        return ""
    cell_img = prepare_for_ocr(cell_img)
    text = pytesseract.image_to_string(
        cell_img, lang=lang,
        config=f"--psm {psm} --oem 3",
    )
    return text.strip()

def detect_sign_cell(page_img: Image.Image, bbox: tuple) -> str:
    """
    Detect +/- sign using pixel analysis in the inner region of the cell,
    excluding table border lines that surround each cell.
    """
    cell_img = crop_cell_image(page_img, bbox, pad=0)
    if cell_img is None:
        return "+"
    gray = cell_img.convert("L")
    w, h = gray.size
    if w < 6 or h < 6:
        return "+"

    # Crop to the inner 60% of the cell to exclude border lines
    margin_x = int(w * 0.20)
    margin_y = int(h * 0.20)
    inner = gray.crop((margin_x, margin_y, w - margin_x, h - margin_y))
    iw, ih = inner.size
    if iw < 3 or ih < 3:
        return "+"

    pixels = np.array(inner)

    # Threshold: dark pixels < 100 (catching dark glyphs, but not gray borders)
    dark_mask = pixels < 100
    dark_count = dark_mask.sum()

    if dark_count < 2:
        # Very few dark pixels — probably a '+' with thin strokes or empty
        return "+"

    # Check vertical coverage: a '-' has dark pixels in only a few rows (narrow band)
    # A '+' has dark pixels spread across many rows (vertical stroke)
    rows_with_dark = dark_mask.any(axis=1)
    dark_row_count = rows_with_dark.sum()

    # The '-' sign occupies a narrow horizontal band (< 40% of inner height)
    # The '+' sign has a vertical stroke spanning > 50% of inner height
    vertical_coverage = dark_row_count / ih

    if vertical_coverage < 0.40:
        return "-"
    else:
        return "+"


def ocr_region(page_img: Image.Image, bbox: tuple, lang: str = "spa") -> str:
    """OCR a larger region (e.g. section header)."""
    cell_img = crop_cell_image(page_img, bbox, pad=4)
    if cell_img is None:
        return ""
    cell_img = prepare_for_ocr(cell_img, min_height=60)
    text = pytesseract.image_to_string(
        cell_img, lang=lang,
        config="--psm 6 --oem 3",
    )
    return text.strip()
