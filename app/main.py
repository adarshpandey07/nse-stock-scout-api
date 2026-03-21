from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    actions, activity, admin, analysis, astro, auth, backtest, chat, config,
    dashboard, fundamental_scanner, health, jobs, kite, news, polymarket,
    results, sop, stocks, superstar, telegram, trades, wallet, watchlist_v2,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="NSE Stock Scout",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Existing Routers ──
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(config.router)
app.include_router(results.router)
app.include_router(jobs.router)
app.include_router(activity.router)
app.include_router(sop.router)

# ── Phase 1: Kite + Trading + Wallet ──
app.include_router(kite.router)
app.include_router(trades.router)
app.include_router(wallet.router)

# ── Phase 2: Stocks + Fundamentals + F1/F2/F3 ──
app.include_router(stocks.router)
app.include_router(fundamental_scanner.router)

# ── Phase 3: News ──
app.include_router(news.router)

# ── Phase 4: Superstar ──
app.include_router(superstar.router)

# ── Phase 5: Actions + Watchlist + Dashboard ──
app.include_router(actions.router)
app.include_router(watchlist_v2.router)
app.include_router(dashboard.router)

# ── Phase 6: Analysis Suite ──
app.include_router(analysis.router)

# ── Phase 7: Backtest ──
app.include_router(backtest.router)

# ── Phase 8: Aadarsh.AI Chat ──
app.include_router(chat.router)

# ── Phase 9: Financial Astrology ──
app.include_router(astro.router)

# ── Phase 10: Telegram ──
app.include_router(telegram.router)

# ── Phase 11: Polymarket Trading ──
app.include_router(polymarket.router)
