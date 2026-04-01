from __future__ import annotations

from datetime import datetime, timedelta


WEEKDAY_MAP = {
    "MON": 0,
    "TUE": 1,
    "WED": 2,
    "THU": 3,
    "FRI": 4,
    "SAT": 5,
    "SUN": 6,
}


def next_run_time(now: datetime, weekday: str, hour: int) -> datetime:
    target_weekday = WEEKDAY_MAP[weekday]
    days_ahead = (target_weekday - now.weekday()) % 7
    candidate = now.replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
    if candidate <= now:
        candidate += timedelta(days=7)
    return candidate
