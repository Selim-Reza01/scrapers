# MegaZip Parts Compatibility Scraper
A powerful Python scraper for MegaZip.net that checks part-number compatibility across vehicle models, chassis codes, engine types, and production years.  
This tool reads part numbers from Excel, queries MegaZip’s compatibility pages, extracts full application mappings, and exports them to a structured Excel file—along with a separate sheet for unmatched parts.

---

## 📌 Features
- Reads part numbers, product names, and brands from Excel  
- Scrapes compatibility data for each part using MegaZip search URLs  
- Extracts:
  - Product Name  
  - Brand  
  - Part Number  
  - Make  
  - Model  
  - Chassis Code  
  - Engine Model  
  - Engine Capacity  
  - Year Start / Year End  
  - Additional Details  
- Handles cases where:
  - No model is found  
  - Chassis is missing  
  - Engine model fields differ in structure  
- Uses multiple CSS selectors + regex to capture all variations  
- Manages:
  - 403 retry logic  
  - JavaScript-rendered data via alternate selectors  
  - Year range parsing with fallback detection  
- Separate Excel sheet for:
  - **Parts with no compatibility results**  
- Clean, structured Excel output appended on each run  

---

## 🛠 Tech Stack
- Python  
- Requests Session (optimized with retries)  
- BeautifulSoup  
- Pandas  
- Excel Output (xlsx)  
- Regex-based parsing  
- User-Agent header spoofing  

---

## 📂 How It Works
1. Loads input Excel (`megazip_input.xlsx`)  
2. Normalizes part numbers and builds search URLs  
3. Sends HTTP requests to MegaZip and parses:
   - Model list  
   - Chassis list  
   - Engine data  
   - Year ranges  
4. Follows nested URLs:
   - Part search page → Model page → Chassis page  
5. Extracts engine, year range, and vehicle applicability  
6. Saves results into `megazip_output.xlsx`:  
   - Main data sheet  
   - “No Model Found” sheet for unmatched entries  

---

## ▶️ Installation & Usage

### Install Dependencies
```bash
pip install requests beautifulsoup4 pandas openpyxl
