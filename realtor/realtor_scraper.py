import re
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import random
import os
import sys
from datetime import datetime

def patched_del(self):
    try:
        self.quit()
    except OSError:
        pass
    except Exception:
        pass

uc.Chrome.__del__ = patched_del

# CONFIGURATION
HEADLESS = False
INPUT_DATA = [
    {
        "Country": "Walworth",
        "URL": "https://www.realtor.com/realestateandhomes-search/Walworth-County_WI"
    },

    {
        "Country": "Waukesha",
        "URL": "https://www.realtor.com/realestateandhomes-search/Waukesha-County_WI"
    },

    {
        "Country": "Washington",
        "URL": "https://www.realtor.com/realestateandhomes-search/Washington-County_WI"
    },

    {
        "Country": "Milwaukee",
        "URL": "https://www.realtor.com/realestateandhomes-search/Milwaukee-County_WI"
    },

    {
        "Country": "Racine",
        "URL": "https://www.realtor.com/realestateandhomes-search/Racine-County_WI"
    },
    
    {
        "Country": "Kenosha",
        "URL": "https://www.realtor.com/realestateandhomes-search/Kenosha-County_WI"
    }
]

def start_browser():
    options = uc.ChromeOptions()
    options.headless = HEADLESS
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--page_load_strategy=eager")
    
    driver = uc.Chrome(options=options)
    driver.set_window_size(1280, 1024)
    return driver

def get_unique_filename(base_name):
    if not os.path.exists(base_name):
        return base_name
    name, ext = os.path.splitext(base_name)
    counter = 1
    while True:
        new_name = f"{name} ({counter}){ext}"
        if not os.path.exists(new_name):
            return new_name
        counter += 1

def load_reference_sheet():
    file_path = 'Reference.xlsx'
    if os.path.exists(file_path):
        return pd.read_excel(file_path)
    return pd.DataFrame(columns=['Country', 'URL', 'Added_Date'])

def save_reference_sheet(df):
    df.to_excel('Reference.xlsx', index=False)

def safe_click(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        element.click()
    except:
        try:
            driver.execute_script("arguments[0].click();", element)
        except:
            pass

def scroll_full_page(driver, speed_mode="normal"):
    total_height = int(driver.execute_script("return document.body.scrollHeight"))
    step = 800 if speed_mode == "fast" else 600
    
    for i in range(1, total_height, step):
        driver.execute_script(f"window.scrollTo(0, {i});")
        time.sleep(0.01)
    
    # Ensure bottom
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(0.5)

def get_total_pages(driver):
    try:
        pagination_divs = driver.find_elements(By.XPATH, "//div[@aria-label='pagination']")
        nums = []
        if pagination_divs:
            links = pagination_divs[0].find_elements(By.TAG_NAME, "a")
            for link in links:
                txt = link.text.strip()
                if txt.isdigit():
                    nums.append(int(txt))
        else:
            links = driver.find_elements(By.XPATH, "//a[contains(@class, 'pagination-item')]")
            for link in links:
                txt = link.text.strip()
                if txt.isdigit():
                    nums.append(int(txt))
        if nums:
            return max(nums)
        return 1
    except:
        return 1

def expand_property_details(driver):
    try:
        # 1. Expand Accordion
        accordion_header = None
        # Fast ID check
        try:
            accordion_header = driver.find_element(By.ID, "Property details")
        except:
            # Fallback
            xpath = "//*[contains(text(), 'Property details')]/ancestor::div[contains(@class, 'Accordion') or contains(@id, 'accordion')]"
            accordion_elems = driver.find_elements(By.XPATH, xpath)
            if accordion_elems:
                accordion_header = accordion_elems[0]

        if accordion_header:
            safe_click(driver, accordion_header)
            time.sleep(0.5)

        # Click "Show more"
        for _ in range(5):
            buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Show more')]")
            clicked_any = False
            for btn in buttons:
                if btn.is_displayed():
                    safe_click(driver, btn)
                    clicked_any = True
            if not clicked_any:
                break
            time.sleep(0.3) 
    except:
        pass

def extract_listing_data(driver, url, country_name):
    data = {
        "Country": country_name,
        "Listing URL": url,
        "Price": "N/A",
        "Listed By": "N/A",
        "Brokered By": "N/A",
        "Sewer": "N/A",
        "Water Source": "N/A",
        "Scraped at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        # === PRICE (Updated with Regex fix) ===
        try:
            wait = WebDriverWait(driver, 2)
            price_el = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@data-testid, 'price')]")))
            raw_price = price_el.text.strip()
            price_match = re.search(r'\$[\d,]+', raw_price)
            if price_match:
                data["Price"] = price_match.group(0)
            else:
                data["Price"] = raw_price
        except: 
            pass

        # === LISTED/BROKERED BY (Primary Method) ===
        try:
            listed_els = driver.find_elements(By.XPATH, "//*[contains(text(), 'Listed by')]")
            if listed_els: 
                # clean 'Listed by' text if attached
                txt = listed_els[0].text.replace("Listed by", "").strip()
                if txt: data["Listed By"] = txt
            
            brokered_els = driver.find_elements(By.XPATH, "//*[contains(text(), 'Brokered by')]")
            if brokered_els: 
                txt = brokered_els[0].text.replace("Brokered by", "").strip()
                if txt: data["Brokered By"] = txt
        except: 
            pass

        # === LISTED/BROKERED BY (Backup Method) ===
        if data["Listed By"] == "N/A" or data["Listed By"] == "":
            try:
                xpath = "//div[@data-testid='listing-provider']//li[contains(., 'Listed by')]//a"
                elm = driver.find_element(By.XPATH, xpath)
                data["Listed By"] = elm.text.strip()
            except: pass

        if data["Brokered By"] == "N/A" or data["Brokered By"] == "":
            try:
                xpath = "//div[@data-testid='listing-provider']//li[contains(., 'Brokered by')]//a"
                elm = driver.find_element(By.XPATH, xpath)
                data["Brokered By"] = elm.text.strip()
            except: pass

        # === UTILITIES ===
        expand_property_details(driver)
        
        # Check LI tags
        li_tags = driver.find_elements(By.TAG_NAME, "li")
        for li in li_tags:
            txt = li.text.strip()
            if "Sewer:" in txt:
                data["Sewer"] = txt.split("Sewer:")[-1].strip()
            if "Water Source:" in txt:
                data["Water Source"] = txt.split("Water Source:")[-1].strip()

        return data 

    except Exception:
        return data

def append_to_excel(filename, new_data_list, columns):
    if not new_data_list:
        return
    
    new_df = pd.DataFrame(new_data_list)
    if os.path.exists(filename):
        existing_df = pd.read_excel(filename)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df
        combined_df = combined_df[columns]
    
    combined_df.to_excel(filename, index=False)

def main():
    driver = start_browser()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Define File Names
    valid_file_base = f"{today_str}_valid_listing.xlsx"
    other_file_base = f"{today_str}_other_listing.xlsx"
    
    valid_filename = get_unique_filename(valid_file_base)
    other_filename = get_unique_filename(other_file_base)
    
    output_columns = ["Country", "Listing URL", "Price", "Listed By", "Brokered By", "Sewer", "Water Source", "Scraped at"]
    
    # Initialize Files
    if not os.path.exists(valid_filename):
        pd.DataFrame(columns=output_columns).to_excel(valid_filename, index=False)
    if not os.path.exists(other_filename):
        pd.DataFrame(columns=output_columns).to_excel(other_filename, index=False)

    ref_df = load_reference_sheet()
    
    try:
        total_countries = len(INPUT_DATA)
        
        for idx, entry in enumerate(INPUT_DATA):
            country_name = entry["Country"]
            base_url = entry["URL"]
            
            print(f"Processing Country {idx+1}/{total_countries}: {country_name}")
            
            # VISIT PAGE 1
            driver.get(base_url)
            driver.refresh()
            time.sleep(3)
            
            try:
                total_listing_el = driver.find_element(By.XPATH, "//div[@data-testid='total-results']")
                print(f"Total Listing: {total_listing_el.text.strip()}")
            except:
                print("Total Listing: Unknown")
            
            # SCROLL
            print("Scrolling to find pagination...")
            scroll_full_page(driver, speed_mode="fast")
            
            # IDENTIFY PAGES
            total_pages = get_total_pages(driver)
            print(f"Total Pages detected: {total_pages}")
            
            # COLLECT URLs
            all_collected_urls = []
            
            for page_num in range(1, total_pages + 1):
                if page_num == 1:
                    pass 
                else:
                    if base_url.endswith("/"): target_url = f"{base_url}pg-{page_num}"
                    else: target_url = f"{base_url}/pg-{page_num}"
                    
                    driver.get(target_url)
                    time.sleep(random.uniform(1.5, 2.5))
                    scroll_full_page(driver, speed_mode="fast")
                
                # Link Extraction
                links = driver.find_elements(By.XPATH, "//a[contains(@href, '/realestateandhomes-detail/')]")
                page_urls = set()
                for lnk in links:
                    href = lnk.get_attribute("href")
                    if href:
                        clean_url = href.split("?")[0]
                        page_urls.add(clean_url)
                all_collected_urls.extend(list(page_urls))
            
            all_collected_urls = list(set(all_collected_urls))
            
            # REFERENCE CHECK
            existing_urls = set(ref_df['URL'].tolist())
            new_urls = []
            already_exist_count = 0
            
            for url in all_collected_urls:
                if url in existing_urls:
                    already_exist_count += 1
                else:
                    new_urls.append(url)
                    new_row = {"Country": country_name, "URL": url, "Added_Date": datetime.now().strftime("%Y-%m-%d")}
                    ref_df = pd.concat([ref_df, pd.DataFrame([new_row])], ignore_index=True)

            save_reference_sheet(ref_df)
            print(f"Already Exist: {already_exist_count}")
            
            # EXTRACT & SORT
            valid_listings_batch = []
            other_listings_batch = []
            total_new = len(new_urls)
            
            for i, url in enumerate(new_urls):
                sys.stdout.write(f"\rScraping: {i+1}/{total_new} | Valid: {len(valid_listings_batch)} | Other: {len(other_listings_batch)}")
                sys.stdout.flush()
                
                driver.get(url)
                time.sleep(random.uniform(1.0, 2.0)) 
                
                data = extract_listing_data(driver, url, country_name)
                
                # VALIDATION LOGIC
                sewer_val = str(data["Sewer"]).lower()
                water_val = str(data["Water Source"]).lower()
                
                is_valid = False
                if "septic" in sewer_val or "well" in water_val:
                    is_valid = True
                
                if is_valid:
                    valid_listings_batch.append(data)
                else:
                    other_listings_batch.append(data)
            
            print("")
            
            # SAVE TO DUAL EXCEL
            if valid_listings_batch:
                append_to_excel(valid_filename, valid_listings_batch, output_columns)
            
            if other_listings_batch:
                append_to_excel(other_filename, other_listings_batch, output_columns)
            
            print("-----------------------")

    except Exception as e:
        print(f"\nError: {e}")
    finally:
        print("\n------------------")
        print("Scraping Completed Successfully!!")
        driver.quit()

if __name__ == "__main__":
    main()