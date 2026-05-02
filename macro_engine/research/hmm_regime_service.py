"""
HMM Regime Service — 加载已训练的 HMM 模型，预测当前市场状态
集成到 signal_daily_report.py

数据源策略：
  - AG/AU: 优先 CSV（SGE金银现货，历史长），PIT 备用
  - CU/NI: PIT 为主，CSV 兜底
  - 其他: PIT

用法:
    from hmm_regime_service import get_regime_score, get_regime_series, train_all_models
    score, label, probs = get_regime_score('AG')
"""
import sys
sys.path.insert(0, r'D:\futures_v6\macro_engine\research')
from phase2_statistical_modules import HMMRegimeDetector
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
import os

DB = r'D:\futures_v6\macro_engine\pit_data.db'
MODEL_DIR = r'D:\futures_v6\macro_engine\research\models'
CSV_BASE = Path(r'D:\futures_v6\macro_engine\data\crawlers')

# ============================================================================
# 数据源配置
# ============================================================================

def _csv_path(symbol, factor='spot'):
    """CSV 文件路径"""
    paths = {
        'AG_SGE': CSV_BASE / 'AG/daily/AG_SGE_silver_spot.csv',
        'AU_SGE': CSV_BASE / 'AU/daily/AU_SGE_gold_spot.csv',
        'CU_FUT': CSV_BASE / 'CU/daily/CU_fut_close.csv',
        'AU_FUT': CSV_BASE / 'AU/daily/AU_fut_close.csv',
        'AG_FUT': CSV_BASE / 'AG/daily/AG_fut_close.csv',
    }
    return paths.get(factor, None)


def _load_csv(symbol, factor='spot', lookback=2000):
    """从 CSV 加载价格序列（升序），优先取 close 列"""
    path = _csv_path(symbol, factor)
    if path is None or not path.exists():
        return None
    try:
        df = pd.read_csv(path, parse_dates=['date'], index_col='date').sort_index()
        # 优先取 close 列（OHLCV 格式），其次 morning_close（SGE），最后第一列
        if 'close' in df.columns:
            col = 'close'
        elif 'morning_close' in df.columns:
            col = 'morning_close'
        else:
            col = df.columns[0]
        series = df[col].dropna()
        if len(series) > lookback:
            series = series.tail(lookback)
        return series
    except Exception:
        return None


def _load_price_from_pit(symbol, factor_code=None, lookback=500):
    """从 PIT 加载收盘价（升序）"""
    if factor_code is None:
        factor_code = symbol + '_FUT_CLOSE'
    conn = sqlite3.connect(DB)
    try:
        df = pd.read_sql(
            "SELECT obs_date, raw_value FROM pit_factor_observations "
            "WHERE symbol=? AND factor_code=? ORDER BY obs_date DESC LIMIT ?",
            conn, params=(symbol, factor_code, lookback))
    finally:
        conn.close()
    if len(df) == 0:
        return None
    df['date'] = pd.to_datetime(df['obs_date'])
    df = df.drop_duplicates('date', keep='first')
    df = df.set_index('date').sort_index()
    df = df[~df.index.duplicated(keep='first')]
    return df['raw_value']


def _load_price(symbol):
    """
    智能加载价格序列：
    - AG/AU: CSV(SGE现货) 优先，PIT 兜底
    - CU: PIT 优先，CSV 兜底
    - NI: PIT
    - 其他: PIT
    """
    if symbol == 'AG':
        # SGE白银现货（历史长）
        p = _load_csv('AG', 'AG_SGE')
        if p is not None and len(p) >= 200:
            return p, 'csv_AG_SGE'
        # 期货兜底
        p = _load_price_from_pit('AG', 'AG_FUT_CLOSE', 2000)
        if p is not None and len(p) >= 200:
            return p, 'pit_AG_FUT'
        return None, None

    elif symbol == 'AU':
        # SGE黄金现货（历史长）
        p = _load_csv('AU', 'AU_SGE')
        if p is not None and len(p) >= 200:
            return p, 'csv_AU_SGE'
        # 期货兜底
        p = _load_price_from_pit('AU', 'AU_FUT_CLOSE', 2000)
        if p is not None and len(p) >= 200:
            return p, 'pit_AU_FUT'
        return None, None

    elif symbol == 'CU':
        # PIT（已有1712行）优先
        p = _load_price_from_pit('CU', 'CU_FUT_CLOSE', 2000)
        if p is not None and len(p) >= 200:
            return p, 'pit_CU_FUT'
        # CSV 兜底
        p = _load_csv('CU', 'CU_FUT', 2000)
        if p is not None and len(p) >= 200:
            return p, 'csv_CU_FUT'
        return None, None

    else:
        # 其他品种：PIT
        p = _load_price_from_pit(symbol, None, 2000)
        if p is not None and len(p) >= 200:
            return p, f'pit_{symbol}'
        return None, None


# ============================================================================
# HMM 训练
# ============================================================================

def _train_hmm(returns, symbol, source, n_regimes=3, random_state=42):
    """训练单个 HMM，返回 detector 或 None"""
    if len(returns) < 200:
        print(f"[HMM] {symbol}({source}): 收益率不足 {len(returns)} (需要>=200)")
        return None

    # 'tied': 所有regime共用一个协方差矩阵，大幅减少过拟合
    # 'full': 每个regime独立协方差，2特征×3regimes=18参数，极易过拟合
    detector = HMMRegimeDetector(
        n_regimes=n_regimes,
        random_state=random_state,
        covariance_type='tied',   # ← 关键修复：减少过拟合
        n_iter=100                 # ← 减少迭代次数，防止过拟合
    )
    try:
        # fit_auto() 先用 BIC 选择最优 n_regimes，再稳定拟合
        detector.fit_auto(returns, n_seeds=20, n_range=(2, 4), criterion='bic')
    except Exception as e:
        print(f"[HMM] {symbol}({source}): fit_stable 失败 - {e}")
        return None

    os.makedirs(MODEL_DIR, exist_ok=True)
    path = os.path.join(MODEL_DIR, f'hmm_{symbol.lower()}.joblib')
    detector.save(path)
    print(f"[HMM] {symbol}({source}): trained on {len(returns)} returns, saved {path}")
    return detector


def train_all_models():
    """训练所有品种 HMM 模型"""
    results = {}
    symbols = {
        'AG': None,  # source determined by _load_price
        'AU': None,
        'CU': None,
        'NI': None,
    }

    for symbol in symbols:
        price, source = _load_price(symbol)
        if price is None:
            print(f"[HMM] {symbol}: 无法加载数据")
            results[symbol] = None
            continue

        returns = price.pct_change().dropna()
        detector = _train_hmm(returns, symbol, source or 'unknown')

        if detector:
            # 验证当前状态
            try:
                result = detector.predict_regime(returns.tail(60))
                curr_regime = int(result['regime'].iloc[-1])
                vol_ratio = returns.tail(20).std() / returns.std()
                if vol_ratio < 0.7:
                    label = 'low_vol'
                elif vol_ratio > 1.3:
                    label = 'high_vol'
                else:
                    label = 'medium_vol'
                prob_cols = [c for c in result.columns if c.startswith('prob_')]
                probs = {c.replace('prob_', ''): float(result[c].iloc[-1]) for c in prob_cols}
                score_map = {0: 18, 1: 15, 2: 12, 3: 9}
                score = score_map.get(curr_regime, 10)
                results[symbol] = {'score': score, 'label': label, 'probs': probs,
                                   'regime': curr_regime, 'n': len(returns)}
            except Exception as e:
                print(f"[HMM] {symbol}: predict_regime 失败 - {e}")
                results[symbol] = None

    return results


# ============================================================================
# 公开 API
# ============================================================================

def get_regime_score(symbol):
    """
    获取品种当前 regime 评分 (0-20)
    Returns: (score, label, probs_dict) 或 (10, 'unknown', {})
    """
    model_path = os.path.join(MODEL_DIR, f'hmm_{symbol.lower()}.joblib')
    if not os.path.exists(model_path):
        # 尝试实时训练
        price, source = _load_price(symbol)
        if price is None:
            return 10, 'unknown', {}
        returns = price.pct_change().dropna()
        detector = _train_hmm(returns, symbol, source or 'unknown')
        if detector is None:
            return 10, 'unknown', {}
    else:
        try:
            detector = HMMRegimeDetector.load(model_path)
        except Exception as e:
            print(f"[HMM] {symbol}: load 失败 - {e}")
            return 10, 'unknown', {}

    price, _ = _load_price(symbol)
    if price is None:
        return 10, 'unknown', {}
    returns = price.pct_change().dropna()

    try:
        result = detector.predict_regime(returns.tail(500))
        curr_regime = int(result['regime'].iloc[-1])
        vol_ratio = returns.tail(20).std() / returns.std()
        label = 'low_vol' if vol_ratio < 0.7 else ('high_vol' if vol_ratio > 1.3 else 'medium_vol')
        prob_cols = [c for c in result.columns if c.startswith('prob_')]
        probs = {c.replace('prob_', ''): float(result[c].iloc[-1]) for c in prob_cols}
        score_map = {0: 18, 1: 15, 2: 12, 3: 9}
        score = score_map.get(curr_regime, 10)
        return score, label, probs
    except Exception as e:
        print(f"[HMM] {symbol}: predict_regime 失败 - {e}")
        return 10, 'unknown', {}


def get_regime_series(symbol, days=60):
    """获取品种最近 days 个交易日的 regime 序列"""
    model_path = os.path.join(MODEL_DIR, f'hmm_{symbol.lower()}.joblib')
    if not os.path.exists(model_path):
        return pd.Series(dtype=int)

    try:
        detector = HMMRegimeDetector.load(model_path)
    except Exception:
        return pd.Series(dtype=int)

    price, _ = _load_price(symbol)
    if price is None:
        return pd.Series(dtype=int)

    returns = price.pct_change().dropna()
    if len(returns) < days:
        days = len(returns)

    try:
        result = detector.predict_regime(returns.tail(days))
        return result['regime']
    except Exception:
        return pd.Series(dtype=int)


# ============================================================================
# 独立运行
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("HMM Regime 模型训练")
    print("=" * 60)
    results = train_all_models()
    print("\n当前 Regime 状态:")
    for symbol, info in results.items():
        if info is None:
            print(f"  {symbol}: FAILED")
        else:
            probs_str = ', '.join([f"R{k}={v:.1%}" for k, v in info['probs'].items()])
            print(f"  {symbol}: score={info['score']} label={info['label']} "
                  f"regime={info['regime']} n={info['n']} [{probs_str}]")
