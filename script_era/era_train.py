import torch
from datasets import load_from_disk
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
)
import evaluate
import numpy as np
import os
import wandb

# ---------------------------------------
# Init W&B
# ---------------------------------------
wandb.init(
    project="thai-music-era-classification",
    name="roberta-era-superfast",
)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ---------------------------------------
# Load tokenized datasets
# ---------------------------------------
train_ds = load_from_disk("datasets/tokenized/train")
val_ds   = load_from_disk("datasets/tokenized/val")
test_ds  = load_from_disk("datasets/tokenized/test")

# Format as PyTorch tensors
cols = ["input_ids", "attention_mask", "labels"]
train_ds.set_format(type="torch", columns=cols)
val_ds.set_format(type="torch", columns=cols)
test_ds.set_format(type="torch", columns=cols)

# Number of labels (eras)
num_labels = len(set(train_ds["labels"]))

tokenizer = AutoTokenizer.from_pretrained("roberta-base")

# ---------------------------------------
# ERA CLASSIFICATION MODEL
# ---------------------------------------
model = AutoModelForSequenceClassification.from_pretrained(
    "roberta-base",
    num_labels=num_labels
)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Using device:", device)
model.to(device)
model.gradient_checkpointing_enable()
optim="adamw_torch_fused"
# ---------------------------------------
# Metrics
# ---------------------------------------
acc_metric = evaluate.load("accuracy")
f1_metric  = evaluate.load("f1")

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": acc_metric.compute(predictions=preds, references=labels)["accuracy"],
        "f1": f1_metric.compute(predictions=preds, references=labels, average="weighted")["f1"]
    }

# ---------------------------------------
# GPU Optimizations
# ---------------------------------------
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32       = True

USE_BF16 = torch.cuda.is_bf16_supported()
BATCH_SIZE = 512

# ---------------------------------------
# Training Arguments
# ---------------------------------------
train_args = TrainingArguments(
    output_dir="./roberta_era_classifier_exp2",
    eval_strategy="epoch",
    save_strategy="epoch",

    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,

    num_train_epochs=10,
    learning_rate=2e-5,
    weight_decay=0.01,

    # GPU settings
    fp16=False,
    bf16=True,
    dataloader_num_workers=16,
    dataloader_prefetch_factor=4,
    dataloader_pin_memory=True,
    dataloader_persistent_workers=True,

    # Classification metrics
    metric_for_best_model="accuracy",
    greater_is_better=True,

    optim=optim,
    lr_scheduler_type="cosine",
    warmup_ratio=0.08,

    logging_strategy="steps",
    logging_steps=20,
    save_total_limit=2,
    load_best_model_at_end=True,
    tf32=True,
    
    report_to="wandb",
    run_name="roberta-era",
)

# ---------------------------------------
# Trainer
# ---------------------------------------
trainer = Trainer(
    model=model,
    args=train_args,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    # tokenizer=tokenizer,
    compute_metrics=compute_metrics,
)

# ---------------------------------------
# Train
# ---------------------------------------
trainer.train()

# ---------------------------------------
# Evaluate
# ---------------------------------------
metrics = trainer.evaluate(test_ds)
print(metrics)

# ---------------------------------------
# Save model
# ---------------------------------------
trainer.save_model("roberta_era_final_exp2")
tokenizer.save_pretrained("roberta_era_final_exp2")