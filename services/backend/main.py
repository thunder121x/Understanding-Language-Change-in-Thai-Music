from pathlib import Path
import logging
import re

import joblib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Thai Lyrics Era Classifier")

# Allow requests from any origin during development; tighten for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/ping")
def ping() -> dict:
    return {"message": "pong"}


def _clean_text(text: str) -> str:
    """Mirror notebook preprocessing for lyrics text."""
    text = text.replace("\n", " ")
    text = re.sub(r"[,\.!?]", "", text)
    text = re.sub(r"\[.*?\]", " ", text)
    text = re.sub(r"\w*\d\w*", " ", text)
    text = re.sub(r"[()]", " ", text)
    return text.lower().strip()


def _load_models_genre_model() -> dict:
    model_path = Path(__file__).parent / "app" / "models" / "logistic_regression.pkl"
    return joblib.load(model_path)


# Load pickle only once at startup.
GENRE_MODEL = _load_models_genre_model()


def _load_era_models(model_dir: Path | None = None) -> dict:
    """
    Load one-vs-rest logistic regression models and TF-IDF vectorizers per era.
    Directory structure should be model_dir/<era>/{logreg.joblib, tfidf.joblib}.
    """
    base_dir = model_dir or (Path(__file__).parent / "app" / "models" / "logreg_binary_era")
    eras: list[str] = []

    for item in base_dir.iterdir():
        if not item.is_dir() or item.name.startswith("."):
            continue
        eras.append(item.name)

    eras = sorted(eras)
    logging.info("Loading era models: %s", eras)

    models: dict[str, dict] = {}
    for era in eras:
        era_path = base_dir / era
        clf_path = era_path / "logreg.joblib"
        tfidf_path = era_path / "tfidf.joblib"

        if not (clf_path.exists() and tfidf_path.exists()):
            logging.warning("Skipping %s — missing model or vectorizer file", era)
            continue

        models[era] = {"clf": joblib.load(clf_path), "tfidf": joblib.load(tfidf_path)}

    if not models:
        raise RuntimeError(f"No era models loaded from {base_dir}")

    return models


# Load era classifiers once at startup.
ERA_MODELS = _load_era_models()


class PredictRequest(BaseModel):
    text: str


@app.post("/predict/genre")
def predict(payload: PredictRequest) -> dict:
    if not payload.text:
        raise HTTPException(status_code=400, detail="Text is required for prediction.")

    scores: dict[str, float] = {}
    clean_text = _clean_text(payload.text)

    for genre, bundle in GENRE_MODEL.items():
        vectorizer = bundle["vectorizer"]
        model = bundle["model"]

        x_input = vectorizer.transform([clean_text])
        probability = model.predict_proba(x_input)[0][1]
        scores[genre] = float(probability)

    predicted_genre = max(scores, key=scores.get)
    return {"predicted_genre": predicted_genre, "scores": scores}


@app.post("/predict/era")
def predict_era(payload: PredictRequest) -> dict:
    if not payload.text:
        raise HTTPException(status_code=400, detail="Text is required for prediction.")

    probs: dict[str, float] = {}
    clean_text = _clean_text(payload.text)

    for era, bundle in ERA_MODELS.items():
        clf = bundle["clf"]
        tfidf = bundle["tfidf"]

        x_input = tfidf.transform([clean_text])
        probability = clf.predict_proba(x_input)[0][1]  # probability of POS class
        probs[era] = float(probability)

    predicted_era = max(probs, key=probs.get)
    return {"predicted_era": predicted_era, "scores": probs}
