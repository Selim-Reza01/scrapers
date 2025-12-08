# Molex Product Compliance PDF Generator Scraper  
A robust Selenium-based automation tool that downloads compliance PDFs from the **Molex Product Compliance** portal for a list of part numbers.  
The script handles browser restarts, download detection, renaming, retries, and logs all outcomes into Excel.

---

## 📌 Features
- Automates Molex Product Compliance page  
- Inputs part numbers from Excel  
- Auto-unchecks **RoHS** box for accurate results  
- Clicks **Generate PDF** and waits for download completion  
- Detects partial `.crdownload` or `.part` files and waits until they become full PDFs  
- Renames each file to `<part_number>.pdf`  
- Handles:
  - Browser failures  
  - Delay timeouts  
  - Restarted sessions  
  - Missing or failed downloads  
- Logs every part’s status (`success`, `fail`, `error`) into Excel  
- Allows manual page reload + cookie dismissal before each session  
- Ensures a clean download directory structure  

---

## 🛠 Tech Stack
- Python  
- Selenium WebDriver  
- Chrome Options (auto-download PDF)  
- Pandas  
- Excel Output  

---

## 📂 How It Works
1. Reads part numbers from `input_parts.xlsx`  
2. Opens Molex Product Compliance page  
3. You manually reload page + dismiss cookies  
4. For each part:
   - Inserts part number  
   - Unchecks RoHS  
   - Clicks **Generate PDF**  
   - Watches download directory for new PDF  
   - Renames file correctly  
5. If a part fails:
   - Browser restarts  
   - Script retries same part (max restarts allowed)  
6. Saves all logs to `download_log.xlsx`  

---

## ▶️ Installation & Usage

### Install dependencies
```bash
pip install selenium pandas openpyxl
