# Google Maps Lead Scraper (3-Step Pipeline)

This repository is a complete lead-generation scraping package that collects business leads from Google Maps by keyword/geolocation, enriches them with business details, and then extracts emails from the business websites.

It works as a 3-step pipeline:

1. **Scrape Google Maps place URLs** from keywords (Step 1)
2. **Extract business details** from each place URL (Step 2)
3. **Extract emails** from each business website (Step 3)

> Output is saved as Excel files at each step for easy review and control.

---

## ✅ What You Can Collect

- Business name
- Google Maps place URL
- Rating + review count
- Category
- Address
- Website
- Phone number
- Emails from website (visible text + `mailto:`)

---

## 📁 Files in This Package

- `g_scraper_1.py` → Step 1: Keyword → Name + Google Maps URL list
- `g_scraper_2.py` → Step 2: URL list → Business details
- `g_scraper_3.py` → Step 3: Website list → Emails

---

## ⚙️ Requirements

### Python
- Python 3.9+ recommended

### Packages
Install dependencies:
```bash
pip install pandas requests beautifulsoup4 selenium webdriver-manager openpyxl
