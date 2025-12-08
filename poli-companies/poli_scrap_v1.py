import json
import os
import time
import base64
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


BASE_URL = "https://app.withpoli.com/companies"
OUTPUT_FILENAME = "withpoli_companies.xlsx"


def get_driver() -> webdriver.Chrome:
    """Create a visible Chrome driver with performance logs enabled."""
    chrome_options = Options()
    # visible browser
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    # enable performance logging for DevTools Network events
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    service = Service()  # uses chromedriver on PATH
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # enable Network domain in CDP
    driver.execute_cdp_cmd("Network.enable", {})
    return driver


def fetch_companies_json(driver: webdriver.Chrome, timeout: int = 30) -> dict:
    """Open page, capture companies JSON via DevTools, and return it as dict."""
    driver.get(BASE_URL)
    print("Waiting for API to load...")
    time.sleep(5)

    end_time = time.time() + timeout
    target_request_id = None

    # 1) Find the right Network response: XHR/Fetch + JSON + 'companies' in URL
    while time.time() < end_time and target_request_id is None:
        logs = driver.get_log("performance")
        for entry in logs:
            try:
                message = json.loads(entry["message"])["message"]
            except (json.JSONDecodeError, KeyError):
                continue

            if message.get("method") != "Network.responseReceived":
                continue

            params = message.get("params", {})
            response = params.get("response", {})
            url = response.get("url", "")
            mime = response.get("mimeType", "")
            rtype = params.get("type", "")

            # limit to XHR/Fetch JSON calls containing 'companies'
            if (
                "companies" in url
                and mime == "application/json"
                and rtype in ("XHR", "Fetch")
            ):
                target_request_id = params.get("requestId")
                print("Captured request ID:", target_request_id)
                break

        if target_request_id is None:
            time.sleep(1)

    if target_request_id is None:
        raise RuntimeError("Could not detect the companies JSON API request.")

    # 2) Get the response body (handle base64Encoded)
    for attempt in range(1, 6):
        print(f"Fetching response body attempt {attempt}/5...")
        body = driver.execute_cdp_cmd(
            "Network.getResponseBody", {"requestId": target_request_id}
        )

        text = body.get("body", "")
        if body.get("base64Encoded"):
            try:
                text = base64.b64decode(text).decode("utf-8", errors="ignore")
            except Exception:
                text = ""

        text = text.strip()
        if not text:
            time.sleep(1)
            continue

        try:
            data = json.loads(text)
            return data
        except json.JSONDecodeError:
            # not valid JSON, try again
            time.sleep(1)

    raise RuntimeError("API body was captured but not valid JSON after several tries.")


def extract_companies(data: dict) -> list[dict]:
    """Extract required fields from JSON to a list of rows."""
    companies = data.get("data", {}).get("companies", [])
    rows = []

    for idx, c in enumerate(companies, start=1):
        rows.append(
            {
                "Company Name": c.get("trading_name", ""),
                "Company URL": c.get("url", ""),
                "Linkedin URL": c.get("url_linkedin", ""),
                "Description": c.get("description", ""),
                "Active Job Count": c.get("active_jobs_count", 0),
                "Logo Image": c.get("url_favicon", ""),
                "Policy": c.get("policy", ""),
                "Company Level": c.get("estimated_num_employees_label", ""),
            }
        )
        # EXACT format required
        print(f"Total Comapny Scraped: {idx}")

    return rows


def save_to_excel(rows: list[dict]) -> str:
    df = pd.DataFrame(rows)
    output_path = os.path.join(os.getcwd(), OUTPUT_FILENAME)
    df.to_excel(output_path, index=False)
    return output_path


def main():
    driver = get_driver()
    try:
        data = fetch_companies_json(driver)
        rows = extract_companies(data)
        path = save_to_excel(rows)
        print(f"\nSaved data for {len(rows)} companies to: {path}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()