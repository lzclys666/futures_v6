# CSV DATA CONTRACT — 宏观评分输出契约

> **版本**: v1.0  
> **日期**: 2026-05-02  
> **Owner**: YIYI (因子分析师)  
> **变更控制**: 修改列定义须通知所有 Consumer

---

## 1. 概述

本契约定义 `daily_scoring.py` 输出的 CSV 文件格式，是宏观评分引擎与下游消费者之间的数据边界。

**生产路径**: `D:\futures_v6\macro_engine\output\{SYMBOL}_macro_daily_{YYYYMMDD}.csv`

**输出频率**: 每日 14:30（Windows 计划任务 `FuturesMacro_DailyScoring`）

---

## 2. 列定义（16列）

| # | 列名 | 类型 | 说明 | 示例 |
|---|------|------|------|------|
| 1 | `symbol` | string | 品种代码 | `AG` |
| 2 | `date` | date | 评分日期 | `2026-05-01` |
| 3 | `rowType` | enum | 行类型：`SUMMARY` 或 `FACTOR` | `SUMMARY` |
| 4 | `compositeScore` | float | 综合评分 [-1, 1] | `0.0325` |
| 5 | `direction` | enum | 方向：`LONG` / `SHORT` / `NEUTRAL` | `NEUTRAL` |
| 6 | `factorCount` | int | 参与评分的因子数量 | `13` |
| 7 | `updatedAt` | iso8601 | 评分时间戳 | `2026-05-01T14:30:02+08:00` |
| 8 | `engineVersion` | string | 引擎版本 | `d_engine_v1.0` |
| 9 | `factorCode` | string | 因子代码（FACTOR行有值） | `AG_FUT_CLOSE` |
| 10 | `factorName` | string | 因子名称（FACTOR行有值） | `期货收盘价` |
| 11 | `rawValue` | float | 原始值（FACTOR行有值） | `8325.0` |
| 12 | `normalizedScore` | float | 标准化得分（FACTOR行有值） | `1.4075` |
| 13 | `weight` | float | IC驱动权重（FACTOR行有值） | `0.082` |
| 14 | `contribution` | float | 贡献度（FACTOR行有值） | `0.1154` |
| 15 | `contributionPolarity` | int | 贡献极性：+1/-1（FACTOR行有值） | `1` |
| 16 | `icValue` | float | IC值（FACTOR行有值，数据不足时为0.0） | `-0.402` |

---

## 3. 行类型规则

### SUMMARY 行（每品种1行）
- 列 1-8 有值
- 列 9-16 为空

### FACTOR 行（每品种 N 行，N = factorCount）
- 列 1-2 与 SUMMARY 相同
- 列 3 固定为 `FACTOR`
- 列 4-8 为空
- 列 9-16 有值

**每个品种的 CSV 包含 1 行 SUMMARY + N 行 FACTOR**

---

## 4. 下游消费者（3个）

| Consumer | 使用方式 | 关注列 | 负责人 |
|----------|----------|--------|--------|
| **FastAPI** (`macro_api_server.py`) | 读取最新 CSV，暴露 `/api/macro/signal/*` | 全部16列 | deep |
| **VNpy 策略** (`macro_demo_strategy.py`) | 读取最新 CSV 的 SUMMARY 行 | symbol, direction, compositeScore | deep |
| **前端** (`SignalChart`, `FactorCard`) | 通过 API 间接消费 | factorCode, normalizedScore, icValue, weight | Lucy |

---

## 5. 约束与保证

1. **不可变性**: CSV 一旦写入不可修改（append-only 日期文件名）
2. **编码**: UTF-8 无 BOM
3. **换行符**: CRLF (Windows 环境)
4. **数值精度**: float 保留 4 位小数
5. **缺失值**: 空字符串（不使用 NULL/NaN）
6. **文件名格式**: 严格 `{SYMBOL}_macro_daily_{YYYYMMDD}.csv`
7. **日终告警**: 当 factorCount 中 >80% 的因子 icValue=0.0 时，应触发质量告警（NEW-2 待开发）

---

## 6. 变更历史

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|----------|------|
| 2026-05-02 | v1.0 | 初始版本，16列定义 | 项目经理 |
