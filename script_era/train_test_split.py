# prepare_dataset.py
import pandas as pd
from sklearn.model_selection import train_test_split

# ---------------------------------------
# CONFIG
# ---------------------------------------
CSV_PATH = "datasets/song_lyrics_map_era.csv"
TEXT_COL = "clean_lyrics"
TARGET_COL = "year"

# ---------------------------------------
# Load CSV
# ---------------------------------------
df = pd.read_csv(CSV_PATH)

# Clean + filter
df[TARGET_COL] = pd.to_numeric(df[TARGET_COL], errors='coerce')
df = df.dropna(subset=[TEXT_COL, TARGET_COL])
df[TARGET_COL] = df[TARGET_COL].astype("float32")
df = df.rename(columns={TARGET_COL: "labels"})

# ---------------------------------------
# Train / Val / Test split
# ---------------------------------------
train_df, test_df = train_test_split(df, test_size=0.10, random_state=42)
train_df, val_df = train_test_split(train_df, test_size=0.10, random_state=42)

print("Train:", len(train_df))
print("Val:", len(val_df))
print("Test:", len(test_df))

# ---------------------------------------
# SAVE SPLITS
# ---------------------------------------
train_df.to_csv("datasets/train_split.csv", index=False)
val_df.to_csv("datasets/val_split.csv", index=False)
test_df.to_csv("datasets/test_split.csv", index=False)

print("Saved: train_split.csv, val_split.csv, test_split.csv")