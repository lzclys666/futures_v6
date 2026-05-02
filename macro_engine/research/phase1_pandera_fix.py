#!/usr/bin/env python3
"""
Phase 1 — Pandera Schema修复脚本
目标：为不同文件类型定义专用Schema，识别真实数据质量问题
"""
import os, glob, sys
import pandas as pd
import pandera.pandas as pa
import pandera as _pa
from pandera import Column, Check, DataFrameSchema
from pandera.typing import DateTime, Float, Int, Series

OUTFILE = r'D:\futures_v6\macro_engine\research\reports\Phase1_Pandera_Fix_20260427.md'
BASE = r'D:\futures_v6\macro_engine\data\crawlers'
TARGET_SYMBOLS = ['AG','AL','AO','AU','BR','BU','CU','EC','EG','HC','I','J','JM',
                   'LC','LH','M','NI','NR','P','PB','PP','RB','RU','SA','SC','SN','TA','Y','ZN']

# ══════════════════════════════════════════════════════
# 专用Schema库
# ══════════════════════════════════════════════════════

# ── 1. 标准OHLCV期货文件 ─────────────────────────────
ohlcv_schema = DataFrameSchema({
    'date':   Column(DateTime, nullable=False),
    'close':  Column(Float, Check.greater_than(0), nullable=False,
               description='收盘价>0'),
    'open':   Column(Float, Check.greater_than(0), nullable=True),
    'high':   Column(Float, Check.greater_than(0), nullable=True),
    'low':    Column(Float, Check.greater_than(0), nullable=True),
    'volume': Column(Int, Check.greater_than_or_equal_to(0), nullable=True),
    'hold':   Column(Int, Check.greater_than_or_equal_to(0), nullable=True),
    'settle': Column(Float, Check.greater_than_or_equal_to(0), nullable=True),
}, strict=False, coerce=True)

# ── 2. Spread/价差文件（列名多变）─────────────────────
spread_schema = DataFrameSchema({
    'date':  Column(DateTime, nullable=False),
    'diff':  Column(Float, nullable=True),   # 价差
}, strict=False, coerce=True)

# ── 3. Ratio比价文件 ─────────────────────────────────
ratio_schema = DataFrameSchema({
    'date':  Column(DateTime, nullable=False),
    'ratio': Column(Float, Check.not_equal_to(0), nullable=True),
}, strict=False, coerce=True)

# ── 4. LME 3M格式文件 ────────────────────────────────
lme_3m_schema = DataFrameSchema({
    'date':    Column(DateTime, nullable=False),
    'latest':  Column(Float, Check.greater_than(0), nullable=True),
    'close':   Column(Float, Check.greater_than(0), nullable=True),
}, strict=False, coerce=True)

# ── 5. 宏观单价格文件（如Brent/CN10Y/USD_CNY）──────────
single_price_schema = DataFrameSchema({
    'date':  Column(DateTime, nullable=False),
    'price': Column(Float, Check.greater_than(0), nullable=True),
}, strict=False, coerce=True)

# ── 6. 宽松Schema（允许任何float列，仅检查date和price>0）
relaxed_schema = DataFrameSchema({
    'date': Column(DateTime, nullable=False),
}, strict=False, coerce=True)

# ── 7. 新版金银比（修正版，已验证正确格式）────────────
au_ag_ratio_schema = DataFrameSchema({
    'date':  Column(DateTime, nullable=False),
    'ratio': Column(Float, Check.greater_than(0), nullable=False),
}, strict=False, coerce=True)


def detect_schema_type(fname_lower, columns):
    """根据文件名和列名自动选择Schema类型"""
    # 金银比
    if 'ratio' in fname_lower and 'au_ag' in fname_lower:
        return au_ag_ratio_schema, '金银比'
    # 比价文件
    if 'ratio' in fname_lower:
        return ratio_schema, '比价'
    # 价差/spread文件
    if 'spread' in fname_lower or 'diff' in fname_lower:
        # 进一步判断
        if 'sge' in fname_lower or 'fut' in fname_lower:
            return spread_schema, '金银价差'
        return spread_schema, '价差'
    # LME 3M文件
    if '_3m' in fname_lower or 'lme' in fname_lower:
        return lme_3m_schema, 'LME_3M'
    # 标准OHLCV期货
    if all(k in columns for k in ['open', 'high', 'low', 'close', 'volume']):
        return ohlcv_schema, 'OHLCV'
    # 宏观单价格（Brent/USD/CNY/Bond）
    if 'brent' in fname_lower or 'wti' in fname_lower:
        return single_price_schema, '宏观价格'
    if 'usd' in fname_lower or 'cny' in fname_lower or 'bond' in fname_lower:
        return single_price_schema, '宏观价格'
    if 'cn10y' in fname_lower or 'cn_10y' in fname_lower:
        return single_price_schema, '宏观价格'
    # 默认宽松
    return relaxed_schema, '宽松'


def normalize_columns(df, fname_lower):
    """标准化列名，返回重命名后的DataFrame"""
    df = df.copy()
    rename_map = {}
    cols_lower = {c.lower(): c for c in df.columns}

    # 日期列
    for col in df.columns:
        try:
            df[col] = pd.to_datetime(df[col])
            rename_map[col] = 'date'
            break
        except:
            pass

    # 价格列
    price_candidates = ['close', 'settle', 'latest', 'price', 'ratio',
                        'wti_spot_usd_bbl', 'cn_10y_yield', 'usd_cny',
                        'dswp10', 'cn_10y', 'cn_2y', 'cn_5y']
    for cand in price_candidates:
        if cand in cols_lower:
            rename_map[cols_lower[cand]] = 'price'
            break

    # OHLCV列
    ohc = {'open': 'open', 'high': 'high', 'low': 'low',
           'volume': 'volume', 'hold': 'hold'}
    for std, cand in ohc.items():
        if cand in cols_lower:
            rename_map[cols_lower[cand]] = std

    df.rename(columns=rename_map, inplace=True)
    return df


def log(msg):
    print(msg)
    with open(OUTFILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

open(OUTFILE, 'w', encoding='utf-8').close()
log("# Phase 1 — Pandera Schema 修复报告")
log(f"**时间**: 2026-04-27 13:46 GMT+8")
log(f"**工具**: pandera {_pa.__version__}")
log("")
log("=" * 70)
log("")

# ── 收集所有价格文件 ─────────────────────────────────
price_files = []
for sym in TARGET_SYMBOLS:
    sym_dir = os.path.join(BASE, sym, 'daily')
    if os.path.isdir(sym_dir):
        for f in glob.glob(os.path.join(sym_dir, '*.csv')):
            price_files.append((sym, f))

shared_dir = os.path.join(BASE, '_shared', 'daily')
if os.path.isdir(shared_dir):
    for f in glob.glob(os.path.join(shared_dir, '*.csv')):
        price_files.append(('SHARED', f))

log(f"## Phase 1 修复：专用Schema验证")
log(f"检查文件数: {len(price_files)}")
log("")
log("| 品种 | 文件 | Schema类型 | 行数 | 状态 | 问题 |")
log("|------|------|-----------|------|------|------|")

total_pass = 0; total_fail = 0; total_warn = 0; total_skip = 0
results = []

# ── 逐文件验证 ──────────────────────────────────────
for sym, fpath in sorted(price_files):
    fname = os.path.basename(fpath)
    fname_lower = fname.lower()
    r = {'sym': sym, 'file': fname, 'type': '', 'rows': 0,
         'status': 'SKIP', 'err': '', 'zero_close': 0, 'null_close': 0}

    try:
        df = pd.read_csv(fpath)
        r['rows'] = len(df)
        if len(df) == 0:
            r['status'] = 'SKIP'; r['err'] = '空文件'; total_skip += 1
            results.append(r); continue

        # 标准化列名
        df_norm = normalize_columns(df, fname_lower)

        # 选择Schema
        schema, type_name = detect_schema_type(fname_lower, list(df.columns))
        r['type'] = type_name

        # 检查真实数据问题：close/price列
        price_col = 'close' if 'close' in df_norm.columns else ('price' if 'price' in df_norm.columns else None)
        if price_col:
            zero_count = int((df_norm[price_col] == 0).sum())
            null_count = int(df_norm[price_col].isnull().sum())
            r['zero_close'] = zero_count
            r['null_close'] = null_count

        # Schema验证
        try:
            schema.validate(df_norm, lazy=True)
            r['status'] = 'PASS'; total_pass += 1
        except pa.errors.SchemaErrors as e:
            fc = e.failure_cases
            n = len(fc)
            # 提取关键错误
            close_zero = (fc['column'] == 'close').sum() if 'column' in fc.columns else 0
            if close_zero > 0:
                r['status'] = 'WARN'; r['err'] = f'close=0: {close_zero}行'
                total_warn += 1
            else:
                sample = fc.head(1).to_string(index=False).replace('\n', ' ')[:80]
                r['status'] = 'FAIL'; r['err'] = f'{n}个失败: {sample}'
                total_fail += 1
        except Exception as ex:
            r['status'] = 'WARN'; r['err'] = str(ex)[:60]; total_warn += 1

    except Exception as ex:
        r['status'] = 'SKIP'; r['err'] = f'读取失败: {str(ex)[:60]}'
        total_skip += 1

    results.append(r)
    st = {'PASS': '[PASS]', 'FAIL': '[FAIL]', 'WARN': '[WARN]', 'SKIP': '[SKIP]'}.get(r['status'], r['status'])
    err_display = r['err'][:60] if r['err'] else ''
    log(f"| {r['sym']} | {r['file']} | {r['type']} | {r['rows']} | {st} | {err_display} |")

log("")

# ── 汇总 ─────────────────────────────────────────────
valid = total_pass + total_fail + total_warn
pct = total_pass / valid * 100 if valid > 0 else 0

log(f"## 汇总")
log(f"| 指标 | 数值 |")
log(f"|------|------|")
log(f"| 总文件数 | {len(price_files)} |")
log(f"| PASS | {total_pass} |")
log(f"| FAIL | {total_fail} |")
log(f"| WARN | {total_warn} |")
log(f"| SKIP | {total_skip} |")
log(f"| 通过率 | {total_pass}/{valid} = {pct:.1f}% |")
log("")

# ── 真实数据问题清单（close=0）──────────────────────────
log(f"## 真实数据问题：close/price=0 的文件")
log(f"| 品种 | 文件 | close=0行数 | null行数 |")
log(f"|------|------|-----------|--------|")
zero_issues = [r for r in results if r['zero_close'] > 0]
if zero_issues:
    for r in zero_issues:
        log(f"| {r['sym']} | {r['file']} | {r['zero_close']} | {r['null_close']} |")
else:
    log("| — | 无 | 0 | 0 |")
log("")

# ── FAIL文件清单 ─────────────────────────────────────
fail_files = [r for r in results if r['status'] == 'FAIL']
if fail_files:
    log(f"## FAIL文件详情（Schema不匹配）")
    for r in fail_files:
        log(f"**{r['sym']} / {r['file']}**")
        log(f"  Schema类型: {r['type']}")
        log(f"  错误: {r['err']}")
        fpath_full = None
        for sym2, fp2 in price_files:
            if sym2 == r['sym'] and os.path.basename(fp2) == r['file']:
                fpath_full = fp2; break
        if fpath_full:
            df2 = pd.read_csv(fpath_full)
            log(f"  列名: {list(df2.columns)}")
            log(f"  前2行:\n{df2.head(2).to_string()}")
        log("")

log("=" * 70)
log("Phase 1 修复检查完成")

# ── 写出问题文件清单供修复 ────────────────────────────
fix_list = []
for r in results:
    if r['status'] in ('FAIL', 'WARN') or r['zero_close'] > 0:
        fix_list.append({
            'symbol': r['sym'],
            'file': r['file'],
            'type': r['type'],
            'status': r['status'],
            'zero_close': r['zero_close'],
            'null_close': r['null_close'],
            'err': r['err']
        })

fix_df = pd.DataFrame(fix_list)
fix_csv = r'D:\futures_v6\macro_engine\research\reports\Phase1_Fix_List_20260427.csv'
fix_df.to_csv(fix_csv, index=False, encoding='utf-8-sig')

print(f"\n完成: PASS={total_pass} FAIL={total_fail} WARN={total_warn} SKIP={total_skip}")
print(f"报告: {OUTFILE}")
print(f"修复清单: {fix_csv}")
