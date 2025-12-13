import os
import re
import time
import threading
from queue import Queue
from typing import Dict, Any, Optional, List

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException


# =========================
# CONFIG
# =========================
HEADLESS = False          # you asked for headless
MAX_WORKERS = 1           # you asked for 5
SAVE_EVERY = 50           # save after every 5 processed
PANEL_TIMEOUT = 20        # from your scrape_place signature
RESTART_EVERY = 250       # restart browser after every 100 processed items (per worker)


# =========================
# WebDriver setup
# =========================
def create_driver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1366,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(45)
    return driver


# =========================
# Waits / helpers
# =========================
def wait_panel_ready(driver: webdriver.Chrome, timeout: int = PANEL_TIMEOUT):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "h1.DUwDvf"))
    )
    # tiny pause so rating/review line renders reliably
    time.sleep(0.4)


def safe_text(el) -> str:
    try:
        return (el.text or "").strip()
    except Exception:
        return ""


# =========================
# Extractors (match your selectors for other fields)
# =========================
def extract_rating(driver: webdriver.Chrome) -> Optional[str]:
    try:
        rating_el = driver.find_element(By.CSS_SELECTOR, "div.F7nice span[aria-hidden='true']")
        return rating_el.text.strip() or None
    except NoSuchElementException:
        return None


def extract_reviews(driver: webdriver.Chrome) -> Optional[str]:
    """
    Robust reviews extraction:
    1) div.F7nice span[role='img'][aria-label*='review'] -> aria-label like "8 reviews"
    2) Fallback: parse '(8)' or '8 reviews' text inside .F7nice
    3) Fallback: review chart button text like '61 reviews' (if available)
    """
    # 1) exact target inside F7nice
    try:
        el = driver.find_element(By.CSS_SELECTOR, "div.F7nice span[role='img'][aria-label*='review']")
        label = (el.get_attribute("aria-label") or el.text or "").strip()
        m = re.search(r"(\d[\d,\.]*)", label)
        if m:
            return m.group(1).replace(",", "")
    except NoSuchElementException:
        pass

    # 2) parse from F7nice text
    try:
        block = driver.find_element(By.CSS_SELECTOR, "div.F7nice")
        txt = (block.get_attribute("innerText") or block.text or "").strip()
        m = re.search(r"\((\d[\d,\.]*)\)", txt)
        if not m:
            m = re.search(r"(\d[\d,\.]*)\s+reviews?", txt, flags=re.I)
        if m:
            return m.group(1).replace(",", "")
    except NoSuchElementException:
        pass

    # 3) review chart button (sometimes present)
    try:
        chart_btn = driver.find_element(
            By.XPATH,
            "//div[contains(@class,'Bd93Zb')]//button[contains(@class,'rqjGif')]"
            "//span[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'reviews')]"
        )
        txt = safe_text(chart_btn)
        m = re.search(r"(\d[\d,\.]*)", txt)
        if m:
            return m.group(1).replace(",", "")
    except NoSuchElementException:
        pass

    return None


def extract_category(driver: webdriver.Chrome) -> Optional[str]:
    try:
        category_el = driver.find_element(By.CSS_SELECTOR, "button.DkEaL")
        return category_el.text.strip() or None
    except NoSuchElementException:
        return None


def extract_address(driver: webdriver.Chrome) -> Optional[str]:
    try:
        address_el = driver.find_element(By.CSS_SELECTOR, "button[data-item-id='address'] div.Io6YTe")
        return address_el.text.strip() or None
    except NoSuchElementException:
        return None


def extract_website(driver: webdriver.Chrome) -> Optional[str]:
    try:
        website_el = driver.find_element(By.CSS_SELECTOR, "a[data-item-id='authority']")
        href = (website_el.get_attribute("href") or "").strip()
        text = (website_el.text or "").strip()
        return href or text or None
    except NoSuchElementException:
        return None


def extract_phone(driver: webdriver.Chrome) -> Optional[str]:
    try:
        phone_el = driver.find_element(By.CSS_SELECTOR, "button[data-item-id^='phone:'] div.Io6YTe")
        return phone_el.text.strip() or None
    except NoSuchElementException:
        return None


# =========================
# Persistent Worker
# =========================
class Worker(threading.Thread):
    def __init__(
        self,
        worker_id: int,
        jobs: Queue,
        results: Dict[int, Dict[str, Any]],
        progress: Dict[str, int],
        total: int,
        save_path: str,
        save_lock: threading.Lock,
        progress_lock: threading.Lock,
    ):
        super().__init__(daemon=True)
        self.worker_id = worker_id
        self.jobs = jobs
        self.results = results
        self.progress = progress
        self.total = total
        self.save_path = save_path
        self.save_lock = save_lock
        self.progress_lock = progress_lock
        self.driver: Optional[webdriver.Chrome] = None
        self.processed_count = 0  # how many this worker has processed since last restart

    def run(self):
        self.driver = create_driver()
        try:
            while True:
                item = self.jobs.get()
                if item is None:
                    self.jobs.task_done()
                    break  # stop signal

                idx, name, url = item
                self.results[idx] = self.process_one(name, url)

                with self.progress_lock:
                    self.progress["done"] += 1
                    done = self.progress["done"]
                    print(f"\rprocessing {done} out of {self.total}", end="", flush=True)
                    if done % SAVE_EVERY == 0:
                        self.save_partial()

                # Track how many this worker has processed since last restart
                self.processed_count += 1

                # Restart browser after RESTART_EVERY items
                if self.processed_count >= RESTART_EVERY:
                    try:
                        if self.driver:
                            self.driver.quit()
                    except Exception:
                        pass

                    print(f"\n[Worker {self.worker_id}] Restarting browser after {self.processed_count} items to free RAM...")
                    self.driver = create_driver()
                    self.processed_count = 0

                self.jobs.task_done()
        finally:
            try:
                if self.driver:
                    self.driver.quit()
            except Exception:
                pass

    def process_one(self, name: str, url: str) -> Dict[str, Any]:
        data = {
            "name": name,
            "url": url,
            "rating": None,
            "reviews": None,
            "category": None,
            "address": None,
            "website": None,
            "phone": None,
        }
        try:
            self.driver.get(url)
            wait_panel_ready(self.driver, timeout=PANEL_TIMEOUT)

            # Your exact selectors for other fields + robust reviews
            data["rating"] = extract_rating(self.driver)
            data["reviews"] = extract_reviews(self.driver)
            data["category"] = extract_category(self.driver)
            data["address"] = extract_address(self.driver)
            data["website"] = extract_website(self.driver)
            data["phone"] = extract_phone(self.driver)
        except (TimeoutException, WebDriverException) as e:
            data["_error"] = str(e)
        return data

    def save_partial(self):
        try:
            with self.save_lock:
                ordered = [self.results[i] for i in sorted(self.results.keys())]
                if not ordered:
                    return
                df = pd.DataFrame(ordered)
                df.to_excel(self.save_path, index=False)
        except Exception:
            pass


# =========================
# Main
# =========================
def main():
    input_file = "search_url.xlsx"
    output_file = "search_url_result.xlsx"

    if not os.path.exists(input_file):
        print(f"Input file '{input_file}' not found in {os.getcwd()}")
        return

    df = pd.read_excel(input_file)
    if "name" not in df.columns or "url" not in df.columns:
        print("Input Excel must have columns: 'name' and 'url'")
        return

    total = len(df)
    if total == 0:
        print("No rows found in input Excel.")
        return

    jobs: Queue = Queue()
    results: Dict[int, Dict[str, Any]] = {}
    progress = {"done": 0}
    save_lock = threading.Lock()
    progress_lock = threading.Lock()
    save_path = os.path.join(os.getcwd(), output_file)

    # enqueue jobs
    for i, row in df.iterrows():
        jobs.put((int(i), str(row["name"]), str(row["url"])))

    # start workers (persistent browsers)
    num_workers = min(MAX_WORKERS, total) if total > 0 else 1
    workers: List[Worker] = []
    for wid in range(num_workers):
        w = Worker(
            worker_id=wid + 1,
            jobs=jobs,
            results=results,
            progress=progress,
            total=total,
            save_path=save_path,
            save_lock=save_lock,
            progress_lock=progress_lock,
        )
        w.start()
        workers.append(w)

    # stop signals
    for _ in workers:
        jobs.put(None)

    # wait for all to finish
    jobs.join()
    for w in workers:
        w.join()

    # final save in original order
    ordered = [results[i] for i in sorted(results.keys())]
    pd.DataFrame(ordered).to_excel(save_path, index=False)
    print(f"\nDone. Saved results to: {save_path}")


if __name__ == "__main__":
    main()
