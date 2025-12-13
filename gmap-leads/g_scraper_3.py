import os
import re
import threading
import pandas as pd
import requests
from bs4 import BeautifulSoup
from bs4 import XMLParsedAsHTMLWarning
from bs4 import MarkupResemblesLocatorWarning
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

# ================= CONFIG =================
INPUT_FILE = "search_email.xlsx"
OUTPUT_FILE = "search_email_output.xlsx"
MAX_WORKERS = 20
SAVE_EVERY = 1000
TIMEOUT_SECS = 15
# ==========================================

# Only count strings with '@' as emails (visible text + mailto)
EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Avoid false positives like "...@2x.jpg"
IMAGE_ENDINGS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".avif", ".webm")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0 Safari/537.36"
    )
}

# Per-thread Session (connection pooling reused within the thread)
_thread_local = threading.local()

def get_session() -> requests.Session:
    sess = getattr(_thread_local, "session", None)
    if sess is None:
        sess = requests.Session()
        sess.headers.update(HEADERS)
        _thread_local.session = sess
    return sess

def normalize_url(url: str) -> str:
    if not isinstance(url, str):
        return ""
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url

def fetch(url: str):
    """
    Fetch with requests.Session; return (status_str, text or '').
    """
    try:
        resp = get_session().get(url, timeout=TIMEOUT_SECS)
        return str(resp.status_code), resp.text or ""
    except requests.RequestException:
        return "ERR", ""

def extract_visible_text(html_text: str) -> str:
    """
    Approximate 'visible text' by stripping tags. This won't execute JS.
    """
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "html.parser")
    # Some builders hide content inside <template>; include its text as well.
    for t in soup.find_all("template"):
        soup.append(t.get_text(" "))
    return soup.get_text(" ")

def extract_mailtos(html_text: str) -> set[str]:
    found = set()
    if not html_text:
        return found
    soup = BeautifulSoup(html_text, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().startswith("mailto:"):
            addr = href.split(":", 1)[1].split("?", 1)[0].strip()
            if "@" in addr and EMAIL_REGEX.fullmatch(addr):
                found.add(addr)
    return found

def extract_emails_from_visible(html_text: str) -> set[str]:
    """
    Only search visible text (and mailto:) for '@' per your requirement.
    """
    emails = set()

    # Visible text
    text = extract_visible_text(html_text)
    if "@" in text:
        emails.update(EMAIL_REGEX.findall(text))

    # mailto: links
    emails.update(extract_mailtos(html_text))

    # Clean false positives
    emails = {e for e in emails if not e.lower().endswith(IMAGE_ENDINGS)}
    return emails

def process_website(website: str):
    """
    Home → if emails found, stop; else try a few contact paths.
    Returns: (emails_set, main_status_code_str)
    """
    base = normalize_url(website)
    if not base:
        return set(), "NO_URL"

    base_no_slash = base.rstrip("/")

    # 1) Home
    main_status, html_home = fetch(base)
    emails = extract_emails_from_visible(html_home)
    if emails:
        return emails, main_status

    # 2) Contact fallbacks (stop at first with emails)
    for path in ("/contacts/", "/contact/", "/contact-us/"):
        _, html_c = fetch(base_no_slash + path)
        if html_c:
            new_emails = extract_emails_from_visible(html_c)
            if new_emails:
                emails.update(new_emails)
                break

    return emails, main_status

def worker(idx: int, website: str):
    emails, status = process_website(website)
    return idx, "; ".join(sorted(emails)) if emails else "", status

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Input file '{INPUT_FILE}' not found in current folder.")
        return

    df = pd.read_excel(INPUT_FILE)
    if "website" not in df.columns:
        print("The input file must have a 'website' column.")
        return

    total = len(df)
    emails_col = [""] * total
    status_col = [""] * total

    processed = 0
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, max(1, total))) as executor:
        futures = {}
        for idx, row in df.iterrows():
            website = str(row.get("website", "")).strip()
            futures[executor.submit(worker, idx, website)] = idx

        for fut in as_completed(futures):
            idx, emails_str, status = fut.result()
            emails_col[idx] = emails_str
            status_col[idx] = status

            processed += 1
            print(f"processing {processed} out of {total}", end="\r", flush=True)

            if processed % SAVE_EVERY == 0 or processed == total:
                df["email"] = emails_col
                df["status"] = status_col
                df.to_excel(OUTPUT_FILE, index=False)

    print()
    print(f"Done. Output saved as '{OUTPUT_FILE}' in the current folder.")

if __name__ == "__main__":
    main()
