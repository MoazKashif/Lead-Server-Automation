<div align="center">

<img src="https://img.shields.io/badge/FantomAI-Lead%20Automation-6C63FF?style=for-the-badge&logoColor=white" />

# 🤖 Lead Server Automation
### *AI-Powered Lead Intake, Triage & Auto-Reply Engine for FantomAI*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Gemini AI](https://img.shields.io/badge/Google%20Gemini-2.5%20Flash-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![SMTP](https://img.shields.io/badge/SMTP-Zoho%20Mail-4A154B?style=flat-square&logo=gmail&logoColor=white)](https://www.zoho.com/mail/)
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
- [SMTP Email Delivery](#-smtp-email-delivery)
- [Admin Dashboard](#-admin-dashboard)
- [Configuration](#️-configuration)
- [Deployment](#-deployment)
- [Future Roadmap](#-future-roadmap)
- [Contributing](#-contributing)

---

## 🎯 The Problem It Solves

Running a startup means every lead matters — but manually reading, categorizing, and replying to every form submission is a time sink. Leads go cold. Replies get delayed. High-priority prospects don't get the urgency they deserve.

**Lead Server Automation** fixes this for FantomAI by creating a fully automated pipeline:

1. A visitor fills out the **lead capture form** on the FantomAI website
2. The server **instantly triages** the lead using Google Gemini AI — scoring urgency, classifying intent, and generating a personalized email draft
3. The lead is **stored in the dashboard** with full AI analysis so nothing falls through the cracks
4. A **personalized reply email is automatically sent** via SMTP (Zoho Mail) — without anyone lifting a finger

---

## ⚙️ How It Works

```
┌─────────────────────┐
│   FantomAI Website  │  ← Lead fills the contact/booking form
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
│  4. Fire background task → direct SMTP email       │
└───────────┬─────────────────────────────────────────┘
            │
    ┌───────┴────────┐
    │                │
    ▼                ▼
┌────────┐    ┌──────────────────────────────┐
│leads.  │    │  SMTP (Zoho Mail)            │
│json    │    │  └── Sends personalized      │
│(local  │    │      HTML reply to the lead  │
│  DB)   │    └──────────────────────────────┘
└────────┘
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

### 📬 Automated Email via SMTP
- Analyzed leads get a personalized HTML reply sent **directly from the backend** via SMTP (Zoho Mail) in a background task (non-blocking)
- Appointment bookings also trigger a confirmation email to the requester
- The email body is the AI's personalized draft — signed as *The FantomAI Team*
- The sender name/address are set via `SMTP_FROM_NAME` and `SMTP_FROM_EMAIL`

### 📊 Admin Dashboard
- A clean, real-time dashboard at `/` shows all incoming leads
- Each card displays: name, company, urgency badge, category tag, AI summary, and the full draft reply
- Stats panel shows totals broken down by urgency, category, and source
- Leads can be deleted individually

### 🔧 Zero-Restart Config
- API keys and SMTP settings can be updated via environment variables — no server restart needed
- All config is persisted to `.env` automatically

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.10+, FastAPI, Uvicorn |
| **AI Engine** | Google Gemini (`google-genai` SDK) — `gemini-2.5-flash` |
| **Data Validation** | Pydantic v2 |
| **Email Delivery** | Direct SMTP (Zoho Mail) via `smtplib` |
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
├── email_service.py        # Central SMTP email service (send_email)
├── leads.json              # Local lead database (auto-created on first run)
├── requirements.txt        # Python dependencies
├── Procfile                # Deployment entry point (Railway/Render/Heroku)
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
- A Zoho Mail account with SMTP access enabled (for auto-reply and appointment emails)

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

Create a `.env` file in the project root for **local development only** (production uses Render environment variables):

```env
GEMINI_API_KEY=your_gemini_api_key_here

SMTP_HOST=smtp.zoho.com
SMTP_PORT=587
SMTP_USERNAME=team@yourdomain.com
SMTP_PASSWORD=your_smtp_app_password
SMTP_FROM_EMAIL=team@yourdomain.com
SMTP_FROM_NAME=Fantom AI
SMTP_USE_TLS=true
```

The server never creates or modifies `.env` at runtime. Configuration is read from environment variables at startup.

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
Receives a new lead, runs AI analysis, saves it, and emails the AI-drafted reply to the lead via SMTP.

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
      "summary": "• Client is exploring AI automation for their sales pipeline\n• Wants to understand FantomAI's service offerings\n• Likely evaluating multiple vendors",
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
Returns current configuration status (presence only — never returns keys, URLs, or secrets).

```json
{
  "configured": true,
  "email_configured": true
}
```

### `POST /api/config`
**Disabled for security.** Configuration cannot be changed through an HTTP endpoint. Update `GEMINI_API_KEY`, `SMTP_*`, and other settings via environment variables instead. This endpoint always returns `403 Forbidden`.

---

## 📬 SMTP Email Delivery

All transactional email is sent directly from the FastAPI backend via SMTP (`smtplib`) — no n8n, no external workflow. This covers:

- **Lead auto-replies** — when a lead submits the web form, the AI-generated personalized draft is emailed to the lead (subject: *FantomAI | Lead Intake Proposal & Next Steps*)
- **Appointment confirmations** — when a visitor books a Genesis Session, a confirmation email is sent to them (subject: *FantomAI | Genesis Session Confirmation*)
- **2FA login codes** — sent to the admin's email on dashboard login

Emails are delivered as HTML with a plain-text fallback, sent from `SMTP_FROM_NAME <SMTP_FROM_EMAIL>`, and failures are logged server-side without exposing raw SMTP errors to users.

---

## 📊 Admin Dashboard

The dashboard (served at `/`) gives a full CRM-style view of all incoming leads:

- **Stats cards** — total leads, urgency breakdown, category distribution
- **Lead cards** — each showing name, company, source, urgency badge (color-coded), AI category tag, AI summary bullets, and the full draft reply
- **Delete** — remove leads you've handled or marked as spam
- **Config panel** — read-only status indicator for Gemini and SMTP email. Secrets are managed via environment variables only.

---

## 🗂️ Configuration

All configuration is read from environment variables. Nothing is stored in `.env` at runtime.

| Variable | Required | Description |
|----------|----------|-------------|
| `ENVIRONMENT` | Optional | `production` (default) or `development`. Development enables the local JSON fallback and localhost CORS. |
| `SUPABASE_URL` | Production | Your Supabase project URL. |
| `SUPABASE_SERVICE_KEY` | Production | Supabase service-role key (server-side only, never exposed to the browser). |
| `GEMINI_API_KEY` | Recommended | Google Gemini API key. Without it, the server uses a rule-based fallback analyzer. |
| `ADMIN_EMAIL_1` / `ADMIN_PASSWORD_1` | Production | First admin account for the dashboard (hashed with bcrypt in memory). |
| `ADMIN_EMAIL_2` / `ADMIN_PASSWORD_2` | Optional | Second admin account. |
| `SMTP_HOST` | Production | SMTP server host. Use `smtp.zoho.com` for free Zoho Mail plans, `smtppro.zoho.com` for paid plans. |
| `SMTP_PORT` | Optional | SMTP port (default `587`). |
| `SMTP_USERNAME` | Production | SMTP username (full email address, e.g. `team@fantomai.site`). |
| `SMTP_PASSWORD` | Production | SMTP password or app-specific password. |
| `SMTP_FROM_EMAIL` | Production | "From" address. Defaults to `SMTP_USERNAME` if not set. |
| `SMTP_FROM_NAME` | Optional | "From" display name (default `Fantom AI`). |
| `SMTP_USE_TLS` | Optional | `true` for STARTTLS (default), `false` for implicit SSL. |
| `SMTP_TIMEOUT` | Optional | SMTP connection timeout in seconds (default `20`). |
| `CALENDAR_URL` | Optional | Cal.com (or other) booking link injected into AI-generated email replies in place of a calendar placeholder. |

Never commit real values for these variables. Set them in the Render dashboard under **Environment**.

Never commit real values for these variables. Set them in the Render dashboard under **Environment**.

---

## ☁️ Deployment

Deployment target: **Render Web Service**.

1. Create a Supabase project and run `schema.sql` in the **Supabase SQL Editor**.
2. Deploy this repo to Render as a Web Service with:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
3. Add all configuration variables from the table above in Render **Environment**.
4. Point the custom domain (`https://fantomai.site`) at the Render service.

The Procfile starts the server with:
```
web: uvicorn app:app --host 0.0.0.0 --port $PORT
```

> ⚠️ **Migrating existing data:** the app previously stored leads/appointments in `leads.json` and `appointments.json`. Run `python migrate_json_to_supabase.py` (with `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` set) to copy that data into Supabase. It is idempotent and will not delete the JSON files.

> ⚠️ **Sessions:** authentication sessions are stored in memory on a single instance. This works for a single Render Web Service but is **not** suitable for multi-instance scaling — restarting the service logs all users out.

> ⚠️ **2FA delivery:** two-factor codes are sent via SMTP and are **never** logged in production. If SMTP is not configured (`SMTP_HOST`/`SMTP_USERNAME`/`SMTP_PASSWORD`/`SMTP_FROM_EMAIL`), the login endpoint returns an error and no code is delivered — the dashboard cannot be accessed until SMTP is set up. In development mode the code is printed to the server console.

---

## 🛣 Future Roadmap

This project is intentionally lean for a solo startup context. As FantomAI scales, here are the natural evolution points:

### 🔐 Security Hardening
- Move sessions from in-memory storage to a persistent store (e.g., Redis) to support multi-instance scaling
- Add rate limiting on `/webhook` to prevent spam submissions

### 🧠 AI Enhancements
- **Lead scoring** — a numerical score (0–100) in addition to urgency tier, based on company size signals, message specificity, and intent keywords
- **Duplicate detection** — flag leads from the same email address
- **Follow-up scheduling** — if a High urgency lead hasn't been responded to in 2 hours, trigger a Slack/email alert

### 📧 Email Improvements
- **Human-in-the-loop mode** — instead of auto-sending, send the draft to your own inbox first for one-click approval
- **Multi-channel support** — route Partnership leads to a different email thread, Technical Support to a helpdesk ticket (Freshdesk/Linear)

### 📊 Dashboard Enhancements
- Filterable/sortable lead table (by date, urgency, category)
- Export to CSV
- Lead status tracking (New → Contacted → Qualified → Closed)

---

## 🤝 Contributing

This is an internal FantomAI project, but contributions, suggestions, and issue reports are welcome.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m 'Add: your feature description'`
4. Push and open a Pull Request

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

Built with ⚡ by **[Moaz Kashif](https://github.com/MoazKashif)** for **FantomAI**

*If this saved you time, consider giving the repo a ⭐*

</div>
