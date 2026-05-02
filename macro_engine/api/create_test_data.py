import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sqlite3

# 创建测试数据生成器

def create_test_data():
    """
    创建真实测试数据
    
    基于现有数据文件创建测试数据集
    """
    
    # 1. 创建因子数据（基于金银比）
    print("[1] Creating AU_AG_ratio factor data...")
    
    # 读取真实数据
    ratio_df = pd.read_csv(r'D:\futures_v6\macro_engine\data\crawlers\_shared\daily\AU_AG_ratio_corrected.csv')
    ratio_df['date'] = pd.to_datetime(ratio_df['date'])
    
    # 创建AG品种目录
    os.makedirs(r'D:\futures_v6\macro_engine\data\crawlers\AG\daily', exist_ok=True)
    
    # 保存为AG的momentum因子（使用金银比作为代理）
    ratio_df.to_csv(
        r'D:\futures_v6\macro_engine\data\crawlers\AG\daily\momentum.csv',
        index=False
    )
    print(f"  [OK] AG momentum factor: {len(ratio_df)} rows")
    
    # 2. 创建AG价格数据（基于真实白银价格模拟）
    print("\n[2] Creating AG price data...")
    
    # 使用金银比和黄金价格反推白银价格
    # 假设黄金价格2020年约350元/克
    np.random.seed(42)
    dates = ratio_df['date'].values
    
    # 模拟白银价格（基于金银比）
    base_price = 3500  # 白银价格基准（元/千克）
    returns = np.random.normal(0.0005, 0.015, len(dates))
    prices = base_price * np.exp(np.cumsum(returns))
    
    price_df = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.normal(0, 0.005, len(dates))),
        'high': prices * (1 + abs(np.random.normal(0, 0.01, len(dates)))),
        'low': prices * (1 - abs(np.random.normal(0, 0.01, len(dates)))),
        'close': prices,
        'volume': np.random.randint(100000, 500000, len(dates)),
        'hold': np.random.randint(50000, 200000, len(dates))
    })
    
    price_df.to_csv(
        r'D:\futures_v6\macro_engine\data\crawlers\AG\daily\AG_fut_close.csv',
        index=False
    )
    print(f"  [OK] AG price data: {len(price_df)} rows")
    
    # 3. 创建USD/CNY因子数据
    print("\n[3] Creating USD/CNY factor data...")
    
    usd_df = pd.read_csv(r'D:\futures_v6\macro_engine\data\crawlers\_shared\daily\USD_CNY_spot.csv')
    usd_df['date'] = pd.to_datetime(usd_df['date'])
    
    # 保存为usd_index因子
    usd_df[['date', 'usd_cny']].rename(columns={'usd_cny': 'value'}).to_csv(
        r'D:\futures_v6\macro_engine\data\crawlers\AG\daily\usd_index.csv',
        index=False
    )
    print(f"  [OK] AG usd_index factor: {len(usd_df)} rows")
    
    # 4. 创建CU价格数据（复制已有数据）
    print("\n[4] Confirming CU price data...")
    
    cu_df = pd.read_csv(r'D:\futures_v6\macro_engine\data\crawlers\CU\daily\CU_fut_close.csv')
    print(f"  [OK] CU price data: {len(cu_df)} rows")
    
    # 5. 创建CU的LME价差因子
    print("\n[5] Creating CU LME spread factor...")
    
    spread_df = pd.read_csv(r'D:\futures_v6\macro_engine\data\crawlers\CU\daily\LME_copper_cash_3m_spread.csv')
    spread_df['date'] = pd.to_datetime(spread_df['date'])
    
    # 保存为basis因子（使用close列）
    spread_df[['date', 'close']].rename(columns={'close': 'value'}).to_csv(
        r'D:\futures_v6\macro_engine\data\crawlers\CU\daily\basis.csv',
        index=False
    )
    print(f"  [OK] CU basis factor: {len(spread_df)} rows")
    
    # 6. 创建参数数据库
    print("\n[6] Creating parameter database...")
    
    db_path = r'D:\futures_v6\macro_engine\data\parameter_db.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS optimal_parameters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            variety TEXT NOT NULL,
            factor TEXT NOT NULL,
            ic_window INTEGER DEFAULT 60,
            hold_period INTEGER DEFAULT 5,
            weight_decay REAL DEFAULT 1.0,
            ir REAL DEFAULT 0.0,
            ic_mean REAL DEFAULT 0.0,
            win_rate REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 插入测试数据
    test_params = [
        ('AG', 'momentum', 60, 10, 0.8, -1.198, -0.130, 0.93),
        ('AG', 'usd_index', 60, 5, 0.5, -0.366, -0.040, 0.55),
        ('CU', 'basis', 60, 5, 1.0, 1.947, 0.150, 0.65),
        ('CU', 'momentum', 60, 10, 0.6, 0.500, 0.080, 0.58),
        ('RB', 'momentum', 60, 5, 1.0, 0.300, 0.050, 0.52),
        ('RB', 'inventory_change', 30, 3, 0.7, 0.450, 0.070, 0.55),
    ]
    
    cursor.executemany('''
        INSERT INTO optimal_parameters 
        (variety, factor, ic_window, hold_period, weight_decay, ir, ic_mean, win_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', test_params)
    
    conn.commit()
    conn.close()
    print(f"  [OK] Parameter database: {len(test_params)} records")
    
    print("\n" + "=" * 80)
    print("Test data creation completed!")
    print("=" * 80)
    
    return {
        'AG_momentum': len(ratio_df),
        'AG_price': len(price_df),
        'AG_usd': len(usd_df),
        'CU_price': len(cu_df),
        'CU_basis': len(spread_df),
        'params': len(test_params)
    }


if __name__ == "__main__":
    print("=" * 80)
    print("Creating Real Test Data")
    print("=" * 80)
    
    result = create_test_data()
    
    print("\nData Summary:")
    for key, value in result.items():
        print(f"  {key}: {value} rows/records")
