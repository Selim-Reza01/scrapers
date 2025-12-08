import os, re, json, math, random, time, sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "Talent Output"
OUTDIR.mkdir(exist_ok=True)

TARGET_URL = "https://www.workmarket.com/talent"
PROFILE_JSON_URL = "https://www.workmarket.com/v2/employer/settings/profile/{row_id}"

# Pagination & selectors
NEXT_BTN_QS = 'button[aria-label="Next Page"][data-attr-id="wm-icon-button"]'
PAGE_STATUS_QS = 'span.talent1z1144.talent1z1154.talent1z1133.talent1z1129'
MAX_PAGES = 500

# Output columns (profile_url followed by rowID-URL)
COLS = [
    "id", "first_name", "last_name", "email", "work_phone", "mobile_phone",
    "location", "zip", "industry",
    "certifications", "licenses", "insurance",
    "account_type", "satisfaction_score", "paid_assignments",
    "drug_test", "background_check",
    "profile_url"
]

# Controls
DETAIL_TAB_VISIBLE_MS = int(os.getenv("DETAIL_TAB_VISIBLE_MS", "0"))
PROFILE_TAB_THROTTLE_MS = int(os.getenv("PROFILE_TAB_THROTTLE_MS", "350"))

# Known bad markers
BANNED_EMAIL = "alexaveryemail@gmail.com".lower()
BANNED_DEPRECATED_USER_NUMBER = "26719881"

# ----- Helpers -----
def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def fmt_date(s: str) -> str:
    if not s:
        return ""
    try:
        s2 = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s2)
        return dt.strftime("%b %d, %Y")
    except Exception:
        try:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
            return dt.strftime("%b %d, %Y")
        except Exception:
            return ""

def safe_json_loads(s):
    try:
        if isinstance(s, (dict, list)):
            return s
        return json.loads(s or "{}")
    except Exception:
        return {}

def join_list(v) -> str:
    if isinstance(v, list):
        return ", ".join([str(x) for x in v if str(x).strip()])
    return str(v or "").strip()

# ----- JS snippets -----
FILTER_CHIPS_JS = """
() => {
  var chips = [];
  var bar = document.querySelector('[data-attr-id="wm-search-clear-all"]');
  var root = bar ? bar.parentElement : document;
  var nodes = root.querySelectorAll('span[title]');
  for (var i = 0; i < nodes.length; i++) {
    var t = (nodes[i].textContent || '').trim().replace(/\\s+/g, ' ');
    if (t && t.indexOf(':') > 0 && t.length < 160) chips.push(t);
  }
  return chips;
}
"""

CLICK_NAME_BY_ID_JS = """
(arg) => {
  const idText = (arg && arg.idText) || '';
  function norm(s){ return (s||'').trim(); }
  if (!idText) return false;

  const spans = Array.from(document.querySelectorAll('span'));
  for (let i=0;i<spans.length;i++){
    const s = spans[i];
    if (norm(s.textContent) === ('ID# ' + idText)) {
      const parent = s.parentElement;
      if (!parent) continue;
      const spans2 = parent.querySelectorAll('span');
      for (let j=0;j<spans2.length;j++){
        const t = norm(spans2[j].textContent);
        const st = spans2[j].getAttribute('style') || '';
        if (t && t !== ('ID# ' + idText) &&
            /cursor:\\s*pointer|rgb\\(41,\\s*98,\\s*255\\)/i.test(st)) {
          spans2[j].click();
          return true;
        }
      }
    }
  }
  return false;
}
"""

def close_profile_popup_sync(page):
    back = page.query_selector('sdf-button#back-button-with-label, sdf-button[aria-label="Back"]')
    if back:
        back.click()
        page.wait_for_timeout(250)
        try:
            page.wait_for_selector('sdf-button#back-button-with-label', state='detached', timeout=1500)
        except Exception:
            pass
    else:
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)

# ----- Dashboard tap -----
class DashboardTap:
    def __init__(self, page):
        self.last_json = None
        self.seq = 0
        self.last_req = None

        def on_request(req):
            url = (req.url or "").lower()
            if "dashboard" in url:
                try:
                    method = (req.method or "GET").upper()
                    try: post_data = req.post_data or ""
                    except Exception: post_data = ""
                    try: headers = dict(req.headers)
                    except Exception: headers = {}
                    self.last_req = (method, req.url, post_data, headers)
                except Exception:
                    pass

        def on_response(resp):
            url = (resp.url or "").lower()
            if "dashboard" in url and resp.status in (200, 206):
                try:
                    j = resp.json()
                    payload = (j or {}).get("result", {}).get("payload", [])
                    if isinstance(payload, list):
                        self.last_json = j
                        self.seq += 1
                except Exception:
                    pass

        page.on("request", on_request)
        page.on("response", on_response)

    def wait_for_next(self, page, prev_seq: int, timeout_ms: int = 60000):
        start = time.time()
        while (time.time() - start) * 1000 < timeout_ms:
            if self.seq > prev_seq and self.last_json is not None:
                return self.last_json
            page.wait_for_timeout(80)
        return self.last_json

def fetch_dashboard_from_last_request(context, tap: DashboardTap):
    if not tap.last_req:
        return None
    method, url, post_data, headers = tap.last_req
    bad = {"content-length", "host", "origin"}
    req_headers = {k: v for k, v in (headers or {}).items() if k.lower() not in bad}
    try:
        if method == "POST":
            r = context.request.post(url, data=post_data or "", headers=req_headers)
        else:
            r = context.request.get(url, headers=req_headers)
        if hasattr(r, "ok") and r.ok:
            return safe_json_loads(r.text())
    except Exception:
        return None
    return None

# ----- Parse dashboard cells (base row record) -----
def record_from_cells(cells: list) -> dict:
    rec = {
        "id": "", "first_name": "", "last_name": "", "email": "",
        "work_phone": "", "mobile_phone": "",
        "location": "", "zip": "",
        "industry": "", "certifications": "―", "licenses": "―", "insurance": "―",
        "account_type": "", "satisfaction_score": "", "paid_assignments": "",
        "drug_test": "―", "background_check": "―",
        "profile_url": "", "rowID-URL": ""
    }

    for cell in cells or []:
        fid = (cell.get("fieldConfigurationId") or "").strip()
        vjson = safe_json_loads(cell.get("cellValue", {}).get("valueJson"))

        if fid == "user":
            u = vjson.get("user", {}) or {}
            rec["id"] = str(u.get("userNumber") or "").strip()
            rec["first_name"] = normalize(u.get("firstName") or "")
            rec["last_name"] = normalize(u.get("lastName") or "")
            if rec["id"]:
                rec["profile_url"] = f"https://www.workmarket.com/profile/{rec['id']}"

        elif fid == "userType":
            rec["account_type"] = normalize(vjson.get("userType") or "")

        elif fid == "backgroundCheck":
            rec["background_check"] = fmt_date(vjson.get("backgroundCheck") or "")

        elif fid == "drugTest":
            rec["drug_test"] = fmt_date(vjson.get("drugTest") or "")

        elif fid == "satisfactionRate":
            s = vjson.get("satisfactionRate", {}) or {}
            val = s.get("satisfactionRate")
            if val is not None and str(val).strip():
                rec["satisfaction_score"] = f"{val}%"

        elif fid == "industry":
            rec["industry"] = join_list(vjson.get("industry", []))

        elif fid == "insurance":
            rec["insurance"] = join_list(vjson.get("insurance", []))

        elif fid == "certifications":
            rec["certifications"] = join_list(vjson.get("certifications", []))

        elif fid == "licenses":
            rec["licenses"] = join_list(vjson.get("licenses", []))

        elif fid == "paidAssignments":
            v = vjson.get("paidAssignments")
            rec["paid_assignments"] = str(v or "").strip()

        elif fid == "location":
            loc = vjson.get("location", {}) or {}
            if not rec["zip"]:
                rec["zip"] = normalize(loc.get("postalCode") or "")

    return rec

# ----- Vendor details fetch (new tab) -----
def deep_find(node, key):
    if isinstance(node, dict):
        if key in node:
            return node[key]
        for v in node.values():
            found = deep_find(v, key)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = deep_find(item, key)
            if found is not None:
                return found
    return None

def extract_location_from_profile_json(j):
    loc = None
    if isinstance(j, dict):
        loc = j.get("location") or deep_find(j, "location")
    if not isinstance(loc, dict):
        return {"location": "", "zip": ""}
    address1 = normalize(loc.get("addressLine1") or "")
    city = normalize(loc.get("city") or "")
    state = normalize(loc.get("state") or "")
    country = normalize(loc.get("country") or "")
    parts = [x for x in [address1, city, state, country] if x]
    zip_code = normalize(loc.get("zip") or loc.get("postalCode") or "")
    return {"location": ", ".join(parts), "zip": zip_code}

def fetch_profile_details_via_tab(context, row_id: str) -> dict:
    from playwright.sync_api import TimeoutError as PWTimeoutError
    url = PROFILE_JSON_URL.format(row_id=row_id)
    tab = context.new_page()
    http_status = None
    try:
        resp = tab.goto(url, wait_until="domcontentloaded", timeout=60000)
        try:
            http_status = resp.status if resp else None
        except Exception:
            http_status = None

        raw = ""
        try:
            tab.wait_for_selector("pre", timeout=3000)
            pre = tab.query_selector("pre")
            if pre:
                raw = pre.inner_text() or ""
        except PWTimeoutError:
            raw = ""

        if not raw:
            raw = tab.evaluate("() => document.body && document.body.innerText || ''") or ""
        raw = raw.strip()
        for prefix in (")]}'", ")]}',"):
            if raw.startswith(prefix):
                raw = raw[len(prefix):].strip()

        j = safe_json_loads(raw)

        # Fallback to fetch() within the tab
        if not (isinstance(j, dict) and (j.get('results') or j.get('email') or j.get('location'))):
            j = tab.evaluate(
                """async (u) => {
                    try {
                        const r = await fetch(u, {credentials: 'include', headers: {'accept': 'application/json'}});
                        if (!r.ok) return {'__fetch_status': r.status};
                        const data = await r.json();
                        data.__fetch_status = r.status;
                        return data;
                    } catch(e) { return {'__fetch_status': -1}; }
                }""",
                url
            )

        if DETAIL_TAB_VISIBLE_MS > 0:
            tab.wait_for_timeout(DETAIL_TAB_VISIBLE_MS)

        out = {"email": "", "work_phone": "", "mobile_phone": "", "location": "", "zip": ""}
        if isinstance(j, dict):
            out["email"] = normalize(str(deep_find(j, "email") or ""))
            out["work_phone"] = normalize(str(deep_find(j, "workPhone") or ""))
            out["mobile_phone"] = normalize(str(deep_find(j, "mobilePhone") or ""))
            out.update(extract_location_from_profile_json(j))

        out["__http_status"] = http_status if http_status is not None else j.get("__fetch_status", None)
        out["__rowid_url"] = url
        return out

    except Exception:
        return {"email":"", "work_phone":"", "mobile_phone":"", "location":"", "zip":"", "__http_status": None, "__rowid_url": url}
    finally:
        try: tab.close()
        except Exception: pass

# ----- WORKER capture -----
class WorkerTap:
    def __init__(self, page):
        self.seq = 0
        self.items = []

        def on_response(resp):
            url = (resp.url or "").lower()
            if "user-at-company-details" in url and resp.status in (200, 206):
                try:
                    j = resp.json()
                    self.seq += 1
                    self.items.append((self.seq, time.time(), j))
                    self.items = self.items[-10:]
                except Exception:
                    pass

        page.on("response", on_response)

    def wait_and_collect_new(self, page, prev_seq: int, timeout_ms: int = 9000):
        start = time.time()
        while (time.time() - start) * 1000 < timeout_ms:
            if self.seq > prev_seq:
                break
            page.wait_for_timeout(80)
        page.wait_for_timeout(400)
        return [j for (s,_,j) in self.items if s > prev_seq]

def _unwrap_worker_record(j):
    node = j or {}
    # wrapper 1
    if isinstance(node, dict) and "result" in node and isinstance(node["result"], dict):
        pl = node["result"].get("payload")
        if isinstance(pl, list) and pl:
            node = pl[0]
        elif isinstance(pl, dict):
            node = pl
    # wrapper 2 (list inside payload)
    if isinstance(node, dict) and "userAtCompanyDetailsList" in node:
        lst = node.get("userAtCompanyDetailsList") or []
        if isinstance(lst, list) and lst:
            node = lst[0]
    return node if isinstance(node, dict) else {}

def _json_signature(obj):
    try:
        return json.dumps(obj, sort_keys=True)
    except Exception:
        return str(obj)[:200]

def choose_best_worker_payload(payloads: list) -> dict:
    good = []
    seen = set()
    for p in payloads or []:
        rec = _unwrap_worker_record(p)

        # find email
        email = ""
        try:
            email = rec.get("email") or (((rec.get("userCoreDetails") or {}).get("baseUserInfo") or {}).get("userEmail")) or ""
        except Exception:
            email = ""
        if str(email).lower() == BANNED_EMAIL:
            continue

        # check deprecatedUserNumber
        try:
            dep_num = (((rec.get("userCoreDetails") or {}).get("baseUserInfo") or {}).get("userIdentifiers") or {}).get("deprecatedUserNumber")
            if str(dep_num).strip() == BANNED_DEPRECATED_USER_NUMBER:
                continue
        except Exception:
            pass

        sig = _json_signature(rec)
        if sig not in seen:
            seen.add(sig)
            good.append(rec)

    if good:
        return good[0]
    return _unwrap_worker_record((payloads or [{}])[0])

def extract_worker_details_from_json(full_json: dict) -> dict:
    rec = _unwrap_worker_record(full_json)
    out = {"first_name":"", "last_name":"", "email":"", "work_phone":"", "mobile_phone":"", "location":"", "zip":""}
    try:
        bu = (((rec.get("userCoreDetails") or {}).get("baseUserInfo")) or {})
        out["first_name"] = normalize(bu.get("firstName") or "")
        out["last_name"]  = normalize(bu.get("lastName") or "")
        top_email = normalize(rec.get("email") or "")
        if top_email.lower() == BANNED_EMAIL:
            top_email = ""
        out["email"] = top_email or normalize((bu.get("userEmail") or ""))
        if out["email"].lower() == BANNED_EMAIL:
            out["email"] = ""
        pd_top = rec.get("phoneDetails")
        if isinstance(pd_top, dict):
            if (pd_top.get("phoneType") or "").upper() == "WORK":
                out["work_phone"] = normalize(pd_top.get("phoneNumber") or "")
        elif isinstance(pd_top, list):
            for ph in pd_top:
                if (ph.get("phoneType") or "").upper() == "WORK":
                    out["work_phone"] = normalize(ph.get("phoneNumber") or "")
                    break
        pd_list = ((rec.get("userCoreDetails") or {}).get("phoneDetails")) or []
        if isinstance(pd_list, list):
            for ph in pd_list:
                if (ph.get("phoneType") or "").upper() == "MOBILE":
                    out["mobile_phone"] = normalize(ph.get("phoneNumber") or "")
                    break
        if not out["mobile_phone"] and isinstance(pd_top, list):
            for ph in pd_top:
                if (ph.get("phoneType") or "").upper() == "MOBILE":
                    out["mobile_phone"] = normalize(ph.get("phoneNumber") or "")
                    break

        # address
        addr = ((rec.get("userCoreDetails") or {}).get("address")) or {}
        address1 = normalize(addr.get("line1") or "")
        city = normalize(addr.get("city") or "")
        state = normalize(addr.get("stateProvince") or "")
        country = normalize(addr.get("country") or "")
        out["location"] = ", ".join([x for x in [address1, city, state, country] if x])
        out["zip"] = normalize(addr.get("postalCode") or "")
    except Exception:
        pass
    return out

# ----- Main -----
def filename_for(count: int) -> Path:
    base = f"{datetime.now():%Y-%m-%d}_{count}"
    path = OUTDIR / f"{base}.xlsx"
    i = 1
    while path.exists():
        path = OUTDIR / f"{base} ({i}).xlsx"
        i += 1
    return path

def safe_run_authentication():
    print("Starting authentication flow...")
    auth_script = None
    for cand in ("authentication.py", "wm.py"):
        if (HERE / cand).exists():
            auth_script = cand
            break
    if not auth_script:
        print("Warning: authentication script not found. Continuing anyway.")
    else:
        try:
            import subprocess
            subprocess.run([sys.executable, str(HERE / auth_script)], cwd=str(HERE))
        except Exception as e:
            print(f"Warning: could not run authentication: {e}")
    print("Moving On Talent Scraping\n")

def is_next_enabled_sync(page):
    loc = page.locator(NEXT_BTN_QS)
    try:
        if loc.count() > 0:
            return loc.is_enabled()
    except Exception:
        pass
    btn = page.query_selector(NEXT_BTN_QS)
    if not btn:
        return False
    if btn.get_attribute("disabled") is not None:
        return False
    aria = (btn.get_attribute("aria-disabled") or "").lower()
    cls = (btn.get_attribute("class") or "").lower()
    return not (aria == "true" or "disabled" in cls)

def read_page_status_sync(page):
    el = page.query_selector(PAGE_STATUS_QS)
    return (el.inner_text().strip() if el else "")

def record_payload_from_latest(tap: DashboardTap):
    j = tap.last_json
    payload = []
    if isinstance(j, dict):
        payload = (j.get("result", {}) or {}).get("payload", []) or []
    return payload

def run_sync():
    from playwright.sync_api import sync_playwright
    import pandas as pd

    safe_run_authentication()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--ignore-certificate-errors"])

        storage = str(HERE/"data/storage_state.json") if (HERE/"data/storage_state.json").exists() else None
        context = browser.new_context(
            ignore_https_errors=True,
            storage_state=storage,
            viewport={"width": 4000, "height": 800},
        )
        page = context.new_page()

        dash_tap = DashboardTap(page)
        worker_tap = WorkerTap(page)

        page.goto(TARGET_URL, wait_until="domcontentloaded")
        page.evaluate("document.body.style.zoom='0.75'")

        if "login" in page.url.lower():
            print("Not logged in. Please run authentication.py and try again.")
            browser.close()
            return

        choice = input("Want to filter Talent? press 1 to filter, or press 0 to continue without filtering: ").strip()
        if choice == "1":
            print("Apply filters, then return to console.\n")
            input("When finished, press ENTER here to start scraping: ")
        page.set_viewport_size({"width": 4000, "height": 6000})

        # Totals
        total_talent = 0
        total_pages = 1
        items_per_page = 50
        try:
            page.wait_for_selector(PAGE_STATUS_QS, timeout=10000)
            total_span = page.query_selector(PAGE_STATUS_QS + " span")
            total_text = total_span.inner_text().strip() if total_span else ""
            if not total_text:
                status_txt = read_page_status_sync(page)
                m = re.search(r'of\\s+([\\d,]+)', status_txt, re.I)
                total_text = m.group(1) if m else ""
            total_text = total_text.replace(",", "")
            if total_text.isdigit():
                total_talent = int(total_text)
                total_pages = max(1, math.ceil(total_talent / items_per_page))
                print(f"Total talent found: {total_talent}")
                print(f"Total pages (approx @ {items_per_page}/page): {total_pages}\n")
            else:
                print("Total talent found: (could not determine)\n")
        except Exception:
            print("Total talent found: (could not determine)\n")

        start_page = 1
        end_page = total_pages
        try:
            start_in = input(f"Enter START page (1-{max(1, total_pages)}) [default: 1]: ").strip()
            if start_in.isdigit():
                start_page = max(1, min(int(start_in), max(1, total_pages)))
            end_in = input(f"Enter END page ({start_page}-{max(start_page, total_pages)}) [default: {total_pages}]: ").strip()
            if end_in.isdigit():
                end_page = max(start_page, min(int(end_in), max(start_page, total_pages)))
            else:
                end_page = total_pages
        except Exception:
            pass

        print(f"\n--- Scraping from page {start_page} to {end_page} ---")

        rows_out = []
        seen_ids = set()

        def process_payload(payload, page_index):
            total_profiles = len(payload)
            for idx, row in enumerate(payload, start=1):
                print(f"\rScraping: Page - {page_index} | Profile - {idx}", end="", flush=True)

                row_id = row.get("rowId") or ""
                cells = row.get("cells") or []
                rec = record_from_cells(cells)

                if row_id:
                    rec["rowID-URL"] = PROFILE_JSON_URL.format(row_id=row_id)

                acct = (rec.get("account_type") or "").upper()

                if acct == "VENDOR":
                    if row_id:
                        details = fetch_profile_details_via_tab(context, row_id)
                        for k in ("location", "zip", "email", "work_phone", "mobile_phone"):
                            v = details.get(k) or ""
                            if v:
                                rec[k] = v
                    page.wait_for_timeout(PROFILE_TAB_THROTTLE_MS)
                else:
                    prev_seq = worker_tap.seq
                    try:
                        clicked = page.evaluate(CLICK_NAME_BY_ID_JS, {"idText": rec.get("id","")})
                    except Exception:
                        clicked = False
                    if clicked:
                        new_payloads = worker_tap.wait_and_collect_new(page, prev_seq, timeout_ms=9000)
                        if new_payloads:
                            best = choose_best_worker_payload(new_payloads)
                            details = extract_worker_details_from_json(best)
                            for k in ("first_name","last_name","email","work_phone","mobile_phone","location","zip"):
                                vv = details.get(k) or ""
                                if vv:
                                    rec[k] = vv
                        try:
                            close_profile_popup_sync(page)
                        except Exception:
                            pass

                key = rec.get("id") or f"ROW-{row_id}"
                if key not in seen_ids:
                    rows_out.append(rec)
                    seen_ids.add(key)

                page.wait_for_timeout(random.randint(250, 700))
            print("")

        page_index = 1
        if start_page == 1:
            payload = record_payload_from_latest(dash_tap)
            if not payload:
                j2 = fetch_dashboard_from_last_request(context, dash_tap)
                try:
                    payload = (j2 or {}).get("result", {}).get("payload", []) or []
                except Exception:
                    payload = []
            if payload:
                process_payload(payload, page_index=1)

        while page_index < start_page:
            if page_index >= MAX_PAGES or not is_next_enabled_sync(page):
                break
            prev_seq = dash_tap.seq
            page.locator(NEXT_BTN_QS).click(timeout=120000)
            page.wait_for_load_state("domcontentloaded")
            dash_tap.wait_for_next(page, prev_seq, timeout_ms=60000)
            page_index += 1

        if start_page > 1:
            payload = record_payload_from_latest(dash_tap)
            if not payload:
                prev = dash_tap.seq
                dash_tap.wait_for_next(page, prev, timeout_ms=8000)
                payload = record_payload_from_latest(dash_tap)
            process_payload(payload, page_index=start_page)
            page_index = start_page

        while page_index < end_page:
            if page_index >= MAX_PAGES or not is_next_enabled_sync(page):
                print("\nNo more pages. Stopping.")
                break
            prev_seq = dash_tap.seq
            page.locator(NEXT_BTN_QS).click(timeout=120000)
            page.wait_for_load_state("domcontentloaded")
            j = dash_tap.wait_for_next(page, prev_seq, timeout_ms=60000)
            payload = (j or {}).get("result", {}).get("payload", []) or []
            page_index += 1
            process_payload(payload, page_index=page_index)

        print(f"\nTotal Talent Scraped: {len(rows_out)}")
        if not rows_out:
            print("No data to save.")
            browser.close()
            return

        import pandas as pd
        df = pd.DataFrame(rows_out, columns=COLS)

        outpath = filename_for(len(rows_out))
        with pd.ExcelWriter(outpath, engine="xlsxwriter") as writer:
            # Filter row (top)
            try:
                chips = page.evaluate(FILTER_CHIPS_JS) or []
            except Exception:
                chips = []
            filt_df = pd.DataFrame([{k:"" for k in COLS}], columns=COLS)
            filt_df.iloc[0,0] = "Filters:"
            filt_df.to_excel(writer, index=False, header=False, startrow=0)
            df.to_excel(writer, index=False, header=True, startrow=1)
            ws = writer.sheets["Sheet1"]
            ws.merge_range(0, 1, 0, len(COLS)-1, " ; ".join(chips))

        print(f"Data saved to: {outpath}")
        print("Scraping Completed!!")
        browser.close()

if __name__ == "__main__":
    run_sync()