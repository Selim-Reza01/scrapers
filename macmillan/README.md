# Macmillan Learning Book Scraper
A Python scraper for MacmillanLearning.com that collects textbook details across multiple academic disciplines.  
This tool reads discipline URLs from Excel, extracts all book links, and captures book metadata including title, authors, edition, and publication year.

---

## 📌 Features
- Loads discipline names & URLs from `macmillian.xlsx`  
- Scrapes:
  - Discipline  
  - Book Title  
  - Author(s)  
  - Publication Year  
  - Edition  
  - Book URL  
- Automatically removes duplicate book URLs  
- Handles Macmillan's custom HTML structure for author & edition extraction  
- Graceful error handling for failed pages  
- Saves consolidated results into `book_scrapings.xlsx`  

---

## 🛠 Tech Stack
- Python  
- Requests  
- BeautifulSoup (bs4)  
- Pandas  
- Excel Output (xlsx)  
- HTML parsing with CSS selectors  

---

## 📂 How It Works
1. Reads an input Excel file containing:
   - Discipline name  
   - URL for that discipline’s textbook listings  
2. For each discipline:
   - Requests the listing page  
   - Extracts all book links  
   - Filters out unwanted `#authors` anchors  
3. For each book:
   - Loads product page  
   - Extracts title, author(s), edition, and publication year  
4. Collects all results into one DataFrame  
5. Saves everything into a clean Excel file  

---

## ▶️ Installation & Usage

### Install Dependencies
```bash
pip install requests beautifulsoup4 pandas openpyxl
