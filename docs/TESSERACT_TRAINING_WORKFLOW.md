# Tesseract Training Workflow for Bank Statements

This guide explains the end-to-end process for fine-tuning Tesseract OCR. By following this, you teach Tesseract the exact fonts and layouts your bank uses, permanently eliminating OCR errors (like misreading `Abr` as `Apbr` or dropping decimals) without needing constant code patches.

## Directory Structure Overview
All documentation has been consolidated into this `docs/` folder.
- `docs/TESSERACT_TRAINING_WORKFLOW.md` - This guide.
- `docs/lessons.md` - Log of past bugs, OCR noise patterns, and logic fixes.
- `docs/*.pdf` - Place your raw bank statement PDFs here for processing.
- `tasks/` - Contains the Python scripts and generated ground truth data.

---

## 🚀 The Training Workflow (Next Steps)

Whenever you want to improve OCR accuracy or process a new statement, follow these 3 steps:

### Step 1: Export & Auto-Correct Ground Truth
Place your new PDF(s) in the `docs/` folder, then run the exporter script. This will extract all date and amount cells into images and auto-clean the text for Tesseract.

```bash
# In Git Bash, from the project root:
# 1. Clear old data (optional, only if starting fresh)
rm -rf tasks/ground_truth/*

# 2. Extract cell images and raw text from all PDFs
python tasks/export_ground_truth.py "docs/Estado de cuenta mayo.pdf" --out tasks/ground_truth

# 3. Auto-correct common OCR noise in the text files
python tasks/correct_ground_truth.py
```
*Note: `correct_ground_truth.py` automatically fixes hundreds of known issues (like `2/` -> `02`, missing decimals, border brackets) so you don't have to.*

### Step 2: Manual Review (Crucial!)
Tesseract learns from the `.gt.txt` (ground truth) files. If they are wrong, Tesseract learns the wrong thing.

1. Open the `tasks/ground_truth/` folder.
2. Look at the `.png` image previews.
3. Open the matching `.gt.txt` file and verify it perfectly matches the characters in the image.
4. Correct any remaining errors that the auto-script missed. Delete any pairs where the image is completely blank or unreadable.

**What to verify:**
- Dates must match the visual characters: `29-Abr-2026`
- Amounts must include the decimal: `811.35` (not `811351`)

### Step 3: Run Tesstrain
Now feed your corrected dataset to Tesseract to generate a new `.traineddata` model file.

```bash
# 1. Switch to the tesstrain directory
cd /l/gmart/Documents/Github/tesstrain

# 2. Run the training process
make training \
  MODEL_NAME=santander \
  START_MODEL=spa \
  TESSDATA="/c/Program Files/Tesseract-OCR/tessdata" \
  GROUND_TRUTH_DIR=/l/gmart/Documents/Github/table-reader-bank/tasks/ground_truth \
  LEARNING_RATE=0.0001 \
  MAX_ITERATIONS=400 \
  PSM=7
```
*(This takes ~5–15 minutes. It outputs `data/santander.traineddata`)*

### Step 4: Install & Use the Model
Copy the new trained model into Tesseract's system folder.

```bash
cp /l/gmart/Documents/Github/tesstrain/data/santander.traineddata \
   "/c/Program Files/Tesseract-OCR/tessdata/santander.traineddata"
```

The Python app is already configured to read from `.env`. Ensure your `.env` contains:
```env
TESSERACT_LANG=santander+spa
```
*(The system will use your custom `santander` model first, falling back to standard Spanish `spa` if needed).*

---

## 💡 Future Maintenance

The next time you get a new card statement:
1. Put the PDF in `docs/`.
2. Extract the ground truth (Step 1).
3. Review and correct the text (Step 2).
4. Run the training again (Step 3).

By continually adding to the dataset, your custom `santander` model will become incredibly accurate, making manual corrections obsolete.
