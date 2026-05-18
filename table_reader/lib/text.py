"""
Text cleaning and date/month helpers for OCR output.
"""

import re

# Known month abbreviations (Spanish + OCR variants)
# The regex is used for a first-pass scan; normalize_month() handles fuzzy cleanup.
MONTHS_PATTERN = r"(?:Ene|Feb|Mar|Ab[a-z]*r|May|Jun|Jul|Ago|Sep|Oct|Nov|Dic)"
MONTH_MAP: dict[str, str] = {
    "Ene": "01", "Feb": "02", "Mar": "03", "Abr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Ago": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dic": "12",
}

# Fuzzy: maps any OCR variant (lowercased, all letters) to canonical abbreviation
_MONTH_FUZZY: dict[str, str] = {
    # April variants (Abr with extra chars)
    "abr": "Abr", "apr": "Abr", "apbr": "Abr", "abrp": "Abr", "abpr": "Abr",
    # January
    "ene": "Ene", "jan": "Ene", "enr": "Ene",
    # February
    "feb": "Feb", "febn": "Feb",
    # March
    "mar": "Mar",
    # May
    "may": "May",
    # June
    "jun": "Jun", "junn": "Jun",
    # July
    "jul": "Jul",
    # August
    "ago": "Ago", "aug": "Ago",
    # September
    "sep": "Sep", "sepp": "Sep",
    # October
    "oct": "Oct",
    # November
    "nov": "Nov",
    # December
    "dic": "Dic", "dec": "Dic",
}

# One optional minus, digits, optional decimal and fractional digits
NUMERIC_PATTERN = re.compile(r"-?[\d]+\.?\d*")


def normalize_month(raw: str) -> str:
    """
    Map a raw OCR month token (with possible extra chars) to a canonical
    Spanish abbreviation. Returns the original string if unrecognised.
    """
    key = re.sub(r"[^a-zA-Z]", "", raw).lower()
    return _MONTH_FUZZY.get(key, raw.capitalize()[:3])


def normalize_day(raw: str) -> str:
    """
    Strip non-digit trailing chars from a day token (e.g. '2/' → '2', '29p' → '29').
    Returns zero-padded 2-digit string.
    """
    digits = re.sub(r"[^\d]", "", raw)
    if not digits:
        return raw
    return digits.zfill(2)


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
