# PB（沪铅）因子采集

**品种：** 沪铅（Lead）  
**品种代码：** PB  
**交易所：** SHFE（上海期货交易所）

---

## 采集因子列表

| 因子代码 | 因子名称 | 数据层 | 数据源 | 状态 |
|---------|---------|--------|--------|------|
| PB_FUT_CLOSE | 沪铅期货收盘价 | L1 | AKShare `futures_main_sina PB0` | ✅ 正常 |
| PB_FUT_OI | 沪铅期货持仓量 | L1 | AKShare `futures_main_sina PB0` | ✅ 正常 |
| PB_PB_SPT_SMM | SMM沪铅现货价格 | L4 Stub | 付费订阅: SMM | ⚠️ 待配 |
| PB_PB_SPD_PRI_VIRGIN | 原生/再生铅价差 | L4 Stub | 付费订阅: SMM/隆众 | ⚠️ 待配 |
| PB_PB_SPD_BASIS | 沪铅期现基差 | L4 Stub | SHFE/沪铅现货待验证 | ⚠️ 待配 |
| PB_PB_POS_NET | 上期所前20净持仓 | L4 Stub | SHFE接口待验证 | ⚠️ 待配 |
| PB_PB_SPD_NEAR_FAR | 沪铅近远月价差 | L4 Stub | SHFE接口待验证 | ⚠️ 待配 |
| PB_PB_FX_USDCNY | 美元兑人民币汇率 | L4 Stub | L1已由其他品种采集 | ⚠️ 待配 |
| PB_PB_MACRO_TC | 铅矿加工费 | L4 Stub | 付费订阅: SMM | ⚠️ 待配 |
| PB_PB_STK_BATTERY_RATE | 铅酸蓄电池开工率 | L4 Stub | 付费订阅: 隆众/卓创 | ⚠️ 待配 |
| PB_PB_STK_WARRANT | 上期所沪铅仓单 | L4 Stub | SHFE接口待验证 | ⚠️ 待配 |
| PB_PB_STK_SOCIAL | 铅锭社会库存 | L4 Stub | 付费订阅: SMM | ⚠️ 待配 |

---

## 脚本说明

### 入口脚本

| 脚本 | 说明 | 运行状态 |
|------|------|---------|
| `PB_run_all.py` | 调度所有PB因子脚本，支持 `--auto` 参数 | ✅ 正常 |

### 因子脚本（L1 - 免费源）

| 脚本 | 说明 | 范式符合 | 运行状态 |
|------|------|---------|---------|
| `PB_沪铅期货收盘价.py` | 通过AKShare获取沪铅期货PB0收盘价，写入DB | ⚠️ 缺类型注解 | ✅ 正常 |
| `PB_沪铅期货持仓量.py` | 通过AKShare获取沪铅期货PB0持仓量，写入DB | ⚠️ 缺类型注解 | ✅ 正常 |

### 因子脚本（L4 Stub - 付费待配）

| 脚本 | 说明 | 范式符合 |
|------|------|---------|
| `PB_SMM沪铅现货价格.py` | Stub：付费订阅SMM，待接入 | ⚠️ Header待完善 |
| `PB_原生铅与再生铅价差.py` | Stub：付费订阅SMM/隆众，待接入 | ⚠️ Header待完善 |
| `PB_沪铅期现基差.py` | Stub：SHFE现货待验证，待接L2/L3 | ⚠️ Header待完善 |
| `PB_沪铅期货净持仓.py` | Stub：SHFE接口待验证，待接L2/L3 | ⚠️ Header待完善 |
| `PB_沪铅期货近远月价差.py` | Stub：SHFE接口待验证，待接L2/L3 | ⚠️ Header待完善 |
| `PB_美元兑人民币汇率.py` | Stub：汇率因子，建议引用其他品种已有数据 | ⚠️ Header待完善 |
| `PB_铅TC加工费.py` | Stub：付费订阅SMM，待接入 | ⚠️ Header待完善 |
| `PB_铅酸电池用铅占比.py` | Stub：付费订阅隆众/卓创，待接入 | ⚠️ Header待完善 |
| `PB_铅锭仓单库存.py` | Stub：SHFE仓单接口待验证，待接L2/L3 | ⚠️ Header待完善 |
| `PB_铅锭社会库存.py` | Stub：付费订阅SMM，待接入 | ⚠️ Header待完善 |

---

## 数据输出

- **数据库：** `D:\futures_v6\macro_engine\pit_data.db`（`pit_factor_observations` 表）
- **日志目录：** `D:\futures_v6\macro_engine\crawlers\logs\`
- **输出格式：** 直接写入SQLite DB，无中间CSV文件

---

## 最近运行记录

```
PB Start @ 2026-05-02 01:04:37
--- PB_沪铅期货收盘价.py ---
[DB] 写入成功: PB_FUT_CLOSE = 16630.0
[L1] PB_FUT_CLOSE=16630.0 (2026-04-30) done

--- PB_沪铅期货持仓量.py ---
[DB] 写入成功: PB_FUT_OI = 63295.0
[L1] PB_FUT_OI=63295.0 (2026-04-30) done

[Done] 2/2
```

---

## 待办事项

| 优先级 | 事项 |
|--------|------|
| P0 | `PB_run_all.py` 补全11个Stub脚本至调度列表 |
| P1 | 11个Stub脚本补充L2/L3免费数据源验证（四层漏斗） |
| P1 | 所有脚本补函数类型注解 `-> int` |
| P2 | 修复子进程日志中文乱码 |
| P3 | 期现基差接入SHFE现货价格（免费） |

---

**最后更新时间：** 2026-05-02  
**负责人：** 程序员mimo
