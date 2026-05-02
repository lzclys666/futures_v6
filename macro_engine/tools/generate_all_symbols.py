# scripts/generate_all_symbols.py
"""
批量生成所有期货品种的因子元数据、品种配置和回填数据配置
"""
import sqlite3
import yaml
from pathlib import Path

# ==================== 配置 ====================
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "db" / "pit_factors.db"
INSTRUMENTS_DIR = PROJECT_ROOT / "config" / "instruments"

# 确保目录存在
INSTRUMENTS_DIR.mkdir(parents=True, exist_ok=True)

# ==================== 品种定义 ====================
# 每个品种的因子配置模板
# 因子命名规则: {symbol}_TS_ROLL_YIELD, {symbol}_STK_WARRANT, {symbol}_INV_{库存后缀}

SYMBOL_CONFIGS = {
    # 农产品板块
    "RU": {"name": "天然橡胶", "sector": "农产品", "macro_lambda": 0.35, "stock_suffix": "QINGDAO",
           "warrant_min": 200000, "warrant_max": 250000, "inventory_min": 60, "inventory_max": 80,
           "roll_min": 0.05, "roll_max": 0.15},
    "NR": {"name": "20号胶", "sector": "农产品", "macro_lambda": 0.35, "stock_suffix": "BONDED",
           "warrant_min": 50000, "warrant_max": 100000, "inventory_min": 30, "inventory_max": 50,
           "roll_min": 0.03, "roll_max": 0.10},
    "M": {"name": "豆粕", "sector": "农产品", "macro_lambda": 0.30, "stock_suffix": "PORT",
          "warrant_min": 100000, "warrant_max": 200000, "inventory_min": 50, "inventory_max": 100,
          "roll_min": 0.02, "roll_max": 0.08},
    "RM": {"name": "菜粕", "sector": "农产品", "macro_lambda": 0.30, "stock_suffix": "PORT",
           "warrant_min": 20000, "warrant_max": 50000, "inventory_min": 20, "inventory_max": 40,
           "roll_min": 0.02, "roll_max": 0.08},
    "P": {"name": "棕榈油", "sector": "农产品", "macro_lambda": 0.35, "stock_suffix": "PORT",
          "warrant_min": 100000, "warrant_max": 200000, "inventory_min": 30, "inventory_max": 60,
          "roll_min": 0.03, "roll_max": 0.10},
    "Y": {"name": "豆油", "sector": "农产品", "macro_lambda": 0.35, "stock_suffix": "PORT",
          "warrant_min": 100000, "warrant_max": 200000, "inventory_min": 50, "inventory_max": 80,
          "roll_min": 0.03, "roll_max": 0.10},
    "OI": {"name": "菜籽油", "sector": "农产品", "macro_lambda": 0.35, "stock_suffix": "PORT",
           "warrant_min": 30000, "warrant_max": 80000, "inventory_min": 20, "inventory_max": 40,
           "roll_min": 0.03, "roll_max": 0.10},
    "CF": {"name": "棉花", "sector": "农产品", "macro_lambda": 0.30, "stock_suffix": "WAREHOUSE",
           "warrant_min": 50000, "warrant_max": 100000, "inventory_min": 200, "inventory_max": 400,
           "roll_min": 0.02, "roll_max": 0.08},
    "LH": {"name": "生猪", "sector": "农产品", "macro_lambda": 0.30, "stock_suffix": "SLAUGHTER",
           "warrant_min": 1000, "warrant_max": 5000, "inventory_min": 50, "inventory_max": 100,
           "roll_min": 0.05, "roll_max": 0.15},
    
    # 黑色板块
    "RB": {"name": "螺纹钢", "sector": "黑色", "macro_lambda": 0.45, "stock_suffix": "SOCIAL",
           "warrant_min": 100000, "warrant_max": 150000, "inventory_min": 300, "inventory_max": 500,
           "roll_min": 0.02, "roll_max": 0.08},
    "HC": {"name": "热卷", "sector": "黑色", "macro_lambda": 0.45, "stock_suffix": "SOCIAL",
           "warrant_min": 50000, "warrant_max": 100000, "inventory_min": 200, "inventory_max": 350,
           "roll_min": 0.02, "roll_max": 0.08},
    "I": {"name": "铁矿石", "sector": "黑色", "macro_lambda": 0.40, "stock_suffix": "PORT",
          "warrant_min": 50000, "warrant_max": 100000, "inventory_min": 10000, "inventory_max": 15000,
          "roll_min": 0.03, "roll_max": 0.12},
    "JM": {"name": "焦煤", "sector": "黑色", "macro_lambda": 0.40, "stock_suffix": "PORT",
           "warrant_min": 10000, "warrant_max": 30000, "inventory_min": 200, "inventory_max": 400,
           "roll_min": 0.04, "roll_max": 0.15},
    "J": {"name": "焦炭", "sector": "黑色", "macro_lambda": 0.40, "stock_suffix": "PORT",
          "warrant_min": 5000, "warrant_max": 15000, "inventory_min": 100, "inventory_max": 200,
          "roll_min": 0.04, "roll_max": 0.15},
    
    # 有色金属板块
    "CU": {"name": "沪铜", "sector": "有色", "macro_lambda": 0.60, "stock_suffix": "LME",
           "warrant_min": 50000, "warrant_max": 100000, "inventory_min": 100000, "inventory_max": 200000,
           "roll_min": 0.02, "roll_max": 0.06},
    "AL": {"name": "沪铝", "sector": "有色", "macro_lambda": 0.60, "stock_suffix": "LME",
           "warrant_min": 100000, "warrant_max": 200000, "inventory_min": 500000, "inventory_max": 1000000,
           "roll_min": 0.01, "roll_max": 0.05},
    "ZN": {"name": "沪锌", "sector": "有色", "macro_lambda": 0.60, "stock_suffix": "LME",
           "warrant_min": 20000, "warrant_max": 50000, "inventory_min": 50000, "inventory_max": 100000,
           "roll_min": 0.02, "roll_max": 0.06},
    "SN": {"name": "沪锡", "sector": "有色", "macro_lambda": 0.60, "stock_suffix": "LME",
           "warrant_min": 3000, "warrant_max": 8000, "inventory_min": 3000, "inventory_max": 6000,
           "roll_min": 0.02, "roll_max": 0.08},
    "NI": {"name": "沪镍", "sector": "有色", "macro_lambda": 0.60, "stock_suffix": "LME",
           "warrant_min": 10000, "warrant_max": 30000, "inventory_min": 50000, "inventory_max": 100000,
           "roll_min": 0.03, "roll_max": 0.10},
    "AO": {"name": "氧化铝", "sector": "有色", "macro_lambda": 0.55, "stock_suffix": "PORT",
           "warrant_min": 5000, "warrant_max": 15000, "inventory_min": 20000, "inventory_max": 50000,
           "roll_min": 0.02, "roll_max": 0.08},
    
    # 能化板块
    "SC": {"name": "原油", "sector": "能化", "macro_lambda": 0.65, "stock_suffix": "EIA",
           "warrant_min": 500000, "warrant_max": 1000000, "inventory_min": 400000, "inventory_max": 500000,
           "roll_min": 0.03, "roll_max": 0.12},
    "SA": {"name": "纯碱", "sector": "能化", "macro_lambda": 0.50, "stock_suffix": "FACTORY",
           "warrant_min": 50000, "warrant_max": 100000, "inventory_min": 300, "inventory_max": 600,
           "roll_min": 0.04, "roll_max": 0.15},
    "TA": {"name": "PTA", "sector": "能化", "macro_lambda": 0.50, "stock_suffix": "FACTORY",
           "warrant_min": 100000, "warrant_max": 200000, "inventory_min": 100, "inventory_max": 200,
           "roll_min": 0.03, "roll_max": 0.10},
    "MA": {"name": "甲醇", "sector": "能化", "macro_lambda": 0.50, "stock_suffix": "PORT",
           "warrant_min": 50000, "warrant_max": 100000, "inventory_min": 500, "inventory_max": 1000,
           "roll_min": 0.03, "roll_max": 0.12},
    "FU": {"name": "燃料油", "sector": "能化", "macro_lambda": 0.55, "stock_suffix": "SINGAPORE",
           "warrant_min": 100000, "warrant_max": 200000, "inventory_min": 2000, "inventory_max": 3000,
           "roll_min": 0.04, "roll_max": 0.15},
    "BU": {"name": "沥青", "sector": "能化", "macro_lambda": 0.55, "stock_suffix": "FACTORY",
           "warrant_min": 50000, "warrant_max": 100000, "inventory_min": 500, "inventory_max": 1000,
           "roll_min": 0.03, "roll_max": 0.12},
    "EG": {"name": "乙二醇", "sector": "能化", "macro_lambda": 0.50, "stock_suffix": "PORT",
           "warrant_min": 50000, "warrant_max": 100000, "inventory_min": 500, "inventory_max": 1000,
           "roll_min": 0.03, "roll_max": 0.10},
    "PP": {"name": "聚丙烯", "sector": "能化", "macro_lambda": 0.50, "stock_suffix": "FACTORY",
           "warrant_min": 30000, "warrant_max": 80000, "inventory_min": 200, "inventory_max": 500,
           "roll_min": 0.02, "roll_max": 0.08},
    "L": {"name": "聚乙烯", "sector": "能化", "macro_lambda": 0.50, "stock_suffix": "FACTORY",
          "warrant_min": 30000, "warrant_max": 80000, "inventory_min": 200, "inventory_max": 500,
          "roll_min": 0.02, "roll_max": 0.08},
    "V": {"name": "PVC", "sector": "能化", "macro_lambda": 0.50, "stock_suffix": "FACTORY",
          "warrant_min": 30000, "warrant_max": 80000, "inventory_min": 200, "inventory_max": 500,
          "roll_min": 0.02, "roll_max": 0.08},
    
    # 贵金属板块
    "AU": {"name": "黄金", "sector": "贵金属", "macro_lambda": 0.70, "stock_suffix": "COMEX",
           "warrant_min": 5000, "warrant_max": 10000, "inventory_min": 20000, "inventory_max": 30000,
           "roll_min": 0.01, "roll_max": 0.04},
    "AG": {"name": "白银", "sector": "贵金属", "macro_lambda": 0.70, "stock_suffix": "COMEX",
           "warrant_min": 100000, "warrant_max": 200000, "inventory_min": 200000, "inventory_max": 300000,
           "roll_min": 0.01, "roll_max": 0.05},
}

# 基础权重配置（按板块）
SECTOR_WEIGHTS = {
    "农产品": {"supply": 0.30, "demand": 0.25, "inventory": 0.25, "spread": 0.10, "macro": 0.10},
    "黑色": {"supply": 0.25, "demand": 0.30, "inventory": 0.25, "spread": 0.10, "macro": 0.10},
    "有色": {"supply": 0.20, "demand": 0.30, "inventory": 0.20, "spread": 0.10, "macro": 0.20},
    "能化": {"supply": 0.25, "demand": 0.25, "inventory": 0.20, "spread": 0.15, "macro": 0.15},
    "贵金属": {"supply": 0.10, "demand": 0.15, "inventory": 0.10, "spread": 0.15, "macro": 0.50},
}

# ==================== 1. 插入因子元数据 ====================
def insert_all_factors():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for symbol, config in SYMBOL_CONFIGS.items():
        # 因子1: 展期收益率
        code1 = f"{symbol}_TS_ROLL_YIELD"
        name1 = f"{config['name']}展期收益率"
        # 因子2: 仓单
        code2 = f"{symbol}_STK_WARRANT"
        name2 = f"{config['name']}仓单"
        # 因子3: 库存
        code3 = f"{symbol}_INV_{config['stock_suffix']}"
        name3 = f"{config['name']}库存"
        
        factors = [
            (code1, name1, 'SPD', 'TS', 1, 'daily', 'mad', 1),
            (code2, name2, 'INV', 'STK', -1, 'daily', 'mad', 1),
            (code3, name3, 'INV', 'STK', -1, 'weekly', 'mad', 1),
        ]
        
        for factor in factors:
            try:
                cursor.execute('''
                INSERT OR REPLACE INTO factor_metadata 
                (factor_code, factor_name, econ_category, logic_category, direction, frequency, norm_method, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', factor)
            except Exception as e:
                print(f"  ❌ 插入 {factor[0]} 失败: {e}")
        
        print(f"  ✅ {symbol} 因子元数据已处理")
    
    conn.commit()
    conn.close()
    print("\n✅ 所有因子元数据插入完成！")

# ==================== 2. 生成品种配置文件 ====================
def generate_instrument_configs():
    for symbol, config in SYMBOL_CONFIGS.items():
        sector = config['sector']
        weights = SECTOR_WEIGHTS[sector].copy()
        
        yaml_data = {
            'symbol': symbol,
            'extends': '_base',
            'macro_lambda': config['macro_lambda'],
            'weights': weights,
            'factors': [
                {'code': f"{symbol}_TS_ROLL_YIELD", 'enabled': True, 'weight_override': 0.15},
                {'code': f"{symbol}_STK_WARRANT", 'enabled': True, 'weight_override': 0.15},
                {'code': f"{symbol}_INV_{config['stock_suffix']}", 'enabled': True, 'weight_override': 0.12},
            ]
        }
        
        file_path = INSTRUMENTS_DIR / f"{symbol}.yaml"
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"  ✅ 已生成 {symbol}.yaml")

# ==================== 3. 生成回填脚本的因子配置代码 ====================
def generate_backfill_config():
    print("\n\n" + "="*60)
    print("回填脚本 FACTOR_CONFIG 配置代码（复制到 backfill_history.py）")
    print("="*60)
    print("FACTOR_CONFIG = {")
    for symbol, config in SYMBOL_CONFIGS.items():
        print(f'    "{symbol}": [')
        print(f'        {{"code": "{symbol}_TS_ROLL_YIELD", "min_val": {config["roll_min"]}, "max_val": {config["roll_max"]}}},')
        print(f'        {{"code": "{symbol}_STK_WARRANT", "min_val": {config["warrant_min"]}, "max_val": {config["warrant_max"]}}},')
        print(f'        {{"code": "{symbol}_INV_{config["stock_suffix"]}", "min_val": {config["inventory_min"]}, "max_val": {config["inventory_max"]}}},')
        print(f'    ],')
    print("}")

# ==================== 4. 生成每日评分脚本的品种列表 ====================
def generate_symbol_list():
    print("\n\n" + "="*60)
    print("每日评分脚本 symbols 列表（复制到 daily_scoring.py）")
    print("="*60)
    symbols = list(SYMBOL_CONFIGS.keys())
    print(f"symbols = {symbols}")

# ==================== 主函数 ====================
def main():
    print("="*60)
    print("批量生成所有期货品种配置")
    print("="*60)
    
    print("\n📌 第一步：插入因子元数据到数据库...")
    insert_all_factors()
    
    print("\n📌 第二步：生成品种配置文件（YAML）...")
    generate_instrument_configs()
    
    print("\n📌 第三步：生成回填脚本配置...")
    generate_backfill_config()
    
    print("\n📌 第四步：生成每日评分品种列表...")
    generate_symbol_list()
    
    print("\n" + "="*60)
    print("🎉 全部完成！")
    print("="*60)

if __name__ == "__main__":
    main()