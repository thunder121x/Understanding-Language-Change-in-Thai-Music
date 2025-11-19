import pandas as pd
from sklearn.model_selection import train_test_split

RAW_PATH = "datasets_old/song_lyrics_map_era.csv"
df = pd.read_csv(RAW_PATH)

MAX_PER_CLASS = 20000  # try 100_000 if you want smaller

df_balanced = (
    df
    .groupby("song_era", group_keys=False)
    .apply(lambda g: g.sample(
        n=min(len(g), MAX_PER_CLASS),
        random_state=42
    ))
    .reset_index(drop=True)
)

print("After soft-undersampling:", len(df_balanced))
print(df_balanced["song_era"].value_counts())

train_df, test_df = train_test_split(
    df_balanced,
    test_size=0.10,
    random_state=42,
    stratify=df_balanced["song_era"],
)
train_df, val_df = train_test_split(
    train_df,
    test_size=0.10,
    random_state=42,
    stratify=train_df["song_era"],
)

print("Train:", len(train_df))
print("Val:", len(val_df))
print("Test:", len(test_df))

train_df.to_csv("datasets_min/train_split.csv", index=False)
val_df.to_csv("datasets_min/val_split.csv", index=False)
test_df.to_csv("datasets_min/test_split.csv", index=False)