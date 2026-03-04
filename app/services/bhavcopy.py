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
    run = db.table("fetch_runs").insert({
        "run_date": str(target_date), "status": "started",
    }).execute()
    run_data = run.data[0] if run.data else {"id": "", "status": "started"}

    log_activity(db, event_type="fetch_started", entity_type="data_fetch_run",
                 entity_id=str(run_data.get("id", "")),
                 message=f"Bhavcopy fetch started for {target_date}", status="started")

    try:
        rows = await _download_and_parse(target_date)
        inserted, skipped = _upsert_bars(db, rows, target_date)

        updated = db.table("fetch_runs").update({
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
        db.table("fetch_runs").update({
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
        await client.get("https://www.nseindia.com/")
        resp = await client.get(url)
        if resp.status_code != 200:
            resp = await client.get(url_v2)
        resp.raise_for_status()

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    csv_name = [n for n in zf.namelist() if n.endswith(".csv")][0]
    csv_content = zf.read(csv_name).decode("utf-8")

    rows = []
    reader = csv.DictReader(io.StringIO(csv_content))
    for row in reader:
        row = {k.strip(): v.strip() if v else v for k, v in row.items()}
        series = row.get("SERIES", row.get("SCtySrs", ""))
        if series != "EQ":
            continue
        symbol = row.get("SYMBOL", row.get("TckrSymb", ""))
        if not symbol:
            continue
        try:
            rows.append({
                "symbol": symbol,
                "date": str(target_date),
                "open": float(row.get("OPEN", row.get("OpnPric", 0))),
                "high": float(row.get("HIGH", row.get("HghPric", 0))),
                "low": float(row.get("LOW", row.get("LwPric", 0))),
                "close": float(row.get("CLOSE", row.get("ClsPric", 0))),
                "volume": int(row.get("TOTTRDQTY", row.get("TtlTradgVol", 0))),
            })
        except (ValueError, TypeError):
            continue
    return rows


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
