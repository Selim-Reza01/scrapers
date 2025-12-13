import os, time
from typing import List, Dict
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException

GOOGLE_MAPS_URL = "https://www.google.com/maps"
INPUT_FILE = "search_key.xlsx"
OUTPUT_FILE = "search_key_results.xlsx"

# ---------- Helpers ----------
def load_existing_urls(path: str) -> set:
    if os.path.exists(path):
        try:
            df = pd.read_excel(path)
            if "url" in df.columns:
                return set(df["url"].dropna().astype(str).tolist())
        except Exception:
            pass
    return set()

def append_rows(path: str, rows: List[Dict]):
    new_df = pd.DataFrame(rows)
    if new_df.empty:
        return
    if os.path.exists(path):
        old = pd.read_excel(path)
        df = pd.concat([old, new_df], ignore_index=True)
    else:
        df = new_df
    if "url" in df.columns:
        df.drop_duplicates(subset=["url"], keep="first", inplace=True)
    df.to_excel(path, index=False)

def wait_for_results_panel(driver, timeout=20):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
    )

def go_home(driver, timeout=25):
    """Open a fresh Maps homepage and wait for the search box to be ready."""
    driver.get(GOOGLE_MAPS_URL)
    # Ensure page fully loaded + search box interactable
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.ID, "searchboxinput"))
    )
    WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.ID, "searchboxinput"))
    )
    time.sleep(0.2)  # tiny settle

def do_search(driver, query: str):
    box = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "searchboxinput"))
    )
    box.click()
    box.clear()
    box.send_keys(query)
    box.send_keys(Keys.ENTER)

def reached_end_of_list(driver) -> bool:
    try:
        for el in driver.find_elements(By.CSS_SELECTOR, 'div.PbZDve span.HlvSq'):
            text = el.text.strip()
            if text in [
                "You've reached the end of the list.",
                "আপনি তালিকার শেষে পৌঁছে গেছেন।",
            ]:
                return True
    except Exception:
        pass
    return False

def scroll_results_to_end(driver, max_scrolls=200, pause=0.5, timeout=5):
    """Scrolls the left results panel until 'end of list' appears or no new items load."""
    feed = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
    )
    last_height = 0
    for _ in range(max_scrolls):
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", feed)
        # Dynamic wait: watch for feed height growth
        start_time = time.time()
        while time.time() - start_time < timeout:
            new_height = driver.execute_script("return arguments[0].scrollHeight;", feed)
            if new_height > last_height:
                last_height = new_height
                break
            if reached_end_of_list(driver):
                return
            time.sleep(pause)
        else:
            # No height change for `timeout` seconds → stop
            break
        if reached_end_of_list(driver):
            break

def parse_results(driver) -> List[Dict]:
    results = []
    cards = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"].Nv2PK.tH5CWc.THOPZb')
    seen_urls = set()
    for card in cards:
        try:
            name = card.get_attribute("aria-label") or ""
            a = card.find_element(By.CSS_SELECTOR, "a.hfpxzc")
            url = a.get_attribute("href") or ""
            if url and url not in seen_urls:
                results.append({"name": name, "url": url})
                seen_urls.add(url)
        except (NoSuchElementException, StaleElementReferenceException):
            continue
    return results

# ---------- Main ----------
def main():
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError("Input Excel 'search_key.xlsx' not found (needs 'keyword' column).")

    df_in = pd.read_excel(INPUT_FILE)
    if "keyword" not in df_in.columns:
        raise ValueError("Input Excel must have a column named 'keyword'.")

    total = len(df_in)
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless=new")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    existing_urls = load_existing_urls(OUTPUT_FILE)
    rows_to_write = []

    try:
        for idx, row in df_in.iterrows():
            keyword = str(row["keyword"]).strip()
            if not keyword or keyword.lower() == "nan":
                continue

            print(f"\n🔍 Processing {idx+1} out of {total} → {keyword}")

            # Fresh homepage for every keyword
            go_home(driver)

            do_search(driver, keyword)

            try:
                wait_for_results_panel(driver, timeout=25)
            except TimeoutException:
                time.sleep(2)

            try:
                scroll_results_to_end(driver)
            except TimeoutException:
                pass

            # Collect new rows only for this keyword
            new_rows = []

            scraped = parse_results(driver)
            for item in scraped:
                if item["url"] not in existing_urls:
                    new_rows.append(item)
                    existing_urls.add(item["url"])

            # Save immediately after each keyword
            if new_rows:
                append_rows(OUTPUT_FILE, new_rows)
                print(f"   → Saved {len(new_rows)} new rows.")
            else:
                print("   → No new rows found.")

            # OPTIONAL: small pause to keep Chrome stable
            time.sleep(0.3)

    finally:
        driver.quit()

    print(f"\n✅ Scraping Done!!")

if __name__ == "__main__":
    main()
