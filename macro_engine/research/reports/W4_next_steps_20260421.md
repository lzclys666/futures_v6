# W4 下一步执行计划 — Paper Trading 启动准备
**生成时间**：2026-04-21
**负责人**：因子分析师 YIYI
**版本**：v1.0

---

## 一、升贴水爬虫 Phase 1 准备

### 1.1 目标网站与数据源清单

| 网站/数据源 | 目标品种 | 数据内容 | 当前状态 |
|------------|---------|---------|---------|
| **上期所官网** | AU/AG/CU/AL/ZN/PB/RU/RB/HC | 升贴水参数、结算价、仓单日报 | 需页面结构分析 |
| **长江有色金属网** | CU/AL/ZN/NI/PB | 现货价格、升贴水报价 | 需页面结构分析 |
| **我的钢铁网（Mysteel）** | RB/HC/I/J/JM/M/Y/P/FU/BU | 现货价格、升贴水、市场情绪 | JM已有基础，扩展其余品种 |

### 1.2 页面结构分析所需字段

Phase 1 **不采集数据**，仅分析页面结构，需输出以下信息：

| 分析项 | 说明 |
|--------|------|
| URL 列表 | 每个数据页面的完整 URL（含翻页参数） |
| HTTP Method | GET / POST |
| 认证方式 | 公开 / 登录 / API Key |
| 关键字段 | 品种、合约、现货价、期货价、升贴水值、单位、日期 |
| 页面结构 | 表格 / JSON / API 接口 / 需要 JS 渲染 |
| 更新频率 | 日度（哪个时间点）/ 周度 |
| 反爬机制 | User-Agent / IP 限制 / 验证码 / 请求频率限制 |
| 数据延迟 | 官方发布到可采集的延迟时间 |
| 历史数据 | 是否可以拉取历史、起始日期 |

### 1.3 Phase 1 详细执行计划

**时间线**：04-28 ~ 05-02（由 Mimo + Lucy 执行）

#### Step 1：上期所官网结构分析（04-28 ~ 04-29，Mimo）
- [ ] 分析页面：`https://www.shfe.com.cn/statements/delayparam/`
- [ ] 确认升贴水参数页面 URL 是否需要登录
- [ ] 确认结算参数数据格式（JSON / HTML 表格）
- [ ] 输出：`SHFE_spread_analysis_20260428.md`

#### Step 2：长江有色网结构分析（04-29 ~ 04-30，Mimo）
- [ ] 访问 `https://www.ccmn.cn/` 或相关页面
- [ ] 确认现货升贴水报价表格结构
- [ ] 输出：`CCMN_spread_analysis_20260429.md`

#### Step 3：我的钢铁网结构分析（04-30 ~ 05-02，Lucy）
- [ ] 确认 Mysteel 现货数据页面结构
- [ ] 分析已有 JM 焦煤 basis 的 Mysteel 对接逻辑
- [ ] 输出：`MYSTEEEL_spread_analysis_20260501.md`

#### Step 4：汇总 Phase 1 分析报告（05-02）
- [ ] 合并三个网站的分析结果
- [ ] 评估各数据源接入难度和优先级
- [ ] 输出：`Spread_Crawler_Phase1_Analysis_Report_20260502.md`

---

## 二、Paper Trading 启动准备清单

### 2.1 系统就绪要求（04-28 前）

| 模块 | 状态 | 说明 |
|------|------|------|
| **PIT 数据服务** | ✅ 已有 | `core/pricing/pit_service.py`（路径待确认） |
| **因子 IC 验证框架** | ✅ 已有 | `research/validate_factor_ic.py` |
| **信号输出管道** | ✅ 已有 | `output/macro_signals.csv`（CSV 格式） |
| **vnpy CTA 策略** | ✅ 已有 | `strategies/macro_demo_strategy.py` |
| **AKShare 日度数据** | ⚠️ 需确认 | 各品种因子数据是否全部就位 |
| **LME SpreadDiff 信号** | 🔴 待 Mimo 开发 | z-score > 0.5 才下单 |

### 2.2 品种因子就绪状态

| 品种 | 因子数量 | IC 验证状态 | Paper Trading 就绪 |
|------|---------|------------|-------------------|
| **AU 黄金** | ~10 | ✅ 验证完毕 | ✅ 可启动 |
| **AG 白银** | ~11 | ✅ 验证完毕（金银比 IC=-0.297） | ✅ 可启动 |
| **CU 沪铜** | ~10 | ✅ 验证完毕（USD/CNY IC=-0.158） | ✅ 可启动 |
| **AL 沪铝** | ~8 | ⚠️ 部分验证 | ⚠️ 需补验证 |
| **ZN 沪锌** | ~8 | ⚠️ 部分验证 | ⚠️ 需补验证 |
| **NI 沪镍** | ~8 | ⚠️ 部分验证 | ⚠️ 需补验证 |
| **PB 沪铅** | ~6 | ⚠️ 部分验证 | ⚠️ 需补验证 |
| **RU 橡胶** | ~8 | ⚠️ 待验证 | 🔴 需 IC 验证 |
| **RB 螺纹钢** | ~10 | ⚠️ 待验证 | 🔴 需 IC 验证 |
| **JM 焦煤** | ~15 | ⚠️ 有基础数据 | 🔴 需 IC 验证 |

### 2.3 Paper Trading 启动前检查清单

#### 数据源检查
- [ ] AKShare 所有品种日度数据接入正常
- [ ] 因子 CSV 文件路径正确、无缺失日期
- [ ] 现货价格数据（AU_SGE、AG_SGE 等）已覆盖目标品种
- [ ] 宏观因子（USD/CNY、CN10Y、国债收益率）数据管道正常

#### 信号管道检查
- [ ] `macro_signals.csv` 格式正确（symbol, direction, score, confidence）
- [ ] 信号更新频率与交易日同步
- [ ] direction 字段支持：BULLISH / BEARISH / NEUTRAL
- [ ] confidence 字段支持：HIGH / MEDIUM / LOW
- [ ] vnpy 策略能正确读取并解析信号 CSV

#### 交易接口检查
- [ ] vnpy Gateway 已配置（SimNow 或飞马）
- [ ] CTA 策略 `macro_demo_strategy.py` 已加载
- [ ] 回测模式切换为 Paper Trading 模式
- [ ] 交易标的合约映射正确（symbol → vt_symbol）
- [ ] 风控模块已启用（止损/止盈/仓位限制）

#### LME SpreadDiff 信号检查
- [ ] LME 铜 cash-3m spread 数据已存档（`CU/daily/LME_copper_cash_3m_spread.csv`）
- [ ] SpreadDiff z-score 计算逻辑已实现
- [ ] **z-score > 0.5** 阈值已设定（由 Mimo 确认）
- [ ] SpreadDiff 信号输出格式与 `macro_signals.csv` 兼容

### 2.4 可能阻塞 Paper Trading 的风险点

| 风险 | 级别 | 应对方案 |
|------|------|---------|
| vnpy Gateway 未配置实时行情 | 🔴 严重 | 确认 SimNow 模拟交易接口是否可用 |
| AKShare 数据日度延迟（收盘后 ~2h） | 🟠 中等 | Paper Trading 使用 T+1 信号，降低频率 |
| 因子数据缺失（RU/RB/JM 等） | 🟠 中等 | 优先启动已验证品种（AU/AG/CU） |
| LME SpreadDiff 信号未就绪 | 🟠 中等 | 先用已有宏观因子启动铜品种 |
| 升贴水因子数据缺失（CU 等品种） | 🟡 轻微 | Phase 2 再接入升贴水因子 |
| 信号与行情时间不同步 | 🟡 轻微 | Paper Trading 阶段允许日内信号延迟 |

---

## 三、LME SpreadDiff 信号阈值（04-28 前）

### 3.1 当前状态
- **数据已有**：`CU/daily/LME_copper_cash_3m_spread.csv`（LME 铜 cash-3m spread）
- **spread_diff 定义**：待确认（通常为 现货-3M期货 或 cash-3m 价差的变化量）
- **z-score 计算**：需 Mimo 确认 rolling window 参数

### 3.2 阈值确认（由 Mimo 负责，04-28 前）
- **阈值**：z-score > 0.5 才下单
- **方向**：spread_diff > 0（contango 扩大）→ 可能反映需求疲软 → 做空铜
- **方向**：spread_diff < -0.5（backwardation）→ 可能反映供应紧张 → 做多铜
- **Mimo 任务**：在 `validate_factor_ic.py` 框架内验证 SpreadDiff 信号 IC，输出验证报告

---

## 四、04-28 Paper Trading 启动推荐方案

### 4.1 推荐启动品种
优先选择因子已验证、数据管道完整的品种：

| 品种 | 核心信号 | IC/IR | 置信度 |
|------|---------|-------|--------|
| **AG 白银** | 金银比 | IC=-0.297（极强） | HIGH |
| **AU 黄金** | USD/CNY 日变化量 | IC=-0.146 | HIGH |
| **CU 沪铜** | USD/CNY 日变化量 | IC=-0.158 | HIGH |
| **CU 沪铜** | LME SpreadDiff（待接入） | 待验证 | 待确认 |

### 4.2 启动阶段划分

| 阶段 | 时间 | 内容 |
|------|------|------|
| **Day 0** | 04-28 | 确认系统就绪，启动 AU/AG/CU Paper Trading |
| **Week 1** | 04-28 ~ 05-04 | 监控信号质量，跟踪 IC衰减，记录异常 |
| **升贴水 Phase 2** | 05-05 ~ | 接入升贴水因子，扩展 RU/RB/JM 品种 |

---

## 五、依赖关系与责任人

| 任务 | 负责人 | 截止日期 | 依赖 |
|------|--------|---------|------|
| 升贴水 Phase 1 分析 | Mimo + Lucy | 05-02 | 无 |
| LME SpreadDiff z-score 逻辑 | Mimo | 04-28 前 | CU spread 数据已就位 |
| 品种因子 IC 补验证 | YIYI | 04-25 | AKShare 数据 |
| Paper Trading 系统检查 | 项目经理 | 04-27 | vnpy 配置 |
| Paper Trading 启动 | 全部 | 04-28 | 以上全部就绪 |

---

## 六、输出文件清单

| 文件 | 路径 | 状态 |
|------|------|------|
| 上期所升贴水结构分析 | `reports/SHFE_spread_analysis_20260428.md` | ⏳ 待 Mimo 输出 |
| 长江有色网结构分析 | `reports/CCMN_spread_analysis_20260429.md` | ⏳ 待 Mimo 输出 |
| 我的钢铁网结构分析 | `reports/MYSTEEEL_spread_analysis_20260501.md` | ⏳ 待 Lucy 输出 |
| Phase 1 汇总报告 | `reports/Spread_Crawler_Phase1_Analysis_Report_20260502.md` | ⏳ 待输出 |
| LME SpreadDiff IC 验证 | `reports/CU_SpreadDiff_IC_validation_{DATE}.md` | ⏳ 待 Mimo 输出 |
| Paper Trading 启动报告 | `reports/Paper_Trading_Launch_Report_20260428.md` | ⏳ 待输出 |

---

## 七、备注

1. **Paper Trading 原则**：无真实资金，仅验证信号质量，重点跟踪 IC 和信号准确度
2. **升贴水因子定位**：Phase 2 扩展，不影响 04-28 基础品种启动
3. **Mimo 工作目录**：`C:\Users\Administrator\.qclaw\workspace-agent-d4f65f0e`（与报告目录不同！）
4. **报告统一存放**：`D:\futures_macro_engine\research\reports\{SYMBOL}\`
