# FastAPI Backend

## Local setup

```bash
cd services/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Deploying to Render/Railway

Start command:

```bash
uvicorn main:app --host 0.0.0.0 --port 10000
```
