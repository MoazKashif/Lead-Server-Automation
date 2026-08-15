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
import secrets
import socket
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
import sys
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import bcrypt

# Environment mode. Production is the default.
# Load .env for local development only. load_dotenv never overrides existing
# environment variables, so Render environment variables remain the source of
# truth in production.
ENV_FILE = ".env"
if os.path.exists(ENV_FILE):
    load_dotenv(ENV_FILE)

IS_PRODUCTION = os.getenv("ENVIRONMENT", "production").lower() == "production"

from database import init_db
import repository
import repository_appointments
import email_service

app = FastAPI(title="Lead Automation & AI Receptionist Webhook Server")


@app.on_event("startup")
async def startup():
    if not ADMIN_ACCOUNTS:
        if IS_PRODUCTION:
            raise RuntimeError(
                "[SECURITY] FATAL: No admin accounts configured. "
                "Set ADMIN_EMAIL_1/ADMIN_PASSWORD_1 environment variables. Refusing to start."
            )
        print("[SECURITY] WARNING: No admin accounts configured. Login will not work.", file=sys.stderr)
    if IS_PRODUCTION and not email_service.is_email_configured():
        print(
            "[SECURITY] WARNING: Resend email is not configured in production. "
            "Two-factor login codes cannot be delivered. Set RESEND_API_KEY and RESEND_FROM_EMAIL.",
            file=sys.stderr,
        )
    init_db()


# Enable CORS for frontend flexibility
_allowed_origins = ["https://fantomai.site", "https://www.fantomai.site"]
if not IS_PRODUCTION:
    _allowed_origins.extend(["http://localhost:8000", "http://127.0.0.1:8000"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# AUTHENTICATION SYSTEM
# ============================================================

# Allowlisted admin accounts with bcrypt-hashed passwords
def _load_admin_accounts() -> dict:
    accounts = {}
    i = 1
    while True:
        email = os.getenv(f"ADMIN_EMAIL_{i}")
        password = os.getenv(f"ADMIN_PASSWORD_{i}")
        if not email or not password:
            break
        accounts[email.strip().lower()] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        i += 1
    return accounts

ADMIN_ACCOUNTS = _load_admin_accounts()
if not ADMIN_ACCOUNTS:
    print("[SECURITY] FATAL: No admin accounts configured. Set ADMIN_EMAIL_1/ADMIN_PASSWORD_1 environment variables.", file=sys.stderr)

# In-memory session store: { session_token: { email, created_at } }
active_sessions = {}

# In-memory 2FA store: { email: { code, created_at, attempts } }
pending_2fa = {}

# In-memory login attempt tracker: { email_or_ip: { count, locked_until } }
login_attempts = {}

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60  # 15 minutes
CODE_EXPIRY_SECONDS = 5 * 60  # 2FA codes expire after 5 minutes
SESSION_COOKIE_NAME = "fai_session"

# Public paths that don't require authentication
PUBLIC_PATHS = {
    "/", "/login", "/website", "/webhook", "/docs", "/openapi.json", "/redoc", "/health",
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


def send_2fa_email(email: str, code: str) -> bool:
    """
    Send the 2FA code to the user's email via the Resend API.
    In development, prints the code to the console for testing.
    Returns True if the code was delivered (or printed in dev), False otherwise.
    """
    html_body = f"""
    <div style="font-family: 'Segoe UI', sans-serif; max-width: 480px; margin: auto; padding: 24px; background: #0a0914; color: #f3f4f6; border-radius: 12px;">
        <h2 style="text-align: center; margin-bottom: 8px;">Fantom<span style="color: #6366f1;">AI</span></h2>
        <p style="text-align: center; color: #9ca3af; font-size: 14px;">Admin Dashboard Two-Factor Verification</p>
        <div style="text-align: center; margin: 32px 0;">
            <span style="font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #6366f1;">{code}</span>
        </div>
        <p style="text-align: center; color: #9ca3af; font-size: 13px;">This code expires in 5 minutes. If you didn't request this, ignore this email.</p>
    </div>
    """

    try:
        email_service.send_email(
            to=email,
            subject=f"FantomAI Admin Login – Your 2FA Code: {code}",
            html_body=html_body,
        )
        print(f"[2FA] Email sent to {email}")
        return True
    except email_service.EmailConfigError as e:
        if IS_PRODUCTION:
            print(f"[2FA] ERROR: {e}", file=sys.stderr)
            return False
        print(f"\n{'='*50}")
        print(f"  2FA CODE for {email}: {code}")
        print(f"{'='*50}\n")
        return True
    except email_service.EmailDeliveryError as e:
        print(f"[2FA] Email send failed ({e}).")
        if IS_PRODUCTION:
            print(
                "[2FA] ERROR: Resend delivery failed in production and the 2FA code "
                "cannot be delivered. Check RESEND_API_KEY/RESEND_FROM_EMAIL.",
                file=sys.stderr,
            )
        else:
            print(f"\n{'='*50}")
            print(f"  2FA CODE for {email}: {code}")
            print(f"{'='*50}\n")
        return False


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

    if not IS_PRODUCTION:
        # Development: print the code to the console (no Resend API required)
        pending_2fa[email] = {
            "code": code,
            "created_at": time.time(),
            "attempts": 0,
        }
        send_2fa_email(email, code)
        return {"status": "2fa_required", "message": "Verification code sent to your email."}

    # Production: the code must be delivered via the Resend API.
    if not email_service.is_email_configured():
        raise HTTPException(
            status_code=503,
            detail="Two-factor email cannot be sent because Resend is not configured. "
                   "Contact your administrator to configure RESEND_API_KEY and RESEND_FROM_EMAIL.",
        )

    delivered = send_2fa_email(email, code)
    if not delivered:
        raise HTTPException(
            status_code=503,
            detail="Failed to deliver the two-factor verification code. Please try again or contact your administrator.",
        )

    pending_2fa[email] = {
        "code": code,
        "created_at": time.time(),
        "attempts": 0,
    }
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
    is_production = IS_PRODUCTION
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=is_production,
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

    # Allow public appointment booking from landing page
    if request.method == "POST" and path == "/api/appointments":
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


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


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

class AppointmentRequest(BaseModel):
    name: str
    email: str
    appointment_date: str
    time_window: str
    automation_goal: str

# Pydantic schema for structured Gemini Output
class LeadAnalysis(BaseModel):
    urgency: str = Field(description="Must be 'High', 'Medium', or 'Low'")
    urgency_rationale: str = Field(description="Short reason why this urgency level was selected")
    category: str = Field(description="One of: 'Inquiry', 'Technical Support', 'Partnership', 'Job Application', 'Spam'")
    summary: str = Field(description="Concise 2-3 bullet point summary of the customer's request")
    draft_reply: str = Field(description="A highly personalized, polite draft email response addressing the user's specific request or questions")

# Call Gemini for Lead analysis (retries + model fallbacks on 503)
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

def build_fallback_analysis(lead: LeadRequest, error: str = "") -> dict:
    """Personalized fallback when Gemini is unavailable."""
    mock = get_mock_analysis(lead)
    company = lead.company or "your company"
    msg_preview = lead.message[:200] + ("..." if len(lead.message) > 200 else "")
    mock["draft_reply"] = (
        f"<p>Dear {lead.name},</p>"
        f"<p>Thank you for reaching out to <strong>FantomAI</strong>. "
        f"We received your inquiry from {company} regarding:</p>"
        f"<p><em>\"{msg_preview}\"</em></p>"
        f"<p>Our team specializes in AI automation — including email workflows, "
        f"lead intake, and client confirmation systems like the one you described. "
        f"We'd love to learn more about your requirements and timeline.</p>"
        f"<p>We'll review your message and follow up within one business day "
        f"to discuss next steps and schedule a brief discovery call.</p>"
        f"<p>Best regards,<br><strong>The FantomAI Team</strong></p>"
    )
    if error:
        mock["urgency_rationale"] = f"Gemini temporarily unavailable; used smart fallback. ({error[:120]})"
        mock["ai_status"] = "Fallback Evaluated (Gemini unavailable)"
    return mock

def analyze_lead_with_ai(lead: LeadRequest, api_key: str) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    calendar_url = os.getenv("CALENDAR_URL", "").strip()

    prompt = f"""
    You are an AI Sales Assistant working for FantomAI — an AI Automation Agency. 
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
    - Sign off as "The FantomAI Team" — never use placeholders like [Your Name] or [Agency Name].
    - Do NOT include a subject line in the body.
    - If you invite the lead to book a call, embed this booking link directly (as an anchor tag or plain URL) instead of using a placeholder like [link to calendar]: {calendar_url}
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

# Helper to email the AI-drafted reply to the lead directly via the Resend API
def send_lead_reply_email(lead_entry: dict):
    """Background task: send the AI-drafted reply to the lead via the Resend API."""
    email = lead_entry.get("email", "")
    if not email:
        print("[EMAIL] Lead reply skipped: no recipient email.")
        return
    analysis = lead_entry.get("ai_analysis", {})
    draft = analysis.get("draft_reply", "")
    if not draft:
        print(f"[EMAIL] Lead reply skipped for {email}: no draft reply generated.")
        return
    try:
        email_service.send_email(
            to=email,
            subject="FantomAI | Lead Intake Proposal & Next Steps",
            html_body=draft,
        )
        print(f"[EMAIL] Lead reply sent to {email}")
    except email_service.EmailError as e:
        print(f"[EMAIL] Failed to send lead reply to {email}: {e}")

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
        "timestamp": datetime.datetime.now(datetime.timezone.utc),
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone,
        "company": lead.company,
        "message": lead.message,
        "source": lead.source,
        "ai_analysis": analysis,
        "read": False
    }
    
    created = repository.create(lead_entry)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to persist lead to the database. Please try again.")
    ts = lead_entry["timestamp"]
    lead_entry["timestamp"] = ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts.microsecond:06d}Z"
    
    # Email the AI-drafted reply to the lead via the Resend API in the background
    background_tasks.add_task(send_lead_reply_email, lead_entry)
    
    return {"status": "success", "lead": lead_entry}

# API Endpoint to list leads
@app.get("/api/leads")
async def get_leads():
    return repository.get_all()

# API Endpoint to fetch dashboard stats
@app.get("/api/stats")
async def get_stats():
    leads = repository.get_all()
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
    return {
        "configured": has_key,
        "email_configured": email_service.is_email_configured()
    }

# Endpoint to save config (API key and email settings)
@app.post("/api/config")
async def save_config(config: dict):
    raise HTTPException(
        status_code=403,
        detail="Configuration changes are not allowed via API. Use environment variables."
    )

# Delete a lead
@app.delete("/api/leads/{lead_id}")
async def delete_lead(lead_id: str):
    if not repository.delete(lead_id):
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"status": "success", "message": "Lead deleted"}

# Mark a lead as read
@app.post("/api/leads/{lead_id}/read")
async def mark_lead_read(lead_id: str):
    if not repository.mark_read(lead_id):
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"status": "success", "message": "Lead marked as read"}

# ============================================================
# Appointment Endpoints
# ============================================================

# Helper to email appointment confirmation to the booker via the Resend API
def send_appointment_confirmation_email(appointment: dict):
    """Background task: send a booking confirmation to the requester via the Resend API."""
    email = appointment.get("email", "")
    if not email:
        print("[EMAIL] Appointment confirmation skipped: no recipient email.")
        return
    name = appointment.get("name", "there")
    date = appointment.get("appointment_date", "")
    time_window = appointment.get("time_window", "")
    goal = appointment.get("automation_goal", "")

    html_body = f"""
    <div style="font-family: 'Segoe UI', sans-serif; max-width: 520px; margin: auto; padding: 24px; background: #0a0914; color: #f3f4f6; border-radius: 12px;">
        <h2 style="text-align: center; margin-bottom: 8px;">Fantom<span style="color: #6366f1;">AI</span></h2>
        <p style="text-align: center; color: #9ca3af; font-size: 14px;">Genesis Session Request Confirmed</p>
        <p>Hi {name},</p>
        <p>Thank you for booking a <strong>Genesis Session</strong> with the FantomAI team. Here are your details:</p>
        <div style="background: rgba(99, 102, 241, 0.12); border: 1px solid rgba(99, 102, 241, 0.35); border-radius: 10px; padding: 16px; margin: 16px 0;">
            <p style="margin: 4px 0;"><strong>Date:</strong> {date}</p>
            <p style="margin: 4px 0;"><strong>Time window:</strong> {time_window}</p>
            <p style="margin: 4px 0;"><strong>Automation goal:</strong> {goal}</p>
        </div>
        <p>Our team will contact you shortly to confirm the session and discuss your automation goals.</p>
        <p style="color: #9ca3af; font-size: 13px;">Best regards,<br><strong>The FantomAI Team</strong></p>
    </div>
    """

    try:
        email_service.send_email(
            to=email,
            subject="FantomAI | Genesis Session Confirmation",
            html_body=html_body,
        )
        print(f"[EMAIL] Appointment confirmation sent to {email}")
    except email_service.EmailError as e:
        print(f"[EMAIL] Failed to send appointment confirmation to {email}: {e}")


@app.post("/api/appointments")
async def create_appointment(body: AppointmentRequest, background_tasks: BackgroundTasks):
    appointment_entry = {
        "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S%f"),
        "name": body.name.strip(),
        "email": body.email.strip().lower(),
        "appointment_date": body.appointment_date.strip(),
        "time_window": body.time_window.strip(),
        "automation_goal": body.automation_goal.strip(),
        "read": False,
    }
    result = repository_appointments.create(appointment_entry)
    if result is None:
        from repository_appointments import _validate_appointment
        err = _validate_appointment(appointment_entry)
        raise HTTPException(status_code=400, detail=err or "Invalid appointment data")
    if result == {}:
        raise HTTPException(status_code=500, detail="Failed to persist appointment to the database. Please try again.")

    # Email the confirmation to the booker via the Resend API in the background
    background_tasks.add_task(send_appointment_confirmation_email, result)

    return {"status": "success", "appointment": result}


@app.get("/api/appointments")
async def get_appointments():
    return repository_appointments.get_all()


@app.get("/api/appointments/stats")
async def get_appointment_stats():
    return repository_appointments.get_stats()


@app.delete("/api/appointments/{appointment_id}")
async def delete_appointment(appointment_id: str):
    if not repository_appointments.delete(appointment_id):
        raise HTTPException(status_code=404, detail="Appointment not found")
    return {"status": "success", "message": "Appointment deleted"}


@app.post("/api/appointments/{appointment_id}/read")
async def mark_appointment_read(appointment_id: str):
    if not repository_appointments.mark_read(appointment_id):
        raise HTTPException(status_code=404, detail="Appointment not found")
    return {"status": "success", "message": "Appointment marked as read"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Mount Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve login page
@app.get("/login")
async def serve_login():
    return FileResponse("static/login.html")

# Serve public website (lead capture form)
@app.get("/website")
async def serve_website():
    resp = FileResponse("static/landing.html")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

# Serve admin dashboard (protected by middleware) when authenticated;
# otherwise serve the public landing page (same as /website).
@app.get("/")
async def serve_index(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token and token in active_sessions:
        session = active_sessions[token]
        if time.time() - session["created_at"] < 24 * 60 * 60:
            return FileResponse("static/index.html")
        del active_sessions[token]
    resp = FileResponse("static/landing.html")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

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
