import csv
import io
import logging
from datetime import date, datetime, timezone

import httpx
from supabase import Client

from app.services.activity import log_activity

logger = logging.getLogger(__name__)

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
}


def _bhavcopy_url(d: date) -> str:
    ddmmyy = d.strftime("%d%m%y")
    return f"https://nsearchives.nseindia.com/content/historical/EQUITIES/{d.strftime('%Y')}/{d.strftime('%b').upper()}/cm{ddmmyy}bhav.csv.zip"


def _bhavcopy_url_v2(d: date) -> str:
    ds = d.strftime("%Y%m%d")
    return f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{ds}_F_0000.csv.zip"


async def fetch_bhavcopy(db: Client, target_date: date) -> dict:
    run = db.table("data_fetch_runs").insert({
        "run_date": str(target_date), "status": "started",
    }).execute()
    run_data = run.data[0] if run.data else {"id": "", "status": "started"}

    log_activity(db, event_type="fetch_started", entity_type="data_fetch_run",
                 entity_id=str(run_data.get("id", "")),
                 message=f"Bhavcopy fetch started for {target_date}", status="started")

    try:
        rows, stock_meta = await _download_and_parse(target_date)
        _sync_nse_stocks(db, stock_meta)
        inserted, skipped = _upsert_bars(db, rows, target_date)
        _update_fundamentals_prices(db, rows)

        updated = db.table("data_fetch_runs").update({
            "status": "completed",
            "total_symbols": len(rows),
            "inserted_count": inserted,
            "skipped_count": skipped,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", run_data["id"]).execute()

        result = updated.data[0] if updated.data else {**run_data, "status": "completed", "inserted_count": inserted}

        log_activity(db, event_type="fetch_completed", entity_type="data_fetch_run",
                     entity_id=str(run_data.get("id", "")),
                     message=f"Bhavcopy fetch completed for {target_date}: {inserted} inserted, {skipped} skipped",
                     status="completed",
                     metadata_json={"total": len(rows), "inserted": inserted, "skipped": skipped})
        return result

    except Exception as e:
        db.table("data_fetch_runs").update({
            "status": "failed",
            "error_message": str(e)[:2000],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", run_data["id"]).execute()

        log_activity(db, event_type="fetch_failed", entity_type="data_fetch_run",
                     entity_id=str(run_data.get("id", "")),
                     message=f"Bhavcopy fetch failed for {target_date}: {e}", status="failed")
        raise


async def _download_and_parse(target_date: date) -> list[dict]:
    import zipfile

    url = _bhavcopy_url(target_date)
    url_v2 = _bhavcopy_url_v2(target_date)

    async with httpx.AsyncClient(headers=NSE_HEADERS, follow_redirects=True, timeout=30) as client:
        # Try v2 URL first (doesn't need cookies, more reliable)
        resp = await client.get(url_v2)
        if resp.status_code != 200:
            # Fallback to v1 URL (needs NSE homepage cookies)
            try:
                await client.get("https://www.nseindia.com/")
            except Exception:
                pass
            resp = await client.get(url)
        resp.raise_for_status()

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    csv_name = [n for n in zf.namelist() if n.endswith(".csv")][0]
    csv_content = zf.read(csv_name).decode("utf-8")

    rows = []
    stock_meta = []  # (symbol, name, isin) for nse_stocks sync
    reader = csv.DictReader(io.StringIO(csv_content))
    for row in reader:
        row = {k.strip(): v.strip() if v else v for k, v in row.items()}
        series = row.get("SERIES", row.get("SctySrs", row.get("SCtySrs", "")))
        if series != "EQ":
            continue
        symbol = row.get("SYMBOL", row.get("TckrSymb", ""))
        if not symbol:
            continue
        name = row.get("NAME", row.get("FinInstrmNm", ""))
        isin = row.get("ISIN", row.get("ISIN", ""))
        stock_meta.append((symbol, name, isin))
        try:
            # Use LTP (Last Traded Price) as close — this matches what
            # trading apps like Groww/Zerodha show. NSE "Close" is a
            # weighted average of last 30 min, LTP is the actual last trade.
            ltp = row.get("LAST", row.get("LastPric", 0))
            nse_close = row.get("CLOSE", row.get("ClsPric", 0))
            # Use LTP if available, fallback to NSE close
            close_price = float(ltp) if float(ltp) > 0 else float(nse_close)
            rows.append({
                "symbol": symbol,
                "date": str(target_date),
                "open": float(row.get("OPEN", row.get("OpnPric", 0))),
                "high": float(row.get("HIGH", row.get("HghPric", 0))),
                "low": float(row.get("LOW", row.get("LwPric", 0))),
                "close": close_price,
                "volume": int(row.get("TOTTRDQTY", row.get("TtlTradgVol", 0))),
            })
        except (ValueError, TypeError):
            continue
    return rows, stock_meta


def _sync_nse_stocks(db: Client, stock_meta: list[tuple]) -> int:
    """Ensure all symbols from bhavcopy exist in nse_stocks table."""
    if not stock_meta:
        return 0

    # Get existing symbols in one query
    existing = db.table("nse_stocks").select("symbol").execute()
    existing_symbols = {r["symbol"] for r in existing.data}

    new_stocks = []
    for symbol, name, isin in stock_meta:
        if symbol not in existing_symbols:
            new_stocks.append({
                "symbol": symbol,
                "name": name or symbol,
                "isin": isin or "",
                "series": "EQ",
                "is_active": True,
            })

    if new_stocks:
        for i in range(0, len(new_stocks), 100):
            try:
                db.table("nse_stocks").upsert(
                    new_stocks[i:i + 100], on_conflict="symbol"
                ).execute()
            except Exception as e:
                logger.warning(f"Failed to upsert nse_stocks batch: {e}")

    if new_stocks:
        logger.info(f"Added {len(new_stocks)} new stocks to nse_stocks")
    return len(new_stocks)


def _update_fundamentals_prices(db: Client, rows: list[dict]) -> int:
    """Update current_price in stock_fundamentals from latest bhavcopy close prices."""
    if not rows:
        return 0
    updates = [{"symbol": r["symbol"], "current_price": r["close"]} for r in rows]
    count = 0
    for i in range(0, len(updates), 100):
        try:
            db.table("stock_fundamentals").upsert(
                updates[i:i + 100], on_conflict="symbol"
            ).execute()
            count += len(updates[i:i + 100])
        except Exception as e:
            logger.warning(f"Failed to update fundamentals prices batch: {e}")
    return count


def _upsert_bars(db: Client, rows: list[dict], target_date: date) -> tuple[int, int]:
    if not rows:
        return 0, 0

    # Use upsert (on_conflict ignore via unique constraint)
    inserted = 0
    skipped = 0
    batch_size = 100
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        try:
            result = db.table("daily_bars").upsert(batch, on_conflict="symbol,date").execute()
            inserted += len(result.data) if result.data else 0
        except Exception:
            # Fallback: insert individually, skip duplicates
            for row in batch:
                try:
                    db.table("daily_bars").insert(row).execute()
                    inserted += 1
                except Exception:
                    skipped += 1

    return inserted, skipped


async def rebuild_history(db: Client, start_date: date, end_date: date) -> list[dict]:
    from app.utils import trading_days_between

    runs = []
    for d in trading_days_between(start_date, end_date):
        try:
            run = await fetch_bhavcopy(db, d)
            runs.append(run)
        except Exception as e:
            logger.error(f"Failed to fetch bhavcopy for {d}: {e}")
    return runs
