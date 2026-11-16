---
plan_id: NOTES-007
status: drafting
feature_name: notes sqlite 存储并发模型修复——读快照瞬态停摆
author: [Codex]
created_at: 2026-11-16
updated_at: 2026-11-16
plan_revision: 1
current_step: 0
total_steps: 5
depends_on: []
supersedes_spec_components: [docs/specs/notes/featurepack-service-and-editor.md]
new_spec_components: []
touched_goals: []
---

# NOTES-007 · notes sqlite 存储并发模型修复（读快照瞬态停摆）

## 0. 变更摘要

消除 notes 服务存储层的并发停摆放大器：读请求当前每笔要开 3 次 sqlite 连接、
重跑全套 schema 舞蹈（含 5 条必然失败的 ALTER TABLE 与一条无条件 meta 写），
在真实 UI 并发负载下与写路径互相顶锁，外部文件锁（AV 类暂停）被放大为
10s～8.5min 的全局读停摆与读快照冻结。本计划先并发复现并定责，再落
"schema 进程级一次 + 读路径零写锁单连接 + BUSY 具名分类"，最终以并发锤
零停摆 + 既有电池全绿收口，并向 READER-013 交接新发布件 pin（其 T-08
全绿收口的第二外部阻塞随之解除）。

[READER-013](../../../auto-reader/docs/plans/013-notes-featurepack-host.md) ·
[证据包 BACK-STALL-BLOCKER.md](../../../plan-artifacts/plan-013/BACK-STALL-BLOCKER.md) ·
[现行规格](../specs/notes/featurepack-service-and-editor.md)

## 1. 目标

- **G1**：停摆根因归因入档（决策 artifact）：notes 存储层调用形状 / 共享
  a2r sqlite facade / 环境文件锁（AV 类）三选一或组合，附最小可重跑负载
  形状与停摆窗口取证。
- **G2**：存储层修复——读请求全程零写锁、单连接；schema/迁移进程级一次；
  BUSY 一律具名 `second_writer` 快速失败，绝不悬挂。
- **G3**：并发锤 ≥20 轮零停摆（并发写负载下读 p99 ≤ 2s）、数据零丢失；
  既有服务电池全绿；发布件重建 + 版本锚更新。
- **非目标**：notes.fpack/1 冻结契约（端点面/幂等语义/来源闭集）不动；
  reader 侧 READER-013 T-08 复跑不归本计划（只交 pin）；AV/Defender 环境治理在仓控
  之外（只做隔离设计 + 建议）；纯性能优化（无停摆语义的加速）不扩面。

## 2. 架构方案

存储层仍是 `repository.at`（SQLite 单写者）+ `db.at`（服务层）+ `api.at`
（端点面）。修复保持既有进程形态（发布件 exe、HTTP 面不变），只改
repository 的连接与 schema 生命周期：

- **schema/迁移生命周期**：`ensure_schema` + `upgrade_if_legacy` 进程内
  once-guard（首次惰性初始化；成功后后续请求直连）。逐条 `ALTER TABLE`
  与无条件 `INSERT meta schema_v` 全部移入 once-guard / 版本化迁移，不再
  每请求重跑。
- **读路径**（repo_get/repo_list_active/repo_search/read_receipt/repo_status）：
  单连接、readonly 语义、零写锁（不再经 `open_repository`；WAL 下读写
  并行）。`repo_status` 的 `ensure_schema` 同样退到 once-guard。
- **写路径**：保持 `BEGIN IMMEDIATE` + busy_timeout（预算在 T-01 用实测
  复核，缺省上调至 5000ms 候选）；BUSY/超时一律具名 `second_writer`
  返回，前端语义不变。
- **总时budget**：存储操作增加进程级慢操作登记（>2s 写入监视日志），
  供停摆取证与回归观测；不引入异步重排（保持同步面）。

## 3. 技术栈

`.at` + auto.sqlite（a2r-std rusqlite 封装）+ WAL；验证为 python 电池
（verify_featurepack_service.py 等）+ 新并发锤脚本；发布件走本仓既有
发布流程（AGENTS.md：日常 debug，release 仅交付门）。

## 4. 需求分析与背景调查

**授权**：用户 2026-11-16 指示起草（"OK，你去起草新计划"）。范围=notes
sqlite 停摆的诊断与修复；未设预算/自动续跑上限。执行仓=auto-notes；
reader 仓只作消费交接。

**背景观察（2026-11-16，本计划起草时实读代码与在案证据）**：

1. 停摆症状（READER-013 §10 + BACK-STALL-BLOCKER.md，44+7 轮验收记录）：
   capture 写成功落盘后，紧随的 list/get 挂起 10s～8.5min；health 全程 UP
   （health 不触 repository——旁证阻塞面在存储层调用路径）；窗口内对已存在
   note_id 的 update 返回 not_found；数据零丢失、事后自恢复；变体"读快照
   冻结"（双路径读 60s+ 不可见，重启恢复真值）。
2. 隔离复现全部为零：直连锤测 100+ op、真实载荷回放 60 capture、verify 环
   90 次、纯 API 负载复算——**触发需真实 UI 并发**（浏览器 fetch + 页面
   VM + 引擎轮询 + fp 出站并存，请求速率倍增）。
3. **代码事实（本计划起草实读）**：
   - `repository.at:12` 头注释宣称"每请求独立 sqlite.open"，实际每读 =
     `open_repository()`（内部再 sqlite.open + ensure_schema + upgrade 检查）
     + 调用方再 `sqlite.open` —— **每读 3 连接**（repository.at:1382-1413）。
   - `ensure_schema`（repository.at:229）每次执行：busy_timeout/WAL pragma +
     3×CREATE TABLE IF NOT EXISTS + **5×无条件 ALTER TABLE ADD COLUMN**
     （列已存在时靠失败幂等，repository.at:238-247 注释自证）+ **无条件
     `INSERT OR REPLACE meta schema_v='3'`** + seed 检查——**读请求每次
     至少两次拿写锁**（ALTER 尝试 + meta 写）。
   - `busy_timeout=3000` 只覆盖锁等待；sqlite.open 的文件打开阶段（AV 类
     排他扫描窗口）不在其保护内——与 10s～8.5min 挂起、3s busy 不报错的
     现象吻合（放大机制假设，T-01 取证定性）。
   - `repo_status`（repository.at:1437）每调一次 `ensure_schema`。
4. 消费方现状：READER-013 T-08 双端验收被本停摆阻塞（其 §10 裁定"notes
   线处置落地后复跑至全绿"）；notes 仓自 NOTES-003 归档（11-13）后无
   在案动作，本停摆此前无本仓登记。

## 5. 详细设计

### T-01 诊断（bounded，决策 artifact）

构建 UI 形状并发锤（tests/probe/ 下新脚本，python）：N 线程混合
capture→立即并发 get/list/update(已存在 id)/receipt + fp_draft put/get +
低间隔轮询，运行 ≥10 分钟或至停摆复现；停摆窗口取证 = 服务端慢操作登记
（T-02 前置先以线程栈/procmon 式观察补位）、sqlite 文件态（-wal/-shm 尺寸）、
请求时长分布。产出决策 artifact（docs/plans/evidence/007-attribution.md）：
根因归因三选一或组合（调用形状放大器 / 共享 facade / 环境文件锁）+
owner 路由。若定责共享 a2r sqlite facade（engine 线域），本计划 bounded
移交并只落调用形状缓解，G2 相应收窄。

### T-02 修复（§2 形状，按 T-01 结论裁剪）

改动面 = repository.at（schema 生命周期、读路径、BUSY 分类）+ db.at
（若有委托面）。约束：不动 notes.fpack/1 端点语义；幂等/迁移状态机
（SD-17/18 语义）原样保留——once-guard 内的首次路径仍完整走
ensure_schema + upgrade_if_legacy；并发首请求的初始化互斥（进程内锁）。

### T-03 验证与发布

并发锤 ≥20 轮全绿（AC-03）→ 既有电池（verify_featurepack_service.py、
verify_standalone.py，必要时 verify_featurepack_editor.py --profile vue
一轮快验）→ 发布件重建（release 仅此一处，AGENTS.md 纪律）→ 新版本锚
sha256 写入 Spec 来源快照表（旧 6939bafa3544 退役登记）。

### 规范增量

| delta_id | add/modify/retire | docs/specs/... target | before/after rule | rationale | acceptance IDs |
|---|---|---|---|---|---|
| SD-01 | modify | docs/specs/notes/featurepack-service-and-editor.md | 无并发模型章节 → 新增「存储并发模型」节：读路径零写锁单连接、schema/迁移进程级一次、BUSY→`second_writer` 具名快速失败、并发写负载下读 p99 ≤ 2s 预算、health 与存储面分离语义 | 停摆修复的合同面从"未规定"变为可验收 | AC-02/03 |
| SD-02 | modify | docs/specs/notes/featurepack-service-and-editor.md | 验证入口节 → 增补并发锤入口与发布件版本锚更新（6939bafa→新 sha） | 复现与回归的常设入口 | AC-03/05 |

## 6. 测试设计

| ID / owner_stage | AC | 入口、反例与独立断言 |
|---|---|---|
| R-01 / work | AC-03 | tests/probe/concurrent_hammer.py（T-01 建，T-03 定版）：≥3 并发写者 + ≥3 并发读者 + draft 面，≥20 轮；断言=零 >2s 读、零 update 幻影 not_found、capture 幂等回执不变、错误全部具名 |
| R-02 / work | AC-02 | 代码级断言脚本或电池扩展：读路径（get/list/search/receipt）追踪零 BEGIN IMMEDIATE、零 ALTER/meta 写；进程生命周期内 ensure_schema 只跑一次（日志计数） |
| R-03 / work | AC-04 | 既有电池全绿：verify_featurepack_service.py（F-01..11+S-01/02）、verify_standalone.py；回归锚=冻结 schema 拒绝面与迁移半途故障自愈不回退 |
| R-04 / work | AC-05 | 发布件 sha256 与 Spec 冻结表一致；发布件上 R-01 复跑 ≥5 轮零停摆 |

第 8 节所列新脚本从本仓根 `python <脚本路径>` 运行，自管隔离
NOTES_DATA_DIR 与端口，双报告非零失败。AGENTS.md 纪律：日常验证 debug
profile，release 仅 T-03 交付门一步。

## 7. 验收标准

| ID | owner_stage | 可观察结果 |
|---|---|---|
| AC-01 | work | 决策 artifact 入档：根因归因（调用形状/facade/环境，含组合）+ 证据 + 最小可重跑负载形状；facade 定责时含 engine 线移交件 |
| AC-02 | work | 读路径零写锁、单连接；schema/迁移进程级一次；BUSY 全部具名 `second_writer` 不悬挂（代码追踪 + R-02） |
| AC-03 | work | R-01 并发锤 ≥20 轮：零 >2s 读停摆、零幻影 not_found、数据零丢失 |
| AC-04 | work | 既有电池全绿（R-03），冻结契约与迁移语义零回退 |
| AC-05 | work | 发布件重建 + 新版本锚入 Spec 冻结表；发布件复跑 R-01 ≥5 轮零停摆 |
| AC-06 | review | 独立上下文复演 R-01～R-04，核 AC-01～05，证据绑定源码/发布件版本 |
| AC-07 | merge | 归档回执；向 READER-013 交接 pin（新发布件 sha + 可引用提交） |

## 8. 执行步骤

拟实施位置 D:/autostack/.wt/notes-007/auto-notes，分支 notes-007-dev（work
确认实际树/分支/HEAD 后以此为准）。日常构建走 AGENTS.md dev 快环
（rust-workspace 内 cargo build -p auto-notes-30db9907-back，热增量 ~7s）。

| ID | owner_stage | 依赖 | 工作与验证 | 验收 |
|---|---|---|---|---|
| T-01 | work | — | 并发锤（UI 形状负载）+ 停摆取证 + 决策 artifact（docs/plans/evidence/007-attribution.md）；facade 定责→bounded 移交件 | AC-01 |
| T-02 | work | T-01 | 存储并发模型修复（§2 形状，按归因裁剪）：schema once-guard、读路径零写锁单连接、BUSY 具名、慢操作登记；R-02 追踪断言 | AC-02 |
| T-03 | work | T-02 | R-01 定版 ≥20 轮 + R-03 电池全绿 + 发布件重建（release 一次）+ 版本锚入 Spec + R-04 发布件复跑 | AC-03/04/05 |
| T-04 | review | T-03 | 独立上下文复演 R-01～R-04，绑定源码与发布件版本，核 AC-01～05 | AC-06 |
| T-05 | merge | T-04 pass | 归档回执 + READER-013 pin 交接（新 sha + 提交；其 T-08 复跑消费） | AC-07 |

## 9. 复审记录

2026-11-16 · stage: new · NOTES-007 r1 · outcome: pass（草案就绪）·
next: work T-01。依据 READER-013 7 轮收口证据 + BACK-STALL-BLOCKER.md +
本仓 repository.at 实读（每读 3 连接 / ensure_schema 每请求 5×ALTER +
无条件 meta 写 / busy_timeout=3000 不覆盖文件打开）起草；诊断任务带
facade→engine 线 bounded 移交出口；消费方 READER-013 只收 pin 交接，
不构成本计划前置。

## 10. 待澄清事项

- AV/Defender 类环境文件锁在仓控之外：修复目标为消除存储层放大器
  （外部百毫秒级暂停不得放大为分钟级全局队列）；若机器体检后环境因素
  消失，R-01 负载形状仍必须在案并通过。
- T-01 若定责共享 a2r sqlite facade（auto.sqlite 内部互斥/挂起）：本计划
  按 G1 出移交件转 engine 线，T-02 收窄为调用形状缓解（如进程内单写者
  串行化），AC-02/03 相应复核。
- notes-service 发布流程的执行者与 gc-target/发布脚本归 notes 线既有一环；
  T-03 按本仓标准流程走，若流程变化以 AGENTS.md/现行脚本为准。
- READER-013 T-08 复跑时点与双端全绿门归 reader 计划所有；本计划交付
  pin 后即解除其第二外部阻塞，无相互排期依赖。
