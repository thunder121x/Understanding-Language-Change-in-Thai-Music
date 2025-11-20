# Understanding Language Change in Thai Music

This project explores how Thai song lyrics evolve over time by combining data analysis notebooks, modern NLP models, and a small web app for real-time prediction.

## Project structure

- `services/backend`: FastAPI inference service with TF‑IDF, Word2Vec, and RoBERTa era predictors plus a genre classifier.
- `services/frontend`: Next.js 14 interface that lets users paste lyrics, fetch lyrics by title/artist, and view model confidence.
- `dev`, `script_era`, `script_final`: exploratory notebooks, data cleaning scripts, and training utilities.
- `services/backend/app/models`: serialized models used by the API (TF‑IDF/logreg, Word2Vec, RoBERTa checkpoints).

## Requirements

- Python 3.11
- Node.js 18+ and npm
- (Optional) Docker + Docker Compose for containerized runs

## Running locally

### Backend

```bash
cd services/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

This exposes:
- `POST /predict/genre`
- `POST /predict/era/roberta` (default `/predict/era` forwards here)
- `POST /predict/era/tfidf`
- `POST /predict/era/w2v`
- `GET /api/search-lyrics` (lyrics lookup helper)
- `GET /docs` / `GET /redoc`

### Frontend

```bash
cd services/frontend
npm install
cp .env.local.example .env.local
# edit NEXT_PUBLIC_API_URL to http://localhost:8000
npm run dev
```

Visit http://localhost:3000 to access the UI. Paste lyrics or search for a title, then click “Classify from lyrics”.

## Development tips

- Notebook experiments live under `dev/` and `script_era/`. Keep large CSVs outside Git and point to them via absolute paths or symlinks.
- When updating backend models, drop new artifacts into `services/backend/app/models/<model_name>` and restart the API.
- The frontend pulls environment variables at build time; restart `npm run dev` after updating `.env.local`.

## License

See [LICENSE](LICENSE) for more details.
