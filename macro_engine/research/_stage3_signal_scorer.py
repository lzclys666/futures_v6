"""
Stage 3: 信号评分系统 v5 — 基于已验证的 RollingICCalculator
SignalScorer — 0-100 综合信号评分
"""
import sqlite3
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
from datetime import datetime
import sys
sys.path.insert(0, r'D:\futures_v6\macro_engine\research')
from phase2_statistical_modules import RollingICCalculator

DB_PATH = r'D:\futures_v6\macro_engine\pit_data.db'

# =============================================================================
# 数据加载 (升序，用于 RollingICCalculator)
# =============================================================================

def _load_factor_pit(db_path, factor_code, symbol, lookback=500):
    """从PIT加载因子（降序取最新，再转为升序）"""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(
        "SELECT obs_date, raw_value FROM pit_factor_observations "
        "WHERE factor_code=? AND symbol=? ORDER BY obs_date DESC LIMIT ?",
        conn, params=(factor_code, symbol, lookback))
    conn.close()
    if len(df) == 0:
        return None
    df['date'] = pd.to_datetime(df['obs_date'])
    df = df.drop_duplicates('date', keep='first')
    df.set_index('date', inplace=True)
    df = df.sort_index()  # 转为升序
    return df['raw_value']


def _load_price_pit(db_path, symbol, lookback=500):
    """
    从PIT加载收盘价（降序取最新，再转为升序）。
    注意：CU_FUT_CLOSE 等每日有2条完全相同的记录（同一价格被录入两次），
    drop_duplicates(keep='first') 保留第一条，等效于去重。
    """
    conn = sqlite3.connect(db_path)
    fc = symbol + '_FUT_CLOSE'
    df = pd.read_sql(
        "SELECT obs_date, raw_value FROM pit_factor_observations "
        "WHERE factor_code=? AND symbol=? ORDER BY obs_date DESC LIMIT ?",
        conn, params=(fc, symbol, lookback))
    if len(df) < 60:
        df2 = pd.read_sql(
            "SELECT obs_date, raw_value FROM pit_factor_observations "
            "WHERE symbol=? AND factor_code LIKE ? ORDER BY obs_date DESC LIMIT ?",
            conn, params=(symbol, '%CLOSE%', lookback))
        if len(df2) > len(df):
            df = df2
    conn.close()
    if len(df) == 0:
        return None
    df['date'] = pd.to_datetime(df['obs_date'])
    # 去重（每日2条完全相同的价格，取任意一条即可）
    df = df.drop_duplicates('date', keep='first')
    df.set_index('date', inplace=True)
    df = df.sort_index()  # 转为升序
    return df['raw_value']


# =============================================================================
# IC 计算 (使用 RollingICCalculator)
# =============================================================================

def _compute_ic_stats(factor_series, price_series, window=60, hold=10):
    """
    用 RollingICCalculator 计算 IC 统计
    返回: (ic_series, ic_mean, ic_std, ic_win_rate)
    """
    df = pd.DataFrame({'f': factor_series, 'p': price_series})
    df = df[~df.index.duplicated(keep='first')].dropna()
    
    if len(df) < window + hold + 10:
        return pd.Series(dtype=float), 0.0, 0.0, 0.0
    
    # 计算前瞻收益
    fwd = df['p'].pct_change(hold).shift(-hold)
    df['fwd'] = fwd
    df_valid = df[['f', 'fwd']].dropna()
    
    if len(df_valid) < window + 5:
        return pd.Series(dtype=float), 0.0, 0.0, 0.0
    
    # RollingICCalculator
    ric = RollingICCalculator(window=window)
    ic_series = ric.compute_rolling_ic(df_valid['f'], df_valid['fwd'])
    
    if len(ic_series) < 5:
        return pd.Series(dtype=float), 0.0, 0.0, 0.0
    
    ic_mean = float(ic_series.mean())
    ic_std = float(ic_series.std()) if len(ic_series) > 1 else 0.0
    ic_win = float((ic_series > 0).mean())
    
    return ic_series, ic_mean, ic_std, ic_win


# =============================================================================
# 评分
# =============================================================================

def _score_ic_component(ic_mean, ic_win):
    """IC均值 (0-40) + 稳定性bonus (0-5)"""
    if ic_mean > 0.25:   s = 40
    elif ic_mean > 0.20: s = 35
    elif ic_mean > 0.15: s = 28
    elif ic_mean > 0.10: s = 20
    elif ic_mean > 0.05: s = 12
    elif ic_mean > 0.02: s = 6
    else:                s = 0
    bonus = 5 if ic_win >= 0.70 else (3 if ic_win >= 0.60 else (1 if ic_win >= 0.55 else 0))
    return min(40, s + bonus)


def _score_stability(ic_win):
    """IC胜率 (0-20)"""
    if ic_win >= 0.75: return 20
    elif ic_win >= 0.65: return 16
    elif ic_win >= 0.55: return 10
    elif ic_win >= 0.50: return 5
    return 0


def _score_freshness(factor_series):
    """数据新鲜度 (0-10)"""
    if factor_series is None or len(factor_series) == 0:
        return 0
    ld = factor_series.index[-1]
    if isinstance(ld, pd.Timestamp):
        ld = ld.to_pydatetime()
    tdays = int(((datetime.now() - ld).days) * 5 / 7) + 1
    if tdays <= 1: return 10
    elif tdays <= 3: return 7
    elif tdays <= 5: return 4
    elif tdays <= 10: return 2
    return 0


def _detect_regime(price_series):
    """波动率regime"""
    if price_series is None or len(price_series) < 100:
        return 1, 'unknown'
    ret = price_series.pct_change().dropna()
    if len(ret) < 60:
        return 1, 'unknown'
    rvol = ret.tail(60).std()
    hvol = ret.std()
    if rvol < hvol * 0.7: return 0, 'low_vol'
    elif rvol > hvol * 1.3: return 2, 'high_vol'
    return 1, 'medium_vol'


def _regime_fit(regime_label, factor_direction):
    """Regime适配 (0-20)"""
    if regime_label == 'low_vol':
        return 18 if factor_direction == -1 else 6
    elif regime_label == 'high_vol':
        return 18 if factor_direction == 1 else 6
    elif regime_label == 'medium_vol':
        return 16 if abs(factor_direction) == 1 else 12
    return 10


# =============================================================================
# 主类
# =============================================================================

class SignalScorer:
    """综合信号评分器 — Stage 3"""
    
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
    
    def score(self, factor_code, symbol, factor_direction=1, hold_days=10,
              ic_window=60, lookback=500):
        """返回: {total_score, signal, components, ic_stats, regime, ...}"""
        # 1. 加载数据
        fser = _load_factor_pit(self.db_path, factor_code, symbol, lookback)
        if fser is None or len(fser) < ic_window + hold_days + 20:
            return {'total_score': 0, 'signal': 'NO_DATA',
                    'error': 'factor {} x {} obs={} < needed {}'.format(
                        factor_code, symbol,
                        0 if fser is None else len(fser),
                        ic_window + hold_days + 20)}
        
        pser = _load_price_pit(self.db_path, symbol, lookback)
        if pser is None or len(pser) < 100:
            return {'total_score': 0, 'signal': 'NO_PRICE',
                    'error': 'price {} obs={}'.format(
                        symbol, 0 if pser is None else len(pser)),
                    'factor_latest': str(fser.index[-1].date())}
        
        # 2. 计算 IC
        ic_series, ic_mean, ic_std, ic_win = _compute_ic_stats(
            fser, pser, window=ic_window, hold=hold_days)
        
        if len(ic_series) < 5:
            return {'total_score': 0, 'signal': 'IC_FAILED',
                    'error': 'IC computation returned {} samples'.format(len(ic_series)),
                    'factor_latest': str(fser.index[-1].date()),
                    'price_latest': str(pser.index[-1].date())}
        
        # 3. 评分
        ic_score = _score_ic_component(ic_mean, ic_win)
        stab_score = _score_stability(ic_win)
        fresh_score = _score_freshness(fser)
        reg_idx, reg_lbl = _detect_regime(pser)
        reg_score = _regime_fit(reg_lbl, factor_direction)
        crowd_score = 10  # 暂满分，等 OI 数据
        
        total = max(0, min(100, ic_score + stab_score + reg_score + fresh_score + crowd_score))
        
        # 4. 信号
        if total >= 70:   sig = 'STRONG_BUY' if factor_direction == 1 else 'STRONG_SELL'
        elif total >= 55: sig = 'BUY' if factor_direction == 1 else 'SELL'
        elif total >= 40: sig = 'NEUTRAL'
        elif total >= 25: sig = 'SELL' if factor_direction == 1 else 'BUY'
        else:             sig = 'STRONG_SELL' if factor_direction == 1 else 'STRONG_BUY'
        
        # 5. IC详情
        rec_ic = ic_series.tail(ic_window).dropna()
        ir = ic_mean / ic_std if ic_std > 0 else 0.0
        
        return {
            'total_score': round(total, 1),
            'signal': sig,
            'components': {
                'IC均值+稳定性(45)': ic_score,
                'IC胜率(20)': stab_score,
                'Regime适配(20)': reg_score,
                '数据新鲜度(10)': fresh_score,
                '持仓集中度(10)': crowd_score,
            },
            'ic_stats': {
                'ic_mean':   round(ic_mean, 4),
                'ic_std':    round(ic_std, 4),
                'ic_ir':     round(ir, 4),
                'ic_win':    round(ic_win, 4),
                'ic_n':      len(ic_series),
                'ic_last5':  [round(x, 4) for x in ic_series.tail(5).tolist()],
            },
            'regime': reg_lbl,
            'regime_idx': int(reg_idx),
            'hold_days': hold_days,
            'factor_latest': str(fser.index[-1].date()),
            'price_latest': str(pser.index[-1].date()),
        }
    
    def score_multiple(self, factor_list, symbol):
        """批量评分"""
        results = []
        for fc, fd, hd in factor_list:
            r = self.score(fc, symbol, factor_direction=fd, hold_days=hd)
            r['factor_code'] = fc
            results.append(r)
        results.sort(key=lambda x: x['total_score'], reverse=True)
        return results


# =============================================================================
# 测试
# =============================================================================

if __name__ == '__main__':
    scorer = SignalScorer()
    print("=" * 60)
    print("Stage 3 SignalScorer v5")
    print("=" * 60)
    
    tests = [
        ('CU_AL_ratio', 'CU', 1, 10),
        ('CU_AL_ratio', 'CU', 1, 20),
    ]
    
    for fc, sym, fd, hd in tests:
        print("\n[{} x {} hold={}]".format(fc, sym, hd))
        r = scorer.score(fc, sym, factor_direction=fd, hold_days=hd)
        if 'error' in r:
            print("  ERROR: {}".format(r['error']))
            print("  factor: {} | price: {}".format(
                r.get('factor_latest'), r.get('price_latest')))
        else:
            print("  Signal={} Score={}/100 | Regime={}".format(
                r['signal'], r['total_score'], r['regime']))
            print("  数据: factor={} | price={}".format(
                r['factor_latest'], r['price_latest']))
            print("  IC: mean={:.4f} IR={:.4f} win={:.1%} n={}".format(
                r['ic_stats']['ic_mean'], r['ic_stats']['ic_ir'],
                r['ic_stats']['ic_win'], r['ic_stats']['ic_n']))
            print("  IC last5: {}".format(r['ic_stats']['ic_last5']))
            print("  分数: {}".format(r['components']))
    
    print("\nDone.")
