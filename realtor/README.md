# Realtor.com Real Estate Scraper  
Automated Python scraper for extracting real estate listing details from Realtor.com across multiple counties.  
Built using **Undetected ChromeDriver**, **Selenium**, **Pandas**, and advanced anti-detection techniques.

---

## 📌 Features
- Scrapes multiple county listing pages automatically  
- Uses **Undetected ChromeDriver** to bypass bot detection  
- Auto-scrolls full pages to load all listings  
- Extracts:
  - Price  
  - Listing Agent / Broker  
  - Sewer Type  
  - Water Source  
  - Property details (expanded automatically)
- Captures every listing URL across paginated results  
- Tracks previously scraped URLs using `Reference.xlsx`  
- Classifies listings into:
  - **Valid Listings** → septic/well water  
  - **Other Listings** → all others  
- Saves results into two Excel files:
  - `YYYY-MM-DD_valid_listing.xlsx`  
  - `YYYY-MM-DD_other_listing.xlsx`

---

## 🛠 Tech Stack
- Python  
- Undetected ChromeDriver  
- Selenium  
- XPath automation  
- Pandas  
- Excel output  

---

## 📂 How It Works
1. Loads **input counties** with URLs  
2. Starts a bot-detection-resistant ChromeDriver  
3. Scans every page → extracts listing URLs  
4. For each listing:
   - Auto expands “Property details”  
   - Extracts utilities (sewer, water)  
   - Extracts listing/broker information  
5. Writes results into Excel in real time  
6. Tracks previously scraped URLs to avoid duplicates  

---

## ▶️ Running the Script

### **Install dependencies**
```bash
pip install undetected-chromedriver selenium pandas openpyxl
