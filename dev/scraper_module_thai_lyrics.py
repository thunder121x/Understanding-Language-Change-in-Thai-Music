# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import pandas as pd
import uuid
from datetime import datetime
import time
import os
import re
from tqdm.notebook import tqdm

def scrape_song_metadata(song_title, artist_name, base_url="https://duckduckgo.com/html/?q=", extra_keyword="ปี"):
    query = f"{artist_name} {song_title} {extra_keyword}"
    url = f"{base_url}{requests.utils.quote(query)}"
    try:
        res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        year_candidates = re.findall(r"(19[5-9]\d|20[0-2]\d)", text)
        if year_candidates:
            years = [int(y) for y in year_candidates if 1950 <= int(y) <= datetime.now().year]
            if years:
                return min(years)
        return None
    except Exception as e:
        print(f"❌ Error searching year for {song_title}: {e}")
        return None

# === ตั้งค่าพื้นฐาน ===
BASE_URL = "https://xn--72c9bva0i.meemodel.com"
OUTPUT_FILE = "thai_songs_progress_5.csv"
FINAL_FILE = "thai_songs_all_years_final5.csv"
PLATFORM = "meemodel"
PLATFORM_TYPE = "lyrics-site"
CONTENT_TYPE = "lyrics"
LANGUAGE_VARIANT = "Central Thai text"
SCRAPER_MODULE = "meemodel_scraper.py"

thai_letters = list("กขฃคฅฆงจฉชซฌญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรฤลฦวศษสหฬอฮ")
scrape_date = datetime.now().strftime("%Y-%m-%d")

# === โหลดข้อมูลที่ค้างไว้ ===
if os.path.exists(OUTPUT_FILE):
    df_existing = pd.read_csv(OUTPUT_FILE)
    all_songs = df_existing.to_dict("records")
    seen_urls = set(df_existing["url"].tolist())
    print(f"🔁 Resume from previous run ({len(all_songs)} songs loaded)")
else:
    all_songs = []
    seen_urls = set()
    print("🚀 Starting new scrape")

try:
    for letter in tqdm(thai_letters, desc="Scraping by Thai letter"):
        try:
            res = requests.get(f"{BASE_URL}/หาศิลปิน/{letter}")
            res.raise_for_status()
        except Exception as e:
            print(f"Error fetching {letter}: {e}")
            continue

        soup = BeautifulSoup(res.text, "html.parser")
        artist_links = soup.select("a[href^='/ศิลปิน/']")

        for a in tqdm(artist_links, desc=f"Artists for {letter}", leave=False):
            artist_name = a.text.strip()
            artist_url = a["href"]
            if not artist_url.startswith("http"):
                artist_url = BASE_URL + artist_url

            try:
                res_artist = requests.get(artist_url)
                res_artist.raise_for_status()
            except Exception as e:
                print(f"Error fetching artist {artist_url}: {e}")
                continue

            soup_artist = BeautifulSoup(res_artist.text, "html.parser")
            song_links = soup_artist.select("a[title^='เนื้อเพลง']")

            for s in tqdm(song_links, desc=f"{artist_name}", leave=False):
                song_title = s.text.strip()
                if song_title == "เนื้อเพลง":
                    continue
                song_url = s["href"]
                if not song_url.startswith("http"):
                    song_url = BASE_URL + song_url

                if song_url in seen_urls:
                    continue

                try:
                    res_song = requests.get(song_url)
                    res_song.raise_for_status()
                except Exception as e:
                    print(f"Failed to fetch {song_url}: {e}")
                    continue

                soup_song = BeautifulSoup(res_song.text, "html.parser")
                lyrics_div = soup_song.find("div", id="lyric-lyric")
                raw_text = str(lyrics_div) if lyrics_div else ""
                full_text = lyrics_div.get_text(separator="\n", strip=True) if lyrics_div else ""
                lyric_text = full_text.replace(song_title, "").strip()

                # 🔎 หา release_year (แต่ไม่ข้ามถ้าไม่มี)
                rel_year = scrape_song_metadata(song_title, artist_name)

                genre = None
                genre_tag = soup_song.find("strong", string=lambda x: x and "หมวดเพลง" in x)
                if genre_tag:
                    text = genre_tag.get_text(strip=True)
                    if "หมวดเพลง" in text:
                        genre = text.split(":")[-1].strip()

                all_songs.append({
                    "id": str(uuid.uuid4()),
                    "platform": PLATFORM,
                    "platform_type": PLATFORM_TYPE,
                    "url": song_url,
                    "content_type": CONTENT_TYPE,
                    "scraper_module": SCRAPER_MODULE,
                    "song_title": song_title,
                    "artist": artist_name,
                    "release_year": rel_year,
                    "genre": genre,
                    "language_variant": LANGUAGE_VARIANT,
                    "lyric_text": lyric_text,
                    "raw_text": raw_text,
                    "scrape_date": scrape_date
                })

                seen_urls.add(song_url)
                time.sleep(0.3)

        pd.DataFrame(all_songs).to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
        print(f"✅ Saved progress: {len(all_songs)} songs so far.")

except KeyboardInterrupt:
    print("🟡 Interrupted! Saving current progress...")
    pd.DataFrame(all_songs).to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

# === บันทึกสุดท้าย ===
df = pd.DataFrame(all_songs)
df.to_csv(FINAL_FILE, index=False, encoding="utf-8-sig")
print(f"🎉 Done! Saved {len(df)} songs (all years) to {FINAL_FILE}")