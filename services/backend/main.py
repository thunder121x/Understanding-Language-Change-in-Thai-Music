from pathlib import Path
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


def _load_models() -> dict:
    model_path = Path(__file__).parent / "app" / "models" / "logistic_regression.pkl"
    return joblib.load(model_path)


# Load pickle only once at startup.
MODEL_BUNDLE = _load_models()


class PredictRequest(BaseModel):
    text: str


@app.post("/predict")
def predict(payload: PredictRequest) -> dict:
    if not payload.text:
        raise HTTPException(status_code=400, detail="Text is required for prediction.")

    scores: dict[str, float] = {}
    clean_text = _clean_text(payload.text)

    for genre, bundle in MODEL_BUNDLE.items():
        vectorizer = bundle["vectorizer"]
        model = bundle["model"]

        x_input = vectorizer.transform([clean_text])
        probability = model.predict_proba(x_input)[0][1]
        scores[genre] = float(probability)

    predicted_genre = max(scores, key=scores.get)
    return {"predicted_genre": predicted_genre, "scores": scores}
