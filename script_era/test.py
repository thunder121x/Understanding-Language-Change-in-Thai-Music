# tfidf_train.py
import os
import joblib
import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report


# -----------------------------
# CONFIG
# -----------------------------
TEXT_COL = "clean_lyrics"
ERA_COL  = "song_era"
MODEL_DIR = "tfidf_models"

os.makedirs(MODEL_DIR, exist_ok=True)


# -----------------------------
# LOAD DATA
# -----------------------------
train_df = pd.read_csv("datasets/train_split.csv")
val_df   = pd.read_csv("datasets/val_split.csv")
test_df  = pd.read_csv("datasets/test_split.csv")

print("Loaded datasets:")
print(len(train_df), "train")
print(len(val_df), "val")
print(len(test_df), "test")


# -----------------------------
# LABEL ENCODING
# -----------------------------
label_encoder = LabelEncoder()
train_df["label_id"] = label_encoder.fit_transform(train_df[ERA_COL])
val_df["label_id"]   = label_encoder.transform(val_df[ERA_COL])
test_df["label_id"]  = label_encoder.transform(test_df[ERA_COL])

y_train = train_df["label_id"].values
y_val   = val_df["label_id"].values
y_test  = test_df["label_id"].values

num_classes = len(label_encoder.classes_)
print("Num classes =", num_classes)


# -----------------------------
# TF-IDF VECTORIZE
# -----------------------------
vectorizer = TfidfVectorizer(
    stop_words="english",
    max_features=50000,
    ngram_range=(1, 2),
    min_df=3
)

print("Fitting TF-IDF...")
X_train = vectorizer.fit_transform(train_df[TEXT_COL])
X_val   = vectorizer.transform(val_df[TEXT_COL])
X_test  = vectorizer.transform(test_df[TEXT_COL])

print("TF-IDF complete.")
print("Train shape:", X_train.shape)


# -----------------------------
# TRAIN ONE-VS-REST (manual)
# -----------------------------
models = []
probas_train = []
probas_val = []

print("\nTraining Logistic Regression (OvR)...\n")

for c in range(num_classes):
    print(f"Training classifier for class {c}/{num_classes-1}...")
    y_train_binary = (y_train == c).astype(int)
    y_val_binary   = (y_val == c).astype(int)

    clf = LogisticRegression(
        max_iter=500,
        class_weight="balanced",
        solver="liblinear"
    )

    clf.fit(X_train, y_train_binary)
    models.append(clf)

    probas_train.append(clf.predict_proba(X_train)[:, 1])
    probas_val.append(clf.predict_proba(X_val)[:, 1])

print("\nAll classifiers trained.")


# -----------------------------
# COMBINE PROBABILITIES
# -----------------------------
probas_train = np.vstack(probas_train).T
probas_val   = np.vstack(probas_val).T

y_pred_train = probas_train.argmax(axis=1)
y_pred_val   = probas_val.argmax(axis=1)

print("\n===== EVALUATION =====")
print("Train Accuracy:", accuracy_score(y_train, y_pred_train))
print("Val Accuracy:", accuracy_score(y_val, y_pred_val))
print("\nValidation Classification Report:")
print(classification_report(y_val, y_pred_val, target_names=label_encoder.classes_))


# -----------------------------
# TEST SET PREDICTION
# -----------------------------
probas_test = []
for clf in models:
    probas_test.append(clf.predict_proba(X_test)[:, 1])

probas_test = np.vstack(probas_test).T
y_pred_test = probas_test.argmax(axis=1)

print("Test Accuracy:", accuracy_score(y_test, y_pred_test))
print("\nTest Classification Report:")
print(classification_report(y_test, y_pred_test, target_names=label_encoder.classes_))


# -----------------------------
# SAVE MODELS + TF-IDF + ENCODER
# -----------------------------
print("\nSaving models...")

# Save all binary logistic models
for c, clf in enumerate(models):
    joblib.dump(clf, f"{MODEL_DIR}/logreg_class_{c}.joblib")

# Save vectorizer + encoder
joblib.dump(vectorizer, f"{MODEL_DIR}/tfidf_vectorizer.joblib")
joblib.dump(label_encoder, f"{MODEL_DIR}/label_encoder.joblib")

print("All models saved to:", MODEL_DIR)
print("Done!")