"""
IC窗口评估脚本
评估每个品种/因子组合的有效IC序列长度
"""

import os
import pandas as pd
from pathlib import Path
from datetime import datetime
import warnings
import sys
warnings.filterwarnings('ignore')

# Windows console UTF-8 fix
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DATA_PATH = Path(r'D:\futures_v6\macro_engine\data\crawlers')
REPORT_PATH = Path(r'D:\futures_v6\macro_engine\research\reports')
REPORT_PATH.mkdir(parents=True, exist_ok=True)

VARIETIES = ['AG', 'AL', 'AU', 'BR', 'BU', 'CU', 'EC', 'EG', 'HC', 'I', 
             'J', 'JM', 'LC', 'LH', 'M', 'NI', 'NR', 'P', 'PB', 'PP', 
             'RB', 'RU', 'SA', 'SC', 'SN', 'TA', 'Y', 'ZN']

IC_WINDOW_MIN = 60  # 最小IC窗口要求
HOLD_PERIODS = [5, 10, 20]  # 持有期

def scan_ic_windows():
    """扫描每个品种的数据文件，评估IC窗口长度"""
    results = []
    
    for sym in VARIETIES:
        sym_path = DATA_PATH / sym
        if not sym_path.exists():
            results.append({
                '品种': sym,
                '数据文件': 'N/A',
                '价格行数': 0,
                '可用IC窗口': '❌ 无数据',
                '5日IC窗口': 0,
                '10日IC窗口': 0,
                '20日IC窗口': 0,
                'IC充足': '❌'
            })
            continue
        
        files = list(sym_path.rglob('*.csv'))
        
        # 找价格文件（fut_close优先）
        price_file = None
        for f in files:
            if 'fut_close' in f.name.lower():
                price_file = f
                break
        
        if not price_file:
            # 找任意csv
            for f in files:
                price_file = f
                break
        
        if not price_file:
            results.append({
                '品种': sym,
                '数据文件': '无CSV文件',
                '价格行数': 0,
                '可用IC窗口': '❌ 无数据',
                '5日IC窗口': 0,
                '10日IC窗口': 0,
                '20日IC窗口': 0,
                'IC充足': '❌'
            })
            continue
        
        try:
            df = pd.read_csv(price_file)
            
            # 找日期列
            date_col = None
            for col in df.columns:
                if 'date' in col.lower():
                    date_col = col
                    break
            
            if date_col:
                df[date_col] = pd.to_datetime(df[date_col])
                df = df.sort_values(date_col)
                df = df.set_index(date_col)
            
            # 找数值列（排除date列）
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            
            if not numeric_cols:
                results.append({
                    '品种': sym,
                    '数据文件': price_file.name,
                    '价格行数': len(df),
                    '可用IC窗口': '⚠️ 无数值列',
                    '5日IC窗口': 0,
                    '10日IC窗口': 0,
                    '20日IC窗口': 0,
                    'IC充足': '❌'
                })
                continue
            
            # 用第一列计算IC窗口
            price_col = numeric_cols[0]
            price_series = df[price_col].dropna()
            n_rows = len(price_series)
            
            # IC窗口 = 总行数 - 持有期 - IC窗口
            ic_windows = {}
            ic_ok = {}
            for hold in HOLD_PERIODS:
                ic_window = n_rows - hold - IC_WINDOW_MIN
                ic_windows[hold] = max(0, ic_window)
                ic_ok[hold] = ic_windows[hold] >= 30  # 至少需要30天
            
            # 总体评估
            if n_rows == 0:
                ic_status = '❌ 无数据'
            elif all(ic_ok.values()):
                ic_status = '✅ 充足'
            elif any(ic_ok.values()):
                ic_status = '🟡 部分充足'
            else:
                ic_status = '❌ 不足'
            
            results.append({
                '品种': sym,
                '数据文件': price_file.name,
                '价格行数': n_rows,
                '可用IC窗口': ic_status,
                '5日IC窗口': ic_windows[5],
                '10日IC窗口': ic_windows[10],
                '20日IC窗口': ic_windows[20],
                'IC充足': '✅' if all(ic_ok.values()) else ('🟡' if any(ic_ok.values()) else '❌')
            })
            
        except Exception as e:
            results.append({
                '品种': sym,
                '数据文件': price_file.name if price_file else 'N/A',
                '价格行数': 0,
                '可用IC窗口': f'❌ 错误: {str(e)[:30]}',
                '5日IC窗口': 0,
                '10日IC窗口': 0,
                '20日IC窗口': 0,
                'IC充足': '❌'
            })
    
    return pd.DataFrame(results)

def main():
    print("=" * 60)
    print("IC窗口评估")
    print("=" * 60)
    
    results_df = scan_ic_windows()
    
    # 保存CSV
    today = datetime.now().strftime('%Y%m%d')
    csv_path = REPORT_PATH / f'audit_ic_window_{today}.csv'
    results_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"✅ IC窗口报告已保存: {csv_path}")
    
    # 打印摘要
    print("\n" + "=" * 60)
    print("IC窗口评估摘要")
    print("=" * 60)
    
    ok_count = len(results_df[results_df['IC充足'] == '✅'])
    partial_count = len(results_df[results_df['IC充足'] == '🟡'])
    fail_count = len(results_df[results_df['IC充足'] == '❌'])
    
    print(f"\n总品种数: {len(results_df)}")
    print(f"IC窗口充足: {ok_count} ✅")
    print(f"IC窗口部分充足: {partial_count} 🟡")
    print(f"IC窗口不足: {fail_count} ❌")
    
    print("\n--- 各品种详情 ---")
    print(results_df[['品种', '价格行数', '5日IC窗口', '10日IC窗口', '20日IC窗口', 'IC充足']].to_string(index=False))
    
    return results_df

if __name__ == '__main__':
    main()
