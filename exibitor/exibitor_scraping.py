#!/usr/bin/env python
# coding: utf-8

# In[5]:


# CELL 2: Scrape a range; uses exact selectors & Back button; robust against stale elements

import os, csv, time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

LIST_URL = "https://dp-host.fieramilano.it/en/page/espositori"

# ======= Notebook inputs =======
start_idx = int(input("Enter starting index (e.g., 1): ").strip() or 1)
end_idx   = int(input("Enter ending index   (0 = till last): ").strip() or 0)
output_dir = input(r'Enter output folder (default: r"D:\Upwork"): ').strip() or r"D:\Upwork"

os.makedirs(output_dir, exist_ok=True)
CSV_PATH  = os.path.join(output_dir, "hostmilano_exhibitors.csv")
XLSX_PATH = os.path.join(output_dir, "hostmilano_exhibitors.xlsx")

HEADERS = ["Index", "Company", "PavilionStand", "Country", "Website", "Email", "Phone", "Sectors", "Categories", "DetailSource"]

# ======= IO =======
def append_row(row: dict):
    # CSV
    new_file = not os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS)
        if new_file:
            w.writeheader()
        w.writerow(row)
    # Excel
    df_new = pd.DataFrame([row], columns=HEADERS)
    if os.path.exists(XLSX_PATH):
        try:
            df_old = pd.read_excel(XLSX_PATH)
            df_new = pd.concat([df_old, df_new], ignore_index=True)
        except Exception:
            pass
    df_new.to_excel(XLSX_PATH, index=False)

# ======= Selenium helpers =======
def build_driver():
    opts = Options()
    opts.add_argument("--window-size=1440,900")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    driver.set_page_load_timeout(90)
    return driver

def ensure_tiles_loaded(driver, needed_count: int, idle_rounds_target=6, pause=0.9) -> int:
    """
    Scroll until at least `needed_count` tiles are present OR page stops growing.
    Returns current tile count.
    """
    idle_rounds = 0
    last_count = 0
    while True:
        tiles = driver.find_elements(By.CSS_SELECTOR, ".lf-espositori-v2-list .lf-espositori-v2-list-item-wrapper")
        count = len(tiles)
        if count >= needed_count:
            return count
        if count > last_count:
            idle_rounds = 0
            last_count = count
        else:
            idle_rounds += 1
            if idle_rounds >= idle_rounds_target:
                return count
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)

def refetch_tile(driver, index_1based: int):
    tiles = driver.find_elements(By.CSS_SELECTOR, ".lf-espositori-v2-list .lf-espositori-v2-list-item-wrapper")
    if 1 <= index_1based <= len(tiles):
        return tiles[index_1based - 1]
    return None

def robust_click(driver, el, retries=4):
    for _ in range(retries):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.15)
            el.click()
            return True
        except Exception:
            try:
                driver.execute_script("arguments[0].click();", el)
                return True
            except Exception:
                driver.execute_script("window.scrollBy(0, -200);")
                time.sleep(0.15)
    return False

def first_visible(driver, css, scope=None):
    root = scope or driver
    els = root.find_elements(By.CSS_SELECTOR, css)
    for e in els:
        try:
            if e.is_displayed():
                return e
        except Exception:
            pass
    return None

def get_text(el, default="N/A"):
    try:
        t = el.text.strip()
        return t if t else default
    except Exception:
        return default

def extract_recapiti(driver, scope):
    country = website = email = phone = "N/A"
    try:
        span = first_visible(driver, ".recapiti .indirizzo span", scope)
        if span:
            lines = [ln.strip() for ln in span.get_attribute("innerText").splitlines() if ln.strip()]
            if lines: country = lines[-1]
    except Exception:
        pass
    try:
        a = first_visible(driver, ".recapiti a.sito_web", scope)
        if a:
            href = (a.get_attribute("href") or "").strip()
            if href.startswith("http://"): href = "https://" + href[len("http://"):]
            website = href or "N/A"
    except Exception:
        pass
    try:
        a = first_visible(driver, ".recapiti a.email", scope)
        if a:
            href = (a.get_attribute("href") or "").strip()
            email = href[len("mailto:"):] if href.lower().startswith("mailto:") else (get_text(a) or "N/A")
    except Exception:
        pass
    try:
        a = first_visible(driver, ".recapiti a.telefono", scope)
        if a:
            href = (a.get_attribute("href") or "").strip()
            phone = href[len("tel:"):] if href.lower().startswith("tel:") else (get_text(a) or "N/A")
    except Exception:
        pass
    return country, website, email, phone

def extract_sectors(driver, scope):
    try:
        el = scope.find_element(
            By.XPATH,
            ".//h3[translate(normalize-space(.),'SECTORS','sectors')='sectors']/following::p[contains(@class,'tag')][1]/span"
        )
        txt = el.text.strip()
        return txt if txt else "N/A"
    except Exception:
        return "N/A"

def extract_categories(driver, scope):
    """
    MAIN A > sub1, sub2; MAIN B > subx
    """
    try:
        cat_root = first_visible(driver, ".categorie", scope)
        inner = cat_root.find_element(By.CSS_SELECTOR, ".categorie > div")
    except Exception:
        return "N/A"
    children = inner.find_elements(By.XPATH, "./*")
    groups = []
    current_main = None
    for c in children:
        tag = c.tag_name.lower()
        if tag == "span":
            current_main = c.text.strip()
            if current_main:
                groups.append([current_main, []])
        elif tag == "div" and current_main and groups:
            subs = [e.text.strip() for e in c.find_elements(By.CSS_SELECTOR, "span") if e.text.strip()]
            groups[-1][1].extend(subs)
    parts = []
    for main, subs in groups:
        parts.append(f"{main} > {', '.join(subs)}" if subs else main)
    return "; ".join(parts) if parts else "N/A"

def click_back_button(driver, wait: WebDriverWait, timeout=10):
    try:
        back_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#close-lf-espositori-v2-list-item-details")))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", back_btn)
        time.sleep(0.1)
        back_btn.click()
        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, "#close-lf-espositori-v2-list-item-details"))
        )
        return True
    except Exception:
        try:
            driver.execute_script("document.dispatchEvent(new KeyboardEvent('keydown',{'key':'Escape'}));")
            time.sleep(0.2)
        except Exception:
            pass
        return False

# ======= Run =======
driver = build_driver()
wait = WebDriverWait(driver, 30)
driver.get(LIST_URL)
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".lf-espositori-v2-list")))

print("✅ Page loaded. Starting…")

i = max(1, start_idx)
while True:
    # Ensure we have at least i tiles loaded
    have = ensure_tiles_loaded(driver, i)
    if have < i:
        print(f"Reached end of list at {have}.")
        break

    tile = refetch_tile(driver, i)
    if not tile:
        print(f"[{i}] Tile not found. Stopping.")
        break

    if not robust_click(driver, tile, retries=4):
        print(f"[{i}] Click failed, skipping.")
        i += 1
        if end_idx and i > end_idx: break
        continue

    # Wait for detail: specifically the name block you showed
    try:
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".name h1")))
    except Exception:
        print(f"[{i}] Detail view did not appear, skipping.")
        i += 1
        if end_idx and i > end_idx: break
        continue

    detail_scope = driver.find_element(By.TAG_NAME, "body")

    # Company & PavilionStand from .name
    company_el = first_visible(driver, ".name h1", detail_scope)
    pav_el     = first_visible(driver, ".name h5", detail_scope)
    company = get_text(company_el, "N/A") if company_el else "N/A"
    pavilion = get_text(pav_el, "N/A") if pav_el else "N/A"

    # Country, Website, Email, Phone from .recapiti
    country, website, email, phone = extract_recapiti(driver, detail_scope)

    # Sectors
    sectors = extract_sectors(driver, detail_scope)

    # Categories (multi-group)
    categories = extract_categories(driver, detail_scope)

    row = {
        "Index": i,
        "Company": company,
        "PavilionStand": pavilion,
        "Country": country,
        "Website": website,
        "Email": email,
        "Phone": phone,
        "Sectors": sectors,
        "Categories": categories,
        "DetailSource": LIST_URL
    }
    append_row(row)
    print(f"[{i}] Saved: {company}")

    # Go back using the page Back button you specified
    clicked_back = click_back_button(driver, wait)
    if not clicked_back:
        print(f"[{i}] Back button fallback used.")

    time.sleep(0.2)
    i += 1
    if end_idx and i > end_idx:
        break

driver.quit()
print(f"✅ Done. Files saved:\n- {CSV_PATH}\n- {XLSX_PATH}")


# In[7]:


# CELL: Scrape ONLY specific indices; highlight + manual click when needed (no wait delays)

import os, csv, time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

LIST_URL = "https://dp-host.fieramilano.it/en/page/espositori"

# ======= Target indices =======
target_indices = [
    41, 91, 141, 191, 241, 291, 341, 391, 441, 491,
    541, 591, 641, 691, 741, 791, 841, 891, 941, 991,
    1041, 1091, 1141, 1191, 1241, 1291, 1341, 1391, 1441, 1491,
    1541, 1591, 1641, 1691, 1741, 1791, 1841, 1891, 1941, 1991,
    2041, 2091, 2141, 2191, 2241, 2291
]

# ======= Output paths =======
output_dir = r"D:\Upwork"
os.makedirs(output_dir, exist_ok=True)
CSV_PATH  = os.path.join(output_dir, "hostmilano_exhibitors.csv")
XLSX_PATH = os.path.join(output_dir, "hostmilano_exhibitors.xlsx")

HEADERS = ["Index", "Company", "PavilionStand", "Country", "Website", "Email", "Phone", "Sectors", "Categories", "DetailSource"]

# ======= IO helpers =======
def append_row(row: dict):
    new_file = not os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS)
        if new_file: w.writeheader()
        w.writerow(row)
    df_new = pd.DataFrame([row], columns=HEADERS)
    if os.path.exists(XLSX_PATH):
        try:
            df_old = pd.read_excel(XLSX_PATH)
            df_new = pd.concat([df_old, df_new], ignore_index=True)
        except Exception: pass
    df_new.to_excel(XLSX_PATH, index=False)

# ======= Selenium helpers =======
def build_driver():
    opts = Options()
    opts.add_argument("--window-size=1440,900")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    return driver

def ensure_tiles_loaded(driver, needed):
    while True:
        tiles = driver.find_elements(By.CSS_SELECTOR, ".lf-espositori-v2-list .lf-espositori-v2-list-item-wrapper")
        if len(tiles) >= needed: return tiles
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.3)

def highlight(driver, el):
    try:
        driver.execute_script("arguments[0].style.outline='3px solid yellow';", el)
    except: pass

def first_visible(driver, css, scope=None):
    root = scope or driver
    els = root.find_elements(By.CSS_SELECTOR, css)
    for e in els:
        if e.is_displayed(): return e
    return None

def get_text(el, default="N/A"):
    try:
        t = el.text.strip()
        return t if t else default
    except: return default

def extract_recapiti(driver, scope):
    country=website=email=phone="N/A"
    try:
        span=first_visible(driver,".recapiti .indirizzo span",scope)
        if span:
            lines=[ln.strip() for ln in span.get_attribute("innerText").splitlines() if ln.strip()]
            if lines: country=lines[-1]
    except: pass
    try:
        a=first_visible(driver,".recapiti a.sito_web",scope)
        if a: website=(a.get_attribute("href") or "").strip()
    except: pass
    try:
        a=first_visible(driver,".recapiti a.email",scope)
        if a:
            href=(a.get_attribute("href") or "").strip()
            email=href[len("mailto:"):] if href.lower().startswith("mailto:") else get_text(a)
    except: pass
    try:
        a=first_visible(driver,".recapiti a.telefono",scope)
        if a:
            href=(a.get_attribute("href") or "").strip()
            phone=href[len("tel:"):] if href.lower().startswith("tel:") else get_text(a)
    except: pass
    return country,website,email,phone

def extract_sectors(driver, scope):
    try:
        el=scope.find_element(By.XPATH,".//h3[translate(normalize-space(.),'SECTORS','sectors')='sectors']/following::p[contains(@class,'tag')][1]/span")
        return el.text.strip() or "N/A"
    except: return "N/A"

def extract_categories(driver, scope):
    try:
        root=first_visible(driver,".categorie",scope)
        inner=root.find_element(By.CSS_SELECTOR,".categorie > div")
    except: return "N/A"
    children=inner.find_elements(By.XPATH,"./*")
    groups=[]; main=None
    for c in children:
        tag=c.tag_name.lower()
        if tag=="span":
            main=c.text.strip()
            if main: groups.append([main,[]])
        elif tag=="div" and main and groups:
            subs=[e.text.strip() for e in c.find_elements(By.CSS_SELECTOR,"span") if e.text.strip()]
            groups[-1][1].extend(subs)
    parts=[f"{m} > {', '.join(s)}" if s else m for m,s in groups]
    return "; ".join(parts) if parts else "N/A"

def click_back(driver):
    try:
        back=driver.find_element(By.CSS_SELECTOR,"#close-lf-espositori-v2-list-item-details")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", back)
        back.click()
    except:
        try: driver.execute_script("document.dispatchEvent(new KeyboardEvent('keydown',{'key':'Escape'}));")
        except: pass

# ======= Run =======
driver = build_driver()
wait = WebDriverWait(driver, 30)
driver.get(LIST_URL)
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".lf-espositori-v2-list")))
print("✅ Page loaded. Manual-click mode ready.\n")

for idx in target_indices:
    tiles = ensure_tiles_loaded(driver, idx)
    if idx > len(tiles):
        print(f"[{idx}] Not found on page. Skipping.")
        continue
    tile = tiles[idx-1]
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", tile)
    except: pass
    # Try auto-open first
    try:
        tile.click()
        WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".name h1")))
    except:
        # manual click required
        highlight(driver, tile)
        input(f"[{idx}] Please CLICK the highlighted tile manually, then press ENTER here: ")
    # Now scrape
    try:
        scope = driver.find_element(By.TAG_NAME,"body")
        company = get_text(first_visible(driver,".name h1",scope))
        pavilion = get_text(first_visible(driver,".name h5",scope))
        country, website, email, phone = extract_recapiti(driver, scope)
        sectors = extract_sectors(driver, scope)
        categories = extract_categories(driver, scope)
        row = {
            "Index": idx, "Company": company, "PavilionStand": pavilion,
            "Country": country, "Website": website, "Email": email,
            "Phone": phone, "Sectors": sectors, "Categories": categories,
            "DetailSource": LIST_URL
        }
        append_row(row)
        print(f"[{idx}] Saved: {company}")
    except Exception as e:
        print(f"[{idx}] Error extracting data: {e}")
    click_back(driver)
    time.sleep(0.2)

driver.quit()
print(f"\n✅ Done. Data appended to:\n- {CSV_PATH}\n- {XLSX_PATH}")

