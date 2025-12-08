# Car Brands Scraper (CarLogos.org & Car.info)
A Python-based scraper that extracts car brand names from CarLogos.org and detailed brand information (name, founding year, origin country) from Car.info.  
Built using Selenium, WebDriver Manager, BeautifulSoup, and Pandas for clean, structured Excel output.

---

## 📌 Features
- Scrapes **all car brand names** from CarLogos.org (8 pages)
- Scrapes **brand name, year, and origin country** from Car.info
- Extracts:
  - Brand Name  
  - Founding Year  
  - Country of Origin  
- Uses Selenium for dynamic content rendering  
- Uses BeautifulSoup for precise HTML parsing  
- Saves results into an Excel file  
- Supports manual scroll on Car.info to load all brands  

---

## 🛠 Tech Stack
- Python  
- Selenium  
- WebDriver Manager  
- BeautifulSoup (bs4)  
- Pandas  
- Excel Output (xlsx)  
- CSS Selectors  

---

## 📂 How It Works
1. Opens CarLogos.org and loops through all 8 pages  
2. Extracts brand names from each logo card  
3. Opens Car.info brand page  
4. User scrolls until all brands are loaded  
5. Scraper collects brand name, founding year, and origin country  
6. Saves everything into `car_brands_info.xlsx`  

---

## ▶️ Installation & Usage

### Install Dependencies
```bash
pip install selenium webdriver-manager beautifulsoup4 pandas openpyxl
