import sqlite3
conn = sqlite3.connect(r'D:\futures_v6\macro_engine\pit_data.db')
c = conn.cursor()
c.execute("SELECT factor_code FROM pit_factor_observations WHERE symbol='RU' GROUP BY factor_code")
ru_factors = [r[0] for r in c.fetchall()]
c.execute("SELECT factor_code FROM factor_metadata WHERE is_active=1")
meta_factors = [r[0] for r in c.fetchall()]
c.execute("SELECT DISTINCT symbol FROM pit_factor_observations")
all_symbols = [r[0] for r in c.fetchall()]
conn.close()
print('RU factors:', ru_factors)
print('Meta active count:', len(meta_factors))
print('Meta active:', meta_factors[:10])
print('RU in meta?', any(f in meta_factors for f in ru_factors))
print('All symbols in DB:', all_symbols)
