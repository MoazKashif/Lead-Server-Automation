# /// script
# dependencies = [
#   "fastapi",
#   "uvicorn",
#   "google-genai",
#   "python-dotenv",
#   "pydantic"
# ]
# ///

import os
import json
import datetime
import time
import random
import secrets
import smtplib
import socket
import urllib.request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv, set_key
import bcrypt

# Load environment variables from .env
ENV_FILE = ".env"
if not os.path.exists(ENV_FILE):
    with open(ENV_FILE, "w") as f:
        f.write("# Gemini API Configuration\nGEMINI_API_KEY=\n# n8n Webhook Configuration\nN8N_WEBHOOK_URL=\n")

load_dotenv(ENV_FILE)

app = FastAPI(title="Lead Automation & AI Receptionist Webhook Server")

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "leads.json"

# Initialize local database
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump([], f)

# ============================================================
# AUTHENTICATION SYSTEM
# ============================================================

# Allowlisted admin accounts with bcrypt-hashed passwords
ADMIN_ACCOUNTS = {
    "moazkashif96@gmail.com": bcrypt.hashpw(b"Moaz@Fast2027", bcrypt.gensalt()).decode(),
    "umersiddiqui614@gmail.com": bcrypt.hashpw(b"Umer@Umt2027", bcrypt.gensalt()).decode(),
}

# In-memory session store: { session_token: { email, created_at } }
active_sessions = {}

# In-memory 2FA store: { email: { code, created_at, attempts } }
pending_2fa = {}

# In-memory login attempt tracker: { email_or_ip: { count, locked_until } }
login_attempts = {}

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60  # 15 minutes
CODE_EXPIRY_SECONDS = 5 * 60  # 2FA codes expire after 5 minutes
SESSION_COOKIE_NAME = "qai_session"

# Public paths that don't require authentication
PUBLIC_PATHS = {
    "/login", "/website", "/webhook", "/docs", "/openapi.json", "/redoc",
    "/api/auth/login", "/api/auth/verify-2fa", "/api/auth/logout",
}
PUBLIC_PREFIXES = ("/static/",)


def get_attempt_key(email: str, ip: str) -> str:
    """Use email if provided, otherwise fall back to IP."""
    return email if email else ip


def check_lockout(key: str) -> Optional[str]:
    """Returns error message if locked out, None otherwise."""
    info = login_attempts.get(key)
    if not info:
        return None
    if info.get("locked_until"):
        now = time.time()
        if now < info["locked_until"]:
            remaining = int(info["locked_until"] - now)
            mins = remaining // 60
            secs = remaining % 60
            return f"Account locked. Try again in {mins}m {secs}s."
        else:
            # Lockout expired, reset
            login_attempts[key] = {"count": 0, "locked_until": None}
            return None
    return None


def record_failed_attempt(key: str) -> int:
    """Records a failed attempt. Returns remaining attempts."""
    if key not in login_attempts:
        login_attempts[key] = {"count": 0, "locked_until": None}

    login_attempts[key]["count"] += 1
    used = login_attempts[key]["count"]
    remaining = MAX_ATTEMPTS - used

    if remaining <= 0:
        login_attempts[key]["locked_until"] = time.time() + LOCKOUT_SECONDS
        login_attempts[key]["count"] = 0
        return 0

    return remaining


def reset_attempts(key: str):
    """Reset attempts after successful authentication."""
    login_attempts.pop(key, None)


def generate_2fa_code() -> str:
    """Generate a secure random 6-digit code."""
    return f"{secrets.randbelow(900000) + 100000}"


def send_2fa_email(email: str, code: str):
    """
    Send the 2FA code to the user's email via SMTP.
    If SMTP is not configured, falls back to printing to the server console.
    """
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")

    if smtp_host and smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"QuantumAI Admin Login – Your 2FA Code: {code}"
            msg["From"] = smtp_user
            msg["To"] = email

            html_body = f"""
            <div style="font-family: 'Segoe UI', sans-serif; max-width: 480px; margin: auto; padding: 24px; background: #0a0914; color: #f3f4f6; border-radius: 12px;">
                <h2 style="text-align: center; margin-bottom: 8px;">Quantum<span style="color: #6366f1;">AI</span></h2>
                <p style="text-align: center; color: #9ca3af; font-size: 14px;">Admin Dashboard Two-Factor Verification</p>
                <div style="text-align: center; margin: 32px 0;">
                    <span style="font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #6366f1;">{code}</span>
                </div>
                <p style="text-align: center; color: #9ca3af; font-size: 13px;">This code expires in 5 minutes. If you didn't request this, ignore this email.</p>
            </div>
            """
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, email, msg.as_string())

            print(f"[2FA] Email sent to {email}")
        except Exception as e:
            print(f"[2FA] SMTP send failed ({e}). Falling back to console.")
            print(f"\n{'='*50}")
            print(f"  2FA CODE for {email}: {code}")
            print(f"{'='*50}\n")
    else:
        # No SMTP configured — print to console for local dev
        print(f"\n{'='*50}")
        print(f"  2FA CODE for {email}: {code}")
        print(f"{'='*50}\n")


# Auth Pydantic models
class LoginRequest(BaseModel):
    email: str
    password: str

class Verify2FARequest(BaseModel):
    email: str
    code: str


# ---- Auth Endpoints ----

@app.post("/api/auth/login")
async def auth_login(body: LoginRequest, request: Request):
    email = body.email.strip().lower()
    password = body.password.encode()
    ip = request.client.host if request.client else "unknown"
    key = get_attempt_key(email, ip)

    # Check lockout
    lockout_msg = check_lockout(key)
    if lockout_msg:
        raise HTTPException(status_code=429, detail=lockout_msg)

    # Validate email is in allowlist
    stored_hash = ADMIN_ACCOUNTS.get(email)
    if not stored_hash:
        remaining = record_failed_attempt(key)
        if remaining <= 0:
            raise HTTPException(status_code=429, detail="Too many failed attempts. Account locked for 15 minutes.")
        raise HTTPException(status_code=401, detail=f"Invalid credentials. {remaining} attempts remaining.")

    # Validate password
    if not bcrypt.checkpw(password, stored_hash.encode()):
        remaining = record_failed_attempt(key)
        if remaining <= 0:
            raise HTTPException(status_code=429, detail="Too many failed attempts. Account locked for 15 minutes.")
        raise HTTPException(status_code=401, detail=f"Invalid credentials. {remaining} attempts remaining.")

    # Password correct — generate 2FA code and send it
    code = generate_2fa_code()
    pending_2fa[email] = {
        "code": code,
        "created_at": time.time(),
        "attempts": 0,
    }

    send_2fa_email(email, code)

    return {"status": "2fa_required", "message": "Verification code sent to your email."}


@app.post("/api/auth/verify-2fa")
async def auth_verify_2fa(body: Verify2FARequest, request: Request):
    email = body.email.strip().lower()
    code = body.code.strip()
    ip = request.client.host if request.client else "unknown"
    key = get_attempt_key(email, ip)

    # Check lockout
    lockout_msg = check_lockout(key)
    if lockout_msg:
        raise HTTPException(status_code=429, detail=lockout_msg)

    entry = pending_2fa.get(email)
    if not entry:
        raise HTTPException(status_code=400, detail="No pending 2FA code found. Please login again.")

    # Check code expiry
    if time.time() - entry["created_at"] > CODE_EXPIRY_SECONDS:
        pending_2fa.pop(email, None)
        raise HTTPException(status_code=400, detail="2FA code has expired. Please login again.")

    # Check code
    if entry["code"] != code:
        entry["attempts"] += 1
        remaining = record_failed_attempt(key)
        if remaining <= 0:
            pending_2fa.pop(email, None)
            raise HTTPException(status_code=429, detail="Too many failed attempts. Account locked for 15 minutes.")
        raise HTTPException(status_code=401, detail=f"Invalid 2FA code. {remaining} attempts remaining.")

    # Success! Create session
    pending_2fa.pop(email, None)
    reset_attempts(key)

    session_token = secrets.token_urlsafe(48)
    active_sessions[session_token] = {
        "email": email,
        "created_at": time.time(),
    }

    response = JSONResponse({"status": "success", "message": "Authentication successful."})
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite="lax",
        max_age=24 * 60 * 60,  # 24 hours
        path="/",
    )
    return response


@app.post("/api/auth/logout")
async def auth_logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token and token in active_sessions:
        del active_sessions[token]

    response = JSONResponse({"status": "success", "message": "Logged out."})
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return response


# ---- Authentication Middleware ----

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # Allow public paths
    if path in PUBLIC_PATHS:
        return await call_next(request)

    # Allow paths with public prefixes
    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return await call_next(request)

    # For protected routes, check session cookie
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token and token in active_sessions:
        session = active_sessions[token]
        # Optional: check session expiry (24h)
        if time.time() - session["created_at"] < 24 * 60 * 60:
            return await call_next(request)
        else:
            # Session expired
            del active_sessions[token]

    # Not authenticated — redirect HTML pages, return 401 for API
    if path.startswith("/api/"):
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required. Please login."},
        )

    return RedirectResponse(url="/login", status_code=302)


# ============================================================
# Pydantic models for request validation
# ============================================================
class LeadRequest(BaseModel):
    name: str
    email: str
    phone: str = ""
    company: str = ""
    message: str
    source: str = "Web Form"

# Pydantic schema for structured Gemini Output
class LeadAnalysis(BaseModel):
    urgency: str = Field(description="Must be 'High', 'Medium', or 'Low'")
    urgency_rationale: str = Field(description="Short reason why this urgency level was selected")
    category: str = Field(description="One of: 'Inquiry', 'Technical Support', 'Partnership', 'Job Application', 'Spam'")
    summary: str = Field(description="Concise 2-3 bullet point summary of the customer's request")
    draft_reply: str = Field(description="A highly personalized, polite draft email response addressing the user's specific request or questions")

# Database Helper Functions
def load_leads() -> List[dict]:
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_leads(leads: List[dict]):
    with open(DB_FILE, "w") as f:
        json.dump(leads, f, indent=4)

# Call Gemini for Lead analysis (retries + model fallbacks on 503)
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

def build_fallback_analysis(lead: LeadRequest, error: str = "") -> dict:
    """Personalized fallback when Gemini is unavailable."""
    mock = get_mock_analysis(lead)
    company = lead.company or "your company"
    msg_preview = lead.message[:200] + ("..." if len(lead.message) > 200 else "")
    mock["draft_reply"] = (
        f"<p>Dear {lead.name},</p>"
        f"<p>Thank you for reaching out to <strong>QuantumAI</strong>. "
        f"We received your inquiry from {company} regarding:</p>"
        f"<p><em>\"{msg_preview}\"</em></p>"
        f"<p>Our team specializes in AI automation — including email workflows, "
        f"lead intake, and client confirmation systems like the one you described. "
        f"We'd love to learn more about your requirements and timeline.</p>"
        f"<p>We'll review your message and follow up within one business day "
        f"to discuss next steps and schedule a brief discovery call.</p>"
        f"<p>Best regards,<br><strong>The QuantumAI Team</strong></p>"
    )
    if error:
        mock["urgency_rationale"] = f"Gemini temporarily unavailable; used smart fallback. ({error[:120]})"
        mock["ai_status"] = "Fallback Evaluated (Gemini unavailable)"
    return mock

def analyze_lead_with_ai(lead: LeadRequest, api_key: str) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    prompt = f"""
    You are an AI Sales Assistant working for QuantumAI — an AI Automation Agency. 
    Analyze the following incoming lead submission and classify/summarize it.
    
    Lead Info:
    - Name: {lead.name}
    - Company: {lead.company}
    - Email: {lead.email}
    - Phone: {lead.phone}
    - Source: {lead.source}
    
    Message:
    {lead.message}
    
    IMPORTANT for the draft_reply field:
    - Write a highly personalized, professional email reply addressing the lead's specific request.
    - Format the reply as clean HTML using <p>, <br>, and <strong> tags for readability.
    - Sign off as "The QuantumAI Team" — never use placeholders like [Your Name] or [Agency Name].
    - Do NOT include a subject line in the body.
    """

    last_error = ""
    for model in GEMINI_MODELS:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=LeadAnalysis,
                        temperature=0.2,
                    ),
                )
                result = json.loads(response.text)
                result["ai_status"] = f"AI Evaluated ({model})"
                return result
            except Exception as e:
                last_error = str(e)
                is_rate_limit = "503" in last_error or "UNAVAILABLE" in last_error or "429" in last_error
                if is_rate_limit and attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                if is_rate_limit:
                    break  # try next model
                print(f"Error calling Gemini API ({model}): {e}")
                return build_fallback_analysis(lead, last_error)

    print(f"All Gemini models failed: {last_error}")
    return build_fallback_analysis(lead, last_error)

# Get simulated analysis if no key is present
def get_mock_analysis(lead: LeadRequest) -> dict:
    # A simple deterministic rule engine for mock data
    msg_lower = lead.message.lower()
    if any(x in msg_lower for x in ["urgent", "asap", "call me", "right away", "critical"]):
        urgency = "High"
        rationale = "Customer used urgency keywords (ASAP/Urgent/Call me)."
    elif any(x in msg_lower for x in ["pricing", "cost", "quote", "how much"]):
        urgency = "Medium"
        rationale = "Pricing questions are important, but not immediately critical."
    else:
        urgency = "Low"
        rationale = "Standard informational query."

    if any(x in msg_lower for x in ["partnership", "collaborate", "partner"]):
        category = "Partnership"
    elif any(x in msg_lower for x in ["seo", "crypto", "buy followers", "wealth"]):
        category = "Spam"
    elif any(x in msg_lower for x in ["bug", "error", "broken", "help", "support"]):
        category = "Technical Support"
    else:
        category = "Inquiry"

    summary = f"Client {lead.name} is inquiring about: '{lead.message[:60]}...'"
    draft = f"Hi {lead.name},\n\nThank you for reaching out from {lead.company or 'your company'}. We received your inquiry about our services and would love to chat further. Let's schedule a call.\n\nBest,\nThe Sales Team"

    return {
        "urgency": urgency,
        "urgency_rationale": rationale + " (Mocked - Gemini API key not configured)",
        "category": category,
        "summary": summary,
        "draft_reply": draft
    }

# Helper to forward analyzed leads to n8n in the background
def build_n8n_payload(lead_entry: dict) -> dict:
    """Flat email fields so n8n Gmail node can use simple expressions."""
    analysis = lead_entry.get("ai_analysis", {})
    draft = analysis.get("draft_reply", "")
    return {
        **lead_entry,
        "to_email": lead_entry.get("email", ""),
        "email_subject": "QuantumAI | Lead Intake Proposal & Next Steps",
        "email_html": draft,
    }

def forward_to_n8n_background(payload: dict):
    n8n_url = os.getenv("N8N_WEBHOOK_URL")
    if not n8n_url or not n8n_url.strip():
        print("n8n forwarding skipped: N8N_WEBHOOK_URL is not configured.")
        return
    
    try:
        req = urllib.request.Request(
            n8n_url.strip(),
            data=json.dumps(build_n8n_payload(payload)).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = response.read().decode('utf-8')
            print(f"n8n Webhook triggered successfully. Status: {response.status}, Response: {res_data}")
    except Exception as e:
        print(f"Error calling n8n webhook: {e}")

# Webhook Endpoint (Receives leads from forms/bots)
@app.post("/webhook")
async def receive_webhook(lead: LeadRequest, background_tasks: BackgroundTasks):
    api_key = os.getenv("GEMINI_API_KEY")
    
    # Process with Gemini if key exists, else use mock analyzer
    if api_key and api_key.strip():
        analysis = analyze_lead_with_ai(lead, api_key)
        if "ai_status" not in analysis:
            analysis["ai_status"] = "AI Evaluated"
    else:
        analysis = get_mock_analysis(lead)
        analysis["ai_status"] = "Mock Evaluated (No API Key)"
        
    lead_entry = {
        "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S%f"),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone,
        "company": lead.company,
        "message": lead.message,
        "source": lead.source,
        "ai_analysis": analysis,
        "read": False
    }
    
    leads = load_leads()
    leads.insert(0, lead_entry) # Insert at the top
    save_leads(leads)
    
    # Forward to n8n in background task
    background_tasks.add_task(forward_to_n8n_background, lead_entry)
    
    return {"status": "success", "lead": lead_entry}

# API Endpoint to list leads
@app.get("/api/leads")
async def get_leads():
    return load_leads()

# API Endpoint to fetch dashboard stats
@app.get("/api/stats")
async def get_stats():
    leads = load_leads()
    total = len(leads)
    
    urgency_counts = {"High": 0, "Medium": 0, "Low": 0}
    category_counts = {}
    source_counts = {}
    
    for lead in leads:
        analysis = lead.get("ai_analysis", {})
        urg = analysis.get("urgency", "Low")
        urgency_counts[urg] = urgency_counts.get(urg, 0) + 1
        
        cat = analysis.get("category", "Inquiry")
        category_counts[cat] = category_counts.get(cat, 0) + 1
        
        src = lead.get("source", "Web Form")
        source_counts[src] = source_counts.get(src, 0) + 1
        
    return {
        "total_leads": total,
        "urgency": urgency_counts,
        "category": category_counts,
        "source": source_counts
    }

# Endpoint to get current config status
@app.get("/api/config")
async def get_config():
    api_key = os.getenv("GEMINI_API_KEY")
    has_key = api_key is not None and len(api_key.strip()) > 0
    n8n_url = os.getenv("N8N_WEBHOOK_URL", "")
    return {
        "configured": has_key,
        "n8n_configured": len(n8n_url.strip()) > 0,
        "n8n_url": n8n_url
    }

# Endpoint to save config (API key and optional n8n URL)
@app.post("/api/config")
async def save_config(config: dict):
    new_key = config.get("api_key", "").strip()
    n8n_url = config.get("n8n_url", "").strip()
    
    try:
        if new_key:
            set_key(ENV_FILE, "GEMINI_API_KEY", new_key)
            os.environ["GEMINI_API_KEY"] = new_key
        
        # Save n8n webhook URL
        set_key(ENV_FILE, "N8N_WEBHOOK_URL", n8n_url)
        os.environ["N8N_WEBHOOK_URL"] = n8n_url
        
        return {"status": "success", "message": "Configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update env file: {str(e)}")

# Delete a lead
@app.delete("/api/leads/{lead_id}")
async def delete_lead(lead_id: str):
    leads = load_leads()
    new_leads = [l for l in leads if l.get("id") != lead_id]
    if len(leads) == len(new_leads):
        raise HTTPException(status_code=404, detail="Lead not found")
    save_leads(new_leads)
    return {"status": "success", "message": "Lead deleted"}

# Mark a lead as read
@app.post("/api/leads/{lead_id}/read")
async def mark_lead_read(lead_id: str):
    leads = load_leads()
    updated = False
    for lead in leads:
        if lead.get("id") == lead_id:
            if lead.get("read") != True:
                lead["read"] = True
                updated = True
            break
    if updated:
        save_leads(leads)
    return {"status": "success", "message": "Lead marked as read"}

# Mount Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve login page
@app.get("/login")
async def serve_login():
    return FileResponse("static/login.html")

# Serve public website (lead capture form)
@app.get("/website")
async def serve_website():
    return FileResponse("static/landing.html")

# Serve admin dashboard (protected by middleware)
@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

def find_available_port(start_port: int = 8000) -> int:
    """Return the first available port starting from start_port."""
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", port))
                return port
            except OSError:
                port += 1


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", find_available_port()))
    print(f"Starting server on port {port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
