import csv
import re
import random
import time
from dataclasses import asdict
from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright
from scraper.dataclass import ThaiMusicRecord  # <-- your dataclass

ATTEMPT_STEP = 8

def extract_year(text: str) -> str | None:
    """
    Extracts the most likely release year from text based on priority:
    1. 'เพลงโดย ... พ.ศ.' pattern (artist and Buddhist year)
    2. 'พ.ศ.' Buddhist year → convert to Christian year (YYYY)
    3. 'release' keyword followed by 20 chars → find first 4-digit year
    4. Thai-style date (e.g. '12 สิงหาคม 2566') → extract year
    Returns: year as string (e.g. "2023") or None if not found.
    """

    # --- เพลงโดย ... พ.ศ. ---- (highest priority)
    artist_year_pattern = re.search(
        r"เพลงโดย\s+.+?[·•‧\-\–—|]\s*พ\.?\s*ศ\.?\s*([0-9๐-๙]{4})", text
    )
    if artist_year_pattern:
        raw_year = artist_year_pattern.group(1)
        digits_map = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
        year_be = int(raw_year.translate(digits_map))
        return str(year_be - 543)

    # --- Buddhist year ---
    buddhist_year = re.search(r"พ\.ศ\.?\s*(\d{4})", text)
    if buddhist_year:
        year = int(buddhist_year.group(1)) - 543
        return str(year)

    # --- RELEASE: extract following 20 chars and filter digits ---
    release_pos = re.search(r"release", text, re.IGNORECASE)
    if release_pos:
        start = release_pos.end()
        snippet = text[start:start + 20]
        digits = re.findall(r"\d{4}", snippet)
        if digits:
            return digits[0]

    # --- Thai-style date (e.g. "12 สิงหาคม 2566") ---
    thai_date = re.search(r"\d{1,2}\s*[ก-๙]+\s*(\d{4})", text)
    if thai_date:
        year = int(thai_date.group(1))
        if year >= 2500:
            year -= 543
        return str(year)

    return None

# ---------------------------------------------------------------------
# Extractor (updated version)
# ---------------------------------------------------------------------
def extract_song_info(text: str) -> dict:
    info = {}

    # --- Album ---
    album_match = re.search(r"ALBUM\s*:\s*([^,]+)", text, re.IGNORECASE)
    if album_match:
        info["album"] = album_match.group(1).strip()

    # --- RELEASE: extract following 20 chars and filter digits ---
    release_pos = re.search(r"release", text, re.IGNORECASE)
    if release_pos:
        start = release_pos.end()
        snippet = text[start:start + 20]  # take 20 chars after "release"
        digits = re.findall(r"\d{4}", snippet)
        if digits:
            info["release_year_candidate"] = digits[0]

    # --- Buddhist year ---
    buddhist_year = re.search(r"พ\.ศ\.?\s*(\d{4})", text)
    if buddhist_year:
        info["buddhist_year"] = int(buddhist_year.group(1))
        info["christian_year"] = info["buddhist_year"] - 543

    # --- Thai-style date (e.g. "12 สิงหาคม 2566") ---
    thai_date = re.search(r"(\d{1,2}\s*[ก-๙]+\s*\d{4})", text)
    if thai_date:
        info["release_date_th"] = thai_date.group(1).strip()

    return info


# ---------------------------------------------------------------------
# Scraper function (DuckDuckGo → HTML → extract)
# ---------------------------------------------------------------------
def scrape_song_metadata(song_title: str, artist: str, base_query: str, ending_keyword: str="") -> dict:
    """Scrape DuckDuckGo and extract album/year info for a Thai song."""
    query_url = f"{base_query}{song_title}+{artist}+{ending_keyword}"
    print(f"🔍 Searching: {song_title}+{artist}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--ignore-certificate-errors",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-features=SameSiteByDefaultCookies",
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-software-rasterizer",
                "--single-process",
            ],
        )
        context = browser.new_context(
            ignore_https_errors=True,
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        for attempt in range(ATTEMPT_STEP):
            try:
                page.goto(query_url, timeout=60000)
                break
            except Exception as e:
                print(f"⚠️ Retry {attempt+1}/{ATTEMPT_STEP} due to {e}")
                time.sleep(random.uniform(3, 6))
        text = page.inner_text("body")
        browser.close()

    return extract_year(text)


# ---------------------------------------------------------------------
# Main process
# ---------------------------------------------------------------------
def update_csv_with_scraped_years(input_csv: str, output_csv: str):
    # Prepare output file and header
    fieldnames = ThaiMusicRecord.get_fields()
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)

    # Create (or overwrite) CSV with header once at start
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    # Process input CSV line by line
    with open(input_csv, newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        for row in reader:
            song_title = row.get("song_title", "")
            artist = row.get("artist", "")
            if not song_title or song_title == "เนื้อเพลง":
                continue

            # --- Step 1: Try multiple search sources ---
            rel_year = scrape_song_metadata(song_title, artist, "https://www.google.com/search?q=")
            if not rel_year:
                rel_year = scrape_song_metadata(song_title, artist, "https://duckduckgo.com/?q=", "เพลง+อัลบั้ม+ปี")
            if not rel_year:
                rel_year = scrape_song_metadata(song_title, artist, "https://duckduckgo.com/?q=", "release")

            # --- Step 2: Update record ---
            row["release_year"] = rel_year
            valid_fields = {k: row.get(k, "") for k in ThaiMusicRecord.get_fields()}
            record = ThaiMusicRecord(**valid_fields)

            # --- Step 3: Save immediately if year found ---
            if rel_year:
                with open(output_csv, "a", newline="", encoding="utf-8") as f_out:
                    writer = csv.DictWriter(f_out, fieldnames=fieldnames)
                    writer.writerow(record.to_dict())
                print(f"💾 Saved: {song_title} - {artist} ({rel_year})")

            else:
                print(f"❌ No year found for: {song_title} - {artist}")

    print(f"\n✅ Finished processing. All found-year records saved to → {output_csv}")


# ---------------------------------------------------------------------
# Example run
# ---------------------------------------------------------------------
if __name__ == "__main__":
    update_csv_with_scraped_years(
        input_csv="thai_songs_52.csv",
        output_csv="thai_songs_updated_52.csv",
    )