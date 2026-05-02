# decisions_log.md — 决策记录

所有L1/L2/L3决策必须记录在此。

---

## 2026-04-22 技术议会（第1次正式运作）

### 议题1: SignalChart P0修复
- **时间**: 11:02
- **提案人**: 项目经理
- **决策**: 通过 (3:0)
- **内容**: 修复 SignalChart 历史打分显示问题（6处改动）
- **影响**: 前端 SignalChart.tsx + macro.ts
- **验收**: ✅ 已验证

### 议题2: I001/I002字段映射
- **时间**: 11:02
- **提案人**: 项目经理
- **决策**: 通过 (3:0)
- **内容**: 修复 API 字段映射问题（5个问题）
- **影响**: macro_api_server.py
- **验收**: ✅ 已修复

### 议题3: Paper Trading启动
- **时间**: 11:02
- **提案人**: 项目经理
- **决策**: 通过 (3:0)
- **内容**: AG先行启动 Paper Trading，USD/CNY暂不入池
- **影响**: 策略配置
- **验收**: ✅ 已批准

---

## 2026-04-30 系统盘查

### 决策: 转向里程碑驱动
- **时间**: 12:19
- **决策人**: 项目经理
- **内容**: 暂停P2-5/6和治理恢复，优先确保M2.1(5/7)可达
- **理由**: M2.1仅剩6天，P2/G不紧急
- **影响**: 任务优先级调整

---

## 2026-05-01 劳动节

### 决策: P2批量完成
- **时间**: 10:25-13:27
- **决策人**: 项目经理
- **内容**: P2-1~P2-6全部完成
- **验收**: ✅ 语法检查通过

### 决策: 服务启动解除M2.1阻塞
- **时间**: 12:58
- **决策人**: 项目经理
- **内容**: 启动 FastAPI + VNpy 服务
- **结果**: FastAPI ✅, PaperBridge ✅, CTP ⚠️(假期关闭)
- **影响**: M2.1阻塞解除，等5/6 CTP恢复

---

### 决策: TYPE_CONTRACT 类型对齐修正（紧急回滚）
- **时间**: 17:44
- **决策人**: 项目经理
- **问题**: deep 和 Lucy 子 agent 未验证真实 API 响应，凭预期修改类型定义，导致相互冲突
  - deep 新增 phantom 字段（signal/strength/timestamp/factorDetails），API 不返回
  - Lucy 的 FactorDetail 缺少 `direction`/`rawValue`，多了 `contributionPolarity`
- **决策**:
  1. 撤销 deep 的 schemas.py 修改，恢复为 API 实际响应格式
  2. 修正 Lucys 的 FactorDetail，补入 `direction`/`rawValue`，删除 `contributionPolarity`
  3. TYPE_CONTRACT.md 重写为 v2.0（以 API 实际响应为唯一真值）
  4. 修复前端构建错误（SignalCellularAltOutlined → CloudServerOutlined）
- **验证**:
  - API 4品种 RU/CU/AU/AG 字段完全一致
  - MacroSignal 5字段 + FactorDetail 8字段 ✅ 全部对齐
  - `npm run build` ✅ 成功
- **教训**: 类型对齐必须先用 Invoke-RestMethod 验证真实响应，禁止凭预期修改

### 决策: 接口工作清单建立
- **时间**: 19:15
- **决策人**: 项目经理
- **内容**: 建立 `shared/INTERFACE_CHECKLIST.md`，约束全员跨模块接口修改行为
- **规则**:
  1. 改前验证：必须先看真实 API 响应
  2. Owner 制度：改他人文件前必须通知
  3. phantom 零容忍：立即删除
  4. 跨模块必须记录 decisions_log
- **文件**: `D:\futures_v6\shared\INTERFACE_CHECKLIST.md` (1971B)
- **联动更新**: GOVERNANCE.md 补充第四章「接口工作约束」

<!-- 后续决策追加在此 -->
