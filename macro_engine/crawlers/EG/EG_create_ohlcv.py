"""Create eg_futures_ohlcv table and populate with historical data from AKShare."""
import sqlite3
import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))

DB_PATH = r"D:\futures_v6\macro_engine\pit_data.db"

def create_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS eg_futures_ohlcv (
            pub_date TEXT,
            obs_date TEXT,
            contract TEXT,
            trade_date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            hold INTEGER,
            settle REAL,
            PRIMARY KEY (contract, trade_date)
        )
    """)
    conn.commit()
    conn.close()
    print("[OK] eg_futures_ohlcv table created/verified")

def populate_data():
    import akshare as ak
    
    conn = sqlite3.connect(DB_PATH)
    today = datetime.date.today()
    pub_date = today.strftime('%Y-%m-%d')
    
    # Get main contract data
    print("[INFO] Fetching EG0 main contract data...")
    try:
        df = ak.futures_main_sina(symbol="EG0")
        if df is None or df.empty:
            print("[WARN] EG0 data is empty")
            return
        
        cols = list(df.columns)
        # Columns: 日期, 开盘价, 最高价, 最低价, 收盘价, 成交量, 持仓量, 动态结算价
        count = 0
        for _, row in df.iterrows():
            trade_date = str(row[cols[0]])[:10]
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO eg_futures_ohlcv
                    (pub_date, obs_date, contract, trade_date, open, high, low, close, volume, hold, settle)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pub_date, trade_date, 'EG0', trade_date,
                    float(row[cols[1]]), float(row[cols[2]]), float(row[cols[3]]),
                    float(row[cols[4]]), int(row[cols[5]]), int(row[cols[6]]),
                    float(row[cols[7]])
                ))
                count += 1
            except Exception as e:
                print(f"[WARN] Skip row {trade_date}: {e}")
        
        conn.commit()
        print(f"[OK] Inserted {count} rows for EG0 main contract")
    except Exception as e:
        print(f"[ERR] EG0 failed: {e}")
    
    # Get individual contract data for recent contracts
    contracts_to_try = ["EG2509", "EG2510", "EG2511", "EG2512", "EG2601", "EG2602", "EG2603", "EG2604", "EG2605"]
    for contract in contracts_to_try:
        try:
            print(f"[INFO] Fetching {contract}...")
            df = ak.futures_zh_daily_sina(symbol=contract)
            if df is None or df.empty:
                print(f"[WARN] {contract} data is empty")
                continue
            
            count = 0
            for _, row in df.iterrows():
                trade_date = str(row['date'])[:10]
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO eg_futures_ohlcv
                        (pub_date, obs_date, contract, trade_date, open, high, low, close, volume, hold, settle)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        pub_date, trade_date, contract, trade_date,
                        float(row['open']), float(row['high']), float(row['low']),
                        float(row['close']), int(row['volume']), int(row['hold']),
                        float(row['settle'])
                    ))
                    count += 1
                except Exception as e:
                    pass  # Skip bad rows silently
            
            conn.commit()
            print(f"[OK] {contract}: {count} rows")
        except Exception as e:
            print(f"[WARN] {contract} failed: {type(e).__name__}: {e}")
    
    # Verify
    cursor = conn.execute("SELECT COUNT(*) FROM eg_futures_ohlcv")
    total = cursor.fetchone()[0]
    cursor = conn.execute("SELECT COUNT(DISTINCT contract) FROM eg_futures_ohlcv")
    contracts = cursor.fetchone()[0]
    print(f"\n[RESULT] eg_futures_ohlcv: {total} rows, {contracts} contracts")
    
    cursor = conn.execute("SELECT contract, MIN(trade_date), MAX(trade_date), COUNT(*) FROM eg_futures_ohlcv GROUP BY contract ORDER BY contract")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} ~ {row[2]} ({row[3]} rows)")
    
    conn.close()

if __name__ == "__main__":
    create_table()
    populate_data()
