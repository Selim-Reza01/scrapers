import os
import time
from pathlib import Path
from typing import List, Tuple, Optional

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

# ===================== USER CONFIG =====================
INPUT_XLSX  = r"D:\Upwork\Project 3\ML3\Model\input_parts.xlsx"     # must have column: part_number
OUTPUT_DIR  = r"D:\Upwork\Project 3\ML3\Model\Modex_PDFs_1"
LOG_XLSX    = r"D:\Upwork\Project 3\ML3\Model\download_log.xlsx"

MOLEX_URL   = "https://www.molex.com/en-us/product-compliance"

# Selenium settings
PAGE_LOAD_TIMEOUT_SEC      = 60
ELEMENT_WAIT_SEC           = 20
DOWNLOAD_WAIT_TIMEOUT_SEC  = 60   # max wait for each PDF to fully download
POLL_INTERVAL_SEC          = 0.5  # polling for download completion

# When a session’s first attempt fails, we restart the browser and retry the SAME part.
MAX_BROWSER_RESTARTS_PER_PART = 3

# Optional recycle: after N successes, force a new browser (0 = disable)
OPEN_NEW_BROWSER_EVERY_N   = 0

# ========================================================

def ensure_dirs():
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

def read_parts() -> List[str]:
    if not os.path.exists(INPUT_XLSX):
        raise FileNotFoundError(f"Excel not found: {INPUT_XLSX}")
    df = pd.read_excel(INPUT_XLSX)
    if "part_number" not in df.columns:
        raise RuntimeError("input_parts.xlsx must have a column named 'part_number'")
    parts = [str(x).strip() for x in df["part_number"].tolist() if str(x).strip()]
    if not parts:
        raise RuntimeError("No part numbers found.")
    return parts

def make_driver(download_dir: str) -> webdriver.Chrome:
    """
    Configure Chrome to auto-download PDFs to OUTPUT_DIR with no prompt,
    and open PDFs externally (not in Chrome viewer).
    """
    chrome_opts = Options()
    chrome_prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "plugins.always_open_pdf_externally": True,  # IMPORTANT: save the PDF instead of opening viewer
    }
    chrome_opts.add_experimental_option("prefs", chrome_prefs)
    # Keep browser visible so you can manually reload the first time
    # (don't run headless here since you want to interact)
    # chrome_opts.add_argument("--start-maximized")  # optional

    driver = webdriver.Chrome(options=chrome_opts)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT_SEC)
    return driver

def open_site(driver: webdriver.Chrome):
    driver.get(MOLEX_URL)
    # Wait until the textarea exists
    WebDriverWait(driver, ELEMENT_WAIT_SEC).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#pn_data"))
    )

def prompt_user_ready():
    print(
        "\n💡 Please prepare the browser:\n"
        "   1) Manually RELOAD the page once (Ctrl+R / Cmd+R)\n"
        "   2) Dismiss cookies if any\n"
        "   3) Ensure you can see the part number textarea\n"
        "When ready, press ENTER here to start this session..."
    )
    try:
        input()
    except KeyboardInterrupt:
        raise
    except Exception:
        pass

def fill_part_and_uncheck_rohs(driver: webdriver.Chrome, part: str):
    ta = WebDriverWait(driver, ELEMENT_WAIT_SEC).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "#pn_data"))
    )
    try:
        ta.clear()
    except Exception:
        pass
    ta.send_keys(part)
    time.sleep(0.15)

    # Uncheck RoHS if checked
    try:
        rohs = driver.find_element(By.CSS_SELECTOR, "input[name='RoHS']")
        if rohs.is_selected():
            rohs.click()
    except NoSuchElementException:
        pass
    time.sleep(0.15)

def click_generate(driver: webdriver.Chrome):
    btn = WebDriverWait(driver, ELEMENT_WAIT_SEC).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#pdfgenerate, input#pdfgenerate"))
    )
    btn.click()

def _list_download_candidates(download_dir: str):
    return {f for f in os.listdir(download_dir) if f.lower().endswith((".pdf", ".crdownload", ".part"))}

def wait_for_download(download_dir: str, before: set, timeout: int) -> Optional[str]:
    """
    Wait for a *new* file to appear and finish downloading.
    Returns the absolute path to the finished PDF, or None on timeout.
    """
    deadline = time.time() + timeout
    candidate = None

    while time.time() < deadline:
        current = _list_download_candidates(download_dir)
        new_files = current - before
        if new_files:
            # If we see a .crdownload/.part, remember it; wait until it becomes a .pdf
            pdfs = [f for f in new_files if f.lower().endswith(".pdf")]
            if pdfs:
                # Finished PDF appeared directly
                return os.path.join(download_dir, pdfs[0])

            # Track any temp download file
            temps = [f for f in new_files if f.lower().endswith((".crdownload", ".part"))]
            if temps:
                candidate = temps[0]

        # If we have a candidate temp name, check if its final .pdf now exists
        if candidate:
            base = candidate.rsplit(".", 1)[0]
            final_pdf = base + ".pdf"
            if final_pdf in os.listdir(download_dir):
                return os.path.join(download_dir, final_pdf)

        time.sleep(POLL_INTERVAL_SEC)

    return None

def click_and_save_pdf(driver: webdriver.Chrome, part: str, download_dir: str) -> Tuple[bool, str]:
    """
    Try once in the current session:
      1) record files before
      2) click Generate
      3) wait for new pdf to finish
      4) rename to <part>.pdf (overwrite if exists)
    """
    before = set(os.listdir(download_dir))
    click_generate(driver)

    pdf_path = wait_for_download(download_dir, before, DOWNLOAD_WAIT_TIMEOUT_SEC)
    if not pdf_path:
        return False, "download timeout (no PDF detected)"

    # rename/move to target name
    target = os.path.join(download_dir, f"{part}.pdf")
    try:
        # If pdf_path == target (server already named), still ensure consistent name
        if os.path.abspath(pdf_path) != os.path.abspath(target):
            # If target exists, overwrite
            if os.path.exists(target):
                os.remove(target)
            os.replace(pdf_path, target)
    except Exception as e:
        return False, f"rename failed: {type(e).__name__}: {e}"
    return True, ""

def main():
    ensure_dirs()
    parts = read_parts()

    all_rows = []
    total = len(parts)
    i = 0

    # Track restart cap per part to avoid infinite loops
    remaining_attempts = {p: MAX_BROWSER_RESTARTS_PER_PART for p in parts}

    while i < total:
        # ---- Start fresh browser session ----
        try:
            driver = make_driver(OUTPUT_DIR)
        except WebDriverException as e:
            print(f"\n🔴 Could not start Chrome: {e}")
            break

        try:
            # Navigate to page (retry a bit on flaky network)
            nav_ok = False
            for attempt in range(3):
                try:
                    open_site(driver)
                    nav_ok = True
                    break
                except Exception:
                    time.sleep(1.5)
            if not nav_ok:
                raise TimeoutException("Failed to open Molex page after retries")

            # Ask *you* to prep the browser (manual reload/dismiss)
            prompt_user_ready()

            # Process parts until one fails (then we restart and ask again)
            successes_in_this_session = 0

            while i < total:
                part = parts[i]
                print(f"\rProcessing {i+1} out of {total}", end="", flush=True)

                try:
                    fill_part_and_uncheck_rohs(driver, part)
                    ok, note = click_and_save_pdf(driver, part, OUTPUT_DIR)
                    if ok:
                        all_rows.append((part, "success", ""))
                        i += 1
                        successes_in_this_session += 1
                    else:
                        all_rows.append((part, "fail", note))
                        remaining_attempts[part] -= 1
                        # Do NOT advance i — we will restart browser and retry same part
                        break
                except Exception as e:
                    all_rows.append((part, "error", f"{type(e).__name__}: {e}"))
                    remaining_attempts[part] -= 1
                    break

                # Optional proactive recycle
                if OPEN_NEW_BROWSER_EVERY_N and successes_in_this_session >= OPEN_NEW_BROWSER_EVERY_N:
                    break

                # best-effort clear
                try:
                    driver.find_element(By.CSS_SELECTOR, "#pn_data").clear()
                except Exception:
                    pass

                time.sleep(0.15)

        finally:
            # Close browser no matter what
            try:
                driver.quit()
            except Exception:
                pass

        # If we exited inner loop due to a fail, check attempts and maybe skip
        if i < total:
            part = parts[i]
            if remaining_attempts.get(part, 0) <= 0:
                print(f"\n⚠️ Skipping '{part}' after too many restarts.")
                i += 1

        # small cooldown before next browser
        time.sleep(1.0)

    # Write log
    pd.DataFrame(all_rows, columns=["part_number", "status", "note"]).to_excel(LOG_XLSX, index=False)
    print(f"\n✅ Done. PDFs saved to: {OUTPUT_DIR}\nLog file: {LOG_XLSX}")

if __name__ == "__main__":
    main()