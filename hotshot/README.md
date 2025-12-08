# HotShot Automotive Product Scraper
A Selenium-based scraper for HotShotAutomotive.com that collects product URLs from category pages and extracts product details such as title, price, stock status, and description.  
Designed with manual scrolling support, automated product-page extraction, and Excel export for clean structured data.

---

## 📌 Features
- Scrapes product listings from any HotShot Automotive product category  
- Extracts:
  - Category Name  
  - Product Title  
  - Price  
  - Stock Status  
  - Short Description  
  - Product URL  
- Requires simple **manual scroll** to load all items on long category pages  
- Progress bar for product detail scraping  
- Automatically saves the dataset into Excel  
- Clean, unique product URL collection using set-based filtering  
- Solid fallback handling for missing descriptions  

---

## 🛠 Tech Stack
- Python  
- Selenium  
- WebDriver Manager  
- BeautifulSoup (optional HTML parsing structure)  
- Pandas  
- Excel Output (xlsx)  
- CSS Selectors  

---

## 📂 How It Works
1. Opens a HotShot Automotive category page  
2. Waits for user to scroll to the bottom (ensures all products load)  
3. Collects all product URLs containing `/product/`  
4. Visits each product page and extracts:
   - Title  
   - Price  
   - Stock Status  
   - Description  
   - URL  
5. Saves all scraped products into `categoryname_products.xlsx`  
6. Closes the browser at completion  

---

## ▶️ Installation & Usage

### Install Dependencies
```bash
pip install selenium webdriver-manager pandas openpyxl tqdm
