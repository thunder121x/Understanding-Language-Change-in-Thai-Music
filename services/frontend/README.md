# Next.js Frontend

## Getting started

```bash
cd services/frontend
npm install
cp .env.local.example .env.local
npm run dev
```

The `NEXT_PUBLIC_API_URL` must point at your FastAPI deployment (e.g. `http://localhost:8000` or your Render URL).

## Deploying on Vercel

1. Push this repo to GitHub.
2. Import the `services/frontend` directory as a Vercel project.
3. Add the `NEXT_PUBLIC_API_URL` environment variable in the Vercel dashboard.
4. Deploy.
