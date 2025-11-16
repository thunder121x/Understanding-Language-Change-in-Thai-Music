import logging
import re
import urllib.parse
from pathlib import Path

import joblib
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
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


def scrape_lyrics_lyricsfreak(song: str, artist: str | None = None) -> str | None:
    """Scrape lyrics from lyricsfreak for a given song (artist optional)."""
    query = f"{song} {artist}" if artist else song
    search_url = (
        "https://www.lyricsfreak.com/search.php?a=search&type=song&q="
        + urllib.parse.quote(query)
    )

    try:
        search_html = requests.get(
            search_url,
            timeout=10,
            headers={"Referer": "https://www.lyricsfreak.com"},
        ).text
    except requests.RequestException as exc:
        logging.warning("lyricsfreak search failed: %s", exc)
        return None

    soup = BeautifulSoup(search_html, "html.parser")
    result_link = soup.select_one("a.song")
    if not result_link:
        return None

    song_url = "https://www.lyricsfreak.com" + result_link["href"]
    try:
        song_html = requests.get(
            song_url,
            timeout=10,
            headers={"Referer": "https://www.lyricsfreak.com"},
        ).text
    except requests.RequestException as exc:
        logging.warning("lyricsfreak fetch failed: %s", exc)
        return None

    soup_song = BeautifulSoup(song_html, "html.parser")
    lyrics_block = soup_song.select_one("div.lyrictxt")

    return lyrics_block.get_text("\n").strip() if lyrics_block else None


SCRAPERS = [
    ("lyricsfreak", scrape_lyrics_lyricsfreak),
]


def scrape_lyrics(song_name: str, artist_name: str | None = None) -> str | None:
    """Try available scrapers sequentially; return first lyrics found."""
    logging.info("Searching lyrics for %s - %s", song_name, artist_name)
    for site_name, scraper_fn in SCRAPERS:
        logging.info("Trying %s ...", site_name)
        lyrics = scraper_fn(song_name, artist_name)
        if lyrics:
            logging.info("Found lyrics on %s", site_name)
            return lyrics
        logging.info("Not found on %s", site_name)

    logging.warning("Lyrics not found on any configured sites.")
    return None


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


@app.get("/api/search-lyrics")
def search_lyrics(title: str, artist: str | None = None) -> dict:
    """
    Fetch lyrics by title (artist optional). Returns 404 if nothing is found.
    """
    if not title:
        raise HTTPException(status_code=400, detail="Title is required for search.")

    lyrics = scrape_lyrics(title, artist)
    if not lyrics:
        raise HTTPException(status_code=404, detail="Lyrics not found.")

    return {"title": title, "artist": artist, "lyrics": lyrics}
