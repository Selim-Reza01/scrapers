# LoyalParts Transmission Category Scraper
A Selenium-based scraper for LoyalParts.com that extracts product types, product URLs, and detailed product data from the Transmission category.  
Supports manual scrolling for dynamic loading, handles nested product categories, and exports all collected product information to Excel.

---

## 📌 Features
- Scrapes all product types from the Transmission category  
- Extracts:
  - Product Type  
  - Product Title  
  - Price  
  - Product Information (description tab)  
  - Product URL  
- Automatically cleans product type names  
- Handles dynamic content with **manual scroll** for each category  
- Collects all unique product URLs from category pages  
- Per-category progress bar for product detail scraping  
- Appends results to a single Excel file (`transmission.xlsx`)  
- Highly stable for large numbers of products  

---

## 🛠 Tech Stack
- Python  
- Selenium  
- WebDriver Manager  
- Pandas  
- TQDM (progress bar)  
- Excel Output (xlsx)  
- CSS Selectors  

---

## 📂 How It Works
1. Loads the Transmission category on LoyalParts.com  
2. Detects all product types (categories) such as:
   - Gearboxes  
   - Transmission assemblies  
   - Clutch systems  
   - More subcategories  
3. For each product type:
   - Prompts user to scroll to load all items  
   - Collects all unique product URLs  
4. Visits each product URL and collects:
   - Title  
   - Price  
   - Product information (description tab)  
5. Saves all products for that product type into the Excel file  
6. Returns to the base page and repeats for the next product type  

---

## ▶️ Installation & Usage

### Install Dependencies
```bash
pip install selenium webdriver-manager pandas openpyxl tqdm
