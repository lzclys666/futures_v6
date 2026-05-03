# Exchange Shared Data Collector v1.0
# Priority 1: SHFE & DCE 仓单/持仓数据
# 修订日期：2026-04-20
# 保存位置: D:\futures_v6\macro_engine\data\crawlers\_shared\exchange\

import os
import sys
import sqlite3
import traceback
import json
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
LOG_DIR = _PROJECT_ROOT / "macro_engine" / "crawlers" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 日期处理：找到最近交易日
# ============================================================
def get_latest_trade_date():
    """获取最近交易日（跳过周末）"""
    today = date.today()
    wd = today.weekday()
    if wd == 0:  # Monday -> Friday
        return (today - timedelta(days=3)).strftime('%Y%m%d')
    elif wd == 6:  # Sunday -> Friday
        return (today - timedelta(days=2)).strftime('%Y%m%d')
    else:
        return (today - timedelta(days=1)).strftime('%Y%m%d')

# ============================================================
# 数据库工具
# ============================================================
def get_db_conn():
    return sqlite3.connect(DB_PATH, timeout=30)

def write_db(factor_code, obs_date, pub_date, raw_value, source, confidence):
    """写入数据库 - 使用 pit_factor_observations 表"""
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
# SHFE 仓单日报
# ============================================================
def collect_shfe_warehouse_receipt(trade_date):
    """采集SHFE仓单日报数据"""
    log(f"采集SHFE仓单日报: {trade_date}")
    result = {"success": False, "data": None, "error": None}
    
    if not AKSHARE_OK:
        result["error"] = "AKShare not installed"
        return result
    
    # 尝试多个日期（如果当天没数据，尝试前几天）
    dates_to_try = [trade_date]
    for i in range(1, 5):
        d = (datetime.strptime(trade_date, '%Y%m%d') - timedelta(days=i)).strftime('%Y%m%d')
        dates_to_try.append(d)
    
    for dt in dates_to_try:
        try:
            data = ak.futures_shfe_warehouse_receipt(date=dt)
            if data and isinstance(data, dict) and len(data) > 0:
                # 保存到CSV
                df = pd.DataFrame(data) if not isinstance(data, pd.DataFrame) else data
                if 'VARNAME' in df.columns:
                    df['date'] = dt
                    csv_path = SHARED_DIR / f"shfe_warehouse_receipt_{dt}.csv"
                    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                    result["success"] = True
                    result["data"] = df
                    result["date"] = dt
                    log(f"SHFE仓单: {dt}, {len(df)} 条记录", "OK")
                    
                    # 写入各品种仓单因子
                    for _, row in df.iterrows():
                        var = row.get('VARNAME', '')
                        receipt = row.get('WAREHOURSE_RECEIPT', row.get('RECEIPT', 0))
                        if var and receipt and str(receipt).replace('.', '').replace('-', '').isdigit():
                            factor_code = f"SHFE_WR_{var.upper()}"
                            write_db(factor_code, dt, date.today().strftime('%Y-%m-%d'), 
                                   float(receipt), "SHFE-warehouse_receipt", 1.0)
                    break
        except Exception as e:
            continue
    
    if not result["success"]:
        result["error"] = f"All dates failed"
        log(f"SHFE仓单采集失败: {result['error']}", "FAIL")
    
    return result

# ============================================================
# SHFE 持仓排名
# ============================================================
def collect_shfe_position_rank(trade_date):
    """采集SHFE持仓排名数据"""
    log(f"采集SHFE持仓排名: {trade_date}")
    result = {"success": False, "data": None, "error": None}
    
    if not AKSHARE_OK:
        result["error"] = "AKShare not installed"
        return result
    
    try:
        data = ak.get_shfe_rank_table(date=trade_date)
        if data and isinstance(data, dict) and len(data) > 0:
            # 合并所有合约的DataFrame并保存为CSV
            all_dfs = []
            for sym, df in data.items():
                if hasattr(df, 'to_dataframe') or hasattr(df, 'copy'):
                    df_copy = df.copy() if hasattr(df, 'copy') else df
                    df_copy['symbol'] = sym
                    all_dfs.append(df_copy)
            
            if all_dfs:
                combined_df = pd.concat(all_dfs, ignore_index=True)
                csv_path = SHARED_DIR / f"shfe_position_rank_{trade_date}.csv"
                combined_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                result["success"] = True
                result["data"] = combined_df
                log(f"SHFE持仓排名: {trade_date}, {len(data)} 合约, {len(combined_df)} 条记录", "OK")
                
                # 写入数据库 - 按品种汇总top5多头/空头持仓
                for variety in combined_df['variety'].unique():
                    var_df = combined_df[combined_df['variety'] == variety]
                    if len(var_df) > 0:
                        # 取排名=1的会员持仓
                        top_long = var_df[var_df['rank'] == 1]['long_open_interest'].sum()
                        top_short = var_df[var_df['rank'] == 1]['short_open_interest'].sum()
                        
                        factor_code = f"SHFE_RANK_LONG_{variety.upper()}"
                        write_db(factor_code, trade_date, date.today().strftime('%Y-%m-%d'),
                               float(top_long), "SHFE-get_shfe_rank_table", 1.0)
                        factor_code = f"SHFE_RANK_SHORT_{variety.upper()}"
                        write_db(factor_code, trade_date, date.today().strftime('%Y-%m-%d'),
                               float(top_short), "SHFE-get_shfe_rank_table", 1.0)
            else:
                result["error"] = "No DataFrames to combine"
        else:
            result["error"] = "Empty data"
    except Exception as e:
        result["error"] = str(e)
        log(f"SHFE持仓排名采集失败: {e}", "FAIL")
    
    return result

# ============================================================
# DCE 仓单日报
# ============================================================
def collect_dce_warehouse_receipt(trade_date):
    """采集DCE仓单日报数据"""
    log(f"采集DCE仓单日报: {trade_date}")
    result = {"success": False, "data": None, "error": None}
    
    if not AKSHARE_OK:
        result["error"] = "AKShare not installed"
        return result
    
    # 尝试多个日期
    dates_to_try = [trade_date]
    for i in range(1, 5):
        d = (datetime.strptime(trade_date, '%Y%m%d') - timedelta(days=i)).strftime('%Y%m%d')
        dates_to_try.append(d)
    
    for dt in dates_to_try:
        try:
            df = ak.futures_warehouse_receipt_dce(date=dt)
            if df is not None and isinstance(df, pd.DataFrame) and len(df) > 0:
                df['date'] = dt
                csv_path = SHARED_DIR / f"dce_warehouse_receipt_{dt}.csv"
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                result["success"] = True
                result["data"] = df
                result["date"] = dt
                log(f"DCE仓单: {dt}, {len(df)} 条记录", "OK")
                
                # 写入各品种仓单因子
                for _, row in df.iterrows():
                    var = row.get('品种', row.get('variety', ''))
                    receipt = row.get('仓单数', row.get('receipt', row.get('仓库仓单', 0)))
                    if var and receipt:
                        try:
                            factor_code = f"DCE_WR_{str(var).upper()}"
                            write_db(factor_code, dt, date.today().strftime('%Y-%m-%d'),
                                   float(receipt), "DCE-warehouse_receipt", 1.0)
                        except:
                            pass
                break
        except Exception as e:
            continue
    
    if not result["success"]:
        result["error"] = f"All dates failed"
        log(f"DCE仓单采集失败: {result['error']}", "FAIL")
    
    return result

# ============================================================
# DCE 持仓排名
# ============================================================
def collect_dce_position_rank(trade_date):
    """采集DCE持仓排名数据"""
    log(f"采集DCE持仓排名: {trade_date}")
    result = {"success": False, "data": None, "error": None}
    
    if not AKSHARE_OK:
        result["error"] = "AKShare not installed"
        return result
    
    # DCE品种列表
    varieties = ['C', 'CS', 'A', 'B', 'M', 'Y', 'P', 'FB', 'BB', 'JD', 'L', 'V', 'PP', 'J', 'JM', 'I', 'EG', 'LH', 'PG']
    
    try:
        data = ak.futures_dce_position_rank(date=trade_date, vars_list=varieties)
        if data and isinstance(data, dict) and len(data) > 0:
            json_path = SHARED_DIR / f"dce_position_rank_{trade_date}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            result["success"] = True
            result["data"] = data
            log(f"DCE持仓排名: {trade_date}, {len(data)} 合约", "OK")
        else:
            result["error"] = "Empty data"
    except Exception as e:
        result["error"] = str(e)
        log(f"DCE持仓排名采集失败: {e}", "FAIL")
    
    return result

# ============================================================
# SHFE 每日行情（OHLCV + 持仓量）
# ============================================================
def collect_shfe_daily(trade_date):
    """采集SHFE所有合约每日行情"""
    log(f"采集SHFE每日行情: {trade_date}")
    result = {"success": False, "data": None, "error": None}
    
    if not AKSHARE_OK:
        result["error"] = "AKShare not installed"
        return result
    
    try:
        df = ak.get_shfe_daily(date=trade_date)
        if df is not None and isinstance(df, pd.DataFrame) and len(df) > 0:
            csv_path = SHARED_DIR / f"shfe_daily_{trade_date}.csv"
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            result["success"] = True
            result["data"] = df
            log(f"SHFE每日行情: {trade_date}, {len(df)} 条记录", "OK")
            
            # 写入各品种收盘价因子
            # 按品种分组，取主力合约
            for variety in df['variety'].unique():
                var_df = df[df['variety'] == variety].copy()
                if len(var_df) > 0:
                    # 过滤掉空值
                    var_df = var_df.replace('', np.nan).dropna(subset=['close', 'open_interest'])
                    if len(var_df) > 0:
                        # 取持仓量最大的合约
                        main_contract = var_df.loc[var_df['open_interest'].idxmax()]
                        close_val = main_contract['close']
                        oi_val = main_contract['open_interest']
                        if pd.notna(close_val) and pd.notna(oi_val):
                            try:
                                factor_code = f"SHFE_CLOSE_{variety.upper()}"
                                write_db(factor_code, trade_date, date.today().strftime('%Y-%m-%d'),
                                       float(close_val), "SHFE-get_shfe_daily", 1.0)
                                factor_code = f"SHFE_OI_{variety.upper()}"
                                write_db(factor_code, trade_date, date.today().strftime('%Y-%m-%d'),
                                       float(oi_val), "SHFE-get_shfe_daily", 1.0)
                            except Exception as db_err:
                                log(f"DB write error for {variety}: {db_err}", "WARN")
        else:
            result["error"] = "Empty data"
    except Exception as e:
        result["error"] = str(e)
        log(f"SHFE每日行情采集失败: {e}", "FAIL")
    
    return result

# ============================================================
# SHFE 结算数据
# ============================================================
def collect_shfe_settlement(trade_date):
    """采集SHFE结算数据"""
    log(f"采集SHFE结算数据: {trade_date}")
    result = {"success": False, "data": None, "error": None}
    
    if not AKSHARE_OK:
        result["error"] = "AKShare not installed"
        return result
    
    try:
        df = ak.futures_settle_shfe(date=trade_date)
        if df is not None and isinstance(df, pd.DataFrame) and len(df) > 0:
            csv_path = SHARED_DIR / f"shfe_settlement_{trade_date}.csv"
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            result["success"] = True
            result["data"] = df
            log(f"SHFE结算数据: {trade_date}, {len(df)} 条记录", "OK")
            
            # 写入结算价因子
            for _, row in df.iterrows():
                variety = str(row.get('variety', '')).upper()
                settle = row.get('settle_price', None)
                if variety and settle is not None and not pd.isna(settle):
                    try:
                        factor_code = f"SHFE_SETTLE_{variety}"
                        write_db(factor_code, trade_date, date.today().strftime('%Y-%m-%d'),
                               float(settle), "SHFE-futures_settle_shfe", 1.0)
                    except Exception as db_err:
                        log(f"DB write error for {variety}: {db_err}", "WARN")
        else:
            result["error"] = "Empty data"
    except Exception as e:
        result["error"] = str(e)
        log(f"SHFE结算数据采集失败: {e}", "FAIL")
    
    return result

# ============================================================
# 主执行
# ============================================================
if __name__ == "__main__":
    log("=" * 60)
    log("Priority 1: 交易所共享数据采集开始")
    log("=" * 60)
    
    trade_date = get_latest_trade_date()
    log(f"最近交易日: {trade_date}")
    
    all_results = {}
    
    # 1. SHFE 仓单日报
    log("--- SHFE 仓单日报 ---")
    all_results["shfe_wr"] = collect_shfe_warehouse_receipt(trade_date)
    
    # 2. SHFE 持仓排名
    log("--- SHFE 持仓排名 ---")
    all_results["shfe_rank"] = collect_shfe_position_rank(trade_date)
    
    # 3. DCE 仓单日报
    log("--- DCE 仓单日报 ---")
    all_results["dce_wr"] = collect_dce_warehouse_receipt(trade_date)
    
    # 4. DCE 持仓排名
    log("--- DCE 持仓排名 ---")
    all_results["dce_rank"] = collect_dce_position_rank(trade_date)
    
    # 5. SHFE 每日行情
    log("--- SHFE 每日行情 ---")
    all_results["shfe_daily"] = collect_shfe_daily(trade_date)
    
    # 6. SHFE 结算数据
    log("--- SHFE 结算数据 ---")
    all_results["shfe_settle"] = collect_shfe_settlement(trade_date)
    
    # 汇总
    log("=" * 60)
    log("采集完成汇总")
    log("=" * 60)
    for name, res in all_results.items():
        status = "OK" if res["success"] else "FAIL"
        log(f"{name}: {status}")
        if res.get("data") is not None:
            if hasattr(res["data"], '__len__'):
                log(f"  记录数: {len(res['data'])}")
    
    # 保存汇总报告
    report_path = SHARED_DIR / f"collection_report_{date.today().strftime('%Y%m%d')}.json"
    report = {
        "trade_date": trade_date,
        "collection_date": date.today().strftime('%Y-%m-%d'),
        "results": {k: {"success": v["success"], "error": v.get("error")} for k, v in all_results.items()}
    }
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    log(f"报告已保存: {report_path}")
    log("=" * 60)
    log("结束")
    log("=" * 60)
