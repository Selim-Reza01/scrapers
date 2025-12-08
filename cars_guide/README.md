# CarsGuide Australia Car Listings Scraper  
A powerful anti-bot–resistant scraper for CarsGuide.com.au, built using **Python**, **Undetected ChromeDriver**, and **Selenium**.  
This tool extracts complete car listing data (pricing, specs, seller details, features) from multiple pages and saves everything into timestamped Excel files.

---

## 📌 Features
- Bypasses bot-detection using **Undetected ChromeDriver**
- Scrapes multiple pages of CarsGuide listings  
- Extracts:
  - Title / Model  
  - Discount & Regular Price  
  - Kilometers  
  - Body Type  
  - Transmission / Drive  
  - Fuel Type  
  - Dealer Status  
  - Location  
  - Full specification table  
  - Full feature list  
  - Seller phone number (via reveal button)  
  - Seller address  
  - Seller comments  
- Auto-scrolls lazy-loaded results  
- Handles popups, new-tabs, off-site redirects  
- Closes unwanted external domains  
- Random human-like delays to reduce detection  
- Saves clean Excel output with preferred column ordering  

---

## 🛠 Tech Stack
- Python  
- Undetected ChromeDriver  
- Selenium  
- XPath & CSS Selectors  
- Pandas  
- Excel Output  

---

## 📂 How It Works
1. Opens CarsGuide search pages  
2. Collects all listing URLs from each page  
3. For each listing:
   - Expands seller comments  
   - Reveals phone number  
   - Opens “See all details” section  
   - Parses full spec table  
   - Extracts features tab  
4. Saves everything as `carsguide_YYYYMMDD_HHMM.xlsx`

---

## ▶️ Installation & Usage

### Install dependencies
```bash
pip install undetected-chromedriver selenium pandas openpyxl lxml
