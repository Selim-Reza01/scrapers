# HostMilano Exhibitors Scraper
A powerful and fully automated scraper for HostMilano (Fiera Milano) exhibitors, built using Python, Selenium, WebDriver Manager, BeautifulSoup, and Pandas.  
This tool extracts full exhibitor profiles—including company details, pavilion/stand, contact information, sectors, and categories—and saves everything into CSV and Excel files with incremental updates.

---

## 📌 Features
- Scrapes exhibitors from the dynamic HostMilano exhibitor directory  
- Supports both:
  - Full-range scraping (index 1 → end)
  - Specific index scraping (manual-assisted mode)  
- Extracts:
  - Index  
  - Company Name  
  - Pavilion / Stand  
  - Country  
  - Website  
  - Email  
  - Phone  
  - Sectors  
  - Categories (multi-level hierarchy)  
  - Detail Source URL  
- Auto-scrolls to load tiles dynamically  
- Handles stale elements, scroll issues, and delayed loading  
- Robust click fallback system + retry logic  
- Auto-appends to CSV and Excel after each record  
- Manual assistance mode for difficult indices  
- Highly stable for long runs (thousands of exhibitors)

---

## 🛠 Tech Stack
- Python  
- Selenium  
- WebDriver Manager  
- BeautifulSoup (HTML parsing)  
- Pandas  
- CSV + Excel Output  
- CSS Selectors & XPath  

---

## 📂 How It Works
1. Loads the HostMilano exhibitors page  
2. Scrolls until all tiles up to the target index are visible  
3. Opens each exhibitor tile via robust click logic  
4. Extracts exhibitor details:
   - Company and pavilion  
   - Full contact information  
   - Sectors and categories (nested groups)  
5. Saves each record immediately into both:
   - `hostmilano_exhibitors.csv`  
   - `hostmilano_exhibitors.xlsx`  
6. Closes the detail popup and continues to next exhibitor  
7. Optional "manual mode" highlights the tile for user click when automation fails  

---

## ▶️ Installation & Usage

### Install Dependencies
```bash
pip install selenium webdriver-manager beautifulsoup4 pandas openpyxl
