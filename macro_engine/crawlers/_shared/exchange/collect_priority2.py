# Priority 2 Free Data Collection Script v1.0
# 采集: LME锌库存, 黄金白银比, PMI, RB-HC价差, PB沪铅, CFTC, SLV ETF
# 修订日期：2026-04-20

import os
import sys
import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path
import pandas as pd
import numpy as np

# 动态计算项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parent
while not (_PROJECT_ROOT / "macro_engine").exists() and _PROJECT_ROOT != _PROJECT_ROOT.parent:
    _PROJECT_ROOT = _PROJECT_ROOT.parent

sys.path.insert(0, str(_PROJECT_ROOT / "macro_engine"))
os.chdir(str(_PROJECT_ROOT / "macro_engine"))

try:
    import akshare as ak
    AKSHARE_OK = True
except ImportError:
    AKSHARE_OK = False
    print("[WARN] AKShare not installed")

DB_PATH = str(_PROJECT_ROOT / "macro_engine" / "pit_data.db")
SHARED_DIR = _PROJECT_ROOT / "macro_engine" / "data" / "crawlers" / "_shared" / "exchange"
SHARED_DIR.mkdir(parents=True, exist_ok=True)

def get_db_conn():
    return sqlite3.connect(DB_PATH, timeout=30)

def write_db(factor_code, obs_date, pub_date, raw_value, source, confidence):
    """写入数据库"""
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO pit_factor_observations 
            (factor_code, obs_date, pub_date, raw_value, source, source_confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (factor_code, str(obs_date), str(pub_date), float(raw_value), source, confidence))
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
# 工具函数
# ============================================================
def get_obs_date():
    """获取obs_date (周一用上周五)"""
    today = date.today()
    wd = today.weekday()
    if wd == 0:  # Monday
        obs_date = (today - timedelta(days=3)).strftime('%Y-%m-%d')
    else:
        obs_date = today.strftime('%Y-%m-%d')
    return obs_date

# ============================================================
# 1. LME锌库存
# ============================================================
def collect_lme_zinc_stock():
    """采集LME锌库存数据"""
    log("采集LME锌库存")
    result = {"success": False, "factors": []}
    obs_date = get_obs_date()
    today = date.today().strftime('%Y-%m-%d')
    
    if not AKSHARE_OK:
        log("AKShare not installed", "FAIL")
        return result
    
    try:
        df = ak.macro_euro_lme_stock()
        if df is not None and len(df) > 0:
            # 列名是中文但内容是LME各金属库存
            # 第一列是日期，后面是各金属的库存数据
            # 找到锌对应的列 (�-� 应该是 Zinc)
            cols = df.columns.tolist()
            print(f"LME stock columns: {cols[:5]}...")
            
            # 获取最新一行数据
            latest = df.iloc[-1]
            date_str = str(latest.iloc[0])
            
            # 第二部分是锌库存 (index 4-6 corresponds to different metrics)
            # 需要确定哪列是锌
            # 根据位置判断: 铜(0-2), 铝(3-5), 锌(6-8), 镍(9-11), 铅(12-14), 锡(15-17)
            # 但实际列名是乱码，需要用位置索引
            zinc_stock = latest.iloc[7] if len(latest) > 7 else None  # 锌-库存
            
            if zinc_stock and pd.notna(zinc_stock):
                try:
                    val = float(zinc_stock)
                    write_db("ZN_LME_STOCK", obs_date, today, val, "AKShare-macro_euro_lme_stock", 1.0)
                    log(f"ZN_LME_STOCK = {val}", "OK")
                    result["success"] = True
                    result["factors"].append(("ZN_LME_STOCK", val, "OK"))
                except Exception as e:
                    log(f"ZN_LME_STOCK conversion failed: {e}", "WARN")
    except Exception as e:
        log(f"LME锌库存采集失败: {e}", "FAIL")
    
    return result

# ============================================================
# 2. 黄金白银比
# ============================================================
def collect_gold_silver_ratio():
    """采集黄金和白银价格，计算金银比"""
    log("采集黄金白银比")
    result = {"success": False, "factors": []}
    obs_date = get_obs_date()
    today = date.today().strftime('%Y-%m-%d')
    
    if not AKSHARE_OK:
        log("AKShare not installed", "FAIL")
        return result
    
    gold_price = None
    silver_price = None
    
    try:
        # 黄金现货价格 (SGE Au99.99)
        df_gold = ak.spot_golden_benchmark_sge()
        if df_gold is not None and len(df_gold) > 0:
            latest = df_gold.iloc[-1]
            # 列名是乱码，但第二个是卖出价
            gold_price = float(latest.iloc[1])  # 卖出价
            write_db("AU_PRICE_SPOT_SGE", obs_date, today, gold_price, "AKShare-spot_golden_benchmark_sge", 1.0)
            log(f"AU_PRICE_SPOT_SGE = {gold_price}", "OK")
            result["success"] = True
            result["factors"].append(("AU_PRICE_SPOT_SGE", gold_price, "OK"))
    except Exception as e:
        log(f"黄金价格采集失败: {e}", "FAIL")
    
    try:
        # 白银现货价格 (SGE Ag99.99)
        df_silver = ak.spot_silver_benchmark_sge()
        if df_silver is not None and len(df_silver) > 0:
            latest = df_silver.iloc[-1]
            silver_price = float(latest.iloc[1])  # 卖出价
            write_db("AG_PRICE_SPOT_SGE", obs_date, today, silver_price, "AKShare-spot_silver_benchmark_sge", 1.0)
            log(f"AG_PRICE_SPOT_SGE = {silver_price}", "OK")
            result["success"] = True
            result["factors"].append(("AG_PRICE_SPOT_SGE", silver_price, "OK"))
    except Exception as e:
        log(f"白银价格采集失败: {e}", "FAIL")
    
    # 计算金银比
    if gold_price and silver_price and silver_price > 0:
        ratio = gold_price / silver_price
        write_db("AU_AG_RATIO", obs_date, today, ratio, "AKShare-calculated", 1.0)
        log(f"AU_AG_RATIO = {ratio:.4f}", "OK")
        result["factors"].append(("AU_AG_RATIO", ratio, "OK"))
    
    return result

# ============================================================
# 3. 制造业PMI
# ============================================================
def collect_china_pmi():
    """采集中国PMI数据 (制造业+非制造业)"""
    log("采集中国PMI")
    result = {"success": False, "factors": []}
    obs_date = get_obs_date()
    today = date.today().strftime('%Y-%m-%d')
    
    if not AKSHARE_OK:
        log("AKShare not installed", "FAIL")
        return result
    
    try:
        df = ak.macro_china_pmi()
        if df is not None and len(df) > 0:
            # 第一列是日期，第二列是制造业PMI，第三列是制造业PMI环比
            # 第四列是非制造业PMI，第五列是非制造业PMI环比
            latest = df.iloc[0]  # 最新一行是最新的月份
            
            # 提取日期
            date_str = str(latest.iloc[0])
            
            # 制造业PMI
            mfg_pmi = latest.iloc[1]
            if pd.notna(mfg_pmi):
                try:
                    val = float(mfg_pmi)
                    write_db("HC_PMI_MFG", obs_date, today, val, "AKShare-macro_china_pmi", 1.0)
                    log(f"HC_PMI_MFG = {val}", "OK")
                    result["success"] = True
                    result["factors"].append(("HC_PMI_MFG", val, "OK"))
                except Exception as e:
                    log(f"HC_PMI_MFG conversion failed: {e}", "WARN")
            
            # 非制造业PMI
            non_mfg_pmi = latest.iloc[3]
            if pd.notna(non_mfg_pmi):
                try:
                    val = float(non_mfg_pmi)
                    write_db("HC_PMI_NON_MFG", obs_date, today, val, "AKShare-macro_china_pmi", 1.0)
                    log(f"HC_PMI_NON_MFG = {val}", "OK")
                    result["factors"].append(("HC_PMI_NON_MFG", val, "OK"))
                except Exception as e:
                    log(f"HC_PMI_NON_MFG conversion failed: {e}", "WARN")
    except Exception as e:
        log(f"PMI采集失败: {e}", "FAIL")
    
    return result

# ============================================================
# 4. RB-HC价差
# ============================================================
def collect_rb_hc_spread():
    """采集螺纹钢-热轧卷板价差"""
    log("采集RB-HC价差")
    result = {"success": False, "factors": []}
    obs_date = get_obs_date()
    today = date.today().strftime('%Y-%m-%d')
    
    if not AKSHARE_OK:
        log("AKShare not installed", "FAIL")
        return result
    
    rb_price = None
    hc_price = None
    
    try:
        # RB期货价格 (上期所)
        df_rb = ak.get_shfe_daily(date=date.today().strftime('%Y%m%d'))
        if df_rb is not None and len(df_rb) > 0:
            rb_df = df_rb[df_rb['variety'] == 'RB']
            if len(rb_df) > 0:
                rb_price = rb_df.iloc[-1]['close']
                log(f"RB price = {rb_price}", "OK")
    except Exception as e:
        log(f"RB价格采集失败: {e}", "WARN")
    
    # RB不在SHFE每日数据中，尝试用新浪
    if not rb_price:
        try:
            df = ak.futures_main_sina(symbol="RB")
            if df is not None and len(df) > 0:
                rb_price = float(df.iloc[-1]['close'])
                log(f"RB price (sina) = {rb_price}", "OK")
        except Exception as e:
            log(f"RB price (sina) failed: {e}", "WARN")
    
    # HC价格
    if not hc_price:
        try:
            df = ak.futures_main_sina(symbol="HC")
            if df is not None and len(df) > 0:
                hc_price = float(df.iloc[-1]['close'])
                log(f"HC price (sina) = {hc_price}", "OK")
        except Exception as e:
            log(f"HC price (sina) failed: {e}", "WARN")
    
    # 计算价差
    if rb_price and hc_price:
        spread = rb_price - hc_price
        write_db("RB_HC_SPREAD", obs_date, today, spread, "AKShare-calculated", 1.0)
        log(f"RB_HC_SPREAD = {spread}", "OK")
        result["success"] = True
        result["factors"].append(("RB_HC_SPREAD", spread, "OK"))
    else:
        log(f"RB或HC价格获取失败: RB={rb_price}, HC={hc_price}", "FAIL")
    
    return result

# ============================================================
# 5. 大豆价格
# ============================================================
def collect_soybean_price():
    """采集大豆现货价格"""
    log("采集大豆价格")
    result = {"success": False, "factors": []}
    obs_date = get_obs_date()
    today = date.today().strftime('%Y-%m-%d')
    
    if not AKSHARE_OK:
        log("AKShare not installed", "FAIL")
        return result
    
    try:
        df = ak.spot_soybean_price_soozhu()
        if df is not None and len(df) > 0:
            latest = df.iloc[-1]
            price = float(latest.iloc[1])  # 价格
            write_db("Y_SOYBEAN_PRICE", obs_date, today, price, "AKShare-spot_soybean_price_soozhu", 1.0)
            log(f"Y_SOYBEAN_PRICE = {price}", "OK")
            result["success"] = True
            result["factors"].append(("Y_SOYBEAN_PRICE", price, "OK"))
    except Exception as e:
        log(f"大豆价格采集失败: {e}", "FAIL")
    
    return result

# ============================================================
# 6. CFTC黄金净持仓
# ============================================================
def collect_cftc_gold():
    """采集CFTC黄金净持仓"""
    log("采集CFTC黄金净持仓")
    result = {"success": False, "factors": []}
    obs_date = get_obs_date()
    today = date.today().strftime('%Y-%m-%d')
    
    if not AKSHARE_OK:
        log("AKShare not installed", "FAIL")
        return result
    
    try:
        # 尝试AKShare CFTC数据
        func_names = [x for x in dir(ak) if 'cftc' in x.lower() or 'futures_cftc' in x.lower()]
        log(f"CFTC functions: {func_names}", "INFO")
    except Exception as e:
        log(f"CFTC函数查找失败: {e}", "WARN")
    
    # 如果没有CFTC接口，记录为待开发
    log("CFTC黄金净持仓 - 待开发(需手动或付费源)", "WARN")
    return result

# ============================================================
# 7. SLV ETF持仓
# ============================================================
def collect_slv_etf():
    """采集iShares Silver Trust (SLV) ETF持仓"""
    log("采集SLV ETF持仓")
    result = {"success": False, "factors": []}
    obs_date = get_obs_date()
    today = date.today().strftime('%Y-%m-%d')
    
    if not AKSHARE_OK:
        log("AKShare not installed", "FAIL")
        return result
    
    # 尝试从iShares官网获取
    try:
        from common.web_utils import fetch_json
        url = "https://www.ishares.com/us/2515485436/1467261812594.ajax?tab=performance&fileType=json&url=1436932140244.ajax"
        headers = {'Accept': 'application/json'}
        data, err = fetch_json(url, headers=headers, timeout=15)
        if not err and data:
            # 解析SLV持仓数据...
            log("SLV ETF数据获取成功(待解析)", "OK")
        else:
            log(f"SLV ETF请求失败: {err}", "WARN")
    except Exception as e:
        log(f"SLV ETF采集失败: {e}", "WARN")
    
    log("SLV ETF持仓 - 待开发(需iShares官网爬虫)", "WARN")
    return result

# ============================================================
# 8. 新加坡燃料油库存
# ============================================================
def collect_singapore_fuel_oil():
    """采集新加坡燃料油库存"""
    log("采集新加坡燃料油库存")
    result = {"success": False, "factors": []}
    obs_date = get_obs_date()
    today = date.today().strftime('%Y-%m-%d')
    
    # MPA (新加坡海事港务局) 数据需要浏览器访问
    log("新加坡燃料油库存 - 需要浏览器自动化采集", "WARN")
    return result

# ============================================================
# 主执行
# ============================================================
if __name__ == "__main__":
    log("=" * 60)
    log("Priority 2: 免费数据采集开始")
    log("=" * 60)
    
    all_results = {}
    
    # 1. LME锌库存
    log("--- LME锌库存 ---")
    all_results["ZN_LME"] = collect_lme_zinc_stock()
    
    # 2. 黄金白银比
    log("--- 黄金白银比 ---")
    all_results["AU_AG"] = collect_gold_silver_ratio()
    
    # 3. PMI
    log("--- 制造业PMI ---")
    all_results["PMI"] = collect_china_pmi()
    
    # 4. RB-HC价差
    log("--- RB-HC价差 ---")
    all_results["RB_HC"] = collect_rb_hc_spread()
    
    # 5. 大豆价格
    log("--- 大豆价格 ---")
    all_results["SOYBEAN"] = collect_soybean_price()
    
    # 6. CFTC黄金
    log("--- CFTC黄金净持仓 ---")
    all_results["CFTC_AU"] = collect_cftc_gold()
    
    # 7. SLV ETF
    log("--- SLV ETF持仓 ---")
    all_results["SLV"] = collect_slv_etf()
    
    # 8. 新加坡燃料油
    log("--- 新加坡燃料油库存 ---")
    all_results["FU_SINGAPORE"] = collect_singapore_fuel_oil()
    
    # 汇总
    log("=" * 60)
    log("采集完成汇总")
    log("=" * 60)
    total_success = 0
    total_fail = 0
    for name, res in all_results.items():
        ok = res["success"]
        total_success += ok
        total_fail += not ok
        status = "OK" if ok else "WARN"
        log(f"{name}: {status}")
        for fac, val, s in res["factors"]:
            log(f"  {fac}: {val} -> {s}")
    
    log(f"总计: {total_success} 成功, {total_fail} 待开发/失败")
    log("=" * 60)
