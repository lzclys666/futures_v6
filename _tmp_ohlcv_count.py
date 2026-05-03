import sqlite3
conn = sqlite3.connect('D:/futures_v6/macro_engine/pit_data.db')
cur = conn.cursor()
tables = ['au_futures_ohlcv','ag_futures_ohlcv','cu_futures_ohlcv',
          'jm_futures_ohlcv','ni_futures_ohlcv','rb_futures_ohlcv',
          'ru_futures_ohlcv','zn_futures_ohlcv']
print('表名               行数')
print('-'*30)
for t in tables:
    try:
        cur.execute(f'SELECT COUNT(*) FROM {t}')
        cnt = cur.fetchone()[0]
        print(f'{t:<20} {cnt}')
    except Exception as e:
        print(f'{t:<20} 错误:{e}')
