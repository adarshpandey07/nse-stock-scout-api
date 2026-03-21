"""Settlement service — wraps position_service.check_resolutions for the router."""

from supabase import Client

from app.services.polymarket.position_service import check_resolutions


async def run_settlement(db: Client) -> int:
    """Check for resolved markets and settle all affected positions."""
    return await check_resolutions(db)
