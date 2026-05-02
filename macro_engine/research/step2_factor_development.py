import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import akshare as ak
import os
from datetime import datetime

print("=" * 80)
print("第二步：开发新因子 + 测试反转信号")
print("=" * 80)

# ============================================================
# 1. AU - 开发美元指数/实际利率因子
# ============================================================

print("\n[1] AU - 开发美元指数/实际利率因子...")

class AUFactorDeveloper:
    """AU黄金新因子开发"""
    
    def __init__(self):
        self.data_path = r'D:\futures_v6\macro_engine\data\crawlers'
    
    def load_usd_index(self):
        """加载美元指数数据"""
        try:
            # 从AKShare获取美元指数
            df = ak.fx_spot_quote()
            if 'USD' in df.columns:
                usd = df[['date', 'USD']].copy()
                usd['date'] = pd.to_datetime(usd['date'])
                usd = usd.set_index('date').sort_index()
                return usd['USD']
        except:
            pass
        
        # 备用：从本地文件加载
        usd_path = os.path.join(self.data_path, '_shared', 'daily', 'USD_index.csv')
        if os.path.exists(usd_path):
            df = pd.read_csv(usd_path)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()
            return df['close']
        
        return None
    
    def load_us_bond_yield(self):
        """加载美国国债收益率"""
        try:
            # 从AKShare获取美债收益率
            df = ak.bond_zh_us_rate()
            if '美国10年期国债' in df.columns:
                us_10y = df[['日期', '美国10年期国债']].copy()
                us_10y.columns = ['date', 'US_10Y']
                us_10y['date'] = pd.to_datetime(us_10y['date'])
                us_10y = us_10y.set_index('date').sort_index()
                return us_10y['US_10Y']
        except:
            pass
        
        # 备用：从本地文件加载
        bond_path = os.path.join(self.data_path, '_shared', 'daily', 'CN_US_bond_yield_full.csv')
        if os.path.exists(bond_path):
            df = pd.read_csv(bond_path)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()
            return df['us_10y']
        
        return None
    
    def load_gold_price(self):
        """加载黄金价格"""
        gold_path = os.path.join(self.data_path, 'AU', 'daily', 'AU_fut_close.csv')
        if os.path.exists(gold_path):
            df = pd.read_csv(gold_path)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()
            return df['close']
        return None
    
    def compute_ic(self, factor, forward_return, ic_window=60):
        """计算IC"""
        aligned = pd.DataFrame({'factor': factor, 'return': forward_return}).dropna()
        
        if len(aligned) < ic_window + 10:
            return None, None, None
        
        ic_list = []
        for i in range(ic_window, len(aligned)):
            fac_window = aligned['factor'].iloc[i-ic_window:i]
            ret_window = aligned['return'].iloc[i-ic_window:i]
            
            if len(fac_window) < 20:
                continue
            
            ic, _ = spearmanr(fac_window, ret_window)
            if not np.isnan(ic):
                ic_list.append(ic)
        
        if ic_list:
            ic_mean = np.mean(ic_list)
            ic_std = np.std(ic_list)
            ir = ic_mean / ic_std if ic_std > 0 else 0
            win_rate = np.mean([ic > 0 for ic in ic_list])
            return ic_mean, ir, win_rate
        
        return None, None, None
    
    def test_usd_factor(self):
        """测试美元指数因子"""
        print("\n  [1.1] 测试美元指数因子...")
        
        usd = self.load_usd_index()
        gold = self.load_gold_price()
        
        if usd is None or gold is None:
            print("  [FAIL] 数据不足，无法测试")
            return None
        
        # 对齐数据
        aligned = pd.DataFrame({'usd': usd, 'gold': gold}).dropna()
        
        if len(aligned) < 100:
            print(f"  [FAIL] 对齐后数据不足: {len(aligned)} 行")
            return None
        
        # 美元指数变化率（负相关预期：美元涨→黄金跌）
        aligned['usd_change'] = aligned['usd'].pct_change(5)
        aligned['gold_return'] = aligned['gold'].pct_change(10).shift(-10)
        
        # 计算IC
        ic_mean, ir, win_rate = self.compute_ic(
            aligned['usd_change'], 
            aligned['gold_return'],
            ic_window=60
        )
        
        if ic_mean is not None:
            print(f"  [OK] 美元指数因子:")
            print(f"    IC均值: {ic_mean:.4f}")
            print(f"    IR: {ir:.4f}")
            print(f"    胜率: {win_rate:.2%}")
            
            return {
                'factor': 'USD_index',
                'ic_mean': ic_mean,
                'ir': ir,
                'win_rate': win_rate,
                'direction': 'negative'  # 负相关
            }
        
        return None
    
    def test_real_rate_factor(self):
        """测试实际利率因子"""
        print("\n  [1.2] 测试实际利率因子...")
        
        us_10y = self.load_us_bond_yield()
        gold = self.load_gold_price()
        
        if us_10y is None or gold is None:
            print("  [FAIL] 数据不足，无法测试")
            return None
        
        # 对齐数据
        aligned = pd.DataFrame({'us_10y': us_10y, 'gold': gold}).dropna()
        
        if len(aligned) < 100:
            print(f"  [FAIL] 对齐后数据不足: {len(aligned)} 行")
            return None
        
        # 实际利率变化（负相关预期：利率涨→黄金跌）
        aligned['rate_change'] = aligned['us_10y'].diff(5)
        aligned['gold_return'] = aligned['gold'].pct_change(10).shift(-10)
        
        # 计算IC
        ic_mean, ir, win_rate = self.compute_ic(
            aligned['rate_change'], 
            aligned['gold_return'],
            ic_window=60
        )
        
        if ic_mean is not None:
            print(f"  [OK] 实际利率因子:")
            print(f"    IC均值: {ic_mean:.4f}")
            print(f"    IR: {ir:.4f}")
            print(f"    胜率: {win_rate:.2%}")
            
            return {
                'factor': 'real_rate',
                'ic_mean': ic_mean,
                'ir': ir,
                'win_rate': win_rate,
                'direction': 'negative'
            }
        
        return None
    
    def run(self):
        """运行AU因子开发"""
        print("\n" + "-" * 80)
        print("AU黄金 - 新因子开发")
        print("-" * 80)
        
        results = []
        
        # 测试美元指数因子
        usd_result = self.test_usd_factor()
        if usd_result:
            results.append(usd_result)
        
        # 测试实际利率因子
        rate_result = self.test_real_rate_factor()
        if rate_result:
            results.append(rate_result)
        
        # 选择最优因子
        if results:
            best = max(results, key=lambda x: x['ir'])
            print(f"\n  [BEST] 最优因子: {best['factor']}")
            print(f"    IR: {best['ir']:.4f}")
            print(f"    IC均值: {best['ic_mean']:.4f}")
            
            return best
        
        print("\n  [FAIL] 所有因子测试失败")
        return None


# ============================================================
# 2. M - 开发季节性因子
# ============================================================

class MFactorDeveloper:
    """M豆粕季节性因子开发"""
    
    def __init__(self):
        self.data_path = r'D:\futures_v6\macro_engine\data\crawlers'
    
    def load_m_price(self):
        """加载豆粕价格"""
        m_path = os.path.join(self.data_path, 'M', 'daily', 'M_fut_close.csv')
        if os.path.exists(m_path):
            df = pd.read_csv(m_path)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()
            return df['close']
        return None
    
    def compute_seasonal_factor(self, price):
        """计算季节性因子"""
        # 提取月份
        df = pd.DataFrame({'price': price})
        df['month'] = df.index.month
        
        # 计算月度收益率
        df['monthly_return'] = df['price'].pct_change(20)
        
        # 计算历史同期平均收益率
        seasonal_avg = df.groupby('month')['monthly_return'].mean()
        
        # 生成季节性因子
        df['seasonal_factor'] = df['month'].map(seasonal_avg)
        
        return df['seasonal_factor']
    
    def test_seasonal_factor(self):
        """测试季节性因子"""
        print("\n  [2.1] 测试季节性因子...")
        
        price = self.load_m_price()
        if price is None:
            print("  [FAIL] 价格数据不存在")
            return None
        
        # 计算季节性因子
        seasonal_factor = self.compute_seasonal_factor(price)
        
        # 计算forward return
        forward_return = price.pct_change(15).shift(-15)
        
        # 对齐
        aligned = pd.DataFrame({
            'factor': seasonal_factor,
            'return': forward_return
        }).dropna()
        
        if len(aligned) < 100:
            print(f"  [FAIL] 对齐后数据不足: {len(aligned)} 行")
            return None
        
        # 计算IC
        ic_list = []
        ic_window = 60
        for i in range(ic_window, len(aligned)):
            fac_window = aligned['factor'].iloc[i-ic_window:i]
            ret_window = aligned['return'].iloc[i-ic_window:i]
            
            if len(fac_window) < 20:
                continue
            
            ic, _ = spearmanr(fac_window, ret_window)
            if not np.isnan(ic):
                ic_list.append(ic)
        
        if ic_list:
            ic_mean = np.mean(ic_list)
            ic_std = np.std(ic_list)
            ir = ic_mean / ic_std if ic_std > 0 else 0
            win_rate = np.mean([ic > 0 for ic in ic_list])
            
            print(f"  [OK] 季节性因子:")
            print(f"    IC均值: {ic_mean:.4f}")
            print(f"    IR: {ir:.4f}")
            print(f"    胜率: {win_rate:.2%}")
            
            return {
                'factor': 'seasonal',
                'ic_mean': ic_mean,
                'ir': ir,
                'win_rate': win_rate
            }
        
        return None
    
    def run(self):
        """运行M因子开发"""
        print("\n" + "-" * 80)
        print("M豆粕 - 季节性因子开发")
        print("-" * 80)
        
        result = self.test_seasonal_factor()
        
        if result and result['ir'] > 0.3:
            print(f"\n  [BEST] 季节性因子有效！")
            print(f"    IR: {result['ir']:.4f}")
            return result
        elif result:
            print(f"\n  [WARN] 季节性因子IR={result['ir']:.4f}，低于0.3阈值")
            return result
        
        print("\n  [FAIL] 季节性因子测试失败")
        return None


# ============================================================
# 3. BR - 测试反转信号
# ============================================================

class BRReverseSignalTester:
    """BR合成橡胶反转信号测试"""
    
    def __init__(self):
        self.data_path = r'D:\futures_v6\macro_engine\data\crawlers'
    
    def load_br_price(self):
        """加载合成橡胶价格"""
        br_path = os.path.join(self.data_path, 'BR', 'daily', 'BR_fut_close.csv')
        if os.path.exists(br_path):
            df = pd.read_csv(br_path)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()
            return df['close']
        return None
    
    def test_reverse_signal(self):
        """测试反转信号"""
        print("\n  [3.1] 测试反转信号...")
        
        price = self.load_br_price()
        if price is None:
            print("  [FAIL] 价格数据不存在")
            return None
        
        # 原始动量因子
        momentum = price.pct_change(5)
        
        # 反转信号（乘以-1）
        reverse_factor = -momentum
        
        # 计算forward return
        forward_return = price.pct_change(10).shift(-10)
        
        # 对齐
        aligned = pd.DataFrame({
            'original': momentum,
            'reverse': reverse_factor,
            'return': forward_return
        }).dropna()
        
        if len(aligned) < 100:
            print(f"  [FAIL] 对齐后数据不足: {len(aligned)} 行")
            return None
        
        # 计算原始信号IC
        ic_list_original = []
        ic_list_reverse = []
        ic_window = 60
        
        for i in range(ic_window, len(aligned)):
            # 原始信号
            fac_orig = aligned['original'].iloc[i-ic_window:i]
            # 反转信号
            fac_rev = aligned['reverse'].iloc[i-ic_window:i]
            ret_window = aligned['return'].iloc[i-ic_window:i]
            
            if len(fac_orig) < 20:
                continue
            
            ic_orig, _ = spearmanr(fac_orig, ret_window)
            ic_rev, _ = spearmanr(fac_rev, ret_window)
            
            if not np.isnan(ic_orig):
                ic_list_original.append(ic_orig)
            if not np.isnan(ic_rev):
                ic_list_reverse.append(ic_rev)
        
        if ic_list_original and ic_list_reverse:
            # 原始信号
            ic_mean_orig = np.mean(ic_list_original)
            ir_orig = ic_mean_orig / np.std(ic_list_original) if np.std(ic_list_original) > 0 else 0
            
            # 反转信号
            ic_mean_rev = np.mean(ic_list_reverse)
            ir_rev = ic_mean_rev / np.std(ic_list_reverse) if np.std(ic_list_reverse) > 0 else 0
            
            print(f"  [OK] 信号对比:")
            print(f"    原始信号: IC={ic_mean_orig:.4f}, IR={ir_orig:.4f}")
            print(f"    反转信号: IC={ic_mean_rev:.4f}, IR={ir_rev:.4f}")
            print(f"    改善幅度: {ir_rev - ir_orig:.4f}")
            
            return {
                'original_ir': ir_orig,
                'reverse_ir': ir_rev,
                'improvement': ir_rev - ir_orig,
                'recommendation': 'reverse' if ir_rev > ir_orig else 'original'
            }
        
        return None
    
    def run(self):
        """运行BR反转测试"""
        print("\n" + "-" * 80)
        print("BR合成橡胶 - 反转信号测试")
        print("-" * 80)
        
        result = self.test_reverse_signal()
        
        if result:
            if result['reverse_ir'] > 0.3:
                print(f"\n  [BEST] 反转信号有效！IR={result['reverse_ir']:.4f}")
                return result
            elif result['reverse_ir'] > result['original_ir']:
                print(f"\n  [OK] 反转信号有改善，但IR={result['reverse_ir']:.4f}仍低于0.3")
                return result
            else:
                print(f"\n  [WARN] 反转信号无改善")
                return result
        
        print("\n  [FAIL] 反转信号测试失败")
        return None


# ============================================================
# 主程序
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("第二步：新因子开发 + 反转信号测试")
    print("=" * 80)
    
    results = {}
    
    # 1. AU新因子
    au_developer = AUFactorDeveloper()
    au_result = au_developer.run()
    if au_result:
        results['AU'] = au_result
    
    # 2. M季节性因子
    m_developer = MFactorDeveloper()
    m_result = m_developer.run()
    if m_result:
        results['M'] = m_result
    
    # 3. BR反转信号
    br_tester = BRReverseSignalTester()
    br_result = br_tester.run()
    if br_result:
        results['BR'] = br_result
    
    # 总结
    print("\n" + "=" * 80)
    print("第二步完成 - 结果总结")
    print("=" * 80)
    
    for variety, result in results.items():
        print(f"\n{variety}:")
        if 'ir' in result:
            print(f"  因子: {result.get('factor', 'unknown')}")
            print(f"  IR: {result['ir']:.4f}")
            print(f"  IC均值: {result['ic_mean']:.4f}")
        elif 'reverse_ir' in result:
            print(f"  原始IR: {result['original_ir']:.4f}")
            print(f"  反转IR: {result['reverse_ir']:.4f}")
            print(f"  建议: {'使用反转信号' if result['recommendation'] == 'reverse' else '保持原始信号'}")
    
    print("\n" + "=" * 80)
    print("下一步：将有效因子写入参数数据库")
    print("=" * 80)
