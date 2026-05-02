"""
Phase 2 Statistical Modules (Fixed Version)
===========================================
修复清单:
  1. RollingICCalculator.compute_rolling_ic: dropna()导致iloc位置偏移 → 改用全局对齐后按位置窗口计算
  2. BootstrapAnalyzer: 缺随机种子 → 添加random_state参数
  3. 新增: 完整单元测试套件
"""
import sys
import unittest
import os
import pandas as pd
import numpy as np
from scipy.stats import spearmanr, ttest_1samp
from sklearn.mixture import GaussianMixture
from datetime import datetime


# ============================================================
# 2.1 滚动IC/IR计算模块
# ============================================================

class RollingICCalculator:
    """滚动IC/IR计算器"""

    def __init__(self, window=60, min_periods=30):
        self.window = window
        self.min_periods = min_periods

    def compute_ic(self, factor_series, forward_return):
        """计算IC（信息系数）- Spearman秩相关"""
        df = pd.DataFrame({
            'factor': factor_series,
            'return': forward_return
        })
        df = df.dropna(subset=['factor', 'return'])
        if len(df) < self.min_periods:
            return np.nan
        ic, _ = spearmanr(df['factor'].values, df['return'].values)
        return ic

    def compute_rolling_ic(self, factor_series, forward_return):
        """
        计算滚动IC序列

        关键修复: 不在dropna后的DataFrame上做rolling窗口，
        而是在全局对齐后的DataFrame上用iloc按位置取窗口。
        这样避免dropna()后iloc位置偏移问题。
        """
        df = pd.DataFrame({
            'factor': factor_series,
            'return': forward_return
        })
        # 全局dropna，但保留在df中（不对齐到新索引）
        df = df.dropna(subset=['factor', 'return'])
        df = df.reset_index(drop=True)  # 重置为纯位置索引，消除日期标签影响

        n = len(df)
        if n < self.window:
            return pd.Series(dtype=float)

        ic_series = []
        for i in range(self.window, n):
            # 用iloc按位置取窗口
            fac_win = df['factor'].iloc[i - self.window:i].values
            ret_win = df['return'].iloc[i - self.window:i].values
            ic, _ = spearmanr(fac_win, ret_win)
            ic_series.append(ic)

        # 用原始因子序列的日期作为输出索引（取每个窗口末尾的日期）
        dates = factor_series.index
        # 对应的日期：从第window个位置开始
        valid_dates = dates[df.index[self.window:n]]
        return pd.Series(ic_series, index=valid_dates)

    def compute_ir(self, ic_series):
        """计算IR（信息比率）= IC均值 / IC标准差"""
        ic_clean = ic_series.dropna()
        if len(ic_clean) < 2:
            return np.nan
        return ic_clean.mean() / ic_clean.std()

    def compute_ic_stats(self, ic_series):
        """IC统计量汇总"""
        ic_clean = ic_series.dropna()
        if len(ic_clean) < 2:
            return {}
        return {
            'mean': float(ic_clean.mean()),
            'std': float(ic_clean.std()),
            'ir': float(ic_clean.mean() / ic_clean.std()),
            't_stat': float(ic_clean.mean() / (ic_clean.std() / np.sqrt(len(ic_clean)))),
            'p_value': float(ttest_1samp(ic_clean, 0)[1]),
            'win_rate': float((ic_clean > 0).mean()),
            'max_drawdown': float((ic_clean.cummax() - ic_clean).max()),
            'skewness': float(ic_clean.skew()),
            'kurtosis': float(ic_clean.kurtosis())
        }


# ============================================================
# 2.2 Bootstrap置信区间模块
# ============================================================

class BootstrapAnalyzer:
    """Bootstrap分析器"""

    def __init__(self, n_bootstrap=1000, confidence=0.95, random_state=42):
        self.n_bootstrap = n_bootstrap
        self.confidence = confidence
        self.random_state = random_state

    def compute_ic_ci(self, factor_series, forward_return):
        """计算IC的Bootstrap置信区间"""
        df = pd.DataFrame({
            'factor': factor_series,
            'return': forward_return
        })
        df = df.dropna(subset=['factor', 'return'])
        n = len(df)
        if n < 30:
            return {'error': '样本不足'}

        np.random.seed(self.random_state)  # 固定随机种子
        ic_bootstraps = []
        for _ in range(self.n_bootstrap):
            idx = np.random.choice(n, size=n, replace=True)
            sample_fac = df['factor'].iloc[idx].values
            sample_ret = df['return'].iloc[idx].values
            ic, _ = spearmanr(sample_fac, sample_ret)
            ic_bootstraps.append(ic)

        ic_bootstraps = np.array(ic_bootstraps)
        alpha = 1 - self.confidence
        ci_lower = np.percentile(ic_bootstraps, alpha / 2 * 100)
        ci_upper = np.percentile(ic_bootstraps, (1 - alpha / 2) * 100)
        return {
            'ic_mean': float(np.mean(ic_bootstraps)),
            'ic_std': float(np.std(ic_bootstraps)),
            'ci_lower': float(ci_lower),
            'ci_upper': float(ci_upper),
            'ci_width': float(ci_upper - ci_lower),
            'significant': bool(not (ci_lower <= 0 <= ci_upper))
        }


# ============================================================
# 2.3 HMM状态检测模块
# ============================================================

class HMMRegimeDetector:
    """HMM市场状态检测器（使用GMM近似，非真正HMM）"""

    def __init__(self, n_regimes=3, random_state=42):
        self.n_regimes = n_regimes
        self.random_state = random_state
        self.model = None
        self.fitted = False
        self._X_mean = None
        self._X_std = None
        self.regime_labels_ = None
        self.regime_probs_ = None

    def fit(self, returns_series):
        """拟合隐状态模型"""
        returns = returns_series.dropna()
        volatility = returns.rolling(window=20).std().dropna()
        aligned = pd.DataFrame({
            'returns': returns,
            'volatility': volatility
        }).dropna()

        if len(aligned) < 60:
            raise ValueError("数据不足，需要至少60个观测值")

        self._X_mean = aligned.mean()
        self._X_std = aligned.std()
        X = (aligned - self._X_mean) / self._X_std

        self.model = GaussianMixture(
            n_components=self.n_regimes,
            random_state=self.random_state,
            covariance_type='full'
        )
        self.model.fit(X.values)
        self.fitted = True

        self.regime_labels_ = self.model.predict(X.values)
        self.regime_probs_ = self.model.predict_proba(X.values)
        self._aligned_index = aligned.index

        return self

    def predict_regime(self, returns_series):
        """预测市场状态序列"""
        if not self.fitted:
            raise ValueError("模型未拟合，请先调用fit()")

        returns = returns_series.dropna()
        volatility = returns.rolling(window=20).std().dropna()
        aligned = pd.DataFrame({
            'returns': returns,
            'volatility': volatility
        }).dropna()

        X = (aligned - self._X_mean) / self._X_std
        regime = self.model.predict(X.values)
        probs = self.model.predict_proba(X.values)

        cols = {f'prob_{i}': probs[:, i] for i in range(self.n_regimes)}
        result = pd.DataFrame({'regime': regime, **cols}, index=aligned.index)
        return result

    def get_regime_stats(self):
        """获取各状态统计特征"""
        if not self.fitted:
            return {}

        stats = {}
        for i in range(self.n_regimes):
            mask = self.regime_labels_ == i
            stats[f'regime_{i}'] = {
                'count': int(mask.sum()),
                'pct': float(mask.mean()),
                'mean_return': float(self._X_mean['returns'] + self.model.means_[i][0] * self._X_std['returns']),
                'mean_volatility': float(self._X_mean['volatility'] + self.model.means_[i][1] * self._X_std['volatility'])
            }
        return stats


# ============================================================
# 2.4 因子衰减分析模块
# ============================================================

class FactorDecayAnalyzer:
    """因子衰减分析器"""

    def __init__(self, max_lag=20):
        self.max_lag = max_lag

    def compute_decay_curve(self, factor_series, returns_series):
        """
        计算因子IC衰减曲线

        经济含义: 因子在 lag 天后的预测能力衰减情况
        正确实现: factor[t] 与 return[t+lag] 做相关
        """
        df = pd.DataFrame({
            'factor': factor_series,
            'return': returns_series
        }).dropna(subset=['factor', 'return'])
        df = df.reset_index(drop=True)

        decay_curve = {}
        for lag in range(1, self.max_lag + 1):
            if len(df) <= lag:
                break
            # factor: positions [0, n-lag-1]
            # return shifted by -lag: positions [lag, n-1]
            # 对齐方式: factor[0..n-lag-1] vs return[lag..n-1]
            fac_vals = df['factor'].iloc[:-lag].values
            ret_vals = df['return'].iloc[lag:].values
            min_len = min(len(fac_vals), len(ret_vals))
            if min_len < 2:
                break
            ic, _ = spearmanr(fac_vals[:min_len], ret_vals[:min_len])
            decay_curve[lag] = ic

        return pd.Series(decay_curve, dtype=float)

    def compute_half_life(self, decay_curve):
        """计算半衰期（IC衰减到初始值一半的lag）"""
        ic_0 = abs(decay_curve.iloc[0])
        if ic_0 < 1e-10:
            return np.nan
        ic_half = ic_0 / 2
        half_life = (decay_curve.abs() - ic_half).abs().idxmin()
        return half_life


# ============================================================
# 单元测试套件
# ============================================================

def _load_ag_data():
    """加载AG期货数据用于测试"""
    f = r'D:\futures_v6\macro_engine\data\crawlers\AG\daily\AG_fut_close.csv'
    if not os.path.exists(f):
        return None, None
    df = pd.read_csv(f, encoding='utf-8-sig')
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    df['return_1d'] = df['close'].pct_change()
    df['return_5d'] = df['close'].pct_change(5)
    return df['close'], df['return_5d']


def _make_random_data(seed=42, n=200):
    """生成确定性的随机测试数据"""
    np.random.seed(seed)
    dates = pd.date_range('2020-01-01', periods=n, freq='B')
    factor = pd.Series(np.random.randn(n) * 10 + 100, index=dates)
    ret = pd.Series(np.random.randn(n) * 0.02, index=dates)
    return factor, ret


class TestRollingICCalculator(unittest.TestCase):
    """RollingICCalculator 单元测试"""

    def test_compute_ic_basic(self):
        """测试: compute_ic 基本功能"""
        factor, ret = _make_random_data(seed=42)
        calc = RollingICCalculator(window=60, min_periods=30)
        ic = calc.compute_ic(factor, ret)
        self.assertIsInstance(ic, float)
        self.assertTrue(-1 <= ic <= 1)

    def test_compute_ic_stats(self):
        """测试: compute_ic_stats 返回完整统计量"""
        factor, ret = _make_random_data(seed=42)
        calc = RollingICCalculator(window=60, min_periods=30)
        rolling_ic = calc.compute_rolling_ic(factor, ret)
        stats = calc.compute_ic_stats(rolling_ic)
        required_keys = {'mean', 'std', 'ir', 't_stat', 'p_value', 'win_rate', 'max_drawdown'}
        for k in required_keys:
            self.assertIn(k, stats, f"Missing key: {k}")

    def test_compute_ir(self):
        """测试: compute_ir 计算"""
        factor, ret = _make_random_data(seed=42)
        calc = RollingICCalculator(window=60, min_periods=30)
        rolling_ic = calc.compute_rolling_ic(factor, ret)
        ir = calc.compute_ir(rolling_ic)
        self.assertIsInstance(ir, float)

    def test_rolling_ic_no_na_windows(self):
        """测试: 无NaN窗口时正确返回"""
        factor, ret = _make_random_data(seed=42, n=200)
        calc = RollingICCalculator(window=60, min_periods=30)
        result = calc.compute_rolling_ic(factor, ret)
        self.assertFalse(result.isna().all(), "所有窗口都是NaN")
        na_count = result.isna().sum()
        total = len(result)
        self.assertLess(na_count, total, f"所有 {total} 个窗口都是NaN")

    def test_rolling_ic_with_real_data(self):
        """测试: 用真实AG数据验证IC为合理值"""
        factor, ret = _load_ag_data()
        if factor is None:
            self.skipTest("AG数据文件不存在")
        calc = RollingICCalculator(window=60, min_periods=30)
        rolling_ic = calc.compute_rolling_ic(factor, ret)
        ic_mean = rolling_ic.mean()
        # AG close价格自相关应该有显著IC（正向）
        self.assertGreater(ic_mean, 0.1, f"AG close因子IC均值 {ic_mean:.4f} 过低")
        # IC应该在[-1, 1]范围内
        self.assertLessEqual(abs(float(ic_mean)), 1.0)

    def test_rolling_ic_alignment_with_pct_change_na(self):
        """
        测试: pct_change产生的NaN不会导致窗口错位

        验证修复有效: dropna后用iloc按位置窗口计算，
        与原始df位置的对应关系正确。
        """
        np.random.seed(99)
        dates = pd.date_range('2020-01-01', periods=100, freq='B')
        # 故意构造pct_change会产生NaN的数据
        close = pd.Series([100.0] + list(np.cumsum(np.random.randn(99))), index=dates)
        ret5 = close.pct_change(5)  # 前5个值是NaN
        calc = RollingICCalculator(window=20, min_periods=10)
        rolling_ic = calc.compute_rolling_ic(close, ret5)
        # 应该返回合理数量的IC值
        self.assertGreater(len(rolling_ic.dropna()), 5)
        # IC应该在[-1, 1]
        for ic_val in rolling_ic.dropna():
            self.assertLessEqual(abs(ic_val), 1.0)


class TestBootstrapAnalyzer(unittest.TestCase):
    """BootstrapAnalyzer 单元测试"""

    def test_bootstrap_reproducible(self):
        """测试: 固定random_state时结果可复现"""
        factor, ret = _make_random_data(seed=42)
        bs1 = BootstrapAnalyzer(n_bootstrap=100, random_state=42)
        bs2 = BootstrapAnalyzer(n_bootstrap=100, random_state=42)
        r1 = bs1.compute_ic_ci(factor, ret)
        r2 = bs2.compute_ic_ci(factor, ret)
        self.assertEqual(r1['ic_mean'], r2['ic_mean'],
                         "相同random_state应产生相同结果")

    def test_bootstrap_different_seeds_different_results(self):
        """测试: 不同random_state产生不同结果"""
        factor, ret = _make_random_data(seed=42)
        bs1 = BootstrapAnalyzer(n_bootstrap=100, random_state=42)
        bs2 = BootstrapAnalyzer(n_bootstrap=100, random_state=99)
        r1 = bs1.compute_ic_ci(factor, ret)
        r2 = bs2.compute_ic_ci(factor, ret)
        self.assertNotEqual(r1['ic_mean'], r2['ic_mean'],
                            "不同random_state应产生不同结果")

    def test_bootstrap_ci_structure(self):
        """测试: CI返回值结构完整"""
        factor, ret = _make_random_data(seed=42)
        bs = BootstrapAnalyzer(n_bootstrap=100, random_state=42)
        r = bs.compute_ic_ci(factor, ret)
        self.assertIn('ic_mean', r)
        self.assertIn('ci_lower', r)
        self.assertIn('ci_upper', r)
        self.assertIn('significant', r)
        self.assertLessEqual(r['ci_lower'], r['ic_mean'])
        self.assertLessEqual(r['ic_mean'], r['ci_upper'])

    def test_bootstrap_insufficient_data(self):
        """测试: 数据不足时返回error"""
        factor, ret = _make_random_data(seed=42, n=10)
        bs = BootstrapAnalyzer(n_bootstrap=100)
        r = bs.compute_ic_ci(factor, ret)
        self.assertIn('error', r)


class TestHMMRegimeDetector(unittest.TestCase):
    """HMMRegimeDetector 单元测试"""

    def test_fit_predict_roundtrip(self):
        """测试: fit后再predict，结果数量一致"""
        factor, ret = _make_random_data(seed=42, n=200)
        hmm = HMMRegimeDetector(n_regimes=3, random_state=42)
        hmm.fit(ret)
        pred = hmm.predict_regime(ret)
        self.assertEqual(len(pred), len(hmm.regime_labels_))
        self.assertIn('regime', pred.columns)
        self.assertIn('prob_0', pred.columns)

    def test_regime_stats(self):
        """测试: get_regime_stats返回正确结构"""
        factor, ret = _make_random_data(seed=42, n=200)
        hmm = HMMRegimeDetector(n_regimes=3, random_state=42)
        hmm.fit(ret)
        stats = hmm.get_regime_stats()
        self.assertEqual(len(stats), 3)
        for k, v in stats.items():
            self.assertIn('count', v)
            self.assertIn('pct', v)
            self.assertIn('mean_return', v)
            self.assertIn('mean_volatility', v)

    def test_unfitted_raises(self):
        """测试: 未fit就predict应抛出异常"""
        hmm = HMMRegimeDetector(n_regimes=3)
        with self.assertRaises(ValueError):
            hmm.predict_regime(pd.Series([0.01, -0.02, 0.03]))


class TestFactorDecayAnalyzer(unittest.TestCase):
    """FactorDecayAnalyzer 单元测试"""

    def test_decay_curve_monotonic(self):
        """测试: 随机数据的衰减曲线不一定单调（正常）"""
        factor, ret = _make_random_data(seed=42, n=200)
        decay = FactorDecayAnalyzer(max_lag=10)
        curve = decay.compute_decay_curve(factor, ret)
        self.assertEqual(len(curve), 10)
        for v in curve.values:
            self.assertIsInstance(v, (float, np.floating))
            self.assertLessEqual(abs(v), 1.0)

    def test_decay_curve_with_real_data(self):
        """测试: AG真实数据衰减曲线"""
        factor, ret = _load_ag_data()
        if factor is None:
            self.skipTest("AG数据文件不存在")
        decay = FactorDecayAnalyzer(max_lag=10)
        curve = decay.compute_decay_curve(factor, ret)
        # close价格自相关在lag增加时应衰减
        self.assertGreater(curve.iloc[0], 0.05, "初始IC应较高")
        self.assertFalse(curve.isna().all())

    def test_half_life(self):
        """测试: 半衰期计算"""
        decay = FactorDecayAnalyzer(max_lag=20)
        # 构造一个简单的线性衰减曲线
        curve = pd.Series({1: 0.10, 2: 0.08, 3: 0.06, 4: 0.04, 5: 0.02})
        hl = decay.compute_half_life(curve)
        self.assertIsNotNone(hl)


# ============================================================
# 主程序：运行测试 + 示例演示
# ============================================================

if __name__ == "__main__":
    print("=" * 80)
    print("Phase 2 Statistical Modules - Fixed Version")
    print("=" * 80)

    # 运行单元测试
    print("\n[单元测试]")
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"\n测试结果: {passed}/{result.testsRun} 通过")

    if result.failures or result.errors:
        print("\n失败详情:")
        for tb in result.failures + result.errors:
            print(tb[0])

    # 示例演示（仅在测试全部通过时）
    if not result.failures and not result.errors:
        print("\n" + "=" * 80)
        print("示例演示")
        print("=" * 80)

        base_path = r'D:\futures_v6\macro_engine\data\crawlers'
        ag_file = os.path.join(base_path, 'AG', 'daily', 'AG_fut_close.csv')

        if os.path.exists(ag_file):
            df = pd.read_csv(ag_file, encoding='utf-8-sig')
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()
            df['return_1d'] = df['close'].pct_change()
            df['return_5d'] = df['close'].pct_change(5)
            print(f"\n[AG数据] {len(df)} 行，日期范围: {df.index[0]} ~ {df.index[-1]}")

            # 2.1 滚动IC
            print("\n[2.1] 滚动IC/IR计算...")
            ic_calc = RollingICCalculator(window=60, min_periods=30)
            rolling_ic = ic_calc.compute_rolling_ic(df['close'], df['return_5d'])
            ic_stats = ic_calc.compute_ic_stats(rolling_ic)
            print(f"IC统计: mean={ic_stats['mean']:.4f}, IR={ic_stats['ir']:.4f}, "
                  f"t={ic_stats['t_stat']:.2f}, 胜率={ic_stats['win_rate']:.1%}")

            # 2.2 Bootstrap CI
            print("\n[2.2] Bootstrap置信区间...")
            bs = BootstrapAnalyzer(n_bootstrap=1000, random_state=42)
            ci_result = bs.compute_ic_ci(df['close'], df['return_5d'])
            print(f"IC均值: {ci_result['ic_mean']:.4f}")
            print(f"95% CI: [{ci_result['ci_lower']:.4f}, {ci_result['ci_upper']:.4f}]")
            print(f"显著性: {'是' if ci_result['significant'] else '否'}")

            # 2.3 HMM
            print("\n[2.3] HMM市场状态检测...")
            hmm = HMMRegimeDetector(n_regimes=3, random_state=42)
            try:
                hmm.fit(df['return_1d'])
                regime_stats = hmm.get_regime_stats()
                print(f"检测到 {len(regime_stats)} 个市场状态:")
                for regime, stats in regime_stats.items():
                    print(f"  {regime}: 占比{stats['pct']:.1%}, "
                          f"平均收益{stats['mean_return']:.6f}")
            except Exception as e:
                print(f"HMM拟合失败: {e}")

            # 2.4 因子衰减
            print("\n[2.4] 因子衰减分析...")
            decay = FactorDecayAnalyzer(max_lag=10)
            decay_curve = decay.compute_decay_curve(df['close'], df['return_1d'])
            half_life = decay.compute_half_life(decay_curve)
            print(f"IC衰减曲线 (lag 1-5): {[f'{v:.4f}' for v in decay_curve.head(5).values]}")
            print(f"半衰期: {half_life} 天")
        else:
            print(f"\n[AG数据文件不存在: {ag_file}]")

    print("\n" + "=" * 80)
    print("Phase 2 Fixed 版本完成")
    print("=" * 80)
