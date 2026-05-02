#!/usr/bin/env python3
"""Pandera Schema 检查 — 期货价格文件"""
import os, glob, sys
import pandas as pd
import pandera.pandas as pa
import pandera as _pa_version
from pandera import Column, Check, DataFrameSchema
from pandera.typing import DateTime, Float, Int

OUTFILE = r'D:\futures_v6\macro_engine\research\reports\Pandera_Schema_Check_20260427.md'
BASE = r'D:\futures_v6\macro_engine\data\crawlers'
TARGET_SYMBOLS = ['AG','AL','AO','AU','BR','BU','CU','EC','EG','HC','I','J','JM',
                   'LC','LH','M','NI','NR','P','PB','PP','RB','RU','SA','SC','SN','TA','Y','ZN']

# ── Schema 定义 ──────────────────────────────────────
price_schema = DataFrameSchema({
    'date':        Column(DateTime, nullable=False),
    'close':       Column(Float, Check.greater_than(0), nullable=False),
    'open':        Column(Float, Check.greater_than(0), nullable=True),
    'high':        Column(Float, Check.greater_than(0), nullable=True),
    'low':         Column(Float, Check.greater_than(0), nullable=True),
    'volume':      Column(Int, Check.greater_than_or_equal_to(0), nullable=True),
}, strict=False, coerce=True)

spread_schema = DataFrameSchema({
    'date':  Column(DateTime, nullable=False),
    'close': Column(Float, nullable=True),
    'diff':  Column(Float, nullable=True),
}, strict=False, coerce=True)

ratio_schema = DataFrameSchema({
    'date':  Column(DateTime, nullable=False),
    'ratio': Column(Float, nullable=True),
}, strict=False, coerce=True)

def log(msg):
    print(msg)
    with open(OUTFILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

open(OUTFILE, 'w', encoding='utf-8').close()

log("# Pandera Schema 检查报告")
log(f"**时间**: 2026-04-27 13:42 GMT+8")
log(f"**工具**: pandera {_pa_version.__version__}")
log("")
log("=" * 70)
log("")

# ── 收集价格文件 ──────────────────────────────────────
price_files = []
for sym in TARGET_SYMBOLS:
    sym_dir = os.path.join(BASE, sym, 'daily')
    if os.path.isdir(sym_dir):
        for f in glob.glob(os.path.join(sym_dir, '*.csv')):
            fname = os.path.basename(f).lower()
            if any(k in fname for k in ['close', 'fut', 'lme', 'spread']):
                price_files.append((sym, f))

shared_dir = os.path.join(BASE, '_shared', 'daily')
if os.path.isdir(shared_dir):
    for f in glob.glob(os.path.join(shared_dir, '*.csv')):
        fname = os.path.basename(f).lower()
        if any(k in fname for k in ['brent', 'bond', 'usd', 'cny', 'ratio', 'cn10y']):
            price_files.append(('SHARED', f))

log(f"## 检查文件列表 ({len(price_files)} 个)")
log("")
total_pass = 0; total_fail = 0; total_warn = 0; total_skip = 0
results = []

def try_validate_schema(df, fname, schema):
    """尝试schema验证，返回 (status, err)"""
    try:
        schema.validate(df, lazy=True)
        return 'PASS', ''
    except pa.errors.SchemaErrors as e:
        fc = e.failure_cases
        n = len(fc)
        sample = fc.head(2).to_string(index=False).replace('\n', ' | ')
        return 'FAIL', f'{n}个失败: {sample}'
    except Exception as ex:
        return 'WARN', str(ex)[:80]

for sym, fpath in sorted(price_files):
    fname = os.path.basename(fpath)
    r = {'sym': sym, 'file': fname, 'rows': 0, 'cols': 0, 'status': 'SKIP', 'err': ''}
    try:
        df = pd.read_csv(fpath)
        r['rows'] = len(df); r['cols'] = len(df.columns)
        if len(df) == 0:
            r['status'] = 'SKIP'; r['err'] = '空文件'; total_skip += 1
            results.append(r); continue

        # 找到日期列
        parsed = df.copy()
        date_col = None
        for col in df.columns:
            try:
                parsed[col] = pd.to_datetime(parsed[col])
                date_col = col
                break
            except:
                pass

        if date_col is None:
            r['status'] = 'WARN'; r['err'] = f'无日期列: {list(df.columns)[:5]}'
            total_warn += 1; results.append(r); continue

        parsed.rename(columns={date_col: 'date'}, inplace=True)

        # 选择schema
        fname_lower = fname.lower()
        if 'spread' in fname_lower or 'diff' in fname_lower:
            schema = spread_schema
            # spread文件可能有不同的值列名
            for c in df.columns:
                if c != date_col and df[c].dtype in ['float64', 'int64']:
                    parsed.rename(columns={c: 'close'}, inplace=True)
                    break
        elif 'ratio' in fname_lower:
            schema = ratio_schema
            for c in df.columns:
                if c != date_col and df[c].dtype in ['float64', 'int64']:
                    parsed.rename(columns={c: 'ratio'}, inplace=True)
                    break
        else:
            schema = price_schema
            # 处理列名标准化
            rename_map = {}
            for c in df.columns:
                cl = c.lower()
                if 'close' in cl or 'settle' in cl or 'price' in cl:
                    rename_map[c] = 'close'
                elif 'open' in cl:
                    rename_map[c] = 'open'
                elif 'high' in cl:
                    rename_map[c] = 'high'
                elif 'low' in cl:
                    rename_map[c] = 'low'
                elif 'vol' in cl:
                    rename_map[c] = 'volume'
            parsed.rename(columns=rename_map, inplace=True)

        status, err = try_validate_schema(parsed, fname, schema)
        r['status'] = status; r['err'] = err
        if status == 'PASS': total_pass += 1
        elif status == 'FAIL': total_fail += 1
        else: total_warn += 1

    except Exception as ex:
        r['status'] = 'SKIP'; r['err'] = f'读取失败: {str(ex)[:60]}'
        total_skip += 1

    results.append(r)

# ── 汇总输出 ──────────────────────────────────────────
valid = total_pass + total_fail + total_warn
pct = total_pass / valid * 100 if valid > 0 else 0

log(f"## 检查结果汇总")
log(f"| 指标 | 数值 |")
log(f"|------|------|")
log(f"| 检查文件数 | {len(price_files)} |")
log(f"| PASS | {total_pass} |")
log(f"| FAIL | {total_fail} |")
log(f"| WARN | {total_warn} |")
log(f"| SKIP | {total_skip} |")
log(f"| 通过率 | {total_pass}/{valid} = {pct:.1f}% |")
log("")
log(f"## 详细结果")
log(f"| 品种 | 文件 | 行数 | 状态 | 问题 |")
log(f"|------|------|------|------|------|")
for r in results:
    st = {'PASS': '[PASS]', 'FAIL': '[FAIL]', 'WARN': '[WARN]', 'SKIP': '[SKIP]'}.get(r['status'], r['status'])
    err = r['err'].replace('\n', ' ')[:70] if r['err'] else ''
    log(f"| {r['sym']} | {r['file']} | {r['rows']} | {st} | {err} |")

# ── 失败样例详细 ──────────────────────────────────────
if total_fail > 0:
    log("")
    log("## FAIL 文件详细错误")
    for r in results:
        if r['status'] == 'FAIL':
            log(f"**{r['sym']} / {r['file']}**")
            log(f"  错误: {r['err']}")
            # 读取并展示问题行
            fpath = None
            for sym, fp in price_files:
                if sym == r['sym'] and os.path.basename(fp) == r['file']:
                    fpath = fp; break
            if fpath:
                try:
                    df = pd.read_csv(fpath)
                    log(f"  列名: {list(df.columns)}")
                    log(f"  前3行:\n{df.head(3).to_string()}")
                except:
                    pass
            log("")

log("")
log("=" * 70)
log("检查完成")

print(f"\n完成: PASS={total_pass} FAIL={total_fail} WARN={total_warn} SKIP={total_skip}")
print(f"报告: {OUTFILE}")
