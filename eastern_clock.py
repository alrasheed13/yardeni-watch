"""Small, zero-dependency New York market clock for Yardeni Watch.

Prefer IANA time zones when available. Windows Python may not have tzdata,
so there is a documented fallback for the current US DST rules (since 2007).
The fallback is sufficient for current US market EOD dates, but is not a
replacement for historical IANA timezone databases.
"""
from __future__ import annotations
import datetime as dt

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    try:
        _NY = ZoneInfo('America/New_York')
    except ZoneInfoNotFoundError:
        _NY = None
except ImportError:  # defensive, stdlib zoneinfo supported by CPython 3.9+
    _NY = None


def _sunday(year: int, month: int, nth: int) -> int:
    first = dt.date(year, month, 1)
    first_sunday = 1 + ((6 - first.weekday()) % 7)
    return first_sunday + (nth - 1) * 7


def eastern_now(utc: dt.datetime | None = None, force_fallback: bool = False) -> dt.datetime:
    """Return timezone-aware Eastern time; fall back without external tzdata.

    The US DST boundaries are 07:00 UTC on the second Sunday of March
    and 06:00 UTC on the first Sunday of November (rules since 2007).
    """
    if utc is None:
        utc = dt.datetime.now(dt.timezone.utc)
    if utc.tzinfo is None:
        raise ValueError('UTC instant must be timezone aware')
    utc = utc.astimezone(dt.timezone.utc)
    if _NY is not None and not force_fallback:
        return utc.astimezone(_NY)
    year = utc.year
    starts = dt.datetime(year, 3, _sunday(year, 3, 2), 7, tzinfo=dt.timezone.utc)
    ends = dt.datetime(year, 11, _sunday(year, 11, 1), 6, tzinfo=dt.timezone.utc)
    offset = -4 if starts <= utc < ends else -5
    tz = dt.timezone(dt.timedelta(hours=offset), 'EDT' if offset == -4 else 'EST')
    return utc.astimezone(tz)
