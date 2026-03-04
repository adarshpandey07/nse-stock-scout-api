from fastapi import APIRouter, HTTPException, Query

from app.dependencies import CurrentUser, DB
from app.schemas.watchlist import WatchlistItemCreate, WatchlistItemOut

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("/", response_model=list[WatchlistItemOut])
def list_watchlist(
    db: DB, _user: CurrentUser,
    user_pin: str = Query(...),
    watchlist_type: str = Query(None),
):
    q = db.table("watchlist_items").select("*").eq("user_pin", user_pin)
    if watchlist_type:
        q = q.eq("watchlist_type", watchlist_type)
    return q.order("added_at", desc=True).execute().data


@router.post("/", response_model=WatchlistItemOut)
def add_to_watchlist(req: WatchlistItemCreate, db: DB, _user: CurrentUser):
    existing = (
        db.table("watchlist_items")
        .select("id")
        .eq("user_pin", req.user_pin)
        .eq("symbol", req.symbol.upper())
        .eq("watchlist_type", req.watchlist_type)
        .limit(1)
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=409, detail=f"{req.symbol} already in {req.watchlist_type} watchlist")

    result = db.table("watchlist_items").insert({
        "user_pin": req.user_pin,
        "symbol": req.symbol.upper(),
        "watchlist_type": req.watchlist_type,
        "notes": req.notes or "",
    }).execute()

    return result.data[0] if result.data else {}


@router.delete("/{item_id}")
def remove_from_watchlist(item_id: str, db: DB, _user: CurrentUser):
    item = db.table("watchlist_items").select("id").eq("id", item_id).limit(1).execute()
    if not item.data:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    db.table("watchlist_items").delete().eq("id", item_id).execute()
    return {"status": "removed"}
