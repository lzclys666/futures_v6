import sqlite3, os
db = r'D:\futures_v6\macro_engine\pit_data.db'
print('PIT DB exists:', os.path.exists(db))
if os.path.exists(db):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    print('Tables:', [t[0] for t in tables])
    if tables:
        cur.execute('PRAGMA table_info(' + tables[0][0] + ')')
        cols = cur.fetchall()
        print('Columns:', [(c[1], c[2]) for c in cols])
        cur.execute('SELECT * FROM ' + tables[0][0] + ' LIMIT 3')
        rows = cur.fetchall()
        print('Sample rows:', rows[:2])
        # Check factor table
        if len(tables) > 1:
            print('Factor table:')
            cur.execute('PRAGMA table_info(' + tables[1][0] + ')')
            cols2 = cur.fetchall()
            print('Columns:', [(c[1], c[2]) for c in cols2])
    conn.close()
