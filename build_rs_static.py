"""Generate a dated, honest static RS artifact for GitHub Pages.

Uses the existing verified-input validation and RS calculation module.
No synthetic data and no network calls here.
"""
import json
from pathlib import Path
from rs_engine import calculate

source = Path('data/rs_history.json')
target = Path('data/rs_static.json')
target.parent.mkdir(exist_ok=True)
result = {'ok': False, 'status': 'missing', 'error': 'ETF history unavailable'}
try:
    history = json.loads(source.read_text(encoding='utf-8'))
    if not isinstance(history, dict) or not isinstance(history.get('rows'), list):
        raise ValueError('ETF history contains no rows')
    calc = calculate(history['rows'], ma_len=21, base='SPY')
    result = {
        'ok': True,
        'status': 'fresh' if calc['fresh'] else 'stale',
        'asof': calc['asof'],
        'source': history.get('source', 'Not specified'),
        'price_basis': history.get('price_basis', 'Not specified'),
        'checked_at': history.get('checked_at'),
        'data': calc,
    }
except Exception as exc:
    result['error'] = f'{type(exc).__name__}: {exc}'
    print('RS snapshot unavailable:', result['error'])
target.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding='utf-8')
print('RS static artifact:', result['status'], result.get('asof', 'no date'))
