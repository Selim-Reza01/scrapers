# Wiley Books Scraper (Field + Subject Based)
A robust Requests + BeautifulSoup scraper for Wiley.com that extracts book information across multiple academic fields and subjects.  
Reads scraping instructions from Excel, scans every paginated results page, and exports clean structured book metadata to Excel.

---

## 📌 Features
- Reads **Field**, **Subject**, **URL**, and **Total Pages** from an Excel file  
- Scrapes:
  - Field  
  - Subject  
  - Title  
  - Author(s)  
  - Edition  
  - Year (parsed from edition string)  
  - Publisher (Wiley)  
  - Book URL  
- Handles pagination for each subject  
- Auto-builds full URLs for books missing `https`  
- Rate-limiting protection with controlled delays  
- Saves all results into a single Excel file (`willey_books_psychology.xlsx`)  
- Clean parsing with BeautifulSoup for accurate data extraction  

---

## 🛠 Tech Stack
- Python  
- Requests  
- BeautifulSoup (bs4)  
- Pandas  
- Excel Output (xlsx)  

---

## 📂 How It Works
1. Loads input file: `willey.xlsx`  
2. For each row:
   - Reads Field, Subject, Base URL, and Total Pages  
   - Iterates through all listing pages  
3. On each page:
   - Detects all book cards  
   - Extracts title, author, edition, and year  
   - Normalizes and completes book URLs  
4. Appends all scraped book data into a master list  
5. Saves final structured results to Excel  

---

## ▶️ Installation & Usage

### Install Dependencies
```bash
pip install requests beautifulsoup4 pandas openpyxl
