import requests, json

# 统计最近一天（最新）的信号方向
print("=" * 60)
print("各品种最新信号（历史快照）")
print("=" * 60)

# 获取所有品种最新信号
r = requests.get('http://127.0.0.1:8000/api/macro/signal/all', timeout=10)
all_signals = r.json()['data']

for s in all_signals:
    sym = s['symbol']
    score = s.get('compositeScore')
    direction = s['direction']
    updated = s.get('updatedAt', 'N/A')
    score_str = f"{score:.4f}" if score is not None else "N/A"
    print(f"  {sym}: score={score_str} -> {direction}  (updated {updated[:16]})")

print()

# 获取最近 7 天历史，看每天各品种方向
for days in [7]:
    r = requests.get(f'http://127.0.0.1:8000/api/macro/score-history/AU?days={days}', timeout=10)
    hist = r.json()['data']
    if hist:
        print(f"AU 近 {days} 天历史:")
        for rec in hist[-7:]:
            print(f"  {rec['date']}: score={rec['score']:.4f} -> {rec['direction']}")

# 检查近7天每天有多少品种是 SHORT
print()
print("=" * 60)
print("近 7 天每日 SHORT 品种数")
print("=" * 60)

# 获取所有品种近7天历史
date_counts = {}
for sym in ['RU', 'CU', 'AU', 'AG']:
    r = requests.get(f'http://127.0.0.1:8000/api/macro/score-history/{sym}?days=7', timeout=10)
    hist = r.json().get('data', [])
    for rec in hist:
        d = rec['date']
        if rec['direction'] == 'SHORT':
            date_counts[d] = date_counts.get(d, 0) + 1

for d in sorted(date_counts.keys()):
    print(f"  {d}: {date_counts[d]} 个 SHORT")
