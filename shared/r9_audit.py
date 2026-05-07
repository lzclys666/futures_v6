# 文件：D:\futures_v6\shared\r9_audit.py
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

DB = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute('SELECT DISTINCT symbol FROM pit_factor_observations ORDER BY symbol')
symbols = [r[0] for r in cur.fetchall()]

p1 = []  # >=10
p2 = []  # 7-9
fail = []  # <7

for sym in symbols:
    cur.execute('''SELECT factor_code, obs_date, raw_value 
                   FROM pit_factor_observations 
                   WHERE symbol=? ORDER BY obs_date DESC, factor_code''', (sym,))
    rows = cur.fetchall()
    latest = {}
    for fc, od, rv in rows:
        if fc not in latest:
            latest[fc] = (od, rv)
    valid = sum(1 for fc, (od, rv) in latest.items() if rv is not None and od >= '2026-04-01')
    total = len(latest)
    
    if valid >= 10:
        p1.append((sym, valid, total))
    elif valid >= 7:
        p2.append((sym, valid, total))
    else:
        missing = [fc for fc, (od, rv) in latest.items() if rv is None or od < '2026-04-01']
        fail.append((sym, valid, total, missing))

conn.close()

print(f"=== 品种因子分层验收 ({len(symbols)} symbols) ===")
print(f"\nP1 标准（≥10有效因子）：{len(p1)} 个")
for s, v, t in p1:
    print(f"  {s}: {v}/{t}")

print(f"\nP2 标准（7-9有效因子）：{len(p2)} 个")
for s, v, t in p2:
    print(f"  {s}: {v}/{t}")

print(f"\n不达标（<7有效因子）：{len(fail)} 个")
for s, v, t, m in fail:
    print(f"  {s}: {v}/{t} — 缺失: {m}")
