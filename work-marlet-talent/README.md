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
- Auto-resolves filename conflicts: `(...)(1), (2), ...`

### 🔹 Filter Detection
- Reads WorkMarket’s toolbar filter chips using in-page JavaScript  
- Saves filters directly inside the Excel header row  

### 🔹 Navigation Control
- User can select:
- Start page  
- End page  
- Batch size  

### 🔹 Pagination Logic
- Advances using “Next Page” button  
- Uses API-sequence tracking to capture updated dashboard payloads  

### 🔹 Stability & Anti-Failure Logic
- Browser restart logic for stuck states  
- Fallback to last-request POST replay  
- Handles:
- Missing values  
- Off-screen columns  
- Virtualized grids  
- Random UI stalls  
- Deprecated user IDs  

---

## 🛠 Tech Stack
- **Python**
- **Playwright (Sync API)**
- **Excel (pandas + openpyxl/xlsxwriter)**
- **Chrome Persistent Context**
- **Network Event Interception**

---

## 📂 How It Works
1. Script launches with Playwright and loads cookies (`storage_state.json`)  
2. If not logged in → triggers external authentication script  
3. User selects batch size + filters  
4. Scraper:
 - Loads the Talent grid  
 - Captures dashboard API JSON payload  
 - Iterates through pages  
5. For each row:
 - Extracts profile-level details  
 - For vendor accounts → fetches JSON endpoint  
 - For worker accounts → opens popup → reads nested API payload  
6. Records are validated using custom rules  
7. Results are saved in batches into Excel  
8. After reaching end page, output is finalized with correct naming

---

## ▶️ Installation

```bash
pip install -r requirements.txt
python -m playwright install
