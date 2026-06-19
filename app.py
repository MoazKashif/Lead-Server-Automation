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
import urllib.request
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv, set_key

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

# Pydantic models for request validation
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
        "ai_analysis": analysis
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

# Mount Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve public website (lead capture form)
@app.get("/website")
async def serve_website():
    return FileResponse("static/landing.html")

# Serve admin dashboard
@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    # Listen on all interfaces, port 8000
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
