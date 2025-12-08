# Bikroy.com Car Listings Scraper
A lightweight Python scraper for Bikroy.com that extracts complete used-car listings using Requests, BeautifulSoup, and Pandas.  
This tool collects detailed vehicle information from multiple listing pages and saves everything into a clean CSV file.

---

## 📌 Features
- Scrapes multiple pages of Bikroy car listings
- Extracts:
  - Brand
  - Model
  - Trim / Edition
  - Year of Manufacture
  - Registration Year
  - Condition
  - Transmission
  - Body Type
  - Fuel Type
  - Engine Capacity
  - Kilometers Run
  - Full Description
  - Listing URL
- Parses individual car pages for complete attribute details
- Auto-creates output directory if missing
- Saves all results into a structured CSV file

---

## 🛠 Tech Stack
- Python  
- Requests  
- BeautifulSoup (bs4)  
- Pandas  
- CSS Selectors for attribute extraction  
- CSV Output  

---

## 📂 How It Works
1. Iterates through Bikroy car listing pages using page numbers  
2. Collects all car listing URLs from each page  
3. Visits each car page individually  
4. Extracts attributes such as brand, model, year, specs, mileage, description, etc.  
5. Stores all results into a CSV file (`bikrpy_car_data.csv`)  

---

## ▶️ Installation & Usage

### Install Dependencies
```bash
pip install requests beautifulsoup4 pandas
