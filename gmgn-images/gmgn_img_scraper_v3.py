import asyncio
import os
import re
import time
import random
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout, Page, ElementHandle

START_URL = "https://gmgn.ai/?chain=sol"
# Matches v2.webp URLs and captures the 32-hex id (group 2)
GMGN_IMG_RE = re.compile(r"https://gmgn\.ai/(external-res(?:-eu)?)/([a-f0-9]{32})_v2\.webp")

COLUMNS = [
    ("New", "NEW"),
    ("Almost bonded", "MC"),
    ("Migrated", "MIGRATED"),
]

SCROLL_STEP = 800
TICK_SLEEP = 0.35


# Input helpers
def ask_run_limits() -> Tuple[int, int]:
    """
    Ask for global run limits:
      - total unique images target for ALL/ (0 or blank = unlimited)
      - time limit in minutes (0 or blank = unlimited)
    Both can be unlimited; in that case the script runs until you close the terminal (Ctrl+C).
    """
    print("Specify run limits (leave blank or 0 for unlimited):")

    def ask(label: str) -> int:
        while True:
            raw = input(f"{label}: ").strip()
            if raw == "":
                return 0  # unlimited
            try:
                val = int(raw)
                if val < 0:
                    print("Please enter 0 (unlimited) or a positive integer.")
                    continue
                return val
            except Exception:
                print("Please enter a number like 0, 10, 20, 35...")

    total = ask("Total images (ALL)")
    minutes = ask("Time to run (minutes)")
    return total, minutes


# Filesystem helpers
def format_output_dir_bd() -> Path:
    """
    Create a timestamped session folder with only:
      - 'All Image/' (images)
      - 'all_urls.txt' (written at the end)
    """
    now = datetime.now()
    folder_name = f"{now.month}-{now.day}-{now.hour}"
    out_dir = Path.cwd() / folder_name
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "All Image").mkdir(exist_ok=True)
    return out_dir


def unique_path(base: Path) -> Path:
    """
    Provide a unique path only if needed. (We try not to create duplicates in All Image anyway.)
    Kept for safety in odd edge cases (non-matching filename patterns).
    """
    if not base.exists():
        return base
    stem, suffix = base.stem, base.suffix
    parent = base.parent
    i = 1
    while True:
        cand = parent / f"{stem}-{i}{suffix}"
        if not cand.exists():
            return cand
        i += 1


def save_unique_to_all(all_dir: Path, filename: str, data: bytes):
    """
    Ensure only one file per 32-hex id exists in All Image.
    Prefer _v2l.webp over _v2.webp. If _v2 exists and _v2l arrives later, upgrade it.
    """
    m = re.match(r"^([a-f0-9]{32})_(v2l|v2)\.webp$", filename)
    if not m:
        # Fallback: if filename doesn't match expected pattern, avoid duplicates by exact name
        dest = all_dir / filename
        if not dest.exists():
            dest.write_bytes(data)
        return

    base, variant = m.groups()  # base: 32-hex id, variant: v2l / v2
    v2l_path = all_dir / f"{base}_v2l.webp"
    v2_path = all_dir / f"{base}_v2.webp"

    if v2l_path.exists():
        return  # best variant already present

    if v2_path.exists():
        if variant == "v2l":
            try:
                v2_path.unlink()
            except Exception:
                pass
            v2l_path.write_bytes(data)  # upgrade
        return

    # Neither present yet — write whichever we have
    dest = v2l_path if variant == "v2l" else v2_path
    dest.write_bytes(data)


def save_bytes_to_all_image(data: bytes, out_dir: Path, filename: str):
    all_dir = out_dir / "All Image"
    save_unique_to_all(all_dir, filename, data)


def count_unique_in_all(all_dir: Path) -> int:
    """
    Count unique images in All Image/ by 32-hex id.
    Treat _v2 and _v2l as the same image id; prefer only one.
    """
    ids: Set[str] = set()
    for p in all_dir.glob("*.webp"):
        m = re.match(r"^([a-f0-9]{32})_(?:v2l|v2)\.webp$", p.name)
        if m:
            ids.add(m.group(1))
        else:
            # If unexpected name pattern, count by full name to avoid missing
            ids.add(p.name)
    return len(ids)


# ------------------------
# Page helpers
# ------------------------
def enhance_url_v2_to_v2l(url: str) -> str:
    return url.replace("_v2.webp", "_v2l.webp")


def extract_urls_from_html(html: str) -> Set[str]:
    return {m.group(0) for m in GMGN_IMG_RE.finditer(html)}


def extract_id_from_url(url: str) -> str:
    m = GMGN_IMG_RE.match(url)
    return m.group(2) if m else ""


def find_column_container(page: Page, header_text: str) -> ElementHandle:
    col = page.locator(
        "xpath=//div[contains(@class,'flex') and contains(@class,'flex-col') "
        "and .//div[normalize-space(text())=$h]]",
        has_text=header_text
    ).first
    col.wait_for()

    gb = col.locator(".g-table-body").first
    if gb.count() > 0:
        return gb.element_handle()

    alt = col.locator("xpath=.//div[contains(@class,'overflow-y-auto')]").first
    if alt.count() > 0:
        return alt.element_handle()

    return col.element_handle()


def dismiss_popup_if_any(page: Page):
    try:
        page.mouse.click(400, 200)
        page.wait_for_timeout(300)
    except Exception:
        pass


def js_fetch_to_base64(page: Page, url: str, tries: int = 3, ref: str = "https://gmgn.ai/") -> bytes:
    """
    Fetch bytes inside the page context (inherits cookies, headers).
    Returns raw bytes or raises after retries.
    """
    last_err = None
    for attempt in range(1, tries + 1):
        try:
            b64 = page.evaluate(
                """async ({url, ref}) => {
                    const res = await fetch(url, {
                      method: 'GET',
                      credentials: 'include',
                      headers: { 'Referer': ref, 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' }
                    });
                    if (!res.ok) {
                      throw new Error('HTTP ' + res.status);
                    }
                    const buf = await res.arrayBuffer();
                    let bin = '';
                    const bytes = new Uint8Array(buf);
                    for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
                    return btoa(bin);
                }""",
                {"url": url, "ref": ref}
            )
            return base64.b64decode(b64)
        except Exception as e:
            last_err = e
            time.sleep(0.3 + random.random() * 0.5)  # jittered backoff
    raise last_err if last_err else RuntimeError("fetch failed")


# ------------------------
# Status printer (no bars; just numbers)
# ------------------------
def status_text(imgs: int, target_total: int, secs: int, total_secs: int) -> str:
    """
    Build a compact status line according to whether limits are set.
    - If target_total == 0: show 'Images: N' else 'Images: N/Target'
    - If total_secs == 0: show 'Time: S' else 'Time: S/Total'
    """
    if target_total > 0:
        img_part = f"Images: {imgs}/{target_total}"
    else:
        img_part = f"Images: {imgs}"

    if total_secs > 0:
        time_part = f"Time: {secs}/{total_secs}"
    else:
        time_part = f"Time: {secs}"

    return f"{img_part} | {time_part}"


def print_status(imgs: int, target_total: int, secs: int, total_secs: int, last_print: Dict[str, int]):
    """
    Print status only when values change. Writes a single updatable line.
    """
    changed = False
    if imgs != last_print.get("imgs"):
        last_print["imgs"] = imgs
        changed = True
    if secs != last_print.get("secs"):
        last_print["secs"] = secs
        changed = True

    if changed:
        line = status_text(imgs, target_total, secs, total_secs)
        print("\r" + line, end="", flush=True)


# ------------------------
# Streaming collector with oscillating scroll
# ------------------------
def stream_collect_and_download(page: Page, out_dir: Path, target_total: int, time_limit_minutes: int):
    """
    Continuously scrolls all 3 columns with oscillation: down until bottom, then up until top, repeat.
    Downloads unique images immediately when found.
    Stops when target_total unique images saved (if target set) or time limit elapses (if set).
    Returns: (ok_urls, fail_primary)
    """
    # Find column containers
    containers: Dict[str, ElementHandle] = {}
    for header_text, label in COLUMNS:
        containers[label] = find_column_container(page, header_text)
        # Reset scroll to top
        containers[label].evaluate("c => c.scrollTo({top: 0, behavior: 'instant'})")

    # Scroll direction per column: +1 = down, -1 = up
    col_dir: Dict[str, int] = {label: 1 for _, label in COLUMNS}

    # Trackers
    attempted_ids: Set[str] = set()   # ids we've attempted to download (avoid re-trying)
    downloaded_ids: Set[str] = set()  # ids successfully saved (unique counter)
    ok_urls: List[str] = []           # actual urls saved (v2l or v2), chronological
    fail_primary: List[str] = []      # primary v2l urls that failed (even after fallback)

    # Time bookkeeping
    start = time.monotonic()
    time_limit_seconds = int(time_limit_minutes * 60) if time_limit_minutes > 0 else 0
    deadline = (start + time_limit_seconds) if time_limit_seconds > 0 else None
    last_display = {"imgs": -1, "secs": -1}

    # Initial status print
    print_status(0, target_total, 0, time_limit_seconds, last_display)

    # Main loop
    while True:
        # Time check at loop start
        now = time.monotonic()
        elapsed_secs = int(now - start)
        print_status(len(downloaded_ids), target_total, elapsed_secs, time_limit_seconds, last_display)
        if deadline is not None and now >= deadline:
            break

        for label in ["NEW", "MC", "MIGRATED"]:
            container = containers[label]
            direction = col_dir[label]

            # 1) Scroll in current direction
            if direction == 1:
                container.evaluate("(c, step) => c.scrollBy(0, step)", SCROLL_STEP)
            else:
                container.evaluate("(c, step) => c.scrollBy(0, -step)", SCROLL_STEP)

            time.sleep(TICK_SLEEP)

            # 2) Parse current HTML and discover URLs
            html = container.evaluate("c => c.innerHTML")
            urls_now = extract_urls_from_html(html)

            # Take only ids we haven't attempted yet
            new_pairs: List[Tuple[str, str]] = []
            for u in urls_now:
                img_id = extract_id_from_url(u)
                if not img_id:
                    continue
                if img_id in attempted_ids:
                    continue
                attempted_ids.add(img_id)
                new_pairs.append((u, img_id))

            # 3) Process new items immediately (download & save)
            if new_pairs:
                for u, img_id in sorted(new_pairs):
                    primary = enhance_url_v2_to_v2l(u)  # _v2l.webp
                    fallback = u                         # _v2.webp
                    fn_p = primary.split("/")[-1]
                    fn_f = fallback.split("/")[-1]

                    saved_ok = False
                    try:
                        data = js_fetch_to_base64(page, primary, tries=3)
                        save_bytes_to_all_image(data, out_dir, fn_p)
                        saved_ok = True
                        ok_urls.append(primary)
                    except Exception:
                        try:
                            data2 = js_fetch_to_base64(page, fallback, tries=3)
                            save_bytes_to_all_image(data2, out_dir, fn_f)
                            saved_ok = True
                            ok_urls.append(fallback)
                        except Exception:
                            fail_primary.append(primary)

                    if saved_ok and img_id not in downloaded_ids:
                        downloaded_ids.add(img_id)
                        # Update status immediately on new unique save
                        now2 = time.monotonic()
                        elapsed_secs2 = int(now2 - start)
                        print_status(len(downloaded_ids), target_total, elapsed_secs2, time_limit_seconds, last_display)

                        # Early exit if we reached target
                        if target_total > 0 and len(downloaded_ids) >= target_total:
                            print()  # end the status line
                            return ok_urls, fail_primary

            # 4) Flip direction at edges (oscillation)
            metrics = container.evaluate(
                "c => ({top: c.scrollTop, ch: c.clientHeight, h: c.scrollHeight})"
            )
            top = metrics["top"]
            ch = metrics["ch"]
            h = metrics["h"]
            at_bottom = (top + ch + 5) >= h
            at_top = top <= 5

            if direction == 1 and at_bottom:
                col_dir[label] = -1
            elif direction == -1 and at_top:
                col_dir[label] = 1

            # 5) Time update after each column
            now_mid = time.monotonic()
            elapsed_secs_mid = int(now_mid - start)
            print_status(len(downloaded_ids), target_total, elapsed_secs_mid, time_limit_seconds, last_display)
            if deadline is not None and now_mid >= deadline:
                print()  # end the status line
                return ok_urls, fail_primary

        # Time check end of pass
        if deadline is not None and time.monotonic() >= deadline:
            print()  # end the status line
            break

    print()  # end the status line
    return ok_urls, fail_primary


# ------------------------
# Utilities
# ------------------------
def dedupe_urls_prefer_v2l(urls: List[str]) -> List[str]:
    """
    Deduplicate by 32-hex id; prefer _v2l.webp over _v2.webp if both appear.
    Preserve first-seen order of ids.
    """
    id_order: List[str] = []
    best_for_id: Dict[str, str] = {}
    id_re = re.compile(r"/([a-f0-9]{32})_v2(l)?\.webp$")

    for u in urls:
        m = id_re.search(u)
        if not m:
            # if no id, keep as-is under its own key
            key = u
            if key not in best_for_id:
                id_order.append(key)
                best_for_id[key] = u
            else:
                # keep first
                pass
            continue

        img_id = m.group(1)
        is_v2l = bool(m.group(2))
        if img_id not in best_for_id:
            id_order.append(img_id)
            best_for_id[img_id] = u
        else:
            # upgrade to v2l if available
            prev = best_for_id[img_id]
            if (not prev.endswith("_v2l.webp")) and is_v2l:
                best_for_id[img_id] = u

    return [best_for_id[k] for k in id_order]


def write_all_urls(out_dir: Path, ok_list: List[str]):
    """
    Write only one combined file: all_urls.txt
    (Deduped by id, preferring _v2l where present.)
    """
    final_urls = dedupe_urls_prefer_v2l(ok_list)
    (out_dir / "all_urls.txt").write_text("\n".join(final_urls), encoding="utf-8")


# ------------------------
# Main
# ------------------------
def main():
    target_total, time_minutes = ask_run_limits()
    print("Starting . . . ")

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1440, "height": 900},
    )
    page = context.new_page()
    page.goto(START_URL, wait_until="networkidle", timeout=90_000)
    dismiss_popup_if_any(page)

    out_dir = format_output_dir_bd()

    ok_list: List[str] = []
    fail_list: List[str] = []

    try:
        try:
            ok_list, fail_list = stream_collect_and_download(page, out_dir, target_total, time_minutes)
        except KeyboardInterrupt:
            print("\nStopped by user (Ctrl+C). Finalizing...")
    finally:
        try:
            write_all_urls(out_dir, ok_list)
        finally:
            try:
                context.close()
                browser.close()
                pw.stop()
            except Exception:
                pass

    # Print total unique images in All Image/ and final status
    unique_total = count_unique_in_all(out_dir / "All Image")
    print(f"Total Unique Images: {unique_total}")

    if ok_list:
        print("\nSuccess !!")
    else:
        print("\nNo images downloaded. (Server blocked or no content)")


if __name__ == "__main__":
    main()