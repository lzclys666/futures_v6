"""IC分析：计算各因子与未来收益的相关系数"""
import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import pearsonr

BASE = Path(r"C:\futures_data\macro_signals")

def compute_ic_for_symbol(symbol: str, forward_days: int = 1) -> dict:
    """计算某品种各因子的IC（前向收益相关性）"""
    files = sorted(BASE.glob(f"{symbol}_macro_daily_*.csv"))
    if len(files) < 5:
        return {}

    # 读取所有FACTOR行
    records = []
    for f in files:
        df = pd.read_csv(f)
        df = df[df['row_type'] == 'FACTOR']
        for _, row in df.iterrows():
            if pd.notna(row['factor_code']) and str(row['factor_code']) != 'nan':
                records.append({
                    'date': row['date'],
                    'factor_code': row['factor_code'],
                    'composite_score': row['composite_score'],
                    'normalized_score': row['normalized_score'],
                })

    if not records:
        return {}

    data = pd.DataFrame(records)
    data = data.sort_values('date')

    # 先算每天的 composite_score（所有因子共享同一个值）
    date_score = data.groupby('date')['composite_score'].first().reset_index()
    date_score = date_score.sort_values('date')
    date_score['fwd_ret'] = date_score['composite_score'].shift(-forward_days) - date_score['composite_score']
    date_score = date_score.dropna(subset=['fwd_ret'])
    date_score = date_score[['date', 'fwd_ret']]

    # 合并前向收益到因子数据
    data = data.merge(date_score, on='date', how='inner')

    # 计算每个因子的IC
    results = {}
    for fc in data['factor_code'].unique():
        fc_data = data[data['factor_code'] == fc].dropna(subset=['normalized_score', 'fwd_ret'])
        if len(fc_data) >= 5:
            try:
                ic, pval = pearsonr(fc_data['normalized_score'], fc_data['fwd_ret'])
                results[fc] = {'ic': ic, 'pval': pval, 'n': len(fc_data)}
            except Exception:
                pass

    return results

for symbol in ['RU', 'CU', 'AU', 'AG']:
    print(f"\n{'='*60}")
    print(f"{symbol} IC Analysis (forward=1 day)")
    print(f"{'='*60}")
    ic_data = compute_ic_for_symbol(symbol)
    if not ic_data:
        print("  No sufficient data")
        continue

    sorted_ic = sorted(ic_data.items(), key=lambda x: abs(x[1]['ic']), reverse=True)
    for fc, vals in sorted_ic:
        ic = vals['ic']
        pval = vals['pval']
        n = vals['n']
        sig = '***' if pval < 0.01 else '**' if pval < 0.05 else '*' if pval < 0.1 else ''
        print(f"  {fc:<25} IC={ic:+.4f}  p={pval:.4f}  n={n:3d} {sig}")
