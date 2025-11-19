# train_binary_hf.py
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

# -----------------------------------------------
# CONFIG
# -----------------------------------------------
TEXT_COL = "clean_lyrics"
BASE_DIR = "binary_datasets_thunder"
MODEL_SAVE_DIR = "hf_binary_models_thunder"
os.makedirs(MODEL_SAVE_DIR, exist_ok=True)

# Choose model
model_name = "roberta-base"

eras = sorted(os.listdir(BASE_DIR))

for era in eras:
    print(f"\n\n===========================================")
    print(f" TRAINING ERA: {era}")
    print(f"===========================================\n")

    wandb.init(
        project="era-binary-classification",
        name=f"binary-{era}",
        reinit=True
    )

    # -----------------------------------------------
    # LOAD DATA
    # -----------------------------------------------
    train_df = pd.read_csv(f"{BASE_DIR}/{era}/train.csv")
    val_df   = pd.read_csv(f"{BASE_DIR}/{era}/val.csv")
    test_df  = pd.read_csv(f"{BASE_DIR}/{era}/test.csv")
    
    train_size = len(train_df)

    if train_size > 100_000:
        LR = 3e-5
    elif train_size > 10_000:
        LR = 1e-5
    else:
        LR = 5e-6

    bin_col = f"is_{era}"
    train_df["labels"] = train_df[bin_col]
    val_df["labels"]   = val_df[bin_col]
    test_df["labels"]  = test_df[bin_col]

    train_ds = Dataset.from_pandas(train_df)
    val_ds   = Dataset.from_pandas(val_df)
    test_ds  = Dataset.from_pandas(test_df)

    # -----------------------------------------------
    # TOKENIZER
    # -----------------------------------------------
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    def tok(batch):
        return tokenizer(
            batch[TEXT_COL],
            truncation=True,
            max_length=256,
            padding="max_length",
        )

    train_ds = train_ds.map(tok, batched=True)
    val_ds   = val_ds.map(tok, batched=True)
    test_ds  = test_ds.map(tok, batched=True)

    cols = ["input_ids", "attention_mask", "labels"]
    train_ds.set_format("torch", columns=cols)
    val_ds.set_format("torch", columns=cols)
    test_ds.set_format("torch", columns=cols)

    # -----------------------------------------------
    # MODEL
    # -----------------------------------------------
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=2,
        torch_dtype=torch.bfloat16,
    )

    # -----------------------------------------------
    # METRICS
    # -----------------------------------------------
    acc = evaluate.load("accuracy")
    f1  = evaluate.load("f1")

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        return {
            "accuracy": acc.compute(predictions=preds, references=labels)["accuracy"],
            "f1": f1.compute(predictions=preds, references=labels, average="binary")["f1"],
        }

    # -----------------------------------------------
    # TRAINING ARGS
    # -----------------------------------------------
    args = TrainingArguments(
        output_dir=f"tmp_out/{era}",
        eval_strategy="epoch",
        save_strategy="epoch",

        per_device_train_batch_size=64,
        per_device_eval_batch_size=64,

        num_train_epochs=6,
        learning_rate=LR,

        bf16=True,
        dataloader_num_workers=6,
        logging_steps=10,
        load_best_model_at_end=True,

        report_to="wandb",
        run_name=f"binary-{era}",
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        compute_metrics=compute_metrics,
        tokenizer=tokenizer
    )

    # -----------------------------------------------
    # TRAIN + TEST
    # -----------------------------------------------
    trainer.train()

    test_metrics = trainer.evaluate(test_ds)
    print("TEST METRICS:", test_metrics)

    # -----------------------------------------------
    # SAFE SAVE (NEVER CORRUPTS)
    # -----------------------------------------------
    save_path = f"{MODEL_SAVE_DIR}/{era}"
    os.makedirs(save_path, exist_ok=True)

    print(f"\n🔐 Saving model safely to: {save_path}")

    # 1. Trainer save (config, training info)
    trainer.save_model(save_path)

    # 2. Raw model weights (ensures complete safetensors or pytorch_model.bin)
    model.save_pretrained(save_path)

    # 3. Tokenizer save (ensures full tokenizer files exist)
    tokenizer.save_pretrained(save_path)

    print(f"✅ Model fully saved → {save_path}\n")

print("\n🎉 ALL ERA MODELS TRAINED SUCCESSFULLY!\n")