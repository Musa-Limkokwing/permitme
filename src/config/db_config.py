import os
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

def get_supabase_pooler_uri() -> str:
    uri = (os.getenv("SUPABASE_POOLER_URI") or os.getenv("DATABASE_URL") or "").strip()
    if not uri:
        raise ValueError(
            "Missing SUPABASE_POOLER_URI environment variable. "
            "Set it to your Supabase Session Pooler connection string."
        )
    return uri


def get_signing_secret() -> str:
    secret = (os.getenv("PERMITME_SIGNING_SECRET") or "").strip()
    if not secret:
        return "permitme-dev-signing-secret-change-in-prod"
    return secret


def describe_connection(uri: str) -> dict[str, object]:
    parsed = urlparse(uri)
    return {
        "host": parsed.hostname or "unknown",
        "port": parsed.port or 5432,
        "dbname": (parsed.path or "/postgres").lstrip("/") or "postgres",
        "user": parsed.username or "postgres",
        "sslmode": "require",
    }