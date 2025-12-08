# WorkMarket Talent Scraper (v1.1)

# Install
pip install -r requirements.txt
python -m playwright install

# Authenticate (only when cookies expire)
python authentication.py

Visible login + 2FA (headless=False by default). Saves cookies to `data/storage_state.json`.

# Run the scraper
python workmarket_talent_scraper.py

If not logged in, the scraper runs `authentication.py` first.
Press **1** to open a visible Talent page and apply filters, then press **Enter**.
Or press **0** to scrape unfiltered headlessly.

# Output
`Talent Output/YYYY-MM-DD_TOTAL.xlsx` (auto (1), (2) if same name exists)
Row 1: filters text
Row 2: headers
Row 3+: data

# Columns
id, name, email, work_phone, location, zip, industry, certifications, licenses, insurance, account_type, satisfaction_score, paid_assignments, drug_test, background_check, profile_url

# Notes
The grid is virtualized and horizontally scrollable; the scraper sweeps `scrollLeft` to reveal off-screen columns.