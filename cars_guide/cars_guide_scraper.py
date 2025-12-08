import os
import re
import sys
import time
import random
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# ---- Silence UC's noisy destructor on Windows (harmless WinError 6) ----
try:
    uc.Chrome.__del__ = lambda self: None
except Exception:
    pass

BASE = "https://www.carsguide.com.au"
LISTING_BASE = f"{BASE}/buy-a-car"

# ---------- Config you can change ----------
START_PAGE = 1       # e.g. 1
END_PAGE   = 2       # e.g. 3
HEADLESS   = False   # you asked for False
DELAY_BETWEEN_REQUESTS = (0.6, 1.6)  # random polite delay (min, max) seconds
OUTPUT_DIR = r"D:\Upwork\Australia Car Scrap\new"
RETRIES_PER_ACTION = 3
ALLOWED_DOMAIN = "carsguide.com.au"   # popups from other domains are closed
# ------------------------------------------

# ---------- Utilities ----------
def make_driver():
    """
    Create a stealthy Chrome instance that avoids basic bot checks and reduces popups.
    """
    options = uc.ChromeOptions()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--lang=en-US,en")
    options.add_argument("--window-size=1200,2000")
    options.add_argument("--disable-notifications")
    # A few prefs to cut down on nags
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_setting_values.geolocation": 2,
    }
    options.add_experimental_option("prefs", prefs)

    driver = uc.Chrome(options=options)
    driver.set_page_load_timeout(60)
    return driver

def wait_for(driver, css, timeout=25):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))

def scroll_to_bottom(driver, pause=0.6, max_scrolls=30):
    """
    Some cards lazy-load. Scroll to bottom a few times.
    """
    last_h = driver.execute_script("return document.body.scrollHeight")
    for _ in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        h = driver.execute_script("return document.body.scrollHeight")
        if h == last_h:
            break
        last_h = h

def get_listing_urls_from_page(driver):
    """
    Collect full listing URLs from the current search results page.
    """
    scroll_to_bottom(driver, pause=0.5)
    cards = driver.find_elements(By.CSS_SELECTOR, "a.carListing")
    urls = []
    for a in cards:
        href = a.get_attribute("href") or ""
        if href.startswith("http"):
            urls.append(href)
        elif href.startswith("/car/"):
            urls.append(BASE + href)
    # de-dup while preserving order
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

def text_or_none(el):
    try:
        return re.sub(r"\s+", " ", el.text).strip()
    except Exception:
        return None

def safe_select_text(driver, selector):
    try:
        el = driver.find_element(By.CSS_SELECTOR, selector)
        return text_or_none(el)
    except NoSuchElementException:
        return None

def click_if_present(driver, by, value, timeout=5):
    """
    Try to click something if it exists & is clickable.
    Returns True on click, else False.
    """
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.2)
        el.click()
        return True
    except Exception:
        return False

def click_by_text_contains(driver, tag, contains_text, timeout=5):
    """
    Click an element by tag name whose visible text contains a substring.
    """
    xpath = f"//{tag}[contains(normalize-space(.), '{contains_text}')]"
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.2)
        el.click()
        return True
    except Exception:
        return False

def reload_and_wait(driver, url, post_wait_ms=400):
    driver.get(url)
    popup_guard(driver)          # <--- guard immediately after navigation
    try:
        wait_for(driver, "h1.title, div.priceInfo--price", timeout=20)
    except TimeoutException:
        pass
    time.sleep(post_wait_ms / 1000.0)
    popup_guard(driver)

# ---------- Popup/Ad guards ----------
def domain_of(url):
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""

def popup_guard(driver):
    """
    1) JS hardening:
         - disable window.open
         - strip target=_blank so clicks don't spawn tabs
    2) Close any non-CarsGuide windows that slipped through.
    """
    try:
        driver.execute_script("""
            try {
                window.open = function(){ return null; };
                document.querySelectorAll('a[target="_blank"]').forEach(a => a.removeAttribute('target'));
            } catch(e) {}
        """)
    except Exception:
        pass

    try:
        base = driver.current_window_handle
    except Exception:
        return

    handles = driver.window_handles[:]
    for h in handles:
        try:
            driver.switch_to.window(h)
            url = driver.current_url
            if url.startswith("about:blank"):
                # close stray blank tabs
                if h != base:
                    driver.close()
                continue
            if ALLOWED_DOMAIN not in domain_of(url):
                # close unwanted (e.g., nrma.com.au)
                if h != base:
                    driver.close()
        except Exception:
            # if anything odd happens, keep going
            pass
    # Ensure we're on a surviving handle
    try:
        if base not in driver.window_handles:
            driver.switch_to.window(driver.window_handles[0])
        else:
            driver.switch_to.window(base)
    except Exception:
        pass

# ---------- Parsing helpers ----------
KNOWN_BODY_TYPES = ["coupe","sedan","hatch","suv","ute","wagon","convertible","van"]

def extract_vehicle_details_grid(driver):
    """
    Parses the icon grid (quick details). Unknown values go into 'others'.
    """
    details = {
        "kms": None,
        "body_type": None,
        "transmission_drive": None,
        "fuel": None,
        "dealer_status": None,
        "location": None,
        "others": []  # collect anything else here
    }
    try:
        items = driver.find_elements(By.CSS_SELECTOR, "div.vehicleDetails--details div.vehicleDetails--detail")
    except Exception:
        items = []
    for el in items:
        val = text_or_none(el)
        if not val:
            continue
        low = val.lower()

        if "km" in low and details["kms"] is None:
            details["kms"] = val
        elif any(bt in low for bt in KNOWN_BODY_TYPES) and details["body_type"] is None:
            details["body_type"] = val
        elif any(x in low for x in ["automatic","manual"]) and details["transmission_drive"] is None:
            details["transmission_drive"] = val
        elif any(f in low for f in ["petrol","diesel","electric","hybrid","lpg","unleaded"]) and details["fuel"] is None:
            details["fuel"] = val
        elif "dealer" in low and details["dealer_status"] is None:
            details["dealer_status"] = val
        elif details["location"] is None and ("," in val or re.search(r"\b[A-Z]{2,3}\b", val)):
            details["location"] = val
        else:
            details["others"].append(val)
    if details["others"]:
        details["others"] = " | ".join(dict.fromkeys(details["others"]))  # dedup & join
    else:
        details["others"] = None
    return details

def extract_full_details_table_with_retry(driver, url):
    """
    Click 'See all Details' and read the two-column details table.
    If clicking opens a new tab or navigates, close/return and retry.
    """
    for attempt in range(1, RETRIES_PER_ACTION + 1):
        popup_guard(driver)
        base_handles = driver.window_handles[:]
        base_url = driver.current_url

        clicked = click_if_present(driver, By.CSS_SELECTOR, "button.btn.btn-purpleOutline")
        if not clicked:
            clicked = click_by_text_contains(driver, "button", "See all Details", timeout=4)
        time.sleep(0.35)

        # Cleanup any stray tab
        popup_guard(driver)

        # If URL navigated away, go back or reload
        if driver.current_url != base_url and not driver.current_url.startswith(base_url + "#"):
            try:
                driver.back()
                time.sleep(0.4)
            except Exception:
                pass
            reload_and_wait(driver, url)
            continue

        # Read table
        rows_out = []
        try:
            rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr.table--row")
            for r in rows:
                try:
                    label = text_or_none(r.find_element(By.CSS_SELECTOR, "td.table--label"))
                except NoSuchElementException:
                    label = None
                try:
                    try:
                        value = text_or_none(r.find_element(By.CSS_SELECTOR, "td.table--bold.table--value"))
                    except NoSuchElementException:
                        value = text_or_none(r.find_element(By.CSS_SELECTOR, "td.table--value"))
                except NoSuchElementException:
                    value = None
                if label and value:
                    rows_out.append(f"{label}: {value}")
        except Exception:
            rows_out = []

        if rows_out:
            return " | ".join(rows_out)

        reload_and_wait(driver, url)

    return None

def extract_features_with_retry(driver):
    """
    Click FEATURES tab and collect features (li items). Returns ' | ' joined string.
    """
    def _try_once():
        popup_guard(driver)
        clicked = click_by_text_contains(driver, "div", "FEATURES", timeout=4)
        if not clicked:
            clicked = click_by_text_contains(driver, "button", "FEATURES", timeout=3) or \
                      click_by_text_contains(driver, "span", "FEATURES", timeout=3)
        time.sleep(0.35)
        popup_guard(driver)

        features = []

        try:
            containers = driver.find_elements(
                By.XPATH,
                "//*[contains(translate(@class,'FEATURES','features'),'features') or contains(translate(@id,'FEATURES','features'),'features')]"
            )
        except Exception:
            containers = []

        for c in containers:
            try:
                items = c.find_elements(By.CSS_SELECTOR, "li")
                for li in items:
                    t = text_or_none(li)
                    if t:
                        features.append(t)
            except Exception:
                pass

        if not features:
            try:
                items = driver.find_elements(By.CSS_SELECTOR, "li")
                for li in items:
                    t = text_or_none(li)
                    if t and len(t) < 120:
                        features.append(t)
            except Exception:
                pass

        out, seen = [], set()
        for f in features:
            if f not in seen:
                seen.add(f); out.append(f)
        return " | ".join(out) if out else None

    for _ in range(RETRIES_PER_ACTION):
        res = _try_once()
        if res:
            return res
        time.sleep(0.3)
    return None

def reveal_phone_and_comments_with_retry(driver, url):
    """
    - Click 'Show number' (retry if needed) to reveal phone.
    - Click 'Read More' (retry if needed) to expand comments.
    """
    # Phone
    phone = None
    for _ in range(RETRIES_PER_ACTION):
        popup_guard(driver)
        clicked_phone = click_if_present(driver, By.CSS_SELECTOR, "button.carTalkToDealerProfile--revealNumber", timeout=4)
        if not clicked_phone:
            click_by_text_contains(driver, "button", "Show number", timeout=3)
        time.sleep(0.3)
        popup_guard(driver)
        try:
            phone_el = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a.carTalkToDealerProfile--phone[href^="tel:"]'))
            )
            phone = text_or_none(phone_el)
        except TimeoutException:
            phone = None
        if phone:
            break
        driver.execute_script("window.scrollBy(0, 150);")
        time.sleep(0.2)

    # Comments
    comments = None
    for _ in range(RETRIES_PER_ACTION):
        popup_guard(driver)
        clicked_rm = click_if_present(driver, By.CSS_SELECTOR, "a.sellerComments--expanderLink", timeout=4)
        if not clicked_rm:
            click_by_text_contains(driver, "a", "Read More", timeout=3)
        time.sleep(0.25)
        popup_guard(driver)
        comments = safe_select_text(driver, "p.sellerComments--description")
        if comments:
            break
        driver.execute_script("window.scrollBy(0, 150);")
        time.sleep(0.2)

    return phone, comments

# ---------- Scrape one vehicle ----------
KNOWN_BODY_TYPES = ["coupe","sedan","hatch","suv","ute","wagon","convertible","van"]

def scrape_vehicle(driver, url, page_no, vehicle_idx):
    """
    Open one vehicle listing and extract the requested fields.
    """
    driver.get(url)
    popup_guard(driver)
    try:
        wait_for(driver, "h1.title, div.priceInfo--price", timeout=30)
    except TimeoutException:
        pass

    # Live progress: "Page | Vehicle" on a single line
    sys.stdout.write(f"\r{page_no} | {vehicle_idx}")
    sys.stdout.flush()

    # Title & prices
    title = safe_select_text(driver, "h1.title")
    discount_price = safe_select_text(driver, "div.priceInfo--price span")
    regular_price  = safe_select_text(driver, "div.priceInfo--priceDrop span")

    # Quick details grid
    quick = extract_vehicle_details_grid(driver)

    # Reveal phone and full comments (with retry)
    seller_phone, seller_comments = reveal_phone_and_comments_with_retry(driver, url)

    # Full details table (robust retry, handles new tab/popups)
    car_details = extract_full_details_table_with_retry(driver, url)

    # FEATURES (retry)
    features = extract_features_with_retry(driver)

    # Seller address
    seller_address = safe_select_text(driver, "div.carTalkToDealerProfile--location")

    return {
        "listing_url": url,
        "model": title,
        "discount_price": discount_price,
        "regular_price": regular_price,
        "kms": quick.get("kms"),
        "body_type": quick.get("body_type"),
        "transmission_drive": quick.get("transmission_drive"),
        "fuel": quick.get("fuel"),
        "dealer_status": quick.get("dealer_status"),
        "location": quick.get("location"),
        "others": quick.get("others"),        # <-- new column
        "car_details": car_details,           # full table
        "features": features,                 # features tab
        "seller_phone": seller_phone,         # revealed phone
        "seller_address": seller_address,
        "seller_comments": seller_comments,   # expanded comments
        "scraped_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }

# ---------- Orchestrator ----------
def scrape_pages(start_page, end_page):
    driver = make_driver()
    rows = []
    try:
        for page in range(start_page, end_page + 1):
            # Go to page
            if page == 1:
                driver.get(LISTING_BASE)
            else:
                driver.get(f"{LISTING_BASE}?page={page}")
            popup_guard(driver)

            # Wait for listing cards
            try:
                wait_for(driver, "a.carListing", timeout=35)
            except TimeoutException:
                driver.execute_script("window.scrollBy(0, 400);")
                time.sleep(1.0)

            urls = get_listing_urls_from_page(driver)

            # Header + prepare live progress
            print("Scraping: Page | Vehicle")
            sys.stdout.write(f"{page} | 0")
            sys.stdout.flush()

            for idx, u in enumerate(urls, start=1):
                try:
                    rows.append(scrape_vehicle(driver, u, page, idx))
                except WebDriverException as e:
                    rows.append({"listing_url": u, "error": str(e)})
                time.sleep(random.uniform(*DELAY_BETWEEN_REQUESTS))

            # finish the line for this page
            sys.stdout.write("\n")
            sys.stdout.flush()

            time.sleep(random.uniform(*DELAY_BETWEEN_REQUESTS))
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    return rows

def save_to_excel(rows, out_dir=OUTPUT_DIR):
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    out_path = os.path.join(out_dir, f"carsguide_{ts}.xlsx")
    df = pd.DataFrame(rows)
    preferred = [
        "model","discount_price","regular_price","kms","body_type",
        "transmission_drive","fuel","dealer_status","location","others",
        "car_details","features",
        "seller_phone","seller_address","seller_comments",
        "listing_url","scraped_at","error"
    ]
    cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
    df = df[cols]
    df.to_excel(out_path, index=False)
    return out_path

if __name__ == "__main__":
    rows = scrape_pages(START_PAGE, END_PAGE)
    path = save_to_excel(rows)
    print(f"Saved: {path}")