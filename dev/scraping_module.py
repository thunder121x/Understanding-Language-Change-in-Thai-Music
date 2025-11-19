import csv
import re
import random
import time
from pathlib import Path
from typing import Optional
from scraper.dataclass import ThaiMusicRecord
from scraper.extractor import scrape_song_metadata

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
                rel_year = scrape_song_metadata(song_title, artist, "https://www.google.com/search?q=", "apple")
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
        input_csv="thai_songs_partial.csv",
        output_csv="thai_songs_partial_.csv",
    )