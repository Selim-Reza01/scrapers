# JapanParts Wiper Blade Scraper
A fast headless Selenium scraper for JapanParts.com.bd that collects product URLs from paginated category pages and extracts complete product details including title, price, product description, car application, and specification list.  
Designed for stability and accuracy using CSS selectors, JavaScript extraction, and duplicate URL filtering.

---

## 📌 Features
- Scrapes all products from the paginated Wiper Blade category  
- Extracts:
  - Product Title  
  - Price  
  - Product Details  
  - Car Application  
  - Specification List (key–value pairs)  
  - Product URL  
- Removes duplicate product links automatically  
- Uses JavaScript execution for hidden/JS-rendered product data  
- Headless Chrome mode for faster performance  
- Saves all results into Excel  
- Clear console logging for each page and product  

---

## 🛠 Tech Stack
- Python  
- Selenium  
- WebDriver Manager  
- JavaScript DOM Extraction  
- Pandas  
- Excel Output (xlsx)  
- CSS Selectors  

---

## 📂 How It Works
1. Opens paginated category pages (`?page=1`, `?page=2`, …)  
2. Collects all product URLs and removes duplicates  
3. For each product:
   - Extracts visible info (title, price, description)  
   - Uses JavaScript to extract *Car Application* and *Specification* data  
4. Stores each product in a structured list  
5. Saves everything to `japanparts_wipeer-blade.xlsx`  
6. Runs entirely in **headless mode** for speed  

---

## ▶️ Installation & Usage

### Install Dependencies
```bash
pip install selenium webdriver-manager pandas openpyxl
