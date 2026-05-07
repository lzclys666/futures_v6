#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pit_quality_check.py
PIT 数据质量巡检脚本

功能:
  1. 检查 PIT 违规（obs_date = pub_date 的记录）
  2. 检查数据新鲜度（最新 obs_date 距今超过 N 天）
  3. 检查因子数量是否达标（每个品种 >= MIN_FACTORS 个有效因子）

用法:
  python scripts/pit_quality_check.py              # 文本报告
  python scripts/pit_quality_check.py --json        # JSON 输出
  python scripts/pit_quality_check.py --stale-days 14  # 自定义过期天数阈值

退出码:
  0 = 正常
  1 = 有警告（过期/因子不足）
  2 = 有严重问题（PIT 违规率 > 50% 或严重数据缺失）
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────
DB_PATH = Path(r"D:\futures_v6\macro_engine\pit_data.db")
MIN_FACTORS_DEFAULT = 10          # 每个品种最低有效因子数
DEFAULT_STALE_DAYS = 5            # 超过此天数标记为过期
PIT_VIOLATION_WARN = 0.05         # 违规率 > 5% 警告
PIT_VIOLATION_CRIT = 0.50         # 违规率 > 50% 严重


def get_connection():
    if not DB_PATH.exists():
        print(f"[ERROR] 数据库不存在: {DB_PATH}", file=sys.stderr)
        sys.exit(2)
    return sqlite3.connect(str(DB_PATH))


def check_pit_violations(conn):
    """检查 obs_date = pub_date 的违规记录"""
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol,
               SUM(CASE WHEN obs_date = pub_date THEN 1 ELSE 0 END) AS violations,
               COUNT(*) AS total
        FROM pit_factor_observations
        GROUP BY symbol
        ORDER BY symbol
    """)
    results = []
    for symbol, violations, total in cur.fetchall():
        rate = violations / total if total > 0 else 0.0
        results.append({
            "symbol": symbol,
            "violations": violations,
            "total": total,
            "rate": rate,
        })
    return results


def check_data_freshness(conn, stale_days):
    """检查每个品种最新 obs_date 的新鲜度"""
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol, MAX(obs_date) AS latest_date
        FROM pit_factor_observations
        GROUP BY symbol
        ORDER BY symbol
    """)
    today = datetime.now().date()
    results = []
    for symbol, latest_str in cur.fetchall():
        if latest_str is None:
            results.append({
                "symbol": symbol,
                "latest_date": None,
                "days_ago": None,
                "stale": True,
            })
            continue
        try:
            latest = datetime.strptime(latest_str, "%Y-%m-%d").date()
        except ValueError:
            latest = datetime.strptime(latest_str, "%Y/%m/%d").date()
        days_ago = (today - latest).days
        results.append({
            "symbol": symbol,
            "latest_date": latest_str,
            "days_ago": days_ago,
            "stale": days_ago > stale_days,
        })
    return results


def check_factor_counts(conn, min_factors):
    """检查每个品种的有效因子数量"""
    cur = conn.cursor()
    cur.execute("""
        SELECT p.symbol, COUNT(DISTINCT p.factor_code) AS active_factors
        FROM pit_factor_observations p
        LEFT JOIN factor_metadata m ON p.factor_code = m.factor_code
        WHERE m.is_active = 1 OR m.is_active IS NULL
        GROUP BY p.symbol
        ORDER BY p.symbol
    """)
    results = []
    for symbol, count in cur.fetchall():
        results.append({
            "symbol": symbol,
            "active_factors": count,
            "required": min_factors,
            "ok": count >= min_factors,
        })
    return results


def determine_exit_code(pit_data, freshness, factor_counts):
    """0=正常, 1=警告, 2=严重"""
    exit_code = 0

    # 严重: 任何品种违规率 > 50%
    for row in pit_data:
        if row["rate"] > PIT_VIOLATION_CRIT:
            return 2

    # 严重: 任何品种完全无数据
    for row in freshness:
        if row["latest_date"] is None:
            return 2

    # 警告: 违规率 > 5%
    for row in pit_data:
        if row["rate"] > PIT_VIOLATION_WARN:
            exit_code = 1

    # 警告: 数据过期
    for row in freshness:
        if row["stale"]:
            exit_code = 1

    # 警告: 因子不足
    for row in factor_counts:
        if not row["ok"]:
            exit_code = 1

    return exit_code


def format_text_report(pit_data, freshness, factor_counts, stale_days, min_factors):
    """生成文本格式报告"""
    lines = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append("=== PIT 数据质量报告 ===")
    lines.append(f"生成时间: {now_str}")
    lines.append(f"数据库: {DB_PATH}")
    lines.append("")

    # PIT 违规统计
    lines.append("【PIT 违规统计】")
    lines.append(f"{'品种':<6} {'违规数':>8} {'总记录数':>10} {'违规率':>8}")
    lines.append("-" * 38)
    for row in pit_data:
        rate_pct = f"{row['rate'] * 100:.1f}%"
        flag = " ⛔" if row["rate"] > PIT_VIOLATION_CRIT else (" ⚠️" if row["rate"] > PIT_VIOLATION_WARN else "")
        lines.append(f"{row['symbol']:<6} {row['violations']:>8} {row['total']:>10} {rate_pct:>8}{flag}")
    lines.append("")

    # 数据新鲜度
    lines.append(f"【数据新鲜度】(阈值: {stale_days} 天)")
    lines.append(f"{'品种':<6} {'最新日期':<12} {'距今天数':>8} {'状态':<4}")
    lines.append("-" * 36)
    for row in freshness:
        if row["latest_date"] is None:
            lines.append(f"{row['symbol']:<6} {'N/A':<12} {'N/A':>8} ⛔")
        else:
            status = "✅" if not row["stale"] else "⚠️"
            lines.append(f"{row['symbol']:<6} {row['latest_date']:<12} {row['days_ago']:>8} {status}")
    lines.append("")

    # 因子数量
    lines.append(f"【因子数量】(最低要求: {min_factors})")
    lines.append(f"{'品种':<6} {'有效因子数':>10} {'要求':>6} {'状态':<4}")
    lines.append("-" * 32)
    for row in factor_counts:
        status = "✅" if row["ok"] else "❌"
        lines.append(f"{row['symbol']:<6} {row['active_factors']:>10} {row['required']:>6} {status}")
    lines.append("")

    # 汇总
    total_violations = sum(r["violations"] for r in pit_data)
    stale_count = sum(1 for r in freshness if r["stale"])
    under_count = sum(1 for r in factor_counts if not r["ok"])
    lines.append("【汇总】")
    lines.append(f"  总违规数: {total_violations}")
    lines.append(f"  过期品种: {stale_count}")
    lines.append(f"  因子不足品种: {under_count}")

    return "\n".join(lines)


def build_json_report(pit_data, freshness, factor_counts, stale_days, min_factors, exit_code):
    """生成 JSON 格式报告"""
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "db_path": str(DB_PATH),
        "stale_days_threshold": stale_days,
        "min_factors": min_factors,
        "exit_code": exit_code,
        "pit_violations": pit_data,
        "data_freshness": freshness,
        "factor_counts": factor_counts,
        "summary": {
            "total_violations": sum(r["violations"] for r in pit_data),
            "stale_symbols": [r["symbol"] for r in freshness if r["stale"]],
            "under_factor_symbols": [r["symbol"] for r in factor_counts if not r["ok"]],
        },
    }


def main():
    # Windows 终端默认 GBK，强制 UTF-8 以支持 emoji
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(description="PIT 数据质量巡检")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--stale-days", type=int, default=DEFAULT_STALE_DAYS,
                        help=f"数据过期天数阈值 (默认 {DEFAULT_STALE_DAYS})")
    parser.add_argument("--min-factors", type=int, default=MIN_FACTORS_DEFAULT,
                        help=f"每个品种最低有效因子数 (默认 {MIN_FACTORS_DEFAULT})")
    args = parser.parse_args()

    conn = get_connection()
    try:
        pit_data = check_pit_violations(conn)
        freshness = check_data_freshness(conn, args.stale_days)
        factor_counts = check_factor_counts(conn, args.min_factors)
    finally:
        conn.close()

    exit_code = determine_exit_code(pit_data, freshness, factor_counts)

    if args.json:
        report = build_json_report(pit_data, freshness, factor_counts,
                                   args.stale_days, args.min_factors, exit_code)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_text_report(pit_data, freshness, factor_counts,
                                 args.stale_days, args.min_factors))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
