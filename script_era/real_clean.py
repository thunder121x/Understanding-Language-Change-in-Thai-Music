import pandas as pd
import re

RAW_PATH = "datasets/song_lyrics.csv"
print("Loading:", RAW_PATH)
df = pd.read_csv(RAW_PATH)
print("Before:", len(df), "rows")

# ---------------------------------------------------------
# 1. BASIC FILTERING (keep only what survives later)
# ---------------------------------------------------------
df = df[df["language"] == "en"]
df = df[df["lyrics"].notna()]

noise_keywords = [
    "google translate", "translate", "google", "edition",
    "how to translate", "cover", "karaoke", "instrumental"
]
pattern = "|".join(noise_keywords)

df["title"] = df["title"].fillna("")
df = df[~df["title"].str.lower().str.contains(pattern)]

# ---------------------------------------------------------
# 2. YEAR CLEANING + DROP BAD ROWS
# ---------------------------------------------------------
df["year"] = pd.to_numeric(df["year"], errors="coerce")
df = df.dropna(subset=["year"])

# ---------------------------------------------------------
# 3. CLEAN LYRICS + REMOVE SHORT ENTRIES
# ---------------------------------------------------------
def clean_text(text):
    text = text.replace("\n", " ")
    text = re.sub(r"[,\.!?]", "", text)
    text = re.sub(r"\[.*?\]", " ", text)
    text = re.sub(r"\w*\d\w*", " ", text)
    text = re.sub(r"[()]", " ", text)
    return text.lower().strip()

df["clean_lyrics"] = df["lyrics"].apply(clean_text)
df = df[df["clean_lyrics"].str.len() > 20]

# ---------------------------------------------------------
# 4. REMOVE DUPLICATE CLEAN LYRICS
#    Keep rule: oldest year → highest views
# ---------------------------------------------------------
if "views" in df.columns:
    df["views"] = pd.to_numeric(df["views"], errors="coerce").fillna(0)
    df = df.sort_values(by=["clean_lyrics", "year", "views"],
                        ascending=[True, True, False])
else:
    df = df.sort_values(by=["clean_lyrics", "year"],
                        ascending=[True, True])

df = df.drop_duplicates(subset=["clean_lyrics"], keep="first")
print("After cleaning:", len(df), "rows")

# Save full cleaned file (optional)
df.to_csv("datasets/song_lyrics_cleaned.csv", index=False)

# ---------------------------------------------------------
# 5. FILTER BY YEAR RANGE
# ---------------------------------------------------------
df = df[(df["year"] >= 1970) & (df["year"] <= 2025)]