import sys
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, 
                             QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox)
from PyQt6.QtGui import QPixmap, QImage, QFont
from PyQt6.QtCore import Qt

class GroundTruthReviewer(QWidget):
    def __init__(self, gt_dir="tasks/ground_truth"):
        super().__init__()
        self.setWindowTitle("Tesseract Ground Truth Reviewer")
        self.resize(700, 450)
        self.gt_dir = Path(gt_dir)
        
        if not self.gt_dir.exists():
            QMessageBox.critical(self, "Error", f"Directory {gt_dir} not found!")
            sys.exit(1)
            
        self.pairs = []
        for png_file in sorted(self.gt_dir.glob("*.png")):
            gt_file = png_file.with_suffix(".gt.txt")
            tif_file = png_file.with_suffix(".tif")
            if gt_file.exists():
                self.pairs.append((png_file, gt_file, tif_file))
                
        if not self.pairs:
            QMessageBox.information(self, "Done", "No files found to review.")
            sys.exit(0)
            
        self.current_idx = 0
        
        # UI Setup
        layout = QVBoxLayout()
        
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(self.info_label)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: grey; border: 2px solid black;")
        layout.addWidget(self.image_label)
        
        self.entry = QLineEdit()
        self.entry.setFont(QFont("Consolas", 24))
        self.entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.entry.returnPressed.connect(self.next_pair)
        layout.addWidget(self.entry)
        
        btn_layout = QHBoxLayout()
        
        self.btn_prev = QPushButton("← Prev (Up Arrow)")
        self.btn_prev.setFont(QFont("Arial", 11))
        self.btn_prev.clicked.connect(self.prev_pair)
        btn_layout.addWidget(self.btn_prev)
        
        self.btn_delete = QPushButton("Delete Pair")
        self.btn_delete.setFont(QFont("Arial", 11))
        self.btn_delete.setStyleSheet("background-color: #ffcccc;")
        self.btn_delete.clicked.connect(self.delete_pair)
        btn_layout.addWidget(self.btn_delete)
        
        self.btn_next = QPushButton("Save & Next (Enter) →")
        self.btn_next.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.btn_next.setStyleSheet("background-color: #ccffcc;")
        self.btn_next.clicked.connect(self.next_pair)
        btn_layout.addWidget(self.btn_next)
        
        layout.addLayout(btn_layout)
        
        instr = QLabel("Focus the text box. Type the exact characters seen in the image.\nPress ENTER to save and advance. Press UP ARROW to go back.")
        instr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instr.setStyleSheet("color: gray;")
        layout.addWidget(instr)
        
        self.setLayout(layout)
        self.load_current()
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Up:
            self.prev_pair()
        else:
            super().keyPressEvent(event)
            
    def load_current(self):
        if self.current_idx >= len(self.pairs):
            QMessageBox.information(self, "Done", "You have reviewed all files in the directory!")
            self.close()
            return
            
        png_file, gt_file, _ = self.pairs[self.current_idx]
        
        self.info_label.setText(f"File {self.current_idx + 1} of {len(self.pairs)}\n{png_file.name}")
        
        pixmap = QPixmap(str(png_file))
        # Scale up the image by 2.5x
        scaled_pixmap = pixmap.scaled(int(pixmap.width() * 2.5), int(pixmap.height() * 2.5), 
                                      Qt.AspectRatioMode.KeepAspectRatio, 
                                      Qt.TransformationMode.FastTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        
        text = gt_file.read_text(encoding="utf-8").strip()
        self.entry.setText(text)
        self.entry.selectAll()
        self.entry.setFocus()
        
    def save_current(self):
        png_file, gt_file, _ = self.pairs[self.current_idx]
        new_text = self.entry.text().strip()
        gt_file.write_text(new_text, encoding="utf-8")
        
    def next_pair(self):
        self.save_current()
        self.current_idx += 1
        self.load_current()
        
    def prev_pair(self):
        self.save_current()
        if self.current_idx > 0:
            self.current_idx -= 1
            self.load_current()
            
    def delete_pair(self):
        png_file, gt_file, tif_file = self.pairs[self.current_idx]
        if png_file.exists(): png_file.unlink()
        if gt_file.exists(): gt_file.unlink()
        if tif_file.exists(): tif_file.unlink()
        
        del self.pairs[self.current_idx]
        if self.current_idx >= len(self.pairs):
            self.current_idx -= 1
            
        if self.current_idx < 0:
            QMessageBox.information(self, "Done", "No more files left.")
            self.close()
        else:
            self.load_current()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GroundTruthReviewer()
    window.show()
    sys.exit(app.exec())
