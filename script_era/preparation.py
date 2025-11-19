import pandas as pd
import re
from sklearn.model_selection import train_test_split

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

# ---------------------------------------------------------
# 6. MAP YEAR → ERA
# ---------------------------------------------------------
bins = [1970, 1980, 1990, 2000, 2010, 2020, 2026]
labels = ["1970s", "1980s", "1990s", "2000s", "2010s", "2020s"]

df["song_era"] = pd.cut(df["year"], bins=bins, labels=labels, right=False)

# ---------------------------------------------------------
# 7. KEEP ONLY NEEDED COLUMNS FOR TRAINING
# ---------------------------------------------------------
# create ID column if missing
if "id" not in df.columns:
    df["id"] = range(1, len(df)+1)

df_small = df[["id", "clean_lyrics", "year", "song_era"]]

mapped_path = "datasets/song_lyrics_map_era.csv"
df_small.to_csv(mapped_path, index=False)
print("Saved era-mapped small file:", mapped_path)

# ---------------------------------------------------------
# 8. SPLITTING (LOW RAM)
# ---------------------------------------------------------
train_df, test_df = train_test_split(df_small, test_size=0.10, random_state=42)
train_df, val_df = train_test_split(train_df, test_size=0.10, random_state=42)

print("Train:", len(train_df))
print("Val:", len(val_df))
print("Test:", len(test_df))

train_df.to_csv("datasets/train_split.csv", index=False)
val_df.to_csv("datasets/val_split.csv", index=False)
test_df.to_csv("datasets/test_split.csv", index=False)

print("Saved train_split.csv, val_split.csv, test_split.csv")
print("\n✅ DONE — optimized for low RAM usage.")