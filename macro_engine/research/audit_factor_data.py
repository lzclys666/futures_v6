#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from config.paths import MACRO_ENGINE
"""
因子数据审计脚本
Factor Data Audit Script

功能：
  1. 扫描所有品种的配置因子定义
  2. 检查对应数据文件是否存在
  3. 评估数据完整度（时间范围、缺失率）
  4. 生成审计报告

用法：
  python audit_factor_data.py

输出：
  str(MACRO_ENGINE)/reports/audit_factor_data_YYYYMMDD.csv
  str(MACRO_ENGINE)/reports/Factor_Data_Readiness_Report_YYYYMMDD.md
"""

import os
import sys
import yaml
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# Windows console UTF-8 fix
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ============ 路径配置 ============
BASE_PATH = Path(r'D:\futures_v6\macro_engine')
CONFIG_PATH = BASE_PATH / 'config' / 'factors'
DATA_PATH = BASE_PATH / 'data' / 'crawlers'
REPORT_PATH = BASE_PATH / 'research' / 'reports'
REPORT_PATH.mkdir(parents=True, exist_ok=True)

# ============ 22个品种列表 ============
ALL_SYMBOLS = [
    'AG', 'AL', 'AO', 'AU', 'BR', 'BU', 'CU', 'EC', 'EG', 'HC',
    'I', 'J', 'JM', 'LC', 'LH', 'M', 'NI', 'NR', 'P', 'PB',
    'PP', 'RB', 'RU', 'SA', 'SC', 'SN', 'TA', 'Y', 'ZN'
]

# ============ 数据文件映射规则 ============
# 根据factor_code前缀和配置文件推断数据文件路径
FACTOR_FILE_PATTERNS = {
    # AG
    'AG_MACRO_GOLD_SILVER_RATIO': '_shared/daily/AU_AG_ratio_corrected.csv',
    'AG_COST_USDCNY': '_shared/daily/USD_CNY_spot.csv',
    'AG_MACRO_DXY': None,  # 需要确认
    'AG_MACRO_US_CPI_YOY': None,  # 需要确认
    'AG_MACRO_US_TIPS_10Y': None,  # 需要确认
    'AG_DEM_ETF_HOLDING': None,  # 需要确认
    'AG_INV_COMEX_SILVER': None,  # 需要确认
    'AG_INV_SHFE_AG': 'AG/daily/AG_fut_close.csv',
    'AG_POS_CFTC_NET': None,  # 需要确认
    'AG_POS_NET': 'AG/daily/AG_fut_close.csv',
    'AG_SPD_BASIS': 'AG/daily/AG_fut_close.csv',
    'AG_SPD_SHFE_COMEX': 'AG/daily/AG_fut_close.csv',
    
    # AU
    'AU_SPD_AUAG': '_shared/daily/AU_AG_ratio_corrected.csv',
    'AU_DXY': '_shared/daily/USD_CNY_spot.csv',
    'AU_US_10Y_YIELD': '_shared/daily/CN_US_bond_yield_full.csv',
    'AU_FED_RATE': None,
    'AU_FED_DOT': None,
    'AU_GOLD_RESERVE_CB': None,
    'AU_SHFE_RANK': 'AU/daily/AU_fut_close.csv',
    'AU_CFTC_NC': None,
    'AU_SPD_BASIS': 'AU/daily/AU_fut_close.csv',
    'AU_SPD_GLD': None,
    'AU_SPOT_SGE': 'AU/daily/AU_SGE_gold_spot.csv',
    
    # AL
    'AL_INV_LME': None,
    'AL_INV_SHFE': None,
    'AL_POS_CONCENTRATION': None,
    'AL_POS_NET': 'AL/daily/AL_fut_close.csv',
    'AL_SPD_AL_CU': 'shared/daily/CU_AL_ratio.csv',
    'AL_SPD_BASIS': 'AL/daily/AL_fut_close.csv',
    'AL_SPD_CONTRACT': 'AL/daily/AL_fut_close.csv',
    'AL_SPD_SHFE_LME': 'AL/daily/AL_fut_close.csv',
    'AL_fut_close': 'AL/daily/AL_fut_close.csv',
    
    # CU
    'CU_LME_SPREAD_DIFF': 'CU/daily/LME_copper_cash_3m_spread.csv',
    'CU_LME_SPREAD': 'CU/daily/LME_copper_cash_3m_spread.csv',
    'CU_LME_SPREAD_EVENT': 'CU/daily/LME_copper_cash_3m_spread.csv',
    'CU_FUT_OI': 'CU/daily/CU_fut_close.csv',
    'CU_POS_NET': 'CU/daily/CU_fut_close.csv',
    'CU_SPD_BASIS': 'CU/daily/CU_fut_close.csv',
    'CU_SPD_CONTRACT': 'CU/daily/CU_fut_close.csv',
    'CU_INV_LME': None,
    'CU_INV_SHFE': None,
    'CU_WRT_SHFE': None,
    'CU_DCE_INV': None,
    
    # JM
    'JM_SPD_BASIS': 'JM/daily/JM03_futures_basis_2026-04-18.csv',
    'JM_SPD_CONTRACT': 'JM/daily/JM02_futures_spread_2026-04-18.csv',
    'JM_SPD_ZC': 'JM/daily/JM10_jm_zc_ratio.csv',
    'JM_SPD_MG_SX': 'JM/daily/JM15_basis_estimated.csv',
    'JM_POS_OI': 'JM/daily/JM04_futures_hold_volume_2026-04-18.csv',
    'JM_COST_COKING_PROFIT': 'JM/daily/JM07_coking_profit_calc.csv',
    'JM_COST_AU_PROFIT': 'JM/daily/JM07_coking_profit_calc.csv',
    'JM_COST_MONGOLIA': None,
    'JM_DEMAND_COKING_RATE': None,
    'JM_DEMAND_HOT_METAL': None,
    'JM_IMPORT': 'JM/monthly/JM06_import_monthly_2026-04-18.csv',
    'JM_INV_COKING_PLANT': None,
    'JM_INV_GQMD': 'JM/daily/JM03_gqmd_crossing_cars.csv',
    'JM_INV_STEEL_PLANT': None,
    'JM_INV_THREE_PORTS': None,
    'JM_SUPPLY_GQMD_CARS': 'JM/daily/JM03_gqmd_crossing_cars.csv',
    'JM_SUPPLY_MINE_RATE': None,
    'JM_SUPPLY_WASHED_OUTPUT': None,
    'JM01_futures_ohlcv': 'JM/daily/JM01_futures_ohlcv_2026-04-18.csv',
    'JM02_futures_spread': 'JM/daily/JM02_futures_spread_2026-04-18.csv',
    'JM03_futures_basis': 'JM/daily/JM03_futures_basis_2026-04-18.csv',
    'JM04_futures_hold_volume': 'JM/daily/JM04_futures_hold_volume_2026-04-18.csv',
    'JM05_basis_volatility': 'JM/daily/JM05_basis_volatility_2026-04-18.csv',
    
    # NI
    'NI_LME_SPREAD_DIFF': 'NI/daily/LME_nickel_cash_3m_spread.csv',
    'NI_fut_close': 'NI/daily/NI_fut_close.csv',
    'NI_LME_3M_CLOSE': 'NI/daily/LME_nickel_cash_3m_spread.csv',
    'NI_LME_3M_SPREAD': 'NI/daily/LME_nickel_cash_3m_spread.csv',
    
    # ZN
    'ZN_fut_close': 'ZN/daily/ZN_fut_close.csv',
    'ZN_FUT_OI': 'ZN/daily/ZN_fut_close.csv',
    'ZN_DCE_INV': None,
    'ZN_LME_3M': 'ZN/daily/ZN_LME_3M.csv',
    
    # PB
    'PB_LME_3M': 'PB/daily/PB_LME_3M.csv',
    
    # SN
    'SN_LME_3M': 'SN/daily/SN_LME_3M.csv',
    
    # Shared
    'BRENT_CRUDE': '_shared/daily/Brent_crude.csv',
    'CN_10Y_YIELD': '_shared/daily/CN_US_bond_yield_full.csv',
    'USD_CNY': '_shared/daily/USD_CNY_spot.csv',
    
    # Generic mappings for common patterns
    '_fut_close': 'daily/{symbol}_fut_close.csv',
    '_FUT_CLOSE': 'daily/{symbol}_fut_close.csv',
    '_FUT_OI': 'daily/{symbol}_fut_close.csv',
    '_SPD_BASIS': 'daily/{symbol}_fut_close.csv',
}

def scan_factor_configs():
    """扫描所有品种的配置因子定义"""
    results = []
    
    for symbol in ALL_SYMBOLS:
        symbol_config_path = CONFIG_PATH / symbol
        if not symbol_config_path.exists():
            results.append({
                'symbol': symbol,
                'factor_code': 'N/A',
                'factor_name': 'N/A',
                'config_exists': False,
                'data_file': None,
                'data_exists': False,
                'data_rows': 0,
                'date_range': None,
                'missing_rate': 1.0,
                'status': 'NO_CONFIG'
            })
            continue
        
        config_files = list(symbol_config_path.glob('*.yaml'))
        if not config_files:
            results.append({
                'symbol': symbol,
                'factor_code': 'N/A',
                'factor_name': 'N/A',
                'config_exists': True,
                'data_file': None,
                'data_exists': False,
                'data_rows': 0,
                'date_range': None,
                'missing_rate': 1.0,
                'status': 'NO_FACTORS'
            })
            continue
        
        for config_file in config_files:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                factor_code = config.get('factor_code', config_file.stem)
                factor_name = config.get('factor_name', config.get('name', 'Unknown'))
                
                # 查找对应的数据文件
                data_file = FACTOR_FILE_PATTERNS.get(factor_code)
                
                # 尝试通用匹配
                if not data_file:
                    for suffix, pattern in FACTOR_FILE_PATTERNS.items():
                        if suffix.startswith('_') and factor_code.endswith(suffix):
                            data_file = pattern.replace('{symbol}', symbol)
                            break
                
                # 自动推断：检查品种目录下是否存在常见数据文件
                if not data_file:
                    symbol_daily_path = DATA_PATH / symbol / 'daily'
                    if symbol_daily_path.exists():
                        # 查找包含fut_close的文件
                        fut_files = list(symbol_daily_path.glob('*fut_close*.csv'))
                        if fut_files:
                            data_file = str(fut_files[0].relative_to(DATA_PATH)).replace('\\', '/')
                
                data_exists = False
                data_rows = 0
                date_range = None
                missing_rate = 1.0
                
                if data_file:
                    full_path = DATA_PATH / data_file
                    # 如果路径不存在，尝试在品种目录下查找
                    if not full_path.exists() and '{symbol}' not in str(data_file):
                        alt_path = DATA_PATH / symbol / data_file
                        if alt_path.exists():
                            full_path = alt_path
                    if full_path.exists():
                        data_exists = True
                        try:
                            # 尝试读取CSV获取统计信息
                            df = pd.read_csv(full_path)
                            data_rows = len(df)
                            if 'date' in df.columns:
                                df['date'] = pd.to_datetime(df['date'])
                                date_min = df['date'].min().strftime('%Y-%m-%d')
                                date_max = df['date'].max().strftime('%Y-%m-%d')
                                date_range = f"{date_min} ~ {date_max}"
                                
                                # 计算缺失率（基于交易日）
                                total_days = (df['date'].max() - df['date'].min()).days
                                if total_days > 0:
                                    missing_rate = 1.0 - (data_rows / total_days)
                        except Exception as e:
                            print(f"  Warning: Error reading {full_path}: {e}")
                
                # 确定状态
                if not data_exists:
                    status = 'MISSING_DATA'
                elif data_rows < 30:
                    status = 'INSUFFICIENT_DATA'
                elif missing_rate > 0.5:
                    status = 'HIGH_MISSING'
                else:
                    status = 'OK'
                
                results.append({
                    'symbol': symbol,
                    'factor_code': factor_code,
                    'factor_name': factor_name,
                    'config_exists': True,
                    'data_file': data_file,
                    'data_exists': data_exists,
                    'data_rows': data_rows,
                    'date_range': date_range,
                    'missing_rate': missing_rate,
                    'status': status
                })
                
            except Exception as e:
                print(f"Error processing {config_file}: {e}")
                results.append({
                    'symbol': symbol,
                    'factor_code': config_file.stem,
                    'factor_name': 'ERROR',
                    'config_exists': True,
                    'data_file': None,
                    'data_exists': False,
                    'data_rows': 0,
                    'date_range': None,
                    'missing_rate': 1.0,
                    'status': 'CONFIG_ERROR'
                })
    
    return pd.DataFrame(results)

def generate_report(df):
    """生成审计报告"""
    today = datetime.now().strftime('%Y%m%d')
    
    # 保存CSV
    csv_path = REPORT_PATH / f'audit_factor_data_{today}.csv'
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"✅ CSV报告已保存: {csv_path}")
    
    # 生成Markdown报告
    md_path = REPORT_PATH / f'Factor_Data_Readiness_Report_{today}.md'
    
    # 统计信息
    total_factors = len(df)
    ok_factors = len(df[df['status'] == 'OK'])
    missing_data = len(df[df['status'] == 'MISSING_DATA'])
    insufficient = len(df[df['status'] == 'INSUFFICIENT_DATA'])
    high_missing = len(df[df['status'] == 'HIGH_MISSING'])
    no_config = len(df[df['status'] == 'NO_CONFIG'])
    config_error = len(df[df['status'] == 'CONFIG_ERROR'])
    
    # 按品种统计
    symbol_stats = df.groupby('symbol').agg({
        'factor_code': 'count',
        'status': lambda x: (x == 'OK').sum()
    }).rename(columns={'factor_code': 'total', 'status': 'ok_count'})
    symbol_stats['completeness'] = (symbol_stats['ok_count'] / symbol_stats['total'] * 100).round(1)
    symbol_stats = symbol_stats.sort_values('completeness', ascending=False)
    
    md_content = f"""# 因子数据就绪审计报告

> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  
> **审计范围**: 22品种 × 配置因子  
> **数据路径**: `{DATA_PATH}`  

---

## 一、总体统计

| 指标 | 数值 | 占比 |
|------|------|------|
| **总因子数** | {total_factors} | 100% |
| **数据完整 (OK)** | {ok_factors} | {ok_factors/total_factors*100:.1f}% |
| **数据缺失 (MISSING_DATA)** | {missing_data} | {missing_data/total_factors*100:.1f}% |
| **数据不足 (INSUFFICIENT_DATA)** | {insufficient} | {insufficient/total_factors*100:.1f}% |
| **缺失率高 (HIGH_MISSING)** | {high_missing} | {high_missing/total_factors*100:.1f}% |
| **无配置 (NO_CONFIG)** | {no_config} | {no_config/total_factors*100:.1f}% |
| **配置错误 (CONFIG_ERROR)** | {config_error} | {config_error/total_factors*100:.1f}% |

**核心因子完整度**: {ok_factors/total_factors*100:.1f}%  
**目标**: ≥ 70%  
**状态**: {'✅ 达标' if ok_factors/total_factors >= 0.7 else '❌ 未达标'}

---

## 二、分品种完整度

| 品种 | 配置因子数 | 数据完整数 | 完整度 |
|------|-----------|-----------|--------|
"""
    
    for symbol, row in symbol_stats.iterrows():
        status_icon = '✅' if row['completeness'] >= 70 else '🟡' if row['completeness'] >= 40 else '❌'
        md_content += f"| {symbol} | {row['total']} | {row['ok_count']} | {status_icon} {row['completeness']}% |\n"
    
    md_content += f"""
---

## 三、数据缺失详情

### 3.1 数据文件缺失的因子

| 品种 | 因子代码 | 因子名称 | 期望数据文件 |
|------|---------|---------|------------|
"""
    
    missing_df = df[df['status'] == 'MISSING_DATA']
    for _, row in missing_df.iterrows():
        md_content += f"| {row['symbol']} | {row['factor_code']} | {row['factor_name']} | {row['data_file'] or '未映射'} |\n"
    
    md_content += f"""
### 3.2 数据量不足的因子

| 品种 | 因子代码 | 数据行数 | 日期范围 |
|------|---------|---------|---------|
"""
    
    insuff_df = df[df['status'] == 'INSUFFICIENT_DATA']
    for _, row in insuff_df.iterrows():
        md_content += f"| {row['symbol']} | {row['factor_code']} | {row['data_rows']} | {row['date_range'] or 'N/A'} |\n"
    
    md_content += f"""
---

## 四、数据文件映射待确认

以下因子尚未建立数据文件映射关系，需要人工确认：

| 品种 | 因子代码 | 因子名称 |
|------|---------|---------|
"""
    
    unmapped_df = df[(df['data_file'].isna()) & (df['status'] != 'NO_CONFIG') & (df['status'] != 'CONFIG_ERROR')]
    for _, row in unmapped_df.iterrows():
        md_content += f"| {row['symbol']} | {row['factor_code']} | {row['factor_name']} |\n"
    
    md_content += f"""
---

## 五、下一步行动

1. **立即修复**: 补充数据文件缺失的因子（{missing_data}个）
2. **短期修复**: 增加数据量不足的因子历史数据（{insufficient}个）
3. **映射完善**: 确认未映射因子的数据文件路径（{len(unmapped_df)}个）
4. **质量提升**: 降低高缺失率因子的缺失比例（{high_missing}个）

---

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"✅ Markdown报告已保存: {md_path}")
    
    return csv_path, md_path

def main():
    print("=" * 60)
    print("因子数据审计脚本")
    print("Factor Data Audit")
    print("=" * 60)
    print(f"\n配置路径: {CONFIG_PATH}")
    print(f"数据路径: {DATA_PATH}")
    print(f"报告路径: {REPORT_PATH}")
    print()
    
    # 扫描配置
    print("🔍 扫描因子配置...")
    df = scan_factor_configs()
    
    # 生成报告
    print("\n📊 生成审计报告...")
    csv_path, md_path = generate_report(df)
    
    # 打印摘要
    print("\n" + "=" * 60)
    print("审计摘要")
    print("=" * 60)
    
    total = len(df)
    ok = len(df[df['status'] == 'OK'])
    missing = len(df[df['status'] == 'MISSING_DATA'])
    
    print(f"总因子数: {total}")
    print(f"数据完整: {ok} ({ok/total*100:.1f}%)")
    print(f"数据缺失: {missing} ({missing/total*100:.1f}%)")
    print(f"\n核心因子完整度: {ok/total*100:.1f}%")
    print(f"目标: ≥ 70%")
    print(f"状态: {'✅ 达标' if ok/total >= 0.7 else '❌ 未达标'}")
    
    print("\n" + "=" * 60)
    print("审计完成")
    print("=" * 60)

if __name__ == '__main__':
    main()
