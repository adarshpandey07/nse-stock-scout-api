from datetime import date, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

# NSE holidays for 2026 (update annually)
# Source: https://www.nseindia.com/resources/exchange-communication-holidays
NSE_HOLIDAYS_2026 = {
    date(2026, 1, 26),  # Republic Day
    date(2026, 2, 17),  # Maha Shivaratri
    date(2026, 3, 14),  # Holi
    date(2026, 3, 31),  # Id-Ul-Fitr (Ramadan)
    date(2026, 4, 2),   # Ram Navami
    date(2026, 4, 3),   # Good Friday
    date(2026, 4, 14),  # Dr. Ambedkar Jayanti
    date(2026, 5, 1),   # Maharashtra Day
    date(2026, 6, 7),   # Id-Ul-Adha (Bakri Id)
    date(2026, 7, 7),   # Muharram
    date(2026, 8, 15),  # Independence Day
    date(2026, 8, 16),  # Parsi New Year
    date(2026, 9, 5),   # Milad-un-Nabi
    date(2026, 10, 2),  # Mahatma Gandhi Jayanti
    date(2026, 10, 20), # Dussehra
    date(2026, 10, 21), # Dussehra
    date(2026, 11, 9),  # Diwali (Laxmi Pujan)
    date(2026, 11, 10), # Diwali (Balipratipada)
    date(2026, 11, 27), # Gurunanak Jayanti
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
