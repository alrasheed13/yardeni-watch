"""Transparent calculation of the Druckenmiller-inspired ETF price-relative panel.

This is NOT a licensed/official Druckenmiller indicator. It is a ratio-EMA
implementation for independent market-internals research, not evidence of
institutional buying/selling. Data must be valid completed daily closes.
"""
from __future__ import annotations
import datetime as dt
import math
from typing import Any
from eastern_clock import eastern_now

REQUIRED = ("SPY", "XHB", "XRT", "IYT")
OPTIONAL = ("QQQ", "IWM")


def check_rows(rows: list[dict[str, Any]], min_rows: int = 63) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or not min_rows <= len(rows) <= 5000:
        raise ValueError(f"Expected {min_rows}–5000 completed daily rows")
    clean: list[dict[str, Any]] = []
    previous = ''
    eastern = eastern_now()
    today = eastern.date().isoformat()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('All rows must be objects')
        date = str(row.get('date', '')).strip()
        try:
            dt.date.fromisoformat(date)
        except ValueError as e:
            raise ValueError(f'Invalid date: {date!r}') from e
        if date <= previous or date > today:
            raise ValueError('Dates must be strictly ascending, unique, and not in future')
        if date == today and eastern.time() < dt.time(16,20):
            raise ValueError('Current session is not complete before 16:20 Eastern time')
        previous = date
        item: dict[str, Any] = {'date': date}
        for sym in REQUIRED:
            val = row.get(sym)
            try:
                num = float(val)
            except (TypeError, ValueError) as e:
                raise ValueError(f'Missing {sym} on {date}') from e
            if not math.isfinite(num) or num <= 0:
                raise ValueError(f'Invalid {sym} on {date}')
            item[sym] = round(num, 8)
        for sym in OPTIONAL:
            if sym in row and row[sym] is not None and str(row[sym]).strip():
                num = float(row[sym])
                if not math.isfinite(num) or num <= 0:
                    raise ValueError(f'Invalid {sym} on {date}')
                item[sym] = round(num, 8)
        clean.append(item)
    return clean


def ema(values: list[float], length: int = 21) -> list[float | None]:
    if not isinstance(length, int) or not 1 <= length <= 100:
        raise ValueError('EMA length must be an integer in [1, 100]')
    out: list[float | None] = [None] * len(values)
    if len(values) < length:
        return out
    alpha = 2.0 / (length + 1.0)
    prior = sum(values[:length]) / length
    out[length - 1] = prior
    for i in range(length, len(values)):
        prior = alpha * values[i] + (1 - alpha) * prior
        out[i] = prior
    return out


def is_fresh(last_date: str, max_calendar_days: int = 5, today: dt.date | None = None) -> bool:
    current = today or eastern_now().date()
    last = dt.date.fromisoformat(last_date)
    return 0 <= (current - last).days <= max_calendar_days


def calculate(rows: list[dict[str, Any]], ma_len: int = 21, base: str = 'SPY',
              allow_stale: bool = False) -> dict[str, Any]:
    # All rows need a shared close date; missing dates are rejected upstream.
    rows = check_rows(rows, min_rows=max(63, 3 * ma_len))
    if base not in ('SPY', 'QQQ', 'IWM'):
        raise ValueError('Baseline must be SPY, QQQ, or IWM')
    if any(base not in r for r in rows):
        raise ValueError(f'Baseline {base} not available in all rows')
    dates = [r['date'] for r in rows]
    fresh = is_fresh(dates[-1])
    sectors = {}
    for sym in ('XHB', 'XRT', 'IYT'):
        values = [r[sym] / r[base] for r in rows]
        smooth = ema(values, ma_len)
        tail = values[-1]
        anchor = values[0]
        ma_last = smooth[-1]
        above3 = all(values[-i] > smooth[-i] for i in (1, 2, 3))
        below3 = all(values[-i] < smooth[-i] for i in (1, 2, 3))
        ema_slope5 = 100 * (ma_last / smooth[-6] - 1) if smooth[-6] else None
        rs20 = 100 * (tail / values[-21] - 1)
        signal = ('Leading' if above3 and ema_slope5 > 0 else
                  'Weakening' if below3 and ema_slope5 < 0 else
                  'Improving' if tail >= ma_last else 'Mixed')
        if not fresh and not allow_stale:
            signal = 'STALE'
        sectors[sym] = dict(
            ratio=tail, ema_current=ma_last, ema_length=ma_len, rs_change20_pct=rs20,
            ema_slope5_pct=ema_slope5, above3=above3, below3=below3,
            signal=signal, normalized=100 * tail / anchor,
            points=[{'date': dates[i], 'ratio': round(values[i], 8),
                     'ema': round(smooth[i], 8) if smooth[i] is not None else None,
                     'normalized': 100 * values[i] / anchor} for i in range(len(rows))]
        )
    weak = sum(x['signal'] == 'Weakening' for x in sectors.values())
    lead = sum(x['signal'] == 'Leading' for x in sectors.values())
    base_close = [r[base] for r in rows]
    near_high60 = base_close[-1] >= .98 * max(base_close[-60:])
    base_down20 = base_close[-1] < base_close[-21]
    if not fresh and not allow_stale:
        diagnosis = 'STALE – no current signal'
    elif weak == 3:
        diagnosis = 'Broad economic-sector relative weakness (3/3)'
    elif weak >= 2 and near_high60:
        diagnosis = 'Bearish divergence watch: benchmark near 60-day high, 2+ RS weakening'
    elif lead >= 2 and base_down20:
        diagnosis = 'Early improvement watch: 2+ RS leading during benchmark decline'
    elif lead >= 2:
        diagnosis = 'Constructive relative participation (2+/3)'
    else:
        diagnosis = 'Mixed / no synchronized confirmation'
    return dict(asof=dates[-1], fresh=fresh, base=base, ma_len=ma_len,
                weak_count=weak if fresh else None, lead_count=lead if fresh else None,
                near_high60=near_high60, base_down20=base_down20,
                diagnosis=diagnosis, sectors=sectors)
