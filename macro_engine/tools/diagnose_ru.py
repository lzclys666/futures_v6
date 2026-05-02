# diagnose_ru.py
import sqlite3
from pathlib import Path

db_path = Path("pit_data.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查看 RU 各因子的数据量和最新值
factors = ["RU_SUP_THAI_CUP", "RU_SUP_THAI_LATEX", "RU_STK_WARRANT", 
           "RU_SPD_RU_BR", "RU_DEM_TIRE_ALLSTEEL", "RU_DEM_TIRE_SEMI", "RU_INV_QINGDAO"]

print("因子数据统计：")
print("-" * 50)
for f in factors:
    cursor.execute("SELECT COUNT(*), MAX(obs_date), raw_value FROM pit_factor_observations WHERE factor_code = ? AND symbol = 'RU'", (f,))
    row = cursor.fetchone()
    if row and row[0] > 0:
        cursor.execute("SELECT raw_value FROM pit_factor_observations WHERE factor_code = ? AND symbol = 'RU' ORDER BY obs_date DESC LIMIT 5", (f,))
        samples = cursor.fetchall()
        print(f"{f}: 共 {row[0]} 条, 最新日期: {row[1]}, 最新值: {row[2]:.4f}")
        print(f"   最近5条: {[s[0] for s in samples]}")
    else:
        print(f"{f}: 无数据")
conn.close()