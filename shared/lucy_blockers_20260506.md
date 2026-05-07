# Lucy 前端模块 — 阻塞项 & 后期任务清单

> **整理日期**: 2026-05-06  
> **整理人**: Lucy (agent-f8666767)  
> **当前 Phase 1 状态**: ✅ M1 里程碑达成（2026-04-28）  
> **当前 Phase 2 状态**: ⚠️ 等待 deep 交付 P0 接口

---

## 一、当前阻塞项

### 🔴 P0 — 阻塞 Phase 2 启动

| # | 阻塞项 | 依赖方 | 具体原因 | 修复成本 | 影响范围 |
|---|--------|--------|----------|----------|----------|
| **B1** | `PaperBridge.is_running()` 方法缺失 | **deep** | `services/vnpy_bridge.py:52` 缺少一行 `def is_running(self) -> bool: return True`，导致 5 个 VNpy API 端点全部返回 500 | **1 行代码** | 持仓看板、交易面板无法获取真实数据 |
| **B2** | CTP 连接 + 策略加载未完成 | **deep** | VNpy CTP 网关未连接真实/模拟账户，策略未加载 | 未知 | 持仓看板 v2 真实数据、交易面板下单功能 |
| **B3** | IC 热力图生产数据 | **YIYI** | `/api/ic/heatmap` 端点已连通但生产数据未就绪 | 待 YIYI 排期 | Phase 2 IC 热力图深化（真实 IC 矩阵） |

#### B1 细节 — 受影响端点

| 端点 | 当前状态 | B1 修复后 |
|------|----------|-----------|
| `GET /api/vnpy/status` | ✅ 已可用 | ✅ 已可用 |
| `GET /api/vnpy/account` | ❌ 500（is_running 缺失） | ✅ 可用 |
| `GET /api/vnpy/positions` | ❌ 500 | ✅ 可用 |
| `GET /api/vnpy/orders` | ❌ 500 | ✅ 可用 |
| `POST /api/vnpy/place-order` | ❌ 500 | ✅ 可用 |
| `DELETE /api/vnpy/cancel-order/{id}` | ❌ 500 | ✅ 可用 |

> **B1 背景**: deep 子代理于 2026-04-28 确认根因并给出修复方案，但当日积分耗尽，修复未执行。至今（5/6）状态不明。

---

### 🟡 P1 — 阻塞 Phase 3 准备

| # | 阻塞项 | 依赖方 | 具体原因 | 影响范围 |
|---|--------|--------|----------|----------|
| **B4** | `/api/risk/precheck` 端点未实现 | **deep** | `routes/risk.py` 中未找到该端点定义，风控预检流程无后端支撑 | 交易面板风控预检（Phase 3） |
| **B5** | YIYI 信号系统 API 未对接 | **YIYI** | `/api/signal/*` 端点 Week 4 规划，因子 Dashboard 无法获取详细因子拆解 | 因子 Dashboard（Phase 3） |
| **B6** | WebSocket 实时推送未在前端对接 | **Lucy** | `ws://localhost:8000/ws/vnpy` 后端已实现，但前端尚未接入 WebSocket 推送 | Dashboard 实时性（目前仅为轮询） |

---

### 🟠 P2 — 阻塞 Phase 4 准备

| # | 阻塞项 | 依赖方 | 具体原因 | 影响范围 |
|---|--------|--------|----------|----------|
| **B7** | 13 条风控规则 API | **deep** | MacroRiskApp 规则定义接口未交付 | 风控面板 v2（Phase 4） |
| **B8** | HMM Regime API | **YIYI** | 宏观状态识别 API Week 4 规划 | 宏观熔断逻辑（Phase 4） |
| **B9** | CTP 真实账户 | **外部** | CTP 模拟户过期，真实账户无 ETA | 全链路真实验收 |

---

### ⚠️ 已发现的前端自身问题（非外部阻塞）

| # | 问题 | 严重度 | 说明 |
|---|------|--------|------|
| **F1** | 两套并行的风控 API 实现 | P1 | `api/trading.ts` 的 `fetchRiskStatus()` 与 `api/risk.ts` 的 `fetchRiskStatusResponse()` 调用同一端点但类型不同 |
| **F2** | `validateRiskStatusData()` 格式不兼容 | P0 | `tradingValidators.ts` 校验旧格式 `['正常','告警','触发']`，但 `/api/risk/status` 返回新格式 `'PASS'|'WARN'|'BLOCK'`，运行时校验必定失败 |
| **F3** | `API_CONTRACT.md` 与 Pydantic 模型不一致 | P1 | YIYI 审查发现 `/api/risk/status` 响应格式三层不一致（API_CONTRACT vs Pydantic vs vnpy_bridge 实际返回） |

---

## 二、后期任务清单

### 🔴 P0 — Phase 2（原计划 5.1-5.14，36h）
> ⚠️ 当前因 B1/B2 阻塞，Phase 2 尚未正式启动，前端可用 Mock 数据先行开发

| # | 任务 | 路由 | 工时 | 依赖 | 备注 |
|---|------|------|------|------|------|
| P2-1 | 持仓看板 v2（可用资金 + 一键平仓按钮） | `/positions` | 10h | B1+B2（真实数据）/ Mock | 优先 Mock 开发 |
| P2-2 | 风控面板 v2（11 条规则完整展示） | `/risk` | 8h | B7（规则定义） | Mock 11 条规则先行 |
| P2-3 | 风控规则配置页 | `/risk/config` | 6h | B7 | 配置化表单，只读/编辑态 |
| P2-4 | 凯利公式计算器 | `/kelly` | 4h | 无后端依赖 | 纯前端计算 |
| P2-5 | 处置效应弹窗 | 持仓看板内嵌 | 3h | B1+B2 | 亏损持仓超出阈值时弹出 |
| P2-6 | IC 热力图深化 | Dashboard 底部 | 4h | B3（YIYI 生产数据） | 当前静态组件，等待真实 IC 矩阵 |
| P2-7 | 修复 F2（validateRiskStatusData） | 全局 | 1h | 无 | **立即修复，不等待外部依赖** |

**Phase 2 小计**: 36h（含 1h 紧急修复）

---

### 🟡 P1 — Phase 3（原计划 5.15-5.28，24h）

| # | 任务 | 路由 | 工时 | 依赖 | 备注 |
|---|------|------|------|------|------|
| P3-1 | 交易面板完整版（含风控预检） | `/trading` | 8h | B4（risk/precheck）+ B1 | 下单前调用 precheck 阻断 |
| P3-2 | 压力测试报告页 | `/stress-test` | 5h | 可 Mock | 场景配置 + 指标计算 |
| P3-3 | 因子 Dashboard（26 因子详细展示） | Dashboard 因子区 | 5h | B5（YIYI signal API） | IC 柱状图 + 因子贡献堆叠 |
| P3-4 | YIYI 信号系统 API 对接 | 全局 | 3h | B5 | `/api/signal/*` 全端点对接 |
| P3-5 | 修复 F1（统一风控 API 调用） | 全局 | 3h | 无 | 废弃 `trading.ts` 重复实现 |

**Phase 3 小计**: 24h

---

### 🟠 P1 — Phase 4（原计划 5.29-6.11，20h）

| # | 任务 | 路由 | 工时 | 依赖 | 备注 |
|---|------|------|------|------|------|
| P4-1 | Rule Simulator（规则模拟器） | `/risk/simulator` | 6h | B7 | 调参 + 回测展示 |
| P4-2 | 月度报告导出（PDF/CSV） | `/profile` | 4h | 无 | 前端生成 + 下载 |
| P4-3 | 个人中心完整版 | `/profile` | 4h | 无 | 偏好设置 + 风险画像 |
| P4-4 | 深色模式 Token | 全局 | 2h | 无 | CSS 变量 + Ant Design 主题 |
| P4-5 | 审计日志页 | `/admin` | 3h | deep 日志接口 | 操作审计 + 系统日志 |
| P4-6 | 宏观熔断对接 | `/risk` | 1h | B8（HMM Regime） | 熔断状态灯 + 通知 |

**Phase 4 小计**: 20h

---

### 🟢 P2 — Phase 5（原计划 6.12-6.30，22h）

| # | 任务 | 工时 | 备注 |
|---|------|------|------|
| P5-1 | 性能优化（虚拟滚动/代码分割） | 6h | 大数据量时的渲染优化 |
| P5-2 | 错误边界 + 全局 ErrorBoundary | 3h | React Error Boundary |
| P5-3 | Mock/真实切换开关 | 2h | 开发/生产模式一键切换 |
| P5-4 | CI/CD 配置 | 3h | Vite build + 部署 |
| P5-5 | 用户文档 | 3h | 操作手册 |
| P5-6 | 生产验收 | 5h | 全链路测试 + UAT |

**Phase 5 小计**: 22h

---

## 三、依赖方当前响应状态

| 依赖方 | 上次回复日期 | 当前状态 | 待交付项 |
|--------|-------------|----------|----------|
| **deep** | 2026-04-28（积分耗尽） | ⚠️ 失联 | B1(is_running) B2(CTP) B4(precheck) B7(风控规则) |
| **YIYI** | 2026-05-03（审查报告） | ✅ 活跃 | B3(IC 生产数据) B5(signal API) B8(HMM Regime) |
| **外部** | N/A | N/A | B9(CTP 真实账户) |

---

## 四、立即行动建议（无需等待外部依赖）

| 优先级 | 行动 | 工时 |
|--------|------|------|
| 🔴 | 修复 F2：`validateRiskStatusData()` → 对齐 `RiskSeverity` 新格式 | 1h |
| 🟡 | 修复 F1：统一风控 API 调用，废弃 `trading.ts` 重复实现 | 3h |
| 🟡 | WebSocket 前端对接（`ws://localhost:8000/ws/vnpy`） | 4h |
| 🟢 | Phase 2 Mock 先行开发（持仓看板 + 风控面板 UI） | 20h |

---

## 五、风险提示

1. **deep 失联超过 7 天（4.28 → 5.6）**：P0 一行修复无人执行，Phase 2 真实数据联调无限期推迟
2. **CTP 账户无 ETA**：即使 B1 修复，Phase 3 交易面板仍无法真实下单
3. **三层接口不一致**：YIYI 审查发现的 API_CONTRACT / Pydantic / vnpy_bridge 三方不一致，需三方对齐后才能联调

> 💡 **建议 PM 介入**：直接联系 deep 人工修复 B1（一行代码），解锁 5 个 VNpy 端点。