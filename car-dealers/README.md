# AutoTrader UK Car Dealers Scraper
A robust Python scraper for AutoTrader.co.uk that collects car dealer names, profile URLs, and phone numbers directly from search result pages.  
Built using Selenium, Undetected ChromeDriver, and Pandas with per-page saving, lazy-load handling, and automatic deduplication.

---

## 📌 Features
- Scrapes multiple pages of AutoTrader dealer search results  
- Extracts:
  - Dealer Name  
  - Dealer Profile URL  
  - Phone Number (regex-based extraction)  
- Works in visible (non-headless) Chrome mode for stability  
- Accepts cookies automatically  
- Auto-scrolls page to load lazy content  
- Per-page save to CSV + Excel (safe progress even if interrupted)  
- Deduplicates by URL  
- Optional filter to scrape **only “Murley Auto Hyundai”**  
- Handles timeouts and unexpected HTML changes gracefully  

---

## 🛠 Tech Stack
- Python  
- Selenium  
- Undetected ChromeDriver  
- Pandas  
- Regular Expressions (phone detection)  
- CSS Selectors & XPath  
- Excel + CSV Output  

---

## 📂 How It Works
1. Loads AutoTrader dealer search pages (`page=1` to a specified end page)  
2. Accepts cookie popup and scrolls to force-render lazy content  
3. Identifies dealer cards via listing title anchor elements  
4. Extracts dealer name, URL, and phone number from card containers  
5. Saves results **after each page** into:  
   - `autotrader_dealers(10pages).csv`  
   - `autotrader_dealers(10pages).xlsx`  
6. Deduplicates by dealer URL and applies optional filtering  
7. Continues until all pages are completed and prints a final summary  

---

## ▶️ Installation & Usage

### Install Dependencies
```bash
pip install undetected-chromedriver selenium pandas openpyxl
