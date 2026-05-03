# -*- coding: utf-8 -*-
"""
PIT 数据完整性验证脚本
对 pit_factor_observations 表执行三类数据质量检查:
  1. 前视偏差 (Look-ahead Bias)
  2. 幸存者偏差 (Survivorship Bias)
  3. 交易日历对齐 (Weekend Data)
"""

import os
import sys
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path
import io

# 强制 UTF-8 输出（Windows GBK 控制台兼容 emoji）
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────
# 颜色输出
# ─────────────────────────────────────────────
class Col:
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"

def c_green(txt):  return f"{Col.GREEN}{txt}{Col.RESET}"
def c_yellow(txt): return f"{Col.YELLOW}{txt}{Col.RESET}"
def c_red(txt):    return f"{Col.RED}{Col.BOLD}{txt}{Col.RESET}"
def c_bold(txt):   return f"{Col.BOLD}{txt}{Col.RESET}"

# Emoji shorthand
EM_OK  = "✅"
EM_WRN = "🟡"
EM_ERR = "🔴"
EM_RUN = "⚙️ "
EM_SYM = "🔍"

# ─────────────────────────────────────────────
# 日志写入
# ─────────────────────────────────────────────
class LogWriter:
    def __init__(self, log_path: str):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self._buf: list[str] = []

    def write(self, line: str, console: str = ""):
        self._buf.append(line)
        if console:
            print(console)
        else:
            print(line)

    def flush(self):
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(self._buf))

# ─────────────────────────────────────────────
# 数据库连接
# ─────────────────────────────────────────────
def connect(db_path: str) -> sqlite3.Connection:
    if not os.path.exists(db_path):
        print(c_red(f"{EM_ERR} 数据库不存在: {db_path}"))
        sys.exit(2)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# ─────────────────────────────────────────────
# 检查 1: 前视偏差
#   obs_date > pub_date  →  观测日期晚于发布日期 = 使用了未来数据
#   正确：pub_date 是"爬虫运行时"，obs_date 是"数据实际对应日期"
#   如果 obs_date（实际观测日）比 pub_date（发布日期）还晚，说明爬虫
#   在obs_date当天/之后才跑，但数据填的是未来才实际发生的事件日期
#   这意味着该数据点包含"当时还不存在"的信息，是前视偏差
#   反之 obs_date < pub_date 是正常的（数据发布滞后，如宏观数据晚1-2天）
# ─────────────────────────────────────────────
def check_lookahead(conn: sqlite3.Connection, log: LogWriter, limit: int = 10):
    log.write("")
    log.write(f"{EM_SYM} 【检查 1/3】前视偏差 (Look-ahead Bias)", c_bold(f"{EM_SYM} 【检查 1/3】前视偏差"))
    log.write("   条件: obs_date > pub_date (观测日期晚于发布日期)")
    log.write("   含义: 记录使用了在实际发布日期之前尚未公开的数据", "")

    cur = conn.cursor()
    # 先获取总数（LIMIT 1000 只影响样例展示，不影响总数统计）
    cur.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE obs_date > pub_date")
    total = cur.fetchone()[0]

    # 样例查询（LIMIT 只影响展示，总数已在上方精确统计）
    cur.execute("""
        SELECT factor_code, symbol, pub_date, obs_date, raw_value, source
        FROM pit_factor_observations
        WHERE obs_date > pub_date
        ORDER BY obs_date DESC, pub_date DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()

    log.write("")
    if total == 0:
        log.write(f"   {EM_OK} {c_green('通过')} — 未发现前视偏差记录", "")
    else:
        log.write(f"   {EM_ERR} {c_red(f'发现 {total} 条前视偏差记录！')}", "")
        log.write(f"   {EM_WRN} 样例 (最多 {limit} 条):", "")
        log.write(f"   {'factor_code':<28} {'symbol':<6} {'pub_date':<12} {'obs_date':<12} {'raw_value':<12} source", "")
        log.write("   " + "-" * 80)
        for i, r in enumerate(rows[:limit]):
            log.write(f"   {r['factor_code']:<28} {r['symbol']:<6} {r['pub_date']:<12} {r['obs_date']:<12} "
                      f"{str(r['raw_value']):<12} {r['source'] or ''}", "")

    return total

# ─────────────────────────────────────────────
# 检查 2: 幸存者偏差
#   子查询 A: 注册品种但无任何因子观测
#   子查询 B: 有观测但不在注册品种列表中的品种
# ─────────────────────────────────────────────
def check_survivorship(conn: sqlite3.Connection, log: LogWriter, limit: int = 10):
    log.write("")
    log.write(f"{EM_SYM} 【检查 2/3】幸存者偏差 (Survivorship Bias)", c_bold(f"{EM_SYM} 【检查 2/3】幸存者偏差"))
    log.write("   A) 注册品种但无因子观测  |  B) 有观测但未注册", "")

    cur = conn.cursor()

    # 子查询 A: 注册品种（在 _futures_ohlcv 表中）但 pit 中无观测
    cur.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table'
          AND name LIKE '%_futures_ohlcv'
          AND name NOT LIKE 'ag_%'
        ORDER BY name
    """)
    registered = {row["name"].replace("_futures_ohlcv", "") for row in cur.fetchall()}

    cur.execute("SELECT DISTINCT symbol FROM pit_factor_observations")
    observed = {row["symbol"] for row in cur.fetchall()}

    # A: 注册但无观测
    orphaned = registered - observed
    # B: 有观测但未注册
    untracked = observed - registered

    all_ok = (len(orphaned) == 0 and len(untracked) == 0)

    log.write("")
    if all_ok:
        log.write(f"   {EM_OK} {c_green('通过')} — 注册品种与观测品种完全一致", "")
    else:
        if orphaned:
            log.write(f"   {EM_WRN} {c_yellow(f'A) 注册品种但无因子观测 ({len(orphaned)} 个): ')}"
                      f"{sorted(orphaned)}", "")
        if untracked:
            log.write(f"   {EM_WRN} {c_yellow(f'B) 有观测但未注册 ({len(untracked)} 个): ')}"
                      f"{sorted(untracked)}", "")

    return len(orphaned) + len(untracked)

# ─────────────────────────────────────────────
# 检查 3: 交易日历对齐
#   非 24h 市场因子（所有期货因子）出现周末 (Saturday=5, Sunday=6) 数据
# ─────────────────────────────────────────────
WEEKEND_SQLITE = """
    SELECT factor_code, symbol, pub_date, obs_date, raw_value, source,
           strftime('%w', obs_date) AS dow,
           CASE CAST(strftime('%w', obs_date) AS INTEGER)
               WHEN 0 THEN '周日'
               WHEN 5 THEN '周五(持仓)'
               WHEN 6 THEN '周六'
               ELSE '周一~周四'
           END AS obs_weekday
    FROM pit_factor_observations
    WHERE CAST(strftime('%w', obs_date) AS INTEGER) IN (0, 5, 6)
      AND obs_date NOT LIKE '%-12-%'
      AND obs_date NOT LIKE '%-31-%'
    ORDER BY obs_date DESC
    LIMIT 1000
"""

def check_weekend(conn: sqlite3.Connection, log: LogWriter, limit: int = 10):
    log.write("")
    log.write(f"{EM_SYM} 【检查 3/3】交易日历对齐 (Weekend Data)", c_bold(f"{EM_SYM} 【检查 3/3】交易日历对齐"))
    log.write("   条件: obs_date 为周六(5)或周日(0) — 非 24h 市场不应有周末数据", "")
    log.write("   注: 周五持仓过渡视为正常,仅报告周六/周日的异常", "")

    cur = conn.cursor()
    # 先获取总数（LIMIT 1000 只影响样例展示，不影响总数统计）
    cur.execute("SELECT COUNT(*) FROM pit_factor_observations WHERE CAST(strftime('%w', obs_date) AS INTEGER) IN (0, 6)")
    total = cur.fetchone()[0]
    # 样例查询（LIMIT 只影响展示，总数已在上方精确统计）
    cur.execute("""
        SELECT factor_code, symbol, pub_date, obs_date, raw_value, source,
               CAST(strftime('%w', obs_date) AS INTEGER) AS dow
        FROM pit_factor_observations
        WHERE CAST(strftime('%w', obs_date) AS INTEGER) IN (0, 6)
        ORDER BY obs_date DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()

    log.write("")
    if total == 0:
        log.write(f"   {EM_OK} {c_green('通过')} — 未发现周末异常数据", "")
    else:
        dow_label = {0: "周日", 6: "周六"}
        log.write(f"   {EM_ERR} {c_red(f'发现 {total} 条周末数据！')}", "")
        log.write(f"   {EM_WRN} 样例 (最多 {limit} 条):", "")
        log.write(f"   {'factor_code':<28} {'symbol':<6} {'obs_date':<12} dow  raw_value  source", "")
        log.write("   " + "-" * 72)
        for i, r in enumerate(rows[:limit]):
            log.write(f"   {r['factor_code']:<28} {r['symbol']:<6} {r['obs_date']:<12} "
                      f"{dow_label.get(r['dow'], r['dow']):<4}  {str(r['raw_value']):<10} {r['source'] or ''}", "")

    return total

# ─────────────────────────────────────────────
# 统计信息
# ─────────────────────────────────────────────
def summary_stats(conn: sqlite3.Connection, log: LogWriter):
    cur = conn.cursor()
    log.write("")
    log.write("─" * 60, "")
    log.write(f"{Col.BOLD}📊 数据统计{Col.RESET}", c_bold("📊 数据统计"))

    cur.execute("SELECT COUNT(*) FROM pit_factor_observations")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT symbol) FROM pit_factor_observations")
    n_symbols = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT factor_code) FROM pit_factor_observations")
    n_factors = cur.fetchone()[0]

    cur.execute("SELECT MIN(pub_date), MAX(pub_date) FROM pit_factor_observations")
    pub_range = cur.fetchone()

    cur.execute("SELECT MIN(obs_date), MAX(obs_date) FROM pit_factor_observations")
    obs_range = cur.fetchone()

    log.write(f"   总记录数  : {total:,}", "")
    log.write(f"   品种数    : {n_symbols}", "")
    log.write(f"   因子数    : {n_factors}", "")
    log.write(f"   pub_date  : {pub_range[0]} ~ {pub_range[1]}", "")
    log.write(f"   obs_date  : {obs_range[0]} ~ {obs_range[1]}", "")

# ─────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="PIT 数据完整性验证")
    parser.add_argument("--db", default=r"D:\futures_v6\macro_engine\pit_data.db",
                        help="SQLite 数据库路径")
    parser.add_argument("--limit", type=int, default=10,
                        help="样例输出行数")
    parser.add_argument("--no-color", action="store_true", help="禁用颜色输出")
    args = parser.parse_args()

    if args.no_color:
        global Col, EM_OK, EM_WRN, EM_ERR, EM_RUN, EM_SYM
        Col = type("Col", (), {k: "" for k in ["GREEN","YELLOW","RED","BOLD","RESET"]})()
        EM_OK = "[OK]"; EM_WRN = "[WRN]"; EM_ERR = "[ERR]"
        EM_RUN = ""; EM_SYM = "[*]"

    today = datetime.now().strftime("%Y-%m-%d")
    base  = os.path.dirname(args.db)
    log_dir = os.path.join(base, "logs")
    log_path = os.path.join(log_dir, f"pit_integrity_{today}.log")

    log = LogWriter(log_path)

    header = (
        f"{Col.BOLD}{'='*60}{Col.RESET}\n"
        f"{Col.BOLD}  PIT 数据完整性检查  |  {today}{Col.RESET}\n"
        f"{Col.BOLD}{'='*60}{Col.RESET}"
    )
    log.write(header, c_bold("=" * 60))
    log.write(f"  数据库: {args.db}", "")
    log.write(f"  日志:   {log_path}", "")

    conn = connect(args.db)

    try:
        # 统计
        summary_stats(conn, log)

        # 三类检查
        n_lookahead = check_lookahead(conn, log, args.limit)
        n_survivorship = check_survivorship(conn, log, args.limit)
        n_weekend = check_weekend(conn, log, args.limit)

        # 汇总
        total_issues = n_lookahead + n_survivorship + n_weekend
        log.write("")
        log.write("─" * 60, "")
        verdict = (
            f"{EM_ERR} {c_red('检查失败 — 存在数据质量问题')}"
            if total_issues > 0
            else f"{EM_OK} {c_green('检查通过 — 所有 PIT 完整性检查项均正常')}"
        )
        log.write(f"{Col.BOLD}【汇总】问题总数: {total_issues}{Col.RESET}", "")
        log.write(f"  前视偏差    : {n_lookahead}", "")
        log.write(f"  幸存者偏差  : {n_survivorship}", "")
        log.write(f"  交易日历    : {n_weekend}", "")
        log.write("")
        log.write(f"{Col.BOLD}判定: {verdict}{Col.RESET}", "")
        log.write(f"  日志文件: {log_path}", "")

    finally:
        conn.close()
        log.flush()

    print(f"\n{Col.BOLD}日志已写入: {log_path}{Col.RESET}")

    # exit code
    sys.exit(1 if total_issues > 0 else 0)


if __name__ == "__main__":
    main()
