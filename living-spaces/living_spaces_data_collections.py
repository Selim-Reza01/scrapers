#!/usr/bin/env python
# coding: utf-8

# In[8]:


import concurrent.futures
import random
import time
from typing import List, Tuple, Dict
from urllib.parse import urljoin
import os

import pandas as pd
import httpx
from bs4 import BeautifulSoup

BASE_LISTING_URL = "https://www.livingspaces.com/departments/rugs/area-rugs/p135361"
BASE_ORIGIN = "https://www.livingspaces.com/"
START_PAGE = 1               # ← set this to 153 if you only want to resume
END_PAGE = 155               # ← last page
OUTPUT_DIR = r"D:\Upwork\Discuss"

# ---------- Tuning ----------
MAX_WORKERS_PER_PAGE = 24    # ↑ a bit faster; lower if you see 403/429
REQUEST_TIMEOUT = 30
RETRY_TIMES = 4
RETRY_BASE_SLEEP = 1.0       # seconds (will add jitter)
SLEEP_BETWEEN_LIST_PAGES = 0.20
# ----------------------------

# A few realistic desktop UA strings (Chrome stable on Windows/macOS)
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
]

def make_headers(user_agent: str) -> Dict[str, str]:
    return {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
    }

def backoff_sleep(attempt: int):
    base = RETRY_BASE_SLEEP * (2 ** (attempt - 1))
    time.sleep(base + random.uniform(0.0, 0.6))

def build_listing_page_url(page_num: int) -> str:
    return BASE_LISTING_URL if page_num == 1 else f"{BASE_LISTING_URL}?pagenumber={page_num}"

def parse_listing_for_product_urls(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for a in soup.select("div.product-item a[href]"):
        href = a.get("href")
        if href and "/pdp-" in href:
            urls.append(urljoin(BASE_ORIGIN, href))
    # unique preserving order
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

def parse_product_variants(html: str, main_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one("div.other-sizes__list")
    urls = [main_url]  # always include main
    if container:
        for a in container.select("a[href]"):
            href = a.get("href")
            if href:
                full = urljoin(BASE_ORIGIN, href)
                if full not in urls:
                    urls.append(full)
    return urls

def get_with_retries(client: httpx.Client, url: str, referer: str = BASE_ORIGIN) -> httpx.Response:
    last_exc = None
    for attempt in range(1, RETRY_TIMES + 1):
        ua = random.choice(UA_POOL)
        headers = make_headers(ua)
        headers["Referer"] = referer
        try:
            r = client.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r
            if r.status_code in (403, 429, 503):
                last_exc = RuntimeError(f"HTTP {r.status_code}")
                backoff_sleep(attempt)
                continue
            r.raise_for_status()
            return r
        except (httpx.HTTPError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            last_exc = e
            backoff_sleep(attempt)
    raise last_exc if last_exc else RuntimeError("Unknown HTTP error")

def fetch_variants(client: httpx.Client, product_url: str) -> Tuple[str, List[str]]:
    r = get_with_retries(client, product_url, referer=BASE_LISTING_URL)
    urls = parse_product_variants(r.text, product_url)
    return product_url, urls  # includes main + variants

def main():
    with httpx.Client(http2=True, follow_redirects=True) as client:
        # warm-up
        try:
            _ = get_with_retries(client, BASE_ORIGIN, referer=BASE_ORIGIN)
        except Exception:
            pass

        # Data buckets
        listing_main_rows: List[Dict] = []     # page_number, url  (main only)
        flattened_rows: List[Dict] = []        # page_number, url  (main + variants)
        page_summary_rows: List[Dict] = []     # page, Url, variants, Total

        for page_num in range(START_PAGE, END_PAGE + 1):
            list_url = build_listing_page_url(page_num)
            try:
                list_resp = get_with_retries(client, list_url, referer=BASE_ORIGIN)
            except Exception as e:
                print(f"page {page_num}: FAILED to load listing page: {e}")
                time.sleep(0.5)
                continue

            product_urls = parse_listing_for_product_urls(list_resp.text)

            # Save main-only listing rows
            for u in product_urls:
                listing_main_rows.append({"page_number": page_num, "url": u})

            # Fetch variants in parallel
            variants_total_extra = 0
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS_PER_PAGE) as ex:
                futures = [ex.submit(fetch_variants, client, u) for u in product_urls]
                for fut in concurrent.futures.as_completed(futures):
                    try:
                        prod_url, urls_for_this_product = fut.result()  # includes main
                        # Flatten (tag to current page)
                        for u in urls_for_this_product:
                            flattened_rows.append({"page_number": page_num, "url": u})
                        # count extra variants for summary line
                        variants_total_extra += (len(urls_for_this_product) - 1)
                    except Exception:
                        # on error, count as single and record at least the main URL
                        flattened_rows.append({"page_number": page_num, "url": "UNKNOWN_URL"})

            urls_count = len(product_urls)
            total_urls_incl_variants = urls_count + variants_total_extra
            print(
                f"page {page_num}:\n"
                f"Url: {urls_count}\n"
                f"variants: {variants_total_extra}\n"
                f"Total: {total_urls_incl_variants}\n"
            )

            page_summary_rows.append({
                "page": page_num,
                "Url": urls_count,
                "variants": variants_total_extra,
                "Total": total_urls_incl_variants
            })

            time.sleep(SLEEP_BETWEEN_LIST_PAGES + random.uniform(0.0, 0.2))

    # ---- Write outputs ----
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path_list = os.path.join(OUTPUT_DIR, "listing_urls_by_page.xlsx")       # main only
    path_all  = os.path.join(OUTPUT_DIR, "all_urls_with_variants.xlsx")     # main + variants (flattened)
    path_sum  = os.path.join(OUTPUT_DIR, "page_summary.xlsx")               # page, Url, variants, Total

    # main only (keep duplicates off per page)
    df_listing = pd.DataFrame(listing_main_rows, columns=["page_number", "url"])
    df_listing.drop_duplicates(subset=["page_number", "url"], inplace=True)
    df_listing.sort_values(["page_number", "url"], inplace=True, ignore_index=True)
    df_listing.to_excel(path_list, index=False)

    # flattened: DO NOT de-dup so totals match printed numbers exactly
    df_all = pd.DataFrame(flattened_rows, columns=["page_number", "url"])
    df_all.to_excel(path_all, index=False)

    # page summary + SUM row
    df_sum = pd.DataFrame(page_summary_rows, columns=["page", "Url", "variants", "Total"]).sort_values("page")
    sum_row = pd.DataFrame([{
        "page": "SUM",
        "Url": int(df_sum["Url"].sum()),
        "variants": int(df_sum["variants"].sum()),
        "Total": int(df_sum["Total"].sum())
    }])
    df_sum_out = pd.concat([df_sum, sum_row], ignore_index=True)
    df_sum_out.to_excel(path_sum, index=False)

    # sanity check print
    print("✅ Done.")
    print(path_list)
    print(path_all)
    print(path_sum)
    print(f"Sanity: rows in all_urls_with_variants.xlsx = {len(df_all)} ; SUM(Total) = {int(df_sum['Total'].sum())}")

if __name__ == "__main__":
    main()

