# TA 因子采集脚本复查报告

**复查时间:** 2026-05-02 10:14
**复查人:** 程序员mimo
**工作目录:** `D:\futures_v6\macro_engine\crawlers\TA\`

---

## 一、脚本清单与检查结果

| # | 脚本名 | 状态 | 主要问题 |
|---|--------|------|----------|
| 1 | `TA_run_all.py` | ⚠️ 有问题 | 成功率判断逻辑误判永久跳过脚本 |
| 2 | `TA_抓取汇率.py` | ⛔ 语法错误 | IndentationError + 缺失函数定义和导入 |
| 3 | `TA_抓取BRENT价格.py` | ✅ 通过 | 符合范式 |
| 4 | `TA_抓取PTA库存.py` | ✅ 通过 | 符合范式 |
| 5 | `TA_抓取社会库存.py` | ✅ 通过 | 符合范式（与TA_抓取PTA库存.py写入同一因子TA_STK_SOCIAL） |
| 6 | `TA_抓取郑商所仓单.py` | ✅ 通过 | 符合范式 |
| 7 | `TA_抓取期货持仓.py` | ✅ 通过 | 符合范式 |
| 8 | `TA_抓取PX价格.py` | ⏸️ 永久跳过 | 无免费数据源，正确返回0 |
| 9 | `TA_抓取PTA成本.py` | ⏸️ 永久跳过 | 无免费数据源，正确返回0 |
| 10 | `TA_抓取PTA开工率.py` | ⏸️ 永久跳过 | 无免费数据源，正确返回0 |
| 11 | `TA_抓取聚酯开工率.py` | ⏸️ 永久跳过 | 无免费数据源，正确返回0 |
| 12 | `TA_批次2_手动输入.py` | ✅ 逻辑正确 | 输出`[永久跳过]`导致run_all误判FAIL |
| 13 | `TA_计算基差.py` | ✅ 通过 | 符合范式 |

**运行结果:** 5/11 成功（5个永久跳过脚本被误判为FAIL）

---

## 二、逐项范式检查

### 1. TA_run_all.py — ⚠️ 有问题

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 脚本头部docstring | ✅ | 有 |
| try-except错误处理 | ✅ | 有 |
| timeout设置 | ✅ | 60秒 |
| 日志记录 | ⚠️ | 仅print，无标准logging |
| 成功率判断逻辑 | ⛔ | 缺陷：永久跳过脚本输出`[永久跳过]`而非OK标记，被误判为FAIL |
| 输出路径 | N/A | 不写CSV |

**问题详情:**
- `run_script()` 函数的 `ok_markers` 列表不包含"永久跳过"，导致永久跳过脚本被报告为 `[FAIL]`
- 实际上脚本返回码为0（正确退出），只是输出内容与成功标记不匹配

---

### 2. TA_抓取汇率.py — ⛔ 语法错误（无法运行）

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 脚本头部docstring | ⚠️ | 有，但Header不完整（缺数据源说明） |
| try-except错误处理 | N/A | 代码结构已损坏 |
| 网络timeout | N/A | 代码结构已损坏 |
| 魔法数字常量 | N/A | 未定义 |
| 函数类型注解 | ❌ | 无函数定义 |
| 日志记录 | ❌ | 无标准日志 |
| 导入语句 | ❌ | 缺失：`requests`, `ensure_table`, `save_to_db`, `get_pit_dates`, `get_latest_value`, `SYMBOL` 均未导入 |

**严重问题:**
- 第17行起出现 `IndentationError: unexpected indent`
- 原因：脚本中 `fetch_usd_cny_sina()` 和 `fetch_usd_cny_qq()` 函数定义完全缺失
- 第17-28行的 `try/except` 块没有附属于任何函数定义，Python解析器在模块顶层遇到缩进的 `try:` 块而报缩进错误
- `main()` 函数中调用的 `fetch_usd_cny_sina()`、`fetch_usd_cny_qq()`、`SYMBOL` 均未定义

**修复建议:** 补全两个函数定义和缺失的import语句。

---

### 3. TA_抓取BRENT价格.py — ✅ 通过

| 检查项 | 结果 |
|--------|------|
| 脚本头部docstring | ✅ 完整 |
| try-except错误处理 | ✅ 每层独立try-except |
| 网络timeout | ✅ 10秒 |
| 魔法数字常量 | ✅ MIN_VALUE/MAX_VALUE |
| 函数类型注解 | ✅ 有类型注解 |
| 日志记录 | ✅ INFO/ERROR级别print |
| 输出路径 | ✅ 通过save_to_db写入DB |
| 无硬编码中文文件名 | ✅ 不涉及文件输出 |

**Header状态:** ⚠️待修复（Header注明"需补充数据源尝试记录"）

---

### 4. TA_抓取PTA库存.py — ✅ 通过

| 检查项 | 结果 |
|--------|------|
| 脚本头部docstring | ✅ |
| try-except错误处理 | ✅ |
| 网络timeout | ✅ AKShare内部处理 |
| 魔法数字常量 | N/A 无需常量 |
| 函数类型注解 | ⚠️ `fetch()`无类型注解 |
| 日志记录 | ✅ |
| 输出路径 | ✅ save_to_db |

**问题:** `fetch()` 函数缺少返回类型注解 `-> Optional[float]:`

---

### 5. TA_抓取社会库存.py — ✅ 通过

| 检查项 | 结果 |
|--------|------|
| 脚本头部docstring | ✅ |
| try-except错误处理 | ✅ |
| 网络timeout | ✅ |
| 魔法数字常量 | N/A |
| 函数类型注解 | ⚠️ `fetch()`无类型注解 |
| 日志记录 | ✅ |

**注意:** 此脚本与 `TA_抓取PTA库存.py` 都写入因子 `TA_STK_SOCIAL`，数据源相同（`akshare_futures_inventory_em`），存在冗余。

---

### 6. TA_抓取郑商所仓单.py — ✅ 通过

| 检查项 | 结果 |
|--------|------|
| 脚本头部docstring | ✅ |
| try-except错误处理 | ✅ 每层独立try-except |
| 网络timeout | ✅ AKShare内部 |
| 魔法数字常量 | N/A |
| 函数类型注解 | ✅ |
| 日志记录 | ✅ 完善 |
| 输出路径 | ✅ save_to_db |

---

### 7. TA_抓取期货持仓.py — ✅ 通过

| 检查项 | 结果 |
|--------|------|
| 脚本头部docstring | ✅ |
| try-except错误处理 | ✅ |
| 网络timeout | ✅ AKShare内部 |
| 魔法数字常量 | ✅ MIN_VALUE/MAX_VALUE |
| 函数类型注解 | ✅ |
| 日志记录 | ✅ |
| 输出路径 | ✅ save_to_db |

---

### 8-11. 永久跳过脚本（PX价格/PTA成本/PTA开工率/聚酯开工率）— ⏸️ 正确跳过

这4个脚本均正确实现：auto模式下打印跳过信息并返回0。但被 `run_all.py` 误判为FAIL。

---

### 12. TA_批次2_手动输入.py — ✅ 逻辑正确（被误判）

| 检查项 | 结果 |
|--------|------|
| 脚本逻辑 | ✅ 正确实现永久跳过 |
| 输出标记 | ⚠️ 输出`[永久跳过]`而非标准OK标记 |
| run_all误判 | 因输出不含成功标记被报告为FAIL |

---

### 13. TA_计算基差.py — ✅ 通过

| 检查项 | 结果 |
|--------|------|
| 脚本头部docstring | ✅ |
| try-except错误处理 | ✅ |
| 网络timeout | ✅ AKShare内部 |
| 魔法数字常量 | ✅ 合理范围-200~200 |
| 函数类型注解 | ✅ |
| 日志记录 | ✅ |
| 输出路径 | ✅ save_to_db |

---

## 三、运行日志

```
==================================================
TA PTA 数据采集 @ 2026-05-02 10:14:17
==================================================
  [OK]   TA_抓取PTA库存.py
  [OK]   TA_抓取郑商所仓单.py
  [OK]   TA_抓取期货持仓.py
  [FAIL] TA_抓取汇率.py          ← IndentationError
  [OK]   TA_抓取BRENT价格.py
  [FAIL] TA_抓取PX价格.py        ← 被误判（永久跳过脚本，输出无OK标记）
  [FAIL] TA_抓取PTA成本.py       ← 被误判（同上）
  [FAIL] TA_抓取聚酯开工率.py     ← 被误判（同上）
  [FAIL] TA_抓取PTA开工率.py     ← 被误判（同上）
  [FAIL] TA_批次2_手动输入.py    ← 被误判（同上）
  [OK]   TA_计算基差.py
==================================================
完成: 5/11  耗时:23.5s
==================================================
```

**实际成功:** `TA_抓取PTA库存.py`、`TA_抓取郑商所仓单.py`、`TA_抓取期货持仓.py`、`TA_抓取BRENT价格.py`、`TA_计算基差.py` = 5个脚本真正成功
**因误判被标FAIL:** 5个永久跳过脚本 + 1个语法错误脚本

---

## 四、问题汇总

| 优先级 | 问题 | 脚本 |
|--------|------|------|
| P0 | 语法错误，脚本完全无法运行 | `TA_抓取汇率.py` |
| P1 | `run_all.py` 成功率判断逻辑缺陷，永久跳过脚本被误判 | `TA_run_all.py` |
| P2 | Header不完整（注明"需补充"） | 多个脚本 |
| P3 | `fetch()` 函数缺少类型注解 | `TA_抓取PTA库存.py`, `TA_抓取社会库存.py` |
| P3 | 社会库存与PTA库存脚本重复（同一因子同一数据源） | `TA_抓取社会库存.py` |

---

## 五、修复建议

### P0: TA_抓取汇率.py 修复

```python
# 需补充完整函数定义和导入
import requests
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

SYMBOL = "TA"

def fetch_usd_cny_sina():
    """L1: 新浪财经美元人民币汇率"""
    try:
        r = requests.get(
            'https://hq.sinajs.cn/rn=ot&list=USDCNY',
            headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn'},
            timeout=10
        )
        r.encoding = 'gbk'
        # ... parse logic
    except Exception as e:
        print(f"  [L1] 新浪汇率失败: {e}")
    return None

def fetch_usd_cny_qq():
    """L2: 腾讯财经美元人民币汇率"""
    # 同上，补全try-except块
```

### P1: TA_run_all.py 成功率判断

在 `ok_markers` 列表中加入：
```python
ok_markers = ["写入成功", "DB", "[OK]", "OK:", "完成", "永久跳过", "[跳过]"]
```

---

## 六、README.md 更新内容

见下一节。

---

_复查完成 | 2026-05-02 10:14 | 程序员mimo_
