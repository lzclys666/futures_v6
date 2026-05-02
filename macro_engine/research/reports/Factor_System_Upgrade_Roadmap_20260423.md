# 因子系统升级实施路线图

> **文档版本**：v1.0  
> **制定日期**：2026-04-23  
> **制定人**：因子分析师 YIYI  
> **对应计划**：Factor_System_Upgrade_Implementation_Plan_20260423.md

---

## 一、总体路线图

```
Week 1        Week 2        Week 3        Week 4        Week 5
  |             |             |             |             |
  v             v             v             v             v
┌──────┐     ┌──────┐     ┌──────┐     ┌──────┐     ┌──────┐
│Phase │────→│Phase │────→│Phase │────→│Phase │────→│Phase │
│  0   │Gate0│  1   │Gate1│  2   │Gate2│ 3+4  │Gate3│5+6+7 │
│审计  │     │管道  │     │统计  │     │信号+ │     │推广  │
│      │     │      │     │      │     │可视化│     │      │
└──────┘     └──────┘     └──────┘     └──────┘     └──────┘
   │                                          │            │
   └──────────────────────────────────────────┴────────────┘
                                              v
                                          Gate 4
                                        全品种上线
```

**总工期**：5周（约14工作日 / 112工时）  
**关键里程碑**：Week 1末 Gate 0 → Week 2末 Gate 1 → Week 3末 Gate 2 → Week 4末 Gate 3 → Week 5末 Gate 4

---

## 二、分阶段路线图

### Phase 0：数据就绪审计（Week 1）

**目标**：摸清数据家底，建立"可升级因子清单"和"待修复数据清单"

```
Day 1~2                    Day 2~3                    Day 3~4                    Day 4~5                    Day 5
  |                          |                          |                          |                          |
  v                          v                          v                          v                          v
┌──────────────┐        ┌──────────────┐        ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│ Step 0.1     │        │ Step 0.2     │        │ Step 0.3     │        │ Step 0.4     │        │ Step 0.5     │
│ 因子数据审计  │        │ 品种价格审计  │        │ 管道健康检查  │        │ IC窗口评估    │        │ 审计报告输出  │
│              │        │              │        │              │        │              │        │              │
│ audit_factor │        │ audit_price  │        │ 检查cron任务  │        │ assess_ic_   │        │ Factor_Data_ │
│ _data.py     │        │ _data.py     │        │ 存活状态      │        │ window.py    │        │ Readiness_   │
│              │        │              │        │              │        │              │        │ Report.md    │
│ 交付物：      │        │ 交付物：      │        │ 交付物：      │        │ 交付物：      │        │ 交付物：      │
│ 因子完整度    │        │ 品种可获取    │        │ 管道状态清单  │        │ IC序列长度    │        │ 综合审计报告  │
│ CSV          │        │ 状态CSV      │        │              │        │ 矩阵         │        │              │
└──────────────┘        └──────────────┘        └──────────────┘        └──────────────┘        └──────────────┘
```

**关键产出**：
- `audit_factor_data_20260423.csv` — 因子完整度报告
- `audit_price_data_20260423.csv` — 品种价格数据状态
- `Factor_Data_Readiness_Report_20260423.md` — 综合审计报告

**质量门控 Gate 0**（Day 5 末）：
- [ ] 核心因子完整度 ≥ 70%
- [ ] AKShare 22品种价格可获取
- [ ] 实时管道 cron 存活
- [ ] IC序列长度 ≥ 60天
- [ ] PIT冒烟测试通过

---

### Phase 1：数据管道修复（Week 2）

**前置条件**：Gate 0 通过  
**目标**：建立数据质量保障体系

```
Step 1.1              Step 1.2              Step 1.3              Step 1.4
  |                     |                     |                     |
  v                     v                     v                     v
┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│ 修复缺失  │      │ pandera  │      │ PIT冒烟  │      │ CSV→    │
│ 数据     │      │ Schema   │      │ 测试     │      │ Parquet │
│          │      │ 校验     │      │          │      │ 双写迁移 │
│ mimo负责 │      │ mimo+YIYI│      │ YIYI负责 │      │ mimo负责 │
│          │      │          │      │          │      │          │
│ 历史补采 │      │ 异常隔离 │      │ 每日随机 │      │ 兼容VNpy│
│ 管道修复 │      │ quarantine│     │ 10时点   │      │ 三阶段  │
└──────────┘      └──────────┘      └──────────┘      └──────────┘
```

**关键产出**：
- 修复后的因子数据文件
- `schemas.py` — pandera Schema定义
- `pit_smoke_test.py` — PIT冒烟测试脚本
- 双写模式数据管道

**质量门控 Gate 1**（Week 2 末）：
- [ ] pandera校验全部通过
- [ ] 异常数据自动隔离
- [ ] PIT冒烟连续7天通过

---

### Phase 2：统计模块开发（Week 3）

**前置条件**：Gate 1 通过  
**目标**：实现核心统计方法论

```
Step 2.1                    Step 2.2                    Step 2.3
  |                           |                           |
  v                           v                           v
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ 滚动IC/IR +     │     │ HMM Regime      │     │ 多因子IC        │
│ Bootstrap CI    │     │ 检测            │     │ 热力图          │
│                 │     │                 │     │                 │
│ 60日窗口        │     │ 3状态HMM        │     │ 因子×品种       │
│ t检验           │     │ GaussianHMM     │     │ 矩阵可视化      │
│ 1000次Bootstrap │     │ 品种自身特征    │     │                 │
│ 95% CI          │     │ 不依赖VIX       │     │                 │
│                 │     │                 │     │                 │
│ 输出：           │     │ 输出：           │     │ 输出：           │
│ icMean/icMedian │     │ REGIME_STRONG   │     │ IC矩阵CSV      │
│ ciLower/ciUpper │     │ REGIME_NORMAL   │     │ IR矩阵CSV      │
│ tStat/pValue    │     │ REGIME_WEAK     │     │ 热力图HTML     │
│ winRate/nObs    │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

**关键产出**：
- `compute_rolling_ic_with_stats()` — 核心统计函数
- `detect_regime()` — HMM Regime检测
- `generate_ic_heatmap()` — IC热力图生成

**质量门控 Gate 2**（Week 3 末）：
- [ ] Bootstrap CI 可计算
- [ ] HMM Regime 可判定
- [ ] IC热力图可渲染
- [ ] 回归测试通过（已知IC不漂移）

---

### Phase 3+4：信号系统 + 可视化（Week 4）

**前置条件**：Gate 2 通过  
**目标**：从统计到决策，从数据到界面

```
Phase 3: 信号系统                          Phase 4: 可视化升级
┌─────────────────────────────┐           ┌─────────────────────────────┐
│ Step 3.1 多维信号评分        │           │ Step 4.1 三图联动Dashboard   │
│  ├─ IC强度分 (25分)         │           │  ├─ 因子走势图              │
│  ├─ 稳定性分 (25分)         │           │  ├─ 滚动IC图 + Bootstrap CI │
│  ├─ Regime分 (25分)         │           │  ├─ 滚动IR图               │
│  └─ 趋势分   (25分)         │           │  └─ 信号仪表盘              │
│                             │           │                             │
│ Step 3.2 拥挤度监控          │           │ Step 4.2 IC热力图           │
│  ├─ IC波动率z-score         │           │  └─ 品种×因子矩阵           │
│  └─ 0~100评分               │           │                             │
│                             │           │ Step 4.3 失效预警           │
│ Step 3.3 动态持有期          │           │  ├─ IC<0.01持续20日         │
│  └─ 1/5/10/20日IR最优       │           │  ├─ 方向反转检测            │
│                             │           │  └─ 拥挤度>85告警           │
│ 输出：0~100评分 + 方向 +     │           │                             │
│       持有期 + Regime        │           │ 技术栈：React + ECharts     │
└─────────────────────────────┘           └─────────────────────────────┘
```

**关键产出**：
- `signal_score()` — 多维评分函数
- `factor_crowding_score()` — 拥挤度计算
- `optimize_holding_period()` — 持有期优化
- `check_failure_signals()` — 失效预警
- 三图联动 Dashboard（React + ECharts）
- IC热力图组件

**质量门控 Gate 3**（Week 4 末）：
- [ ] 信号评分可计算
- [ ] 拥挤度可计算
- [ ] 动态持有期推荐正确
- [ ] 失效预警可触发
- [ ] Dashboard响应 < 2秒

---

### Phase 5+6+7：全品种推广（Week 5）

**前置条件**：Gate 3 通过  
**目标**：从4品种扩展到22品种，建立持续优化机制

```
Phase 5: 标注+知识库        Phase 6: 多品种看板         Phase 7: 推广优化
  |                          |                          |
  v                          v                          v
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ 私人标注系统  │      │ 品种分组信号  │      │ 未覆盖品种补全 │
│              │      │              │      │              │
│ SQLite存储   │      │ 贵金属组      │      │ 第一梯队：    │
│ 因子+日期+备注│     │ 有色金属组    │      │ AU/AG/CU/NI  │
│ Dashboard集成 │     │ 黑色系组      │      │              │
│              │      │ 化工组        │      │ 第二梯队：    │
│ 失效事件知识库│      │ 农产品组      │      │ AL/ZN/PB/SN  │
│              │      │              │      │ RB/HC/I/J/JM │
│ 记录失效模式  │      │ 板块联动信号  │      │              │
│ 团队共享     │      │ 方向一致率    │      │ 第三梯队：    │
│              │      │              │      │ TA/EG/PP等   │
└──────────────┘      └──────────────┘      └──────────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                v
                         持续优化机制
                         ├─ 每月1日：IC热力图更新
                         ├─ 每月第一个周五：失效复盘
                         ├─ 每月15日：管道健康检查
                         └─ 每季度：新因子评估
```

**关键产出**：
- `annotations.db` — 私人标注数据库
- `knowledge_base.db` — 失效事件知识库
- 品种分组信号看板
- 板块联动信号分析
- 全品种覆盖（22个）

**质量门控 Gate 4**（Week 5 末）：
- [ ] 22品种全部接入
- [ ] 月度review机制建立
- [ ] 标注系统运行
- [ ] 知识库 ≥ 5条记录
- [ ] 文档完整

---

## 三、关键路径与依赖关系

```
关键路径（决定总工期）：
═══════════════════════════════════════════════════════════════════

数据审计(Week1) → 管道修复(Week2) → 统计模块(Week3) → 信号+可视化(Week4) → 全品种推广(Week5)
      │                │                │                  │                │
   Gate 0           Gate 1           Gate 2             Gate 3           Gate 4
   ( blocker )      ( blocker )      ( blocker )        ( blocker )      ( final )

═══════════════════════════════════════════════════════════════════

可并行工作（不阻塞关键路径）：
├─ Week 2: PIT冒烟测试可与管道修复并行
├─ Week 3: HMM可与Bootstrap CI并行开发
├─ Week 4: 私人标注系统可与可视化并行
└─ Week 5: 知识库积累可与品种推广并行
```

---

## 四、资源分配

| 角色 | 主要职责 | 投入工时 |
|------|---------|---------|
| **YIYI（因子分析师）** | 数据审计、统计模块、信号系统、验收 | ~60h |
| **mimo（程序员）** | 数据修复、Schema校验、采集脚本、标注系统 | ~40h |
| **前端开发** | Dashboard、热力图、多品种看板 | ~24h |
| **项目经理** | 进度跟踪、资源协调、月度review排期 | ~8h |

> 注：若前端资源不足，Phase 4 可拆分为 MVP（ECharts快速原型，8h）和完整版（16h）两期交付

---

## 五、风险应对路线图

```
风险发生时点与应对：

Week 1                    Week 2                    Week 3
  |                         |                         |
  v                         v                         v
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│ R1:数据缺失  │       │ R2:AKShare  │       │ R3:HMM不稳定│
│ 严重        │       │ 接口变更    │       │ 切换频繁    │
│             │       │             │       │             │
│ 应对：降级  │       │ 应对：备用源 │       │ 应对：平滑  │
│ 观察因子    │       │ Tushare     │       │ N天确认期   │
└─────────────┘       └─────────────┘       └─────────────┘

Week 4                    Week 5
  |                         |
  v                         v
┌─────────────┐       ┌─────────────┐
│ R4:Dashboard │       │ R5:拥挤度   │
│ 响应慢      │       │ 数据不足    │
│             │       │             │
│ 应对：缓存  │       │ 应对：IC波动│
│ 按需加载    │       │ 率替代      │
└─────────────┘       └─────────────┘
```

---

## 六、交付物清单

| 阶段 | 交付物 | 格式 | 存放路径 |
|------|--------|------|---------|
| Phase 0 | 因子数据审计报告 | CSV | `research/reports/audit_factor_data_YYYYMMDD.csv` |
| Phase 0 | 品种价格审计报告 | CSV | `research/reports/audit_price_data_YYYYMMDD.csv` |
| Phase 0 | 数据就绪综合报告 | MD | `research/reports/Factor_Data_Readiness_Report_YYYYMMDD.md` |
| Phase 1 | pandera Schema | PY | `core/schemas.py` |
| Phase 1 | PIT冒烟测试脚本 | PY | `core/pit_smoke_test.py` |
| Phase 2 | IC统计模块 | PY | `core/validation/ic_stats.py` |
| Phase 2 | HMM Regime检测 | PY | `core/regime/hmm_detector.py` |
| Phase 2 | IC热力图生成 | PY | `core/visualization/ic_heatmap.py` |
| Phase 3 | 信号评分系统 | PY | `core/scoring/signal_engine.py` |
| Phase 3 | 拥挤度监控 | PY | `core/scoring/crowding_detector.py` |
| Phase 3 | 持有期优化 | PY | `core/scoring/hold_optimizer.py` |
| Phase 3 | 失效预警 | PY | `core/alerts/failure_monitor.py` |
| Phase 4 | 三图联动Dashboard | React | `frontend/src/components/macro/` |
| Phase 4 | IC热力图组件 | React | `frontend/src/components/macro/ICHeatmap.tsx` |
| Phase 5 | 私人标注系统 | SQLite | `data/annotations.db` |
| Phase 5 | 失效知识库 | SQLite | `data/knowledge_base.db` |
| Phase 6 | 多品种看板 | React | `frontend/src/components/macro/SectorDashboard.tsx` |
| Phase 7 | 操作手册 | MD | `docs/operation_manual.md` |
| Phase 7 | 故障排查指南 | MD | `docs/troubleshooting.md` |

---

## 七、里程碑检查点

```
Week 1 末 ──→ Gate 0: 数据就绪审计
                ├─ 因子完整度 ≥ 70%
                ├─ 22品种价格可获取
                ├─ 管道存活
                └─ IC序列 ≥ 60天

Week 2 末 ──→ Gate 1: 数据管道验收
                ├─ pandera校验通过
                ├─ 异常自动隔离
                └─ PIT冒烟7天通过

Week 3 末 ──→ Gate 2: 统计模块验收
                ├─ Bootstrap可计算
                ├─ HMM可判定
                ├─ 热力图可渲染
                └─ 回归测试通过

Week 4 末 ──→ Gate 3: 信号系统验收
                ├─ 评分可计算
                ├─ 拥挤度可计算
                ├─ 持有期推荐正确
                ├─ 预警可触发
                └─ Dashboard < 2秒

Week 5 末 ──→ Gate 4: 全品种上线
                ├─ 22品种接入
                ├─ 月度review机制
                ├─ 标注系统运行
                ├─ 知识库 ≥ 5条
                └─ 文档完整
```

---

## 八、成功标准

升级完成后的系统应达到：

| 指标 | 目标值 |
|------|--------|
| 因子覆盖 | 22品种 × 平均5因子 = 110+ 因子对 |
| 信号响应 | Dashboard < 2秒 |
| 数据质量 | 完整度 ≥ 90%，异常自动隔离 |
| 统计能力 | Bootstrap CI + HMM Regime + 拥挤度 |
| 可视化 | 三图联动 + IC热力图 + 多品种看板 |
| 预警能力 | 失效预警 + 拥挤度告警 |
| 知识积累 | 失效事件库 ≥ 5条 |

---

> **下一步行动**：执行 Phase 0 Step 0.1，运行 `audit_factor_data.py` 开始数据审计
