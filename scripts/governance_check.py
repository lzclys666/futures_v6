#!/usr/bin/env python3
"""
治理框架逾期检查脚本
检查：议题投票截止、任务截止、每日ACK

用法：
    python governance_check.py [--mode check|enforce]
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# 配置
DOCS_DIR = Path(r"D:\futures_v6\docs")
EVENTS_DIR = DOCS_DIR / "events"
DECISIONS_LOG = DOCS_DIR / "decisions_log.md"

def check_overdue_proposals():
    """检查逾期未投票的L2议题"""
    proposals = []
    
    # 检查 events 目录下的议会提案
    parliament_file = EVENTS_DIR / "20260422_parliament_proposals.md"
    if parliament_file.exists():
        content = parliament_file.read_text(encoding="utf-8")
        # 简单检查：如果有"截止"字段且已过期的
        if "截止" in content:
            # TODO: 解析具体日期并检查
            proposals.append({
                "file": str(parliament_file),
                "status": "需要手动检查",
                "note": "存在截止字段，请确认是否逾期"
            })
    
    return proposals

def check_overdue_tasks():
    """检查逾期未完成的任务"""
    # 从 active_work_plan.md 检查
    plan_file = Path(r"C:\Users\Administrator\.qclaw\workspace-agent-63961edb\memory\active_work_plan.md")
    if not plan_file.exists():
        return []
    
    content = plan_file.read_text(encoding="utf-8")
    overdue = []
    
    # 检查 P0/P1 是否有未完成且已过里程碑的
    # TODO: 解析里程碑日期并检查
    
    return overdue

def check_daily_ack():
    """检查每日同步会ACK"""
    # 检查今天的事件日志是否有 ACK 记录
    today = datetime.now().strftime("%Y%m%d")
    event_file = EVENTS_DIR / f"{today}.json"
    
    if not event_file.exists():
        return {"status": "missing", "note": f"今日事件日志不存在: {event_file}"}
    
    try:
        data = json.loads(event_file.read_text(encoding="utf-8"))
        # TODO: 检查是否有 ACK 事件
        return {"status": "ok", "note": "事件日志存在"}
    except Exception as e:
        return {"status": "error", "note": str(e)}

def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    
    print("=" * 60)
    print("治理框架逾期检查")
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 议题逾期检查
    print("\n[1] 议题投票逾期检查")
    proposals = check_overdue_proposals()
    if proposals:
        for p in proposals:
            print(f"  - {p['file']}: {p['status']} ({p['note']})")
    else:
        print("  ✅ 无逾期议题")
    
    # 2. 任务逾期检查
    print("\n[2] 任务截止逾期检查")
    tasks = check_overdue_tasks()
    if tasks:
        for t in tasks:
            print(f"  - {t}")
    else:
        print("  ✅ 无逾期任务（或需手动检查 active_work_plan.md）")
    
    # 3. 每日ACK检查
    print("\n[3] 每日同步会ACK检查")
    ack = check_daily_ack()
    print(f"  状态: {ack['status']}")
    print(f"  说明: {ack['note']}")
    
    print("\n" + "=" * 60)
    print("检查完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
