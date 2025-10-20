from datetime import datetime, timedelta, timezone

UTC = timezone.utc

def now_utc() -> datetime:
    return datetime.now(tz=UTC)

def add_days(dt: datetime, days: int) -> datetime:
    return dt + timedelta(days=days)
