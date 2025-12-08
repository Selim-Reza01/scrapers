# Newark Product Compliance PDF Downloader (Async Playwright)

An advanced asynchronous automation tool that downloads **Product Compliance Certificates (PDF)** for Newark part numbers.  
The scraper uses **Playwright + asyncio** with multiple workers, anti-bot bypass, browser persistence, cookie loading, robust PDF detection, and fallback extraction logic.

---

## 📌 Features
- Fully asynchronous scraping with **multiple concurrent workers**  
- Uses **persistent browser context** to stay logged in & reduce detection  
- Loads and normalizes cookies (`cookies.json`)  
- Searches part numbers via Enter-only submission (no resubmits)  
- Detects navigation into product pages via URL & fallback visual signals  
- Opens **Product Compliance Certificate → PDF modal**  
- Downloads PDF using:
  - Direct browser download  
  - Pop-up/new-page PDF extraction  
  - Fallback: any PDF link on the page  
- Automatically saves each file as `<part_number>.pdf`  
- Handles:
  - Timeout errors  
  - Missing certificate links  
  - Popup-based PDFs  
  - Soft anti-bot evasions (navigator tweaks)  
- Multi-thread–style concurrency using asyncio + semaphore  
- Logs all results into `results.xlsx`  
- Auto-creates required folders  

---

## 🛠 Tech Stack
- Python  
- Playwright (Async)  
- asyncio  
- aiohttp (for fallback request mode)  
- Chrome Persistent Context  
- Pandas  
- Excel Output  

---

## 📂 How It Works
1. Loads part numbers from `input_parts.xlsx`  
2. Starts Chromium persistent context with:
   - user_data folder  
   - cookies  
   - anti-bot JS patches  
3. For each part number (with concurrency limit):
   - Opens Newark homepage  
   - Performs search using Enter  
   - Waits for product-page confirmation  
   - Scrolls to compliance section  
   - Clicks **Product Compliance Certificate**  
   - Attempts multiple PDF download techniques  
   - Saves file or logs failure  
4. Writes log:
   - `success`  
   - `fail` (with detailed reason)  
   - `error` (network/timeouts)

---

## ▶️ Installation & Usage

### Install dependencies
```bash
pip install playwright pandas openpyxl
playwright install chromium
