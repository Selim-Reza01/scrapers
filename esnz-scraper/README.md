# ESNZ Horse Lookup Scraper (HorseReg.com)
A fully automated Python scraper for extracting horse registration details from the ESNZ Horse Lookup directory on HorseReg.com.  
Built using **Selenium**, **ChromeDriverManager**, and **Pandas**, this scraper processes 1600+ pages and exports clean structured data into Excel.

---

## 📌 Features
- Extracts complete horse profiles including:
  - Horse Name
  - Registration details
  - Microchip information
  - Breed, Color, DOB
  - Owner / Rider info
  - Discipline groups & registration blocks
- Automatically detects **"Jumping & Show Hunter Horse"** status  
- Handles duplicate keys in registration blocks
- Saves results **after every page** to avoid data loss
- Supports manual login before scraping
- Exports results to `horse_scraped_data.xlsx`

---

## 🛠 Tech Stack
- Python  
- Selenium WebDriver  
- WebDriver Manager  
- ChromeOptions (anti-detection tuning)  
- Pandas  
- Excel output  

---

## 📂 How It Works
1. Script opens HorseReg.com Horse Lookup page  
2. You manually log in  
3. Scraper loops through **all 1600+ pages**  
4. Extracts each horse card on the page  
5. Saves extracted data into Excel after each page  
6. Continues until all pages are scraped  

---

## ▶️ Running the Script

### **Install dependencies**
```bash
pip install selenium webdriver-manager pandas openpyxl
