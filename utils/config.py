"""
Configuration loader for shared expense settings.
Reads from a .env file (or real environment variables).

Variables:
  PEOPLE         : comma-separated list of people labels (default: "Person1,Person2")
  SHARED_LABEL   : label for shared/both (default: "Los 2")
  MORTGAGE_TOTAL : total monthly mortgage amount (default: 26000)
  SPLITS         : comma-separated percentages matching PEOPLE (default: "50,50")
"""

import os

try:
    from dotenv import load_dotenv
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(_root, ".env"))
except ImportError:
    pass


# ── Exported constants ────────────────────────────────────────────
PEOPLE_RAW: str = os.getenv("PEOPLE", "Person1,Person2")
PEOPLE: list[str] = [p.strip() for p in PEOPLE_RAW.split(",") if p.strip()]

SHARED_LABEL: str = os.getenv("SHARED_LABEL", "Los 2")
MORTGAGE_TOTAL: float = float(os.getenv("MORTGAGE_TOTAL", "26000"))

SPLITS_RAW: str = os.getenv("SPLITS", "50,50")
_splits_list = [float(s.strip()) / 100.0 for s in SPLITS_RAW.split(",") if s.strip()]

# Validate splits length
if len(_splits_list) != len(PEOPLE):
    # fallback to even split
    n = len(PEOPLE)
    _splits_list = [1.0 / n] * n

SPLIT: dict[str, float] = {person: split for person, split in zip(PEOPLE, _splits_list)}
