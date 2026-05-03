# -*- coding: utf-8 -*-
# Phase 3 v2.0 缁煎悎閲囬泦鑴氭湰
# 鍝佺: ZN, NI, PB, Y, P, EG, PP, FU, AG, AU, HC, RB
# 妯″紡: 鍏嶈垂鏁版嵁绔嬪嵆閲囬泦
# 鏃ユ湡: 2026-04-20

import os
import sys
import sqlite3
import traceback
from datetime import datetime, date
import pandas as pd
import numpy as np
from config.paths import MACRO_ENGINE, PIT_DB, CRAWLER_LOGS

sys.path.insert(0, str(MACRO_ENGINE))
os.chdir(str(MACRO_ENGINE))

# 灏濊瘯瀵煎叆 akshare
try:
    import akshare as ak
    AKSHARE_OK = True
except ImportError:
    AKSHARE_OK = False
    print("[WARN] AKShare not installed, will use alternative methods")

DB_PATH = str(PIT_DB)
LOG_DIR = str(CRAWLER_LOGS)
os.makedirs(LOG_DIR, exist_ok=True)

def get_db_conn():
    return sqlite3.connect(DB_PATH, timeout=30)

def write_db(factor_code, obs_date, pub_date, raw_value, source, confidence):
    """鍐欏叆鏁版嵁搴?""
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
# P0: ZN 娌攲
# ============================================================
def collect_ZN():
    results = {"success": 0, "fail": 0, "factors": []}
    today = date.today().strftime("%Y-%m-%d")
    
    # 鍛ㄤ竴鐢ㄤ笂鍛ㄤ簲
    wd = datetime.now().weekday()
    obs_date = today if wd != 0 else (datetime.now() - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    
    try:
        # 1. 娌攲涓诲姏浠锋牸
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
# P0: NI 娌晬
# ============================================================
def collect_NI():
    results = {"success": 0, "fail": 0, "factors": []}
    today = date.today().strftime("%Y-%m-%d")
    wd = datetime.now().weekday()
    obs_date = today if wd != 0 else (datetime.now() - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    
    try:
        # 娌晬涓诲姏浠锋牸
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
# P0: Y 璞嗘补
# ============================================================
def collect_Y():
    results = {"success": 0, "fail": 0, "factors": []}
    today = date.today().strftime("%Y-%m-%d")
    wd = datetime.now().weekday()
    obs_date = today if wd != 0 else (datetime.now() - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    
    try:
        # CBOT澶ц眴
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
# AU 榛勯噾 + AG 鐧介摱锛堜竴璧烽噰闆嗛粍閲戠櫧閾舵瘮锛?
# ============================================================
def collect_AU_AG():
    results_au = {"success": 0, "fail": 0, "factors": []}
    results_ag = {"success": 0, "fail": 0, "factors": []}
    today = date.today().strftime("%Y-%m-%d")
    wd = datetime.now().weekday()
    obs_date = today if wd != 0 else (datetime.now() - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    
    au_price = None
    ag_price = None
    
    # 榛勯噾鐜拌揣浠锋牸
    try:
        df = ak.spot_glass_risk_lme()
        if df is not None and len(df) > 0:
            gold_row = df[df['鍚堢害'].str.contains('Gold', na=False)]
            if len(gold_row) > 0:
                au_price = float(gold_row.iloc[-1]['鏈€鏂颁环'])
                write_db("AU_PRICE_SPOT", obs_date, today, au_price, "AKShare-spot_glass_risk_lme", 1.0)
                log(f"AU: AU_PRICE_SPOT = {au_price}", "OK")
                results_au["success"] += 1
                results_au["factors"].append(("AU_PRICE_SPOT", au_price, "OK"))
    except Exception as e:
        log(f"AU: gold spot failed: {e}", "FAIL")
        results_au["fail"] += 1
    
    # 鐧介摱鐜拌揣浠锋牸
    try:
        df = ak.spot_glass_risk_lme()
        if df is not None and len(df) > 0:
            silver_row = df[df['鍚堢害'].str.contains('Silver', na=False)]
            if len(silver_row) > 0:
                ag_price = float(silver_row.iloc[-1]['鏈€鏂颁环'])
                write_db("AG_PRICE_SPOT", obs_date, today, ag_price, "AKShare-spot_glass_risk_lme", 1.0)
                log(f"AG: AG_PRICE_SPOT = {ag_price}", "OK")
                results_ag["success"] += 1
                results_ag["factors"].append(("AG_PRICE_SPOT", ag_price, "OK"))
    except Exception as e:
        log(f"AG: silver spot failed: {e}", "FAIL")
        results_ag["fail"] += 1
    
    # 榛勯噾鐧介摱姣?
    if au_price and ag_price and ag_price > 0:
        ratio = au_price / ag_price
        write_db("AU_AG_RATIO", obs_date, today, ratio, "AKShare-calculated", 1.0)
        log(f"AU/AG: ratio = {ratio:.4f}", "OK")
        results_au["success"] += 1
        results_au["factors"].append(("AU_AG_RATIO", ratio, "OK"))
    
    return results_au, results_ag

# ============================================================
# HC 鐑涧鍗锋澘
# ============================================================
def collect_HC():
    results = {"success": 0, "fail": 0, "factors": []}
    today = date.today().strftime("%Y-%m-%d")
    wd = datetime.now().weekday()
    obs_date = today if wd != 0 else (datetime.now() - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    
    # 鍒堕€犱笟PMI (鍥藉缁熻灞€ - 鍏嶈垂)
    try:
        try:
            df = ak.macro_china_pmi()
            if df is not None and len(df) > 0:
                # 鎵炬渶鏂板埗閫犱笟PMI
                for col in df.columns:
                    if '鍒堕€? in str(col) or 'PMI' in str(col):
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
# RB 铻虹汗閽?
# ============================================================
def collect_RB():
    results = {"success": 0, "fail": 0, "factors": []}
    today = date.today().strftime("%Y-%m-%d")
    wd = datetime.now().weekday()
    obs_date = today if wd != 0 else (datetime.now() - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    
    try:
        # RB涓诲姏浠锋牸
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
# FU 鐕冩枡娌?
# ============================================================
def collect_FU():
    results = {"success": 0, "fail": 0, "factors": []}
    today = date.today().strftime("%Y-%m-%d")
    wd = datetime.now().weekday()
    obs_date = today if wd != 0 else (datetime.now() - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    
    # WTI鍘熸补锛圔rent鏇夸唬锛?
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
# 涓绘墽琛?
# ============================================================
if __name__ == "__main__":
    log("=" * 60)
    log("Phase 3 v2.0 缁煎悎閲囬泦寮€濮?)
    log("=" * 60)
    
    all_results = {}
    
    # 骞惰搴︿笉澶熺殑椤哄簭鎵ц锛屼絾鍒嗘壒
    log("--- ZN 娌攲 ---")
    all_results["ZN"] = collect_ZN()
    
    log("--- NI 娌晬 ---")
    all_results["NI"] = collect_NI()
    
    log("--- Y 璞嗘补 ---")
    all_results["Y"] = collect_Y()
    
    log("--- AU + AG 榛勯噾鐧介摱 ---")
    au_res, ag_res = collect_AU_AG()
    all_results["AU"] = au_res
    all_results["AG"] = ag_res
    
    log("--- HC 鐑涧鍗锋澘 ---")
    all_results["HC"] = collect_HC()
    
    log("--- RB 铻虹汗閽?---")
    all_results["RB"] = collect_RB()
    
    log("--- FU 鐕冩枡娌?---")
    all_results["FU"] = collect_FU()
    
    log("=" * 60)
    log("閲囬泦瀹屾垚姹囨€?)
    log("=" * 60)
    for sym, res in all_results.items():
        ok = res["success"]
        fail = res["fail"]
        total = ok + fail
        log(f"{sym}: {ok}/{total} 鎴愬姛, {fail} 澶辫触")
        for fac, val, status in res["factors"]:
            log(f"  {fac}: {val} -> {status}")
    
    log("=" * 60)
    log("缁撴潫")
    log("=" * 60)
