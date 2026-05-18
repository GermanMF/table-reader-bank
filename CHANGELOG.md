# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.0.0] - 2026-05-18

### Added
- **Tesseract Fine-Tuning Workflow:** Built an end-to-end dataset generation pipeline (`export_ground_truth.py` and `correct_ground_truth.py`) to extract cell images from PDFs and auto-correct OCR text for model training.
- **Advanced Reconciliation Strategies:** Added missing decimal point detection and mathematical outlier correction to robustly match statement totals when OCR digits are garbled.
- **OCR Constraints:** Added `AMOUNT_CHAR_WHITELIST` to Tesseract configuration for amount columns to aggressively filter out description text noise.
- **Fuzzy Date Parsing:** Introduced `normalize_month()` and `normalize_day()` to handle severe OCR noise (e.g. "Apbr") without brittle regex patches.
- **Centralized Documentation:** Consolidated all training workflows, guides, and lessons learned into a dedicated `docs/` folder.

### Fixed
- Stopped PDF footer summary totals ("Total de cargos") from leaking into transaction data.
- Fixed per-table footer reconciliation erroneously corrupting individual table data by prioritizing the exact `.env` expected totals.

## [2.0.0] - 2026-03-14

### Changed
- Refactored the entire project structure from a flat `utils/` script collection into a modular `table_reader` package.
- Modularized data cleaning, extraction, and export logic into dedicated sub-packages.
- Updated `main.py` to serve as a clean entry point leveraging the new package structure.
- Improved configuration management by separating constants and using a structured config approach.

### Added
- `pyproject.toml` for modern Python project management and dependency declaration.
- New library modules for image processing and text manipulation in `table_reader/lib`.
- Comprehensive `__init__.py` files to support package-level imports.

## [1.0.0] - 2026-02-22

### Added
- Core PDF table extraction from bank statements using Google Cloud Vision OCR.
- Data cleaning engine to normalize monetary values, remove OCR noise, and correct character misidentifications (e.g., '7' vs '/').
- Specific logic for categorizing "Meses sin intereses" (MSI) vs regular transactions.
- Dual export support for CSV and Excel formats.
- Configuration system via `.env` file support and `TABLE_NAME` structured references for Google Sheets.
- Automated date standardization (YYYY-MM-DD) and month abbreviation mapping.
- Multi-person expense summary generation logic.
- Initial README and project documentation.

