# run.py
"""
期货智能交易系统 V6.0 启动脚本（最终稳定版）
集成：数据源降级（CTP/缓存）、审计日志独立存储、多因子策略、风控插件
"""

import sys
import os
import json
import shutil
import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

# ==================== 环境与路径设置 ====================
# Qt 无头模式：服务器无图形界面时使用 offscreen 渲染
if not os.environ.get('DISPLAY') and not os.environ.get('QT_QPA_PLATFORM'):
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    print("[环境] 已设置 QT_QPA_PLATFORM=offscreen（无头模式）")

project_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_dir)
print(f"当前工作目录已切换到: {os.getcwd()}")

user_path = os.path.expanduser("~")
vntrader_path = os.path.join(user_path, ".vntrader")
os.environ["VNTRADER_DIR"] = vntrader_path
os.makedirs(vntrader_path, exist_ok=True)

# 删除嵌套目录
nested_path = os.path.join(vntrader_path, ".vntrader")
if os.path.exists(nested_path):
    shutil.rmtree(nested_path)
    print(f"[修复] 已删除嵌套目录: {nested_path}")

# 添加自定义模块搜索路径
custom_modules = [
    os.path.join(project_dir, "adapters"),
    os.path.join(project_dir, "services"),
    os.path.join(project_dir, "strategies"),  # 项目内策略目录
    os.path.join(user_path, "strategies"),  # 用户策略目录（兼容旧路径）
    project_dir,  # 项目根目录（用于导入 api, services 等）
]
for path in custom_modules:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)
        print(f"[路径] 已添加模块搜索路径: {path}")

# ==================== 导入 VNPY 模块 ====================
from vnpy.event import EventEngine, Event
from vnpy.trader.engine import MainEngine
from vnpy.trader.setting import SETTINGS
from vnpy.trader.utility import load_json, save_json, get_folder_path
from vnpy.trader.constant import Status
from vnpy.trader.object import OrderData, TradeData
# from vnpy_riskmanager import RiskManagerApp  # P0-fix: 未安装，已注释（自写 FastAPI bridge 替代）
from vnpy_ctp import CtpGateway
from vnpy_ctastrategy import CtaStrategyApp
# from vnpy_webtrader import WebTraderApp  # P0-fix: 未安装，已注释（自写 FastAPI bridge 替代）
from vnpy_datamanager import DataManagerApp
from vnpy_ctabacktester import CtaBacktesterApp
from services.macro_risk_app import MacroRiskApp

# ==================== 配置文件初始化 ====================
setting_file = os.path.join(vntrader_path, "vt_setting.json")
config = {
    "datafeed.name": "xt",
    "datafeed.username": "token",
    "datafeed.password": os.getenv("TUSHARE_TOKEN", "PLEASE_SET_ENV"),
    "log.active": True,
    "log.level": 10,
    "log.console": True,
    "log.file": True
}
with open(setting_file, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=4, ensure_ascii=False)
SETTINGS.update(config)
print(f"配置文件已更新: {setting_file}")

# ==================== 自定义事件类型 ====================
EVENT_DATA_SOURCE_ALERT = "eDataSourceAlert"

# ==================== 数据适配器链（精简版，仅 CTP / 缓存） ====================
class DataAdapterChain:
    """数据源降级管理：CTP 优先，断开后切换至本地缓存"""

    def __init__(self, event_engine: EventEngine, main_engine: MainEngine):
        self.event_engine = event_engine
        self.main_engine = main_engine
        self.config_path = os.path.join(vntrader_path, "data_adapter_chain.json")
        self.priority = self.load_priority()
        self.current_source: Optional[str] = None
        self.last_alert_level = None

        self.event_engine.register("eGateway", self.on_gateway_event)
        self._check_and_switch()

    def load_priority(self) -> List[str]:
        default = ["ctp", "cache"]
        try:
            if os.path.exists(self.config_path):
                cfg = load_json(self.config_path)
                return cfg.get("priority", default)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return default

    def save_priority(self):
        save_json(self.config_path, {"priority": self.priority})

    def _publish_alert(self, level: str, message: str):
        event = Event(
            type=EVENT_DATA_SOURCE_ALERT,
            data={"level": level, "message": message, "timestamp": datetime.now().isoformat()}
        )
        self.event_engine.put(event)
        self.last_alert_level = level

    def on_gateway_event(self, event: Event):
        data = event.data
        if data.get("gateway_name") != "CTP":
            return
        if data.get("status") == "connected":
            self.mark_source_healthy("ctp")
        elif data.get("status") == "disconnected":
            self.mark_source_unhealthy("ctp")

    def _check_health(self, source_name: str) -> bool:
        if source_name == "ctp":
            gw = self.main_engine.get_gateway("CTP")
            return gw is not None and gw.connected
        elif source_name == "cache":
            return True
        return False

    def _check_and_switch(self):
        if self.current_source and self._check_health(self.current_source):
            return
        for src in self.priority:
            if self._check_health(src):
                new_source = src
                break
        else:
            self._publish_alert("ERROR", "所有数据源均不可用")
            self.current_source = None
            return

        old = self.current_source
        self.current_source = new_source
        if old and old != new_source:
            self._publish_alert("WARNING", f"数据源降级：{old} -> {new_source}")
        else:
            self._publish_alert("INFO", f"当前数据源：{new_source}")

    def mark_source_unhealthy(self, source_name: str):
        self._check_and_switch()

    def mark_source_healthy(self, source_name: str):
        self._check_and_switch()

    def get_current_source(self) -> str:
        self._check_and_switch()
        return self.current_source or "unknown"

# ==================== 审计日志服务 ====================
class AuditService:
    """审计日志独立存储，分表保留 90 天 / 7 天"""

    def __init__(self, event_engine: EventEngine):
        self.event_engine = event_engine
        db_dir = Path(vntrader_path)
        db_dir.mkdir(exist_ok=True)
        self.db_path = str(db_dir / "audit.db")
        self._init_db()
        self._register_events()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operator TEXT,
                    operation_type TEXT,
                    target_type TEXT,
                    target_id TEXT,
                    old_value TEXT,
                    new_value TEXT,
                    extra_data TEXT,
                    created_at TEXT DEFAULT (datetime('now','localtime'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS event_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    event_data TEXT,
                    created_at TEXT DEFAULT (datetime('now','localtime'))
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_event_created ON event_queue(created_at)")

    def _register_events(self):
        self.event_engine.register("eStrategy", self.on_strategy_event)
        self.event_engine.register("eOrder", self.on_order_event)
        self.event_engine.register("eTrade", self.on_trade_event)
        self.event_engine.register("eRiskRule", self.on_risk_rule_event)

    def on_strategy_event(self, event: Event):
        data = event.data
        op_type = data.get("type")
        if op_type in ("start", "stop"):
            self.log_audit(
                operator="system",
                operation_type=f"strategy_{op_type}",
                target_type="strategy",
                target_id=data.get("strategy_name"),
                extra_data={"vt_symbol": data.get("vt_symbol")}
            )

    def on_order_event(self, event: Event):
        order: OrderData = event.data
        if order.status == Status.SUBMITTING:
            self.log_audit(
                operator="strategy",
                operation_type="send_order",
                target_type="order",
                target_id=order.vt_orderid,
                new_value=f"{order.direction.value} {order.offset.value} {order.volume}@{order.price}",
                extra_data={"symbol": order.symbol}
            )

    def on_trade_event(self, event: Event):
        trade: TradeData = event.data
        self.log_audit(
            operator="strategy",
            operation_type="trade",
            target_type="trade",
            target_id=trade.vt_tradeid,
            new_value=f"{trade.direction.value} {trade.offset.value} {trade.volume}@{trade.price}",
            extra_data={"symbol": trade.symbol}
        )

    def on_risk_rule_event(self, event: Event):
        data = event.data
        self.log_audit(
            operator="system",
            operation_type="risk_rule",
            target_type="risk_rule",
            target_id=data.get("rule_name"),
            extra_data={"action": data.get("action")}
        )

    def log_audit(self, operator: str, operation_type: str, target_type: str = None,
                  target_id: str = None, old_value: Any = None, new_value: Any = None,
                  extra_data: Dict = None):
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO audit_log 
                    (operator, operation_type, target_type, target_id, old_value, new_value, extra_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    operator, operation_type, target_type, target_id,
                    json.dumps(old_value, ensure_ascii=False) if old_value is not None else None,
                    json.dumps(new_value, ensure_ascii=False) if new_value is not None else None,
                    json.dumps(extra_data, ensure_ascii=False) if extra_data else None
                ))
        except sqlite3.OperationalError as e:
            print(f"审计日志写入失败（数据库锁）: {e}")

    def cleanup(self, audit_days=90, event_days=7):
        audit_cut = (datetime.now() - timedelta(days=audit_days)).strftime("%Y-%m-%d %H:%M:%S")
        event_cut = (datetime.now() - timedelta(days=event_days)).strftime("%Y-%m-%d %H:%M:%S")
        with self._get_conn() as conn:
            conn.execute("DELETE FROM audit_log WHERE created_at < ?", (audit_cut,))
            conn.execute("DELETE FROM event_queue WHERE created_at < ?", (event_cut,))
            conn.execute("VACUUM")

# ==================== 命令行参数解析 ====================
def parse_args():
    parser = argparse.ArgumentParser(description="Futures V6 Trading System")
    parser.add_argument("--api-only", action="store_true",
                        help="仅启动 API 服务（无 CTP，纯数据/信号服务）")
    parser.add_argument("--headless", action="store_true",
                        help="无头模式（策略 + CTP，无 API）")
    parser.add_argument("--symbol", type=str, default=None,
                        help="指定交易品种（默认全部）")
    parser.add_argument("--no-macro", action="store_true",
                        help="不加载宏观信号")
    return parser.parse_args()


def init_engine(args):
    """初始化交易引擎（CTP + 策略 + 数据链路）

    提取自 main() 默认模式的初始化代码，供默认模式和 --headless 共用。
    """
    global event_engine, main_engine, data_chain, audit_svc, vnpy_bridge, signal_bridge

    # ==================== 主引擎初始化 ====================
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)

    # 数据适配器链
    data_chain = DataAdapterChain(event_engine, main_engine)
    print(f"数据适配器链已初始化，当前数据源：{data_chain.get_current_source()}")

    # 审计服务
    audit_svc = AuditService(event_engine)
    main_engine.audit_service = audit_svc
    print("审计服务已启动并挂载到主引擎")

    # VNpyBridge（FastAPI 桥接器）
    from services.vnpy_bridge import VNpyBridge, set_vnpy_bridge as _set_bridge
    vnpy_bridge = VNpyBridge()
    main_engine.vnpy_bridge = vnpy_bridge
    _set_bridge(vnpy_bridge)
    print("VNpyBridge 已初始化")

    # SignalBridge（宏观信号事件桥接器）
    from services.signal_bridge import SignalBridge
    signal_bridge = SignalBridge(csv_dir=os.path.join(project_dir, "macro_engine", "output"), event_engine=event_engine)
    signal_bridge.start()
    main_engine.signal_bridge = signal_bridge
    print("SignalBridge 已启动")

    # 添加网关和应用
    main_engine.add_gateway(CtpGateway)

    # ==================== CTP 连接配置（config/ctp.json + 环境变量 fallback） ====================
    ctp_config = {}
    ctp_config_path = os.path.join(project_dir, "config", "ctp.json")
    if os.path.exists(ctp_config_path):
        with open(ctp_config_path, "r", encoding="utf-8") as f:
            ctp_config = json.load(f)
        print(f"[CTP] 已加载配置: {ctp_config_path}")
    else:
        print(f"[CTP] 配置文件不存在，使用环境变量: {ctp_config_path}")

    def _ctp_val(key, env_key, default):
        """config/ctp.json 优先，环境变量其次，默认值兜底"""
        val = ctp_config.get(key, "")
        if val and not val.startswith("$"):
            return val
        return os.environ.get(env_key, default)

    CTP_USER_ID     = _ctp_val("user_id",    "VNPY_CTP_USER_ID",    "PLEASE_SET_ENV")
    CTP_PASSWORD    = _ctp_val("password",   "VNPY_CTP_PASSWORD",   "PLEASE_SET_ENV")
    CTP_BROKER_ID   = _ctp_val("broker_id",  "VNPY_CTP_BROKER_ID",  "9999")
    CTP_TD_SERVER   = _ctp_val("td_server",  "VNPY_CTP_TD_SERVER",  "182.254.243.31:30001")
    CTP_MD_SERVER   = _ctp_val("md_server",  "VNPY_CTP_MD_SERVER",  "182.254.243.31:30011")
    CTP_APP_ID      = _ctp_val("app_id",     "VNPY_CTP_APP_ID",     "simnow_client_test")
    CTP_AUTH_CODE    = _ctp_val("auth_code",  "VNPY_CTP_AUTH_CODE",  "0000000000000000")

    try:
        gw = main_engine.get_gateway("CTP")
        gw.connect({
            "用户名": CTP_USER_ID,
            "密码": CTP_PASSWORD,
            "经纪商代码": CTP_BROKER_ID,
            "交易服务器": CTP_TD_SERVER,
            "行情服务器": CTP_MD_SERVER,
            "产品名称": CTP_APP_ID,
            "授权编码": CTP_AUTH_CODE,
            "环境": "仿真",
        })
        print(f"[CTP] SimNow 连接: user={CTP_USER_ID}, broker={CTP_BROKER_ID}, "
              f"td={CTP_TD_SERVER}, md={CTP_MD_SERVER}")
    except Exception as e:
        print(f"[CTP] 连接失败: {e}")

    main_engine.add_app(CtaStrategyApp)
    main_engine.add_app(DataManagerApp)
    main_engine.add_app(CtaBacktesterApp)
    main_engine.add_app(MacroRiskApp)
    print("[App] MacroRiskApp 已加载")

    main_engine.init_engines()

    # ==================== 自动加载策略（StrategyRegistry） ====================
    try:
        from core.strategy_registry import init_registry
        strategy_dir = Path(project_dir) / "strategies"
        bindings_path = Path(project_dir) / "config" / "strategy_bindings.yaml"
        registry = init_registry(
            strategy_dir=strategy_dir,
            bindings_path=bindings_path,
            project_dir=Path(project_dir),
        )
        cta_engine = main_engine.get_engine("CtaStrategy")
        if cta_engine:
            # 通过注册中心加载策略类
            for class_name, info in registry.get_all_strategies().items():
                try:
                    cta_engine.add_strategy_class(info.cls)
                except Exception:
                    pass
            class_names = cta_engine.get_all_strategy_class_names()
            print(f"[策略] 已加载 {len(class_names)} 个策略类: {class_names}")
            # 校验绑定
            binding_errors = registry.validate_bindings()
            for err in binding_errors:
                print(f"[策略] WARNING: {err}")
            enabled = registry.get_enabled_bindings()
            print(f"[策略] 品种绑定: {len(enabled)} 个启用 / {len(registry.get_bindings())} 个总计")
        else:
            print("[策略] CtaEngine 未找到，跳过策略加载")
    except Exception as e:
        print(f"[策略] 自动加载策略失败: {e}")

    # ==================== 启动前注册桥接器到 API ====================
    try:
        import api.macro_api_server as api_server
        api_server.set_vnpy_bridge(vnpy_bridge)
        print("VNpyBridge 已注册到 FastAPI")
    except Exception as e:
        print(f"VNpyBridge 注册到 FastAPI 失败: {e}")

    # ==================== 对账快照启动恢复 ====================
    try:
        from services.reconciliation_engine import get_reconciliation_engine
        recon = get_reconciliation_engine()
        mode = recon.check_recovery_mode()
        if mode == "RECOVERY_NEEDED":
            print("[对账] 检测到重启恢复模式，从最近快照恢复持仓...")
            from datetime import date
            yesterday = (date.today()).isoformat()
            recovered = recon.recover_positions_from_snapshot(yesterday, bridge=vnpy_bridge)
            print(f"[对账] 已从快照恢复 {recovered} 条持仓")
        else:
            print("[对账] 快照状态正常，无需恢复")
    except Exception as e:
        print(f"[对账] 启动恢复检查失败（不影响交易）: {e}")

    return main_engine


def main():
    args = parse_args()

    # 模式互斥检查
    modes = sum([args.api_only, args.headless])
    if modes > 1:
        print("ERROR: --api-only 和 --headless 不能同时使用")
        sys.exit(1)

    if args.api_only:
        # === API-only 模式：仅启动 FastAPI 服务（无 CTP） ===
        print("[INFO] API-only 模式 — 仅启动 FastAPI 服务（无 CTP）")
        try:
            import uvicorn
        except ImportError:
            print("[ERROR] uvicorn 未安装，请执行: pip install uvicorn")
            sys.exit(1)
        from api.macro_api_server import app
        # API-only 模式：对账引擎已由 FastAPI startup 事件初始化，此处仅记录恢复状态
        try:
            from services.reconciliation_engine import get_reconciliation_engine
            recon = get_reconciliation_engine()
            mode = recon.check_recovery_mode()
            if mode == "RECOVERY_NEEDED":
                print("[对账] API模式: 检测到重启恢复需求，详见日志")
            else:
                print("[对账] API模式: 快照状态正常")
        except Exception as e:
            print(f"[对账] API模式恢复检查失败: {e}")
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

    elif args.headless:
        # === Headless 模式：引擎 + CTP，无 API ===
        print("[INFO] Headless 模式 — 策略 + CTP，无 API")
        engine = init_engine(args)
        print("[INFO] Headless 模式运行中，按 Ctrl+C 退出")
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("[退出] 收到中断信号，正在关闭...")
            try:
                from services.reconciliation_engine import get_reconciliation_engine
                recon = get_reconciliation_engine()
                cnt = recon.trigger_daily_snapshots(
                    bridge=engine.vnpy_bridge if hasattr(engine, 'vnpy_bridge') else None,
                    snapshot_type="EOD")
                print(f"[对账] 日终快照已写入 {cnt} 条")
            except Exception as e:
                print(f"[对账] 日终快照失败: {e}")
            engine.close()
            event_engine.stop()

    else:
        # === 默认模式：引擎 + CTP + GUI/无头循环 ===
        engine = init_engine(args)

        # 强制无头模式：服务器无图形界面
        headless = True
        print("[模式] 无头模式启动（不加载GUI）")

        if __name__ == "__main__" and not headless:
            print("=" * 50)
            print(f"VNPY 配置目录: {get_folder_path('.vntrader')}")
            print("=" * 50)

            from vnpy.trader.ui import create_qapp, MainWindow
            qapp = create_qapp()
            main_window = MainWindow(engine, event_engine)
            main_window.show()
            qapp.exec()
        else:
            print("[模式] 引擎已启动，无头模式运行中...")
            import time
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("[退出] 收到中断信号，正在关闭...")
                try:
                    from services.reconciliation_engine import get_reconciliation_engine
                    recon = get_reconciliation_engine()
                    cnt = recon.trigger_daily_snapshots(
                        bridge=engine.vnpy_bridge if hasattr(engine, 'vnpy_bridge') else None,
                        snapshot_type="EOD")
                    print(f"[对账] 日终快照已写入 {cnt} 条")
                except Exception as e:
                    print(f"[对账] 日终快照失败: {e}")
                engine.close()
                event_engine.stop()


if __name__ == "__main__":
    main()