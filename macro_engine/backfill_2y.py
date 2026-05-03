# -*- coding: utf-8 -*-
from config.paths import CRAWLERS
"""2年历史回填脚本 - 12个新品种 2023-01-01至今"""
import sys, os, datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, str(CRAWLERS / 'common'))
from db_utils import save_to_db
import akshare as ak
import pandas as pd
from datetime import timedelta

TODAY = datetime.date.today()
CUTOFF = datetime.date(2023, 1, 1)  # 2年+回填
WRITTEN = []
ERRORS = []

def save(fcode, sym, obs_date, raw_value, conf=1.0):
    try:
        save_to_db(fcode, sym, TODAY, obs_date, raw_value, source_confidence=conf)
        WRITTEN.append((fcode, sym, obs_date, raw_value))
    except Exception as e:
        ERRORS.append((fcode, sym, obs_date, str(e)[:50]))

def backfill_main_sina(symbol_code, factor_close, factor_oi, sym):
    """期货收盘+持仓回填"""
    try:
        df = ak.futures_main_sina(symbol=symbol_code)
        if df.empty:
            return 0
        df_rev = df.iloc[::-1]
        count = 0
        for _, row in df_rev.iterrows():
            obs = pd.to_datetime(row.iloc[0]).date()
            if obs < CUTOFF:
                break
            close = float(row.iloc[4])
            oi = float(row.iloc[6])
            save(factor_close, sym, obs, close)
            save(factor_oi, sym, obs, oi)
            count += 1
        return count
    except Exception as e:
        ERRORS.append((factor_close, sym, 'fetch', str(e)[:50]))
        return 0

def backfill_dce_inv(symbol_ak, factor_code, sym, emin, emax):
    """DCE库存回填"""
    try:
        df = ak.futures_inventory_em(symbol=symbol_ak)
        if df.empty:
            return 0
        df_rev = df.iloc[::-1]
        count = 0
        for _, row in df_rev.iterrows():
            obs = pd.to_datetime(row.iloc[0]).date()
            if obs < CUTOFF:
                break
            v = float(row.iloc[1])
            if emin <= v <= emax:
                save(factor_code, sym, obs, v)
                count += 1
        return count
    except Exception as e:
        ERRORS.append((factor_code, sym, 'fetch', str(e)[:50]))
        return 0

# (sym, symbol_code, close_fc, oi_fc, inv_sym, inv_emin, inv_emax)
varieties = [
    ('P',  'P0',  'P_FUT_CLOSE',  'P_FUT_OI',  'p',    1000,  200000),
    ('NI', 'ni0', 'NI_FUT_CLOSE', 'NI_FUT_OI', 'ni',   30000, 150000),
    ('SN', 'sn0', 'SN_FUT_CLOSE', 'SN_FUT_OI', 'sn',   5000,  30000),
    ('ZN', 'zn0', 'ZN_FUT_CLOSE', 'ZN_FUT_OI', 'zn',   50000, 300000),
    ('AU', 'au0', 'AU_FUT_CLOSE', 'AU_FUT_OI', None,   0,     0),
    ('SC', 'sc0', 'SC_FUT_CLOSE', 'SC_FUT_OI', None,   0,     0),
    ('LH', 'lh0', 'LH_FUT_CLOSE', 'LH_FUT_OI', None,   0,     0),
    ('LC', 'lc0', 'LC_FUT_CLOSE', 'LC_FUT_OI', None,   0,     0),
    ('AO', 'ao0', 'AO_FUT_CLOSE', 'AO_FUT_OI', 'ao',   200000, 1000000),
    ('EC', 'ec0', 'EC_FUT_CLOSE', 'EC_FUT_OI', None,   0,     0),
    ('CU', 'cu0', 'CU_FUT_CLOSE', 'CU_FUT_OI', 'cu',  50000, 500000),
    ('I',  'i0',  'I_FUT_CLOSE',  'I_FUT_OI',  None,  0,     0),
]

print("=== 2年回填: cutoff=%s ===" % CUTOFF)
t0 = datetime.datetime.now()

for sym, code, fc, oi_fc, inv_sym, inv_min, inv_max in varieties:
    rows_main = backfill_main_sina(code, fc, oi_fc, sym)
    rows_inv = 0
    if inv_sym:
        rows_inv = backfill_dce_inv(inv_sym, sym+'_DCE_INV', sym, inv_min, inv_max)
    total = rows_main * 2 + rows_inv
    tag = "OK" if total > 0 else "SKIP"
    print("[%s] %s: main=%dx2 inv=%d total=%d" % (tag, sym, rows_main, rows_inv, total))

# SGE现货黄金
print("\n[AU] SGE spot gold:", end=" ")
try:
    df = ak.spot_golden_benchmark_sge()
    df_rev = df.iloc[::-1]
    count = 0
    for _, row in df_rev.iterrows():
        obs = pd.to_datetime(row.iloc[0]).date()
        if obs < CUTOFF:
            break
        save('AU_SPOT_SGE', 'AU', obs, float(row.iloc[1]))
        count += 1
    print("%d rows" % count)
except Exception as e:
    print("FAIL:", str(e)[:40])

elapsed = (datetime.datetime.now() - t0).total_seconds()
print("\n=== 回填完成 ===")
print("写入: %d条" % len(WRITTEN))
print("耗时: %.0fs" % elapsed)
if ERRORS[:5]:
    print("错误:")
    for e in ERRORS[:5]:
        print("  ERR:", e)
