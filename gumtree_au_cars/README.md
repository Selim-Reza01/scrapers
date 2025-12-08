# Gumtree Daily Car Listings Scraper  
A fully automated Gumtree car listings scraper built with **Python**, **Undetected ChromeDriver**, **Selenium**, and **lxml**.  
This scraper runs through multiple Gumtree search URLs (AU states), handles anti-bot detection, scrolls dynamically, extracts listings, prevents duplicates, and saves daily results into a structured Excel file.

---

## 📌 Features
- Scrapes multiple Gumtree car listing URLs across different Australian states
- Uses **Undetected ChromeDriver** to bypass bot detection
- Auto-scrolls randomly to simulate human behavior
- Handles:
  - Rate limiting / 429 errors
  - “Access Denied” pages
  - Browser restarts after failures
- Extracts:
  - Title  
  - Price  
  - Description  
  - Listing URL  
  - Timestamp  
- Prevents duplicates using Excel-based URL comparison
- Supports early exit if multiple pages contain no new data
- Saves output into a **daily Excel file (YYYY-MM-DD.xlsx)**

---

## 🛠 Tech Stack
- Python  
- Undetected ChromeDriver  
- Selenium  
- lxml  
- Pandas  
- Excel Output  

---

## 📂 How It Works
1. Loads a predefined list of Gumtree search URLs  
2. Launches an anti-detection Chrome browser  
3. For each URL:
   - Determines total number of pages  
   - Extracts listing cards using XPath  
   - Scrolls randomly to load content  
   - Handles blocks, cooldowns, and browser restarts  
4. Deduplicates results by URL  
5. Saves new data immediately page-by-page  
6. Moves to the next region when no new items are found  

---

## ▶️ Installation & Usage

### Install packages
```bash
pip install undetected-chromedriver selenium lxml pandas openpyxl
