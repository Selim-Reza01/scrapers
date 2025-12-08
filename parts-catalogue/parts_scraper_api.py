import time
import sys
import os
import json
import threading
import pandas as pd
import pyautogui
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --------------------------
# CONFIGURATION
# --------------------------
INPUT_FILE = "input_url_1.xlsx"
OUTPUT_FILE = "parts_catalogue_25.csv"

PROXY_HOST = "gw.dataimpulse.com"
PROXY_PORT = 823
PROXY_USER = "f4d28af4b46f636a1e86"
PROXY_PASS = "11ecd1332b4ca2c2"

RESTART_EVERY_N_URLS = 50
SKIP_CATEGORIES = ["Maintenance parts", "Multi-purpose parts"]
MAX_SHOW_MORE_CLICKS = 10
TIMEOUT_SECONDS = 60
MAX_RETRIES_PER_URL = 5

# --------------------------
# CSV INIT
# --------------------------
if not os.path.exists(OUTPUT_FILE):
    pd.DataFrame(columns=["ID", "Input URL", "Category", "Group", "Group URL"]).to_csv(
        OUTPUT_FILE, index=False
    )

# --------------------------
# HELPER FUNCTIONS (PROXY + BROWSER)
# --------------------------
def kill_chrome_process():
    """Force-kill leftover chromedriver on Windows."""
    try:
        if os.name == "nt":
            os.system("taskkill /f /im chromedriver.exe >nul 2>&1")
    except:
        pass


def handle_login_popup():
    """
    Background thread to handle the proxy authentication popup.
    Uses the pattern you said works:
    - Wait ~6 seconds
    - Click center of screen
    - Type USER, Tab, PASS, Enter
    """
    time.sleep(6)  # Wait for browser & popup to appear

    # Focus popup
    try:
        screenWidth, screenHeight = pyautogui.size()
        pyautogui.click(screenWidth / 2, screenHeight / 2)
    except:
        pass

    # Type credentials
    try:
        pyautogui.write(PROXY_USER, interval=0.1)
        time.sleep(0.5)
        pyautogui.press("tab")
        time.sleep(0.5)
        pyautogui.write(PROXY_PASS, interval=0.1)
        time.sleep(1.0)
        pyautogui.press("enter")
    except Exception as e:
        print(f"   [Auto-Typer Error]: {e}")


def start_browser_with_proxy():
    """
    Start Chrome with:
    - Proxy
    - Disabled images for speed
    - Disabled notifications & password save bubbles
    - Performance logging (needed for Network.getResponseBody)
    - Warm-up request to api.ipify.org to trigger proxy popup & finish auth
    """
    kill_chrome_process()
    print("\n[System] Launching New Browser Session...")

    # Start auto-typer thread for proxy popup
    t = threading.Thread(target=handle_login_popup)
    t.daemon = True
    t.start()

    options = uc.ChromeOptions()
    options.add_argument(f"--proxy-server=http://{PROXY_HOST}:{PROXY_PORT}")
    options.add_argument("--start-maximized")

    # Logging for performance (Network logs)
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    # Preferences (merged from both of your snippets)
    prefs = {
        "profile.managed_default_content_settings.images": 2,  # Disable images
        "profile.default_content_setting_values.notifications": 2,  # Block notifications
        "credentials_enable_service": False,  # Disable 'Save password'
        "profile.password_manager_enabled": False,  # Disable password manager
    }
    options.add_experimental_option("prefs", prefs)

    try:
        driver = uc.Chrome(options=options)
        driver.set_page_load_timeout(60)

        # Warm-up: trigger proxy popup, then verify IP (if possible)
        try:
            driver.get("https://api.ipify.org?format=json")
            time.sleep(10)  # Give time for handle_login_popup to type
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text
                print("[IP Check] Response from api.ipify.org:", body_text)
            except:
                pass
        except Exception as e:
            print("[System] Connection check skipped/failed:", e)

        return driver
    except Exception as e:
        print(f"[System] Driver Launch Error: {e}")
        return None


# --------------------------
# OTHER HELPER FUNCTIONS
# --------------------------
def check_for_block_page(driver):
    """Detects generic block / error pages."""
    try:
        txt = driver.find_element(By.TAG_NAME, "body").text
        if "Something went wrong" in txt:
            return True
        # Custom block element you mentioned
        if driver.find_elements(By.CLASS_NAME, "Cuiq3OWYztM-"):
            return True
    except:
        pass
    return False


def wait_for_new_json(driver, existing_ids, timeout=10):
    """
    Wait for a NEW Network.responseReceived event whose URL contains 'schemas?'.
    Only returns True if the requestId wasn't already in existing_ids.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            logs = driver.get_log("performance")
        except Exception:
            time.sleep(0.5)
            continue

        for entry in logs:
            try:
                msg = json.loads(entry["message"])["message"]
                if msg["method"] == "Network.responseReceived":
                    url = msg["params"]["response"]["url"]
                    if "schemas?" in url:
                        req_id = msg["params"]["requestId"]
                        if req_id not in existing_ids:
                            return True
            except:
                continue

        time.sleep(0.5)

    return False


def scroll_to_bottom(driver):
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
    except:
        pass


def click_all_show_more_buttons(driver, max_clicks=MAX_SHOW_MORE_CLICKS):
    """
    Clicks all visible 'show more' buttons up to max_clicks.
    """
    clicks = 0
    while clicks < max_clicks:
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, "button._710xV-kIMAg-")
            buttons = [b for b in buttons if b.is_displayed()]
            if not buttons:
                break

            clicked = False
            for btn in buttons:
                if clicks >= max_clicks:
                    break
                try:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", btn
                    )
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(1.5)
                    clicks += 1
                    clicked = True
                except:
                    continue

            if not clicked:
                break
        except:
            break


def harvest_json_logs(driver, processed_ids):
    """
    Extract ONLY new JSON responses from performance logs.
    We consider URLs that contain 'schemas?' AND 'branchId='.
    Returns a list of parsed JSON bodies and the updated processed_ids set.
    """
    captured = []
    try:
        logs = driver.get_log("performance")
    except Exception:
        return captured, processed_ids

    for entry in logs:
        try:
            msg = json.loads(entry["message"])["message"]
            if msg["method"] == "Network.responseReceived":
                params = msg["params"]
                url = params["response"]["url"]
                req_id = params["requestId"]

                if "schemas?" in url and "branchId=" in url:
                    if req_id in processed_ids:
                        continue

                    # Mark as processed immediately
                    processed_ids.add(req_id)

                    try:
                        res = driver.execute_cdp_cmd(
                            "Network.getResponseBody", {"requestId": req_id}
                        )
                        captured.append(json.loads(res["body"]))
                    except:
                        pass
        except:
            continue

    return captured, processed_ids


# --------------------------
# MAIN SCRIPT
# --------------------------
def main():
    if not os.path.exists(INPUT_FILE):
        print(f"[Error] Input file '{INPUT_FILE}' not found.")
        return

    df_input = pd.read_excel(INPUT_FILE)

    driver = start_browser_with_proxy()
    if driver is None:
        print("[Fatal] Could not start browser with proxy.")
        return

    wait = WebDriverWait(driver, TIMEOUT_SECONDS)

    # GLOBAL tracker for JSON request IDs
    processed_req_ids = set()

    for idx, row in df_input.iterrows():
        url_id = row["ID"]
        start_url = row["URL"]

        if pd.isna(start_url):
            continue

        # Periodic restart of browser
        if idx > 0 and idx % RESTART_EVERY_N_URLS == 0:
            print(f"\n[Maintenance] Restarting browser after {idx} URLs...")
            try:
                driver.quit()
            except:
                pass
            driver = start_browser_with_proxy()
            if driver is None:
                print("[Fatal] Could not restart browser with proxy.")
                return
            wait = WebDriverWait(driver, TIMEOUT_SECONDS)
            processed_req_ids = set()

        attempt = 0
        success = False

        while attempt < MAX_RETRIES_PER_URL and not success:
            attempt += 1
            print(
                f"\nProcessing {idx + 1}/{len(df_input)} | ID: {url_id} | Attempt {attempt}"
            )

            fatal_error = False

            try:
                # 1. LOAD PAGE
                try:
                    driver.get(start_url)
                except:
                    fatal_error = True

                if check_for_block_page(driver):
                    fatal_error = True

                if not fatal_error:
                    try:
                        wait.until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "ul._4uWvJ1pkaiA-")
                            )
                        )
                        time.sleep(2)
                    except:
                        fatal_error = True

                if fatal_error:
                    print(" -> Load error / block page. Restarting browser...")
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = start_browser_with_proxy()
                    if driver is None:
                        print("[Fatal] Could not restart browser with proxy.")
                        return
                    wait = WebDriverWait(driver, TIMEOUT_SECONDS)
                    processed_req_ids = set()
                    continue

                # 2. ITERATE CATEGORIES
                category_lis = driver.find_elements(
                    By.CSS_SELECTOR, "ul._4uWvJ1pkaiA- > li"
                )
                total_items_for_car = 0

                for c_idx in range(len(category_lis)):
                    try:
                        # Refresh DOM each loop
                        cats = driver.find_elements(
                            By.CSS_SELECTOR, "ul._4uWvJ1pkaiA- > li"
                        )
                        if c_idx >= len(cats):
                            break

                        cat_li = cats[c_idx]
                        cat_name = cat_li.text.strip()

                        # Skip unwanted categories
                        if any(s in cat_name for s in SKIP_CATEGORIES):
                            continue

                        if check_for_block_page(driver):
                            fatal_error = True
                            break

                        # CLICK CATEGORY
                        link = cat_li.find_element(By.TAG_NAME, "a")
                        driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", link
                        )
                        try:
                            link.click()
                        except:
                            driver.execute_script("arguments[0].click();", link)

                        # Wait for NEW JSON (not seen before)
                        data_changed = wait_for_new_json(
                            driver, processed_req_ids, timeout=8
                        )

                        if not data_changed:
                            # Assume IP flagged / no data returned
                            print(
                                f"   -> Skipped '{cat_name}' (No new JSON). "
                                f"Assuming IP flagged or stale data."
                            )
                            fatal_error = True
                            break

                        # Scroll & click "Show more" buttons
                        scroll_to_bottom(driver)
                        click_all_show_more_buttons(
                            driver, max_clicks=MAX_SHOW_MORE_CLICKS
                        )

                        # HARVEST JSON from logs
                        batches, processed_req_ids = harvest_json_logs(
                            driver, processed_req_ids
                        )

                        batch_results = []
                        for data in batches:
                            try:
                                b_id = data["group"]["id"]
                                c_name = data["group"]["name"]

                                for item in data["list"]:
                                    g_id = item.get("groupId")
                                    if g_id:
                                        final_url = (
                                            f"{start_url}&branchId={b_id}&groupId={g_id}"
                                        )
                                        batch_results.append(
                                            {
                                                "ID": url_id,
                                                "Input URL": start_url,
                                                "Category": c_name,
                                                "Group": item.get("name"),
                                                "Group URL": final_url,
                                            }
                                        )
                            except:
                                continue

                        if batch_results:
                            pd.DataFrame(batch_results).to_csv(
                                OUTPUT_FILE, mode="a", header=False, index=False
                            )
                            print(
                                f"   -> Captured {len(batch_results)} items from '{cat_name}'"
                            )
                            total_items_for_car += len(batch_results)

                    except Exception:
                        # Any category-level error: just continue to next category
                        continue

                # END FOR categories

                if not fatal_error:
                    if total_items_for_car > 0:
                        print(f" -> DONE. Total saved for this ID: {total_items_for_car}")
                        success = True
                    else:
                        print(
                            " -> No items found for this car (or fatal error in loop). Retrying."
                        )
                        fatal_error = True

                if fatal_error and not success:
                    print(" -> Fatal error or IP Flag detected. Restarting Browser...")
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = start_browser_with_proxy()
                    if driver is None:
                        print("[Fatal] Could not restart browser with proxy.")
                        return
                    wait = WebDriverWait(driver, TIMEOUT_SECONDS)
                    processed_req_ids = set()

            except Exception as e:
                print(f" -> Error: {e}")
                try:
                    driver.quit()
                except:
                    pass
                driver = start_browser_with_proxy()
                if driver is None:
                    print("[Fatal] Could not restart browser with proxy.")
                    return
                wait = WebDriverWait(driver, TIMEOUT_SECONDS)
                processed_req_ids = set()

    print("\nJob Complete.")
    try:
        driver.quit()
    except:
        pass


if __name__ == "__main__":
    main()