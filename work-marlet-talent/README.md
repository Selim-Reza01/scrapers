# WorkMarket Talent Scraper (Advanced Playwright Automation)

A highly advanced Playwright-based automation tool that extracts **Talent profiles, vendor details, and contact information** from WorkMarket.  
This scraper captures dashboard JSON payloads, profile-level API responses, vendor tabs, worker tabs, filter chips, and exports validated batches into Excel—handling thousands of results with stability and accuracy.

---

## 📌 Key Features
### 🔹 Full Dashboard API Extraction
- Intercepts WorkMarket’s **dashboard API payloads** via Playwright network listeners  
- Parses virtualized grid rows  
- Extracts:
  - First & Last Name  
  - Email (multiple sources)  
  - Work Phone + Mobile  
  - Location + ZIP  
  - Industry  
  - Certifications, Licenses, Insurance  
  - Account Type  
  - Satisfaction Score  
  - Paid assignments  
  - Drug Test & Background Check  
  - Profile URL  

### 🔹 Vendor Profile Extraction
- For vendor accounts, the scraper:
  - Calls internal Profile JSON endpoint  
  - Extracts deeper fields not shown in the dashboard  

### 🔹 Worker Profile Extraction
- Opens profile popups dynamically  
- Captures **userAtCompanyDetails** API JSON  
- Performs duplicate-suppression  
- Extracts fallback phone/email/address from nested fields  

### 🔹 Batch Export System
- Saves records in **batches** (user chooses batch size)  
- Excel output includes:
  - Filters applied (Row 1)
  - Headers (Row 2)
  - Records (Row 3+)

### 🔹 Intelligent Naming
- Output is saved as:  
