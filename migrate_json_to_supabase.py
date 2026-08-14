#!/usr/bin/env python3
"""Migrate existing JSON data to Supabase PostgreSQL.

Usage:
    export SUPABASE_URL=...
    export SUPABASE_SERVICE_KEY=...
    python migrate_json_to_supabase.py
"""

import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from supabase import create_client

BASE_DIR = Path(__file__).parent
LEADS_FILE = BASE_DIR / "leads.json"
APPOINTMENTS_FILE = BASE_DIR / "appointments.json"


def load_json(filepath: Path) -> list:
    if not filepath.exists():
        print(f"  File not found: {filepath}")
        return []
    try:
        with filepath.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            print(f"  WARNING: {filepath.name} is not a JSON array, skipping.")
            return []
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"  ERROR reading {filepath.name}: {e}")
        return []


def get_existing_ids(supabase_client, table: str) -> set:
    """Fetch all existing IDs from a Supabase table."""
    try:
        response = supabase_client.table(table).select("id").execute()
        return {row["id"] for row in response.data}
    except Exception as e:
        print(f"  WARNING: Could not fetch existing IDs from {table}: {e}")
        return set()


def migrate_leads(supabase_client) -> tuple:
    """Migrate leads from JSON to Supabase. Returns (migrated, skipped, failed)."""
    records = load_json(LEADS_FILE)
    if not records:
        return 0, 0, 0

    existing_ids = get_existing_ids(supabase_client, "leads")
    migrated = 0
    skipped = 0
    failed = 0

    for record in records:
        try:
            if not isinstance(record, dict):
                print(f"  Skipping malformed record (not a dict)")
                failed += 1
                continue

            record_id = record.get("id")
            if not record_id:
                print(f"  Skipping record without ID")
                failed += 1
                continue

            if record_id in existing_ids:
                skipped += 1
                continue

            # Ensure ai_analysis is a dict (JSON serializable)
            if "ai_analysis" in record and isinstance(record["ai_analysis"], str):
                try:
                    record["ai_analysis"] = json.loads(record["ai_analysis"])
                except json.JSONDecodeError:
                    record["ai_analysis"] = {}

            # Normalize fields
            lead_data = {
                "id": record_id,
                "name": record.get("name", ""),
                "email": record.get("email", ""),
                "phone": record.get("phone", ""),
                "company": record.get("company", ""),
                "message": record.get("message", ""),
                "source": record.get("source", "Web Form"),
                "ai_analysis": record.get("ai_analysis", {}),
                "read": record.get("read", False),
            }
            # Preserve timestamps if present
            if record.get("timestamp"):
                lead_data["timestamp"] = record["timestamp"]
            if record.get("created_at"):
                lead_data["created_at"] = record["created_at"]

            supabase_client.table("leads").insert(lead_data).execute()
            migrated += 1

        except Exception as e:
            print(f"  ERROR migrating lead {record.get('id', '?')}: {e}")
            failed += 1

    return migrated, skipped, failed


def migrate_appointments(supabase_client) -> tuple:
    """Migrate appointments from JSON to Supabase. Returns (migrated, skipped, failed)."""
    records = load_json(APPOINTMENTS_FILE)
    if not records:
        return 0, 0, 0

    existing_ids = get_existing_ids(supabase_client, "appointments")
    migrated = 0
    skipped = 0
    failed = 0

    for record in records:
        try:
            if not isinstance(record, dict):
                print(f"  Skipping malformed record (not a dict)")
                failed += 1
                continue

            record_id = record.get("id")
            if not record_id:
                print(f"  Skipping record without ID")
                failed += 1
                continue

            if record_id in existing_ids:
                skipped += 1
                continue

            appt_data = {
                "id": record_id,
                "name": record.get("name", ""),
                "email": record.get("email", ""),
                "appointment_date": record.get("appointment_date", ""),
                "time_window": record.get("time_window", ""),
                "automation_goal": record.get("automation_goal", ""),
                "read": record.get("read", False),
            }
            # Preserve created_at timestamp if present
            if record.get("created_at"):
                appt_data["created_at"] = record["created_at"]

            supabase_client.table("appointments").insert(appt_data).execute()
            migrated += 1

        except Exception as e:
            print(f"  ERROR migrating appointment {record.get('id', '?')}: {e}")
            failed += 1

    return migrated, skipped, failed


def main():
    print("=" * 60)
    print("  FantomAI — JSON to Supabase Migration")
    print("=" * 60)

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        print("\nERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        print("Set them as environment variables or in a .env file.")
        sys.exit(1)

    print(f"\nConnecting to Supabase...")
    try:
        client = create_client(url, key)
    except Exception as e:
        print(f"ERROR: Failed to connect to Supabase: {e}")
        sys.exit(1)

    print("Connected successfully.\n")

    # Migrate Leads
    print("--- Leads Migration ---")
    leads_migrated, leads_skipped, leads_failed = migrate_leads(client)

    print("\n--- Appointments Migration ---")
    appts_migrated, appts_skipped, appts_failed = migrate_appointments(client)

    # Summary
    print("\n" + "=" * 60)
    print("  MIGRATION SUMMARY")
    print("=" * 60)
    print(f"  Migrated leads:       {leads_migrated}")
    print(f"  Skipped duplicates:   {leads_skipped}")
    print(f"  Failed:               {leads_failed}")
    print()
    print(f"  Migrated appointments: {appts_migrated}")
    print(f"  Skipped duplicates:    {appts_skipped}")
    print(f"  Failed:                {appts_failed}")
    print("=" * 60)
    print("\nJSON files have NOT been deleted. You may remove them manually after verification.")


if __name__ == "__main__":
    main()
