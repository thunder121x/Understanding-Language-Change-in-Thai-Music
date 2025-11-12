import requests
from bs4 import BeautifulSoup
import pandas as pd
import uuid
from datetime import datetime
import time

BASE_URL = "https://xn--72c9bva0i.meemodel.com"
SCRAPER_MODULE = "meemodel_scraper.py"
PLATFORM = "meemodel"
PLATFORM_TYPE = "lyrics-site"
CONTENT_TYPE = "lyrics"
LANGUAGE_VARIANT = "Central Thai text"

all_songs = []

# สมมติเว็บมี pagination
for page in range(1, 201):
    url = f"{BASE_URL}/เนื้อเพลง?page={page}"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    
    songs_on_page = soup.select("a[title^='เนื้อเพลง']")
    if not songs_on_page:
        break
    
    for a_tag in songs_on_page:
        song_title = a_tag.text.strip()
        song_url = a_tag["href"]
        artist_tag = a_tag.find_next("div", class_="artistName")
        artist = artist_tag.text.strip() if artist_tag else ""
        
        all_songs.append({
            "song_title": song_title,
            "artist": artist,
            "url": song_url
        })
    
    print(f"Fetched page {page}, total songs: {len(all_songs)}")
    if len(all_songs) >= 4000:
        break
    time.sleep(0.5)

# ดึงเนื้อเพลง + ปี + raw HTML
data = []
scrape_date = datetime.now().strftime("%Y-%m-%d")

for i, song in enumerate(all_songs[:4000]):
    # ตรวจสอบ URL
    song_url = song["url"]
    if not song_url.startswith("http"):
        song_url = BASE_URL + song_url
    
    try:
        res = requests.get(song_url)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch {song_url}: {e}")
        continue
    
    lyrics_div = soup.find("div", id="lyric-lyric")
    raw_text = str(lyrics_div) if lyrics_div else ""
    full_text = lyrics_div.get_text(separator="\n", strip=True) if lyrics_div else ""
    lyric_text = full_text.replace(song["song_title"], "").strip()
    
    year_tag = soup.find("span", class_="year")
    release_year = int(year_tag.text.strip()) if year_tag and year_tag.text.strip().isdigit() else None
    
    data.append({
        "id": str(uuid.uuid4()),
        "platform": PLATFORM,
        "platform_type": PLATFORM_TYPE,
        "url": song_url,
        "content_type": CONTENT_TYPE,
        "timestamp": None,
        "scraper_module": SCRAPER_MODULE,
        "song_title": song["song_title"],
        "artist": song["artist"],
        "album": None,
        "release_year": release_year,
        "genre": None,
        "language_variant": LANGUAGE_VARIANT,
        "lyric_text": lyric_text,
        "raw_text": raw_text,
        "scrape_date": scrape_date
    })
    
    if (i+1) % 50 == 0:
        print(f"Processed {i+1} songs")
    time.sleep(0.2)

df = pd.DataFrame(data)
df.to_csv("thai_songs_4000.csv", index=False, encoding="utf-8-sig")
print("Saved 4000 songs successfully!")
