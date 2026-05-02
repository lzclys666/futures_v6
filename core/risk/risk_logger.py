"""
Risk Event Logger Module
风控事件日志模块 - 记录所有风控拦截/警告事件

V6.1 特性：
- 结构化日志（JSON格式）
- 按日期分文件
- 支持查询和统计
- 与前端风控面板集成

Author: 程序员deep
Date: 2026-04-26
"""

import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3


class EventType(Enum):
    """事件类型"""
    BLOCK = "block"          # 拦截
    WARN = "warn"            # 警告
    PASS = "pass"            # 通过
    FUSE_TRIGGER = "fuse"    # 熔断触发
    FUSE_RECOVER = "recover" # 熔断恢复


class EventLevel(Enum):
    """事件级别"""
    CRITICAL = "critical"    # 严重（如保证金不足）
    HIGH = "high"            # 高（如宏观熔断）
    MEDIUM = "medium"        # 中（如波动率异常）
    LOW = "low"              # 低（如警告）
    INFO = "info"            # 信息


@dataclass
class RiskEvent:
    """风控事件"""
    timestamp: str
    event_type: str
    level: str
    rule_id: str
    symbol: str
    direction: str
    message: str
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'timestamp': self.timestamp,
            'event_type': self.event_type,
            'level': self.level,
            'rule_id': self.rule_id,
            'symbol': self.symbol,
            'direction': self.direction,
            'message': self.message,
            'details': self.details,
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class RiskEventLogger:
    """
    风控事件日志记录器
    
    支持两种存储方式：
    1. JSON文件（按日期分文件）
    2. SQLite数据库（支持查询统计）
    """
    
    def __init__(self, log_dir: str = "logs/risk", db_path: Optional[str] = None):
        """
        初始化日志记录器
        
        Args:
            log_dir: JSON日志文件目录
            db_path: SQLite数据库路径（可选）
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path or str(self.log_dir / "risk_events.db")
        self._init_db()
        
        # 当日日志文件
        self.current_date = date.today()
        self.current_file = self._get_log_file()
    
    def _init_db(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS risk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                level TEXT NOT NULL,
                rule_id TEXT NOT NULL,
                symbol TEXT,
                direction TEXT,
                message TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON risk_events(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_rule_id ON risk_events(rule_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol ON risk_events(symbol)
        ''')
        
        conn.commit()
        conn.close()
    
    def _get_log_file(self) -> Path:
        """获取当日日志文件路径"""
        return self.log_dir / f"risk_events_{self.current_date.strftime('%Y%m%d')}.jsonl"
    
    def _check_date(self):
        """检查日期是否变化，如果是则切换日志文件"""
        today = date.today()
        if today != self.current_date:
            self.current_date = today
            self.current_file = self._get_log_file()
    
    def log(self, event: RiskEvent):
        """
        记录事件
        
        Args:
            event: 风控事件
        """
        self._check_date()
        
        # 写入JSON文件
        with open(self.current_file, 'a', encoding='utf-8') as f:
            f.write(event.to_json() + '\n')
        
        # 写入数据库
        self._save_to_db(event)
    
    def _save_to_db(self, event: RiskEvent):
        """保存到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO risk_events 
            (timestamp, event_type, level, rule_id, symbol, direction, message, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.timestamp,
            event.event_type,
            event.level,
            event.rule_id,
            event.symbol,
            event.direction,
            event.message,
            json.dumps(event.details, ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()
    
    def log_block(self, rule_id: str, symbol: str, direction: str, 
                  message: str, details: Dict[str, Any] = None,
                  level: EventLevel = EventLevel.HIGH):
        """记录拦截事件"""
        event = RiskEvent(
            timestamp=datetime.now().isoformat(),
            event_type=EventType.BLOCK.value,
            level=level.value,
            rule_id=rule_id,
            symbol=symbol,
            direction=direction,
            message=message,
            details=details or {}
        )
        self.log(event)
    
    def log_warn(self, rule_id: str, symbol: str, direction: str,
                 message: str, details: Dict[str, Any] = None):
        """记录警告事件"""
        event = RiskEvent(
            timestamp=datetime.now().isoformat(),
            event_type=EventType.WARN.value,
            level=EventLevel.LOW.value,
            rule_id=rule_id,
            symbol=symbol,
            direction=direction,
            message=message,
            details=details or {}
        )
        self.log(event)
    
    def log_fuse(self, rule_id: str, symbol: str, direction: str,
                 message: str, details: Dict[str, Any] = None):
        """记录熔断事件"""
        event = RiskEvent(
            timestamp=datetime.now().isoformat(),
            event_type=EventType.FUSE_TRIGGER.value,
            level=EventLevel.CRITICAL.value,
            rule_id=rule_id,
            symbol=symbol,
            direction=direction,
            message=message,
            details=details or {}
        )
        self.log(event)
    
    def query(self, start_date: Optional[str] = None,
              end_date: Optional[str] = None,
              rule_id: Optional[str] = None,
              symbol: Optional[str] = None,
              event_type: Optional[str] = None,
              limit: int = 100) -> List[Dict]:
        """
        查询事件日志
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            rule_id: 规则ID筛选
            symbol: 品种筛选
            event_type: 事件类型筛选
            limit: 返回条数限制
            
        Returns:
            List[Dict]: 事件列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM risk_events WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND date(timestamp) >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date(timestamp) <= ?"
            params.append(end_date)
        if rule_id:
            query += " AND rule_id = ?"
            params.append(rule_id)
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            result = dict(row)
            result['details'] = json.loads(result['details'] or '{}')
            results.append(result)
        
        conn.close()
        return results
    
    def get_statistics(self, days: int = 7) -> Dict:
        """
        获取统计信息
        
        Args:
            days: 统计天数
            
        Returns:
            Dict: 统计结果
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总拦截次数
        cursor.execute('''
            SELECT COUNT(*) FROM risk_events 
            WHERE event_type = 'block' 
            AND date(timestamp) >= date('now', '-{} days')
        '''.format(days))
        total_blocks = cursor.fetchone()[0]
        
        # 按规则统计
        cursor.execute('''
            SELECT rule_id, COUNT(*) as count 
            FROM risk_events 
            WHERE date(timestamp) >= date('now', '-{} days')
            GROUP BY rule_id 
            ORDER BY count DESC
        '''.format(days))
        rule_stats = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 按品种统计
        cursor.execute('''
            SELECT symbol, COUNT(*) as count 
            FROM risk_events 
            WHERE date(timestamp) >= date('now', '-{} days')
            AND symbol IS NOT NULL
            GROUP BY symbol 
            ORDER BY count DESC
        '''.format(days))
        symbol_stats = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 按类型统计
        cursor.execute('''
            SELECT event_type, COUNT(*) as count 
            FROM risk_events 
            WHERE date(timestamp) >= date('now', '-{} days')
            GROUP BY event_type
        '''.format(days))
        type_stats = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            'period_days': days,
            'total_blocks': total_blocks,
            'rule_statistics': rule_stats,
            'symbol_statistics': symbol_stats,
            'type_statistics': type_stats,
        }
    
    def get_fuse_status(self) -> Dict:
        """
        获取当前熔断状态
        
        Returns:
            Dict: 熔断状态信息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取最近的熔断触发和恢复事件
        cursor.execute('''
            SELECT rule_id, symbol, direction, event_type, timestamp
            FROM risk_events 
            WHERE event_type IN ('fuse', 'recover')
            ORDER BY timestamp DESC
            LIMIT 20
        ''')
        
        fuse_events = []
        active_fuses = {}
        
        for row in cursor.fetchall():
            rule_id, symbol, direction, event_type, timestamp = row
            key = f"{rule_id}_{symbol}_{direction}"
            
            if event_type == 'fuse':
                if key not in active_fuses:
                    active_fuses[key] = {
                        'rule_id': rule_id,
                        'symbol': symbol,
                        'direction': direction,
                        'triggered_at': timestamp,
                    }
            elif event_type == 'recover':
                if key in active_fuses:
                    del active_fuses[key]
            
            fuse_events.append({
                'rule_id': rule_id,
                'symbol': symbol,
                'direction': direction,
                'event_type': event_type,
                'timestamp': timestamp,
            })
        
        conn.close()
        
        return {
            'active_fuses': list(active_fuses.values()),
            'recent_events': fuse_events,
            'fuse_count': len(active_fuses),
        }


# ==================== 测试 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("Risk Event Logger Test")
    print("=" * 60)
    
    # 创建日志记录器
    logger = RiskEventLogger(
        log_dir="logs/risk_test",
        db_path="logs/risk_test/events.db"
    )
    
    # 记录测试事件
    print("\n[1] Recording test events...")
    
    logger.log_block(
        rule_id="R10",
        symbol="RU2505",
        direction="LONG",
        message="宏观熔断：评分20 <= 阈值30，禁止做多",
        details={"macro_score": 20, "threshold": 30},
        level=EventLevel.HIGH
    )
    
    logger.log_block(
        rule_id="R3",
        symbol="RU2505",
        direction="LONG",
        message="价格16500 >= 涨停价16000",
        details={"price": 16500, "limit_up": 16000},
        level=EventLevel.MEDIUM
    )
    
    logger.log_warn(
        rule_id="R5",
        symbol="CU2506",
        direction="SHORT",
        message="波动率异常：ATR/价格=5.2%",
        details={"atr_ratio": 0.052, "threshold": 0.03}
    )
    
    logger.log_fuse(
        rule_id="R10",
        symbol="RU2505",
        direction="LONG",
        message="宏观熔断触发：评分15",
        details={"macro_score": 15, "threshold": 30}
    )
    
    print("[OK] Events recorded")
    
    # 查询测试
    print("\n[2] Querying events...")
    events = logger.query(limit=10)
    for event in events:
        print(f"  [{event['event_type']}] {event['rule_id']}: {event['message']}")
    
    # 统计测试
    print("\n[3] Statistics (last 7 days)...")
    stats = logger.get_statistics(days=7)
    print(f"  Total blocks: {stats['total_blocks']}")
    print(f"  Rule stats: {stats['rule_statistics']}")
    print(f"  Type stats: {stats['type_statistics']}")
    
    # 熔断状态
    print("\n[4] Fuse status...")
    fuse_status = logger.get_fuse_status()
    print(f"  Active fuses: {fuse_status['fuse_count']}")
    for fuse in fuse_status['active_fuses']:
        print(f"    - {fuse['rule_id']} {fuse['symbol']} {fuse['direction']} @ {fuse['triggered_at']}")
    
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)
