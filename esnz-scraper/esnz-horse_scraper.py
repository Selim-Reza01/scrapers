import time
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options


def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver


def extract_horse_data(card):
    data = {}

    # Horse Name
    try:
        data["Horse Name"] = card.find_element(By.CSS_SELECTOR, ".name").text.strip()
    except:
        data["Horse Name"] = ""

    # Key-value detail items
    items = card.find_elements(By.CSS_SELECTOR, ".details .item")
    for item in items:
        try:
            spans = item.find_elements(By.TAG_NAME, "span")
            if len(spans) >= 2:
                label = spans[0].text.strip().replace(":", "")
                value = spans[-1].text.strip()
                data[label] = value
        except:
            pass

    # Registration Groups
    groups = card.find_elements(By.CSS_SELECTOR, ".groups .block")
    discipline_text = ""  # To detect Valid Status

    for g in groups:
        try:
            key = g.find_elements(By.TAG_NAME, "span")[0].text.strip()
            val = g.find_elements(By.TAG_NAME, "span")[1].text.strip()

            # Track discipline for VALID STATUS
            if "Jumping & Show Hunter Horse" in key or "Jumping & Show Hunter Horse" in val:
                discipline_text = "Jumping & Show Hunter Horse"

            # Handle duplicate keys
            if key in data:
                i = 2
                while f"{key}_{i}" in data:
                    i += 1
                data[f"{key}_{i}"] = val
            else:
                data[key] = val

        except:
            pass

    # ⭐ Add Valid Status Column
    if "Jumping & Show Hunter Horse" in discipline_text:
        data["Valid Status"] = "Valid"
    else:
        data["Valid Status"] = "Not Valid"

    return data


def save_to_excel(records, filename="horse_scraped_data.xlsx"):
    df_new = pd.DataFrame(records)

    if os.path.exists(filename):  
        df_existing = pd.read_excel(filename)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new

    df_combined.to_excel(filename, index=False)
    print(f"💾 Saved {len(df_combined)} total records to {filename}")


def scrape_all():
    driver = create_driver()
    url = "https://horsereg.com/#!/horselookup/esnz-horses?next=%2Fhorselookup%2Fesnz-horses"
    driver.get(url)

    print("🔵 Please log in manually, then press ENTER here to continue...")
    input()

    page = 1
    total_pages = 1690  
    filename = "horse_scraped_data.xlsx"

    # Remove old file to avoid mixing old scrapings
    if os.path.exists(filename):
        os.remove(filename)

    while page <= total_pages:
        print(f"\n📄 Scraping page {page}/{total_pages} ...")
        time.sleep(3)

        cards = driver.find_elements(By.CSS_SELECTOR, ".result-card")
        page_records = []

        for card in cards:
            page_records.append(extract_horse_data(card))

        # ⭐ SAVE OUTPUT IMMEDIATELY AFTER EACH PAGE ⭐
        save_to_excel(page_records, filename)

        # Next page
        try:
            next_btn = driver.find_element(By.XPATH, "//a[@ng-click='setCurrent(pagination.current + 1)']")
            driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
            ActionChains(driver).move_to_element(next_btn).click().perform()
        except:
            print("⚠️ No next page button found. Stopping.")
            break

        page += 1
        time.sleep(2)

    driver.quit()
    print("\n✅ COMPLETED! All pages scraped.")


if __name__ == "__main__":
    scrape_all()
