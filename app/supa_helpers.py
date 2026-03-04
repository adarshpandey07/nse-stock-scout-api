"""Helper utilities for Supabase PostgREST queries."""

from supabase import Client


def first_or_none(result) -> dict | None:
    """Get first row from Supabase query result or None."""
    if result.data:
        return result.data[0]
    return None


def row_count(db: Client, table: str, filters: dict | None = None) -> int:
    """Count rows with optional filters."""
    q = db.table(table).select("id", count="exact")
    for k, v in (filters or {}).items():
        q = q.eq(k, v)
    result = q.execute()
    return result.count or 0
