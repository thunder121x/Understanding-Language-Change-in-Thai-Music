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
def scrape_song_metadata(song_title: str, artist: str, base_query: str) -> dict:
    """Scrape DuckDuckGo and extract album/year info for a Thai song."""
    query_url = f"{base_query}{song_title}+{artist}+เพลง+อัลบั้ม+ปี"
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

    return extract_song_info(text)


# ---------------------------------------------------------------------
# Main process
# ---------------------------------------------------------------------
def update_csv_with_scraped_years(input_csv: str, output_csv: str):
    updated_records: list[ThaiMusicRecord] = []

    with open(input_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            song_title = row.get("song_title", "")
            artist = row.get("artist", "")
            if not song_title or song_title == "เนื้อเพลง":
                continue

            info = scrape_song_metadata(song_title, artist, "https://www.google.com/search?q=")
            print(f"Result Data: {info} from https://www.google.com/search?q=")

            if not info:
                info = scrape_song_metadata(song_title, artist, "https://duckduckgo.com/?q=")
                print(f"Result Data: {info} from https://duckduckgo.com/?q=")

            # update scraped values
            row["album"] = info.get("album") or row.get("album")
            year = None
            if info.get("christian_year"):
                year = str(info["christian_year"])
            elif info.get("release_year_candidate"):
                year = info["release_year_candidate"]
            elif info.get("release_year"):
                year = info["release_year"]
            else:
                year = row.get("release_date_th")

            row["release_year"] = year

            # only pass expected fields to dataclass
            valid_fields = {k: row.get(k, "") for k in ThaiMusicRecord.get_fields()}
            record = ThaiMusicRecord(**valid_fields)
            updated_records.append(record)

    # Write updated CSV
    fieldnames = ThaiMusicRecord.get_fields()
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in updated_records:
            writer.writerow(rec.to_dict())

    print(f"✅ Updated CSV saved → {output_csv}")


# ---------------------------------------------------------------------
# Example run
# ---------------------------------------------------------------------
if __name__ == "__main__":
    update_csv_with_scraped_years(
        input_csv="thai_songs_4000.csv",
        output_csv="thai_songs_updated_4.csv",
    )