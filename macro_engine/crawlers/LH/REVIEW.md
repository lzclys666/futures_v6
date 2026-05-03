# LH（生猪）因子采集脚本复查报告

**复查时间**: 2026-05-02 09:45 GMT+8  
**工作目录**: `D:\futures_v6\macro_engine\crawlers\LH\`  
**脚本数量**: 3 个

---

## 一、脚本清单

| 脚本名 | 类型 | 运行状态 |
|--------|------|---------|
| `LH_run_all.py` | 批量入口 | ✅ 可运行 |
| `LH_生猪期货收盘价.py` | 因子脚本 | ❌ 崩溃 |
| `LH_生猪期货持仓量.py` | 因子脚本 | ❌ 崩溃 |

---

## 二、逐脚本范式检查

### 2.1 LH_run_all.py

**通过项**:
- ✅ 脚本头部 docstring（内置）
- ✅ 有 try-except（subprocess 调用）
- ✅ subprocess 有 timeout=30
- ✅ 日志记录完善（print 分行输出）
- ✅ 数据输出：调用子脚本，不直接输出
- ✅ 无硬编码中文文件名（使用 SCRIPTS 列表驱动）
- ✅ 有中断/恢复逻辑（os.path.exists 检查）

**问题项**:
- ⚠️ 子进程调用时中文文件名在某些环境下可能乱码（实测 subprocess 输出中文字符显示为 `LH_�����ڻ����̼�.py`），建议统一改为英文脚本名或使用 glob 枚举

---

### 2.2 LH_生猪期货收盘价.py

**通过项**:
- ✅ 脚本头部有 docstring
- ✅ 有 try-except（fetch 和 main 两层）
- ✅ 魔法数字定义为常量（EMIN=10000, EMAX=30000）
- ✅ 日志记录（`[L1]` `[L4FB]` `[WARN]` `[OK]` 前缀）
- ✅ 输出路径通过 `save_to_db` 统一管理（符合数据库写入规范）
- ✅ 无硬编码中文文件名（脚本本身文件名含中文是命名规范，不是问题）

**问题项**:
- ❌ **`import os` 缺失** → 运行直接崩溃：`NameError: name 'os' is not defined`（第 17 行）
- ❌ **`import sys` 缺失** → `sys.path.insert` 报错
- ❌ **无 `--auto` 参数解析** → 不接受命令行参数，每次都执行采集逻辑（无 `if __name__ == "__main__"` 入口守卫时依赖手动调用）
- ❌ **网络请求无 timeout** → `ak.futures_main_sina()` 无超时保护
- ❌ **函数无类型注解** → `fetch()` 和 `main()` 缺少返回类型注解
- ❌ **PIT 日期未使用 `get_pit_dates()`** → 直接用 `date.today()` 作为 obs_date，周一未回退到上周五

---

### 2.3 LH_生猪期货持仓量.py

**通过项**:
- ✅ 脚本头部有 docstring
- ✅ 有 try-except（fetch 和 main 两层）
- ✅ 魔法数字定义为常量（EMIN=10000, EMAX=500000）
- ✅ 日志记录完善（`[L1]` `[L4]` `[WARN]` `[OK]` 前缀）
- ✅ 输出通过 `save_to_db` 统一管理

**问题项**:
- ❌ **`import os` 缺失** → 同上，崩溃：`NameError: name 'os' is not defined`
- ❌ **`import sys` 缺失**
- ❌ **无 `--auto` 参数解析**
- ❌ **网络请求无 timeout**
- ❌ **函数无类型注解**
- ❌ **PIT 日期未使用 `get_pit_dates()`** → 直接用 `date.today()`

---

## 三、运行验证

```
LH @ 2026-05-02T09:45:22.582955
>> LH_�����ڻ����̼�.py   ← subprocess 编码问题
>> LH_�����ڻ��ֲ���.py  ← subprocess 编码问题
LH Done 0.1s OK=0/2
```

直接运行任一因子脚本：
```
NameError: name 'os' is not defined
  File "LH_生猪期货收盘价.py", line 17
    this_dir = os.path.dirname(os.path.abspath(__file__))
```

**结论**: 两个因子脚本因 `import os` 缺失而完全无法运行，`OK=0/2`。

---

## 四、README.md 更新建议

```markdown
# LH — 生猪 期货数据采集

## 基本信息

| 字段 | 值 |
|------|-----|
| 品种代码 | `LH` |
| 中文名称 | 生猪 |
| 交易所 | DCE |
| 合约代码 | LH |
| 品种分类 | 农产品 |
| 因子数量 | 2 |
| 数据库因子数 | 2 |
| 数据库记录数 | 3190 |

## 因子配置

| 因子代码 | 名称 | 数据源 | 状态 |
|----------|------|--------|------|
| `LH_FUT_CLOSE` | 生猪期货收盘价 | AKShare (L1) | ⚠️ 待修复（import os/sys缺失） |
| `LH_FUT_OI` | 生猪期货持仓量 | AKShare (L1) | ⚠️ 待修复（import os/sys缺失） |

## 爬虫脚本

- `LH_run_all.py` 🔧 批量入口（正常）
- `LH_生猪期货收盘价.py` ⛔ 崩溃（缺 import）
- `LH_生猪期货持仓量.py` ⛔ 崩溃（缺 import）

## 运行方式

```bash
python crawlers/LH/LH_run_all.py
```

---

_最后更新时间: 2026-05-02 | 复查人: 程序员mimo_
```

---

## 五、修复优先级

| 优先级 | 问题 | 涉及脚本 |
|--------|------|---------|
| **P0 - 致命** | `import os` / `import sys` 缺失 | 全部因子脚本 |
| **P1 - 高** | 无 `--auto` 参数解析 | 全部因子脚本 |
| **P1 - 高** | PIT 日期周一未回退 | 全部因子脚本 |
| **P2 - 中** | 网络请求无 timeout | 全部因子脚本 |
| **P2 - 中** | 函数无类型注解 | 全部因子脚本 |
| **P3 - 低** | subprocess 中文文件名编码 | LH_run_all.py |
