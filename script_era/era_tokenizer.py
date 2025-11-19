# tokenize_era.py
import pandas as pd
from datasets import Dataset
from transformers import AutoTokenizer
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

TEXT_COL = "clean_lyrics"
ERA_COL = "song_era"
MAX_LEN = 512
model_name = "roberta-base"

train_df = pd.read_csv("datasets/train_split.csv")
val_df   = pd.read_csv("datasets/val_split.csv")
test_df  = pd.read_csv("datasets/test_split.csv")

# Map era → label id
all_eras = sorted(train_df[ERA_COL].unique())
era2id = {era:i for i,era in enumerate(all_eras)}

train_df["labels"] = train_df[ERA_COL].map(era2id).astype(int)
val_df["labels"]   = val_df[ERA_COL].map(era2id).astype(int)
test_df["labels"]  = test_df[ERA_COL].map(era2id).astype(int)

tokenizer = AutoTokenizer.from_pretrained(model_name)

def tokenize(batch):
    return tokenizer(
        batch[TEXT_COL],
        padding="max_length",
        truncation=True,
        max_length=MAX_LEN,
    )

train_ds = Dataset.from_pandas(train_df[[TEXT_COL, "labels"]]).map(tokenize, batched=True)
val_ds   = Dataset.from_pandas(val_df[[TEXT_COL, "labels"]]).map(tokenize, batched=True)
test_ds  = Dataset.from_pandas(test_df[[TEXT_COL, "labels"]]).map(tokenize, batched=True)

# Remove raw text for speed & memory
train_ds = train_ds.remove_columns([TEXT_COL])
val_ds   = val_ds.remove_columns([TEXT_COL])
test_ds  = test_ds.remove_columns([TEXT_COL])

# Save dataset to disk
train_ds.save_to_disk("datasets/tokenized/train")
val_ds.save_to_disk("datasets/tokenized/val")
test_ds.save_to_disk("datasets/tokenized/test")

print("Tokenized datasets saved!")
print("Run train_era.py next.")