import os
import numpy as np
import pandas as pd
import torch
import evaluate
import wandb

from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
)

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
TEXT_COL = "clean_lyrics"
ERA_COL  = "song_era"

# ⭐ Choose model here:
# model_name = "roberta-base"                     # no FlashAttention2

wandb.init(
    project="thai-music-era-classification",
    name="era-classifier",
)

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# -------------------------------------------------
# LOAD CSV DATA
# -------------------------------------------------
train_df = pd.read_csv("datasets_min/train_split.csv")
val_df   = pd.read_csv("datasets_min/val_split.csv")
test_df  = pd.read_csv("datasets_min/test_split.csv")

# Map labels
eras = sorted(train_df[ERA_COL].unique())
era2id = {e:i for i,e in enumerate(eras)}

train_df["labels"] = train_df[ERA_COL].map(era2id)
val_df["labels"]   = val_df[ERA_COL].map(era2id)
test_df["labels"]  = test_df[ERA_COL].map(era2id)

# Convert to HF datasets
train_ds = Dataset.from_pandas(train_df)
val_ds   = Dataset.from_pandas(val_df)
test_ds  = Dataset.from_pandas(test_df)

# -------------------------------------------------
# TOKENIZER
# -------------------------------------------------
tokenizer = AutoTokenizer.from_pretrained(model_name)

def tokenize_fn(batch):
    return tokenizer(
        batch[TEXT_COL],
        max_length=512,
        truncation=True,
        padding="max_length",
    )

train_ds = train_ds.map(tokenize_fn, batched=True)
val_ds   = val_ds.map(tokenize_fn, batched=True)
test_ds  = test_ds.map(tokenize_fn, batched=True)

cols = ["input_ids", "attention_mask", "labels"]
train_ds.set_format(type="torch", columns=cols)
val_ds.set_format(type="torch", columns=cols)
test_ds.set_format(type="torch", columns=cols)

# -------------------------------------------------
# MODEL
# -------------------------------------------------
model = AutoModelForSequenceClassification.from_pretrained(
    model_name,
    num_labels=len(eras),
    torch_dtype=torch.bfloat16,
    attn_implementation="flash_attention_2" if "Mistral" in model_name else None,
)

model.to("cuda")
model.gradient_checkpointing_enable()

# -------------------------------------------------
# METRICS
# -------------------------------------------------
acc_metric = evaluate.load("accuracy")
f1_metric  = evaluate.load("f1")

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": acc_metric.compute(predictions=preds, references=labels)["accuracy"],
        "f1": f1_metric.compute(predictions=preds, references=labels, average="weighted")["f1"],
    }

# -------------------------------------------------
# TRAINING ARGS
# -------------------------------------------------
train_args = TrainingArguments(
    output_dir="era_model_out",
    eval_strategy="epoch",
    save_strategy="epoch",

    per_device_train_batch_size=512,
    per_device_eval_batch_size=512,

    num_train_epochs=6,
    learning_rate=2e-5,
    warmup_ratio=0.08,

    weight_decay=0.01,
    optim="adamw_torch_fused",

    bf16=True,
    tf32=True,

    dataloader_num_workers=16,
    dataloader_prefetch_factor=4,
    dataloader_pin_memory=True,

    logging_steps=20,
    save_total_limit=2,
    load_best_model_at_end=True,

    report_to="wandb",
    run_name="era-classifier",
)

# -------------------------------------------------
# TRAINER
# -------------------------------------------------
trainer = Trainer(
    model=model,
    args=train_args,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    compute_metrics=compute_metrics,
    tokenizer=tokenizer,
)

# TRAIN
trainer.train()

# TEST
metrics = trainer.evaluate(test_ds)
print(metrics)

# SAVE
trainer.save_model("era_final")
tokenizer.save_pretrained("era_final")

print("DONE ✔")