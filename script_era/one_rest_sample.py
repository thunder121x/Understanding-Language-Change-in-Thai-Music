# build_binary_era_datasets.py
import os
import pandas as pd
from sklearn.model_selection import train_test_split

RAW_PATH = "datasets_old/song_lyrics_map_era.csv"
OUTPUT_DIR = "binary_datasets"
os.makedirs(OUTPUT_DIR, exist_ok=True)

df = pd.read_csv(RAW_PATH)

# 6 classes
ALL_ERAS = sorted(df["song_era"].unique())
print("ALL ERAS:", ALL_ERAS)

# Limit negatives per class (optional)
MAX_NEG = 200_000

for era in ALL_ERAS:
    print(f"\n========================================")
    print(f"BUILDING DATASET FOR ERA = {era}")
    print("========================================")

    era_folder = os.path.join(OUTPUT_DIR, era)
    os.makedirs(era_folder, exist_ok=True)

    # 1) POSITIVE samples (all rows where era == target)
    pos_df = df[df["song_era"] == era].copy()
    num_pos = len(pos_df)
    print(f"Positive samples: {num_pos}")

    # 2) NEGATIVE samples (from other classes)
    neg_df = df[df["song_era"] != era].copy()

    # undersample negative to match positives or MAX_NEG
    neg_target = min(num_pos, MAX_NEG)
    neg_df = neg_df.sample(n=neg_target, random_state=42)
    print(f"Negative samples (undersampled): {len(neg_df)}")

    # 3) Combine dataset
    combined = pd.concat([pos_df, neg_df], axis=0).reset_index(drop=True)

    # 4) Add binary label
    binary_col = f"is_{era}"
    combined[binary_col] = (combined["song_era"] == era).astype(int)

    print("Final combined dataset size:", len(combined))

    # 5) Train/Val/Test split (stratified on binary label)
    train_df, test_df = train_test_split(
        combined,
        test_size=0.10,
        random_state=42,
        stratify=combined[binary_col]
    )
    train_df, val_df = train_test_split(
        train_df,
        test_size=0.10,
        random_state=42,
        stratify=train_df[binary_col]
    )

    print(f"Train: {len(train_df)} | Val: {len(val_df)} | Test: {len(test_df)}")

    # 6) Save dataset
    train_df.to_csv(os.path.join(era_folder, "train.csv"), index=False)
    val_df.to_csv(os.path.join(era_folder, "val.csv"), index=False)
    test_df.to_csv(os.path.join(era_folder, "test.csv"), index=False)

print("\nAll 6 binary datasets created successfully!")