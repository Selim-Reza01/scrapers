import os, sys, json, re, asyncio, time
import pandas as pd
from pathlib import Path
from typing import Tuple, List
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

# ========= Paths / Config =========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARTS_XLSX    = os.path.join(BASE_DIR, "input_parts.xlsx")
OUTPUT_DIR    = os.path.join(BASE_DIR, "PDFs")
RESULTS_XLSX  = os.path.join(BASE_DIR, "results.xlsx")
USER_DATA     = os.path.join(BASE_DIR, "user_data")
COOKIES_JSON  = os.path.join(BASE_DIR, "cookies.json")
HOMEPAGE      = "https://www.newark.com/"
HEADLESS      = False
MAX_WORKERS   = 3
EXTRA_WAIT    = 0.6

SHORT = 0.15

def ensure_dirs():
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(USER_DATA).mkdir(parents=True, exist_ok=True)

def read_parts() -> List[str]:
    if not os.path.exists(PARTS_XLSX):
        raise FileNotFoundError(f"Excel not found: {PARTS_XLSX}")
    df = pd.read_excel(PARTS_XLSX)
    if "part_number" not in df.columns:
        raise RuntimeError("parts.xlsx must have a column named 'part_number'")
    return [str(x).strip() for x in df["part_number"].tolist() if str(x).strip()]

def save_results(rows):
    pd.DataFrame(rows, columns=["part_number","status","note"]).to_excel(RESULTS_XLSX, index=False)

def load_and_normalize_cookies():
    if not os.path.exists(COOKIES_JSON):
        return []
    raw = json.load(open(COOKIES_JSON, "r", encoding="utf-8"))
    out = []
    for c in raw:
        name = c.get("name"); value = c.get("value","")
        domain = c.get("domain",""); path = c.get("path") or "/"
        secure = bool(c.get("secure", True)); httpOnly = bool(c.get("httpOnly", False))
        session = bool(c.get("session", False))
        same_site_raw = c.get("sameSite")
        if same_site_raw is None: same_site = "Lax"
        else:
            s = str(same_site_raw).lower()
            same_site = "None" if "no_restriction" in s or s=="none" else ("Strict" if "strict" in s else "Lax")
        expires = None
        if not session:
            exp = c.get("expirationDate") or c.get("expiry")
            if exp:
                try: expires = int(float(exp))
                except: expires = None
        out.append({
            "name": name, "value": value, "domain": domain, "path": path,
            "secure": secure, "httpOnly": httpOnly, "sameSite": same_site,
            **({"expires": expires} if expires else {})
        })
    return out

# ======== Helpers (no reloads, no direct product navigation) ========
async def get_search_input(page):
    for sel in [
        "#search-bar__search__input",
        "input[role='searchbox']",
        "input[data-testid*='search__input']",
        "input[type='search']",
    ]:
        loc = page.locator(sel)
        if await loc.count() > 0:
            first = loc.first
            try:
                if await first.is_visible():
                    return first
            except Exception:
                pass
    return None

async def search_part_enter_only(page, part: str) -> Tuple[bool,str]:
    """Type part and press Enter ONCE. Do not click buttons or resubmit."""
    sinput = await get_search_input(page)
    if not sinput:
        return False, "search input not found"
    await sinput.click()
    await asyncio.sleep(SHORT)
    await sinput.fill(part)
    await asyncio.sleep(SHORT)
    await sinput.press("Enter")  # single enter only
    return True, ""

async def wait_until_product_context(page, timeout_sec: float = 20.0) -> Tuple[bool,str]:
    try:
        await page.wait_for_url(re.compile(r".*/dp/.*"), timeout=int(timeout_sec*1000))
        await asyncio.sleep(0.6)
        return True, ""
    except Exception:
        pass

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if "/dp/" in (page.url or ""):
            await asyncio.sleep(0.6)
            return True, ""
        if await page.locator("h2:has-text('Legislation and Environmental')").count() or \
           await page.locator("span:has-text('Download Product Compliance Certificate')").count():
            await asyncio.sleep(0.6)
            return True, ""
        await asyncio.sleep(0.25)
    return False, "product view not detected"

async def open_pdf_from_product_page(page, context, part: str, extra_wait: float) -> Tuple[bool,str]:
    for y in (0.55, 0.7, 0.85, 0.95):
        try:
            await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight*{y});")
        except Exception:
            pass
        await asyncio.sleep(0.35 + extra_wait)

    try:
        await page.wait_for_selector("h2:has-text('Legislation and Environmental')", timeout=7000)
    except PWTimeout:
        pass

    row = page.locator("span:has-text('Download Product Compliance Certificate')").first
    if not (await row.count()):
        await asyncio.sleep(0.8)
        row = page.locator("span:has-text('Download Product Compliance Certificate')").first
        if not (await row.count()):
            return False, "Legislation row not found"

    try:
        await row.scroll_into_view_if_needed(timeout=3000)
        await asyncio.sleep(SHORT)
    except Exception:
        pass

    container = row.locator("xpath=ancestor::div[1]").locator("[data-testid*='__rohs-button']").first
    if not (await container.count()):
        container = page.locator("[data-testid*='__rohs-button']").first

    trigger = None
    if await container.count():
        trg = container.locator("p:has-text('Product Compliance Certificate'), span:has-text('Product Compliance Certificate')")
        if await trg.count():
            trigger = trg.first
    if trigger is None:
        trigger = page.locator("p:has-text('Product Compliance Certificate'), span:has-text('Product Compliance Certificate')").first
        if not (await trigger.count()):
            return False, "Product Compliance Certificate trigger not visible"

    try:
        await trigger.hover()
        await asyncio.sleep(SHORT)
        await trigger.click()
    except Exception as e:
        return False, f"trigger click error: {e}"

    try:
        await page.wait_for_selector("button[data-testid='catalog.modal.footer__button-primary']", timeout=12000)
    except PWTimeout:
        return False, "modal not shown"

    pbtn = page.locator("button[data-testid='catalog.modal.footer__button-primary']:has-text('PDF Certificate')").first
    if not (await pbtn.count()):
        pbtn = page.locator("button:has-text('PDF Certificate')").first
        if not (await pbtn.count()):
            return False, "PDF button not visible"

    filename = os.path.join(OUTPUT_DIR, f"{part}.pdf")

    # 1) direct browser download
    try:
        async with page.expect_download(timeout=int((10+extra_wait)*1000)) as d_info:
            await pbtn.hover()
            await asyncio.sleep(SHORT)
            await pbtn.click()
        download = await d_info.value
        await download.save_as(filename)
        return True, ""
    except PWTimeout:
        pass
    except Exception:
        pass

    # 2) popup/new page with PDF
    newp = None
    try:
        async with context.expect_page(timeout=int((10+extra_wait)*1000)) as p_info:
            try:
                await pbtn.click()
            except Exception:
                pass
        newp = await p_info.value
    except PWTimeout:
        newp = None
    except Exception:
        newp = None

    async def fetch_to_file(url: str) -> bool:
        if not url: return False
        if url.startswith("/"): url = "https://www.newark.com" + url
        try:
            resp = await context.request.get(url, timeout=15000)
            if resp.ok:
                content = await resp.body()
                with open(filename, "wb") as f:
                    f.write(content)
                return True
        except Exception:
            return False
        return False

    if newp:
        try:
            await newp.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        url = newp.url or ""
        if ".pdf" in url.lower():
            if await fetch_to_file(url): return True, ""
        for sel in ["embed[type='application/pdf']",
                    "iframe[src*='.pdf']",
                    "a[href$='.pdf']",
                    "a[href*='.pdf?']"]:
            el = newp.locator(sel).first
            if await el.count():
                href = await el.get_attribute("src") or await el.get_attribute("href")
                if href and await fetch_to_file(href): return True, ""

    # 3) any visible link in current page
    try:
        a = page.locator("a[href$='.pdf'], a[href*='.pdf?']").first
        if await a.count():
            href = await a.get_attribute("href")
            if href and await fetch_to_file(href):
                return True, ""
    except Exception:
        pass

    return False, "no download detected"

async def process_part(context, part: str) -> Tuple[str,str]:
    page = await context.new_page()
    page.set_default_navigation_timeout(30000)
    page.set_default_timeout(15000)
    try:
        await page.goto(HOMEPAGE, wait_until="domcontentloaded")
        await asyncio.sleep(SHORT)

        ok, note = await search_part_enter_only(page, part)
        if not ok: return "fail", note

        ok, note = await wait_until_product_context(page, timeout_sec=20)
        if not ok: return "fail", note

        ok, note = await open_pdf_from_product_page(page, context, part, extra_wait=EXTRA_WAIT)
        return ("success","") if ok else ("fail", note)
    except PWTimeout as e:
        return "error", f"timeout: {e}"
    except Exception as e:
        return "error", f"{type(e).__name__}: {e}"
    finally:
        try:
            await page.close()
        except Exception:
            pass

async def run_all(parts: List[str]):
    ensure_dirs()
    cookies = load_and_normalize_cookies()

    rows: List[Tuple[str,str,str]] = []
    done = 0
    total = len(parts)
    lock = asyncio.Lock()
    sem = asyncio.Semaphore(MAX_WORKERS)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            USER_DATA,
            headless=HEADLESS,
            accept_downloads=True,
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
        )

        # Anti-bot softening
        for js in [
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
            "Object.defineProperty(navigator, 'languages', { get: () => ['en-US','en'] })",
            "Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4] })",
        ]:
            await context.add_init_script(js)

        if cookies:
            await context.add_cookies(cookies)

        async def worker(part: str):
            nonlocal done
            async with sem:
                status, note = await process_part(context, part)
                async with lock:
                    done += 1
                    # Print ONE line that updates in place
                    summary = "success" if status == "success" else ("fail" if status == "fail" else "error")
                    sys.stdout.write(f"\rProcess: {done}/{total} {summary}      ")
                    sys.stdout.flush()
                    rows.append((part, status, note))

        tasks = [asyncio.create_task(worker(pn)) for pn in parts]
        await asyncio.gather(*tasks)

        await context.close()

    # Make sure the progress line ends with newline
    sys.stdout.write("\n")
    save_results(rows)
    print(f"Saved log: {RESULTS_XLSX}")
    print(f"PDFs: {OUTPUT_DIR}")

def main():
    parts = read_parts()
    asyncio.run(run_all(parts))

if __name__ == "__main__":
    main()