import urllib.request, json
# Test 1: /factors with symbol=RU
url = "http://127.0.0.1:8000/api/ic-heatmap/factors?symbol=RU"
with urllib.request.urlopen(url) as r:
    d = json.loads(r.read())
    factors = d['data']['factors']
    print(f"Test 1 /factors?symbol=RU: {d['data']['count']} factors")
    print("  First 5:", [f['factor_code'] for f in factors[:5]])

# Test 2: /heatmap with symbols=RU
url2 = "http://127.0.0.1:8000/api/ic-heatmap/?symbols=RU&lookback_days=120"
with urllib.request.urlopen(url2) as r:
    d2 = json.loads(r.read())
    hm = d2['data']
    non_none = sum(1 for row in hm['matrix'] for v in row if v is not None)
    print(f"\nTest 2 /heatmap symbols=RU: {len(hm['factors'])} factors")
    print("  Non-None ICs:", non_none, "/", len(hm['factors']))
    ic_vals = [row[0] for row in hm['matrix'] if row[0] is not None]
    print("  IC values:", ic_vals)

# Test 3: /factors no symbol
url3 = "http://127.0.0.1:8000/api/ic-heatmap/factors"
with urllib.request.urlopen(url3) as r:
    d3 = json.loads(r.read())
    print(f"\nTest 3 /factors (no symbol): {d3['data']['count']} factors")
    print("  First 5:", [f['factor_code'] for f in d3['data']['factors'][:5]])
    all_ru = [f for f in d3['data']['factors'] if f['factor_code'].startswith('RU_')]
    print("  RU factors:", [f['factor_code'] for f in all_ru])