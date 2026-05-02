#!/usr/bin/env python3
"""
Phase 1 — 纯数据质量检查（无Schema依赖）
只检查真实数据问题：日期可解析、价格列有效、无未来数据
"""
import os, glob
import pandas as pd
import numpy as np

OUTFILE = r'D:\futures_v6\macro_engine\research\reports\Phase1_Quality_Check_20260427.md'
BASE = r'D:\futures_v6\macro_engine\data\crawlers'
TARGET_SYMBOLS = ['AG','AL','AO','AU','BR','BU','CU','EC','EG','HC','I','J','JM',
                   'LC','LH','M','NI','NR','P','PB','PP','RB','RU','SA','SC','SN','TA','Y','ZN']

def log(msg):
    print(msg)
    with open(OUTFILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

open(OUTFILE, 'w', encoding='utf-8').close()
log("# Phase 1 — 纯数据质量检查报告（无Schema）")
log("**时间**: 2026-04-27 14:15 GMT+8")
log("**策略**: 无Schema依赖，只检查真实数据质量")
log("")
log("=" * 70)
log("")

# 收集文件
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

log(f"## 检查文件 ({len(price_files)} 个)")
log("")
log("| 品种 | 文件 | 行数 | 日期解析 | 价格>0 | 无未来数据 | 状态 |")
log("|------|------|------|----------|--------|------------|------|")

ok_count = 0; warn_count = 0; fail_count = 0; skip_count = 0
all_results = []

for sym, fpath in sorted(price_files):
    fname = os.path.basename(fpath)
    r = {'sym': sym, 'file': fname, 'rows': 0,
         'date_ok': False, 'price_ok': False, 'no_future': False, 'status': 'OK', 'issues': []}

    try:
        df = pd.read_csv(fpath)
        r['rows'] = len(df)
        if len(df) == 0:
            r['status'] = 'SKIP'; r['issues'].append('空文件'); skip_count += 1
            all_results.append(r); continue

        # 1. 日期列解析
        date_col = None
        for col in df.columns:
            try:
                test = pd.to_datetime(df[col])
                if test.notna().sum() > len(df) * 0.5:
                    date_col = col; break
            except:
                pass

        if date_col:
            df['date_parsed'] = pd.to_datetime(df[date_col])
            r['date_ok'] = True
        else:
            r['issues'].append('无法解析日期列'); r['status'] = 'FAIL'; fail_count += 1

        # 2. 价格列有效（>0）
        price_col = None
        for col in ['close', 'price', 'ratio', 'settle', 'latest',
                     'wti_spot_usd_bbl', 'usd_cny', 'cn_10y_yield', 'dswp10',
                     'au_ag_ratio_corrected', 'au_ag_ratio_g_per_g']:
            if col in df.columns:
                price_col = col; break
        if price_col:
            p = pd.to_numeric(df[price_col], errors='coerce')
            zero_pct = (p == 0).sum() / len(p) * 100
            null_pct = p.isnull().sum() / len(p) * 100
            if zero_pct < 5 and null_pct < 50:
                r['price_ok'] = True
            elif zero_pct >= 5:
                r['issues'].append(f'{price_col}=0: {zero_pct:.1f}%')
        else:
            # 无标准价格列（spread文件等），检查任何float列
            for col in df.select_dtypes(include=[np.number]).columns:
                if 'date' not in col.lower():
                    p = pd.to_numeric(df[col], errors='coerce')
                    if p.notna().sum() > len(df) * 0.3:
                        r['price_ok'] = True; price_col = col; break

        # 3. 无未来数据（日期不超过今天+1天）
        if r['date_ok']:
            max_date = df['date_parsed'].max()
            today = pd.Timestamp.today()
            if max_date <= today + pd.Timedelta(days=1):
                r['no_future'] = True
            else:
                r['issues'].append(f'未来数据: {max_date}'); r['status'] = 'FAIL'; fail_count += 1

        if r['status'] == 'OK' and r['date_ok'] and r['price_ok'] and r['no_future']:
            ok_count += 1
        elif r['status'] == 'OK':
            warn_count += 1

    except Exception as ex:
        r['status'] = 'FAIL'; r['issues'].append(f'读取错误: {str(ex)[:40]}')
        fail_count += 1

    all_results.append(r)
    st = {'OK': '[OK]', 'FAIL': '[FAIL]', 'SKIP': '[SKIP]'}.get(r['status'], r['status'])
    issues = '; '.join(r['issues'])[:50] if r['issues'] else ''
    log(f"| {r['sym']} | {fname} | {r['rows']} | {'Y' if r['date_ok'] else 'N'} | {'Y' if r['price_ok'] else 'N'} | {'Y' if r['no_future'] else 'N'} | {st} | {issues} |")

log("")
log(f"## 汇总")
log(f"| 指标 | 数值 |")
log(f"|------|------|")
log(f"| 总文件 | {len(price_files)} |")
log(f"| OK（全部通过） | {ok_count} |")
log(f"| WARN（有小问题） | {warn_count} |")
log(f"| FAIL | {fail_count} |")
log(f"| SKIP | {skip_count} |")
log(f"| 通过率 | {ok_count}/{len(price_files)-skip_count} = {ok_count/(len(price_files)-skip_count)*100:.1f}% |")
log("")
log(f"## FAIL/WARN详情")
log(f"| 品种 | 文件 | 问题 |")
log(f"|------|------|------|")
for r in all_results:
    if r['status'] == 'FAIL' or r['issues']:
        issues = '; '.join(r['issues'])
        log(f"| {r['sym']} | {r['file']} | {issues} |")

log("")
log("=" * 70)
log("结论: 数据质量真实情况以本报告为准")
print(f"\n完成: OK={ok_count} WARN={warn_count} FAIL={fail_count} SKIP={skip_count}")
print(f"报告: {OUTFILE}")
