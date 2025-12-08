import pandas as pd
import json
import time
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# --- CONFIGURATION ---
INPUT_FILE = 'car_listing.xlsx'
OUTPUT_FILE = 'gumtree_listing_details.xlsx'
MAX_THREADS = 4
MAX_RETRIES = 3
SAVE_INTERVAL = 30

# Thread-local storage to reuse drivers
thread_local = threading.local()
progress_lock = threading.Lock()
processed_count = 0
total_rows = 0

def get_driver():
    if not hasattr(thread_local, "driver"):
        chrome_options = Options()
        chrome_options.add_argument("--headless=new") 
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
        
        service = Service(ChromeDriverManager().install())
        thread_local.driver = webdriver.Chrome(service=service, options=chrome_options)
    
    return thread_local.driver

def extract_fields_from_json(json_data):
    data = {}
    
    # --- 1. PARSE 'details' SECTION ---
    details_map = {}
    if "details" in json_data:
        for item in json_data["details"]:
            name = item.get("name")
            values = item.get("values", [])
            if name and values:
                details_map[name] = values

    def get_detail_text(key):
        vals = details_map.get(key)
        if vals and len(vals) > 0:
            return vals[0].get("text")
        return None

    data["Seller Type"] = get_detail_text("Seller Type")
    data["Make & Model"] = get_detail_text("Make & Model") or get_detail_text("Make &amp; Model")
    data["Variant"] = get_detail_text("Variant")
    data["Body Type"] = get_detail_text("Body Type")
    data["Year"] = get_detail_text("Year")
    data["Odometer"] = get_detail_text("Odometer")
    data["Transmission"] = get_detail_text("Transmission")
    data["Drive Train"] = get_detail_text("Drive Train")
    data["Fuel Type"] = get_detail_text("Fuel Type")
    data["Engine Capacity"] = get_detail_text("Engine Capacity")
    data["Cylinder Configuration"] = get_detail_text("Cylinder Configuration")
    data["Colour"] = get_detail_text("Colour")
    data["Air Conditioning"] = get_detail_text("Air conditioning?") or get_detail_text("Air Conditioning")
    data["Registered"] = get_detail_text("Is your car registered?") or get_detail_text("Registered")
    data["VIN"] = get_detail_text("VIN")

    # Special Logic for Registration Number & Status
    reg_vals = details_map.get("Registration number") or details_map.get("Registration Number")
    data["Registration Number"] = None
    data["Registration Status"] = None
    
    if reg_vals:
        if len(reg_vals) > 0:
            data["Registration Number"] = reg_vals[0].get("text")
        if len(reg_vals) > 1:
            data["Registration Status"] = reg_vals[1].get("text")

    # --- 2. PARSE 'specs' SECTION ---
    data["Body Type (Specs)"] = None
    if "specs" in json_data:
        for category in json_data["specs"]:
            for spec_item in category.get("values", []):
                if spec_item.get("name") == "Body Type":
                    data["Body Type (Specs)"] = spec_item.get("value")
                    break
            if data["Body Type (Specs)"]: break

    # --- 3. PARSE 'listingInfo' SECTION ---
    if "listingInfo" in json_data:
        for item in json_data["listingInfo"]:
            n = item.get("name")
            v = item.get("value")
            if n == "Location": data["Location"] = v
            elif n == "Listed By": data["Listed By"] = v
            elif n == "Views": data["Views"] = v
            elif n == "Last Edited": data["Last Edited"] = v
            elif n == "Date Listed": data["Date Listed"] = v
            elif n == "Listing ID": data["Listing ID"] = v

    return data

def scrape_row(row):
    global processed_count
    
    # Extract ID from URL
    listing_url = str(row.get('URL', ''))
    listing_id = None
    try:
        clean_url = listing_url.strip().rstrip('/')
        parts = clean_url.split('/')
        if parts[-1].isdigit():
            listing_id = parts[-1]
        else:
            for p in reversed(parts):
                if p.isdigit() and len(p) > 6:
                    listing_id = p
                    break
    except:
        pass

    if not listing_id:
        with progress_lock:
            processed_count += 1
            print(f"Process {processed_count} out of {total_rows} | Skipped (No ID)", end='\r')
        return row

    api_url = f"https://gt-api.gumtree.com.au/web/vip/snapshot-tabs/{listing_id}"
    driver = get_driver()
    json_data = None
    
    # Retry Logic
    for attempt in range(MAX_RETRIES):
        try:
            driver.get(api_url)
            # Find JSON content
            content = driver.find_element(By.TAG_NAME, "body").text
            if content:
                json_data = json.loads(content)
                break
        except Exception:
            time.sleep(1)

    # Process Result
    result_row = row.copy()
    if json_data:
        extracted = extract_fields_from_json(json_data)
        result_row.update(extracted)
        result_row["Scraped AT"] = datetime.datetime.now().strftime("%H:%M:%S")
    else:
        result_row["Scraped AT"] = "FAILED"

    with progress_lock:
        processed_count += 1
        print(f"Process {processed_count} out of {total_rows}", end='\r')

    return result_row

def save_data(data_list, filename):
    try:
        df = pd.DataFrame(data_list)
        
        # Define exact column order
        target_cols = [
            "Seller Type", "Make & Model", "Variant", "Body Type", "Year", 
            "Odometer", "Transmission", "Drive Train", "Fuel Type", "Engine Capacity", 
            "Cylinder Configuration", "Colour", "Air Conditioning", "Registered", 
            "Registration Number", "Registration Status", "VIN", "Body Type (Specs)", 
            "Location", "Listed By", "Views", "Last Edited", "Date Listed", "Listing ID"
        ]
        
        final_output_columns = ["Title", "Price", "URL", "Description"] + target_cols + ["Scraped AT"]
        
        # Ensure all columns exist
        for col in final_output_columns:
            if col not in df.columns:
                df[col] = ""
                
        # Reorder
        df = df[final_output_columns]
        
        # Save to Excel
        df.to_excel(filename, index=False)
        return True
    except PermissionError:
        print(f"\n[Warning] Could not save to {filename}. Is the file open? Continuing...")
        return False
    except Exception as e:
        print(f"\n[Error] Saving failed: {e}")
        return False

def main():
    global total_rows
    
    print("Loading Input Excel...")
    try:
        df = pd.read_excel(INPUT_FILE)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    rows = df.to_dict('records')
    total_rows = len(rows)
    
    print(f"Starting Scraper with {MAX_THREADS} threads...")
    print(f"Data will be autosaved every {SAVE_INTERVAL} rows.")
    
    processed_data = []
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        # Submit all tasks
        futures = [executor.submit(scrape_row, row) for row in rows]
        
        # Process as they complete
        for future in as_completed(futures):
            result = future.result()
            processed_data.append(result)
            
            # --- INCREMENTAL SAVE CHECK ---
            if len(processed_data) % SAVE_INTERVAL == 0:
                print(f"\n[Checkpoint] Saving {len(processed_data)} rows...")
                save_data(processed_data, OUTPUT_FILE)
                # print process line again because the save message broke the line
                print(f"Process {processed_count} out of {total_rows}", end='\r')

    duration = time.time() - start_time
    print(f"\n\nScraping completed in {duration:.2f} seconds.")

    # Final Save
    print("Performing final save...")
    save_data(processed_data, OUTPUT_FILE)
    print(f"Done! Data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()