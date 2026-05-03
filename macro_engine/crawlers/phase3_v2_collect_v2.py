# -*- coding: utf-8 -*-
"""
Phase 3 v2.0 综合采集脚本
品种: ZN, NI, PB, Y, P, EG, PP, FU, AG, AU, HC, RB
模式: 免费数据立即采集
日期: 2026-04-20
"""

import sys
import os
import datetime
from pathlib import Path
import pandas as pd
import numpy as np

# 动态计算项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parent
while not (_PROJECT_ROOT / "macro_engine").exists() and _PROJECT_ROOT != _PROJECT_ROOT.parent:
    _PROJECT_ROOT = _PROJECT_ROOT.parent

sys.path.insert(0, str(_PROJECT_ROOT / "macro_engine" / "crawlers" / "common"))
from db_utils import save_to_db, get_latest_value, ensure_table

import akshare as ak

os.chdir(str(_PROJECT_ROOT / "macro_engine"))
ensure_table()

DB_PATH = str(_PROJECT_ROOT / "macro_engine" / "pit_data.db")
LOG_DIR = str(_PROJECT_ROOT / "macro_engine" / "crawlers" / "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def log(msg, level="INFO"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}][{level}] {msg}")

def get_obs_date():
    """获取PIT观测日期（周一用上周五）"""
    today = datetime.date.today()
    dow = today.weekday()
    if dow == 0:  # 周一
        obs_date = today - pd.Timedelta(days=2)
    elif dow == 6:  # 周日
        obs_date = today - pd.Timedelta(days=2)
    else:
        obs_date = today
    return today, obs_date

# ============================================================
# 工具函数
# ============================================================

def get_last_trading_day(days_back=1):
    """获取最近交易日（跳过周末）"""
    d = datetime.date.today()
    while days_back > 0:
        d = d - datetime.timedelta(days=1)
        if d.weekday() < 5:
            days_back -= 1
    return d

def write(factor_code, symbol, raw_value, source, confidence=1.0):
    """写入数据库，带异常处理"""
    pub_date, obs_date = get_obs_date()
    try:
        ok = save_to_db(factor_code, symbol, pub_date, obs_date, raw_value, 
                       source_confidence=confidence, source=source)
        if ok:
            log(f"DB写入成功: {factor_code} = {raw_value}")
            return True
    except Exception as e:
        log(f"DB写入失败: {factor_code}: {e}", "ERROR")
    return False

# ============================================================
# ZN 沪锌
# ============================================================
def collect_ZN():
    results = []
    pub_date, obs_date = get_obs_date()
    sym = "ZN"
    
    # 1. ZN主力合约价格
    try:
        df = ak.futures_main_sina(symbol='ZN0')
        if df is not None and len(df) > 0:
            last = df.iloc[-1]
            val = float(last.iloc[4])  # 收盘价
            if 15000 <= val <= 35000:
                write("ZN_FUT_CLOSE", sym, val, "AKShare-futures_main_sina(ZN0)")
                results.append(("ZN_FUT_CLOSE", val, "OK"))
            else:
                results.append(("ZN_FUT_CLOSE", val, f"WARN: 超出合理范围[15000,35000]"))
    except Exception as e:
        results.append(("ZN_FUT_CLOSE", None, f"FAIL: {e}"))
    
    # 2. LME锌库存
    try:
        df = ak.futures_inventory_em(symbol='zn')
        if df is not None and len(df) > 0:
            last = df.iloc[-1]
            val = float(last.iloc[1])  # 库存量
            if 50000 <= val <= 300000:
                write("ZN_DCE_INV", sym, val, "AKShare-futures_inventory_em(zn)")
                results.append(("ZN_DCE_INV", val, "OK"))
            else:
                results.append(("ZN_DCE_INV", val, f"WARN: 超出合理范围[50000,300000]"))
    except Exception as e:
        results.append(("ZN_DCE_INV", None, f"FAIL: {e}"))
    
    return results

# ============================================================
# NI 沪镍
# ============================================================
def collect_NI():
    results = []
    pub_date, obs_date = get_obs_date()
    sym = "NI"
    
    # 1. NI主力合约价格
    try:
        df = ak.futures_main_sina(symbol='NI0')
        if df is not None and len(df) > 0:
            last = df.iloc[-1]
            val = float(last.iloc[4])
            if 80000 <= val <= 250000:
                write("NI_FUT_CLOSE", sym, val, "AKShare-futures_main_sina(NI0)")
                results.append(("NI_FUT_CLOSE", val, "OK"))
            else:
                results.append(("NI_FUT_CLOSE", val, f"WARN: 超出合理范围[80000,250000]"))
    except Exception as e:
        results.append(("NI_FUT_CLOSE", None, f"FAIL: {e}"))
    
    # 2. LME镍库存
    try:
        df = ak.futures_inventory_em(symbol='ni')
        if df is not None and len(df) > 0:
            last = df.iloc[-1]
            val = float(last.iloc[1])
            if 30000 <= val <= 150000:
                write("NI_DCE_INV", sym, val, "AKShare-futures_inventory_em(ni)")
                results.append(("NI_DCE_INV", val, "OK"))
            else:
                results.append(("NI_DCE_INV", val, f"WARN: 超出合理范围[30000,150000]"))
    except Exception as e:
        results.append(("NI_DCE_INV", None, f"FAIL: {e}"))
    
    return results

# ============================================================
# Y 豆油
# ============================================================
def collect_Y():
    results = []
    pub_date, obs_date = get_obs_date()
    sym = "Y"
    
    # CBOT大豆 (使用 futures_foreign_hist, symbol='ZSD')
    try:
        df = ak.futures_foreign_hist(symbol='ZSD')
        if df is not None and len(df) > 0:
            val = float(df.iloc[-1]['close'])
            if 800 <= val <= 2000:
                write("Y_CBOT_SOYBEAN", sym, val, "AKShare-futures_foreign_hist(ZSD)")
                results.append(("Y_CBOT_SOYBEAN", val, "OK"))
            else:
                results.append(("Y_CBOT_SOYBEAN", val, f"WARN: 超出合理范围[800,2000]"))
    except Exception as e:
        results.append(("Y_CBOT_SOYBEAN", None, f"FAIL: {e}"))
    
    # Y主力合约价格
    try:
        df = ak.futures_main_sina(symbol='Y0')
        if df is not None and len(df) > 0:
            last = df.iloc[-1]
            val = float(last.iloc[4])
            if 5000 <= val <= 15000:
                write("Y_FUT_CLOSE", sym, val, "AKShare-futures_main_sina(Y0)")
                results.append(("Y_FUT_CLOSE", val, "OK"))
            else:
                results.append(("Y_FUT_CLOSE", val, f"WARN: 超出合理范围[5000,15000]"))
    except Exception as e:
        results.append(("Y_FUT_CLOSE", None, f"FAIL: {e}"))
    
    return results

# ============================================================
# P 棕榈油
# ============================================================
def collect_P():
    results = []
    pub_date, obs_date = get_obs_date()
    sym = "P"
    
    try:
        df = ak.futures_main_sina(symbol='P0')
        if df is not None and len(df) > 0:
            last = df.iloc[-1]
            val = float(last.iloc[4])
            if 4000 <= val <= 12000:
                write("P_FUT_CLOSE", sym, val, "AKShare-futures_main_sina(P0)")
                results.append(("P_FUT_CLOSE", val, "OK"))
            else:
                results.append(("P_FUT_CLOSE", val, f"WARN: 超出合理范围[4000,12000]"))
    except Exception as e:
        results.append(("P_FUT_CLOSE", None, f"FAIL: {e}"))
    
    return results

# ============================================================
# EG 乙二醇
# ============================================================
def collect_EG():
    results = []
    pub_date, obs_date = get_obs_date()
    sym = "EG"
    
    try:
        df = ak.futures_main_sina(symbol='EG0')
        if df is not None and len(df) > 0:
            last = df.iloc[-1]
            val = float(last.iloc[4])
            if 3000 <= val <= 8000:
                write("EG_FUT_CLOSE", sym, val, "AKShare-futures_main_sina(EG0)")
                results.append(("EG_FUT_CLOSE", val, "OK"))
            else:
                results.append(("EG_FUT_CLOSE", val, f"WARN: 超出合理范围[3000,8000]"))
    except Exception as e:
        results.append(("EG_FUT_CLOSE", None, f"FAIL: {e}"))
    
    return results

# ============================================================
# PP 聚丙烯
# ============================================================
def collect_PP():
    results = []
    pub_date, obs_date = get_obs_date()
    sym = "PP"
    
    try:
        df = ak.futures_main_sina(symbol='PP0')
        if df is not None and len(df) > 0:
            last = df.iloc[-1]
            val = float(last.iloc[4])
            if 6000 <= val <= 12000:
                write("PP_FUT_CLOSE", sym, val, "AKShare-futures_main_sina(PP0)")
                results.append(("PP_FUT_CLOSE", val, "OK"))
            else:
                results.append(("PP_FUT_CLOSE", val, f"WARN: 超出合理范围[6000,12000]"))
    except Exception as e:
        results.append(("PP_FUT_CLOSE", None, f"FAIL: {e}"))
    
    return results

# ============================================================
# FU 燃料油
# ============================================================
def collect_FU():
    results = []
    pub_date, obs_date = get_obs_date()
    sym = "FU"
    
    # WTI原油价格（Brent替代，使用CL）
    try:
        df = ak.futures_foreign_hist(symbol='CL')
        if df is not None and len(df) > 0:
            val = float(df.iloc[-1]['close'])
            if 40 <= val <= 200:
                write("FU_WTI_PRICE", sym, val, "AKShare-futures_foreign_hist(CL)")
                results.append(("FU_WTI_PRICE", val, "OK"))
            else:
                results.append(("FU_WTI_PRICE", val, f"WARN: 超出合理范围[40,200]"))
    except Exception as e:
        results.append(("FU_WTI_PRICE", None, f"FAIL: {e}"))
    
    # FU主力合约价格
    try:
        df = ak.futures_main_sina(symbol='FU0')
        if df is not None and len(df) > 0:
            last = df.iloc[-1]
            val = float(last.iloc[4])
            if 2000 <= val <= 6000:
                write("FU_FUT_CLOSE", sym, val, "AKShare-futures_main_sina(FU0)")
                results.append(("FU_FUT_CLOSE", val, "OK"))
            else:
                results.append(("FU_FUT_CLOSE", val, f"WARN: 超出合理范围[2000,6000]"))
    except Exception as e:
        results.append(("FU_FUT_CLOSE", None, f"FAIL: {e}"))
    
    return results

# ============================================================
# AU 黄金
# ============================================================
def collect_AU():
    results = []
    pub_date, obs_date = get_obs_date()
    sym = "AU"
    
    # AU主力合约价格
    try:
        df = ak.futures_main_sina(symbol='AU0')
        if df is not None and len(df) > 0:
            last = df.iloc[-1]
            val = float(last.iloc[4])
            if 500 <= val <= 3000:
                write("AU_FUT_CLOSE", sym, val, "AKShare-futures_main_sina(AU0)")
                results.append(("AU_FUT_CLOSE", val, "OK"))
            else:
                results.append(("AU_FUT_CLOSE", val, f"WARN: 超出合理范围[500,3000]"))
    except Exception as e:
        results.append(("AU_FUT_CLOSE", None, f"FAIL: {e}"))
    
    # SGE黄金现货价格
    try:
        df = ak.spot_golden_benchmark_sge()
        if df is not None and len(df) > 0:
            last = df.iloc[-1]
            # 列: 日期, 现货价, 伦敦银合约定盘价(美元/盎司), ...
            val = float(last.iloc[1])  # 现货价
            if 500 <= val <= 3000:
                write("AU_SPOT_SGE", sym, val, "AKShare-spot_golden_benchmark_sge")
                results.append(("AU_SPOT_SGE", val, "OK"))
            else:
                results.append(("AU_SPOT_SGE", val, f"WARN: 超出合理范围[500,3000]"))
    except Exception as e:
        results.append(("AU_SPOT_SGE", None, f"FAIL: {e}"))
    
    # 黄金白银比
    try:
        au_df = ak.spot_golden_benchmark_sge()
        ag_df = ak.macro_china_fx_gold()  # 可能是月度数据
        if au_df is not None and len(au_df) > 0:
            au_val = float(au_df.iloc[-1].iloc[1])
            if ag_df is not None and len(ag_df) > 0:
                # 尝试找白银价格
                ag_val = None
                for col in ag_df.columns:
                    if '白银' in str(col) or 'silver' in str(col).lower():
                        ag_val = float(ag_df.iloc[-1][col])
                        break
                if ag_val and ag_val > 0:
                    ratio = au_val / ag_val
                    write("AG_MACRO_GOLD_SILVER_RATIO", "AG", ratio, "AKShare-calculated")
                    results.append(("AU_AG_RATIO", ratio, "OK"))
    except Exception as e:
        results.append(("AU_AG_RATIO", None, f"FAIL: {e}"))
    
    return results

# ============================================================
# AG 白银
# ============================================================
def collect_AG():
    results = []
    pub_date, obs_date = get_obs_date()
    sym = "AG"
    
    # AG主力合约价格
    try:
        df = ak.futures_main_sina(symbol='AG0')
        if df is not None and len(df) > 0:
            last = df.iloc[-1]
            val = float(last.iloc[4])
            if 3000 <= val <= 30000:
                write("AG_FUT_CLOSE", sym, val, "AKShare-futures_main_sina(AG0)")
                results.append(("AG_FUT_CLOSE", val, "OK"))
            else:
                results.append(("AG_FUT_CLOSE", val, f"WARN: 超出合理范围[3000,30000]"))
    except Exception as e:
        results.append(("AG_FUT_CLOSE", None, f"FAIL: {e}"))
    
    return results

# ============================================================
# HC 热轧卷板
# ============================================================
def collect_HC():
    results = []
    pub_date, obs_date = get_obs_date()
    sym = "HC"
    
    # HC主力合约价格
    try:
        df = ak.futures_main_sina(symbol='HC0')
        if df is not None and len(df) > 0:
            last = df.iloc[-1]
            val = float(last.iloc[4])
            if 2000 <= val <= 6000:
                write("HC_FUT_CLOSE", sym, val, "AKShare-futures_main_sina(HC0)")
                results.append(("HC_FUT_CLOSE", val, "OK"))
            else:
                results.append(("HC_FUT_CLOSE", val, f"WARN: 超出合理范围[2000,6000]"))
    except Exception as e:
        results.append(("HC_FUT_CLOSE", None, f"FAIL: {e}"))
    
    # 制造业PMI - 使用iloc直接取第2列（制造业PMI）
    try:
        df = ak.macro_china_pmi()
        if df is not None and len(df) > 0:
            # 列顺序: 月份, 制造业PMI, 制造业同比, 非制造业PMI, 非制造业同比
            val = float(df.iloc[-1, 1])  # 制造业PMI
            if 40 <= val <= 60:
                write("HC_PMI_MFG", sym, val, "AKShare-macro_china_pmi")
                results.append(("HC_PMI_MFG", val, "OK"))
            else:
                results.append(("HC_PMI_MFG", val, f"WARN: 超出合理范围[40,60]"))
    except Exception as e:
        results.append(("HC_PMI_MFG", None, f"FAIL: {e}"))
    
    return results

# ============================================================
# RB 螺纹钢
# ============================================================
def collect_RB():
    results = []
    pub_date, obs_date = get_obs_date()
    sym = "RB"
    
    # RB主力合约价格
    try:
        df = ak.futures_main_sina(symbol='RB0')
        if df is not None and len(df) > 0:
            last = df.iloc[-1]
            val = float(last.iloc[4])
            if 2000 <= val <= 6000:
                write("RB_FUT_CLOSE", sym, val, "AKShare-futures_main_sina(RB0)")
                results.append(("RB_FUT_CLOSE", val, "OK"))
            else:
                results.append(("RB_FUT_CLOSE", val, f"WARN: 超出合理范围[2000,6000]"))
    except Exception as e:
        results.append(("RB_FUT_CLOSE", None, f"FAIL: {e}"))
    
    # RB-HC价差（螺纹钢-热轧卷板）
    try:
        rb_df = ak.futures_main_sina(symbol='RB0')
        hc_df = ak.futures_main_sina(symbol='HC0')
        if rb_df is not None and len(rb_df) > 0 and hc_df is not None and len(hc_df) > 0:
            rb_val = float(rb_df.iloc[-1].iloc[4])
            hc_val = float(hc_df.iloc[-1].iloc[4])
            spread = rb_val - hc_val
            write("RB_SPD_RB_HC", sym, spread, "AKShare-calculated(RB-HC)")
            results.append(("RB_SPD_RB_HC", spread, "OK"))
    except Exception as e:
        results.append(("RB_SPD_RB_HC", None, f"FAIL: {e}"))
    
    return results

# ============================================================
# PB 沪铅
# ============================================================
def collect_PB():
    results = []
    pub_date, obs_date = get_obs_date()
    sym = "PB"
    
    # PB主力合约价格
    try:
        df = ak.futures_main_sina(symbol='PB0')
        if df is not None and len(df) > 0:
            last = df.iloc[-1]
            val = float(last.iloc[4])
            if 10000 <= val <= 25000:
                write("PB_FUT_CLOSE", sym, val, "AKShare-futures_main_sina(PB0)")
                results.append(("PB_FUT_CLOSE", val, "OK"))
            else:
                results.append(("PB_FUT_CLOSE", val, f"WARN: 超出合理范围[10000,25000]"))
    except Exception as e:
        results.append(("PB_FUT_CLOSE", None, f"FAIL: {e}"))
    
    return results

# ============================================================
# 主执行
# ============================================================
if __name__ == "__main__":
    log("=" * 60)
    log("Phase 3 v2.0 综合采集开始")
    log("=" * 60)
    
    all_results = {}
    
    log("--- ZN 沪锌 ---")
    all_results["ZN"] = collect_ZN()
    
    log("--- NI 沪镍 ---")
    all_results["NI"] = collect_NI()
    
    log("--- Y 豆油 ---")
    all_results["Y"] = collect_Y()
    
    log("--- P 棕榈油 ---")
    all_results["P"] = collect_P()
    
    log("--- EG 乙二醇 ---")
    all_results["EG"] = collect_EG()
    
    log("--- PP 聚丙烯 ---")
    all_results["PP"] = collect_PP()
    
    log("--- FU 燃料油 ---")
    all_results["FU"] = collect_FU()
    
    log("--- AU 黄金 ---")
    all_results["AU"] = collect_AU()
    
    log("--- AG 白银 ---")
    all_results["AG"] = collect_AG()
    
    log("--- HC 热轧卷板 ---")
    all_results["HC"] = collect_HC()
    
    log("--- RB 螺纹钢 ---")
    all_results["RB"] = collect_RB()
    
    log("--- PB 沪铅 ---")
    all_results["PB"] = collect_PB()
    
    log("=" * 60)
    log("采集完成汇总")
    log("=" * 60)
    
    total_success = 0
    total_fail = 0
    
    for sym, res in all_results.items():
        ok = sum(1 for _, _, s in res if "OK" in s)
        fail = len(res) - ok
        total_success += ok
        total_fail += fail
        log(f"{sym}: {ok}/{len(res)} 成功, {fail} 失败")
        for fac, val, status in res:
            log(f"  {fac}: {val} -> {status}")
    
    log("=" * 60)
    log(f"总计: {total_success} 成功, {total_fail} 失败")
    log("=" * 60)
