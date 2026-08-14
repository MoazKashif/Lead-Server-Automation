import os
import sys
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

_IS_PRODUCTION = os.getenv("ENVIRONMENT", "production").lower() == "production"

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    except Exception as exc:
        logger.error(f"Failed to create Supabase client: {exc}")
        if _IS_PRODUCTION:
            print(f"[db] FATAL: Cannot connect to Supabase in production: {exc}", file=sys.stderr)
else:
    if _IS_PRODUCTION:
        print("[db] WARNING: Supabase credentials not configured in production!", file=sys.stderr)
    else:
        print("[db] Supabase not configured; JSON fallback will be used for development.")


def init_db():
    """Verify database connectivity. Tables must be created via Supabase SQL Editor."""
    if not supabase:
        if _IS_PRODUCTION:
            raise RuntimeError(
                "[db] FATAL: Supabase is not configured in production. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables. "
                "Refusing to start to prevent data loss."
            )
        logger.info("Running without Supabase (development mode with JSON fallback).")
        return

    # Verify connectivity by checking if tables exist
    try:
        supabase.table("leads").select("id").limit(1).execute()
        print("[db] Leads table verified.")
    except Exception as exc:
        print(f"[db] WARNING: Could not verify leads table: {exc}", file=sys.stderr)

    try:
        supabase.table("appointments").select("id").limit(1).execute()
        print("[db] Appointments table verified.")
    except Exception as exc:
        print(f"[db] WARNING: Could not verify appointments table: {exc}", file=sys.stderr)
