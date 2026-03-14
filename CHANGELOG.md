# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

