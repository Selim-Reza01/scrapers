# Pearson Books Category Scraper
A Selenium-based scraper for Pearson.com that extracts all books from multiple academic categories, including title, author, edition, publication year, and book URLs.  
Supports full pagination handling, duplicate prevention, and detailed book metadata extraction.

---

## 📌 Features
- Reads categories & URLs from an Excel file (`pearson.xlsx`)  
- Scrapes:
  - Category  
  - Book Title  
  - Author  
  - Edition  
  - Publication Year  
  - Book URL  
- Handles fully paginated search results  
- Visits each book page to extract accurate title + publication year  
- Prevents duplicate records based on (Title + URL)  
- Saves all results into `output_books.xlsx`  
- Tracks and prints number of books found per category  

---

## 🛠 Tech Stack
- Python  
- Selenium  
- WebDriver Manager  
- BeautifulSoup (optional parsing)  
- Pandas  
- Excel Output (xlsx)  
- CSS Selectors  

---

## 📂 How It Works
1. Loads the category list from `pearson.xlsx`  
2. For each category:
   - Opens the URL  
   - Scrapes book items from the search results  
   - Extracts title, author, edition, and book link  
   - Follows pagination until no more pages exist  
3. Opens each book page:
   - Extracts final title and publication year  
4. Appends all validated results to the master Excel file  
5. Prints category totals and overall number of books scraped  

---

## ▶️ Installation & Usage

### Install Dependencies
```bash
pip install selenium webdriver-manager pandas openpyxl beautifulsoup4
