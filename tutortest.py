import requests
from bs4 import BeautifulSoup
import pandas as pd
import uuid
from datetime import datetime
import time
import signal
import sys

from scraper.extractor import scrape_song_metadata

# === ฟังก์ชันบันทึกเมื่อหยุด (Ctrl + C) ===
def save_and_exit(signum, frame):
    print("\n\n🟡 Interrupted! Saving current progress...")
    pd.DataFrame(all_songs).to_csv("thai_songs_partial.csv", index=False, encoding="utf-8-sig")
    print(f"✅ Saved {len(all_songs)} songs before exit.")
    sys.exit(0)

signal.signal(signal.SIGINT, save_and_exit)

# === ตั้งค่าพื้นฐาน ===
BASE_URL = "https://xn--72c9bva0i.meemodel.com"
PLATFORM = "meemodel"
PLATFORM_TYPE = "lyrics-site"
CONTENT_TYPE = "lyrics"
LANGUAGE_VARIANT = "Central Thai text"
SCRAPER_MODULE = "meemodel_scraper.py"

thai_letters = list("ธ")  # จะลองเฉพาะตัว "ก" ก่อน
all_songs = []
seen_urls = set()
scrape_date = datetime.now().strftime("%Y-%m-%d")

# === เริ่มดึงข้อมูล ===
for letter in thai_letters:
    try:
        res = requests.get(f"{BASE_URL}/หาศิลปิน/{letter}")
        res.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {letter}: {e}")
        continue

    soup = BeautifulSoup(res.text, "html.parser")
    artist_links = soup.select("a[href^='/ศิลปิน/']")

    for a in artist_links:
        artist_name = a.text.strip()
        artist_url = a["href"]
        if not artist_url.startswith("http"):
            artist_url = BASE_URL + artist_url

        # เข้าแต่ละศิลปิน
        try:
            res_artist = requests.get(artist_url)
            res_artist.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching artist {artist_url}: {e}")
            continue

        soup_artist = BeautifulSoup(res_artist.text, "html.parser")
        song_links = soup_artist.select("a[title^='เนื้อเพลง']")

        for s in song_links:
            song_title = s.text.strip()
            if song_title == "เนื้อเพลง":
                continue
            song_url = s["href"]
            if not song_url.startswith("http"):
                song_url = BASE_URL + song_url

            if song_url in seen_urls:
                continue

            # เข้าเพลง
            try:
                res_song = requests.get(song_url)
                res_song.raise_for_status()
            except requests.exceptions.RequestException as e:
                print(f"Failed to fetch {song_url}: {e}")
                continue

            soup_song = BeautifulSoup(res_song.text, "html.parser")

            # --- ดึงเนื้อเพลง ---
            lyrics_div = soup_song.find("div", id="lyric-lyric")
            raw_text = str(lyrics_div) if lyrics_div else ""
            full_text = lyrics_div.get_text(separator="\n", strip=True) if lyrics_div else ""
            lyric_text = full_text.replace(song_title, "").strip()

            # --- ดึงปี ---
            year_tag = soup_song.find("span", class_="year")
            release_year = int(year_tag.text.strip()) if year_tag and year_tag.text.strip().isdigit() else None
            rel_year = scrape_song_metadata(song_title, artist_name, "https://www.google.com/search?q=")
            if not rel_year:
                rel_year = scrape_song_metadata(song_title, artist_name, "https://www.google.com/search?q=", "apple")
            if not rel_year:
                rel_year = scrape_song_metadata(song_title, artist_name, "https://duckduckgo.com/?q=", "เพลง+อัลบั้ม+ปี")
            if not rel_year:
                rel_year = scrape_song_metadata(song_title, artist_name, "https://duckduckgo.com/?q=", "release")

            # --- ดึงหมวดเพลง (genre) ---
            genre = None
            genre_tag = soup_song.find("strong", string=lambda x: x and "หมวดเพลง" in x)
            if genre_tag:
                # เช่น <strong>หมวดเพลง : ลูกทุ่ง</strong>
                text = genre_tag.get_text(strip=True)
                if "หมวดเพลง" in text:
                    genre = text.split(":")[-1].strip()

            all_songs.append({
                "id": str(uuid.uuid4()),
                "platform": PLATFORM,
                "platform_type": PLATFORM_TYPE,
                "url": song_url,
                "content_type": CONTENT_TYPE,
                "timestamp": None,
                "scraper_module": SCRAPER_MODULE,
                "song_title": song_title,
                "artist": artist_name,
                "album": None,
                "release_year": rel_year,
                "genre": genre,
                "language_variant": LANGUAGE_VARIANT,
                "lyric_text": lyric_text,
                "raw_text": raw_text,
                "scrape_date": scrape_date
            })

            seen_urls.add(song_url)
            time.sleep(0.2)

    print(f"✅ Completed letter {letter}, total unique songs: {len(all_songs)}")

# === บันทึกเมื่อจบรัน ===
df = pd.DataFrame(all_songs)
df.to_csv("thai_songs_no_duplicate.csv", index=False, encoding="utf-8-sig")
print(f"🎉 Saved {len(all_songs)} unique songs successfully!")
