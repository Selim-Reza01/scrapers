# Goo-Net Catalog Scraper  
A Python-based scraper that extracts all vehicle specifications from Goo-Net Exchange (Japan).  
The scraper collects catalog entries, follows each model detail page, and extracts complete technical specifications including engine, drivetrain, suspension, dimensions, and pricing.

---

## 📌 Features
- Scrapes all entries from Goo-Net Exchange  
- Extracts:
  - Sale year
  - Model type
  - Transmission / Drive type
  - Weight & MSRP
  - Engine specs (power, displacement, torque, cylinders)
  - Drivetrain details (gear ratios, final drive)
  - Suspension & brake specs
  - Dimensions & body details
- Gathers clean structured data from every detail page
- Exports a fully organized CSV file  
- Includes polite request delays to avoid blocks

---

## 🛠 Tech Stack
- Python  
- Requests  
- BeautifulSoup  
- CSV Output  
- Regex Parsing  
- Goo-Net Catalog Scraping

---

## 📂 How It Works
1. Loads catalog page  
2. Extracts all listed models with:
   - model type  
   - detail page URL  
   - transmission  
   - weight  
   - msrp  
3. Visits each detail page and scrapes:
   - Engine specs  
   - Drivetrain specs  
   - Suspension  
   - Dimensions  
   - General specifications  
4. Saves all rows to `japan_toyota_86.csv`

---

## ▶️ Installation & Usage

### Install dependencies
```bash
pip install requests beautifulsoup4
