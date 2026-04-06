from datetime import date, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

# NSE holidays for 2026 — weekday closures only (update annually)
# Source: https://groww.in/p/nse-holidays, https://cleartax.in/s/nse-holidays-2026
NSE_HOLIDAYS_2026 = {
    date(2026, 1, 15),  # Maharashtra Municipal Elections
    date(2026, 1, 26),  # Republic Day
    date(2026, 3, 3),   # Holi
    date(2026, 3, 26),  # Shri Ram Navami
    date(2026, 3, 31),  # Shri Mahavir Jayanti
    date(2026, 4, 3),   # Good Friday
    date(2026, 4, 14),  # Dr. Baba Saheb Ambedkar Jayanti
    date(2026, 5, 1),   # Maharashtra Day
    date(2026, 5, 28),  # Bakri Id (Id-Ul-Adha)
    date(2026, 6, 26),  # Muharram
    date(2026, 9, 14),  # Ganesh Chaturthi
    date(2026, 10, 2),  # Mahatma Gandhi Jayanti
    date(2026, 10, 20), # Dussehra
    date(2026, 11, 10), # Diwali (Balipratipada)
    date(2026, 11, 24), # Prakash Gurpurb Sri Guru Nanak Dev
    date(2026, 12, 25), # Christmas
}


def _is_trading_day(d: date) -> bool:
    """Check if a date is a valid NSE trading day (weekday + not a holiday)."""
    return d.weekday() < 5 and d not in NSE_HOLIDAYS_2026


def today_ist() -> date:
    """Return today's date in IST timezone."""
    return datetime.now(IST).date()


def trading_days_between(start: date, end: date) -> list[date]:
    """Return list of trading dates between start and end (inclusive)."""
    days = []
    current = start
    while current <= end:
        if _is_trading_day(current):
            days.append(current)
        current += timedelta(days=1)
    return days


def last_trading_day(ref: date | None = None) -> date:
    """Return the most recent trading day on or before ref (default: today IST)."""
    if ref is None:
        ref = today_ist()
    while not _is_trading_day(ref):
        ref -= timedelta(days=1)
    return ref
