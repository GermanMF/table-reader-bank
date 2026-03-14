"""
Configuration loader for shared expense settings.
Reads from a .env file (or real environment variables).

Variables:
  PEOPLE                    : comma-separated list of people labels
  SHARED_LABEL              : label for shared/both (default: "Los 2")
  MORTGAGE_TOTAL            : total monthly mortgage amount
  SPLITS                    : comma-separated percentages matching PEOPLE
  TABLE_NAME                : name of the table range in Google Sheets
  EXPECTED_NOAMESES_CARGOS  : optional; validate No a Meses Cargos sum
  EXPECTED_NOAMESES_ABONOS   : optional; validate No a Meses Abonos sum
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    _root = Path(__file__).resolve().parent.parent
    load_dotenv(_root / ".env")
except ImportError:
    pass


# ── Exported constants ────────────────────────────────────────────
PEOPLE_RAW: str = os.getenv("PEOPLE", "Person1,Person2")
PEOPLE: list[str] = [p.strip() for p in PEOPLE_RAW.split(",") if p.strip()]

SHARED_LABEL: str = os.getenv("SHARED_LABEL", "Los 2")
MORTGAGE_TOTAL: float = float(os.getenv("MORTGAGE_TOTAL", "26000"))
TABLE_NAME: str = os.getenv("TABLE_NAME", "Transacciones_Banco_Enero_Febrero")

SPLITS_RAW: str = os.getenv("SPLITS", "50,50")
_splits_list = [float(s.strip()) / 100.0 for s in SPLITS_RAW.split(",") if s.strip()]

if len(_splits_list) != len(PEOPLE):
    n = len(PEOPLE)
    _splits_list = [1.0 / n] * n

SPLIT: dict[str, float] = {person: split for person, split in zip(PEOPLE, _splits_list)}

_exp_c = os.getenv("EXPECTED_NOAMESES_CARGOS", "").strip()
_exp_a = os.getenv("EXPECTED_NOAMESES_ABONOS", "").strip()
EXPECTED_NOAMESES_CARGOS: float | None = float(_exp_c) if _exp_c else None
EXPECTED_NOAMESES_ABONOS: float | None = float(_exp_a) if _exp_a else None
