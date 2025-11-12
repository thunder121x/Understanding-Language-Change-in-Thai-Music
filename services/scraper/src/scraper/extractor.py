
import re
import csv
import random
import time
from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright
from scraper.dataclass import ThaiMusicRecord

from .constants import ATTEMPT_STEP

def extract_year(text: str, is_heavy_search: bool = False) -> str | None:
    """
    Extracts the most likely release year from text based on priority:
    1. 'เพลงโดย ... พ.ศ.' pattern (artist and Buddhist year)
    2. 'ทาง ... พ.ศ.' pattern (platform and Buddhist year)
    3. 'release' or 'วางจำหน่าย' keyword followed by 20 chars → find 4-digit year
    4. (Heavy search only) Buddhist year or Thai-style date patterns
    """

    digits_map = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")

    # --- 1️⃣ เพลงโดย ... พ.ศ. (artist reference) ---
    artist_year_pattern = re.search(
        r"เพลงโดย\s+.+?[·•‧\-\–—|]\s*พ\.?\s*ศ\.?\s*([0-9๐-๙]{4})",
        text,
    )
    if artist_year_pattern:
        raw_year = artist_year_pattern.group(1)
        year_be = int(raw_year.translate(digits_map))
        return str(year_be - 543)

    # --- 2️⃣ ทาง ... พ.ศ. (e.g., 'ทาง Apple Music พ.ศ. 2538') ---
    platform_year_pattern = re.search(
        r"ทาง\s+[A-Za-zก-๙\s]+?\s*พ\.?\s*ศ\.?\s*([0-9๐-๙]{4})",
        text,
    )
    if platform_year_pattern:
        raw_year = platform_year_pattern.group(1)
        year_be = int(raw_year.translate(digits_map))
        return str(year_be - 543)

    # --- 3️⃣ RELEASE / วางจำหน่าย keyword ---
    release_pos = re.search(r"release", text, re.IGNORECASE)
    release_pos_th = re.search(r"วางจำหน่าย", text, re.IGNORECASE)
    apple_release = re.search(r"Apple Music", text, re.IGNORECASE)
    if release_pos or release_pos_th or apple_release:
        release = release_pos or release_pos_th or apple_release
        start = release.end()
        snippet = text[start:start + 20]
        digits = re.findall(r"\d{4}", snippet)
        if digits:
            return digits[0]

    # --- 4️⃣ (optional) Heavy fallback search ---
    if is_heavy_search:
        # Buddhist year only
        buddhist_year = re.search(r"พ\.ศ\.?\s*(\d{4})", text)
        if buddhist_year:
            year = int(buddhist_year.group(1)) - 543
            return str(year)

        # Thai-style date (e.g. "12 สิงหาคม 2566")
        thai_date = re.search(r"\d{1,2}\s*[ก-๙]+\s*(\d{4})", text)
        if thai_date:
            year = int(thai_date.group(1))
            if year >= 2500:
                year -= 543
            return str(year)

    return None


def scrape_song_metadata(song_title: str, artist: str, base_query: str, ending_keyword: str="") -> dict:
    """Scrape DuckDuckGo and extract album/year info for a Thai song."""
    query_url = f"{base_query}{song_title}+{artist}+{ending_keyword}"
    print(f"🔍 Searching: {song_title}+{artist}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
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
            java_script_enabled=True,
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