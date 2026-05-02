# scripts/cleanup_audit.py
"""
审计日志清理脚本
用法：python scripts/cleanup_audit.py
建议：通过 Windows 任务计划程序，每天凌晨 2:00 执行一次
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# 审计数据库路径（与 run.py 中一致）
vntrader_path = Path.home() / ".vntrader"
db_path = vntrader_path / "audit.db"

if not db_path.exists():
    print(f"数据库文件不存在: {db_path}")
    exit(1)

def cleanup(audit_days=90, event_days=7):
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    audit_cut = (datetime.now() - timedelta(days=audit_days)).strftime("%Y-%m-%d %H:%M:%S")
    event_cut = (datetime.now() - timedelta(days=event_days)).strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("DELETE FROM audit_log WHERE created_at < ?", (audit_cut,))
    deleted_audit = cursor.rowcount
    
    cursor.execute("DELETE FROM event_queue WHERE created_at < ?", (event_cut,))
    deleted_event = cursor.rowcount
    
    conn.commit()
    cursor.execute("VACUUM")
    conn.close()
    
    print(f"清理完成：审计日志删除 {deleted_audit} 条，事件队列删除 {deleted_event} 条")

if __name__ == "__main__":
    cleanup()