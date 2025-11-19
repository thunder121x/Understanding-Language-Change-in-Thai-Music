import pandas as pd

# 1) Ensure year is numeric
df = pd.read_csv("datasets/song_lyrics_cleaned.csv")
df["year"] = pd.to_numeric(df["year"], errors="coerce")
df = df.dropna(subset=["year"])

# 2) Filter valid range
df = df[(df["year"] >= 1970) & (df["year"] <= 2025)]

# 3) Map to eras (vectorized)
bins = [1970, 1980, 1990, 2000, 2010, 2020, 2026]
labels = ["1970s", "1980s", "1990s", "2000s", "2010s", "2020s"]

df["song_era"] = pd.cut(df["year"], bins=bins, labels=labels, right=False)

print("Counts per era:")
print(df["song_era"].value_counts())
df.to_csv("datasets/song_lyrics_map_era.csv")