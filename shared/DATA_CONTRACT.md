# 数据契约 — CSV文件格式定义

> **版本**: v1.0  
> **生效日期**: 2026-05-01  
> **Owner**: YIYI  
> **状态**: 初始版本

---

## 一、文件命名规范

```
{symbol}_macro_daily_{YYYYMMDD}.csv

示例:
- RU_macro_daily_20260501.csv
- CU_macro_daily_20260501.csv
```

**文件位置**: `D:\futures_v6\macro_engine\output\`

---

## 二、列定义（v1.0）

| # | 列名 | 数据类型 | 说明 | 适用行类型 |
|---|------|---------|------|-----------|
| 1 | symbol | string | 品种代码（RU/CU/AU/AG/ZN等） | SUMMARY + FACTOR |
| 2 | date | string | 日期，格式 YYYY-MM-DD | SUMMARY + FACTOR |
| 3 | rowType | string | `SUMMARY`=汇总行，`FACTOR`=因子行 | SUMMARY + FACTOR |
| 4 | compositeScore | float | 综合得分，范围 -1.0 ~ +1.0 | SUMMARY |
| 5 | direction | string | `LONG`/`NEUTRAL`/`SHORT` | SUMMARY |
| 6 | factorCount | int | 有效因子数量 | SUMMARY |
| 7 | updatedAt | string | 引擎时间，ISO8601格式 | SUMMARY + FACTOR |
| 8 | engineVersion | string | 引擎版本标识，格式 `d_engine_v1.0` | SUMMARY + FACTOR |
| 9 | factorCode | string | 因子代码，如 `RU_TS_ROLL_YIELD` | FACTOR |
| 10 | factorName | string | 因子中文名 | FACTOR |
| 11 | rawValue | float | 因子原始值 | FACTOR |
| 12 | normalizedScore | float | 标准化得分 | FACTOR |
| 13 | weight | float | 因子权重，范围 0.0 ~ 1.0 | FACTOR |
| 14 | contribution | float | 因子对综合得分的贡献度 | FACTOR |
| 15 | contributionPolarity | string | `positive`/`negative`/`neutral` | FACTOR |
| 16 | icValue | float | 因子IC值，可为0 | FACTOR |

---

## 三、行类型说明

### SUMMARY行（汇总行）
每个CSV文件**有且仅有1行** SUMMARY，表示该品种当日的宏观信号。

### FACTOR行（因子行）
每个有效因子**1行**，包含该因子的详细分解数据。

**文件结构示例**：
```
symbol,date,rowType,compositeScore,direction,...
RU,2026-05-01,SUMMARY,0.45,LONG,...
RU,2026-05-01,FACTOR,0.45,LONG,...（因子1）
RU,2026-05-01,FACTOR,0.45,LONG,...（因子2）
RU,2026-05-01,FACTOR,0.45,LONG,...（因子3）
```

---

## 四、版本变更规则

### 轻微变更（v1.x）— 无需投票
- 在末尾新增列
- 新增因子代码（新增FACTOR行）

### 重大变更（v2.0）— 需要L2技术议会表决
- 删除已有列
- 修改列的数据类型
- 修改列的顺序
- 修改已有列的名称

### 升级版本号时的操作
1. 在本文档顶部更新版本号和生效日期
2. 在 `decisions_log.md` 中记录变更原因
3. 通知所有读取方（deep/Lucy/VNpy策略）

---

## 五、读写权限

| 模块 | 读 | 写 | 说明 |
|------|---|---|------|
| factor_collector_main.py | — | ✅ 写入 | 唯一写入方 |
| macro_scoring_engine.py | ✅ | ✅ 追加因子行 | 读取+处理 |
| VNpy策略 (PaperBridge) | ✅ | — | 只读，禁止写 |
| macro_api_server.py | ✅ | — | 只读 |
| 前端 (api/macro.ts) | 通过API间接读取 | — | 不直接读CSV |

---

## 六、已知读取方

| 读取方 | 读取方式 | 依赖列 |
|--------|---------|--------|
| macro_scoring_engine.py | pandas.read_csv | 全部 |
| VNpy策略 (PaperBridge) | pandas.read_csv | symbol, date, rowType, compositeScore, direction |
| macro_api_server.py | pandas.read_csv | 全部 |

---

## 七、版本历史

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-05-01 | 初始版本，16列定义 |
