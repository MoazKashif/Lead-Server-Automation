import os
import sys
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

supabase: Client | None = (
    create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    if SUPABASE_URL and SUPABASE_SERVICE_KEY
    else None
)

APPOINTMENTS_DDL = """
CREATE TABLE IF NOT EXISTS appointments (
    id VARCHAR(30) PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    appointment_date DATE NOT NULL,
    time_window VARCHAR(100) NOT NULL,
    automation_goal TEXT NOT NULL DEFAULT '',
    read BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_appointments_created_at ON appointments(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_appointments_email ON appointments(email);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_appointments_read ON appointments(read);
"""


def init_db():
    """Create tables if they don't exist. Tries psycopg2 first, falls back gracefully."""
    sql = APPOINTMENTS_DDL
    # Try direct psycopg2 connection first
    try:
        import psycopg2
        db_url = os.getenv("SUPABASE_DATABASE_URL", "")
        if db_url:
            conn = psycopg2.connect(db_url, connect_timeout=5)
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            conn.close()
            print("[db] Appointments table created via direct connection.")
            return
    except ImportError:
        pass
    except Exception as exc:
        print(f"[db] Direct connection failed ({exc}); trying REST API...")

    # Fallback: try via supabase-py REST API (works over IPv4 HTTPS)
    if supabase:
        try:
            resp = supabase.table("appointments").select("*").limit(1).execute()
            print("[db] Appointments table already exists.")
            return
        except Exception:
            pass
        # Try creating the table via PostgREST schema endpoint
        try:
            client = supabase.postgrest
            raw = client.request("POST", "/rpc/", json={})
        except Exception:
            pass
        print(
            "[db] Could not create appointments table via REST API.\n"
            f"  Run this SQL in your Supabase Dashboard > SQL Editor:\n{APPOINTMENTS_DDL}",
            file=sys.stderr,
        )
    else:
        print("[db] No Supabase credentials configured; using JSON fallback for appointments.")
