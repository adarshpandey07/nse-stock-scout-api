"""Database layer — uses Supabase REST API (PostgREST) via service role key."""

from supabase import Client

from app.supabase_client import get_supabase


# Keep Base for any ORM model references (no longer used for queries)
class Base:
    pass


def get_db() -> Client:
    """Return the Supabase client (replaces SQLAlchemy Session)."""
    return get_supabase()
