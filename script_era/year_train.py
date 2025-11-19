# train_model.py
import os
import pandas as pd
import numpy as np
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
)
import evaluate
import torch
from torch.utils.data import WeightedRandomSampler
import wandb
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ---------------------------------------
# CONFIG
# ---------------------------------------
TEXT_COL = "clean_lyrics"
LABEL_COL = "year"
model_name = "roberta-base"
MAX_LEN = 256
WANDB_PROJECT = "thai-music-year-regression"

# ---------------------------------------
# Init W&B
# ---------------------------------------
wandb.init(
    project=WANDB_PROJECT,
    name="roberta-regression-v1",
    config={
        "model": model_name,
        "max_len": MAX_LEN,
        "batch_size": 16,
        "epochs": 4,
        "lr": 2e-5,
    }
)

# ---------------------------------------
# Load PRE-SPLIT CSVs
# ---------------------------------------
train_df = pd.read_csv("datasets/train_split.csv")
val_df   = pd.read_csv("datasets/val_split.csv")
test_df  = pd.read_csv("datasets/test_split.csv")

print("Loaded splits:", len(train_df), len(val_df), len(test_df))

train_df = train_df.rename(columns={LABEL_COL: "labels"})
val_df   = val_df.rename(columns={LABEL_COL: "labels"})
test_df  = test_df.rename(columns={LABEL_COL: "labels"})

train_df["labels"] = train_df["labels"].astype(np.float32)
val_df["labels"]   = val_df["labels"].astype(np.float32)
test_df["labels"]  = test_df["labels"].astype(np.float32)

# ---------------------------------------
# Weighted sampler
# ---------------------------------------
if "song_era" in train_df.columns:
    era_counts = train_df["song_era"].value_counts()
    train_weights = train_df["song_era"].map(lambda e: 1.0 / era_counts[e]).values
    sampler = WeightedRandomSampler(
        weights=train_weights,
        num_samples=len(train_df),
        replacement=True
    )
else:
    sampler = None
    print("Warning: 'song_era' not found → skipping sampler.")

# ---------------------------------------
# Convert to HF Dataset
# ---------------------------------------
train_ds = Dataset.from_pandas(train_df[[TEXT_COL, "labels"]])
val_ds   = Dataset.from_pandas(val_df[[TEXT_COL, "labels"]])
test_ds  = Dataset.from_pandas(test_df[[TEXT_COL, "labels"]])

# ---------------------------------------
# Tokenizer
# ---------------------------------------
tokenizer = AutoTokenizer.from_pretrained(model_name)

def tokenize(batch):
    return tokenizer(
        batch[TEXT_COL],
        padding="max_length",
        truncation=True,
        max_length=MAX_LEN,
    )

train_ds = train_ds.map(tokenize, batched=True)
val_ds   = val_ds.map(tokenize, batched=True)
test_ds  = test_ds.map(tokenize, batched=True)

train_ds.set_format("torch", columns=["input_ids", "attention_mask", "labels"])
val_ds.set_format("torch", columns=["input_ids", "attention_mask", "labels"])
test_ds.set_format("torch", columns=["input_ids", "attention_mask", "labels"])

# ---------------------------------------
# Model
# ---------------------------------------
model = AutoModelForSequenceClassification.from_pretrained(
    model_name,
    num_labels=1,
    problem_type="regression"
)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Using device:", device)

# ---------------------------------------
# Metrics
# ---------------------------------------
mse_metric = evaluate.load("mse")
mae_metric = evaluate.load("mae")

def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    predictions = predictions.flatten()
    labels = labels.flatten()
    mse = mse_metric.compute(predictions=predictions, references=labels)["mse"]
    rmse = float(np.sqrt(mse))
    mae = mae_metric.compute(predictions=predictions, references=labels)["mae"]
    return {"rmse": rmse, "mse": mse, "mae": mae}

# ---------------------------------------
# TrainingArguments
# ---------------------------------------
train_args = TrainingArguments(
    output_dir="./roberta_year_regression",
    eval_strategy="epoch",
    save_strategy="epoch",
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    num_train_epochs=4,
    learning_rate=2e-5,
    weight_decay=0.01,
    fp16=True,
    gradient_accumulation_steps=2,
    load_best_model_at_end=True,
    metric_for_best_model="rmse",
    greater_is_better=False,
    logging_strategy="steps",
    logging_steps=50,
    save_total_limit=2,
    report_to="wandb",     # ENABLE W&B LOGGING
)

# ---------------------------------------
# Trainer
# ---------------------------------------
trainer = Trainer(
    model=model,
    args=train_args,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    tokenizer=tokenizer,
    compute_metrics=compute_metrics,
)

if sampler is not None:
    from torch.utils.data import DataLoader

    def get_train_dataloader():
        return DataLoader(
            train_ds,
            batch_size=train_args.per_device_train_batch_size,
            sampler=sampler,
            collate_fn=trainer.data_collator,
        )

    trainer.get_train_dataloader = get_train_dataloader

# ---------------------------------------
# Train
# ---------------------------------------
print("\n========================= Starting Training =========================\n")
trainer.train()

# ---------------------------------------
# Test Evaluation
# ---------------------------------------
print("\n========================= Test Evaluation =========================\n")
metrics = trainer.evaluate(test_ds)
print("Test metrics:", metrics)
wandb.log({"test_rmse": metrics["eval_rmse"]})

# ---------------------------------------
# Save final model
# ---------------------------------------
trainer.save_model("./roberta_year_regression_final")
tokenizer.save_pretrained("./roberta_year_regression_final")

print("\nTraining complete! Saved to ./roberta_year_regression_final\n")
wandb.finish()