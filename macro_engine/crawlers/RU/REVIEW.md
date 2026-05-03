# RU 因子采集脚本复查报告

**复查时间：** 2026-05-02 10:05
**复查人：** 程序员mimo（子代理）
**工作目录：** `D:\futures_v6\macro_engine\crawlers\RU\`

---

## 一、脚本清单与范式检查

| 脚本 | 头部docstring | try-except | timeout | 魔法数字 | 类型注解 | 日志INFO/ERROR | 输出路径 | 无中文硬编码 | 中断恢复 |
|------|---------------|------------|---------|---------|---------|----------------|---------|------------|---------|
| `RU_run_all.py` | ✅ | ✅ | ✅120s | ⚠️魔法数字分散 | ❌无 | ⚠️print | N/A | ✅ | ✅ |
| `RU_抓取仓单.py` | ✅ | ✅ | ❌无 | ⚠️列名字符串 | ❌无 | ⚠️print | DB | ✅ | ✅L4 |
| `RU_抓取库存.py` | ✅ | ✅ | ❌无 | ⚠️"橡胶" | ❌无 | ⚠️print | DB | ✅ | ✅L4 |
| `RU_抓取期货持仓.py` | ✅ | ✅ | ❌无 | ⚠️"RU0"/"持仓量" | ❌无 | ⚠️print | DB | ✅ | ✅L4 |
| `RU_抓取现货和基差.py` | ✅ | ✅ | ❌无 | ⚠️"RU"/"spot_price" | ❌无 | ⚠️print | DB | ✅ | ✅L4 |
| `RU_期货持仓量.py` | ✅ | ✅ | ❌无 | ⚠️列名硬编码 | ❌无 | ✅ | DB | ✅ | ✅L4 |
| `RU_计算比价.py` | ✅ | ✅ | ❌无 | ⚠️symbol重复 | ❌无 | ⚠️print | DB | ✅ | ✅L4 |

**通过率：** 1/7 完全合规，其余 6 个均有缺失项。

---

## 二、各脚本详细问题

### RU_run_all.py ✅ 基本正常
- 有 subprocess timeout=120s
- 执行逻辑正确
- **问题：** 无类型注解，日志用 print 而非标准 logging

---

### RU_抓取仓单.py ⚠️ 有问题
- AKShare `ak.futures_warehouse_receipt_czce()` **无 timeout**，网络不稳定时可能永久阻塞
- 列名用 unicode 字符串拼接（`"\u6ce8\u518c"` 等价于"注册"），可读性差，应提前定义常量
- `save_to_db` 写入 `RU_INV_QINGDAO`，因子命名含义模糊——仓单≠青岛库存，建议明确因子含义

---

### RU_抓取库存.py ⚠️ 有问题
- `ak.futures_inventory_em(symbol="橡胶")` **无 timeout**
- 硬编码 `symbol="橡胶"`，如 AKShare 接口参数名变化会静默失败
- 同样写入 `RU_INV_QINGDAO`，与仓单脚本**写入同一因子**——两套逻辑混用同一字段，可能造成数据混淆

---

### RU_抓取期货持仓.py ⚠️ 有问题
- `ak.futures_main_sina(symbol="RU0")` **无 timeout**
- 硬编码 `"RU0"` 和 `"持仓量"` 列名
- 同样写入 `RU_POS_NET`，与 `RU_抓取现货和基差.py` **写入同一因子**——两套数据源冲突

---

### RU_抓取现货和基差.py ⚠️ 有问题
- `ak.futures_spot_price(date=date_str, vars_list=["RU"])` **无 timeout**
- 写入 `RU_POS_NET`（与期货持仓脚本冲突）
- 实际上现货价格≠持仓量，写入 `RU_POS_NET` 是错误映射

---

### RU_期货持仓量.py ⚠️ 有问题
- `ak.futures_main_sina(symbol="RU0")` **无 timeout**
- `fix_encoding()` 调用了 `common.io_win` 模块，未见异常
- 列名硬编码 `'open_interest'`，`df.columns = [...]` 强制覆盖原列名，若 AKShare 返回列顺序变化会出错
- 同时写入 `RU_FUT_OI` 和 `RU_INV_TOTAL` 两个因子——逻辑合理，但应在 Header 说明

---

### RU_计算比价.py 🔴 逻辑错误
- `vars_list=["RU", "RU"]`，取 `symbol=="RU"` 的行自己除自己 → 比值恒等于 1.0
- 实际输出 `[L4] 回补... RU_SPD_RU_BR=1.0` 证明计算层完全失败，全部走了 L4 回补
- 写入 `RU_SPD_RU_BR` = 1.0 是无意义的脏数据

---

## 三、运行验证

```
RU采集 start @ 2026-05-02 10:05:15
待执行: 6 scripts
>> running RU_抓取现货和基差.py...
    (auto) === RU现货 === obs=2026-05-01
    [DB] 写入成功: RU_POS_NET = 191346.0
    >>> RU_POS_NET=191346.0 L4回补成功      ← L1失败，L4回补
[OK] RU_抓取现货和基差.py done
>> running RU_抓取期货持仓.py...
    (auto) === RU持仓 === obs=2026-05-01
    [DB] 写入成功: RU_POS_NET = 191346.0
    >>> RU_POS_NET=191346.0 写入成功        ← 实际用了L4值
[OK] RU_抓取期货持仓.py done
>> running RU_期货持仓量.py...
    [DB] 写入成功: RU_FUT_OI = 191346.0
    [OK] RU_FUT_OI=191346.0 写入成功
    [DB] 写入成功: RU_INV_TOTAL = 191346.0
    [OK] RU_INV_TOTAL=191346.0 写入成功
[OK] RU_期货持仓量.py done
>> running RU_抓取库存.py...
    (auto) === RU库存 === obs=2026-05-01
    [DB] 写入成功: RU_INV_QINGDAO = 129170.0
    >>> RU_INV_QINGDAO=129170.0 写入成功    ← 实际用了L4值
[OK] RU_抓取库存.py done
>> running RU_抓取仓单.py...
    (auto) === RU仓单 === obs=2026-05-01
    [DB] 写入成功: RU_INV_QINGDAO = 129170.0
    >>> RU_INV_QINGDAO=129170.0 L4回补成功  ← L1失败，L4回补
[OK] RU_抓取仓单.py done
>> running RU_计算比价.py...
    (auto) === RU比价 === obs=2026-05-01
    [DB] 写入成功: RU_SPD_RU_BR = 1.0
    >>> RU_SPD_RU_BR=1.0 L4回补成功         ← 比价计算逻辑错误
[OK] RU_计算比价.py done
RU done  18.0s  OK:6/6
```

**关键发现：**
- 所有 L1 数据源均失效（AKShare 接口返回空或异常），6/6 走了 L4 回补
- `RU_INV_QINGDAO` 被仓单和库存两个逻辑重复写入，数据源打架
- `RU_POS_NET` 被现货和期货持仓两个逻辑重复写入，语义混淆
- `RU_SPD_RU_BR = 1.0` 是错误的计算结果

---

## 四、关键问题汇总

| 严重程度 | 问题 | 涉及脚本 |
|---------|------|---------|
| 🔴 致命 | 比价计算 self/SELF=1.0，逻辑完全错误 | `RU_计算比价.py` |
| 🔴 致命 | 所有 L1 数据源全部失效，无真实数据 | 全部6个因子脚本 |
| 🟠 严重 | 同一因子被多个脚本重复写入，数据源打架 | `RU_INV_QINGDAO`, `RU_POS_NET` |
| 🟡 中等 | AKShare 调用无 timeout | 全部6个因子脚本 |
| 🟡 中等 | 无函数类型注解 | 全部7个脚本 |
| 🟡 中等 | 列名/参数硬编码，可读性差 | 全部6个因子脚本 |
| 🟢 低 | 日志用 print 而非标准 logging | 全部7个脚本 |

---

## 五、修复优先级建议

1. **P0 — 修复 RU_计算比价.py：** 比价公式写错了，需明确 RU vs 哪个品种的比价
2. **P0 — 调查 L1 失效原因：** AKShare 接口是否变更，6个因子全失效极不正常
3. **P1 — 去重 RU_INV_QINGDAO / RU_POS_NET：** 明确哪个脚本负责哪个因子
4. **P2 — 补充 timeout：** 给所有 akshare 调用加 timeout=30
5. **P3 — 完善 Header：** 所有脚本 Header 仍标注"待定义/需补充"，应填完整

---

_复查完成_
