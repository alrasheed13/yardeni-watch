"""Optional dependency-free historical ETF downloader, using Yahoo's UNOFFICIAL chart JSON.

Yahoo's chart endpoint has no service-level agreement, may block automated
access, and is not an authorized source for commercial redistribution. No
sample/fabricated data are returned on failures. Browser never contacts Yahoo.
"""
from __future__ import annotations
import concurrent.futures
import datetime as dt
import json
import math
import urllib.error
import urllib.parse
import urllib.request
from eastern_clock import eastern_now

REQUIRED = ('SPY', 'XHB', 'XRT', 'IYT')
OPTIONAL = ('QQQ', 'IWM')


def _download_symbol(sym: str, getter=None, instant=None):
    # Adjusted closes are required for a consistent long-run relative series.
    url = ('https://query1.finance.yahoo.com/v8/finance/chart/'
           + urllib.parse.quote(sym, safe='') + '?' + urllib.parse.urlencode({
               'range': '2y', 'interval': '1d', 'events': 'div,splits',
               'includeAdjustedClose': 'true'}))
    if getter is None:
        def getter(u):
            req=urllib.request.Request(u,headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36',
                'Accept': 'application/json', 'Referer': 'https://finance.yahoo.com/'})
            with urllib.request.urlopen(req,timeout=13) as res:
                raw=res.read(2_000_001)
                if len(raw)>2_000_000:
                    raise ValueError('ETF provider response exceeds 2MB')
                return raw
    blob=getter(url)
    if isinstance(blob,bytes): data=json.loads(blob.decode('utf-8'))
    elif isinstance(blob,str):data=json.loads(blob)
    else: data=blob
    chart=data.get('chart') or {}
    if chart.get('error'):
        raise ValueError(f'{sym}: {chart["error"]}')
    result=(chart.get('result') or [None])[0]
    if not isinstance(result,dict):raise ValueError(f'{sym}: missing chart results')
    meta=result.get('meta') or {}
    if str(meta.get('currency','USD')).upper()!='USD':
        raise ValueError(f'{sym}: expected USD prices')
    timestamps=result.get('timestamp') or []
    inds=result.get('indicators') or {}
    adjusted=inds.get('adjclose') or []
    values=(adjusted[0].get('adjclose') if adjusted and isinstance(adjusted[0],dict) else None)
    if not isinstance(values,list) or len(timestamps)!=len(values):
        raise ValueError(f'{sym}: adjusted prices unavailable or misaligned')
    ny=instant or eastern_now()
    series={}
    for unix, price in zip(timestamps,values):
        if price is None:continue
        try:v=float(price)
        except (TypeError,ValueError):continue
        if not math.isfinite(v) or v<=0:continue
        bar_date=eastern_now(dt.datetime.fromtimestamp(int(unix),tz=dt.timezone.utc)).date()
        if bar_date>ny.date():continue
        # Never mix incomplete intraday data with historical completed closes.
        if bar_date==ny.date() and ny.time()<dt.time(16,20):continue
        series[bar_date.isoformat()]=v
    if len(series)<63:raise ValueError(f'{sym}: insufficient completed observations ({len(series)})')
    return series


def fetch_aligned(getter=None, instant=None):
    """Return aligned split/dividend-adjusted daily closes, no forward fills.

    The required series must all be retrieved. Optional QQQ/IWM can fail
    independently, without preventing the default SPY benchmark from working.
    """
    syms=REQUIRED+OPTIONAL
    series={}
    failures={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        jobs={pool.submit(_download_symbol,s,getter,instant):s for s in syms}
        for job in concurrent.futures.as_completed(jobs):
            s=jobs[job]
            try:series[s]=job.result()
            except Exception as e:failures[s]=f'{type(e).__name__}: {e}'
    required_fail=[s for s in REQUIRED if s not in series]
    if required_fail:
        raise RuntimeError('ETF chart download failed: '+ '; '.join(f'{s}: {failures.get(s)}' for s in required_fail))
    dates=set.intersection(*(set(series[s]) for s in REQUIRED))
    optional_ok=[s for s in OPTIONAL if s in series]
    if optional_ok:
        # QQQ/IWM are optional for SPY benchmark, include only on dates shared
        # with mandatory series; no filling of gaps or silent extrapolation.
        dates=set.intersection(dates,*(set(series[s]) for s in optional_ok))
    rows=[]
    for day in sorted(dates):
        row={'date':day}
        for s in REQUIRED+tuple(optional_ok):row[s]=series[s][day]
        rows.append(row)
    if len(rows)<63:
        raise ValueError(f'Only {len(rows)} common completed sessions; require at least 63')
    return rows, {'source':'Yahoo Finance chart JSON (unofficial; personal research)',
                  'price_basis':'dividend/split-adjusted daily closes',
                  'available_symbols':list(REQUIRED+tuple(optional_ok)),
                  'optional_errors':{s:failures[s] for s in OPTIONAL if s in failures}}
