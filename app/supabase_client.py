"""Supabase REST client — replaces direct PostgreSQL connection."""

from supabase import Client, create_client

from app.config import settings


def _get_client() -> Client:
    url = settings.vite_supabase_url
    # Use service role key if available, otherwise fall back to anon key
    key = settings.supabase_service_role_key or settings.vite_supabase_publishable_key
    if not url or not key:
        raise RuntimeError(
            "VITE_SUPABASE_URL and either SUPABASE_SERVICE_ROLE_KEY or VITE_SUPABASE_PUBLISHABLE_KEY must be set"
        )
    return create_client(url, key)


# Singleton
_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = _get_client()
    return _client
