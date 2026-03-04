from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.dependencies import AdminUser, CurrentUser, DB
from app.schemas.news import NewsPointerScoreOut, NewsSourceCreate, NewsSourceOut, StockNewsOut
from app.services.news_scorer import compute_pointer_score, update_article_sentiments
from app.services.news_scraper import scrape_all_sources

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/sources", response_model=list[NewsSourceOut])
def list_sources(db: DB, _user: CurrentUser):
    return db.table("news_sources").select("*").order("credibility_score", desc=True).execute().data


@router.post("/sources", response_model=NewsSourceOut)
def add_source(req: NewsSourceCreate, db: DB, _user: AdminUser):
    result = db.table("news_sources").insert(req.model_dump()).execute()
    return result.data[0] if result.data else {}


@router.get("/articles", response_model=list[StockNewsOut])
def list_articles(
    db: DB, _user: CurrentUser,
    symbol: str = Query(None),
    date_from: date = Query(None),
    date_to: date = Query(None),
    limit: int = Query(50, le=200),
):
    q = db.table("stock_news").select("*").order("published_at", desc=True)
    if symbol:
        q = q.eq("symbol", symbol.upper())
    if date_from:
        q = q.gte("published_at", str(date_from))
    if date_to:
        q = q.lte("published_at", str(date_to))
    return q.limit(limit).execute().data


@router.get("/pointer-scores", response_model=NewsPointerScoreOut)
def get_pointer_score(db: DB, _user: CurrentUser, symbol: str = Query(...)):
    score = compute_pointer_score(db, symbol.upper())
    if not score:
        raise HTTPException(status_code=404, detail=f"No news data for {symbol}")
    return score


@router.post("/scrape-now")
async def trigger_scrape(db: DB, _user: AdminUser, symbol: str = Query(None)):
    count = await scrape_all_sources(db, symbol.upper() if symbol else None)
    scored = update_article_sentiments(db, symbol.upper() if symbol else None)
    return {"articles_scraped": count, "articles_scored": scored}
