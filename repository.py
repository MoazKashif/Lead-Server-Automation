"""Database repository layer for lead operations with a JSON fallback."""

import json
from pathlib import Path
from typing import List
from database import supabase

STORAGE_FILE = Path(__file__).with_name("leads.json")


def _normalize_lead(data: dict) -> dict:
    normalized = dict(data)
    if "timestamp" in normalized and hasattr(normalized["timestamp"], "isoformat"):
        normalized["timestamp"] = normalized["timestamp"].isoformat()
    normalized.setdefault("read", False)
    normalized.setdefault("ai_analysis", {})
    return normalized


def _load_json_leads() -> List[dict]:
    if not STORAGE_FILE.exists():
        return []
    try:
        with STORAGE_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, list):
        return [_normalize_lead(item) for item in data]
    return []


def _save_json_leads(leads: List[dict]) -> None:
    with STORAGE_FILE.open("w", encoding="utf-8") as handle:
        json.dump(leads, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _append_json_lead(lead: dict) -> None:
    leads = _load_json_leads()
    if not any(item.get("id") == lead.get("id") for item in leads):
        leads.append(_normalize_lead(lead))
    _save_json_leads(leads)


def get_all() -> List[dict]:
    """Fetch all leads ordered by timestamp descending (newest first)."""
    if not supabase:
        return _load_json_leads()
    try:
        response = supabase.table("leads").select("*").order("timestamp", desc=True).execute()
        return [_normalize_lead(item) for item in response.data]
    except Exception as exc:
        print(f"[repo] Database unavailable, using JSON fallback: {exc}")
        return _load_json_leads()


def create(data: dict) -> dict:
    """Create a new lead and return it as a dict."""
    lead_data = _normalize_lead(data)
    if not supabase:
        _append_json_lead(lead_data)
        return lead_data
    try:
        response = supabase.table("leads").insert(lead_data).execute()
        created = response.data[0] if response.data else lead_data
        _append_json_lead(created)
        return _normalize_lead(created)
    except Exception as exc:
        print(f"[repo] Database unavailable, storing lead in JSON fallback: {exc}")
        _append_json_lead(lead_data)
        return lead_data


def delete(lead_id: str) -> bool:
    """Delete a lead by ID. Returns True if deleted, False if not found."""
    if not supabase:
        leads = _load_json_leads()
        updated = [lead for lead in leads if lead.get("id") != lead_id]
        if len(updated) == len(leads):
            return False
        _save_json_leads(updated)
        return True
    try:
        response = supabase.table("leads").delete().eq("id", lead_id).execute()
        if response.data and len(response.data) > 0:
            return True
        return False
    except Exception as exc:
        print(f"[repo] Database unavailable, deleting from JSON fallback: {exc}")
        leads = _load_json_leads()
        updated = [lead for lead in leads if lead.get("id") != lead_id]
        if len(updated) == len(leads):
            return False
        _save_json_leads(updated)
        return True


def mark_read(lead_id: str) -> bool:
    """Mark a lead as read. Returns True if updated, False if not found."""
    if not supabase:
        leads = _load_json_leads()
        for lead in leads:
            if lead.get("id") == lead_id:
                lead["read"] = True
                _save_json_leads(leads)
                return True
        return False
    try:
        response = supabase.table("leads").update({"read": True}).eq("id", lead_id).execute()
        if response.data and len(response.data) > 0:
            return True
        return False
    except Exception as exc:
        print(f"[repo] Database unavailable, updating JSON fallback: {exc}")
        leads = _load_json_leads()
        for lead in leads:
            if lead.get("id") == lead_id:
                lead["read"] = True
                _save_json_leads(leads)
                return True
        return False
