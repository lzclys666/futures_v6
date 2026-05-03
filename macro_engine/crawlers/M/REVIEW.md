# M（豆粕）因子采集脚本复查报告

**复查时间**: 2026-05-02 09:47  
**复查人**: mimo  
**工作目录**: `D:\futures_v6\macro_engine\crawlers\M\`

---

## 一、脚本清单

| # | 脚本名 | 状态 |
|---|--------|------|
| 1 | `M_run_all.py` | 🔧 入口脚本 |
| 2 | `M_抓取库存.py` | ✅ 已运行 |
| 3 | `M_抓取期货持仓.py` | ✅ 已运行 |
| 4 | `M_抓取现货和基差.py` | ✅ 已运行 |
| 5 | `M_抓取仓单.py` | ⏸️ stub（永久跳过） |
| 6 | `M_计算近远月价差.py` | ✅ 已运行 |
| 7 | `M_计算比价.py` | ⚠️ 未纳入batch |

---

## 二、范式检查结果

### ✅ 通过项（所有脚本）

- 脚本头部有 docstring
- 数据直写数据库（`save_to_db`），无 CSV 输出需求
- 无硬编码中文文件名
- 有 L4 历史回补兜底逻辑
- `except Exception as e` 形式（非 bare except）

### ⚠️ 通用问题（全部 6 个采集脚本 + 入口脚本）

| 问题 | 说明 | 严重度 |
|------|------|--------|
| **无类型注解** | 所有 `main()` 和子函数无 `-> None`/`-> int` 等返回类型注解 | ⚠️ 中 |
| **无标准 logging** | 仅用 `print()`，无 `logging.INFO/ERROR` | ⚠️ 中 |
| **AKShare 无 timeout** | `akshare` 调用未传 `timeout=N` 参数 | ⚠️ 中 |
| **魔法数字** | `M_run_all.py` 中 `timeout=60` 硬编码 | ⚠️ 低 |

### ❌ 逐脚本问题

#### M_run_all.py（入口脚本）
- `run_script()` / `main()` 无类型注解
- `timeout=60` 硬编码为魔法数字，应提取为常量
- 仅 `print`，无 `logging`
- **SCRIPTS 清单遗漏 `M_计算比价.py`**

#### M_抓取库存.py
- `akshare.futures_inventory_em()` 无 `timeout`
- `main()` 无类型注解
- 仅 `print`，无 `logging`
- **因子命名问题**：保存为 `M_STK_WARRANT`，但因子本意是库存，仓单已在 `M_抓取仓单.py` 中定义，两者因子代码重复

#### M_抓取期货持仓.py
- `akshare.futures_main_sina()` 无 `timeout`
- `main()` 无类型注解
- 仅 `print`，无 `logging`

#### M_抓取现货和基差.py
- `akshare.futures_spot_price()` 无 `timeout`
- `main()` 无类型注解
- 仅 `print`，无 `logging`

#### M_抓取仓单.py
- stub 脚本，永久跳过（CZCE 仓单制度不适用于 DCE 豆粕）✅ 设计合理
- 标注了永久跳过原因：`厂库交割制度`

#### M_计算近远月价差.py
- 两处 `akshare.futures_main_sina()` 无 `timeout`
- `main()` 无类型注解
- 仅 `print`，无 `logging`
- L1/L2 两层漏斗设计合理 ✅

#### M_计算比价.py
- **未列入 `M_run_all.py` 的 SCRIPTS 清单** — batch 运行不覆盖此脚本
- `akshare.futures_spot_price()` 无 `timeout`
- `main()` 无类型注解
- 仅 `print`，无 `logging`
- 独立运行时 RU 数据因非交易日失败（退出码 1），回退 L4

---

## 三、运行验证结果

```
==================================================
开始执行 M 数据采集 @ 2026-05-02 09:47:05.817224
待执行脚本数: 5
==================================================
>> 运行 M_抓取现货和基差.py...
    (auto) === M现货 === obs=2026-05-01
    >>> M_BASIS_SPOT_FUTURES=2996.0 L4回补成功
[OK] M_抓取现货和基差.py done

>> 运行 M_抓取期货持仓.py...
    (auto) === M持仓 === obs=2026-05-01
    >>> M_POS_NET=2493483.0 写入成功
[OK] M_抓取期货持仓.py done

>> 运行 M_抓取库存.py...
    (auto) === M库存 === obs=2026-05-01
    >>> M_STK_WARRANT=32080.0 写入成功
[OK] M_抓取库存.py done

>> 运行 M_抓取仓单.py...
    === M_STK_WARRANT === obs=2026-05-01
    [永久跳过] CZCE豆粕(M)无免费仓单数据（厂库交割制度）
    M_STK_WARRANT: SKIP(无免费源)
[OK] M_抓取仓单.py done

>> 运行 M_计算近远月价差.py...
    (auto) === M近远月价差 === obs=2026-05-01
    >>> M_SPD_NEAR_FEAR=-4.0 写入成功
[OK] M_计算近远月价差.py done

==================================================
M 数据采集完成  耗时:10.3s  成功:5/5
==================================================
```

**M_计算比价.py 单独运行**（不在 batch 清单中）：
```
(auto) === M比价 === obs=2026-05-01
>>> M_SPD_NEAR_FAR=0.0 L4回补成功
(Command exited with code 1)
```

---

## 四、核心结论

### 🔴 严重问题

1. **M_计算比价.py 未纳入 batch**：`M_run_all.py` 的 `SCRIPTS` 列表缺少此脚本，导致批量运行永远不采集 `M_SPD_NEAR_FAR`（豆粕/橡胶比价）因子

### ⚠️ 需改进（全部脚本共同问题）

1. **AKShare 无 timeout**：网络抖动时可能长时间阻塞，应统一加 `timeout=30`
2. **无标准 logging**：生产环境无法按级别过滤日志，应统一替换 `print()` 为 `logging.info/error`
3. **无类型注解**：Python 最佳实践要求函数有类型注解

### ✅ 良好设计

1. **M_抓取仓单.py**：正确识别 DCE 品种无需 CZCE 仓单数据，永久跳过而非硬写无效值
2. **M_计算近远月价差.py**：L1→L2 双层漏斗 + L4 回补，设计完整
3. **所有脚本**：L4 历史回补逻辑统一，防止空值

---

## 五、修复建议优先级

| 优先级 | 动作 | 涉及脚本 |
|--------|------|---------|
| **P0** | 将 `M_计算比价.py` 加入 `M_run_all.py` 的 SCRIPTS | M_run_all.py |
| **P1** | 给所有 `akshare` 调用加 `timeout=30` | 全部 5 个采集脚本 |
| **P1** | 将 `print()` 替换为 `logging.info/error` | 全部 6 个脚本 |
| **P2** | 添加函数类型注解 | 全部 6 个脚本 |
| **P2** | 审查 `M_抓取库存.py` 因子命名（`M_STK_WARRANT` vs `M_STK_INVENTORY`） | M_抓取库存.py |

---

_复查完成 | 复查人: mimo | 时间: 2026-05-02_
