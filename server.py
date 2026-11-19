"""Yardeni Watch v10 local-only server. All external fetches happen server-side.

Run: python server.py
Optional: INSTALL_OPTIONAL_PRICE_FEED.bat installs yfinance as a fallback.
The web dashboard never contacts Yahoo, FRED, or Treasury itself.
"""
from __future__ import annotations
import csv
import datetime as dt
import io
import json
import math
import threading
import time
import urllib.request
import webbrowser
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from eastern_clock import eastern_now
from history_feed import fetch_aligned
from yardeni_feed import parse_rss, FEED_URL

from rs_engine import calculate, check_rows, is_fresh

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
DATA.mkdir(exist_ok=True)
HOST='127.0.0.1'
PORT=8765
LOCK=threading.Lock()
STATE={'refreshing':False, 'started':None, 'last_error':None}
CACHE=DATA/'snapshot_cache.json'
RS_CACHE=DATA/'rs_history.json'
RSS_CACHE=DATA/'yardeni_feed.json'
YARDENI=DATA/'yardeni_metrics.json'
BREADTH=DATA/'breadth_metrics.json'

def now_utc(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
def now_ny(): return eastern_now()

def read_json(path:Path, fallback=None):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, OSError):return fallback

def save_json(path:Path,value):
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    temp.replace(path)

def make_missing(source='Unavailable',error='Not retrieved'):
    return {'status':'missing','source':source,'asof':None,'error':error}

def load_manual(path:Path):
    x=read_json(path)
    if not isinstance(x,dict):return make_missing('User-supplied reviewed data','No file')
    # Never allow older monthly Yardeni metrics to appear fresh by virtue of a new request.
    date=x.get('asof')
    x['status']=('manual' if date and is_fresh(date,45) else 'stale')
    return x

def geturl(url:str,timeout=14):
    req=urllib.request.Request(url,headers={'User-Agent':'YardeniWatchPersonalResearch/10 (local browser dashboard; public data)','Accept':'text/xml,text/csv,*/*'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        result=r.read(3_000_000)
        if len(result)==3_000_000:raise ValueError('Response too large')
        return result

def fetch_treasury():
    ny=now_ny()
    months=[(ny.year,ny.month)]
    y,m=(ny.year-1,12) if ny.month==1 else (ny.year,ny.month-1)
    months.append((y,m))
    last_error='No observations'
    for yr,mo in months:
        url=('https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml'
             f'?data=daily_treasury_yield_curve&field_tdr_date_value_month={yr}{mo:02d}')
        try:
            root=ET.fromstring(geturl(url,timeout=12))
            items=[]
            for entry in root.iter():
                if entry.tag.split('}')[-1]!='entry':continue
                d={el.tag.split('}')[-1].upper():str(el.text).strip() for el in entry.iter() if el.text and el.text.strip()}
                date=(d.get('NEW_DATE') or '')[:10]
                def n(key):
                    v=d.get(key)
                    return float(v) if v and v not in ('N/A','null') else None
                a=(n('BC_2YEAR'),n('BC_10YEAR'),n('BC_30YEAR'))
                if date and all(v is not None and math.isfinite(v) for v in a):
                    items.append((date,*a))
            if items:
                date,y2,y10,y30=max(items)
                return {'y2':y2,'y10':y10,'y30':y30,'asof':date,'source':url,
                        'status':'daily' if is_fresh(date,5) else 'stale','checked_at':now_utc()}
        except Exception as e:last_error=f'{type(e).__name__}: {e}'
    return make_missing('U.S. Treasury official XML feed',last_error)

def fetch_fred_series(series:str):
    url=f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}'
    try:
        s=geturl(url,timeout=12).decode('utf-8-sig')
        if '<html' in s[:200].lower():raise ValueError('HTML instead of CSV')
        table=list(csv.DictReader(io.StringIO(s)))
        dates=[]
        for row in table:
            date=row.get('DATE') or row.get('observation_date')
            val=row.get(series)
            try:
                value=float(val)
                if date and math.isfinite(value):dates.append((date[:10],value))
            except (TypeError,ValueError):pass
        if not dates:raise ValueError('No numeric dated observations')
        dates.sort()
        date,value=dates[-1]
        prior10=dates[-11][1] if len(dates)>=11 else None
        return {'value':value,'asof':date,'delta10':value-prior10 if prior10 is not None else None,
                'status':'daily' if is_fresh(date,7) else 'stale','source':url,'checked_at':now_utc()}
    except Exception as e:return make_missing(url,f'{type(e).__name__}: {e}')

def fetch_credit_oil():
    hy=fetch_fred_series('BAMLH0A0HYM2')
    ig=fetch_fred_series('BAMLC0A0CM')
    wti=fetch_fred_series('DCOILWTICO')
    c={'hy':hy.get('value'),'ig':ig.get('value'),'hy_delta10':hy.get('delta10'),
       'status':'daily' if hy.get('status')=='daily' and ig.get('status')=='daily' else 'partial',
       'asof':min(hy.get('asof'),ig.get('asof')) if hy.get('asof') and ig.get('asof') else None,
       'source':'FRED / ICE BofA public series', 'meta':{'HY':hy,'IG':ig}}
    o={'wti':wti.get('value'),'status':wti.get('status'), 'asof':wti.get('asof'),
       'source':wti.get('source'),'error':wti.get('error')}
    return c,o

def refresh_public_feed():
    """Fetch public RSS metadata. On failure keep previous items and mark stale.

    Free RSS does not grant access to member-only Morning Briefing content.
    """
    cached=read_json(RSS_CACHE,{})
    try:
        items=parse_rss(geturl(FEED_URL,timeout=13))
        payload={'status':'fresh','source':FEED_URL,'checked_at':now_utc(),
                 'latest_post':items[0].get('published'), 'items':items}
        save_json(RSS_CACHE,payload)
        return payload
    except Exception as e:
        cached=cached if isinstance(cached,dict) else {}
        cached.update({'status':'stale' if cached.get('items') else 'missing',
                       'source':FEED_URL,'last_error':f'{type(e).__name__}: {e}'})
        # Failure time is not the success time; retain previous checked_at.
        save_json(RSS_CACHE,cached)
        return cached


def public_feed():
    cache=read_json(RSS_CACHE)
    if not isinstance(cache,dict):
        return {'status':'missing','source':FEED_URL,'items':[],
                'last_error':'Not fetched yet; update on opening dashboard'}
    if cache.get('checked_at'):
        try:
            age=(dt.datetime.now(dt.timezone.utc) -
                 dt.datetime.fromisoformat(cache['checked_at'])).total_seconds()
            if age>24*3600:cache['status']='stale'
        except (TypeError,ValueError):cache['status']='stale'
    return cache


def fresh_snapshot_fields(d:dict):
    if 'yardeni' in d:
        # Historical fundamentals do not become current just because cache refreshes.
        y=d['yardeni']
        if isinstance(y,dict) and y.get('asof'):
            y['status']='manual' if is_fresh(y['asof'],45) else 'stale'
        for k,days in [('forward_eps',14),('neri',45),('margin',30),('forward_pe',14)]:
            if isinstance(y,dict):
                date=y.get('metric_asof',{}).get(k)
                y.setdefault('metric_status',{})[k]='manual' if date and is_fresh(date,days) else 'stale'
    for key,days in [('treasury',5),('credit',7),('oil',7),('breadth',5)]:
        dct=d.get(key,{})
        date=dct.get('asof')
        if date and not is_fresh(date,days) and dct.get('status') not in ('missing',):
            dct['status']='stale'
    return d

def initial_snapshot():
    return {'yardeni':load_manual(YARDENI),'breadth':load_manual(BREADTH),
            'treasury':make_missing('U.S. Treasury','Refresh needed'),
            'credit':make_missing('FRED/ICE','Refresh needed'),
            'oil':make_missing('FRED spot WTI','Refresh needed'),
            'market_yields':make_missing('Market yield','Uses Treasury official close'),
            'market':make_missing('Daily market tape','Optional data feed not configured'),
            'effectiveYields':{}}

def get_snapshot():
    x=read_json(CACHE)
    if not isinstance(x,dict):x=initial_snapshot()
    x['yardeni']=load_manual(YARDENI)
    x['breadth']=load_manual(BREADTH)
    return fresh_snapshot_fields(x)

def do_refresh():
    try:
        t=fetch_treasury()
        c,o=fetch_credit_oil()
        old=get_snapshot()
        old['treasury']=t
        old['credit']=c
        old['oil']=o
        old['market_yields']=make_missing('Market intraday yields','Uses official Treasury daily yields')
        old['generated_at']=now_utc()
        save_json(CACHE,old)
        refresh_public_feed()
        STATE['last_error']=None
    except Exception as e:STATE['last_error']=f'{type(e).__name__}: {e}'
    finally:
        with LOCK:STATE['refreshing']=False

def trigger_refresh(force=False):
    with LOCK:
        if STATE['refreshing']:return
        cache=read_json(CACHE,{})
        last=cache.get('generated_at')
        if not force and last:
            try:
                if (dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(last)).total_seconds()<600:return
            except ValueError:pass
        STATE['refreshing']=True
        STATE['started']=now_utc()
    threading.Thread(target=do_refresh,daemon=True).start()

def fetch_etf_prices():
    """Best-effort ETF EOD history. Dependency-free chart first, yfinance fallback.

    Both are unofficial Yahoo sources. Failures are explicit; cached data
    are kept, and the user can import a dated CSV if the source blocks access.
    """
    errors=[]
    try:
        rows,meta=fetch_aligned(instant=now_ny())
        clean=check_rows(rows)
        return {'rows':clean,'asof':clean[-1]['date'],
                'source':meta['source'],'price_basis':meta['price_basis'],
                'available_symbols':meta['available_symbols'],
                'optional_errors':meta['optional_errors'],
                'checked_at':now_utc(),
                'status':'daily' if is_fresh(clean[-1]['date']) else 'stale'}
    except Exception as e:
        errors.append('Free chart endpoint: '+str(e))
    try:
        import yfinance as yf  # optional; no install needed for server boot
    except (ImportError, OSError) as e:
        errors.append('Optional yfinance not installed: '+str(e))
        raise RuntimeError(' | '.join(errors) +
            ' | Try INSTALL_OPTIONAL_PRICE_FEED.bat or import a dated CSV.')
    try:
        syms=['SPY','XHB','XRT','IYT','QQQ','IWM']
        df=yf.download(syms,period='2y',interval='1d',auto_adjust=True,
                       threads=False,progress=False,group_by='column',timeout=13)
        if df is None or len(df)==0:raise ValueError('Provider returned no history')
        closes=df['Close']
        if not hasattr(closes,'columns'):
            raise ValueError('Expected adjusted close columns for multiple tickers')
        for sym in ('SPY','XHB','XRT','IYT'):
            if sym not in closes.columns:
                raise ValueError('Missing '+sym+' close column')
        rows=[]
        ny=now_ny()
        for date, vals in closes.iterrows():
            trading_date=date.date()
            if trading_date>ny.date():continue
            if trading_date==ny.date() and ny.time()<dt.time(16,20):continue
            row={'date':trading_date.isoformat()}
            bad=False
            for sym in ('SPY','XHB','XRT','IYT'):
                val=vals.get(sym)
                if val is None or not math.isfinite(float(val)) or float(val)<=0:
                    bad=True;break
                row[sym]=float(val)
            if bad:continue
            for sym in ('QQQ','IWM'):
                val=vals.get(sym)
                if val is not None and math.isfinite(float(val)) and float(val)>0:
                    row[sym]=float(val)
            rows.append(row)
        clean=check_rows(rows)
        # Optional benchmark columns should be present on every row, else
        # discard them from all rows so the whole common price grid is sound.
        for sym in ('QQQ','IWM'):
            if any(sym not in r for r in clean):
                for r in clean:r.pop(sym,None)
        return {'rows':clean,'asof':clean[-1]['date'],
                'source':'Yahoo Finance adjusted EOD via yfinance (unofficial)',
                'price_basis':'dividend/split-adjusted daily close',
                'checked_at':now_utc(),
                'status':'daily' if is_fresh(clean[-1]['date']) else 'stale'}
    except Exception as e:
        errors.append('yfinance fallback: '+str(e))
        raise RuntimeError(' | '.join(errors) +
            ' | Try later or import a dated CSV; existing history is preserved.')

def rs_payload(ma_len=21,base='SPY'):
    cache=read_json(RS_CACHE)
    if not isinstance(cache,dict) or not isinstance(cache.get('rows'),list):
        return {'ok':False,'error':'No ETF history yet. Select Refresh ETF history or import CSV.'}
    try:
        calc=calculate(cache['rows'],ma_len,base)
        return {'ok':True,'source':cache.get('source'), 'price_basis':cache.get('price_basis'),
                'status':'fresh' if calc['fresh'] else 'stale','asof':calc['asof'],
                'checked_at':cache.get('checked_at'),'data':calc}
    except Exception as e:
        return {'ok':False,'error':str(e)}

class Handler(BaseHTTPRequestHandler):
    server_version='YardeniWatch/10.2'
    def log_message(self,format,*args):
        print('[local]',format%args)
    def reply(self,payload,code=200):
        data=json.dumps(payload,ensure_ascii=False,allow_nan=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-cache, no-store, must-revalidate')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Length',str(len(data)))
        self.end_headers();self.wfile.write(data)
    def parse_body(self):
        try:n=int(self.headers.get('Content-Length','0'))
        except ValueError:raise ValueError('Invalid request length')
        if n<0 or n>3_000_000:raise ValueError('Upload too large (max 3MB)')
        payload=json.loads(self.rfile.read(n) or b'{}')
        if not isinstance(payload,dict):raise ValueError('JSON object expected')
        return payload
    def do_GET(self):
        p=urlparse(self.path)
        if p.path in ('/','/dashboard.html'):
            data=(ROOT/'dashboard.html').read_bytes()
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Security-Policy',"default-src 'self' 'unsafe-inline' data:; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-src 'none'")
            self.send_header('Cache-Control','no-cache');self.send_header('Content-Length',str(len(data)))
            self.end_headers();self.wfile.write(data);return
        if p.path in ('/rs.css','/rs_module.js','/rs_prices_template.csv'):
            name=p.path.lstrip('/')
            data=(ROOT/name).read_bytes()
            ctype=('text/css' if name.endswith('.css') else 'application/javascript' if name.endswith('.js') else 'text/csv')
            self.send_response(200);self.send_header('Content-Type',ctype+'; charset=utf-8')
            self.send_header('Cache-Control','no-cache');self.send_header('Content-Length',str(len(data)))
            self.end_headers();self.wfile.write(data);return
        if p.path=='/health':
            self.reply({'ok':True,'version':'v10.2 · local-only','network':'backend only',
                        'refreshing':STATE['refreshing'],'last_error':STATE['last_error']});return
        if p.path=='/api/snapshot':
            snap=get_snapshot();self.reply({'ok':True,'data':snap,'refreshing':STATE['refreshing'],
                            'generated_at':snap.get('generated_at') or STATE['started'] or now_utc()});return
        if p.path=='/api/yardeni/feed':
            self.reply({'ok':True, **public_feed()});return
        if p.path=='/api/rs':
            q=parse_qs(p.query)
            try:
                ma=int(q.get('ma_len',['21'])[0]);base=q.get('base',['SPY'])[0]
                if not 1<=ma<=100:raise ValueError('EMA range 1–100')
                r=rs_payload(ma,base)
                self.reply(r,200 if r['ok'] else 409)
            except Exception as e:self.reply({'ok':False,'error':str(e)},400)
            return
        self.reply({'ok':False,'error':'Unknown endpoint'},404)
    def do_POST(self):
        p=urlparse(self.path)
        try:
            body=self.parse_body()
            if p.path=='/api/snapshot':
                trigger_refresh(bool(body.get('force')))
                x=get_snapshot()
                self.reply({'ok':True,'data':x,'refreshing':STATE['refreshing'],
                        'generated_at':x.get('generated_at') or STATE['started'] or now_utc()});return
            if p.path=='/api/rs/refresh':
                prices=fetch_etf_prices()
                save_json(RS_CACHE,prices)
                self.reply(rs_payload(int(body.get('ma_len',21)),str(body.get('base','SPY'))));return
            if p.path=='/api/rs/import':
                rows=check_rows(body.get('rows'))
                if len(rows)<max(63,3*int(body.get('ma_len',21))):
                    raise ValueError('At least three EMA lengths of history required')
                record={'rows':rows,'asof':rows[-1]['date'],'source':'User CSV import · unverified external prices',
                        'price_basis':str(body.get('price_basis','imported close values'))[:100],
                        'checked_at':now_utc(),'status':'manual'}
                save_json(RS_CACHE,record)
                self.reply(rs_payload(int(body.get('ma_len',21)),str(body.get('base','SPY'))));return
            self.reply({'ok':False,'error':'Unknown endpoint'},404)
        except Exception as e:
            self.reply({'ok':False,'error':f'{type(e).__name__}: {e}'},422)

def main():
    import sys
    if '--refresh-once' in sys.argv:
        print('Refreshing Treasury, FRED and public QuickTakes RSS once...')
        do_refresh()
        try:
            rows=fetch_etf_prices()
            save_json(RS_CACHE,rows)
            print('ETF EOD history:',rows['asof'])
        except Exception as e:
            print('ETF data unavailable; preserving last saved data:',e)
        print('Public feed:',public_feed().get('status'))
        print('Macro refresh status:', 'OK' if STATE['last_error'] is None else STATE['last_error'])
        return
    port=int(sys.argv[1]) if len(sys.argv)>1 else PORT
    for p in range(port,port+5):
        try:server=ThreadingHTTPServer((HOST,p),Handler);break
        except OSError:continue
    else:raise RuntimeError('Ports 8765–8769 are occupied')
    url=f'http://{HOST}:{p}/'
    print(f'Yardeni Watch v10.2 serving at {url} (Ctrl+C to quit)')
    threading.Timer(0.45,lambda:webbrowser.open(url)).start()
    try:server.serve_forever(poll_interval=.4)
    except KeyboardInterrupt:print('Stopping...')
    finally:server.server_close()

if __name__=='__main__':main()
