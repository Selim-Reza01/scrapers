import os
from pathlib import Path

# Folder path
BASE_DIR = Path.cwd()
folder_path = BASE_DIR / "PDFs"

for filename in os.listdir(folder_path):
    if filename.endswith(".pdf") and filename.startswith("Statement_of_Compliance_PN_"):
        parts = filename.replace(".pdf", "").split("_")
        pn = parts[4]
        date = parts[5]
        new_name = f"TE Connectivity_{pn}_Statement of Compliance_{date}.pdf"
        old_path = os.path.join(folder_path, filename)
        new_path = os.path.join(folder_path, new_name)
        if os.path.exists(new_path):
            os.remove(old_path)
            print(f"Removed duplicate: {filename}")
        else:
            os.rename(old_path, new_path)
            print(f"Renamed: {filename}  -->  {new_name}")

print("All files processed! Duplicates removed and others renamed successfully.")