#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
因子采集主程序（NEW-1）
==========================================
两种运行模式：
  --mode daily   : 每日15:30定时运行，采集当天数据
  --mode startup : 开机触发，检测缺口并补齐

采集品种：JM RU RB ZN NI (spread + hold_volume)
数据写入：D:\futures_v6\macro_engine\data\pit_data.db

设计要点：
  - 每日模式：直接采集当天数据
  - 开机模式：查PIT最大日期，补齐缺失交易日
  - 跳过周末（周六日不补）
"""

import sys
import sqlite3
import logging
import argparse
from datetime import date, timedelta
from pathlib import Path

# 项目路径
PROJECT_ROOT = Path(r'D:\futures_v6\macro_engine')
SCRIPT_DIR = PROJECT_ROOT / 'scripts'
DB_PATH = PROJECT_ROOT / 'pit_data.db'  # 实际路径在项目根目录，非data/
LOG_DIR = PROJECT_ROOT / 'logs'
LOG_DIR.mkdir(exist_ok=True)

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(str(LOG_DIR / 'factor_collector.log'), encoding='utf-8', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 品种列表（collect_real_factors.py 支持的）
SPREAD_SYMBOLS = ["JM", "RU", "RB", "ZN", "NI"]


def get_last_pit_date() -> date:
    """查询PIT表最大obs_date"""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.execute(
            "SELECT MAX(obs_date) FROM pit_factor_observations"
        )
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            return date.fromisoformat(row[0])
    except Exception as e:
        logger.warning(f"查PIT最大日期失败: {e}")
    return None


def get_last_spread_date(symbol: str) -> date:
    """查询某品种spread表最大obs_date"""
    table = f"{symbol.lower()}_futures_spread"
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.execute(f"SELECT MAX(obs_date) FROM {table}")
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            return date.fromisoformat(row[0])
    except Exception as e:
        logger.warning(f"查{table}最大日期失败: {e}")
    return None


def get_missing_dates(since: date, until: date) -> list:
    """返回缺失的交易日列表（跳过周末）"""
    missing = []
    current = since + timedelta(days=1)
    while current <= until:
        if current.weekday() < 5:  # 0-4 = 周一到周五
            missing.append(current)
        current += timedelta(days=1)
    return missing


def run_daily_collect():
    """每日模式：采集今天数据"""
    logger.info("=" * 50)
    logger.info("【每日采集模式】开始")
    
    # 导入采集模块
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        from collect_real_factors import collect_spread, collect_hold_volume
    except ImportError as e:
        logger.error(f"导入collect_real_factors失败: {e}")
        return {"status": "FAIL", "error": str(e)}
    
    results = {}
    for sym in SPREAD_SYMBOLS:
        try:
            r1 = collect_spread(sym)
            r2 = collect_hold_volume(sym)
            if r1 and r2:
                results[sym] = "OK"
                logger.info(f"  {sym}: spread✓ hold✓")
            else:
                results[sym] = "PARTIAL"
                logger.warning(f"  {sym}: spread={r1} hold={r2}")
        except Exception as e:
            results[sym] = f"FAIL: {e}"
            logger.error(f"  {sym}: {e}")
    
    logger.info(f"【每日采集】完成: {results}")
    return results


def run_backfill_gaps(gap_dates: list):
    """缺口模式：逐日回填（注意：collect_real_factors使用当前合约代码，历史回填可能无效）"""
    logger.info("=" * 50)
    logger.info(f"【缺口补齐模式】缺失{len(gap_dates)}天")
    logger.info(f"缺失日期: {[str(d) for d in gap_dates]}")
    
    if not gap_dates:
        logger.info("无缺口，跳过")
        return {"status": "SKIP"}
    
    # 导入采集模块
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        from collect_real_factors import collect_spread, collect_hold_volume
    except ImportError as e:
        logger.error(f"导入collect_real_factors失败: {e}")
        return {"status": "FAIL", "error": str(e)}
    
    filled = []
    failed = []
    
    # 警告：合约代码问题
    logger.warning("注意：collect_real_factors.py使用固定合约代码(如JM2505)")
    logger.warning("历史回填可能因合约不匹配而无效，仅尝试采集当前合约数据")
    
    for day in gap_dates:
        logger.info(f"补采 {day} ...")
        day_ok = True
        for sym in SPREAD_SYMBOLS:
            try:
                r1 = collect_spread(sym)
                r2 = collect_hold_volume(sym)
                if not (r1 and r2):
                    day_ok = False
                    failed.append((day, sym, "partial"))
            except Exception as e:
                day_ok = False
                failed.append((day, sym, str(e)[:50]))
        
        if day_ok:
            filled.append(day)
    
    logger.info(f"【缺口补齐】完成: {len(filled)}天成功, {len(failed)}条失败")
    if failed:
        for f in failed[:10]:
            logger.error(f"  FAIL {f[0]} {f[1]}: {f[2]}")
        if len(failed) > 10:
            logger.error(f"  ... 还有{len(failed)-10}条失败")
    
    return {"filled": len(filled), "failed": len(failed)}


def check_and_report_gaps():
    """检查并报告各表缺口情况"""
    logger.info("=" * 50)
    logger.info("【缺口检查】")
    
    today = date.today()
    gaps = {}
    
    # 检查pit_factor_observations
    last_pit = get_last_pit_date()
    if last_pit:
        missing = get_missing_dates(last_pit, today)
        gaps['pit_factor_observations'] = {
            'last_date': str(last_pit),
            'missing_count': len(missing),
            'missing_dates': [str(d) for d in missing[:5]]  # 只显示前5个
        }
        logger.info(f"  pit_factor_observations: 最后日期={last_pit}, 缺失{len(missing)}天")
    else:
        gaps['pit_factor_observations'] = {'last_date': None, 'missing_count': 'N/A'}
        logger.warning("  pit_factor_observations: 表为空或查询失败")
    
    # 检查各品种spread表
    for sym in SPREAD_SYMBOLS:
        last = get_last_spread_date(sym)
        if last:
            missing = get_missing_dates(last, today)
            gaps[f'{sym}_spread'] = {
                'last_date': str(last),
                'missing_count': len(missing)
            }
            logger.info(f"  {sym}_spread: 最后日期={last}, 缺失{len(missing)}天")
        else:
            gaps[f'{sym}_spread'] = {'last_date': None, 'missing_count': 'N/A'}
            logger.warning(f"  {sym}_spread: 表为空或查询失败")
    
    return gaps


def main():
    parser = argparse.ArgumentParser(description='因子采集主程序')
    parser.add_argument('--mode', choices=['daily', 'startup', 'check'], default='daily',
                        help='daily=每日定时采集, startup=开机缺口检测+补齐, check=仅检查缺口')
    parser.add_argument('--symbols', default='JM,RU,RB,ZN,NI',
                        help='品种列表，逗号分隔')
    args = parser.parse_args()
    
    global SPREAD_SYMBOLS
    SPREAD_SYMBOLS = [s.strip().upper() for s in args.symbols.split(',')]
    
    logger.info(f"启动参数: mode={args.mode}, symbols={SPREAD_SYMBOLS}")
    
    if args.mode == 'daily':
        result = run_daily_collect()
    elif args.mode == 'startup':
        # 先检查缺口
        gaps = check_and_report_gaps()
        
        # 计算需要补齐的日期
        last_date = get_last_pit_date()
        today = date.today()
        
        if last_date is None:
            logger.info("PIT表为空，执行全量回填最近30天")
            gap_dates = get_missing_dates(today - timedelta(days=30), today)
        else:
            gap_dates = get_missing_dates(last_date, today)
        
        # 执行补齐
        result = run_backfill_gaps(gap_dates)
        
        # 补齐后再采集今天
        logger.info("补齐完成，执行今日采集...")
        result_daily = run_daily_collect()
        result['daily'] = result_daily
    elif args.mode == 'check':
        result = check_and_report_gaps()
    
    logger.info("执行完毕")
    return result


if __name__ == '__main__':
    main()
