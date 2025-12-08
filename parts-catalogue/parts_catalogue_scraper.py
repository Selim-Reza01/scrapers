import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from selenium import webdriver  # Changed: Standard selenium (no wire)
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

# REMOVED: PROXIES list is no longer needed

MAX_RETRIES = 3
MAX_TIMEOUT = 30.0          # seconds per group URL (initial load)
MAX_SHOW_MORE = 10          # allow many show-more clicks for big groups
NUM_WORKERS = 5             # number of parallel threads / drivers

GROUP_CODES = {
    "Accessories and miscellaneous": 1094,
    "Fuels and lubricants, car care products": 548,
    "Engine": 549,
    "Exhaust system": 558,
    "IC engine cooling": 560,
    "Body, car glass": 551,
    "Heating, A/C": 993,
    "Suspension, chassis": 554,
    "Transmission, gearbox": 553,
    "Wheels, tyres": 550,
    "Steering": 556,
    "Fuel system": 561,
    "Air system": 979,
    "Ignition system": 559,
    "Brake system": 562,
    "Filters": 563,
    "Electrical": 564,
    "Others": -1,
}

# Shared progress counter
progress_lock = threading.Lock()
# NEW: Input lock to prevent multiple threads asking for "Enter" at the same time
input_lock = threading.Lock()

progress_counter = 0
total_group_urls = 0  # set in main()


# -------------------------------------------------
# DRIVER (NO PROXY)
# -------------------------------------------------

def create_driver():
    """Create a headed Chrome driver with images DISABLED using standard Selenium."""
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # --- BLOCK IMAGES ---
    prefs = {
        "profile.managed_default_content_settings.images": 2,  # 2 = Block images
        "profile.default_content_setting_values.notifications": 2, # Block notifications
    }
    options.add_experimental_option("prefs", prefs)
    
    # --- FASTER LOADING STRATEGY ---
    options.page_load_strategy = 'eager'

    # REMOVED: seleniumwire_options and interceptor
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(int(MAX_TIMEOUT))
    driver.maximize_window()
    return driver

# -------------------------------------------------
# SCROLL LIST (POPUP) UNTIL NO NEW ITEMS
# -------------------------------------------------

def scroll_list_until_no_new_items(driver, prev_count=None, max_scrolls: int = 40) -> int:
    """
    Robust scroller:
    1. Scrolls to the LAST item to trigger lazy load.
    2. Includes 'patience' - if no new items appear, it retries a few times.
    """
    try:
        items = driver.find_elements(By.CSS_SELECTOR, "ul._9ikbUAgVfYQ- li.sXbh6y72f90-")
        last_count = len(items)
    except WebDriverException:
        return prev_count if prev_count is not None else 0

    no_change_retries = 0
    MAX_RETRIES_ON_NO_CHANGE = 3 

    for _ in range(max_scrolls):
        try:
            items = driver.find_elements(By.CSS_SELECTOR, "ul._9ikbUAgVfYQ- li.sXbh6y72f90-")
            if not items:
                break
            
            last_item = items[-1]
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", last_item)
            
            time.sleep(0.5) 

            new_items = driver.find_elements(By.CSS_SELECTOR, "ul._9ikbUAgVfYQ- li.sXbh6y72f90-")
            new_count = len(new_items)

            if new_count > last_count:
                last_count = new_count
                no_change_retries = 0
            else:
                no_change_retries += 1
                if no_change_retries >= MAX_RETRIES_ON_NO_CHANGE:
                    break
                else:
                    time.sleep(0.5)

        except WebDriverException:
            break

    return last_count


# -------------------------------------------------
# SCRAPE ONE GROUP URL
# -------------------------------------------------

def scrape_group_items(driver, group_url: str):
    # 1) Navigate
    try:
        driver.get(group_url)
    except (TimeoutException, WebDriverException):
        return "TIMEOUT", [], []

    start = time.time()

    # 2) Poll for item/error/no-data
    while True:
        if time.time() - start > MAX_TIMEOUT:
            return "TIMEOUT", [], []

        try:
            html = driver.page_source
        except WebDriverException:
            return "TIMEOUT", [], []

        # Check for IP block text
        if "Something went wrong" in html and "solving the problem" in html:
            return "IP_BLOCKED", [], []

        if "No interactive diagrams are found" in html:
            return "NO_ITEMS", [], []

        try:
            items = driver.find_elements(By.CSS_SELECTOR, "ul._9ikbUAgVfYQ- li.sXbh6y72f90-")
        except WebDriverException:
            items = []

        if items:
            break
        time.sleep(0.5)

    # 3) Initial Scroll
    current_count = 0
    current_count = scroll_list_until_no_new_items(driver, current_count, max_scrolls=20)

    # 4) Show more loop
    for _ in range(MAX_SHOW_MORE):
        try:
            btns = driver.find_elements(By.CSS_SELECTOR, "button._710xV-kIMAg-")
        except WebDriverException:
            break

        if not btns:
            break 
        
        btn = btns[0]
        if not (btn.is_displayed() and btn.is_enabled()):
            break 

        count_before = current_count

        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
            time.sleep(0.5)
            btn.click()
        except WebDriverException:
            break

        data_arrived = False
        for wait_tick in range(15):
            time.sleep(0.5)
            try:
                check_items = driver.find_elements(By.CSS_SELECTOR, "ul._9ikbUAgVfYQ- li.sXbh6y72f90-")
                if len(check_items) > count_before:
                    current_count = len(check_items)
                    data_arrived = True
                    break
            except:
                pass
        
        if not data_arrived:
            break

        current_count = scroll_list_until_no_new_items(driver, current_count, max_scrolls=20)

    # 5) Final Scroll
    current_count = scroll_list_until_no_new_items(driver, current_count, max_scrolls=10)
    
    # 6) EXTRACT ALL DATA
    items_text = []
    item_urls = []

    try:
        final_items = driver.find_elements(By.CSS_SELECTOR, "ul._9ikbUAgVfYQ- li.sXbh6y72f90-")
    except WebDriverException:
        final_items = []

    for li in final_items:
        try:
            try:
                h2 = li.find_element(By.CSS_SELECTOR, "h2")
                title = h2.text.strip()
            except NoSuchElementException:
                continue

            try:
                a_tag = li.find_element(By.CSS_SELECTOR, "a")
                href = a_tag.get_attribute("href")
            except NoSuchElementException:
                continue
            
            if href and href.startswith("#"):
                href = "https://www.parts-catalogs.com/eu/demo" + href

            if title and href:
                items_text.append(title)
                item_urls.append(href)

        except Exception:
            continue

    return "OK", items_text, item_urls

# -------------------------------------------------
# PER-ID WORKER – RUNS IN A THREAD
# -------------------------------------------------

def process_single_id(task):
    global progress_counter, total_group_urls

    _, ID, base_url = task
    rows_for_this_id = []
    driver = None

    try:
        for group_name, code in GROUP_CODES.items():
            group_url = base_url.replace("/groups?", "/schemas?") + f"&branchId={code}"

            status = "TIMEOUT"
            items = []
            urls = []

            # Loop for retries
            while True: 
                # Create driver if needed
                if driver is None:
                    driver = create_driver()

                status, items, urls = scrape_group_items(driver, group_url)

                # --- NEW LOGIC: PAUSE ON BLOCK ---
                if status == "IP_BLOCKED":
                    # Close current driver as it's useless now
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = None 

                    # Use lock so only one thread prints and asks for input
                    with input_lock:
                        print(f"\n\n🛑 IP BLOCKED on {ID} - {group_name}")
                        print("👉 Please change your VPN/IP Address.")
                        input("⌨️  Then press ENTER in this console to continue...")
                        print("✅ Resuming...\n")
                    
                    # Continue the 'while' loop to retry this exact same group_url
                    continue
                
                # If TIMEOUT, we retry simply
                if status == "TIMEOUT":
                    # We can count retries here if we want, or just retry forever
                    # For now, let's just close driver and retry
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = None
                    continue

                # If OK or NO_ITEMS, break the retry loop and save data
                break

            # Progress log (thread-safe)
            with progress_lock:
                progress_counter += 1
                print(
                    f"process group URL {progress_counter} out of {total_group_urls} : {len(items)} Items"
                )

            if not items:
                rows_for_this_id.append(
                    [ID, base_url, f"{group_name}-{code}", group_url, "", ""]
                )
            else:
                for it, iu in zip(items, urls):
                    rows_for_this_id.append(
                        [ID, base_url, f"{group_name}-{code}", group_url, it, iu]
                    )

    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass

    return rows_for_this_id


# -------------------------------------------------
# MAIN – MULTI-THREAD CONTROLLER
# -------------------------------------------------

def main():
    global total_group_urls

    # Assumption: Input is still Excel
    df = pd.read_excel("input_url.xlsx")

    tasks = [(i, row["ID"], row["Category-URL"]) for i, row in df.iterrows()]

    total_group_urls = len(tasks) * len(GROUP_CODES)

    output_rows = []

    print(f"Starting scraping with {NUM_WORKERS} workers...")

    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {executor.submit(process_single_id, t): t for t in tasks}

        for future in as_completed(futures):
            rows_for_this_id = future.result()
            output_rows.extend(rows_for_this_id)

            # Flush partial results to CSV
            out_df = pd.DataFrame(
                output_rows,
                columns=[
                    "ID",
                    "Category-URL",
                    "Group-Code",
                    "Group-URL",
                    "Group-ITEM",
                    "Group-ITEM-URL",
                ],
            )
            # CHANGED: Save to CSV
            out_df.to_csv("output_1.csv", index=False)

    print("\n✅ Completed! Output saved as output.csv")


if __name__ == "__main__":
    main()