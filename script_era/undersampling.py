import pandas as pd
import re
from sklearn.model_selection import train_test_split

RAW_PATH = "datasets_old/song_lyrics_map_era.csv"
df_small = pd.read_csv(RAW_PATH)

# ---------------------------------------------------------
# ⭐ 8. UNDERSAMPLE EACH ERA (max 10,000 per class)
# ---------------------------------------------------------
print("\nApplying undersampling (10,000 per era)...")

df_balanced = (
    df_small
    .groupby("song_era", group_keys=False)
    .apply(lambda x: x.sample(n=min(len(x), 20000), random_state=42))
)

print("After undersampling:", len(df_balanced), "rows")
print(df_balanced["song_era"].value_counts())

# ---------------------------------------------------------
# 9. SPLITTING (LOW RAM)
# ---------------------------------------------------------
train_df, test_df = train_test_split(df_balanced, test_size=0.10, random_state=42, stratify=df_balanced["song_era"])
train_df, val_df = train_test_split(train_df, test_size=0.10, random_state=42, stratify=train_df["song_era"])

print("\nFinal split sizes:")
print("Train:", len(train_df))
print("Val:", len(val_df))
print("Test:", len(test_df))

train_df.to_csv("datasets/train_split.csv", index=False)
val_df.to_csv("datasets/val_split.csv", index=False)
test_df.to_csv("datasets/test_split.csv", index=False)

print("\n✅ DONE — undersampled to max 10k per era + low-RAM splits.")