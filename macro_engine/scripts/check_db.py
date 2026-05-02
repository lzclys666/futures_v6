import sqlite3
conn = sqlite3.connect('D:/futures_v6/macro_engine/pit_data.db')
cursor = conn.cursor()

cursor.execute("SELECT obs_date, contract, open, high, low, close, volume FROM jm_futures_ohlcv WHERE contract LIKE 'JM%' ORDER BY obs_date DESC LIMIT 5")
rows = cursor.fetchall()
print('JM latest 5 records:')
for row in rows:
    print(f'  {row[0]} {row[1]}: O={row[2]} H={row[3]} L={row[4]} C={row[5]} V={row[6]}')

cursor.execute("SELECT contract, COUNT(*) FROM jm_futures_ohlcv GROUP BY contract")
stats = cursor.fetchall()
print(f'\nContract stats:')
for contract, count in stats:
    print(f'  {contract}: {count} records')

conn.close()
