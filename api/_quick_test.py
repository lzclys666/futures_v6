import requests, json

BASE = 'http://127.0.0.1:8000'
tests = [
    ('GET /health',                                  f'{BASE}/health',                                  200, 0),
    ('GET /api/macro/signal/RU',                     f'{BASE}/api/macro/signal/RU',                     200, 0),
    ('GET /api/macro/signal/all',                    f'{BASE}/api/macro/signal/all',                    200, 0),
    ('GET /api/macro/factor/RU',                      f'{BASE}/api/macro/factor/RU',                     200, 0),
    ('GET /api/macro/score-history/RU?days=7',       f'{BASE}/api/macro/score-history/RU?days=7',       200, 0),
    ('GET /api/macro/score-history/RU?days=90',      f'{BASE}/api/macro/score-history/RU?days=90',      200, 0),
    ('GET /api/macro/signal/UNKNOWN (expect 404)',   f'{BASE}/api/macro/signal/UNKNOWN',                404, 404),
    ('GET /api/macro/score-history/RU?days=999 (422)',f'{BASE}/api/macro/score-history/RU?days=999',     422, None),
]

passed = 0; failed = 0
for name, url, exp_status, exp_code in tests:
    r = requests.get(url, timeout=5)
    data = r.json()
    code = data.get('code')
    ok = (r.status_code == exp_status) and (exp_code is None or code == exp_code)
    mark = '[PASS]' if ok else '[FAIL]'
    print(f'{mark} {name} | status={r.status_code} code={code}')
    if ok: passed += 1
    else: failed += 1

print()
print(f'=== Result: {passed} passed, {failed} failed ===')

# Extra validation of RU signal structure
r = requests.get(f'{BASE}/api/macro/signal/RU', timeout=5)
d = r.json()['data']
print()
print('RU signal sample:')
print(f'  compositeScore={d["compositeScore"]} (valid range -1~1: {-1 <= d["compositeScore"] <= 1})')
print(f'  direction={d["direction"]} (enum LONG/NEUTRAL/SHORT: {d["direction"] in ("LONG","NEUTRAL","SHORT")})')
print(f'  updatedAt={d["updatedAt"]}')
print(f'  factors count={len(d["factors"])} (expected 7)')
for f in d['factors']:
    print(f'  {f["factor_code"]}: value={f["factor_value"]} weight={f["factor_weight"]} direction={f["factor_direction"]}')

print()
r2 = requests.get(f'{BASE}/api/macro/score-history/RU?days=30', timeout=5)
hist = r2.json()['data']
print(f'Score history: {len(hist)} records (max 90)')
if hist:
    print(f'  First: {hist[0]}')
    print(f'  Last:  {hist[-1]}')
