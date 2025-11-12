import requests
from bs4 import BeautifulSoup
import time
import uuid
import pandas as pd
from datetime import datetime

# Import your dataclass
from scraper.dataclass import ThaiMusicRecord
from scraper.config import SCRAPE_DATE
from scraper.constants import DATETIME_FORMAT

BASE_URL = "https://xn--72c9bva0i.meemodel.com"
SCRAPER_MODULE = "meemodel_scraper.py"
PLATFORM = "meemodel"
PLATFORM_TYPE = "lyrics-site"
CONTENT_TYPE = "lyrics"
LANGUAGE_VARIANT = "Central Thai text"

all_songs = []

# Step 1: Collect song URLs from paginated listing (~40 songs)
for page in range(1, 51):
    url = f"{BASE_URL}/เนื้อเพลง?page={page}"
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        print(f"Failed to fetch page {page}: {e}")
        break

    songs_on_page = soup.select("a[title^='เนื้อเพลง']")
    if not songs_on_page:
        print(f"No songs found on page {page}, maybe last page.")
        break

    for a_tag in songs_on_page:
        song_title = a_tag.text.strip()
        song_url = BASE_URL + a_tag["href"]
        artist_tag = a_tag.find_next("div", class_="artistName")
        artist = artist_tag.text.strip() if artist_tag else ""

        all_songs.append({
            "song_title": song_title,
            "artist": artist,
            "url": song_url
        })

    print(f"Fetched page {page}, total songs: {len(all_songs)}")
    time.sleep(0.5)  # avoid server block

# Step 2: Scrape lyrics and metadata for first 40 songs
records = []

for i, song in enumerate(all_songs[:40]):
    try:
        res = requests.get(song["url"])
        soup = BeautifulSoup(res.text, "html.parser")

        lyrics_div = soup.find("div", id="lyric-lyric")
        raw_text = str(lyrics_div) if lyrics_div else ""
        full_text = lyrics_div.get_text(separator="\n", strip=True) if lyrics_div else ""
        text = full_text.replace(song["song_title"], "").strip()

        # Extract year if exists
        year_tag = soup.find("span", class_="year")
        release_year = year_tag.text.strip() if year_tag and year_tag.text.strip().isdigit() else None

        record = ThaiMusicRecord(
            id=str(uuid.uuid4()),
            platform=PLATFORM,
            platform_type=PLATFORM_TYPE,
            url=song["url"],
            content_type=CONTENT_TYPE,
            timestamp=None,
            scraper_module=SCRAPER_MODULE,
            song_title=song["song_title"],
            artist=song["artist"],
            album=None,
            release_year=release_year,
            genre=None,
            language_variant=LANGUAGE_VARIANT,
            text=text,
            raw_text=raw_text,
            scrape_date=SCRAPE_DATE
        )
        records.append(record)

        if (i + 1) % 50 == 0:
            print(f"Processed {i+1}/{len(all_songs[:40])} songs")

        time.sleep(0.2)
    except Exception as e:
        print(f"Failed to process song {song['song_title']}: {e}")

# Step 3: Convert all records to a DataFrame and save CSV
df = pd.DataFrame([r.to_dict() for r in records])
df.to_csv("thai_songs_40.csv", index=False, encoding="utf-8-sig")
print("Saved 40 songs successfully!")
