# -*- coding: utf-8 -*-
"""
MacroRiskApp UI 模块

最小的 UI 骨架, 兼容无头模式和 GUI 模式
"""

from vnpy.trader.ui import QtWidgets, QtCore
from vnpy.trader.ui.widget import BaseMonitor, BaseCell


class RiskManagerWidget(QtWidgets.QWidget):
    """风控管理界面 (最小骨架)"""

    signal_rule_changed = QtCore.Signal(str, bool)

    def __init__(self, main_engine, event_engine):
        super().__init__()
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.risk_engine = main_engine.get_engine("RiskEngine")

        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("宏观风控系统")

        layout = QtWidgets.QVBoxLayout()

        # 标题
        title = QtWidgets.QLabel("宏观风控核心规则")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        # 规则状态表格
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["规则", "名称", "状态", "违规次数"])
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        # 控制按钮
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_enable_all = QtWidgets.QPushButton("全部启用")
        self.btn_disable_all = QtWidgets.QPushButton("全部禁用")
        self.btn_refresh = QtWidgets.QPushButton("刷新")
        btn_layout.addWidget(self.btn_enable_all)
        btn_layout.addWidget(self.btn_disable_all)
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # 信号连接
        self.btn_enable_all.clicked.connect(self._enable_all)
        self.btn_disable_all.clicked.connect(self._disable_all)
        self.btn_refresh.clicked.connect(self.refresh)

        self.refresh()

    RULE_NAMES = {
        "R8": "交易时间检查",
        "R10": "宏观熔断",
        "R3": "涨跌停限制",
        "R5": "波动率过滤",
        "R6": "流动性检查",
    }

    def refresh(self):
        """刷新规则状态"""
        if not self.risk_engine:
            return

        rules = self.risk_engine.get_rule_status()
        self.table.setRowCount(len(rules))

        for i, rule in enumerate(rules):
            rid = rule["rule_id"]
            self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(rid))
            self.table.setItem(i, 1, QtWidgets.QTableWidgetItem(
                self.RULE_NAMES.get(rid, rid)))
            self.table.setItem(i, 2, QtWidgets.QTableWidgetItem(
                "启用" if rule["enabled"] else "禁用"))
            self.table.setItem(i, 3, QtWidgets.QTableWidgetItem(
                str(rule["violations"])))

    def _enable_all(self):
        for rid in ["R8", "R10", "R3", "R5", "R6"]:
            self.risk_engine.set_rule_enabled(rid, True)
        self.refresh()

    def _disable_all(self):
        for rid in ["R8", "R10", "R3", "R5", "R6"]:
            self.risk_engine.set_rule_enabled(rid, False)
        self.refresh()


class RiskMonitor(BaseMonitor):
    """风控拦截监控器"""
    event_type = "eRiskRule"
    data_key = "vt_orderid"
    sorting = True

    headers = {
        "symbol": {"display": "品种", "cell": BaseCell, "update": False},
        "direction": {"display": "方向", "cell": BaseCell, "update": False},
        "violations": {"display": "违规", "cell": BaseCell, "update": False},
        "blocked": {"display": "是否拦截", "cell": BaseCell, "update": False},
    }
