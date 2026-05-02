import sys
sys.path.insert(0, r'D:\futures_v6')
sys.path.insert(0, r'D:\futures_v6\macro_engine')
import sqlite3
db = r'D:\futures_v6\macro_engine\pit_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("SELECT DISTINCT factor_code FROM pit_factor_observations WHERE symbol='RU' ORDER BY factor_code")
ru_factors = [r[0] for r in cur.fetchall()]
print('RU factors:', ru_factors)
cur.execute("SELECT DISTINCT factor_code FROM pit_factor_observations ORDER BY factor_code")
all_factors = [r[0] for r in cur.fetchall()]
print('All factor codes:', all_factors)
conn.close()