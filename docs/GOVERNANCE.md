# 治理框架 — Minimum Viable Version

> 版本: v2.0-minimal  
> 更新: 2026-05-01  
> 状态: 简化生效

---

## 一、核心原则

1. **决策留痕** — 所有L2+决策记录到 `docs/decisions_log.md`
2. **接口锁定** — 核心接口变更必须技术议会投票
3. **里程碑驱动** — 任务优先级由里程碑倒推

---

## 二、技术议会

### 成员
- 项目经理 (agent-63961edb) — 主席
- 程序员deep (agent-0a11ab7c)
- 因子分析师YIYI (agent-ded0d6a7)

### 时间
- **周三 16:00-16:30**
- **周五 16:00-16:30**
- 议题收集截止: 当日 12:00

### 投票
- 2票通过
- 反对必须附理由

### 纪要
自动生成: `docs/events/YYYYMMDD_parliament.md`

---

## 三、核心接口锁定

| ID | 接口 | 文件 |
|----|------|------|
| I001 | GET /api/macro/signal/all | macro_api_server.py |
| I002 | GET /api/macro/signal/{symbol} | macro_api_server.py |
| I003 | calculate_composite_score | macro_scoring_engine.py |
| I004 | get_factor_details | macro_scoring_engine.py |

修改以上接口必须 L2 投票通过。

---

## 四、接口工作约束

跨模块接口修改前，必须参考：
```
D:\futures_v6\shared\INTERFACE_CHECKLIST.md
```

核心规则：
1. **改前验证** — 必须先看真实 API 响应，禁止凭预期修改
2. **Owner 制度** — 改他人负责的文件前必须通知 owner
3. **phantom 零容忍** — 发现 phantom 字段立即删除
4. **跨模块必须记录** — 改前在 decisions_log 记录，等确认后再改

---

## 五、决策记录格式

```markdown
### [日期] 议题标题
- **提案人**: xxx
- **决策**: 通过/否决 (票数)
- **内容**: 具体内容
- **影响**: 修改的文件/接口
```

记录到 `docs/decisions_log.md`。

---

## 五、检查脚本

```bash
python D:\futures_v6\scripts\governance_check.py
```

检查逾期议题/任务。

---

*原完整版 GOVERNANCE.md 保留在 docs/GOVERNANCE_full.md 作为参考*
