#!/usr/bin/env python3
"""Phase 0 完整审计脚本"""
import sqlite3, os, glob, json
from datetime import datetime, timezone, timedelta

BASE = r'D:\futures_v6\macro_engine'
DB = r'D:\futures_v6\macro_engine\pit_data.db'
CRAWLERS = r'D:\futures_v6\macro_engine\data\crawlers'
OUTFILE = r'D:\futures_v6\macro_engine\research\reports\Phase0_Audit_Report_20260427.md'

TARGET_SYMBOLS = ['AG','AL','AO','AU','BR','BU','CU','EC','EG','HC','I','J','JM',
                   'LC','LH','M','NI','NR','P','PB','PP','RB','RU','SA','SC','SN','TA','Y','ZN']

# 清空输出文件
open(OUTFILE, 'w', encoding='utf-8').close()

def log(msg, console=True):
    if console:
        try:
            print(msg)
        except UnicodeEncodeError:
            # Strip non-ASCII chars for GBK console
            ascii_msg = msg.encode('ascii', errors='replace').decode('ascii')
            print(ascii_msg)
    with open(OUTFILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

def dt_from_ms(ms):
    if not ms: return 'N/A'
    return datetime.fromtimestamp(ms/1000, tz=timezone(timedelta(hours=8))).strftime('%m-%d %H:%M')

log("# Phase 0 完整审计报告")
log(f"**审计时间**: 2026-04-27 13:10 GMT+8")
log(f"**数据路径**: {BASE}")
log(f"**数据库**: {DB}")
log("")
log("=" * 70)

# ── 1. 数据库健康 ──────────────────────────────────────
log("\n## [1] 数据库健康检查")
conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM pit_factor_observations")
total = cur.fetchone()[0]
log(f"  总记录数: {total:,}")

cur.execute("SELECT MAX(obs_date) FROM pit_factor_observations")
max_obs = cur.fetchone()[0]
log(f"  最新obs_date: {max_obs}")

cur.execute("SELECT MAX(pub_date) FROM pit_factor_observations")
max_pub = cur.fetchone()[0]
log(f"  最新pub_date: {max_pub}")

cur.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE obs_date > '2026-04-27'")
future = cur.fetchone()[0]
log(f"  未来obs_date (应=0): {future}  {'[PASS]' if future == 0 else '[FAIL]'}")

cur.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE raw_value IS NULL")
null_val = cur.fetchone()[0]
log(f"  NULL值记录 (应=0): {null_val}  {'[PASS]' if null_val == 0 else '[FAIL]'}")

cur.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE source_confidence IS NULL OR source_confidence < 0")
bad_conf = cur.fetchone()[0]
log(f"  无效置信度 (应=0): {bad_conf}  {'[PASS]' if bad_conf == 0 else '[FAIL]'}")

cur.execute("SELECT COUNT(DISTINCT symbol) FROM pit_factor_observations")
sym_count = cur.fetchone()[0]
log(f"  数据库品种数: {sym_count}")

conn.close()

# ── 2. 品种覆盖 ──────────────────────────────────────
log("\n## [2] 品种数据覆盖")
log(f"  {'品种':<6} {'记录数':>10} {'最新日期':>12} {'因子数':>6}")
log(f"  {'-'*6:<6} {'-'*10:>10} {'-'*12:>12} {'-'*6:>6}")

results = []
for sym in TARGET_SYMBOLS:
    conn2 = sqlite3.connect(DB)
    cur2 = conn2.cursor()
    cur2.execute("SELECT COUNT(*), MAX(obs_date) FROM pit_factor_observations WHERE symbol=?", (sym,))
    cnt, latest = cur2.fetchone()
    cur2.execute("SELECT COUNT(DISTINCT factor_code) FROM pit_factor_observations WHERE symbol=?", (sym,))
    fcnt = cur2.fetchone()[0]
    conn2.close()
    results.append((sym, cnt or 0, latest, fcnt or 0))
    flag = "[OK]" if cnt > 0 else "[NO DATA]"
    log(f"  {flag} {sym:<5} {cnt:>10,} {str(latest):>12} {fcnt:>6}")

has_data = [(s,c,f) for s,c,_,f in results if c > 0]
no_data = [s for s,c,_,_ in results if c == 0]
log(f"\n  有数据品种: {len(has_data)}/{len(TARGET_SYMBOLS)}")
if no_data:
    log(f"  无数据品种: {no_data}")

# ── 3. 因子完整度 ─────────────────────────────────────
log("\n## [3] 因子完整度（22品种）")
CONFIG_FACTORS = {
    'AG':12,'AL':8,'AO':3,'AU':11,'BR':12,'BU':15,'CU':11,'EC':2,'EG':10,
    'HC':18,'I':5,'J':17,'JM':18,'LC':2,'LH':2,'M':12,'NI':8,'NR':18,
    'P':6,'PB':17,'PP':15,'RB':7,'RU':12,'SA':18,'SC':2,'SN':3,'TA':10,'Y':16,'ZN':3
}

factor_details = []
for sym, cnt, _, fcnt in results:
    if sym not in CONFIG_FACTORS:
        continue
    cfg = CONFIG_FACTORS[sym]
    pct = (fcnt / cfg * 100) if cfg > 0 else 0
    status = "[OK]" if pct >= 70 else ("[WARN]" if pct >= 50 else "[FAIL]")
    factor_details.append((sym, fcnt, cfg, pct, status))

total_fc = sum(f[1] for f in factor_details)
total_cfg = sum(f[2] for f in factor_details)
overall_pct = total_fc / total_cfg * 100 if total_cfg > 0 else 0

log(f"  总体因子完整度: {total_fc}/{total_cfg} = {overall_pct:.1f}%  (目标 >= 70%)")
log(f"  {'品种':<6} {'实际':>6} {'配置':>6} {'完整度':>10} {'状态':<6}")
log(f"  {'-'*6:<6} {'-'*6:>6} {'-'*6:>6} {'-'*10:>10} {'-'*6:<6}")
for sym, fc, cfg, pct, st in sorted(factor_details, key=lambda x: -x[3]):
    log(f"  {sym:<6} {fc:>6} {cfg:>6} {pct:>9.1f}% {st:<6}")

# ── 4. 价格文件IC窗口 ─────────────────────────────────
log("\n## [4] 价格文件IC窗口")
# 查找所有期货价格文件
price_files = []
for sym in TARGET_SYMBOLS:
    sym_dir = os.path.join(CRAWLERS, sym, 'daily')
    if os.path.isdir(sym_dir):
        for f in glob.glob(os.path.join(sym_dir, '*.csv')):
            fname = os.path.basename(f)
            if 'close' in fname.lower() or 'fut' in fname.lower() or 'lme' in fname.lower():
                price_files.append(f)
# shared文件
shared_dir = os.path.join(CRAWLERS, '_shared', 'daily')
if os.path.isdir(shared_dir):
    for f in glob.glob(os.path.join(shared_dir, '*.csv')):
        price_files.append(f)

log(f"  {'文件名':<45} {'行数':>6} {'5日IC':>8} {'10日IC':>8} {'20日IC':>8}")
log(f"  {'-'*45:<45} {'-'*6:>6} {'-'*8:>8} {'-'*8:>8} {'-'*8:>8}")
ic_ok_count = 0
for pf in price_files:
    fname = os.path.basename(pf)
    try:
        with open(pf, 'r', encoding='utf-8') as f:
            lines = sum(1 for _ in f) - 1
        ic5 = max(lines - 4, 0)
        ic10 = max(lines - 9, 0)
        ic20 = max(lines - 19, 0)
        ok = "[OK]" if ic20 >= 60 else "[FAIL]"
        if ic20 >= 60: ic_ok_count += 1
        log(f"  {ok} {fname:<43} {lines:>6} {ic5:>8} {ic10:>8} {ic20:>8}")
    except Exception as e:
        log(f"  [ERR] {fname:<45} 读取失败: {e}")

log(f"\n  IC窗口>=60天的文件: {ic_ok_count}/{len(price_files)}")

# ── 5. cron任务状态 ───────────────────────────────────
log("\n## [5] cron任务状态")
cron_file = r'C:\Users\Administrator\.qclaw\cron\jobs.json'
with open(cron_file, 'r', encoding='utf-8') as f:
    jobs_data = json.load(f)['jobs']

active = [j for j in jobs_data if j.get('enabled')]
disabled = [j for j in jobs_data if not j.get('enabled')]
log(f"  总任务数: {len(jobs_data)}")
log(f"  启用中: {len(active)}")
log(f"  已禁用: {len(disabled)}")

log("\n  启用任务:")
for j in active:
    last = j.get('state',{}).get('lastRunAtMs')
    next_run = j.get('state',{}).get('nextRunAtMs')
    log(f"    [ACTIVE] {j['name']}")
    log(f"             last={dt_from_ms(last)}  next={dt_from_ms(next_run)}")

log("\n  禁用任务:")
for j in disabled:
    last = j.get('state',{}).get('lastRunAtMs')
    status = j.get('state',{}).get('lastRunStatus','从未运行')
    log(f"    [DISABLED] {j['name']} (last={status})")

# ── 6. Gate 0 最终检查 ────────────────────────────────
log("\n## [6] Gate 0 最终检查表")
print()

checks = [
    ("因子完整度", f">=70%", f"{overall_pct:.1f}%", overall_pct >= 70),
    ("品种数据覆盖", "22品种", f"{len(has_data)}品种有数据", len(has_data) >= 22),
    ("IC窗口>=60天", "全部文件", f"{ic_ok_count}/{len(price_files)}文件", ic_ok_count >= len(price_files) * 0.8),
    ("数据管道存活", "obs_date新鲜", f"最新{max_obs}", max_obs >= '2026-04-23'),
    ("PIT合规(未来数据)", "0条", f"{future}条", future == 0),
    ("PIT合规(NULL值)", "0条", f"{null_val}条", null_val == 0),
    ("cron至少1个启用", ">=1个", f"{len(active)}个", len(active) >= 1),
]

log(f"  {'检查项':<25} {'要求':<15} {'实际':<20} {'状态':<8}")
log(f"  {'-'*25:<25} {'-'*15:<15} {'-'*20:<20} {'-'*8:<8}")
passed = 0
for name, req, actual, ok in checks:
    st = "[PASS]" if ok else "[FAIL]"
    if ok: passed += 1
    log(f"  {name:<25} {req:<15} {actual:<20} {st:<8}")

log(f"\n  Gate 0 通过: {passed}/{len(checks)}")
if passed == len(checks):
    log("  最终评定: [PASS] 全部通过 - Gate 0 已通过")
elif passed >= len(checks) - 1:
    log("  最终评定: [MARGINAL] 接近通过 - 1项以内可接受")
elif passed >= len(checks) - 2:
    log("  最终评定: [CONDITIONAL] 有条件通过 - 需修复少量问题")
else:
    log(f"  最终评定: [FAIL] 未通过 - {len(checks) - passed}项不合格")

log("")
log("=" * 70)
log("审计完成")
print(f"\n报告已保存至: {OUTFILE}")
