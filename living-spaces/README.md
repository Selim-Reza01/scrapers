# LivingSpaces Product URL & Variant Collector
A high-performance URL collector for LivingSpaces.com that scans listing pages, extracts all product URLs, detects variant URLs (size/color versions), and exports organized Excel files.  
Built using httpx (HTTP/2), BeautifulSoup, Python concurrency, retry logic, and clean Excel output generation.

---

## 📌 Features
- Scrapes **155 listing pages** (or any configured range)
- Extracts:
  - Main product URLs  
  - Variant URLs from product detail pages  
- Parallel fetching of product pages using `ThreadPoolExecutor`  
- HTTP/2 + keep-alive via **httpx.Client** for maximum speed  
- Random User-Agent rotation  
- Intelligent retry mechanism for:
  - 403  
  - 429  
  - 503  
  - Timeouts  
- Detailed page summary (count per page → totals)  
- Outputs 3 Excel files:
  1. `listing_urls_by_page.xlsx` — main URLs only  
  2. `all_urls_with_variants.xlsx` — main + variant URLs (flattened)  
  3. `page_summary.xlsx` — per-page counts + SUM row  
- Strict ordering, unique filtering for main URLs, variant flattening without dedupe  
- Fully automated and extremely fast

---

## 🛠 Tech Stack
- Python  
- httpx (HTTP/2 client)  
- BeautifulSoup  
- ThreadPoolExecutor (parallel scraping)  
- Pandas  
- Excel Export (xlsx)  
- Random User-Agent Pool  
- Retry + Backoff logic  

---

## 📂 How It Works
1. Loads a page from LivingSpaces (dynamic page number)  
2. Extracts all product URLs from listing cards  
3. For each product:
   - Fetches product page  
   - Finds variant URLs from the “Other Sizes” section  
4. Flattens all URLs (main + variants)  
5. Writes three outputs:
   - Main URLs per page  
   - All URLs including variants  
   - Summary of counts  
6. Includes backoff for repeated failures and UA rotation to avoid blocking  

---

## ▶️ Installation & Usage

### Install Dependencies
```bash
pip install httpx beautifulsoup4 pandas openpyxl
