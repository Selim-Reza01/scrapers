# GMGN AI Image Stream Scraper (Playwright, Sync, Streaming Downloader)

A high-performance Playwright scraper that continuously scrolls through the **gmgn.ai** live image feed, detects all `_v2.webp` and `_v2l.webp` images in three columns (New, Almost Bonded, Migrated), and downloads each unique image with intelligent variant selection.

The scraper uses **streaming discovery + oscillating scroll**, **in-page JS fetch**, and **duplicate-aware storage** for long continuous sessions.

---

## 📌 Features
- Scrapes all three GMGN columns:
  - **New**
  - **Almost Bonded (MC)**
  - **Migrated**
- Continuous streaming mode:
  - Scrolls down to bottom → then up → repeating oscillation  
  - Detects every new image revealed during scroll
- Extracts both variants:
  - `_v2l.webp` (preferred HQ)
  - `_v2.webp` (fallback)
- De-duplicates by **32-hex ID**
- In-page JavaScript **fetch()** to inherit cookies & headers  
- Automatic upgrade: replaces `_v2.webp` with `_v2l.webp` if found later  
- Live status printing:
  - Images downloaded  
  - Time elapsed  
  - Target counters
- Supports:
  - **Image count limits**
  - **Time-limit sessions**
  - **Ctrl+C graceful exit**
- Writes:
  - `/All Image/` → all unique image variants  
  - `all_urls.txt` → deduped master URL list  

---

## 🛠 Tech Stack
- Python  
- Playwright (Sync API)  
- Regex pattern extraction  
- Base64 decoding  
- Intelligent file versioning  

---

## 📂 How It Works
1. Opens **gmgn.ai** with Playwright  
2. Locates column containers for:
   - NEW  
   - MC (Almost Bonded)  
   - MIGRATED  
3. Scrolls each column up/down repeatedly  
4. For every revealed image:
   - Extracts ID & determines preferred filename  
   - Fetches bytes internally via JS `fetch()`  
   - Stores into `/All Image/` folder  
5. Stops when:
   - Target number of images reached, OR  
   - Time limit reached, OR  
   - User presses Ctrl+C  

---

## ▶️ Installation & Usage

### Install dependencies
```bash
pip install playwright
playwright install chromium
