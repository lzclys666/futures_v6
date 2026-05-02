#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_all_factors.py"""
import sqlite3, os, yaml

BASE = r"D:\futures_v6\macro_engine"
DB = os.path.join(BASE, "pit_data.db")
TABLE = "pit_factor_observations"

conn = sqlite3.connect(DB)
cur = conn.cursor()

# 1. 各品种全局统计
print("=" * 70)
print("[1] Symbol Stats")
print("=" * 70)
cur.execute("""
    SELECT symbol, COUNT(DISTINCT factor_code) as nf, COUNT(*) as nr,
           MIN(pub_date) as first_dt, MAX(pub_date) as last_dt
    FROM %s GROUP BY symbol ORDER BY symbol
""" % TABLE)
rows = cur.fetchall()
hdr = "%-6s %6s %8s %-12s %-12s" % ("Sym", "Factors", "Records", "FirstDate", "LastDate")
print(hdr)
print("-" * 50)
tf, tr = 0, 0
for r in rows:
    print("%-6s %6d %8d %-12s %-12s" % (r[0], r[1], r[2], str(r[3]), str(r[4])))
    tf += r[1]; tr += r[2]
print("\n  TOTAL: %d symbols, %d factors, %d records" % (len(rows), tf, tr))

# 2. 加载config因子
factors_cfg = {}
cfg_dir = os.path.join(BASE, "config", "factors")
if os.path.isdir(cfg_dir):
    for sym in os.listdir(cfg_dir):
        sym_path = os.path.join(cfg_dir, sym)
        if not os.path.isdir(sym_path):
            continue
        factors_cfg[sym] = []
        for f in os.listdir(sym_path):
            if f.endswith(".yaml"):
                fname = f.replace(".yaml", "")
                try:
                    with open(os.path.join(sym_path, f), "r", encoding="utf-8") as fp:
                        data = yaml.safe_load(fp)
                    desc = data.get("description", "") if data else ""
                except:
                    desc = ""
                factors_cfg[sym].append((fname, desc))

# 3. 各品种因子明细
print("\n" + "=" * 70)
print("[2] Per-Symbol Factor Details (DB vs Config)")
print("=" * 70)

all_syms = sorted(set(list(factors_cfg.keys()) + [r[0] for r in rows]))

for sym in all_syms:
    # DB factors
    cur.execute("""
        SELECT factor_code, COUNT(*) as cnt, MAX(pub_date) as ldt
        FROM %s WHERE symbol=? GROUP BY factor_code ORDER BY factor_code
    """ % TABLE, (sym,))
    db_f = {r[0]: (r[1], str(r[2])) for r in cur.fetchall()}
    
    cfg_f = factors_cfg.get(sym, [])
    cfg_names = set(f[0] for f in cfg_f)
    db_names = set(db_f.keys())
    
    has = cfg_names & db_names
    miss = cfg_names - db_names
    extra = db_names - cfg_names
    
    if not db_f and not cfg_f:
        continue
    
    print("\n[%s] has=%d miss=%d extra=%d" % (sym, len(has), len(miss), len(extra)))
    
    if has:
        print("  --- Collected (%d) ---" % len(has))
        for fname in sorted(has):
            cnt, ldt = db_f[fname]
            print("    [OK] %-35s %5d recs  last=%s" % (fname, cnt, ldt))
    
    if miss:
        print("  --- MISSING (%d) ---" % len(miss))
        for fname in sorted(miss):
            desc = next((d for f, d in cfg_f if f == fname), "")
            # tag by factor group
            tag = ""
            if "SUP" in fname or "PROD" in fname or "OUTPUT" in fname:
                tag = "[SUPPLY]"
            elif "DEM" in fname or "CONS" in fname:
                tag = "[DEMAND]"
            elif "INV" in fname or "STK" in fname or "库存" in desc:
                tag = "[INVENTORY]"
            elif "POS" in fname or "NET" in fname:
                tag = "[POSITION]"
            elif "MACRO" in fname or "FX" in fname or "CPI" in fname or "DXY" in fname:
                tag = "[MACRO]"
            elif "CST" in fname or "COST" in fname or "MARGIN" in fname or "FREIGHT" in fname:
                tag = "[COST]"
            elif "SPD" in fname or "RATIO" in fname or "BASIS" in fname or "SPREAD" in fname:
                tag = "[SPREAD]"
            elif "FUT" in fname or "CLOSE" in fname:
                tag = "[PRICE]"
            print("    %s %-30s -- %s" % (tag, fname, desc[:50]))

# 4. 今日采集情况
print("\n" + "=" * 70)
print("[3] Today (2026-04-19) Collection")
print("=" * 70)
cur.execute("""
    SELECT symbol, COUNT(DISTINCT factor_code), COUNT(*)
    FROM %s WHERE pub_date='2026-04-19' GROUP BY symbol ORDER BY symbol
""" % TABLE)
today = cur.fetchall()
if today:
    print("%-8s %6s %8s" % ("Sym", "Factors", "Records"))
    print("-" * 25)
    for r in today:
        print("%-8s %6d %8d" % (r[0], r[1], r[2]))
    print("\n  %d symbols collected today" % len(today))
else:
    print("  No data for today (2026-04-19)")

# 5. 最新采集日期
print("\n" + "=" * 70)
print("[4] Last Collection Date per Symbol")
print("=" * 70)
cur.execute("""
    SELECT symbol, MAX(pub_date) as ldt FROM %s GROUP BY symbol ORDER BY ldt DESC
""" % TABLE)
for r in cur.fetchall():
    m = " <--" if r[1] != "2026-04-19" else ""
    print("  %-6s  last=%s%s" % (r[0], r[1], m))

conn.close()
