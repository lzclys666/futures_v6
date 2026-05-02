import sqlite3
conn = sqlite3.connect('D:/futures_v6/macro_engine/pit_data.db')
cursor = conn.cursor()

# 检查各表的数据量
tables = ['jm_futures_basis', 'jm_futures_spread', 'jm_futures_hold_volume', 'jm_basis_volatility', 'jm_import_monthly']

for table in tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        
        # 获取列名
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]
        
        print(f'{table}: {count} rows')
        print(f'  columns: {columns}')
        
        # 查看前3条
        cursor.execute(f"SELECT * FROM {table} LIMIT 3")
        rows = cursor.fetchall()
        for row in rows:
            print(f'  {row}')
        print()
    except Exception as e:
        print(f'{table}: ERROR - {e}\n')

conn.close()
