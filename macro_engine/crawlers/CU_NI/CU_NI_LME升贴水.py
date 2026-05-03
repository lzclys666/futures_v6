#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NI_抓取LME升贴水_EVENT
因子: 待定义 = NI_抓取LME升贴水_EVENT

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""

import sys
import os
import sqlite3
from datetime import datetime, date
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value, DB_PATH

import akshare as ak

# 阈值设定
SPREAD_THRESHOLD = 50.0  # USD/吨，市场紧张信号阈值

def get_pit_date():
    """获取PIT日期（周一用上周五）"""
    today = date.today()
    dow = today.weekday()
    if dow == 0:  # 周一
        obs_date = today - pd.Timedelta(days=2)
    elif dow == 6:  # 周日
        obs_date = today - pd.Timedelta(days=2)
    else:
        obs_date = today
    return today.strftime('%Y-%m-%d'), obs_date.strftime('%Y-%m-%d')

def fetch_lme_copper_spread():
    """
    获取LME铜升贴水数据
    
    尝试多种方式获取:
    1. AKShare futures_foreign_commodity_realtime (LME铜3个月)
    2. 从CSV历史文件读取最新值
    3. DB回补
    
    Returns:
        dict: {'spread': float, 'source': str, 'confidence': float}
    """
    spread = None
    source = None
    confidence = 0.0
    
    # L1: AKShare LME铜3个月实时行情
    # 符号'CAD'在AKShare中对应LME铜3个月期货价格
    try:
        print("[L1] AKShare futures_foreign_commodity_realtime (LME铜3个月)...")
        df = ak.futures_foreign_commodity_realtime(['CAD'])
        if df is not None and len(df) > 0:
            # 列: 名称, 最新价, 人民币报价, 涨跌额, 涨跌幅, 开盘价, 最高价, 最低价, 昨日结算价, 持仓量, 买价, 卖价, 行情时间, 日期
            today_3m = float(df['最新价'].values[0])  # 今天3M结算价
            yesterday_3m = float(df['昨日结算价'].values[0])  # 昨天3M结算价
            daily_change = float(df['涨跌额'].values[0])  # 每日价格变动

            # Cash-3M升贴水估算:
            # 用backwardation模型: Cash ≈ 今天3M - 每日变动（隐含昨日3M≈现货+昨日spread）
            # 更准确: Cash ≈ 今天3M - (今天3M - 昨天3M) = 昨天3M
            # spread ≈ 昨天3M - 今天3M = -daily_change
            cash_est = today_3m - daily_change
            spread = cash_est - today_3m  # = -daily_change
            # 或者用昨日结算价直接估算: spread ≈ 昨天3M - 今天3M
            spread_v2 = yesterday_3m - today_3m

            print(f"[L1] LME铜3M: 今天={today_3m}, 昨天={yesterday_3m}, 变动={daily_change}")
            print(f"[L1] 估算C-3M升贴水: {spread_v2:.2f} (昨天-今天)")
            source = 'akshare_futures_foreign_commodity_realtime_CAD'
            confidence = 1.0

            # 使用 spread_v2 (昨天3M - 今天3M) 作为C-3M代理
            # 正值=backwardation(现货紧张), 负值=contango(供需宽松)
            return {'spread': round(spread_v2, 4), 'source': source, 'confidence': confidence}
    except Exception as e:
        print(f"[L1] 失败: {e}")
    
    # L2: 尝试其他LME数据源
    try:
        print("[L2] 尝试其他数据源...")
        # 尝试从历史CSV读取
        csv_path = r'D:\futures_v6\macro_engine\data\crawlers\CU\daily\LME_copper_cash_3m_spread.csv'
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            if len(df) > 0 and 's' in df.columns:
                last_spread = float(df.iloc[-1]['s'])
                if last_spread != 0:
                    print(f"[L2] CSV历史数据: spread={last_spread}")
                    return {'spread': last_spread, 'source': 'csv_historical', 'confidence': 0.9}
    except Exception as e:
        print(f"[L2] 失败: {e}")
    
    # L3: 付费数据源提示（不做采集，只记录日志）
    print("[L3] 前瞻网等付费源需要订阅，暂不使用")
    
    # L4: DB回补
    print("[L4] DB历史回补...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT raw_value FROM pit_factor_observations 
            WHERE factor_code = 'CU_LME_SPREAD' AND symbol = 'CU'
            ORDER BY obs_date DESC LIMIT 1
        """)
        result = cur.fetchone()
        conn.close()
        if result:
            spread = float(result[0])
            print(f"[L4] 兜底: spread={spread}")
            return {'spread': spread, 'source': 'db_fallback', 'confidence': 0.5}
    except Exception as e:
        print(f"[L4] 失败: {e}")
    
    return {'spread': 0.0, 'source': 'no_data', 'confidence': 0.0}

def fetch_lme_nickel_spread():
    """
    获取LME镍升贴水数据
    """
    spread = None
    source = None
    confidence = 0.0
    
    # L1: AKShare LME镍3个月实时行情 (NID)
    try:
        print("[L1] AKShare futures_foreign_commodity_realtime (LME镍3个月)...")
        df = ak.futures_foreign_commodity_realtime(['NID'])
        if df is not None and len(df) > 0:
            close_price = float(df['最新价'].values[0])
            yesterday_settle = float(df['昨日结算价'].values[0])
            
            # 价格变化作为spread代理
            spread = close_price - yesterday_settle
            
            print(f"[L1] LME镍3个月: 最新价={close_price}, 昨日结算={yesterday_settle}, 升贴水(代理)={spread:.2f}")
            source = 'akshare_futures_foreign_commodity_realtime_NID'
            confidence = 1.0
            return {'spread': spread, 'source': source, 'confidence': confidence}
    except Exception as e:
        print(f"[L1] 失败: {e}")
    
    # L2: 历史CSV
    try:
        print("[L2] 尝试其他数据源...")
        csv_path = r'D:\futures_v6\macro_engine\data\crawlers\NI\daily\LME_nickel_cash_3m_spread.csv'
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            if len(df) > 0 and 's' in df.columns:
                last_spread = float(df.iloc[-1]['s'])
                if last_spread != 0:
                    print(f"[L2] CSV历史数据: spread={last_spread}")
                    return {'spread': last_spread, 'source': 'csv_historical', 'confidence': 0.9}
    except Exception as e:
        print(f"[L2] 失败: {e}")
    
    # L4: DB回补
    print("[L4] DB历史回补...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT raw_value FROM pit_factor_observations 
            WHERE factor_code = 'NI_LME_SPREAD' AND symbol = 'NI'
            ORDER BY obs_date DESC LIMIT 1
        """)
        result = cur.fetchone()
        conn.close()
        if result:
            spread = float(result[0])
            print(f"[L4] 兜底: spread={spread}")
            return {'spread': spread, 'source': 'db_fallback', 'confidence': 0.5}
    except Exception as e:
        print(f"[L4] 失败: {e}")
    
    return {'spread': 0.0, 'source': 'no_data', 'confidence': 0.0}

def compute_spread_diff(factor_code, symbol, current_spread):
    """
    计算升贴水变化量（diff）
    
    Args:
        factor_code: 因子代码
        symbol: 品种代码
        current_spread: 当前升贴水值
    
    Returns:
        float: diff值
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT raw_value FROM pit_factor_observations 
            WHERE factor_code = ? AND symbol = ?
            ORDER BY obs_date DESC LIMIT 1
        """, (factor_code, symbol))
        result = cur.fetchone()
        conn.close()
        
        if result:
            prev_spread = float(result[0])
            diff = current_spread - prev_spread
            print(f"  [DIFF] 当前={current_spread:.2f}, 上次={prev_spread:.2f}, diff={diff:.2f}")
            return diff
    except Exception as e:
        print(f"  [DIFF] 计算失败: {e}")
    
    return 0.0

def compute_spread_event(spread, threshold=SPREAD_THRESHOLD):
    """
    计算升贴水事件标记
    
    Args:
        spread: 当前升贴水值
        threshold: 阈值，默认50 USD/吨
    
    Returns:
        int: 1 if spread > threshold, else 0
    """
    event = 1 if abs(spread) > threshold else 0
    print(f"  [EVENT] spread={spread:.2f}, threshold={threshold}, event={event}")
    return event

def save_spread_data(factor_code, symbol, pub_date, obs_date, spread, source, confidence):
    """保存升贴水数据到数据库"""
    try:
        ok = save_to_db(factor_code, symbol, pub_date, obs_date, spread,
                        source_confidence=confidence, source=source)
        if ok:
            print(f"[OK] {factor_code} = {spread:.2f} ({obs_date})")
        return ok
    except Exception as e:
        print(f"[FAIL] {factor_code} save error: {e}")
        return False

def main():
    ensure_table()
    pub_date, obs_date = get_pit_date()
    
    print("=" * 60)
    print("CU/NI LME升贴水事件驱动采集")
    print(f"pub_date: {pub_date}, obs_date: {obs_date}")
    print("=" * 60)
    
    results = {}
    
    # ========== 铜 ==========
    print("\n--- CU 沪铜 ---")
    cu_data = fetch_lme_copper_spread()
    
    if cu_data and cu_data.get('spread') is not None:
        cu_spread = cu_data['spread']
        cu_source = cu_data.get('source', 'unknown')
        cu_conf = cu_data.get('confidence', 0.5)
        
        # 保存原始升贴水
        save_spread_data('CU_LME_SPREAD', 'CU', pub_date, obs_date, 
                        cu_spread, cu_source, cu_conf)
        
        # 计算并保存diff
        cu_diff = compute_spread_diff('CU_LME_SPREAD', 'CU', cu_spread)
        save_spread_data('CU_LME_SPREAD_DIFF', 'CU', pub_date, obs_date,
                        cu_diff, f'{cu_source}_diff', cu_conf * 0.9)
        
        # 计算并保存event
        cu_event = compute_spread_event(cu_spread, SPREAD_THRESHOLD)
        save_spread_data('CU_LME_SPREAD_EVENT', 'CU', pub_date, obs_date,
                        float(cu_event), f'{cu_source}_event', cu_conf * 0.9)
        
        results['CU'] = cu_spread
    else:
        print("❌ CU_LME_SPREAD 采集失败")
        results['CU'] = None
    
    # ========== 镍 ==========
    print("\n--- NI 沪镍 ---")
    ni_data = fetch_lme_nickel_spread()
    
    if ni_data and ni_data.get('spread') is not None:
        ni_spread = ni_data['spread']
        ni_source = ni_data.get('source', 'unknown')
        ni_conf = ni_data.get('confidence', 0.5)
        
        # 保存原始升贴水
        save_spread_data('NI_LME_SPREAD', 'NI', pub_date, obs_date,
                        ni_spread, ni_source, ni_conf)
        
        # 计算并保存diff
        ni_diff = compute_spread_diff('NI_LME_SPREAD', 'NI', ni_spread)
        save_spread_data('NI_LME_SPREAD_DIFF', 'NI', pub_date, obs_date,
                        ni_diff, f'{ni_source}_diff', ni_conf * 0.9)
        
        # 计算并保存event
        ni_event = compute_spread_event(ni_spread, SPREAD_THRESHOLD)
        save_spread_data('NI_LME_SPREAD_EVENT', 'NI', pub_date, obs_date,
                        float(ni_event), f'{ni_source}_event', ni_conf * 0.9)
        
        results['NI'] = ni_spread
    else:
        print("❌ NI_LME_SPREAD 采集失败")
        results['NI'] = None
    
    print("\n" + "=" * 60)
    print("采集完成")
    print(f"CU: {results.get('CU')}")
    print(f"NI: {results.get('NI')}")
    print("=" * 60)
    
    return 0 if all(results.values()) else 1

if __name__ == "__main__":
    sys.exit(main())
