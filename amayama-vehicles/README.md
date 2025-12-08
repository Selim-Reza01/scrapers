# Automotive Parts Catalog Deep Scraper for Amayama
A powerful multi-layer scraper for Amayama.com, built using Python, Selenium, Undetected ChromeDriver, Pandas, and OpenPyXL.  
This tool extracts complete part catalogs from selected product groups, including part numbers, product names, compatibility details, production periods, and status.  
Designed to handle large datasets, CAPTCHA interruptions, and deep multi-page navigation.

---

## 📌 Features
- Bypasses bot detection using Undetected ChromeDriver  
- Scrapes full parts catalog from chassis variation pages  
- Extracts:
  - Product Code
  - Product Name
  - Part Number
  - Chassis Compatibility
  - Production Period
  - Product Status
  - Product URL
- Handles multi-level navigation (chassis → product group → parts list)  
- Auto-splits Excel output when reaching large row limits  
- Supports manual CAPTCHA solving with safe pause detection  
- Random human-like delays to reduce anti-bot detection  
- Saves structured Excel output with consistent column ordering  

---

## 🛠 Tech Stack
- Python  
- Selenium  
- Undetected ChromeDriver  
- Pandas  
- OpenPyXL  
- CSS Selectors & Tag Parsing  

---

## 📂 How It Works
1. Loads vehicle and chassis data from an Excel file  
2. Visits each variation URL and detects allowed product groups  
3. Opens product schema pages and extracts all parts under each group  
4. Captures part numbers, product names, compatibility details, and production dates  
5. Automatically creates new Excel files when row limits are reached  
6. Saves final structured output as multiple `all_final_outputX.xlsx` files  

---

## ▶️ Installation & Usage

### Install Dependencies
```bash
pip install undetected-chromedriver selenium pandas openpyxl
