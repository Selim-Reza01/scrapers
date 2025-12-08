#!/usr/bin/env python
# coding: utf-8

import asyncio
import contextlib
import os
import re
import sys
import time
from typing import List, Dict, Set, Tuple, Optional

import pandas as pd
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PWTimeout

SERIES_ANCHOR_SELECTOR = (
    "div.Table_vshSerLnk__H5wPI a[href^='/en/product/'], "
    "div.Webtable_vshSerLnk__X0mQK a[href^='/en/product/'], "
    "td[role='cell'] a[href^='/en/product/']:not([href*='/doc?'])"
)

LIST_NEXT_BUTTON_SELECTORS = [
    "button.Table_vshNextBtn__1KHAv",
    "button.Table_vshBtn__HoJs9.Table_vshNextBtn__1KHAv",
    "button:has-text('Next')",
]

QUALITY_TABLE_SELECTOR = "div.Table_vshGentblContainer__2axM2 table[role='table']"
QUALITY_THEAD_TH = f"{QUALITY_TABLE_SELECTOR} thead th"
QUALITY_TBODY_ROWS = f"{QUALITY_TABLE_SELECTOR} tbody tr"
QUALITY_NEXT_BUTTON_SELECTORS = [
    "#Table_vshNextBtn__1KHAv",
    "button.Table_vshBtn__HoJs9#Table_vshNextBtn__1KHAv",
    "button:has-text('Next')",
]

CONCURRENCY = 8
NAV_TIMEOUT_MS = 35000
CLICK_RETRY = 3
ROW_WAIT_MS = 10000
SLOWMO_MS = 0

# I/O
DEFAULT_INPUT_XLSX = r"D:\Upwork\Project 3\input_file.xlsx"
DEFAULT_OUT_DIR = r"D:\Upwork\Project 3\outputs"
DEFAULT_STATUS_XLSX = r"D:\Upwork\Project 3\status.xlsx"

def build_quality_url(series_url: str) -> str:
    series_url = series_url.rstrip("/")
    if not series_url.endswith("/tab/quality"):
        series_url = series_url + "/tab/quality/"
    return series_url

def safe_text(el) -> str:
    return (el or "").strip()

def sanitize_filename(s: str) -> str:
    s = re.sub(r"[\\/:*?\"<>|]+", "_", s)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s or "result"

async def ensure_cookie_banner_closed(page: Page):
    candidates = [
        "button:has-text('Accept')",
        "button:has-text('I Agree')",
        "button:has-text('Got it')",
        "button:has-text('Allow all')",
        "text=Accept",
    ]
    for sel in candidates:
        with contextlib.suppress(Exception):
            btn = page.locator(sel)
            if await btn.count() > 0:
                await btn.first.click(timeout=2000)
                await asyncio.sleep(0.2)

async def click_with_retries(page: Page, selectors: List[str], timeout_ms: int = 5000) -> bool:
    for attempt in range(CLICK_RETRY):
        for sel in selectors:
            try:
                btn = page.locator(sel)
                if await btn.count() == 0:
                    continue
                await btn.first.click(timeout=timeout_ms)
                await asyncio.sleep(0.25)
                return True
            except PWTimeout:
                continue
            except Exception:
                continue
        await asyncio.sleep(0.25 * (attempt + 1))
    return False

async def is_next_disabled(page: Page, selectors: List[str]) -> bool:
    for sel in selectors:
        btn = page.locator(sel)
        if await btn.count() > 0:
            try:
                disabled_attr = await btn.first.get_attribute("disabled")
                aria_disabled = await btn.first.get_attribute("aria-disabled")
                classes = (await btn.first.get_attribute("class")) or ""
                if (disabled_attr is not None) or (aria_disabled == "true") or ("disabled" in classes):
                    return True
                if await btn.first.is_disabled():
                    return True
                return False
            except Exception:
                return False
    return True

async def wait_for_table_rows(page: Page, timeout_ms: int) -> bool:
    try:
        await page.wait_for_selector(QUALITY_TBODY_ROWS, timeout=timeout_ms)
        return True
    except PWTimeout:
        return False

async def load_all_series_from(page: Page, root_list_url: str) -> List[Tuple[str, str]]:
    await page.goto(root_list_url, timeout=NAV_TIMEOUT_MS)
    await ensure_cookie_banner_closed(page)
    await page.wait_for_load_state("domcontentloaded")
    seen: Set[str] = set()
    series: List[Tuple[str, str]] = []

    while True:
        await page.wait_for_selector(SERIES_ANCHOR_SELECTOR, timeout=NAV_TIMEOUT_MS)
        anchors = page.locator(SERIES_ANCHOR_SELECTOR)
        count = await anchors.count()
        for i in range(count):
            a = anchors.nth(i)
            href = await a.get_attribute("href")
            text = (await a.inner_text() or "").strip()
            if not href:
                continue
            if "/doc?" in href:
                continue
            abs_url = "https://www.vishay.com" + href if href.startswith("/") else href
            if abs_url not in seen:
                seen.add(abs_url)
                series.append((abs_url, text))
        if await is_next_disabled(page, LIST_NEXT_BUTTON_SELECTORS):
            break

        clicked = await click_with_retries(page, LIST_NEXT_BUTTON_SELECTORS, timeout_ms=7000)
        if not clicked:
            break

        await asyncio.sleep(0.4)

    return series

async def extract_table(page: Page, series_url: str, series_text: str) -> List[Dict[str, str]]:
    """Extract all rows from the quality tab table, paging with Next → till the end (same behavior as your code)."""
    records: List[Dict[str, str]] = []

    if not await wait_for_table_rows(page, ROW_WAIT_MS):
        return records

    headers: List[str] = []
    try:
        ths = page.locator(QUALITY_THEAD_TH)
        count = await ths.count()
        for i in range(count):
            headers.append((await ths.nth(i).inner_text()).strip())
    except Exception:
        headers = [
            "Part Number", "RoHS-Compliant", "Lead (Pb)-Free", "MSL Designation",
            "Device Termination Plating Finish", "Halogen-Free", "GREEN", "Qualification"
        ]

    while True:
        await wait_for_table_rows(page, ROW_WAIT_MS)
        rows = page.locator(QUALITY_TBODY_ROWS)
        rcount = await rows.count()
        for i in range(rcount):
            tds = rows.nth(i).locator("td")
            tcount = await tds.count()
            row_vals = []
            for j in range(tcount):
                txt = safe_text(await tds.nth(j).inner_text())
                row_vals.append(txt)
            if len(row_vals) < len(headers):
                row_vals += [""] * (len(headers) - len(row_vals))
            elif len(row_vals) > len(headers):
                row_vals = row_vals[:len(headers)]
            rec = dict(zip(headers, row_vals))
            rec["Series URL"] = series_url
            rec["Series Name"] = series_text
            rec["Quality Tab URL"] = page.url
            records.append(rec)
        if await is_next_disabled(page, QUALITY_NEXT_BUTTON_SELECTORS):
            break

        clicked = await click_with_retries(page, QUALITY_NEXT_BUTTON_SELECTORS, timeout_ms=5000)
        if not clicked:
            break
        await asyncio.sleep(0.4)

    return records

async def process_one_series(browser: Browser, series_url: str, series_text: str) -> List[Dict[str, str]]:
    page: Optional[Page] = None
    try:
        page = await browser.new_page()
        qurl = build_quality_url(series_url)
        await page.goto(qurl, timeout=NAV_TIMEOUT_MS)
        await ensure_cookie_banner_closed(page)
        with contextlib.suppress(PWTimeout):
            await page.wait_for_selector(QUALITY_TABLE_SELECTOR, timeout=7000)
        data = await extract_table(page, series_url, series_text)
        return data
    except Exception as e:
        print(f"[WARN] Failed {series_url}: {e}")
        return []
    finally:
        with contextlib.suppress(Exception):
            if page:
                await page.close()

async def scrape_list_url(root_list_url: str) -> pd.DataFrame:
    """Scrape a single list URL. Returns a DataFrame (may be empty)."""
    print("[*] Loading series list…")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=SLOWMO_MS)
        page = await browser.new_page()
        series = await load_all_series_from(page, root_list_url)
        print(f"[*] Found {len(series)} series URLs.")
        if not series:
            await browser.close()
            return pd.DataFrame()
        sem = asyncio.Semaphore(CONCURRENCY)
        results: List[Dict[str, str]] = []

        async def worker(item: Tuple[str, str]):
            url, text = item
            async with sem:
                recs = await process_one_series(browser, url, text)
                results.extend(recs)

        await asyncio.gather(*(worker(s) for s in series))

        await browser.close()

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)

    preferred = [
        "Part Number", "RoHS-Compliant", "Lead (Pb)-Free", "MSL Designation",
        "Device Termination Plating Finish", "Halogen-Free", "GREEN", "Qualification",
        "Series Name", "Series URL", "Quality Tab URL",
    ]
    cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
    df = df[cols]
    return df

def write_result_xlsx(df: pd.DataFrame, out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="All Parts", index=False)
        # Also include a distinct list of series for reference
        if not df.empty and {"Series Name", "Series URL"}.issubset(df.columns):
            series_df = pd.DataFrame(sorted({(r["Series Name"], r["Series URL"]) for r in df.to_dict("records")}),
                                     columns=["Series Name", "Series URL"])
        else:
            series_df = pd.DataFrame(columns=["Series Name", "Series URL"])
        series_df.to_excel(writer, sheet_name="Series List", index=False)

def append_status_row(status_path: str, row: Dict[str, str | int]):
    """Append/overwrite the status workbook on disk after each URL."""
    os.makedirs(os.path.dirname(status_path), exist_ok=True)
    if os.path.exists(status_path):
        try:
            existing = pd.read_excel(status_path)
        except Exception:
            existing = pd.DataFrame(columns=["Category", "Sub-Category", "URL", "Status", "Number of products"])
        df = pd.concat([existing, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row], columns=["Category", "Sub-Category", "URL", "Status", "Number of products"])
    with pd.ExcelWriter(status_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Status", index=False)

def main():
    args = sys.argv[1:]
    input_xlsx = DEFAULT_INPUT_XLSX
    out_dir = DEFAULT_OUT_DIR
    status_xlsx = DEFAULT_STATUS_XLSX

    if "--input" in args:
        try:
            input_xlsx = args[args.index("--input") + 1]
        except Exception:
            print("[!] --input provided but no path found. Using default.")
    if "--outdir" in args:
        try:
            out_dir = args[args.index("--outdir") + 1]
        except Exception:
            print("[!] --outdir provided but no folder found. Using default.")
    if "--status" in args:
        try:
            status_xlsx = args[args.index("--status") + 1]
        except Exception:
            print("[!] --status provided but no path found. Using default.")

    try:
        input_df = pd.read_excel(input_xlsx)
    except Exception as e:
        print(f"[!] Failed to read input file: {input_xlsx} ({e})")
        sys.exit(1)

    required_cols = {"Category", "Sub-Category", "URL"}
    if not required_cols.issubset(set(input_df.columns)):
        print(f"[!] Input must contain columns: {required_cols}")
        sys.exit(1)

    total = len(input_df)
    for idx, row in input_df.iterrows():
        i = idx + 1
        category = str(row["Category"]) if not pd.isna(row["Category"]) else ""
        subcat = str(row["Sub-Category"]) if not pd.isna(row["Sub-Category"]) else ""
        url = str(row["URL"]).strip()

        print(f"Processing {i} out of {total}")
        status = "failed"
        num_products = 0

        try:
            async def probe_series(url_):
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True, slow_mo=SLOWMO_MS)
                    page = await browser.new_page()
                    try:
                        series = await load_all_series_from(page, url_)
                    finally:
                        await browser.close()
                return series

            series_list = asyncio.run(probe_series(url))
            if not series_list:
                print("[*] No series found on this list page. Skipping.")
                status = "skip"
                num_products = 0
                base = f"{i:03d}_{sanitize_filename(category or 'category')}_{sanitize_filename(subcat or 'subcat')}"
                out_path = os.path.join(out_dir, f"{base}.xlsx")
                write_result_xlsx(pd.DataFrame(), out_path)
                append_status_row(status_xlsx, {
                    "Category": category, "Sub-Category": subcat, "URL": url,
                    "Status": status, "Number of products": num_products
                })
                continue
            df = asyncio.run(scrape_list_url(url))
            num_products = len(df)
            base = f"{i:03d}_{sanitize_filename(category or 'category')}_{sanitize_filename(subcat or 'subcat')}"
            out_path = os.path.join(out_dir, f"{base}.xlsx")
            write_result_xlsx(df, out_path)

            if df.empty:
                status = "success"
                print(f"[*] Wrote 0 rows to: {out_path} (no quality rows found)")
            else:
                status = "success"
                print(f"[*] Wrote {num_products} rows to: {out_path}")

        except Exception as e:
            status = "failed"
            print(f"[WARN] URL failed: {url} ({e})")
        append_status_row(status_xlsx, {
            "Category": category,
            "Sub-Category": subcat,
            "URL": url,
            "Status": status,
            "Number of products": num_products
        })

if __name__ == "__main__":
    main()
