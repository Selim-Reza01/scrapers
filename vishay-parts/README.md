# Vishay Series Scraper (Playwright, Async, Multi-Threaded)
A high-performance asynchronous scraper built using **Python**, **Playwright**, and **pandas** to extract all *Quality* tab product data from Vishay series catalogue pages.  
The tool processes hundreds of series concurrently, navigates pagination, captures full quality tables, and exports complete structured Excel files.

---

## 📌 Features
- Scrapes all series/products under a Vishay list URL
- Async scraping with **8 concurrent workers** for high speed
- Extracts full *Quality* tab tables:
  - Part Number
  - RoHS Compliance
  - Lead-Free Status
  - MSL Level
  - Plating Finish
  - GREEN / Halogen-Free flags
  - Qualification
- Automatically builds *Quality Tab URLs*
- Extracts all paginated rows until last page
- Saves:
  - **All product rows sheet**
  - **Series List sheet** (unique series names/URLs)
- Status tracking file auto-updates after each input row
- Sanitized filenames for safe exporting
- Fully resilient with retry logic and cookie-banner handling

---

## 🛠 Tech Stack
- Python  
- Playwright (Async)  
- Pandas  
- Excel Output  
- Concurrency (Semaphore)  
- Robust retry + navigation handling  

---

## 📂 How It Works
1. Loads an input Excel sheet containing:  
   - Category  
   - Sub-Category  
   - List URL  
2. For each list URL:
   - Collects all **series URLs** with pagination  
   - Builds a `/tab/quality/` URL for each series  
   - Scrapes the complete quality table  
3. Aggregates all extracted rows  
4. Saves a timestamped Excel file containing:
   - **All Parts** sheet  
   - **Series List** sheet  
5. Updates a **status.xlsx** log of processed URLs  

---

## ▶️ Installation & Usage

### Install dependencies
```bash
pip install playwright pandas openpyxl
playwright install chromium
