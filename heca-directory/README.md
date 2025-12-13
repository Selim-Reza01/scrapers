# HECA Member Directory Scraper

A Python-based web scraper that extracts publicly available member directory data from the HECA (Heating, Electrical & Cooling Association) website and exports the results into a clean Excel file.

The scraper iterates through alphabetical and numeric search terms to ensure maximum directory coverage, deduplicates records, and applies polite request delays to avoid overwhelming the server.

---

## 🚀 Features

- Scrapes HECA member directory listings by **alphabetical, numeric, and special-character terms**
- Extracts:
  - Business / member name
  - Phone number
  - Website URL (if available)
  - Member details page URL
- Automatically **deduplicates results** using a stable identifier
- Saves results to a structured **Excel (.xlsx)** file
- Uses a persistent HTTP session with custom headers
- Includes polite rate limiting to reduce server load
- Simple, single-file execution

---

## 🛠 Tech Stack

- Python 3
- `requests` – HTTP requests
- `BeautifulSoup` (bs4) – HTML parsing
- `pandas` – data structuring and Excel export

---

## 📂 Project Structure
