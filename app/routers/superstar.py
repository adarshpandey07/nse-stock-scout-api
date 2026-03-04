from fastapi import APIRouter, HTTPException, Query

from app.dependencies import AdminUser, CurrentUser, DB
from app.schemas.superstar import SuperstarHoldingOut, SuperstarInvestorCreate, SuperstarInvestorOut
from app.services.superstar_scraper import get_recent_changes, scrape_all_investors, scrape_investor_holdings

router = APIRouter(prefix="/superstar", tags=["superstar"])


@router.get("/investors", response_model=list[SuperstarInvestorOut])
def list_investors(db: DB, _user: CurrentUser):
    return db.table("superstar_investors").select("*").eq("is_active", True).execute().data


@router.post("/investors", response_model=SuperstarInvestorOut)
def add_investor(req: SuperstarInvestorCreate, db: DB, _user: AdminUser):
    result = db.table("superstar_investors").insert(req.model_dump()).execute()
    return result.data[0] if result.data else {}


@router.get("/investors/{investor_id}/holdings", response_model=list[SuperstarHoldingOut])
def get_holdings(investor_id: str, db: DB, _user: CurrentUser, quarter: str = Query(None)):
    q = db.table("superstar_holdings").select("*").eq("investor_id", investor_id)
    if quarter:
        q = q.eq("quarter", quarter)
    return q.order("created_at", desc=True).execute().data


@router.post("/scrape-holdings")
async def trigger_scrape(db: DB, _user: AdminUser, investor_id: str = Query(None)):
    if investor_id:
        count = await scrape_investor_holdings(db, investor_id)
        return {"investor_id": investor_id, "holdings_scraped": count}
    else:
        count = await scrape_all_investors(db)
        return {"total_holdings_scraped": count}


@router.get("/changes")
def recent_changes(db: DB, _user: CurrentUser, limit: int = Query(50, le=100)):
    return get_recent_changes(db, limit)
