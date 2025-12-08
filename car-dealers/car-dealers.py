#!/usr/bin/env python
# coding: utf-8

# In[4]:


"""
Auto Trader Dealer Scraper — Jupyter version (HEAD mode + per-page save)
Scrapes dealer Name, URL, and Phone Number directly from search results.

- Visible Chrome (headless = False)
- Prints progress like "1/5: Success"
- Immediately saves after each page (both XLSX and CSV)
"""

import os
import time
import re
from urllib.parse import urljoin, urlencode, urlparse, parse_qs, urlunparse

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from selenium.common.exceptions import TimeoutException, WebDriverException

# ======================================================
# CONFIG — set these manually
# ======================================================
BASE = "https://www.autotrader.co.uk"
SEARCH_URL = (
    "https://www.autotrader.co.uk/cars/dealers/search"
    "?advertising-locations=at_cars&forSale=on&make&model&page=1"
    "&postcode=CV37%200AA&radius=1501&sort=with-retailer-reviews&toOrder=on"
)

OUTPUT_DIR = r"D:\Upwork"
OUTPUT_XLSX = os.path.join(OUTPUT_DIR, "autotrader_dealers(10pages).xlsx")
OUTPUT_CSV  = os.path.join(OUTPUT_DIR, "autotrader_dealers(10pages).csv")

start_page = 1        # first page to scrape
end_page   = 10        # last page to scrape
headless   = False    # <-- head mode so you can see the browser
only_murley = False   # True = keep only “Murley Auto Hyundai”

WAIT_SECS = 30
PAGE_PAUSE = 1.0      # small pause between pages

# ======================================================
# HELPERS
# ======================================================

def set_url_page(url: str, page: int) -> str:
    """Return url with ?page=<page> preserved/replaced (keeps other params)."""
    parts = list(urlparse(url))
    q = parse_qs(parts[4])
    q["page"] = [str(page)]
    parts[4] = urlencode(q, doseq=True)
    return urlunparse(parts)

def start_driver(headless: bool = False):
    opts = uc.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    # More stable in notebooks:
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1300,900")
    driver = uc.Chrome(options=opts)
    driver.set_page_load_timeout(60)
    return driver

def accept_cookies(driver):
    """Click the cookie consent button if present."""
    selectors = [
        "//*[@id='onetrust-accept-btn-handler']",
        "//button[contains(translate(., 'ACEPTLl', 'aceptll'), 'accept')]",
        "//button[contains(., 'Accept all')]",
        "//button[contains(., 'Accept All')]",
        "//button[contains(., 'I accept')]",
        "//button[contains(., 'Got it')]",
    ]
    for sel in selectors:
        try:
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, sel))
            )
            btn.click()
            time.sleep(0.4)
            return True
        except Exception:
            continue
    return False

PHONE_RE = re.compile(
    r"(\(\s?0\d{2,5}\s?\)\s?\d{3,4}\s?\d{3,4}|\+44\s?\d{3,4}\s?\d{3}\s?\d{3,4}|0\d{9,10})"
)

def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def extract_phone_from_container(container) -> str:
    """Try to find a phone number in the dealer card container."""
    try:
        spans = container.find_elements(By.TAG_NAME, "span")
        for sp in spans:
            txt = normalize_space(sp.text)
            if PHONE_RE.search(txt):
                return txt
    except Exception:
        pass
    try:
        tel = container.find_element(By.CSS_SELECTOR, "a[href^='tel:']")
        if tel and tel.text.strip():
            return normalize_space(tel.text)
    except Exception:
        pass
    return ""

def scrape_page(driver, page_num: int):
    """Scrape all dealers from one search results page."""
    url = set_url_page(SEARCH_URL, page_num)
    driver.get(url)

    # Accept cookies only once (first page)
    if page_num == start_page:
        accept_cookies(driver)

    # Wait for listing titles to appear
    WebDriverWait(driver, WAIT_SECS).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[data-testid='search-listing-title']"))
    )

    # Nudge rendering (helps lazy content)
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.4);")
        time.sleep(0.3)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.9);")
        time.sleep(0.3)
        driver.execute_script("window.scrollTo(0, 0);")
    except WebDriverException:
        pass

    anchors = driver.find_elements(By.CSS_SELECTOR, "a[data-testid='search-listing-title']")
    rows = []
    for a in anchors:
        try:
            name = normalize_space(a.text)
            href = a.get_attribute("href") or a.get_attribute("data-href") or a.get_attribute("pathname")
            if not href:
                continue
            if href.startswith("/"):
                href = urljoin(BASE, href)

            # Find card container (class names can change; keep a fallback)
            container = None
            try:
                container = a.find_element(By.XPATH, "ancestor::div[contains(@class,'sc-g51lfe-8')][1]")
            except Exception:
                try:
                    container = a.find_element(By.XPATH, "ancestor::div[1]")
                except Exception:
                    container = None

            phone = extract_phone_from_container(container) if container else ""
            if name and "/dealers/" in href:
                rows.append({"Name": name, "URL": href, "Phone Number": phone})
        except Exception:
            continue

    return rows

def save_incremental(all_rows, xlsx_path=OUTPUT_XLSX, csv_path=OUTPUT_CSV):
    """Save current cumulative results to XLSX and CSV."""
    os.makedirs(os.path.dirname(xlsx_path), exist_ok=True)
    df = pd.DataFrame(all_rows, columns=["Name", "URL", "Phone Number"])
    # Optional Murley filter
    if only_murley:
        df = df[df["Name"].str.strip().str.lower() == "murley auto hyundai"]

    # Deduplicate by URL
    df = df.drop_duplicates(subset=["URL"], keep="first")

    # Save both formats (CSV is quicker + safe)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Dealers")

# ======================================================
# MAIN (immediate per-page save + progress prints)
# ======================================================

def main():
    total_pages = end_page - start_page + 1
    all_rows = []
    driver = start_driver(headless=headless)

    try:
        for idx, p in enumerate(range(start_page, end_page + 1), start=1):
            try:
                page_rows = scrape_page(driver, p)
                all_rows.extend(page_rows)
                # Save immediately after this page
                save_incremental(all_rows)
                print(f"{idx}/{total_pages}: Success")
            except TimeoutException:
                print(f"{idx}/{total_pages}: Failed (timeout)")
            except Exception as e:
                print(f"{idx}/{total_pages}: Failed ({e})")
            finally:
                time.sleep(PAGE_PAUSE)
    finally:
        # Always close the browser
        try:
            driver.quit()
        except Exception:
            pass

    # Final summary
    df_final = pd.read_csv(OUTPUT_CSV)
    print(f" - Total rows: {len(df_final)}")

# Run
main()


# In[ ]:




