"""
CU 扩大样本重测脚本
测试多个因子的IC有效性
"""

import pandas as pd
import numpy as np
from scipy import stats
import os
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("CU 扩大样本重测")
print("=" * 80)

# ============================================================
# 1. 加载所有可用数据
# ============================================================

DATA_PATH = r'D:\futures_v6\macro_engine\data\crawlers'

def load_data():
    """加载所有CU相关数据"""
    data = {}
    
    # CU价格数据
    cu_price_path = os.path.join(DATA_PATH, 'CU', 'daily', 'CU_fut_close.csv')
    if os.path.exists(cu_price_path):
        df = pd.read_csv(cu_price_path)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        data['CU_price'] = df['close']
        print(f"[OK] CU价格: {len(df)} 行, {df.index[0].date()} ~ {df.index[-1].date()}")
    
    # LME铜价
    lme_path = os.path.join(DATA_PATH, 'CU', 'daily', 'LME_copper_cash_3m_spread.csv')
    if os.path.exists(lme_path):
        df = pd.read_csv(lme_path)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        # 尝试找到LME相关列
        for col in df.columns:
            if 'lme' in col.lower() or 'copper' in col.lower() or 'close' in col.lower() or 'cash' in col.lower():
                data['LME_copper'] = df[col]
                print(f"[OK] LME铜: {len(df)} 行, 列名={col}")
                break
        else:
            # 取最后一列
            data['LME_copper'] = df.iloc[:, -1]
            print(f"[OK] LME铜: {len(df)} 行, 列名={df.columns[-1]}")
    
    # CU/AL比价
    ratio_path = os.path.join(DATA_PATH, 'shared', 'daily', 'CU_AL_ratio.csv')
    if os.path.exists(ratio_path):
        df = pd.read_csv(ratio_path)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        # 找到比价列
        for col in df.columns:
            if 'ratio' in col.lower() or 'al' in col.lower() or 'cu' in col.lower():
                data['CU_AL_ratio'] = df[col]
                print(f"[OK] CU/AL比价: {len(df)} 行, 列名={col}")
                break
        else:
            data['CU_AL_ratio'] = df.iloc[:, -1]
            print(f"[OK] CU/AL比价: {len(df)} 行, 列名={df.columns[-1]}")
    
    # CU现货价
    spot_path = os.path.join(DATA_PATH, 'CU', 'daily', 'basis.csv')
    if os.path.exists(spot_path):
        df = pd.read_csv(spot_path)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        # 尝试找现货价列
        for col in df.columns:
            if 'spot' in col.lower() or 'cash' in col.lower() or 'price' in col.lower():
                data['CU_spot'] = df[col]
                print(f"[OK] CU现货: {len(df)} 行, 列名={col}")
                break
        else:
            data['CU_spot'] = df.iloc[:, -1]
            print(f"[OK] CU现货: {len(df)} 行, 列名={df.columns[-1]}")
    
    # 宏观因子
    usd_path = os.path.join(DATA_PATH, '_shared', 'daily', 'USD_CNY_spot.csv')
    if os.path.exists(usd_path):
        df = pd.read_csv(usd_path)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        for col in df.columns:
            if 'usd' in col.lower() or 'cny' in col.lower():
                data['USD_CNY'] = df[col]
                print(f"[OK] USD/CNY: {len(df)} 行, 列名={col}")
                break
    
    cn10y_path = os.path.join(DATA_PATH, '_shared', 'daily', 'CN_US_bond_yield_full.csv')
    if os.path.exists(cn10y_path):
        df = pd.read_csv(cn10y_path)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        for col in df.columns:
            if 'cn10y' in col.lower() or 'china 10y' in col.lower():
                data['CN10Y'] = df[col]
                print(f"[OK] CN10Y: {len(df)} 行, 列名={col}")
                break
    
    return data

# ============================================================
# 2. 计算IC
# ============================================================

def compute_ic(factor, price, hold_period=5, ic_window=60):
    """
    计算IC（Information Coefficient）
    
    Args:
        factor: 因子序列
        price: 价格序列
        hold_period: 持有期（天）
        ic_window: 计算窗口（天）
    
    Returns:
        ic_series: 滚动IC序列
    """
    # 对齐数据
    aligned = pd.DataFrame({'factor': factor, 'price': price}).dropna()
    
    if len(aligned) < ic_window + hold_period:
        return pd.Series(), 0.0, 0.0, 0.0
    
    # 计算前瞻收益
    aligned['forward_return'] = aligned['price'].pct_change(hold_period).shift(-hold_period)
    aligned = aligned.dropna()
    
    if len(aligned) < ic_window:
        return pd.Series(), 0.0, 0.0, 0.0
    
    # 计算滚动IC
    ic_values = []
    dates = []
    
    for i in range(ic_window, len(aligned)):
        window = aligned.iloc[i-ic_window:i]
        future = aligned.iloc[i]['forward_return']
        
        if window['factor'].std() == 0 or window['forward_return'].std() == 0:
            ic = 0
        else:
            ic, _ = stats.spearmanr(window['factor'], window['forward_return'])
        
        if np.isnan(ic):
            ic = 0
        
        ic_values.append(ic)
        dates.append(aligned.index[i])
    
    ic_series = pd.Series(ic_values, index=dates)
    
    # 计算统计量
    ic_mean = np.mean(ic_values)
    ic_std = np.std(ic_values)
    ir = ic_mean / ic_std if ic_std > 0 else 0
    
    # 计算t统计量
    n = len(ic_values)
    t_stat = ic_mean / (ic_std / np.sqrt(n)) if ic_std > 0 else 0
    
    # 计算胜率
    win_rate = np.mean([1 if ic > 0 else 0 for ic in ic_values])
    
    return ic_series, ic_mean, ir, t_stat, win_rate

# ============================================================
# 3. 主程序
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("Step 1: 加载数据")
    print("=" * 80)
    
    data = load_data()
    
    if 'CU_price' not in data:
        print("[ERROR] 未找到CU价格数据")
        exit(1)
    
    cu_price = data['CU_price']
    
    print("\n" + "=" * 80)
    print("Step 2: 计算各因子IC")
    print("=" * 80)
    
    # 定义测试的因子
    factors_to_test = [
        ('CU_price', 'CU价格（自身）'),
        ('CU_spot', 'CU现货价'),
        ('LME_copper', 'LME铜价'),
        ('CU_AL_ratio', 'CU/AL比价'),
        ('USD_CNY', 'USD/CNY'),
        ('CN10Y', 'CN10Y国债'),
    ]
    
    results = []
    hold_periods = [5, 10, 20]
    
    for factor_name, factor_desc in factors_to_test:
        if factor_name not in data:
            print(f"\n[WARN] 跳过 {factor_desc}: 数据不可用")
            continue
        
        print(f"\n--- {factor_desc} ({factor_name}) ---")
        
        factor = data[factor_name]
        
        for hold in hold_periods:
            ic_series, ic_mean, ir, t_stat, win_rate = compute_ic(
                factor, cu_price, 
                hold_period=hold, 
                ic_window=60
            )
            
            if len(ic_series) == 0:
                continue
            
            print(f"  持有期={hold}日: IC={ic_mean:+.4f}, IR={ir:+.4f}, t={t_stat:+.2f}, 胜率={win_rate:.1%}")
            
            results.append({
                'factor': factor_name,
                'factor_desc': factor_desc,
                'hold_period': hold,
                'ic_mean': ic_mean,
                'ir': ir,
                't_stat': t_stat,
                'win_rate': win_rate,
                'sample_size': len(ic_series)
            })
    
    print("\n" + "=" * 80)
    print("Step 3: 结果汇总")
    print("=" * 80)
    
    if results:
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('ic_mean', key=abs, ascending=False)
        
        print("\n按|IC|排序:")
        print(results_df.to_string(index=False))
        
        # 保存结果
        output_path = r'D:\futures_v6\macro_engine\research\reports\CU_expanded_IC_20260427.csv'
        results_df.to_csv(output_path, index=False)
        print(f"\n[OK] 结果已保存: {output_path}")
    
    print("\n" + "=" * 80)
    print("CU 扩大样本重测完成")
    print("=" * 80)
