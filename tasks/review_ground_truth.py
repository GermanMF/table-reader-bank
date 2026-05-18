import os
import sys
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from PIL import Image, ImageTk

class GroundTruthReviewer:
    def __init__(self, master, gt_dir="tasks/ground_truth"):
        self.master = master
        self.master.title("Tesseract Ground Truth Reviewer")
        self.gt_dir = Path(gt_dir)
        
        if not self.gt_dir.exists():
            messagebox.showerror("Error", f"Directory {gt_dir} not found!")
            sys.exit(1)
            
        self.pairs = []
        for png_file in sorted(self.gt_dir.glob("*.png")):
            gt_file = png_file.with_suffix(".gt.txt")
            tif_file = png_file.with_suffix(".tif")
            if gt_file.exists():
                self.pairs.append((png_file, gt_file, tif_file))
                
        if not self.pairs:
            messagebox.showinfo("Done", "No files found to review.")
            sys.exit(0)
            
        self.current_idx = 0
        
        # UI Setup
        self.info_var = tk.StringVar()
        self.info_label = tk.Label(master, textvariable=self.info_var, font=("Arial", 12, "bold"))
        self.info_label.pack(pady=15)
        
        self.image_label = tk.Label(master, bg="grey", bd=2, relief="solid")
        self.image_label.pack(pady=10)
        
        self.text_var = tk.StringVar()
        self.entry = tk.Entry(master, textvariable=self.text_var, font=("Consolas", 24), width=30, justify="center")
        self.entry.pack(pady=20)
        self.entry.bind("<Return>", lambda e: self.next_pair())
        self.entry.bind("<Up>", lambda e: self.prev_pair())
        
        btn_frame = tk.Frame(master)
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="← Prev (Up Arrow)", command=self.prev_pair, width=15, font=("Arial", 11)).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Delete Pair", command=self.delete_pair, width=15, font=("Arial", 11), bg="#ffcccc").pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Save & Next (Enter) →", command=self.next_pair, width=25, font=("Arial", 11, "bold"), bg="#ccffcc").pack(side=tk.LEFT, padx=10)
        
        # Instructions
        instr = tk.Label(master, text="Focus the text box. Type the exact characters seen in the image.\nPress ENTER to save and advance. Press UP ARROW to go back.", fg="gray")
        instr.pack(side=tk.BOTTOM, pady=10)

        self.load_current()
        self.entry.focus_set()
        
    def load_current(self):
        if self.current_idx >= len(self.pairs):
            messagebox.showinfo("Done", "You have reviewed all files in the directory!")
            self.master.quit()
            return
            
        png_file, gt_file, _ = self.pairs[self.current_idx]
        
        self.info_var.set(f"File {self.current_idx + 1} of {len(self.pairs)}\n{png_file.name}")
        
        img = Image.open(png_file)
        # Scale up the image by 2.5x just for viewing so it's easier to read
        w, h = img.size
        img = img.resize((int(w * 2.5), int(h * 2.5)), Image.Resampling.NEAREST)
        
        self.photo = ImageTk.PhotoImage(img)
        self.image_label.config(image=self.photo)
        
        text = gt_file.read_text(encoding="utf-8").strip()
        self.text_var.set(text)
        self.entry.icursor(tk.END)
        self.entry.selection_range(0, tk.END)
        
    def save_current(self):
        png_file, gt_file, _ = self.pairs[self.current_idx]
        new_text = self.text_var.get().strip()
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
            messagebox.showinfo("Done", "No more files left.")
            self.master.quit()
        else:
            self.load_current()

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("700x450")
    # Center the window
    root.update_idletasks()
    x = (root.winfo_screenwidth() - 700) // 2
    y = (root.winfo_screenheight() - 450) // 2
    root.geometry(f"+{x}+{y}")
    
    app = GroundTruthReviewer(root)
    root.mainloop()
