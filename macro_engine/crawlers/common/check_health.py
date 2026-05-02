# check_health.py - 数据库健康检查 v2
# 用法: python check_health.py [--alert] [--json]
import sys, os, sqlite3, json
from datetime import date, timedelta

DB = "d:/futures_v6/macro_engine/pit_data.db"

def get_cutoff(days=7):
    return (date.today() - timedelta(days=days)).isoformat()

def check_health(alert_only=False, as_json=False):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    today = date.today().isoformat()
    cutoff_7d = get_cutoff(7)
    cutoff_3d = get_cutoff(3)
    cutoff_1d = get_cutoff(1)

    # 1. 全量因子（近7天有数据的）
    cur.execute("""
        SELECT DISTINCT factor_code, symbol
        FROM pit_factor_observations
        WHERE obs_date >= ?
        ORDER BY factor_code
    """, (cutoff_7d,))
    all_factors = {r[0]: r[1] for r in cur.fetchall()}

    # 2. NULL / 非数值检查（近7天）
    cur.execute("""
        SELECT factor_code, COUNT(*) as cnt
        FROM pit_factor_observations
        WHERE obs_date >= ? AND (raw_value IS NULL OR typeof(raw_value) NOT IN ('real','integer'))
        GROUP BY factor_code
    """, (cutoff_7d,))
    null_rows = {r[0]: r[1] for r in cur.fetchall()}

    # 3. L4 回补检查（source_confidence <= 0.6，近7天）
    cur.execute("""
        SELECT factor_code, COUNT(*) as cnt,
               MAX(source_confidence) as max_conf
        FROM pit_factor_observations
        WHERE obs_date >= ? AND source_confidence <= 0.6
        GROUP BY factor_code
    """, (cutoff_7d,))
    l4_factors = {r[0]: (r[1], r[2]) for r in cur.fetchall()}

    # 4. Stale 数据（超过3天没更新的因子）
    cur.execute("""
        SELECT factor_code, MAX(obs_date) as last_obs
        FROM pit_factor_observations
        WHERE obs_date < ?
        GROUP BY factor_code
    """, (cutoff_3d,))
    stale_factors = {r[0]: r[1] for r in cur.fetchall()}

    # 5. 今日有数据的因子
    cur.execute("""
        SELECT DISTINCT factor_code
        FROM pit_factor_observations
        WHERE obs_date = ?
    """, (today,))
    today_factors = set(r[0] for r in cur.fetchall())

    # 6. 数值异常检测（负值、极端值）- 抽样检查
    cur.execute("""
        SELECT factor_code,
               MIN(raw_value) as min_val,
               MAX(raw_value) as max_val,
               AVG(raw_value) as avg_val
        FROM pit_factor_observations
        WHERE obs_date >= ? AND raw_value IS NOT NULL
        GROUP BY factor_code
    """, (cutoff_7d,))
    stats = {r[0]: (r[1], r[2], r[3]) for r in cur.fetchall()}

    conn.close()

    # 汇总
    report = {
        "run_date": today,
        "total_recent_factors": len(all_factors),
        "today_updated": len(today_factors),
        "null_issues": null_rows,
        "l4_backfill": l4_factors,
        "stale_factors": stale_factors,
        "factor_stats": stats,
        "all_factors": sorted(all_factors.keys())
    }

    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    # 人类可读输出
    print("=" * 60)
    print(f"数据库健康检查  ({today})")
    print("=" * 60)
    print(f"近7天有数据的因子: {len(all_factors)}")
    print(f"今日已更新: {len(today_factors)}")

    # NULL 问题
    if null_rows:
        print(f"\n[CRITICAL] NULL/无效值 ({len(null_rows)} 个因子):")
        for fc, cnt in sorted(null_rows.items()):
            print(f"  {fc}: {cnt} 条 NULL")
    else:
        print("\n[OK] 无 NULL/无效值")

    # L4 回补
    l4_list = sorted(l4_factors.items(), key=lambda x: -x[1][0])
    l4_pct = {fc: round(cnt / stats[fc][2] * 100) if fc in stats and stats[fc][2] > 0 else 0 for fc, (cnt, _) in l4_factors.items()}
    high_l4 = [(fc, cnt, max_conf) for fc, (cnt, max_conf) in l4_list if cnt > 3]
    if high_l4:
        print(f"\n[WARN] L4 回补率偏高 ({len(high_l4)} 个因子 >3条 或 conf<=0.6):")
        for fc, cnt, max_conf in high_l4[:20]:
            pct = l4_pct.get(fc, 0)
            print(f"  {fc}: {cnt} 条 L4 (max_conf={max_conf}, ~{pct}%)")
    else:
        print("\n[OK] L4 回补率正常")

    # Stale 数据
    if stale_factors and not alert_only:
        print(f"\n[INFO] Stale 因子（3天以上未更新, {len(stale_factors)} 个）:")
        for fc, last in sorted(stale_factors.items())[:20]:
            print(f"  {fc}: 最后 {last}")
        if len(stale_factors) > 20:
            print(f"  ... 还有 {len(stale_factors) - 20} 个")

    # 今日未更新但近7天有的
    not_today = set(all_factors.keys()) - today_factors
    if not_today and not alert_only:
        print(f"\n[INFO] 今日未更新 ({len(not_today)} 个):")
        for fc in sorted(not_today)[:15]:
            print(f"  {fc}")
        if len(not_today) > 15:
            print(f"  ... 还有 {len(not_today) - 15} 个")

    # 全量因子列表
    if not alert_only:
        print(f"\n--- 全量因子列表 ({len(all_factors)} 个) ---")
        for i, fc in enumerate(sorted(all_factors.keys()), 1):
            tag = ""
            if fc in null_rows:
                tag += " [NULL]"
            if fc in l4_factors:
                tag += " [L4]"
            print(f"  {fc}{tag}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    alert = "--alert" in sys.argv
    as_json = "--json" in sys.argv
    check_health(alert_only=alert, as_json=as_json)
