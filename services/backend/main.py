from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.post("/predict")
def predict(item: dict) -> dict:
    text = item.get("text", "")
    # Replace this stub with your ML inference logic.
    return {"predicted_era": "1990s", "input": text}
