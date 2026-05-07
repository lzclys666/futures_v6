# 前端开发红线清单 v1.1

> 每次提交前必须逐条自查。违反任何一条禁止合并。
> 
> 起草：项目经理 | 日期：2026-05-06 | 审核：Lucy(有条件通过) + deep(可批准)

---

## 一、字段对齐（最高频事故）

### ✅ 1. 改接口字段必须查 TYPE_CONTRACT.md

**场景**：后端 schemas.py 或 routes/*.py 新增/改名字段时

**动作**：
1. 先读 `D:\futures_v6\shared\TYPE_CONTRACT.md`
2. 确认 Python 字段名（snake_case）→ TypeScript 字段名（camelCase）映射
3. 同步更新 TYPE_CONTRACT.md
4. 前后端一起改，不能只改一端

**已发生事故**：
- FactorDetail `icValue` vs `factorIc`（6 处修复）
- RiskRuleId `R3_PRICE_LIMIT` vs `R3_TOTAL_POSITION`（语义完全不同）
- OrderResponse `vt_orderid` vs `orderId`（5 处残留）

### ✅ 2. 禁止使用 vt_ 前缀字段

**规则**：所有 VNpy 返回的字段必须在适配层转换为标准命名，前端禁止直接使用 `vt_orderid`、`vt_symbol` 等 VNpy 原始字段。

**正确做法**：后端 trading.py 做映射，前端只用 `orderId`、`symbol`。

---

## 二、幽灵引用（Phantom Reference）

### ✅ 3. 删除导出前必须搜索所有引用

**规则**：删除任何函数/组件/类型导出前，执行：
```bash
grep -r "函数名" frontend/src/ --include="*.ts" --include="*.tsx"
```
确认零引用后才能删除。

**已发生事故**：
- `usePolling` Hook 不存在但被 2 处引用
- `fetchEquityCurve` 已删除但 userStore.ts 仍调用
- `RiskConfig` 两套实现各自维护

### ✅ 4. tsc --noEmit 必须零错误零警告

**规则**：每次提交前运行 `tsc --noEmit --skipLibCheck`，任何 warning 视为 error。

**禁止**：
- `any` 类型（除非有充分理由注释说明）

**限制**：
- `@ts-ignore` 注释必须附带 `// TODO: [原因] | 限期: YYYY-MM-DD` 格式注释，过期未处理视为 error

---

## 三、样式隔离

### ✅ 5. 禁止全局 CSS 选择器

**规则**：
- 禁止在任何 CSS 文件中使用 `body`、`*`、`div`、`html`、`.container` 等全局选择器
- 使用 CSS Module（`*.module.css`）或组件内 scoped 样式
- 新增或修改全局样式需 PM 审批

**已发生事故**：
- `index.css` 中 `text-align: center` + `width: 1126px` 污染全局布局

### ✅ 6. 颜色使用 CSS 变量

**规则**：颜色值禁止硬编码，必须使用 `var(--color-xxx)` 或 Ant Design token。

**目的**：支持深色主题切换（ConfigProvider darkAlgorithm）。

---

## 四、Mock 数据管理

### ✅ 7. USE_MOCK 必须显式声明

**规则**：
- 每个 API 文件顶部必须有 `const USE_MOCK = false;`（或从环境变量读取）
- `.env.production` 强制 `VITE_USE_MOCK=false`
- 构建时检查：如果 `USE_MOCK=true` 且 `NODE_ENV=production`，构建失败

**禁止**：提交时遗留 `USE_MOCK = true` 到主分支。

### ✅ 8. Mock 数据必须标注来源

**规则**：Mock 数据文件顶部必须有注释说明：
- 数据来源（API 响应截取 / 手工构造 / 历史数据）
- 最后更新日期
- 对应的后端端点

---

## 五、错误处理

### ✅ 9. 禁止静默失败

**规则**：
- `catch` 块禁止为空 `catch(err) {}`
- 必须记录错误（console.error / 日志 / 通知用户）
- 异步函数必须有 `.catch()` 或 try-catch

**已发生事故**：
- SignalBridge 初始化异常被静默吞掉 → NoneType 错误持续 8 天未被发现

---

## 六、接口变更流程

**Breaking change 定义**：字段删除、字段重命名、字段类型变更、端点移除。新增字段不是 breaking change。

### ✅ 10. 改后端接口必须通知前端

**规则**：后端 routes/*.py 或 schemas.py 有 breaking change 时：
1. 更新 `INTERFACE_GOVERNANCE.md`
2. 更新 `TYPE_CONTRACT.md`
3. 更新 `API_CONTRACT.md`
4. 通知 Lucy（或当前前端负责人）
5. 前后端同步验证后才算完成

**禁止**：后端改了字段名，前端不知道，线上静默失败。

### ✅ 11. 新增 API 端点必须文档化

**规则**：新增任何 `/api/xxx` 端点时：
- 在 `INTERFACE_GOVERNANCE.md` 添加条目
- 在 `API_CONTRACT.md` 添加端点定义
- 明确 owner（谁维护）
- 明确响应格式（字段名 + 类型）

### ✅ 12. schemas.py 变更必须同步更新 API_CONTRACT.md

**规则**：`api/schemas.py` 是后端类型真值源。任何 Pydantic model 的新增/修改/删除，必须同步更新 `shared/API_CONTRACT.md` 中对应的类型定义。

---

## 七、提交前自查 Checklist（打印贴桌）

```
□ tsc --noEmit --skipLibCheck 零错误
□ grep "vt_" 无新增 vt_ 前缀字段
□ TYPE_CONTRACT.md 已同步更新
□ USE_MOCK = false（非开发分支）
□ 无全局 CSS 选择器新增
□ 删除的导出已确认零引用
□ 新增 API 已文档化
□ 前后端字段名一致（camelCase）
□ catch 块非空（有错误处理）
```

---

## 八、后续自动化任务（P2，不阻塞本次发布）

| 任务 | 优先级 | 说明 |
|------|--------|------|
| ESLint 规则配置 | P2 | 自动检测 vt_ 前缀、全局 CSS、@ts-ignore |
| husky pre-commit hook | P2 | 提交前自动运行 tsc + eslint |
| CI 流水线 | P2 | PR 合并前自动检查 |
| zod/io-ts 响应校验 | P2 | API 响应运行时类型检查 |
| tsconfig strict: true | P2 | 存量代码迁移 |

---

## 审核记录

| 角色 | 姓名 | 审核意见 | 日期 |
|------|------|----------|------|
| 前端 | Lucy | 有条件通过。采纳：@ts-ignore 附TODO+限期、错误处理规范、全局样式审批。不采纳：去掉 --skipLibCheck（第三方库噪音）。后续任务：ESLint+husky 自动化、zod 校验、tsconfig strict | 2026-05-06 |
| 后端 | deep | 可批准执行。采纳：breaking change 定义、API_CONTRACT 同步、新增规则 12 schemas.py | 2026-05-06 |
| 项目经理 | PM | 定稿 v1.1。采纳 6 项，2 项后续任务，2 项不采纳 | 2026-05-06 |
