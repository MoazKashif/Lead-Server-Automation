<div align="center">

<img src="https://img.shields.io/badge/QuantumAI-Lead%20Automation-6C63FF?style=for-the-badge&logoColor=white" />

# 🤖 Lead Server Automation
### *AI-Powered Lead Intake, Triage & Auto-Reply Engine for QuantumAI*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Gemini AI](https://img.shields.io/badge/Google%20Gemini-2.5%20Flash-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![n8n](https://img.shields.io/badge/n8n-Workflow-EA4B71?style=flat-square&logo=n8n&logoColor=white)](https://n8n.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

> **Stop manually replying to every lead. Let AI do it — instantly.**  
> A full-stack lead automation server that captures, triages, and responds to every incoming inquiry with a personalized AI-drafted email — all in seconds.

</div>

---

## 📖 Table of Contents

- [The Problem It Solves](#-the-problem-it-solves)
- [How It Works](#-how-it-works)
- [Feature Highlights](#-feature-highlights)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [API Reference](#-api-reference)
- [n8n Workflow Integration](#-n8n-workflow-integration)
- [Admin Dashboard](#-admin-dashboard)
- [Configuration](#️-configuration)
- [Deployment](#-deployment)
- [Future Roadmap](#-future-roadmap)
- [Contributing](#-contributing)

---

## 🎯 The Problem It Solves

Running a startup means every lead matters — but manually reading, categorizing, and replying to every form submission is a time sink. Leads go cold. Replies get delayed. High-priority prospects don't get the urgency they deserve.

**Lead Server Automation** fixes this for QuantumAI by creating a fully automated pipeline:

1. A visitor fills out the **lead capture form** on the QuantumAI website
2. The server **instantly triages** the lead using Google Gemini AI — scoring urgency, classifying intent, and generating a personalized email draft
3. The lead is **stored in the dashboard** with full AI analysis so nothing falls through the cracks
4. A **personalized reply email is automatically sent** via n8n + Gmail — without anyone lifting a finger

---

## ⚙️ How It Works

```
┌─────────────────────┐
│   QuantumAI Website  │  ← Lead fills the contact/booking form
│   (landing.html)     │
└────────┬────────────┘
         │ POST /webhook
         ▼
┌─────────────────────────────────────────────────────┐
│                  FastAPI Server (app.py)             │
│                                                     │
│  1. Validate incoming lead data (Pydantic)          │
│  2. Call Google Gemini AI for analysis:             │
│     ├── Urgency Score  (High / Medium / Low)        │
│     ├── Category       (Inquiry / Support / etc.)   │
│     ├── 2-3 Bullet Summary of the request          │
│     └── Personalized HTML Email Draft              │
│  3. Save enriched lead to local database            │
│  4. Fire background task → n8n Webhook             │
└───────────┬─────────────────────────────────────────┘
            │
    ┌───────┴────────┐
    │                │
    ▼                ▼
┌────────┐    ┌──────────────────────────────┐
│leads.  │    │  n8n Automation Workflow     │
│json    │    │  └── Gmail Node              │
│(local  │    │       └── Sends personalized │
│  DB)   │    │           reply to the lead  │
└────────┘    └──────────────────────────────┘
    │
    ▼
┌─────────────────────┐
│  Admin Dashboard     │  ← You see all leads, AI scores,
│  (index.html)        │    urgency levels & draft replies
└─────────────────────┘
```

---

## ✨ Feature Highlights

### 🧠 AI-Powered Lead Intelligence
- Uses **Google Gemini 2.5 Flash** to analyze every lead the moment it arrives
- Scores urgency as **High / Medium / Low** with a written rationale
- Classifies intent: `Inquiry`, `Technical Support`, `Partnership`, `Job Application`, or `Spam`
- Generates a **fully personalized HTML email reply** — not a generic template, but a response that directly addresses what the lead actually wrote

### 🔁 Smart Fallback Chain
- If Gemini is overloaded (503) or rate-limited (429), the system automatically **retries with exponential backoff** and **falls back through model tiers**: `gemini-2.5-flash → gemini-2.0-flash → gemini-1.5-flash`
- If no API key is configured at all, a **rule-based mock analyzer** kicks in so the server still runs and classifies leads intelligently in offline/demo mode

### 📬 Automated Email via n8n
- Analyzed leads are forwarded to an **n8n webhook** in a background task (non-blocking)
- The included `My workflow.json` can be imported directly into n8n — it picks up the AI-generated HTML email and fires it to the lead via Gmail
- The email body is the AI's personalized draft — signed as *The QuantumAI Team*

### 📊 Admin Dashboard
- A clean, real-time dashboard at `/` shows all incoming leads
- Each card displays: name, company, urgency badge, category tag, AI summary, and the full draft reply
- Stats panel shows totals broken down by urgency, category, and source
- Leads can be deleted individually

### 🔧 Zero-Restart Config
- API keys and n8n webhook URLs can be updated via the `/api/config` endpoint — no server restart needed
- All config is persisted to `.env` automatically

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.10+, FastAPI, Uvicorn |
| **AI Engine** | Google Gemini (`google-genai` SDK) — `gemini-2.5-flash` |
| **Data Validation** | Pydantic v2 |
| **Automation** | n8n (self-hosted or cloud), Gmail node |
| **Storage** | JSON flat-file (local, zero-dependency) |
| **Frontend** | Vanilla HTML/CSS/JS (served as static files) |
| **Deployment** | Procfile-ready (Railway / Render / Heroku compatible) |
| **Config** | `python-dotenv`, `.env` file |

---

## 📁 Project Structure

```
Lead-Server-Automation/
│
├── app.py                  # Core FastAPI application — all routes & logic
├── leads.json              # Local lead database (auto-created on first run)
├── requirements.txt        # Python dependencies
├── Procfile                # Deployment entry point (Railway/Render/Heroku)
├── My workflow.json        # Importable n8n automation workflow
├── README_DEPLOY.md        # Deployment-specific notes
├── .gitignore
│
└── static/
    ├── index.html          # Admin dashboard (served at /)
    └── landing.html        # Public lead capture form (served at /website)
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- A [Google AI Studio](https://aistudio.google.com/) account for a free Gemini API key
- (Optional) [n8n](https://n8n.io) instance for email automation

### 1. Clone the Repository

```bash
git clone https://github.com/MoazKashif/Lead-Server-Automation.git
cd Lead-Server-Automation
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the project root (the server will auto-create one on first run, but you can do it manually):

```env
GEMINI_API_KEY=your_gemini_api_key_here
N8N_WEBHOOK_URL=your_n8n_webhook_url_here
```

Or configure it live through the admin dashboard after starting the server.

### 4. Run the Server

```bash
python app.py
```

Or via uvicorn directly:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Access the App

| URL | Description |
|-----|-------------|
| `http://localhost:8000/` | Admin Dashboard |
| `http://localhost:8000/website` | Public Lead Capture Form |
| `http://localhost:8000/docs` | Interactive API Docs (Swagger UI) |

---

## 📡 API Reference

### `POST /webhook`
Receives a new lead, runs AI analysis, saves it, and triggers the n8n email workflow.

**Request Body:**
```json
{
  "name": "Sarah Johnson",
  "email": "sarah@acme.com",
  "phone": "+1-555-0199",
  "company": "Acme Corp",
  "message": "We're looking for an AI automation solution for our sales pipeline. What do you offer?",
  "source": "Web Form"
}
```

**Response:**
```json
{
  "status": "success",
  "lead": {
    "id": "20250619143022123456",
    "timestamp": "2025-06-19T14:30:22Z",
    "name": "Sarah Johnson",
    "email": "sarah@acme.com",
    "ai_analysis": {
      "urgency": "Medium",
      "urgency_rationale": "Pricing/solution inquiry — important but not time-critical.",
      "category": "Inquiry",
      "summary": "• Client is exploring AI automation for their sales pipeline\n• Wants to understand QuantumAI's service offerings\n• Likely evaluating multiple vendors",
      "draft_reply": "<p>Dear Sarah,</p><p>Thank you for reaching out...</p>",
      "ai_status": "AI Evaluated (gemini-2.5-flash)"
    }
  }
}
```

---

### `GET /api/leads`
Returns all stored leads in reverse chronological order.

### `DELETE /api/leads/{lead_id}`
Deletes a specific lead by its ID.

### `GET /api/stats`
Returns aggregate dashboard statistics.

```json
{
  "total_leads": 47,
  "urgency": { "High": 5, "Medium": 21, "Low": 21 },
  "category": { "Inquiry": 30, "Partnership": 8, "Technical Support": 6, "Spam": 3 },
  "source": { "Web Form": 40, "Referral": 7 }
}
```

### `GET /api/config`
Returns current configuration status (key presence only, never the key itself).

### `POST /api/config`
Updates the Gemini API key and/or n8n webhook URL at runtime without restarting the server.

```json
{
  "api_key": "AIza...",
  "n8n_url": "https://your-n8n.instance/webhook/xyz"
}
```

---

## 🔗 n8n Workflow Integration

The repo includes `My workflow.json` — a pre-built n8n workflow you can import in two steps:

1. In your n8n instance, go to **Workflows → Import from File**
2. Select `My workflow.json`

The workflow listens for the webhook payload from this server and uses the `email_html` field (the AI-generated reply) to send a personalized email to the lead via Gmail.

**Payload fields the n8n workflow uses:**

| Field | Description |
|-------|-------------|
| `to_email` | Lead's email address |
| `email_subject` | Pre-set subject line |
| `email_html` | AI-generated personalized HTML email body |
| `name`, `company` | For workflow conditions/logging |

---

## 📊 Admin Dashboard

The dashboard (served at `/`) gives a full CRM-style view of all incoming leads:

- **Stats cards** — total leads, urgency breakdown, category distribution
- **Lead cards** — each showing name, company, source, urgency badge (color-coded), AI category tag, AI summary bullets, and the full draft reply
- **Delete** — remove leads you've handled or marked as spam
- **Config panel** — update your Gemini API key and n8n URL without touching `.env`

---

## 🗂️ Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Recommended | Google Gemini API key. Without it, the server uses a rule-based mock analyzer. |
| `N8N_WEBHOOK_URL` | Optional | Your n8n webhook endpoint. Without it, leads are stored but emails are not sent automatically. |

Both can be set in `.env` or updated live via `POST /api/config`.

---

## ☁️ Deployment

The project includes a `Procfile` making it ready to deploy on:

- **[Railway](https://railway.app)** — connect repo, add env vars, deploy
- **[Render](https://render.com)** — add as a Web Service, set `GEMINI_API_KEY` in environment
- **[Heroku](https://heroku.com)** — `git push heroku main`

The Procfile starts the server with:
```
web: uvicorn app:app --host 0.0.0.0 --port $PORT
```

> ⚠️ **Note:** When deploying, `leads.json` lives on the ephemeral filesystem. Your data will reset on each redeploy. See the [Future Roadmap](#-future-roadmap) for the recommended upgrade path.

---

## 🛣 Future Roadmap

This project is intentionally lean for a solo startup context. As QuantumAI scales, here are the natural evolution points:

### 🗄️ Database — Replace `leads.json` with a Real Database
The current flat-file approach works perfectly for low-to-medium traffic. However, concurrent webhook hits (multiple form submissions at the same time) can cause a race condition where two writes happen simultaneously and one overwrites the other.

**Recommended upgrades by scale:**

| Traffic Level | Recommendation |
|--------------|----------------|
| Low-Medium (< 100 leads/day) | SQLite via `aiosqlite` — zero-infrastructure, just swap the file |
| Medium (100–1000 leads/day) | **Supabase** (hosted Postgres) — free tier, real-time dashboard, REST API out of the box, zero DevOps |
| High (1000+ leads/day) | Dedicated PostgreSQL (via Railway, Render, or Neon) with async SQLAlchemy |

Supabase is the sweet spot: you get a proper relational database, a built-in dashboard to view leads without the custom frontend, Row Level Security, and webhook support — all free up to 50,000 rows.

### 🔐 Security Hardening
- Add API key authentication on `/api/config` (currently unprotected — anyone with the URL can overwrite your Gemini key)
- Restrict CORS from `allow_origins=["*"]` to your actual frontend domain in production
- Add rate limiting on `/webhook` to prevent spam submissions

### 🧠 AI Enhancements
- **Lead scoring** — a numerical score (0–100) in addition to urgency tier, based on company size signals, message specificity, and intent keywords
- **Duplicate detection** — flag leads from the same email address
- **Follow-up scheduling** — if a High urgency lead hasn't been responded to in 2 hours, trigger a Slack/email alert via n8n

### 📧 Email Improvements
- **Human-in-the-loop mode** — instead of auto-sending, send the draft to your own inbox first for one-click approval
- **Multi-channel support** — route Partnership leads to a different email thread, Technical Support to a helpdesk ticket (Freshdesk/Linear)

### 📊 Dashboard Enhancements
- Filterable/sortable lead table (by date, urgency, category)
- Export to CSV
- Lead status tracking (New → Contacted → Qualified → Closed)

---

## 🤝 Contributing

This is an internal QuantumAI project, but contributions, suggestions, and issue reports are welcome.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m 'Add: your feature description'`
4. Push and open a Pull Request

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

Built with ⚡ by **[Moaz Kashif](https://github.com/MoazKashif)** for **QuantumAI**

*If this saved you time, consider giving the repo a ⭐*

</div>
