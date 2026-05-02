import sqlite3
conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')
c = conn.cursor()
c.execute("SELECT DISTINCT factor_code FROM pit_factor_observations WHERE symbol='RU' ORDER BY factor_code")
rows = c.fetchall()
conn.close()
print('RU factors:', [r[0] for r in rows])
