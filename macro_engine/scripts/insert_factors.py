# scripts/insert_factors.py
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "db" / "pit_factors.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 要插入的因子元数据
factors = [
    ('RU_TS_ROLL_YIELD', '天然橡胶展期收益率', 'SPD', 'TS', 1, 'daily', 'mad', 1),
    ('RU_STK_WARRANT', '上期所RU仓单', 'INV', 'STK', -1, 'daily', 'mad', 1),
    ('RU_INV_QINGDAO', '青岛保税区库存', 'INV', 'STK', -1, 'weekly', 'mad', 1)
]

# 执行插入
cursor.executemany('''
INSERT OR REPLACE INTO factor_metadata 
(factor_code, factor_name, econ_category, logic_category, direction, frequency, norm_method, is_active)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', factors)

conn.commit()
conn.close()
print("✅ 因子元数据插入成功！")