#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
log_rotation.py
ETL 日志轮转脚本

功能:
1. 扫描指定日志目录，检查 .log 文件大小
2. 超过阈值（默认 10MB）的文件自动归档为 .log.YYYYMMDD
3. 保留最近 N 天（默认 7 天）的归档，删除更早的

用法:
  python log_rotation.py [--log-dir DIR] [--max-size-mb MB] [--keep-days DAYS] [--dry-run]

退出码:
  0 = 正常（有或无操作）
  1 = 错误
"""

import os
import sys
import glob
import argparse
from datetime import datetime, timedelta
from pathlib import Path


def rotate_logs(log_dir: str, max_size_mb: int = 10, keep_days: int = 7, dry_run: bool = False) -> dict:
    """
    执行日志轮转
    
    Returns:
        dict: {"rotated": [...], "deleted": [...], "errors": [...]}
    """
    result = {"rotated": [], "deleted": [], "errors": []}
    log_path = Path(log_dir)
    
    if not log_path.exists():
        result["errors"].append(f"日志目录不存在: {log_dir}")
        return result
    
    max_size_bytes = max_size_mb * 1024 * 1024
    today = datetime.now().strftime("%Y%m%d")
    
    # Step 1: 轮转超过大小阈值的 .log 文件
    for log_file in log_path.glob("*.log"):
        try:
            file_size = log_file.stat().st_size
            if file_size > max_size_bytes:
                archive_name = f"{log_file.name}.{today}"
                archive_path = log_path / archive_name
                
                # 如果今天的归档已存在，跳过（避免重复轮转）
                if archive_path.exists():
                    continue
                
                size_mb = round(file_size / 1024 / 1024, 2)
                if dry_run:
                    result["rotated"].append(f"[DRY-RUN] {log_file.name} ({size_mb}MB) -> {archive_name}")
                else:
                    # 重命名当前日志为归档
                    log_file.rename(archive_path)
                    # 创建新的空日志文件
                    log_file.touch()
                    result["rotated"].append(f"{log_file.name} ({size_mb}MB) -> {archive_name}")
        except Exception as e:
            result["errors"].append(f"轮转 {log_file.name} 失败: {e}")
    
    # Step 2: 清理超过保留天数的归档文件
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    cutoff_str = cutoff_date.strftime("%Y%m%d")
    
    # 匹配 *.log.YYYYMMDD 格式的归档文件
    for archive_file in log_path.glob("*.log.*"):
        try:
            suffix = archive_file.suffix  # .YYYYMMDD
            if len(suffix) == 9 and suffix[1:].isdigit():
                file_date = suffix[1:]  # YYYYMMDD
                if file_date < cutoff_str:
                    if dry_run:
                        result["deleted"].append(f"[DRY-RUN] {archive_file.name}")
                    else:
                        archive_file.unlink()
                        result["deleted"].append(archive_file.name)
        except Exception as e:
            result["errors"].append(f"删除 {archive_file.name} 失败: {e}")
    
    return result


def main():
    parser = argparse.ArgumentParser(description="ETL 日志轮转脚本")
    parser.add_argument("--log-dir", default=r"D:\futures_v6\macro_engine\logs",
                        help="日志目录路径 (默认: D:\\futures_v6\\macro_engine\\logs)")
    parser.add_argument("--max-size-mb", type=int, default=10,
                        help="日志文件大小阈值，单位 MB (默认: 10)")
    parser.add_argument("--keep-days", type=int, default=7,
                        help="保留最近 N 天的归档 (默认: 7)")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅预览，不实际执行")
    args = parser.parse_args()
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 日志轮转开始")
    print(f"  目录: {args.log_dir}")
    print(f"  阈值: {args.max_size_mb}MB")
    print(f"  保留: {args.keep_days}天")
    print()
    
    result = rotate_logs(args.log_dir, args.max_size_mb, args.keep_days, args.dry_run)
    
    if result["rotated"]:
        print("[轮转]")
        for item in result["rotated"]:
            print(f"  {item}")
    
    if result["deleted"]:
        print("[清理]")
        for item in result["deleted"]:
            print(f"  {item}")
    
    if result["errors"]:
        print("[错误]")
        for item in result["errors"]:
            print(f"  {item}")
    
    if not result["rotated"] and not result["deleted"] and not result["errors"]:
        print("  无需操作")
    
    print()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 日志轮转完成")
    
    sys.exit(1 if result["errors"] else 0)


if __name__ == "__main__":
    main()
