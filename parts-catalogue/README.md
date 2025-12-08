# Parts-Catalogs.com Multi-Threaded Groups & Schemas Scraper
A high-performance multi-threaded Selenium scraper designed to extract all **Group Schemas**, **Item Titles**, and **Item Detail URLs** from Parts-Catalogs.com.  
The script supports parallel workers, IP-block handling, popup blocks, “Show More” lazy loading, scrolling-based loading, and CSV export.

---

## 📌 Features
- Scrapes full category trees using:
  - Category URL  
  - 18 predefined Group Codes  
- Multi-threaded execution using **ThreadPoolExecutor**
- Each thread launches its own Chrome browser instance
- Disables images for extreme speed  
- Extracts:
  - Group Name + Code  
  - Group URL  
  - All item titles  
  - Item detail links  
- Handles:
  - Infinite scrolling lists  
  - Multiple “Show More” expansions  
  - Banners / popup variations  
  - Soft IP blocking → prompts for manual VPN change  
- Progress indicators with thread-safe counters
- Saves continuous partial progress to `output_1.csv`

---

## 🛠 Tech Stack
- Python  
- Selenium  
- ThreadPoolExecutor (multithreading)  
- Pandas  
- CSV output  

---

## 📂 How It Works
1. Loads `input_url.xlsx`:
