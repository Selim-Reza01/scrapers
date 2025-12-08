# WithPoli Companies Scraper (Chrome DevTools Network API Capture)

A Selenium-based scraper that extracts companies from **withpoli.com** by intercepting the hidden JSON API request using Chrome DevTools Protocol (CDP).  
Instead of parsing HTML, this tool captures the actual XHR JSON response from the browser network log and exports all company details directly into Excel.

---

## 📌 Features
- Uses **Chrome DevTools Protocol (CDP)** to capture the API response
- Detects XHR/Fetch calls containing `"companies"` in the URL
- Extracts JSON body (supports Base64-encoded bodies)
- Cleans & normalizes fields into a structured dataset
- Extracts:
  - Company Name  
  - Company URL  
  - LinkedIn URL  
  - Description  
  - Active Job Count  
  - Logo Image  
  - Policy  
  - Company Level (Employee Estimate)
- Saves results to `withpoli_companies.xlsx`
- Fully automated — no manual scraping required
- Visible browser for debugging & accurate network capture

---

## 🛠 Tech Stack
- Python  
- Selenium  
- Chrome DevTools Protocol  
- Base64 Decoding  
- Pandas  
- Excel Output  

---

## 📂 How It Works
1. Browser opens **withpoli.com/companies**
2. CDP `Network.enable` is activated to capture network traffic
3. Script waits for an XHR/Fetch request containing `"companies"`
4. Extracts the response body via:
   - `Network.getResponseBody`
   - Base64 decoding if necessary
5. Parses JSON to extract all company details
6. Saves cleaned data into Excel

---

## ▶️ Installation & Usage

### Install dependencies
```bash
pip install selenium pandas openpyxl
