import sqlite3
from datetime import date, timedelta

db = 'D:/futures_v6/macro_engine/pit_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
today = date.today()
cutoff7 = (today - timedelta(days=7)).isoformat()

cur.execute('''
    SELECT o.factor_code, o.symbol, o.raw_value, o.obs_date, o.source_confidence, o.source
    FROM pit_factor_observations o
    INNER JOIN (
        SELECT factor_code, MAX(obs_date) as maxd FROM pit_factor_observations
        WHERE obs_date >= ? GROUP BY factor_code
    ) latest ON o.factor_code = latest.factor_code AND o.obs_date = latest.maxd
    WHERE o.source_confidence <= 0.6
    ORDER BY o.source_confidence, o.factor_code
''', (cutoff7,))

rows = cur.fetchall()
print(f'L4回补因子 (conf<=0.6, 近7天): {len(rows)}个')
print(f'{"因子":<35} {"品种":<6} {"值":<12} {"日期":<12} {"conf":<6} {"来源"}')
print('-' * 90)
for row in rows:
    fc, sym, val, obs, conf, src = row
    val_str = f'{val:.4f}' if val else 'None'
    print(f'{fc:<35} {sym:<6} {val_str:<12} {str(obs):<12} {conf:<6} {src}')
conn.close()
