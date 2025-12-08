# TE Connectivity PDF Datasheet Downloader (Async Python + Aiohttp)

A high-performance asynchronous downloader for **TE Connectivity** product datasheets.  
Given a list of TE part numbers, this tool fetches each product’s official datasheet (PDF) using TE’s `SinglePartSearch` endpoint, validates the file, and saves it with clean filenames.  
Non-PDF or failed downloads are logged in a separate Excel report.

---

## 📌 Features
- Fully async pipeline using **aiohttp + asyncio**
- Builds correct TE search URLs automatically for each part number
- Validates responses using:
  - `Content-Type` headers  
  - PDF magic bytes (`%PDF`)
- Extracts filenames from:
  - `Content-Disposition` headers  
  - URL fallbacks
- Cleans invalid filename characters
- Ensures **unique** filenames to avoid overwriting
- Saves PDFs into a dedicated output folder
- Writes skipped/failed parts to `skipped_parts.xlsx`
- Configurable concurrency (default: 5 workers)
- Handles retries, timeouts, redirects, and network errors

---

## 🛠 Tech Stack
- Python  
- aiohttp  
- asyncio  
- aiofiles  
- pandas  
- TE Connectivity SinglePartSearch API  

---

## 📂 How It Works
1. Reads `te_parts.xlsx` containing a `part_number` column  
2. Builds a TE request URL for each part  
3. Sends concurrent PDF download requests (5 at a time)  
4. Validates the response to confirm it's a real PDF  
5. Saves the file using sanitized, conflict-free names  
6. Logs failed downloads into an Excel file  
7. Prints summary: total, downloaded, skipped  

---

## ▶️ Installation & Usage

### Install dependencies
```bash
pip install aiohttp aiofiles pandas openpyxl
