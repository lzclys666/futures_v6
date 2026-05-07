# 三方模块阻塞项 & 后期任务 — 完整汇总 v4

> **日期**: 2026-05-06 14:20 | **汇总人**: 项目经理  
> **来源**: deep / YIYI / Lucy 各自报告 + 接口对齐深度扫描 + PM 实时验证  
> **v4 变更**: 逐项核验修复状态，纠正 v3 中 3 处错误，新增 2 个发现，删除 2 个已解决项

---

## 〇、v3→v4 修正记录

| # | v3 错误 | v4 修正 |
|---|---------|---------|
| 1 | L-B2 仍标为「阻塞项」 | ✅ 已修复（importlib 方案），移至已解决 |
| 2 | L-F5 仍标为「待修复」 | ✅ 已修复（L1189+L1318 by_alias=True），移至已解决 |
| 3 | 第五节「第一步」仍列「修复 vnpy_bridge + by_alias」为待执行 | 删除，已在 14:07 完成 |
| 4 | 未记录 importlib 循环导入修复过程 | 补入技术细节 |
| 5 | 未记录 simulate R12 实测结果 | 补入验证数据 |
| 6 | 未记录 _simulate_fallback 缺 R12 | 新增 D-P1-6 |

---

## 一、deep — 后端 / API / 风控

### 1.1 模块总体评估

**总体**: Phase 1+2 超额完成（风控全系列 + 交易闭环），正处在 Phase 3 交接期。
- 11/11 模块导入通过 | 7/7 语法通过 | 82 路由正常
- 关键风险：生产就绪级别差距大，代码功能级 vs 运维可靠性级

### 1.2 里程碑对照表

| 里程碑 | 目标日期 | 状态 | 说明 |
|--------|---------|------|------|
| M2.2 模拟盘首笔成交 | 5.23 | ✅ 已完成（超前） | |
| M3.1 VNpyBridge 打通 | 5.30 | ✅ 已完成（超前） | |
| **M3.2 前端风控面板上线** | **6.06** | ❌ 未开始 | deep 后端接口 + Lucy 前端 |
| **M4.1 回测夏普 > 1.0** | **6.13** | ❌ 未开始 | 12条规则未跑回测 |
| **M4.2 生产验收通过** | **6.20** | ❌ 未开始 | |

### 1.3 🔴 P0 阻塞项（不解决不能上线）

| # | 阻塞项 | 当前状态 | 差距 |
|---|--------|---------|------|
| **D-P0-1** | 实盘账户验证 | SimNow 模拟盘已 ESTABLISHED | 未连接过真实 CTP 账户，资金/持仓同步零验证 |
| **D-P0-2** | 连续运行稳定性 | 模块级测试通过 | VNpyBridge/SignalBridge 从未 >24h 连续运行，内存泄漏/线程安全未验证 |
| **D-P0-3** | 生产部署方案 | 手动 uvicorn 启动 | 未配置 Windows Service/守护进程，断电/崩溃后无自动恢复，无告警通道 |
| **D-P0-4** | 风控参数生产校准 | moderate 画像参数已设 | 11 条规则参数未经过任何回测验证，上线等于盲狙 |
| **D-P0-5** | 订单对账机制 | 下单/撤单 API 就绪 | 无成交回报与系统订单自动比对，漏单/重复单无法及时发现 |

### 1.4 🟡 P1 重要项（实盘前应完成）

| # | 任务 | 当前状态 | 预计工作量 |
|---|------|---------|-----------|
| **D-P1-1** | 风控引擎回测验证 | 回测系统跑通过，但风控未单独验证 | 12条规则跑完历史3年数据，确认夏普>1.0 |
| **D-P1-2** | 数据采集 cron 化 | schtasks 已配置 ✅ | 20:00采集 + 14:30日终打分 |
| **D-P1-3** | 信号时效性保障 | CSV 轮询模式已验证 | CSV写入→策略读取延迟未测量 |
| **D-P1-4** | 连接断线恢复 | CTP 重连逻辑在 VNpyBridge 中 | 断网/换日未完整测试 |
| **D-P1-5** | 前端风控面板 | ❌ 未开发 | M3.2 里程碑要求上线 |
| **D-P1-6** | _simulate_fallback 缺 R12 | 降级路径仅 R1/R8/R9/R10 | RiskEngine 不可用时 R12 撤单限制不生效 |

### 1.5 🟢 P2 优化项（可上线后迭代）

| # | 任务 |
|---|------|
| D-P2-1 | Y 品种爬虫错误修复（SyntaxError/IndentationError） |
| D-P2-2 | 压力测试 4 种标准场景实现 |
| D-P2-3 | 数据质量监控（PIT合规审计 + 异常值告警） |
| D-P2-4 | API 鉴权（82 路由完全开放，生产环境需 JWT/API Key） |
| D-P2-5 | 残留空 .db 文件清理 |

### 1.6 deep 核心结论

> 三件最关键的事: ① 风控回测（M4.1）→ ② 连续运行验证 → ③ 生产部署
> 建议优先级: 先做风控回测（M4.1），同时并行推进前端风控面板（M3.2→Lucy）和生产部署方案。

---

## 二、YIYI — 因子 / 数据

### 2.1 今日已完成（5/6 上午）

| 项目 | 状态 | 说明 |
|------|------|------|
| R1 db_utils 去重修复 | ✅ | |
| R2 免费因子修复 | ✅ | 7品种 + 17因子 |
| signal_daily_report 数据源修复 | ✅ | CSV→PIT+AKShare 双源 |

### 2.2 Phase 进度

| Phase | 状态 | 备注 |
|-------|------|------|
| Phase 0 数据就绪审计 | ✅ | |
| Phase 1 基础设施 | ✅ | |
| Phase 2 统计模块（IC/HMM/Bootstrap） | ✅ | |
| Phase 3 信号评分 | ✅ | |
| **Phase 4 宏观熔断** | 🔲 未启动 | ⚠️ 依赖 deep Phase 3 |
| **Phase 5 参数敏感性** | 🔲 未启动 | ⚠️ 依赖 deep Phase 4 |

### 2.3 🔴 实盘阻塞项

| # | 阻塞项 | 依赖方 | 具体描述 |
|---|--------|--------|----------|
| **Y-P0-1** | 宏观熔断机制 | deep | 所有品种同向极端时自动暂停交易。依赖 VNpyBridge/SignalBridge，未启动 |
| **Y-P0-2** | 12 品种有效因子不足（<10个） | mimo / 外部 | DCE 反爬 + 付费数据源缺失 |
| **Y-P0-3** | 信号日报数据新鲜度 | 待验证 | 今天修了 signal_daily_report.py，需等明天 09:00 cron 验证 |

### 2.4 12 品种有效因子 FAIL 清单

| 品种 | 有效因子数 | 要求 |
|------|-----------|------|
| EC | 2 | ≥10 |
| LC | 2 | ≥10 |
| LH | 2 | ≥10 |
| SC | 2 | ≥10 |
| PB | 7 | ≥10 |
| PP | 4 | ≥10 |
| Y | 5 | ≥10 |
| HC | 8 | ≥10 |
| J | 7 | ≥10 |
| I | 8 | ≥10 |
| SN | 6 | ≥10 |
| P | 6 | ≥10 |

### 2.5 后续任务

**🔴 P0 — 本周**
1. 19品种批量验收收尾
2. R2 修复收尾: HC→PP→Y
3. SN 修复验收
4. BU 补齐
5. EG 深修
6. ETL cron 入队
7. 验证明日 09:00 日报 cron 输出数据新鲜度

**🟡 P1**
1. AG 补 1 因子达 P0 门槛
2. BR OHLCV 建表 + 补采历史日线
3. AL/AO/BR 冷启动监控
4. OHLCV 数据新鲜度修复
5. 清理 AG PIT 违规 5 条

**🟢 P2（需 deep 先解除阻塞）**
1. Phase 4 宏观熔断（5.29-6.11）
2. Phase 5 参数敏感性分析（6.12-6.30）

### 2.6 现在能做的（不依赖他人）

1. 验证明日日报
2. 清理 AG PIT 违规
3. 设计 Phase 4 熔断方案
4. 推动 12 品种数据补齐
5. 金银比 IC 方向验证

---

## 三、Lucy — 前端 / UI

### 3.1 模块总体评估

- 前端 70% 的任务可以 100% Mock 先行完成
- Phase 3-4 的 UI 工作几乎不依赖实盘数据

### 3.2 🔴 阻塞项（外部依赖）

| # | 阻塞项 | 依赖方 | 等级 | 当前状态 |
|---|--------|--------|------|----------|
| **L-B1** | CTP 连接 + 模拟账户 | deep | 🔴 致命 | SimNow 已连接，等 5/7 开盘验证 |
| **L-B2** | vnpy_bridge 导入路径断裂 | deep | 🔴 致命 | ✅ **已修复**（importlib 方案，14:07 验证通过） |
| **L-B3** | SignalBridge | deep | 🔴 致命 | ❌ 未开发 |
| **L-B4** | MacroRiskApp 13 条规则 | deep | 🟠 高 | ❌ 未开发 |
| **L-B5** | IC 热力图生产数据 | YIYI | 🟡 中 | API 已就绪，等前端对接 |
| **L-B6** | HMM Regime API | YIYI | 🟡 中 | ❌ 未开发 |
| **L-B7** | 信号系统 API | YIYI | 🟡 中 | ✅ API 已就绪 |

### 3.3 🔧 前端自身待修复

| # | 问题 | 严重度 | 工时 | 当前状态 |
|---|------|--------|------|----------|
| **L-F1** | validateRiskStatusData 格式不兼容 | 🔴 P0 | **1h** | ❌ 待修 |
| **L-F2** | 两套并行风控 API | 🟡 P1 | 3h | ❌ 待修 |
| **L-F3** | RiskConfigPage 6 项改进 | 🟡 P1 | 4h | ❌ 待修 |
| **L-F4** | 三层接口不一致 | 🟡 P1 | 待对齐 | ❌ 待修 |
| **L-F5** | FactorDetail by_alias | 🔴 P0 | 5min | ✅ **已修复**（14:07 验证通过） |
| **L-F6** | OrderResponse 格式完全不同 | 🔴 P0 | 2h | ❌ 待修 |
| **L-F7** | CancelOrderResponse 缺 orderId | 🟡 P1 | 30min | ❌ 待修 |
| **L-F8** | SimulateResponse pass_ 别名 | 🟡 P1 | 15min | ❌ 待修（风险低） |

> usePolling Hook：代码库核验无定义无引用，已排除。

### 3.4 按 Phase 划分的待完成任务

#### Phase 2（当前，38h）
持仓看板 v2 (4h) | 风控面板 v2 (6h) | 风控配置页 (6h) | 凯利计算器 (4h,已完成) | 处置效应弹窗 (4h) | IC热力图深化 (4h) | L-F1修复 (1h)

#### Phase 3（5.15-5.28，24h）
交易面板完整版 (8h) | 压力测试报告 (4h) | 因子 Dashboard (8h) | 信号 API 对接 (4h)

#### Phase 4（5.29-6.11，20h）
Rule Simulator (6h) | 月度报告导出 (4h) | 个人中心 (4h) | 深色模式 (3h) | 审计日志 (3h)

#### Phase 5（6.12-6.30，22h）
性能优化 (6h) | 错误边界 (3h) | Mock切换 (3h) | CI/CD (4h) | 验收 (6h)

---

## 四、接口对齐状态（PM 实时验证 14:20）

### 4.1 已修复

| # | 问题 | 修复方式 | 验证结果 |
|---|------|---------|----------|
| **#1** | vnpy_bridge 导入路径断裂 | importlib 加载绝对路径 | ✅ trading/portfolio code=0 |
| **#2** | FactorDetail by_alias | L1189+L1318 by_alias=True | ✅ camelCase 字段全部正确 |

### 4.2 仍待修复

| # | 问题 | 严重度 | 修复方 | 工时 |
|---|------|--------|--------|------|
| **#3** | OrderResponse 格式完全不同 | 🔴 P0 | deep+Lucy | 2h |
| **#4** | CancelOrderResponse 缺 orderId | 🟡 P1 | deep | 30min |
| **#5** | SimulateResponse pass_ 别名 | 🟡 P1 | deep | 15min |

### 4.3 已对齐的接口

RiskStatusResponse ✅ | RiskRuleId (R1-R12) ✅ | RiskRule ✅ | KellyRequest/Response ✅ | StressTestReport/Result ✅ | SimulateRequest/Response ✅ | Portfolio ✅ | MacroSignal ✅

### 4.4 R12 全链路验证（14:17 实测）

| 检查项 | 结果 |
|--------|------|
| risk_rules.yaml 含 R12 | ✅ 12条规则 |
| /api/risk/rules 返回 R12 | ✅ 12条，R12 layer=2 |
| /api/risk/status 含 R12_CANCEL_LIMIT | ✅ |
| /api/risk/simulate R12 | ✅ pass=true |
| _RULE_LAYERS R12=2 | ✅ |
| _simulate_fallback 含 R12 | ❌ **缺失**（仅 R1/R8/R9/R10） |

---

## 五、跨团队依赖矩阵

### 5.1 阻塞传递链

```
deep Phase 3（VNpyBridge + SignalBridge + MacroRiskApp）
  ↓ 阻塞
Lucy Phase 2-4 所有交易/风控功能联调
  ↓ 连累
YIYI Phase 4 宏观熔断 + Phase 5 参数敏感性
```

### 5.2 协作关系汇总

| # | 需求 | → 到谁 | 紧急度 |
|---|------|--------|--------|
| 1 | CTP 真实账户连接 | deep | 🔴🔴🔴 |
| 2 | SignalBridge 开发 | deep | 🔴🔴 |
| 3 | 12 条风控规则 API 完整 | deep | 🔴🔴 |
| 4 | Phase 3 完成为 Phase 4/5 解锁 | deep→YIYI | 🔴🔴 |
| 5 | AG 因子 IC 重算 | deep→YIYI | 🔴 |
| 6 | 因子采集/ETL cron 入队 | YIYI→mimo | 🔴 |
| 7 | 12 品种数据补齐 | YIYI→mimo | 🔴 |
| 8 | IC 热力图生产数据 | YIYI→Lucy | 🟡 |
| 9 | OrderResponse 格式对齐 | deep+Lucy | 🔴 |
| 10 | validateRiskStatusData 格式修复 | Lucy 自行 | 🟡 |

---

## 六、PM 建议行动顺序

### 第一步：立即修复剩余接口断裂 🔴（今天）

| # | 行动 | 执行者 | 工时 |
|---|------|--------|------|
| **1** | OrderResponse 格式对齐 | **deep** | 2h |
| **2** | CancelOrderResponse 补 orderId | **deep** | 30min |
| **3** | 修复 L-F1 validateRiskStatusData | **Lucy** | 1h |
| **4** | _simulate_fallback 补 R12 | **deep** | 30min |

### 第二步：并行推进 🟡（本周）

| # | 行动 | 执行者 |
|---|------|--------|
| 5 | Lucy Phase 2 Mock 先行 | Lucy |
| 6 | deep 风控回测（M4.1） | deep |
| 7 | YIYI 品种批量验收 | YIYI+mimo |
| 8 | deep 生产部署方案 | deep |

### 第三步：解锁后期 🟢（Phase 3 完成后）

| # | 行动 | 执行者 | 前提 |
|---|------|--------|------|
| 9 | Lucy Phase 3 交易面板 | Lucy | SignalBridge |
| 10 | YIYI Phase 4 宏观熔断 | YIYI | deep Phase 3 |
| 11 | deep Phase 4 回测引擎 | deep | Phase 3 |
| 12 | YIYI Phase 5 参数敏感性 | YIYI | Phase 4 |

---

## 七、结论

### 今日进展（5/6）

- ✅ vnpy_bridge 导入路径修复（importlib，PM 人肉介入）
- ✅ FactorDetail by_alias 修复（PM 人肉介入）
- ✅ R12 全链路验证通过（12条规则，layer=2）
- ✅ API 重启成功
- ❌ OrderResponse 格式对齐未完成（2h）
- ❌ _simulate_fallback 缺 R12（30min）

### 全局瓶颈

**deep 是当前全局瓶颈**——阻塞 Lucy Phase 2-4 + YIYI Phase 4/5 + M3.2/M4.x 里程碑。

### 好消息

- Lucy 70% 可 Mock 先行
- YIYI 核心能力已就绪（Phase 0-3）
- 代码骨架健康（82 路由，12条风控规则全部上线）
