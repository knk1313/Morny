from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def get_zoneinfo(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("Asia/Tokyo")


def iso_now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_in_timezone(tz_name: str) -> datetime:
    return datetime.now(get_zoneinfo(tz_name))


def today_bounds_rfc3339(tz_name: str) -> tuple[str, str]:
    tz = get_zoneinfo(tz_name)
    now_local = datetime.now(tz)
    start = datetime.combine(now_local.date(), time.min, tzinfo=tz)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def normalize_iso_datetime(value: str) -> str:
    if value.endswith("Z"):
        return value[:-1] + "+00:00"
    return value


def parse_iso_datetime_to_local(value: str, tz_name: str) -> datetime:
    dt = datetime.fromisoformat(normalize_iso_datetime(value))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=get_zoneinfo(tz_name))
    return dt.astimezone(get_zoneinfo(tz_name))


def format_hhmm(dt: datetime) -> str:
    return dt.strftime("%H:%M")
