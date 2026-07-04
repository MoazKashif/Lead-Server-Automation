"""Database repository layer for appointment operations with a JSON fallback."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from database import supabase

STORAGE_FILE = Path(__file__).with_name("appointments.json")

TIME_WINDOWS = [
    "09:00 AM - 12:00 PM",
    "12:00 PM - 03:00 PM",
    "03:00 PM - 06:00 PM",
    "06:00 PM - 09:00 PM",
]


def _normalize_appointment(data: dict) -> dict:
    normalized = dict(data)
    normalized.setdefault("read", False)
    return normalized


def _validate_appointment(data: dict) -> Optional[str]:
    if not data.get("name") or not data["name"].strip():
        return "Name is required"
    if not data.get("email") or not data["email"].strip():
        return "Email is required"
    if not re.match(r"[^@]+@[^@]+\.[^@]+", data["email"].strip()):
        return "Invalid email format"
    if not data.get("appointment_date"):
        return "Appointment date is required"
    try:
        datetime.strptime(data["appointment_date"], "%Y-%m-%d")
    except ValueError:
        return "Appointment date must be in YYYY-MM-DD format"
    if not data.get("time_window") or data["time_window"] not in TIME_WINDOWS:
        return f"Time window must be one of: {', '.join(TIME_WINDOWS)}"
    if not data.get("automation_goal") or not data["automation_goal"].strip():
        return "Automation goal is required"
    return None


def _load_json_appointments() -> List[dict]:
    if not STORAGE_FILE.exists():
        return []
    try:
        with STORAGE_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, list):
        return [_normalize_appointment(item) for item in data]
    return []


def _save_json_appointments(appointments: List[dict]) -> None:
    with STORAGE_FILE.open("w", encoding="utf-8") as handle:
        json.dump(appointments, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _append_json_appointment(appointment: dict) -> None:
    appointments = _load_json_appointments()
    if not any(item.get("id") == appointment.get("id") for item in appointments):
        appointments.append(_normalize_appointment(appointment))
    _save_json_appointments(appointments)


def get_all() -> List[dict]:
    """Fetch all appointments ordered by created_at descending (newest first)."""
    if not supabase:
        return _load_json_appointments()
    try:
        response = (
            supabase.table("appointments")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return [_normalize_appointment(item) for item in response.data]
    except Exception as exc:
        print(f"[repo-appointments] Database unavailable, using JSON fallback: {exc}")
        return _load_json_appointments()


def create(data: dict) -> dict:
    """Create a new appointment and return it as a dict. Returns None on validation failure."""
    error = _validate_appointment(data)
    if error:
        return None

    appointment_data = _normalize_appointment(data)
    if not supabase:
        _append_json_appointment(appointment_data)
        return appointment_data
    try:
        response = supabase.table("appointments").insert(appointment_data).execute()
        created = response.data[0] if response.data else appointment_data
        _append_json_appointment(created)
        return _normalize_appointment(created)
    except Exception as exc:
        print(f"[repo-appointments] Database unavailable, storing in JSON fallback: {exc}")
        _append_json_appointment(appointment_data)
        return appointment_data


def delete(appointment_id: str) -> bool:
    """Delete an appointment by ID. Returns True if deleted, False if not found."""
    if not supabase:
        appointments = _load_json_appointments()
        updated = [a for a in appointments if a.get("id") != appointment_id]
        if len(updated) == len(appointments):
            return False
        _save_json_appointments(updated)
        return True
    try:
        response = (
            supabase.table("appointments")
            .delete()
            .eq("id", appointment_id)
            .execute()
        )
        if response.data and len(response.data) > 0:
            return True
        return False
    except Exception as exc:
        print(f"[repo-appointments] Database unavailable, deleting from JSON fallback: {exc}")
        appointments = _load_json_appointments()
        updated = [a for a in appointments if a.get("id") != appointment_id]
        if len(updated) == len(appointments):
            return False
        _save_json_appointments(updated)
        return True


def mark_read(appointment_id: str) -> bool:
    """Mark an appointment as read. Returns True if updated, False if not found."""
    if not supabase:
        appointments = _load_json_appointments()
        for a in appointments:
            if a.get("id") == appointment_id:
                a["read"] = True
                _save_json_appointments(appointments)
                return True
        return False
    try:
        response = (
            supabase.table("appointments")
            .update({"read": True})
            .eq("id", appointment_id)
            .execute()
        )
        if response.data and len(response.data) > 0:
            return True
        return False
    except Exception as exc:
        print(f"[repo-appointments] Database unavailable, updating JSON fallback: {exc}")
        appointments = _load_json_appointments()
        for a in appointments:
            if a.get("id") == appointment_id:
                a["read"] = True
                _save_json_appointments(appointments)
                return True
        return False


def get_stats() -> dict:
    """Return aggregate stats for appointments."""
    appointments = get_all()
    total = len(appointments)
    read_count = sum(1 for a in appointments if a.get("read"))
    time_window_counts = {}
    for a in appointments:
        tw = a.get("time_window", "Unknown")
        time_window_counts[tw] = time_window_counts.get(tw, 0) + 1
    return {
        "total_appointments": total,
        "unread": total - read_count,
        "time_windows": time_window_counts,
    }
