"""
Text cleaning and date/month helpers for OCR output.
"""

import re

# Known month abbreviations (Spanish + OCR variants)
MONTHS_PATTERN = r"(?:Ene|Feb|Mar|Abr|May|Jun|Jul|Ago|Sep|Oct|Nov|Dic)"
MONTH_MAP: dict[str, str] = {
    "Ene": "01", "Feb": "02", "Mar": "03", "Abr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Ago": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dic": "12",
}

# One optional minus, digits, optional decimal and fractional digits
NUMERIC_PATTERN = re.compile(r"-?[\d]+\.?\d*")


def looks_numeric(s: str) -> bool:
    """Return True if s contains a numeric substring (amount/number)."""
    return bool(NUMERIC_PATTERN.search(s)) if s else False


def first_number(s: str) -> str:
    """Return first numeric substring in s, or s if none."""
    match = NUMERIC_PATTERN.search(s)
    return match.group() if match else s


def sanitize_ocr(raw: str) -> str:
    """Strip common border-bleed artefacts and normalise whitespace."""
    cleaned = re.sub(r"[\[\]|\\]", " ", raw)
    cleaned = " ".join(cleaned.split())
    cleaned = re.sub(r"(\d)/$", r"\g<1>7", cleaned)
    cleaned = re.sub(r"(\d)/(\d)", r"\g<1>7\2", cleaned)
    return cleaned.strip()
