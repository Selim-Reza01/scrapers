# Datacenters.com Australia Scraper
A high-performance scraper for Datacenters.com (Australia) that collects full data center listings, detailed facility information, Google Maps links, and logos/media images.  
Built using Selenium for lightweight pagination, Requests + BeautifulSoup for fast detail-page parsing, and ThreadPoolExecutor for parallelized data + image downloading.

---

## 📌 Features
- Scrapes all data center listings across 7 pages  
- Extracts:
  - Operator  
  - Facility Name  
  - Address + Detailed Address  
  - Data Center URL (relative + full)  
  - Logo Image URL  
  - Media Image URL  
  - Short Details  
  - Long Details  
  - Google Maps “pin” link  
  - Total Space, Colocation Space  
  - Total Power, Power Density  
  - Nearest Airport  
- Uses **Selenium only for pagination** (super fast, images disabled)  
- Detail pages fetched in **parallel** via Requests for speed  
- Downloads and saves both **logo** and **media images**  
- Generates pinned Google Maps URL when address is available  
- Auto-saves each processed data center directly into Excel  
- Deduplicates listings by URL before detail scraping  
- Robust retry logic for HTTP requests  
- Fully headless-compatible for background execution  

---

## 🛠 Tech Stack
- Python  
- Selenium (lightweight pagination)  
- BeautifulSoup (detail parsing)  
- Requests with retry + connection pooling  
- ThreadPoolExecutor (parallel scraping)  
- OpenPyXL (incremental Excel writing)  
- WebDriver Manager  
- CSS Selectors & XPath  

---

## 📂 How It Works
1. Opens the Datacenters.com Australia listing page  
2. Loads up to 7 pages using Selenium (images disabled for speed)  
3. Parses listing cards (operator, facility, address, images, URLs)  
4. Deduplicates centers by full URL  
5. Uses a thread pool to:
   - Fetch detail pages  
   - Extract technical specs (space, power, airport, descriptions)  
   - Download logo + media images  
   - Build Google Maps “place” pin link  
6. Saves each completed record immediately into `Australia Datacenters.xlsx`  
7. Saves all images into the `images/logo` and `images/media` folders  

---

## ▶️ Installation & Usage

### Install Dependencies
```bash
pip install selenium webdriver-manager requests beautifulsoup4 pandas openpyxl
