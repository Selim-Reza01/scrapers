import time
import re
import os
import random
import pandas as pd
from datetime import datetime
from urllib.parse import urljoin

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from lxml import html
from selenium.common.exceptions import TimeoutException, WebDriverException

# --- CONFIGURATION ---
EXCEL_FILENAME = datetime.now().strftime("%Y-%m-%d") + ".xlsx"

WAIT_TIMEOUT = 120  
MIN_SLEEP = 1      
MAX_SLEEP = 5     
COOLDOWN_SLEEP = 60 
MAX_CONSECUTIVE_FAILS = 3  
MAX_CONSECUTIVE_ZERO_SAVES = 2 

INPUT_URLS = [
    "https://www.gumtree.com.au/s-cars-vans-utes/act/c18320l3008838?forsaleby=ownr&view=gallery",
    "https://www.gumtree.com.au/s-cars-vans-utes/nsw/c18320l3008839?forsaleby=ownr&sort=price_asc&view=gallery&price-type=fixed",
    "https://www.gumtree.com.au/s-cars-vans-utes/nsw/c18320l3008839?forsaleby=ownr&sort=price_desc&view=gallery&price-type=fixed",
    "https://www.gumtree.com.au/s-cars-vans-utes/nsw/c18320l3008839?forsaleby=ownr&sort=price_asc&view=gallery&price-type=negotiable",
    "https://www.gumtree.com.au/s-cars-vans-utes/nsw/c18320l3008839?forsaleby=ownr&sort=price_desc&view=gallery&price-type=negotiable",
    "https://www.gumtree.com.au/s-cars-vans-utes/nsw/c18320l3008839?forsaleby=ownr&view=gallery&price-type=swap-trade",
    "https://www.gumtree.com.au/s-cars-vans-utes/nt/c18320l3008840?forsaleby=ownr&view=gallery",
    "https://www.gumtree.com.au/s-cars-vans-utes/qld/c18320l3008841?forsaleby=ownr&sort=price_asc&view=gallery",
    "https://www.gumtree.com.au/s-cars-vans-utes/qld/c18320l3008841?forsaleby=ownr&sort=price_desc&view=gallery",
    "https://www.gumtree.com.au/s-cars-vans-utes/sa/c18320l3008842?forsaleby=ownr&view=gallery",
    "https://www.gumtree.com.au/s-cars-vans-utes/tas/c18320l3008843?forsaleby=ownr&view=gallery",
    "https://www.gumtree.com.au/s-cars-vans-utes/vic/c18320l3008844?forsaleby=ownr&sort=price_asc&view=gallery",
    "https://www.gumtree.com.au/s-cars-vans-utes/vic/c18320l3008844?forsaleby=ownr&sort=price_desc&view=gallery",
    "https://www.gumtree.com.au/s-cars-vans-utes/wa/c18320l3008845?forsaleby=ownr&sort=price_asc&view=gallery",
    "https://www.gumtree.com.au/s-cars-vans-utes/wa/c18320l3008845?forsaleby=ownr&sort=price_desc&view=gallery"
]

if hasattr(uc, "Chrome"):
    def _chrome_noop_del(self):
        pass
    uc.Chrome.__del__ = _chrome_noop_del

def create_driver():
    print("Launching new browser instance...")
    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    }
    options.add_experimental_option("prefs", prefs)
    
    try:
        driver = uc.Chrome(options=options)
    except Exception:
        time.sleep(5)
        driver = uc.Chrome(options=options)
    return driver

def random_scroll(driver):
    try:
        scroll_counts = random.randint(2, 7)
        for _ in range(scroll_counts):
            scroll_height = random.randint(300, 700)
            driver.execute_script(f"window.scrollBy(0, {scroll_height});")
            time.sleep(random.uniform(0.5, 1.5))
    except Exception:
        pass

def is_page_blocked(driver):
    try:
        title = driver.title.lower()
        source = driver.page_source.lower()
        if "429" in title or "too many requests" in source:
            return True
        if "access denied" in title or "access denied" in source:
            return True
    except Exception:
        pass
    return False

def safe_get(driver, url):
    max_retries = 5
    for attempt in range(max_retries):
        try:
            driver.get(url)
            
            if is_page_blocked(driver):
                print(f"Blocked detected. Waiting {COOLDOWN_SLEEP}s...")
                time.sleep(COOLDOWN_SLEEP)
                driver.delete_all_cookies()
                continue 

            WebDriverWait(driver, WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.CLASS_NAME, "user-ad-square-new-design"))
            )
            
            random_scroll(driver)
            return True 
            
        except TimeoutException:
            if is_page_blocked(driver):
                print(f"Timeout due to Block. Waiting {COOLDOWN_SLEEP}s...")
                time.sleep(COOLDOWN_SLEEP)
            else:
                print(f"Timeout loading page (Attempt {attempt+1})")
        except WebDriverException as e:
            raise e 
                
    return False

def clean_text(text):
    if not text:
        return "N/A"
    # Remove vertical tabs, null bytes, etc.
    return re.sub(r'[\x00-\x1F\x7F]', '', text)

def scrape_current_page_source(driver_source):
    items = []
    tree = html.fromstring(driver_source)
    listings = tree.xpath('//a[contains(@class,"user-ad-square-new-design")]')

    for node in listings:
        try:
            href = node.get("href")
            if not href: continue
            full_url = urljoin("https://www.gumtree.com.au", href)
            
            title_node = node.xpath('.//span[contains(@class,"user-ad-square-new-design__title")]/text()')
            title = title_node[0].strip() if title_node else "N/A"
            
            price_node = node.xpath('.//span[contains(@class,"user-ad-price-new-design__price")]/text()')
            price = price_node[0].strip() if price_node else "N/A"
            
            desc_node = node.xpath('.//div[contains(@class,"user-ad-square-new-design__description")]/text()')
            description = desc_node[0].strip() if desc_node else "N/A"

            # Clean the text before saving
            items.append({
                "Title": clean_text(title),
                "Price": clean_text(price),
                "URL": full_url,
                "Description": clean_text(description),
                "Scraped Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception:
            continue
    return items

def save_to_excel_deduplicated(new_data):
    if not new_data: return 0, 0
    df_new = pd.DataFrame(new_data)
    df_new.drop_duplicates(subset=["URL"], inplace=True)
    
    saved, dupes = 0, 0
    
    if os.path.exists(EXCEL_FILENAME):
        try:
            # Read existing Excel file
            df_existing = pd.read_excel(EXCEL_FILENAME)
            existing_urls = set(df_existing["URL"].astype(str).tolist())
            
            # Filter unique rows
            unique_rows = df_new[~df_new["URL"].isin(existing_urls)]
            
            dupes = len(df_new) - len(unique_rows)
            saved = len(unique_rows)
            
            if not unique_rows.empty:
                # Concatenate
                df_final = pd.concat([df_existing, unique_rows], ignore_index=True)
                df_final.to_excel(EXCEL_FILENAME, index=False)
        except Exception as e:
            print(f"  [Save Error] {e}")
            # Fallback
            df_new.to_excel(EXCEL_FILENAME, index=False)
            saved = len(df_new)
    else:
        # File doesn't exist
        df_new.to_excel(EXCEL_FILENAME, index=False)
        saved = len(df_new)
        
    return saved, dupes

def process_single_input(driver, index, total_inputs, start_url):
    print(f"Process {index} out of {total_inputs}: {start_url}")
    
    total_pages = 0
    url_template = start_url
    
    # --- Init: Get Total Pages ---
    while total_pages == 0:
        try:
            if safe_get(driver, start_url):
                source = driver.page_source
                tree = html.fromstring(source)
                
                last_link = tree.xpath('//a[contains(@class, "page-number-navigation__link-last")]')
                
                if last_link:
                    href = last_link[0].get("href")
                    full_href = urljoin("https://www.gumtree.com.au", href)
                    match = re.search(r'page-(\d+)', full_href)
                    if match:
                        total_pages = int(match.group(1))
                        url_template = full_href.replace(f"page-{total_pages}", "page-{}")
                    else:
                        total_pages = 1 
                else:
                    total_pages = 1 
            else:
                print("Failed to load Page 1. Retrying...")
                driver.quit()
                time.sleep(5)
                driver = create_driver()
        except Exception as e:
            print(f"Restarting...")
            try: driver.quit()
            except: pass
            time.sleep(5)
            driver = create_driver()

    print(f"Total Page: {total_pages}")
    
    # --- Main Loop ---
    current_page = 1
    consecutive_fails = 0
    consecutive_zero_saves = 0
    all_rows = []

    while current_page <= total_pages:
        
        if current_page > 1:
            sleep_time = random.uniform(MIN_SLEEP, MAX_SLEEP)
            #print(f"    ...Reading... (Waiting {sleep_time:.1f}s)")
            time.sleep(sleep_time)
        
        target_url = start_url if current_page == 1 else url_template.format(current_page)
        
        try:
            if current_page == 1 and total_pages > 0:
                success = True 
            else:
                success = safe_get(driver, target_url)
            
            if success:
                page_items = scrape_current_page_source(driver.page_source)
                print(f"  > Scraped Page {current_page}/{total_pages} (Items: {len(page_items)})")
                
                # Save to Excel immediately
                saved, dupes = save_to_excel_deduplicated(page_items)
                
                if saved > 0:
                    print(f"     Saved {saved} rows.")
                    consecutive_zero_saves = 0
                else:
                    print(f"     Saved 0 rows.")
                    consecutive_zero_saves += 1
                
                # Check Early Exit
                if consecutive_zero_saves >= MAX_CONSECUTIVE_ZERO_SAVES:
                    print(f"No new data for {MAX_CONSECUTIVE_ZERO_SAVES} pages. Moving to next Process.")
                    break 
                
                consecutive_fails = 0
                current_page += 1
            
            else:
                consecutive_fails += 1
                print(f"Failed to load Page {current_page} (Attempt {consecutive_fails}/{MAX_CONSECUTIVE_FAILS})")
                
                if consecutive_fails >= MAX_CONSECUTIVE_FAILS:
                    raise Exception("Max consecutive fails reached")

        except Exception as e:
            print("Restarting Browser and Resuming from Page " + str(current_page))
            try:
                driver.quit()
            except:
                pass
            time.sleep(10)
            driver = create_driver()
            consecutive_fails = 0

    print("---------------------------------")
    return driver

if __name__ == "__main__":
    driver = create_driver()
    try:
        total_inputs = len(INPUT_URLS)
        for i, url in enumerate(INPUT_URLS, 1):
            driver = process_single_input(driver, i, total_inputs, url)
    except KeyboardInterrupt:
        print("\nScraper stopped by user.")
    finally:
        print("Closing browser...")
        try:
            driver.quit()
        except:
            pass