from datetime import date, timedelta


def trading_days_between(start: date, end: date) -> list[date]:
    """Return list of weekday dates between start and end (inclusive)."""
    days = []
    current = start
    while current <= end:
        if current.weekday() < 5:  # Mon=0 .. Fri=4
            days.append(current)
        current += timedelta(days=1)
    return days


def last_trading_day(ref: date | None = None) -> date:
    """Return the most recent weekday on or before ref (default today)."""
    if ref is None:
        ref = date.today()
    while ref.weekday() >= 5:
        ref -= timedelta(days=1)
    return ref
