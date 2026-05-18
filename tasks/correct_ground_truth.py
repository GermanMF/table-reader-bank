import sys
import re
from pathlib import Path

def clean_gt_date(raw: str) -> str:
    # Remove border bleed artifacts
    cleaned = re.sub(r"[\[\]|\\]", "", raw).strip()
    
    # Fix common OCR month errors
    fuzzy_months = {
        "apbr": "Abr", "apr": "Abr", "abrp": "Abr", "abpr": "Abr",
        "ene": "Ene", "jan": "Ene", "enr": "Ene",
        "feb": "Feb", "febn": "Feb",
        "mar": "Mar", "may": "May",
        "jun": "Jun", "junn": "Jun",
        "jul": "Jul", "ago": "Ago", "aug": "Ago",
        "sep": "Sep", "sepp": "Sep",
        "oct": "Oct", "nov": "Nov", "dic": "Dic", "dec": "Dic"
    }
    
    # Extract parts
    match = re.search(r"(\d{1,2}[^\w\d-]*)-([a-zA-Z]+)-(\d{4})", cleaned, flags=re.IGNORECASE)
    if match:
        day_raw, month_raw, year = match.groups()
        day = re.sub(r"[^\d]", "", day_raw).zfill(2)
        month_key = re.sub(r"[^a-zA-Z]", "", month_raw).lower()
        month = fuzzy_months.get(month_key, month_raw.capitalize()[:3])
        return f"{day}-{month}-{year}"
        
    return cleaned

def clean_gt_amount(raw: str) -> str:
    # Remove $ and commas, spaces
    cleaned = re.sub(r"[$,\s]", "", raw)
    
    # If there's no dot but it's >= 4 digits, assume missing decimal
    if re.fullmatch(r"-?\d{4,}", cleaned):
        cleaned = cleaned[:-2] + "." + cleaned[-2:]
        
    return cleaned

def main():
    gt_dir = Path("tasks/ground_truth")
    if not gt_dir.exists():
        print("Ground truth directory not found.")
        return

    corrected_count = 0
    for gt_file in gt_dir.glob("*.gt.txt"):
        raw_text = gt_file.read_text(encoding="utf-8").strip()
        
        if "date" in gt_file.name:
            cleaned_text = clean_gt_date(raw_text)
        elif "amount" in gt_file.name:
            cleaned_text = clean_gt_amount(raw_text)
        else:
            cleaned_text = raw_text
            
        if cleaned_text != raw_text:
            print(f"Correcting {gt_file.name}: '{raw_text}' -> '{cleaned_text}'")
            gt_file.write_text(cleaned_text, encoding="utf-8")
            corrected_count += 1
            
    print(f"\nCorrected {corrected_count} files automatically.")

if __name__ == "__main__":
    main()
