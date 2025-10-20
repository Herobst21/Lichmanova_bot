from datetime import datetime, timedelta
def ttl_expire(ts_hours: int) -> int:
    # return unix timestamp for expire_date
    return int((datetime.utcnow() + timedelta(hours=ts_hours)).timestamp())
