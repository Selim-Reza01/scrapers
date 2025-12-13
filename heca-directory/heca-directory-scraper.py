import time
import string
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
import pandas as pd


BASE = "https://association.hecalive.org/heca-member-directory/FindStartsWith?term={term}"


def scrape_term(session: requests.Session, term: str):
    """
    Scrape one FindStartsWith page for a given term (e.g., 'A', 'B', '#!').
    Returns list of dict rows.
    """
    url = BASE.format(term=quote(term, safe=""))
    r = session.get(url, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    container = soup.select_one("div.row.gz-cards.gz-directory-cards")
    if not container:
        return []

    rows = []
    for card in container.select("div.card.gz-directory-card"):
        # NAME
        name_el = card.select_one("h5.gz-card-title a")
        name = name_el.get_text(strip=True) if name_el else ""

        # PHONE
        phone_el = card.select_one("li.gz-card-phone span[itemprop='telephone']")
        phone = phone_el.get_text(strip=True) if phone_el else ""

        # WEBSITE (optional)
        website_el = card.select_one("li.gz-card-website a[href]")
        website = website_el["href"].strip() if website_el and website_el.has_attr("href") else ""

        # A stable id for deduping (details page link if present)
        details_el = card.select_one("li.gz-card-more-details a[href]")
        details_href = details_el["href"].strip() if details_el and details_el.has_attr("href") else ""
        # Normalize protocol-relative links like //association....
        if details_href.startswith("//"):
            details_href = "https:" + details_href
        elif details_href.startswith("/"):
            details_href = "https://association.hecalive.org" + details_href

        rows.append(
            {
                "name": name,
                "phone": phone,
                "website": website,
                "details_url": details_href,
                "term": term,
            }
        )

    return rows


def main():
    # Terms to cover most names.
    # You can add more terms if needed (e.g., "&", ".", etc.)
    terms = list(string.ascii_uppercase) + list(string.digits) + ["#!"]

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; directory-scraper/1.0; +https://example.com)",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )

    all_rows = []
    seen = set()  # dedupe by details_url (preferred) or (name, phone, website) fallback

    for t in terms:
        try:
            rows = scrape_term(session, t)
        except Exception as e:
            print(f"[WARN] term={t!r} failed: {e}")
            continue

        for row in rows:
            key = row["details_url"] or (row["name"], row["phone"], row["website"])
            if key in seen:
                continue
            seen.add(key)
            all_rows.append(row)

        print(f"[OK] term={t!r}: +{len(rows)} rows (total unique: {len(all_rows)})")
        time.sleep(1.0)  # polite delay

    # Save to Excel in the same folder you run the script from
    df = pd.DataFrame(all_rows, columns=["name", "phone", "website", "details_url", "term"])
    out_file = "heca_member_directory.xlsx"
    df.to_excel(out_file, index=False)
    print(f"\nSaved: {out_file} ({len(df)} unique records)")


if __name__ == "__main__":
    main()