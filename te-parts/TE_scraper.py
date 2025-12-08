import asyncio
from pathlib import Path
from urllib.parse import urlparse, unquote, quote
import re

import aiohttp
import aiofiles
import pandas as pd

BASE_DIR = Path.cwd()

INPUT_XLSX = BASE_DIR / "te_parts.xlsx"
DEST_DIR = BASE_DIR / "PDFs"
SKIPPED_XLSX = BASE_DIR / "skipped_parts.xlsx"

MAX_CONCURRENCY = 5
MAX_RETRIES = 3
CHUNK_SIZE = 524_288
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=600, connect=20, sock_read=180)

INVALID_CHARS = r'<>:"/\\|?*'

def sanitize_filename(name: str) -> str:
    name = unquote(name)
    name = re.sub(f"[{re.escape(INVALID_CHARS)}]", "_", name)
    name = name.strip().rstrip(".")
    return name or "file"

def filename_from_headers(headers: aiohttp.typedefs.LooseHeaders):
    cd = headers.get("Content-Disposition")
    if not cd:
        return None
    m = re.search(r'filename\*=(?:UTF-8\'\')?([^;]+)', cd, flags=re.I)
    if m:
        return unquote(m.group(1).strip().strip('"'))
    m2 = re.search(r'filename="?([^";]+)"?', cd, flags=re.I)
    if m2:
        return m2.group(1).strip()
    return None

def candidate_filename(idx: int, url: str, headers: aiohttp.typedefs.LooseHeaders) -> str:
    fname = filename_from_headers(headers)
    if not fname:
        path = urlparse(url).path
        base = Path(path).name or f"file_{idx}.pdf"
        fname = base
    fname = sanitize_filename(fname)
    if not fname.lower().endswith(".pdf"):
        fname += ".pdf"
    return fname

def ensure_unique(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    for n in range(1, 10_000):
        candidate = path.with_name(f"{stem} ({n}){suffix}")
        if not candidate.exists():
            return candidate
    import uuid
    return path.with_name(f"{stem}-{uuid.uuid4().hex[:8]}{suffix}")

def looks_like_pdf(headers, first_bytes: bytes) -> bool:
    ct = (headers.get("Content-Type") or "").lower()
    if "pdf" in ct:
        return True
    # Check for the PDF magic within first kilobyte
    return b"%PDF" in (first_bytes or b"")[:2048]

def build_te_url(part_number: str) -> str:
    encoded = quote(str(part_number).strip())
    return f"https://www.te.com/commerce/alt/SinglePartSearch.do?PN={encoded}&dest=stmt"

async def download_one(
    sema: asyncio.Semaphore,
    idx: int,
    part_number: str,
    url: str,
    session: aiohttp.ClientSession,
    dest_dir: Path,
    failures: list,
) -> None:
    async with sema:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with session.get(url, allow_redirects=True) as resp:
                    if resp.status != 200:
                        raise aiohttp.ClientResponseError(
                            resp.request_info, resp.history,
                            status=resp.status,
                            message=f"HTTP {resp.status}"
                        )
                    # Peek first bytes to verify actual PDF
                    first = await resp.content.read(4096)
                    if not looks_like_pdf(resp.headers, first):
                        failures.append({
                            "index": idx,
                            "part_number": part_number,
                            "reason": "not a PDF response",
                        })
                        return
                    fname = candidate_filename(idx, url, resp.headers)
                    out_path = ensure_unique(dest_dir / fname)

                    async with aiofiles.open(out_path, "wb") as f:
                        if first:
                            await f.write(first)
                        async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                            await f.write(chunk)
                    return

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == MAX_RETRIES:
                    failures.append({
                        "index": idx,
                        "part_number": part_number,
                        "reason": str(e),
                    })
                    return
                await asyncio.sleep(1.5 * attempt)

async def run():
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_excel(INPUT_XLSX)

    if "part_number" not in df.columns:
        raise SystemExit("Input Excel must contain a 'part_number' column.")

    part_numbers = [
        str(p).strip()
        for p in df["part_number"].tolist()
        if pd.notna(p) and str(p).strip()
    ]

    if not part_numbers:
        raise SystemExit("No valid part_number values found in te_parts.xlsx.")
    urls = [build_te_url(part) for part in part_numbers]

    sema = asyncio.Semaphore(MAX_CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENCY, ttl_dns_cache=300)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PDFFetcher/1.0",
        "Accept": "application/pdf, */*;q=0.9",
    }

    failures = []

    async with aiohttp.ClientSession(
        timeout=REQUEST_TIMEOUT,
        connector=connector,
        headers=headers,
        trust_env=True,
    ) as session:
        tasks = []
        for i, (part, url) in enumerate(zip(part_numbers, urls), start=1):
            tasks.append(
                asyncio.create_task(
                    download_one(
                        sema=sema,
                        idx=i,
                        part_number=part,
                        url=url,
                        session=session,
                        dest_dir=DEST_DIR,
                        failures=failures,
                    )
                )
            )
        await asyncio.gather(*tasks)

    if failures:
        skipped_df = pd.DataFrame(failures)
        skipped_df.to_excel(SKIPPED_XLSX, index=False)

    total = len(part_numbers)
    skipped = len(failures)
    downloaded = total - skipped
    print(f"Total parts: {total}")
    print(f"Downloaded PDFs: {downloaded}")
    print(f"Skipped parts: {skipped}")
    if skipped:
        print(f"See details in: {SKIPPED_XLSX.name}")

if __name__ == "__main__":
    try:
        import sys
        if sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # type: ignore
    except Exception:
        pass

    try:
        asyncio.run(run())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            try:
                import nest_asyncio
            except ImportError:
                raise RuntimeError(
                    "An event loop is already running and 'nest_asyncio' is not installed. "
                    "Install it with: pip install nest_asyncio\n"
                    "Alternatively, call `await run()` directly in your notebook/console."
                ) from e
            nest_asyncio.apply()
            loop = asyncio.get_event_loop()
            loop.run_until_complete(run())
        else:
            raise