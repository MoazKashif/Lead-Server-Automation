# Deployment (Render)

This project is a FastAPI server that serves:
- `GET /` -> dashboard UI (`static/index.html`)
- `GET /website` -> public landing page (`static/landing.html`)
- `POST /webhook` -> lead intake endpoint
- `GET /api/*` -> dashboard data

## 1) Push to GitHub
Create a GitHub repo (or use the existing one) and push the `lead-server` folder contents.

## 2) Create a Render Web Service
1. Go to https://render.com
2. Click **New** -> **Web Service**
3. Connect your GitHub repo
4. Choose **Runtime:** Python
5. Choose **Build Command:** `pip install -r requirements.txt`
6. Choose **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - (Render usually honors `Procfile`, but this is the safe explicit command.)

## 3) Set Environment Variables
In **Environment** section, set:
- `GEMINI_API_KEY` (optional but recommended for real AI scoring)
- `N8N_WEBHOOK_URL` (optional)

Render will provide `PORT` automatically.

## 4) (Recommended) Use a persistent storage for leads.json
This app stores leads in the local file `leads.json`.
On free hosts, filesystem may be ephemeral after restarts.
To keep data, attach persistent storage if your plan supports it.

## 5) Testing after deploy
After deployment, Render provides a URL like:
- Dashboard: `https://YOUR-RENDER-URL/`
- Website: `https://YOUR-RENDER-URL/website`
- Webhook: `https://YOUR-RENDER-URL/webhook`

Verify by submitting the landing form, then check dashboard tables.

