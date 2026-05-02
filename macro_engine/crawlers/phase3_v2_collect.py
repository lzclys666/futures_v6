# Phase 3 v2.0 综合采集脚本
# 品种: ZN, NI, PB, Y, P, EG, PP, FU, AG, AU, HC, RB
# 模式: 免费数据立即采集
# 日期: 2026-04-20

import os
import sys
import sqlite3
import traceback
from datetime import datetime, date
import pandas as pd
import numpy as np

sys.path.insert(0, 'D:/futures_v6/macro_engine')
os.chdir('D:/futures_v6/macro_engine')

# 尝试导入 akshare
try:
    import akshare as ak
    AKSHARE_OK = True
except ImportError:
    AKSHARE_OK = False
    print("[WARN] AKShare not installed, will use alternative methods")

DB_PATH = 'D:/futures_v6/macro_engine/pit_data.db'
LOG_DIR = 'D:/futures_v6/macro_engine/crawlers/logs'
os.makedirs(LOG_DIR, exist_ok=True)

def get_db_conn():
    return sqlite3.connect(DB_PATH, timeout=30)

def write_db(factor_code, obs_date, pub_date, raw_value, source, confidence):
    """写入数据库"""
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO factor_data 
            (factor_code, obs_date, pub_date, raw_value, source, source_confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (factor_code, str(obs_date), str(pub_date), float(raw_value), source, confidence, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] DB write failed for {factor_code}: {e}")
        return False

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}][{level}] {msg}")

# ============================================================
# P0: ZN 沪锌
# ============================================================
def collect_ZN():
    results = {"success": 0, "fail": 0, "factors": []}
    today = date.today().strftime("%Y-%m-%d")
    
    # 周一用上周五
    wd = datetime.now().weekday()
    obs_date = today if wd != 0 else (datetime.now() - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    
    try:
        # 1. 沪锌主力价格
        try:
            df = ak.futures_main_sina(symbol="ZN")
            if df is not None and len(df) > 0:
                val = float(df.iloc[-1]['close'])
                write_db("ZN_PRICE_MAIN", obs_date, today, val, "AKShare-futures_main_sina", 1.0)
                log(f"ZN: ZN_PRICE_MAIN = {val}", "OK")
                results["success"] += 1
                results["factors"].append(("ZN_PRICE_MAIN", val, "OK"))
        except Exception as e:
            log(f"ZN: ZN_PRICE_MAIN failed: {e}", "FAIL")
            results["fail"] += 1
            results["factors"].append(("ZN_PRICE_MAIN", None, f"FAIL: {e}"))
    except Exception as e:
        log(f"ZN block error: {e}", "FAIL")
    
    return results

# ============================================================
# P0: NI 沪镍
# ============================================================
def collect_NI():
    results = {"success": 0, "fail": 0, "factors": []}
    today = date.today().strftime("%Y-%m-%d")
    wd = datetime.now().weekday()
    obs_date = today if wd != 0 else (datetime.now() - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    
    try:
        # 沪镍主力价格
        try:
            df = ak.futures_main_sina(symbol="NI")
            if df is not None and len(df) > 0:
                val = float(df.iloc[-1]['close'])
                write_db("NI_PRICE_MAIN", obs_date, today, val, "AKShare-futures_main_sina", 1.0)
                log(f"NI: NI_PRICE_MAIN = {val}", "OK")
                results["success"] += 1
                results["factors"].append(("NI_PRICE_MAIN", val, "OK"))
        except Exception as e:
            log(f"NI: NI_PRICE_MAIN failed: {e}", "FAIL")
            results["fail"] += 1
            results["factors"].append(("NI_PRICE_MAIN", None, f"FAIL: {e}"))
    except Exception as e:
        log(f"NI block error: {e}", "FAIL")
    
    return results

# ============================================================
# P0: Y 豆油
# ============================================================
def collect_Y():
    results = {"success": 0, "fail": 0, "factors": []}
    today = date.today().strftime("%Y-%m-%d")
    wd = datetime.now().weekday()
    obs_date = today if wd != 0 else (datetime.now() - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    
    try:
        # CBOT大豆
        try:
            df = ak.futures_cbot_soybean()
            if df is not None and len(df) > 0:
                val = float(df.iloc[-1]['close'])
                write_db("Y_CBOT_SOYBEAN", obs_date, today, val, "AKShare-futures_cbot_soybean", 1.0)
                log(f"Y: Y_CBOT_SOYBEAN = {val}", "OK")
                results["success"] += 1
                results["factors"].append(("Y_CBOT_SOYBEAN", val, "OK"))
        except Exception as e:
            log(f"Y: Y_CBOT_SOYBEAN failed: {e}", "FAIL")
            results["fail"] += 1
            results["factors"].append(("Y_CBOT_SOYBEAN", None, f"FAIL: {e}"))
    except Exception as e:
        log(f"Y block error: {e}", "FAIL")
    
    return results

# ============================================================
# AU 黄金 + AG 白银（一起采集黄金白银比）
# ============================================================
def collect_AU_AG():
    results_au = {"success": 0, "fail": 0, "factors": []}
    results_ag = {"success": 0, "fail": 0, "factors": []}
    today = date.today().strftime("%Y-%m-%d")
    wd = datetime.now().weekday()
    obs_date = today if wd != 0 else (datetime.now() - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    
    au_price = None
    ag_price = None
    
    # 黄金现货价格
    try:
        df = ak.spot_glass_risk_lme()
        if df is not None and len(df) > 0:
            gold_row = df[df['合约'].str.contains('Gold', na=False)]
            if len(gold_row) > 0:
                au_price = float(gold_row.iloc[-1]['最新价'])
                write_db("AU_PRICE_SPOT", obs_date, today, au_price, "AKShare-spot_glass_risk_lme", 1.0)
                log(f"AU: AU_PRICE_SPOT = {au_price}", "OK")
                results_au["success"] += 1
                results_au["factors"].append(("AU_PRICE_SPOT", au_price, "OK"))
    except Exception as e:
        log(f"AU: gold spot failed: {e}", "FAIL")
        results_au["fail"] += 1
    
    # 白银现货价格
    try:
        df = ak.spot_glass_risk_lme()
        if df is not None and len(df) > 0:
            silver_row = df[df['合约'].str.contains('Silver', na=False)]
            if len(silver_row) > 0:
                ag_price = float(silver_row.iloc[-1]['最新价'])
                write_db("AG_PRICE_SPOT", obs_date, today, ag_price, "AKShare-spot_glass_risk_lme", 1.0)
                log(f"AG: AG_PRICE_SPOT = {ag_price}", "OK")
                results_ag["success"] += 1
                results_ag["factors"].append(("AG_PRICE_SPOT", ag_price, "OK"))
    except Exception as e:
        log(f"AG: silver spot failed: {e}", "FAIL")
        results_ag["fail"] += 1
    
    # 黄金白银比
    if au_price and ag_price and ag_price > 0:
        ratio = au_price / ag_price
        write_db("AU_AG_RATIO", obs_date, today, ratio, "AKShare-calculated", 1.0)
        log(f"AU/AG: ratio = {ratio:.4f}", "OK")
        results_au["success"] += 1
        results_au["factors"].append(("AU_AG_RATIO", ratio, "OK"))
    
    return results_au, results_ag

# ============================================================
# HC 热轧卷板
# ============================================================
def collect_HC():
    results = {"success": 0, "fail": 0, "factors": []}
    today = date.today().strftime("%Y-%m-%d")
    wd = datetime.now().weekday()
    obs_date = today if wd != 0 else (datetime.now() - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    
    # 制造业PMI (国家统计局 - 免费)
    try:
        try:
            df = ak.macro_china_pmi()
            if df is not None and len(df) > 0:
                # 找最新制造业PMI
                for col in df.columns:
                    if '制造' in str(col) or 'PMI' in str(col):
                        val = df[col].dropna().iloc[-1]
                        if isinstance(val, (int, float)) and 40 < val < 60:
                            write_db("HC_PMI_MFG", obs_date, today, float(val), "AKShare-macro_china_pmi", 1.0)
                            log(f"HC: HC_PMI_MFG = {val}", "OK")
                            results["success"] += 1
                            results["factors"].append(("HC_PMI_MFG", float(val), "OK"))
                            break
        except Exception as e:
            log(f"HC: PMI failed: {e}", "FAIL")
            results["fail"] += 1
            results["factors"].append(("HC_PMI_MFG", None, f"FAIL: {e}"))
    except Exception as e:
        log(f"HC block error: {e}", "FAIL")
    
    return results

# ============================================================
# RB 螺纹钢
# ============================================================
def collect_RB():
    results = {"success": 0, "fail": 0, "factors": []}
    today = date.today().strftime("%Y-%m-%d")
    wd = datetime.now().weekday()
    obs_date = today if wd != 0 else (datetime.now() - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    
    try:
        # RB主力价格
        try:
            df = ak.futures_main_sina(symbol="RB")
            if df is not None and len(df) > 0:
                val = float(df.iloc[-1]['close'])
                write_db("RB_PRICE_MAIN", obs_date, today, val, "AKShare-futures_main_sina", 1.0)
                log(f"RB: RB_PRICE_MAIN = {val}", "OK")
                results["success"] += 1
                results["factors"].append(("RB_PRICE_MAIN", val, "OK"))
        except Exception as e:
            log(f"RB: RB_PRICE_MAIN failed: {e}", "FAIL")
            results["fail"] += 1
            results["factors"].append(("RB_PRICE_MAIN", None, f"FAIL: {e}"))
    except Exception as e:
        log(f"RB block error: {e}", "FAIL")
    
    return results

# ============================================================
# FU 燃料油
# ============================================================
def collect_FU():
    results = {"success": 0, "fail": 0, "factors": []}
    today = date.today().strftime("%Y-%m-%d")
    wd = datetime.now().weekday()
    obs_date = today if wd != 0 else (datetime.now() - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    
    # WTI原油（Brent替代）
    try:
        try:
            df = ak.futures_main_sina(symbol="NYMEX")
            if df is not None and len(df) > 0:
                val = float(df.iloc[-1]['close'])
                write_db("FU_WTI_PRICE", obs_date, today, val, "AKShare-futures_main_sina(NYMEX)", 1.0)
                log(f"FU: FU_WTI_PRICE = {val}", "OK")
                results["success"] += 1
                results["factors"].append(("FU_WTI_PRICE", val, "OK"))
        except Exception as e:
            log(f"FU: WTI failed: {e}", "FAIL")
            results["fail"] += 1
            results["factors"].append(("FU_WTI_PRICE", None, f"FAIL: {e}"))
    except Exception as e:
        log(f"FU block error: {e}", "FAIL")
    
    return results

# ============================================================
# 主执行
# ============================================================
if __name__ == "__main__":
    log("=" * 60)
    log("Phase 3 v2.0 综合采集开始")
    log("=" * 60)
    
    all_results = {}
    
    # 并行度不够的顺序执行，但分批
    log("--- ZN 沪锌 ---")
    all_results["ZN"] = collect_ZN()
    
    log("--- NI 沪镍 ---")
    all_results["NI"] = collect_NI()
    
    log("--- Y 豆油 ---")
    all_results["Y"] = collect_Y()
    
    log("--- AU + AG 黄金白银 ---")
    au_res, ag_res = collect_AU_AG()
    all_results["AU"] = au_res
    all_results["AG"] = ag_res
    
    log("--- HC 热轧卷板 ---")
    all_results["HC"] = collect_HC()
    
    log("--- RB 螺纹钢 ---")
    all_results["RB"] = collect_RB()
    
    log("--- FU 燃料油 ---")
    all_results["FU"] = collect_FU()
    
    log("=" * 60)
    log("采集完成汇总")
    log("=" * 60)
    for sym, res in all_results.items():
        ok = res["success"]
        fail = res["fail"]
        total = ok + fail
        log(f"{sym}: {ok}/{total} 成功, {fail} 失败")
        for fac, val, status in res["factors"]:
            log(f"  {fac}: {val} -> {status}")
    
    log("=" * 60)
    log("结束")
    log("=" * 60)
