# Oilco.com.bd Category & Product Scraper
A full-category scraping system for Oilco.com.bd that extracts categories, product groups, item URLs, and detailed product information—including pricing, stock status, and product descriptions.  
Built using Selenium for dynamic scrolling, BeautifulSoup for parsing, and Pandas for exporting clean Excel output.

---

## 📌 Features
- Scrapes every category from the Oilco website  
- Extracts:
  - Category Name  
  - Product Group Name  
  - Product Title  
  - Price (discounted or regular)  
  - Stock Status  
  - Description  
  - “At A Glance” data  
  - Item URL  
- Detects **/all?** product pages automatically  
- Scroll-based infinite loading to fetch all items  
- Removes duplicate item URLs  
- Saves all collected data to a single Excel file (`scraped_data.xlsx`)  
- Live progress bars for item scraping  
- Handles missing titles, prices, and description gracefully  

---

## 🛠 Tech Stack
- Python  
- Selenium  
- BeautifulSoup (bs4)  
- Pandas  
- TQDM (progress bar)  
- Excel Output (xlsx)  
- CSS Selectors  

---

## 📂 How It Works
1. Loads **/category** page to fetch category names & URLs  
2. For each category:
   - Extracts product groups (links with `/all?`)  
3. Opens each product group page:
   - Scrolls repeatedly until no more items load  
   - Collects all item URLs  
4. For each item:
   - Extracts title, price, stock status  
   - Reads product description and AT-A-GLANCE section  
5. Saves all data into a unified Excel file  
6. Continues until all categories & their items are fully scraped  

---

## ▶️ Installation & Usage

### Install Dependencies
```bash
pip install selenium beautifulsoup4 pandas openpyxl tqdm
