# FitInParts Vehicle Compatibility Scraper  
A Python + Selenium-based web scraper that extracts **vehicle compatibility data**, **part details**, and **specifications** from FitInParts (fitinpart.sg) using a list of product part numbers.

---

## 📌 Features
- Automated search for each part number  
- Captcha detection + manual bypass support  
- Vehicle compatibility extraction (Make, Model, Year, Chassis, Engine Model, etc.)  
- Product specification extraction (Location, Position, Brand)  
- Saves results into clean Excel files:
  - `new_data.xlsx` → Found vehicle applications  
  - `not_found_new.xlsx` → Missing or invalid part numbers  
- Handles network delays, missing entries, and retry logic  
- BeautifulSoup used for HTML parsing  
- Selenium used for handling dynamic content  

---

## 🛠️ Tech Stack
- **Python**
- **Selenium WebDriver**
- **BeautifulSoup**
- **Pandas**
- **Chrome WebDriver**
- **Excel (xlsx) Output**

---

## 📂 How It Works
1. Load an Excel file containing:
   - `product_name`
   - `brand`
   - `part_number`
2. For each part number:
   - Program constructs the search URL  
   - Handles captcha (pauses until you solve it manually)  
   - Scrapes product details and vehicle list  
3. Stores:
   - Product brand  
   - Vehicle make/model  
   - Engine details  
   - Year, chassis, specifications  
4. Writes all data to Excel output files  

---

## ▶️ Running the Script

### **1. Install dependencies**
```bash
pip install selenium pandas beautifulsoup4 openpyxl
