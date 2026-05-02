"""
Phase 2 Statistical Modules (v3 - hmmlearn + PIT)
=================================================
改造清单:
  1. HMM: GaussianMixture → hmmlearn.GaussianHMM (真正的隐马尔可夫模型，带转移矩阵)
  2. PIT: 新增 PITDataService，支持 point-in-time 合规数据查询
  3. 保留全部原有接口，单元测试完全兼容
"""
import sys
import unittest
import os
import sqlite3
import pandas as pd
import numpy as np
from scipy.stats import spearmanr, ttest_1samp
from hmmlearn.hmm import GaussianHMM
from datetime import datetime


# ============================================================
# 2.0 PIT 数据服务
# ============================================================

class PITDataService:
    """
    Point-in-Time 数据服务

    核心保证: 查询时只返回在 as_of_date 之前已经公开的数据，
    避免未来函数漏（look-ahead bias）。

    PIT 合规原则:
    - obs_date: 观察值对应的实际日期（经济数据对应月份、价格数据对应交易日）
    - pub_date: 该数据点被公开/录入系统的日期
    - 查询时: WHERE pub_date <= as_of_date，确保数据在 as_of_date 时已存在
    """

    DEFAULT_DB = r'D:\futures_v6\macro_engine\pit_data.db'

    def __init__(self, db_path=None):
        self.db_path = db_path or self.DEFAULT_DB
        self._conn = None

    def _connect(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def list_factors(self, is_active=None, frequency=None):
        """
        列出因子元数据

        参数:
            is_active: True/False/None（不过滤）
            frequency: 'daily'/'weekly'/'monthly'/None（不过滤）
        返回:
            DataFrame，columns: factor_code, factor_name, direction, frequency, norm_method, is_active
        """
        conn = self._connect()
        sql = "SELECT factor_code, factor_name, direction, frequency, norm_method, is_active FROM factor_metadata WHERE 1=1"
        params = []
        if is_active is not None:
            sql += " AND is_active = ?"
            params.append(1 if is_active else 0)
        if frequency:
            sql += " AND frequency = ?"
            params.append(frequency)
        return pd.read_sql(sql, conn, params=params)

    def get_snapshot(self, factor_code, as_of_date, obs_date_col='obs_date'):
        """
        获取某个因子在 as_of_date 时刻的 PIT 快照

        参数:
            factor_code: 因子代码（如 'jm_futures_spread'）
            as_of_date: 查询截止日期（str or datetime）
            obs_date_col: 观察值日期字段（默认 obs_date）
        返回:
            DataFrame，过滤为 pub_date <= as_of_date 的所有 obs_date 记录
        """
        conn = self._connect()
        as_of = pd.to_datetime(as_of_date).strftime('%Y-%m-%d')
        sql = f"""
            SELECT * FROM {factor_code}
            WHERE pub_date <= ?
            ORDER BY {obs_date_col} DESC
        """
        return pd.read_sql(sql, conn, params=[as_of])

    def get_factor_observations(self, factor_code, start_date=None, end_date=None,
                               as_of_date=None, obs_date_col='obs_date'):
        """
        获取因子时间序列（支持 PIT 过滤）

        参数:
            factor_code: 因子代码
            start_date: 观察日期起始（可选）
            end_date: 观察日期结束（可选）
            as_of_date: PIT 截止日期（可选，传None表示不用PIT过滤）
            obs_date_col: 观察值日期字段
        返回:
            DataFrame，按 obs_date 排序
        """
        conn = self._connect()
        if as_of_date:
            as_of = pd.to_datetime(as_of_date).strftime('%Y-%m-%d')
            pit_filter = "pub_date <= ?"
            params = [as_of]
        else:
            pit_filter = "1=1"
            params = []

        sql = f"SELECT * FROM {factor_code} WHERE {pit_filter}"
        if start_date:
            sql += f" AND {obs_date_col} >= ?"
            params.append(pd.to_datetime(start_date).strftime('%Y-%m-%d'))
        if end_date:
            sql += f" AND {obs_date_col} <= ?"
            params.append(pd.to_datetime(end_date).strftime('%Y-%m-%d'))
        sql += f" ORDER BY {obs_date_col}"
        return pd.read_sql(sql, conn, params=params)

    def get_price_series(self, symbol, field='close', start_date=None, end_date=None,
                         as_of_date=None):
        """
        获取期货价格序列（从 pit_factor_observations 表）

        参数:
            symbol: 品种代码（如 'jm'）
            field: 字段名（close/settle/open/high/low/volume/hold）
            start_date/end_date: 日期范围
            as_of_date: PIT 截止日期
        返回:
            Series，index=obs_date, values=field
        """
        conn = self._connect()
        table = f"{symbol.lower()}_futures_ohlcv"
        if as_of_date:
            as_of = pd.to_datetime(as_of_date).strftime('%Y-%m-%d')
            pit_filter = "pub_date <= ?"
            params = [as_of]
        else:
            pit_filter = "1=1"
            params = []
        sql = f"SELECT obs_date, {field} FROM {table} WHERE {pit_filter}"
        if start_date:
            sql += " AND obs_date >= ?"
            params.append(pd.to_datetime(start_date).strftime('%Y-%m-%d'))
        if end_date:
            sql += " AND obs_date <= ?"
            params.append(pd.to_datetime(end_date).strftime('%Y-%m-%d'))
        sql += " ORDER BY obs_date"
        df = pd.read_sql(sql, conn, params=params)
        if df.empty:
            return pd.Series(dtype=float)
        df['obs_date'] = pd.to_datetime(df['obs_date'])
        return df.set_index('obs_date')[field].astype(float)

    def get_forward_return(self, symbol, holding_days=5, price_field='close',
                          start_date=None, end_date=None, as_of_date=None):
        """
        计算前瞻收益率序列

        参数:
            symbol: 品种代码
            holding_days: 持有天数（用于 pct_change）
            price_field: 价格字段
            start_date/end_date/as_of_date: 同上
        返回:
            Series，index=obs_date（return的结算日），values=收益率
        """
        price = self.get_price_series(symbol, field=price_field,
                                      start_date=start_date, end_date=end_date,
                                      as_of_date=as_of_date)
        ret = price.pct_change(holding_days)
        return ret.dropna()

    def verify_pit_compliance(self, factor_code, date_range=('2020-01-01', '2025-12-31')):
        """
        验证某个因子的 PIT 合规性（检查无未来数据）

        返回:
            dict: {'compliant': bool, 'future_violations': int,
                   'null_obs_dates': int, 'sample'}
        """
        conn = self._connect()
        sql = f"SELECT obs_date, pub_date FROM {factor_code} ORDER BY obs_date"
        df = pd.read_sql(sql, conn)
        if df.empty:
            return {'compliant': True, 'future_violations': 0, 'null_obs_dates': 0, 'sample': df}

        df['obs_date'] = pd.to_datetime(df['obs_date'])
        df['pub_date'] = pd.to_datetime(df['pub_date'])

        # 未来违规: pub_date 在 obs_date 之后（正常应该是 pub_date <= obs_date）
        future_violations = (df['pub_date'] > df['obs_date']).sum()
        null_obs = df['obs_date'].isna().sum()
        compliant = (future_violations == 0) and (null_obs == 0)

        return {
            'compliant': compliant,
            'future_violations': int(future_violations),
            'null_obs_dates': int(null_obs),
            'sample': df.tail(5)
        }

    def verify_pit_compliance_v2(self, factor_code, date_range=('2020-01-01', '2025-12-31')):
        """
        PIT 合规性验证（v2，适用于爬虫录入数据）

        判断标准:
        - 真正违规: obs_date > trade_date（obs_date 填了"录入日期"而非真实交易日）
        - 爬虫正常: pub_date >= obs_date（录入日期晚于观察日期，符合爬虫行为）
        - 假阳性: pub_date > obs_date 但 obs_date = trade_date（历史补录，不算真正违规）
        """
        conn = self._connect()
        sql = f"SELECT obs_date, pub_date, trade_date FROM {factor_code} ORDER BY obs_date"
        df = pd.read_sql(sql, conn)
        if df.empty:
            return {'compliant': True, 'obs_gt_trade': 0, 'null_count': 0, 'sample': df}

        df['obs_date'] = pd.to_datetime(df['obs_date'])
        df['pub_date'] = pd.to_datetime(df['pub_date'])
        df['trade_date'] = pd.to_datetime(df['trade_date'])

        # 真正的 PIT 违规: obs_date 填了 crawl date 而非 trade_date
        obs_gt_trade = (df['obs_date'] > df['trade_date']).sum()
        null_count = df['obs_date'].isna().sum()
        compliant = (obs_gt_trade == 0) and (null_count == 0)

        return {
            'compliant': compliant,
            'obs_gt_trade': int(obs_gt_trade),
            'null_count': int(null_count),
            'sample': df.tail(5)
        }

    def repair_obs_date(self, table_name, dry_run=True):
        """
        修复 obs_date 填充错误：将 obs_date 纠正为 trade_date

        根因：爬虫录入时错误地用"录入日期"填充 obs_date，
        而非真实的 trade_date。导致 pub_date > obs_date 未来违规。

        适用场景：每日快照类数据表（spread、hold_volume 等），
        其中 obs_date 应严格等于 trade_date。

        参数:
            table_name: 表名（如 'jm_futures_spread'）
            dry_run: True=只查不改，返回诊断；False=执行 UPDATE
        返回:
            dict: 诊断报告
        """
        conn = self._connect()

        # 检查表是否有 trade_date 列
        cols = pd.read_sql(f"PRAGMA table_info({table_name})", conn)
        col_names = cols['name'].tolist()
        if 'trade_date' not in col_names:
            return {'error': f'表 {table_name} 没有 trade_date 列', 'columns': col_names}

        # 诊断：哪些 obs_date != trade_date
        sql = f"""
            SELECT obs_date, trade_date, pub_date,
                   COUNT(*) as cnt
            FROM {table_name}
            WHERE obs_date != trade_date
            GROUP BY obs_date, trade_date
            ORDER BY obs_date DESC
            LIMIT 20
        """
        mismatches = pd.read_sql(sql, conn)
        total_mismatches = sum(mismatches['cnt']) if not mismatches.empty else 0

        result = {
            'table': table_name,
            'dry_run': dry_run,
            'total_mismatches': int(total_mismatches),
            'mismatch_sample': mismatches.head(10).to_dict('records') if not mismatches.empty else [],
            'columns': col_names,
            'fixed': 0
        }

        if dry_run:
            result['message'] = f"[DRY RUN] 发现 {total_mismatches} 条 obs_date 与 trade_date 不一致的记录"
            return result

        # 执行修复
        sql_fix = f"""
            UPDATE {table_name}
            SET obs_date = trade_date
            WHERE obs_date != trade_date
        """
        cur = conn.cursor()
        cur.execute(sql_fix)
        conn.commit()
        result['fixed'] = cur.rowcount
        result['message'] = f"已修复 {cur.rowcount} 条 obs_date → trade_date"

        # 重新验证（用 v2：对爬虫录入数据正确判断 obs_date > trade_date 为违规）
        verify = self.verify_pit_compliance_v2(table_name)
        result['pit_after'] = verify
        return result

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


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

    def compute_from_pit(self, pit_service, factor_code, symbol,
                        holding_days=5, price_field='close',
                        start_date=None, end_date=None, as_of_date=None):
        """
        从PIT数据库计算滚动IC（自动合规）

        参数:
            pit_service: PITDataService 实例
            factor_code: 因子代码
            symbol: 品种代码（用于计算收益）
            holding_days: 持有天数
            price_field: 价格字段
            start_date/end_date/as_of_date: 同PITDataService
        """
        ret = pit_service.get_forward_return(
            symbol, holding_days=holding_days, price_field=price_field,
            start_date=start_date, end_date=end_date, as_of_date=as_of_date
        )
        obs_dates = ret.index
        factor_obs = pit_service.get_factor_observations(
            factor_code, start_date=start_date, end_date=end_date,
            as_of_date=as_of_date
        )
        if factor_obs.empty:
            return pd.Series(dtype=float)
        factor_obs['obs_date'] = pd.to_datetime(factor_obs['obs_date'])
        factor_obs = factor_obs.set_index('obs_date').sort_index()
        # 合并因子和收益（按obs_date对齐）
        combined = pd.DataFrame({'factor': factor_obs.iloc[:, 0], 'return': ret})
        combined = combined.dropna()
        return self.compute_rolling_ic(combined['factor'], combined['return'])


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
# 2.3 HMM状态检测模块（hmmlearn）
# ============================================================

class HMMRegimeDetector:
    """
    HMM市场状态检测器（使用hmmlearn.GaussianHMM）

    相比GMM近似版本的优势:
    - 真正的隐马尔可夫模型，包含状态转移概率矩阵
    - 支持预测未来状态序列
    - 提供更好的时序建模能力
    """

    def __init__(self, n_regimes=3, random_state=42, n_iter=200,
                 covariance_type='full'):
        self.n_regimes = n_regimes
        self.random_state = random_state
        self.n_iter = n_iter
        self.covariance_type = covariance_type
        self.model = None
        self.fitted = False
        self._X_mean = None
        self._X_std = None
        self.regime_labels_ = None
        self.regime_probs_ = None
        self._aligned_index = None

    def fit(self, returns_series):
        """
        拟合GaussianHMM模型

        特征: [returns, rolling_volatility] 二维高斯
        """
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
        X_arr = X.values

        # hmmlearn GaussianHMM
        self.model = GaussianHMM(
            n_components=self.n_regimes,
            covariance_type=self.covariance_type,
            n_iter=self.n_iter,
            random_state=self.random_state
        )
        self.model.fit(X_arr)
        self.fitted = True

        # 状态序列和概率
        self.regime_labels_ = self.model.predict(X_arr)
        self.regime_probs_ = self.model.predict_proba(X_arr)
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
        # HMM means_: shape (n_components, n_features)
        for i in range(self.n_regimes):
            mask = self.regime_labels_ == i
            stats[f'regime_{i}'] = {
                'count': int(mask.sum()),
                'pct': float(mask.mean()),
                'mean_return': float(self._X_mean['returns'] + self.model.means_[i][0] * self._X_std['returns']),
                'mean_volatility': float(self._X_mean['volatility'] + self.model.means_[i][1] * self._X_std['volatility']),
                'transition_from_self': float(self.model.transmat_[i, i]) if self.model else None
            }
        return stats

    def get_transition_matrix(self):
        """获取状态转移概率矩阵"""
        if not self.fitted:
            return None
        return pd.DataFrame(
            self.model.transmat_,
            index=[f'regime_{i}' for i in range(self.n_regimes)],
            columns=[f'regime_{i}' for i in range(self.n_regimes)]
        )

    def get_stationary_distribution(self):
        """获取稳态分布"""
        if not self.fitted:
            return None
        eigvals, eigvecs = np.linalg.eig(self.model.transmat_.T)
        stationary = np.abs(eigvecs[:, 0])
        stationary = stationary / stationary.sum()
        return pd.Series(stationary, index=[f'regime_{i}' for i in range(self.n_regimes)])

    def _score_transition_matrix(self, transmat, min_self_threshold=0.30):
        """
        给转移矩阵打分，识别异常模式

        硬阈值规则（优先于评分）：
        - 任何状态自转移 < min_self_threshold → 立即返回 0.0（拒绝该模型）
          原因: 自转移 < 0.30 意味着该状态平均停留 < 1.4 个周期，属于瞬态

        评分维度:
        - 自转移稳健性: 所有状态自转移 > 0.90 → 1.0
        - 往复震荡惩罚: max(非对角) > 0.90 → 开始扣分

        返回:
            float: 健康分 [0,1]，0.0 表示不合格（硬阈值触发）
        """
        n = transmat.shape[0]
        min_self = np.min(np.diag(transmat))
        max_off = 0.0
        for i in range(n):
            for j in range(n):
                if i != j and transmat[i, j] > max_off:
                    max_off = transmat[i, j]

        # 硬阈值: 自转移低于阈值 → 0.0（一票否决）
        if min_self < min_self_threshold:
            return 0.0

        # 1. 自转移评分: 用指数函数，越高越快趋近 1.0
        #    min_self=0.30 → 0.55, min_self=0.50 → 0.87, min_self=0.90 → 0.99
        self_score = 1.0 - np.exp(-10.0 * (min_self - 0.30))

        # 2. 往复惩罚: max_off > 0.90 开始扣分, 达到 0.99 时为 0.0
        if max_off >= 0.99:
            off_penalty = 0.0
        elif max_off <= 0.90:
            off_penalty = 1.0
        else:
            off_penalty = 1.0 - (max_off - 0.90) / 0.09

        return self_score * 0.6 + off_penalty * 0.4

    def fit_stable(self, returns_series, n_seeds=10):
        """
        稳定拟合: 自动尝试多个随机种子，选择转移矩阵最健康的模型

        根因: GaussianHMM 对随机初始化敏感。
        某些种子会产生瞬态状态（regime 自转移 ≈ 0），导致状态解释失效。

        参数:
            returns_series: 收益率序列
            n_seeds: 尝试的随机种子数量（默认 10）

        返回:
            self（ fitted 状态，转移矩阵健康）
        """
        import itertools

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
        X_arr = X.values

        best_score = -1.0
        best_model = None
        best_seed = None
        best_labels = None
        best_probs = None

        for seed in range(42, 42 + n_seeds):
            model = GaussianHMM(
                n_components=self.n_regimes,
                covariance_type=self.covariance_type,
                n_iter=self.n_iter,
                random_state=seed
            )
            try:
                model.fit(X_arr)
                score = self._score_transition_matrix(model.transmat_)
                if score > best_score:
                    best_score = score
                    best_model = model
                    best_seed = seed
                    best_labels = model.predict(X_arr)
                    best_probs = model.predict_proba(X_arr)
            except Exception:
                # 模型拟合失败，跳过
                continue

        if best_model is None:
            raise ValueError(f"所有 {n_seeds} 个随机种子均拟合失败")

        self.model = best_model
        self.random_state = best_seed
        self.fitted = True
        self.regime_labels_ = best_labels
        self.regime_probs_ = best_probs
        self._aligned_index = aligned.index

        # 健康度警告
        min_self = np.min(np.diag(best_model.transmat_))
        if min_self < 0.05:
            import warnings
            warnings.warn(
                f"[HMM WARNING] 最小的自转移概率={min_self:.4f} < 0.05，"
                f"建议降低 n_regimes 或增大数据量"
            )

        return self

    # ========================================================
    # 2.3.2b 自动选择最优 n_regimes 后再稳定拟合
    # ========================================================

    def fit_auto(self, returns_series, n_seeds=10, n_range=(2, 5), criterion='bic'):
        """
        自动选择最优regime数量，再稳定拟合

        流程:
          1. 准备数据（与 fit_stable 相同）
          2. 调用 select_n_regimes() 找到 BIC/AIC 最优 n_regimes
          3. 更新 self.n_regimes
          4. 调用 fit_stable() 完成拟合

        参数:
            returns_series: 收益率序列
            n_seeds: 传给 fit_stable 的种子数量
            n_range: 自动搜索的 n_regimes 范围
            criterion: 'bic'（默认）或 'aic'

        返回:
            self（fitted 状态）
        """
        returns = returns_series.dropna()
        volatility = returns.rolling(window=20).std().dropna()
        aligned = pd.DataFrame({
            'returns': returns,
            'volatility': volatility
        }).dropna()

        if len(aligned) < 60:
            raise ValueError("数据不足，需要至少60个观察值")

        self._X_mean = aligned.mean()
        self._X_std = aligned.std()
        X = (aligned - self._X_mean) / self._X_std
        X_arr = X.values

        # Step 1: 自动选择最优 n_regimes
        optimal_n = self.select_n_regimes(
            X_arr, n_range=n_range, criterion=criterion, verbose=True)

        if optimal_n != self.n_regimes:
            print(f"[HMM fit_auto] n_regimes {self.n_regimes} -> {optimal_n} (BIC最优)")
            self.n_regimes = optimal_n

        # Step 2: 用最优 n_regimes 做稳定拟合
        return self.fit_stable(returns_series, n_seeds=n_seeds)

    # ========================================================
    # 2.3.3 自动选择最优 n_regimes（BIC/AIC 准则）
    # ========================================================

    def _compute_bic(self, X, n_regimes, n_iter=100, random_state=42):
        """
        计算给定 n_regimes 的 BIC 值
        
        BIC = -2 * log_L + log(n_samples) * n_params
        n_params(full协方差) = n_regimes          # means: n_regimes * n_features
                       + n_regimes*(n_regimes-1) # transmat: 自由度
                       + n_regimes*n_features**2 # covars: full协方差矩阵
                       + n_regimes-1             # startprob: 自由度
        """
        n_samples, n_features = X.shape
        try:
            model = GaussianHMM(
                n_components=n_regimes,
                covariance_type='full',
                n_iter=n_iter,
                random_state=random_state,
                init_params='stmc'
            )
            model.fit(X)
            log_L = model.score(X)
            n_params = (
                n_regimes * n_features           # means
                + n_regimes * (n_regimes - 1)    # transmat (行和=1，自由度-1)
                + n_regimes * n_features**2      # covars (full矩阵)
                + n_regimes - 1                  # startprob (和=1，自由度-1)
            )
            bic = -2 * log_L + np.log(n_samples) * n_params
            aic = -2 * log_L + 2 * n_params
            return {'bic': bic, 'aic': aic, 'log_L': log_L, 'model': model}
        except Exception:
            return {'bic': np.inf, 'aic': np.inf, 'log_L': -np.inf, 'model': None}

    def select_n_regimes(self, X, n_range=(2, 5), criterion='bic', verbose=True):
        """
        自动选择最优隐状态数量
        
        Parameters
        ----------
        X : np.ndarray, shape (n_samples, n_features)
            标准化后的特征矩阵
        n_range : tuple (min, max)
            遍历的状态数范围，默认 2~5
        criterion : 'bic' or 'aic'
            选择准则，默认 BIC（更保守，适合模型选择）
        verbose : bool
            是否打印每个状态的 BIC/AIC
        
        Returns
        -------
        int, 最优 n_regimes
        """
        results = []
        for n in range(n_range[0], n_range[1] + 1):
            # 多seed取最优，避免局部最优
            best = None
            for seed in [42, 0, 99, 2024, 7]:
                r = self._compute_bic(X, n, n_iter=100, random_state=seed)
                if best is None or r[criterion] < best[criterion]:
                    best = r
            results.append({'n_regimes': n, **best})
            if verbose:
                print(f"  n_regimes={n}: BIC={best['bic']:.2f}, AIC={best['aic']:.2f}, "
                      f"log_L={best['log_L']:.2f}")
        
        best_result = min(results, key=lambda x: x[criterion])
        optimal = best_result['n_regimes']
        if verbose:
            print(f"\n  最优 n_regimes={optimal} (criterion={criterion}, "
                  f"{criterion.upper()}={best_result[criterion]:.2f})")
        return optimal

    # ========================================================
    # 2.3.4 模型持久化（joblib）
    # ========================================================

    def save(self, filepath):
        """
        保存模型到磁盘（joblib pickle）
        
        保存内容：
        - self.model: fitted GaussianHMM 对象
        - self._X_mean / self._X_std: 标准化参数
        - self._aligned_index: 对齐后的日期索引
        - self._df: 原始 DataFrame（可选，文件大则不含）
        - self.n_regimes / self.covariance_type
        - self._regimes / self._df 等 fitted 状态
        
        Parameters
        ----------
        filepath : str, .pkl 或 .joblib 路径
        """
        import joblib
        import os
        
        # 构造保存字典，仅保存实际存在的属性
        save_dict = {
            'model': self.model,
            'n_regimes': self.n_regimes,
            'covariance_type': self.covariance_type,
            '_X_mean': getattr(self, '_X_mean', None),
            '_X_std': getattr(self, '_X_std', None),
            '_aligned_index': getattr(self, '_aligned_index', None),
            '_regimes': getattr(self, '_regimes', None),
            '_df': getattr(self, '_df', None),
            '_scores': getattr(self, '_scores', None),
            '_n_features': getattr(self, '_n_features', None),
            '_n_samples': getattr(self, '_n_samples', None),
            '_version': '3.0',
        }
        
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        joblib.dump(save_dict, filepath)
        print(f"[HMM save] saved to {filepath} ({os.path.getsize(filepath)/1024:.1f} KB)")

    @classmethod
    def load(cls, filepath):
        """
        从磁盘加载模型（joblib pickle）
        
        Parameters
        ----------
        filepath : str, .pkl 或 .joblib 路径
        
        Returns
        -------
        HMMRegimeDetector 实例（已 fitted）
        """
        import joblib
        
        save_dict = joblib.load(filepath)
        version = save_dict.pop('_version', '1.0')
        
        # 重建实例
        instance = cls(n_regimes=save_dict['n_regimes'],
                       covariance_type=save_dict['covariance_type'])
        instance.model = save_dict['model']
        # 可选字段（fit()可能不设置这些）
        for attr in ['_X_mean','_X_std','_aligned_index','_regimes',
                      '_df','_scores','_n_features','_n_samples']:
            if save_dict.get(attr) is not None:
                setattr(instance, attr, save_dict[attr])
        instance.fitted = True
        
        print(f"[HMM load] loaded from {filepath} (version={version})")
        return instance


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


def _load_ag_return_1d():
    """加载AG 1日收益用于HMM测试"""
    f = r'D:\futures_v6\macro_engine\data\crawlers\AG\daily\AG_fut_close.csv'
    if not os.path.exists(f):
        return None
    df = pd.read_csv(f, encoding='utf-8-sig')
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    df['return_1d'] = df['close'].pct_change()
    return df['return_1d'].dropna()


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
        """
        np.random.seed(99)
        dates = pd.date_range('2020-01-01', periods=100, freq='B')
        close = pd.Series([100.0] + list(np.cumsum(np.random.randn(99))), index=dates)
        ret5 = close.pct_change(5)
        calc = RollingICCalculator(window=20, min_periods=10)
        rolling_ic = calc.compute_rolling_ic(close, ret5)
        self.assertGreater(len(rolling_ic.dropna()), 5)
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
        self.assertEqual(r1['ic_mean'], r2['ic_mean'])

    def test_bootstrap_different_seeds_different_results(self):
        """测试: 不同random_state产生不同结果"""
        factor, ret = _make_random_data(seed=42)
        bs1 = BootstrapAnalyzer(n_bootstrap=100, random_state=42)
        bs2 = BootstrapAnalyzer(n_bootstrap=100, random_state=99)
        r1 = bs1.compute_ic_ci(factor, ret)
        r2 = bs2.compute_ic_ci(factor, ret)
        self.assertNotEqual(r1['ic_mean'], r2['ic_mean'])

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
        ret = _load_ag_return_1d()
        if ret is None:
            self.skipTest("AG数据文件不存在")
        hmm = HMMRegimeDetector(n_regimes=3, random_state=42)
        hmm.fit(ret)
        pred = hmm.predict_regime(ret)
        self.assertEqual(len(pred), len(hmm.regime_labels_))
        self.assertIn('regime', pred.columns)
        self.assertIn('prob_0', pred.columns)

    def test_regime_stats(self):
        """测试: get_regime_stats返回正确结构"""
        ret = _load_ag_return_1d()
        if ret is None:
            self.skipTest("AG数据文件不存在")
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

    def test_transition_matrix(self):
        """测试: 转移矩阵返回正确形状"""
        ret = _load_ag_return_1d()
        if ret is None:
            self.skipTest("AG数据文件不存在")
        hmm = HMMRegimeDetector(n_regimes=3, random_state=42)
        hmm.fit(ret)
        tm = hmm.get_transition_matrix()
        self.assertEqual(tm.shape, (3, 3))
        # 每行和为1
        for i in range(3):
            self.assertAlmostEqual(tm.iloc[i].sum(), 1.0, places=5)

    def test_stationary_distribution(self):
        """测试: 稳态分布"""
        ret = _load_ag_return_1d()
        if ret is None:
            self.skipTest("AG数据文件不存在")
        hmm = HMMRegimeDetector(n_regimes=3, random_state=42)
        hmm.fit(ret)
        sd = hmm.get_stationary_distribution()
        self.assertAlmostEqual(sd.sum(), 1.0, places=5)


class TestPITDataService(unittest.TestCase):
    """PITDataService 单元测试"""

    def test_list_factors(self):
        """测试: 列出因子元数据"""
        pit = PITDataService()
        df = pit.list_factors(is_active=True)
        self.assertIn('factor_code', df.columns)
        self.assertIn('direction', df.columns)

    def test_verify_pit_compliance(self):
        """测试: PIT合规验证"""
        pit = PITDataService()
        # 测试有数据的因子表
        result = pit.verify_pit_compliance('jm_futures_spread')
        self.assertIn('compliant', result)
        self.assertIn('future_violations', result)

    def test_get_price_series(self):
        """测试: 获取价格序列"""
        pit = PITDataService()
        price = pit.get_price_series('jm', field='close',
                                     start_date='2024-01-01',
                                     end_date='2024-01-31')
        self.assertTrue(isinstance(price, pd.Series))

    def test_context_manager(self):
        """测试: 上下文管理器"""
        with PITDataService() as pit:
            df = pit.list_factors(is_active=True)
            self.assertIn('factor_code', df.columns)


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
        self.assertGreater(curve.iloc[0], 0.05, "初始IC应较高")
        self.assertFalse(curve.isna().all())

    def test_half_life(self):
        """测试: 半衰期计算"""
        decay = FactorDecayAnalyzer(max_lag=20)
        curve = pd.Series({1: 0.10, 2: 0.08, 3: 0.06, 4: 0.04, 5: 0.02})
        hl = decay.compute_half_life(curve)
        self.assertIsNotNone(hl)


# ============================================================
# 主程序：运行测试 + 示例演示
# ============================================================

if __name__ == "__main__":
    import sys
    print("=" * 80)
    print("Phase 2 Statistical Modules - hmmlearn + PIT 版本")
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

    # 示例演示
    if not result.failures and not result.errors:
        print("\n" + "=" * 80)
        print("示例演示")
        print("=" * 80)

        base_path = r"D:\futures_v6\macro_engine\data\crawlers"
        ag_file = os.path.join(base_path, "AG", "daily", "AG_fut_close.csv")

        if os.path.exists(ag_file):
            df = pd.read_csv(ag_file, encoding="utf-8-sig")
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
            df["return_1d"] = df["close"].pct_change()
            df["return_5d"] = df["close"].pct_change(5)
            print(f"\n[AG数据] {len(df)} 行，日期范围: {df.index[0]} ~ {df.index[-1]}")

            # 2.1 滚动IC
            print("\n[2.1] 滚动IC/IR计算...")
            ic_calc = RollingICCalculator(window=60, min_periods=30)
            rolling_ic = ic_calc.compute_rolling_ic(df["close"], df["return_5d"])
            ic_stats = ic_calc.compute_ic_stats(rolling_ic)
            print(f"IC统计: mean={ic_stats['mean']:.4f}, IR={ic_stats['ir']:.4f}, "
                  f"t={ic_stats['t_stat']:.2f}, 胜率={ic_stats['win_rate']:.1%}")

            # 2.2 Bootstrap CI
            print("\n[2.2] Bootstrap置信区间...")
            bs = BootstrapAnalyzer(n_bootstrap=1000, random_state=42)
            ci_result = bs.compute_ic_ci(df["close"], df["return_5d"])
            print(f"IC均值: {ci_result['ic_mean']:.4f}")
            print(f"95% CI: [{ci_result['ci_lower']:.4f}, {ci_result['ci_upper']:.4f}]")
            print(f"显著性: {'是' if ci_result['significant'] else '否'}")

            # 2.3 HMM
            print("\n[2.3] HMM市场状态检测 (hmmlearn)...")
            hmm = HMMRegimeDetector(n_regimes=3, random_state=42)
            try:
                hmm.fit(df["return_1d"])
                regime_stats = hmm.get_regime_stats()
                print(f"检测到 {len(regime_stats)} 个市场状态:")
                for regime, stats in regime_stats.items():
                    print(f"  {regime}: 占比{stats['pct']:.1%}, "
                          f"平均收益{stats['mean_return']:.6f}")
                print("转移矩阵:")
                print(hmm.get_transition_matrix())
            except Exception as e:
                print(f"HMM拟合失败: {e}")

            # 2.4 因子衰减
            print("\n[2.4] 因子衰减分析...")
            decay = FactorDecayAnalyzer(max_lag=10)
            decay_curve = decay.compute_decay_curve(df["close"], df["return_1d"])
            half_life = decay.compute_half_life(decay_curve)
            print(f"IC衰减曲线 (lag 1-5): {[f'{v:.4f}' for v in decay_curve.head(5).values]}")
            print(f"半衰期: {half_life} 天")
        else:
            print(f"\n[AG数据文件不存在: {ag_file}]")

        # 2.5 PIT数据服务演示
        print("\n[2.5] PIT数据服务...")
        try:
            with PITDataService() as pit:
                factors = pit.list_factors(is_active=True, frequency="daily")
                print(f"活跃日频因子数: {len(factors)}")
                pit_check = pit.verify_pit_compliance("jm_futures_spread")
                print(f"JM spread PIT合规: {pit_check['compliant']}, "
                      f"未来违规: {pit_check['future_violations']}")
        except Exception as e:
            print(f"PIT查询失败: {e}")

    print("\n" + "=" * 80)
    print("Phase 2 hmmlearn+PIT 版本完成")
    print("=" * 80)