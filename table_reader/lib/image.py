"""
Image cropping and preparation for OCR (pure helpers, no Tesseract).
"""

from PIL import Image, ImageFilter

# PDF points to pixels at 300 DPI (72 points per inch)
SCALE = 300 / 72.0


def crop_cell_image(
    page_img: Image.Image, bbox: tuple[float, float, float, float], pad: int = 5
) -> Image.Image | None:
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
        img = img.resize((w * factor, h * factor), Image.Resampling.LANCZOS)
    img = img.convert("L")
    img = img.filter(ImageFilter.SHARPEN)
    return img
