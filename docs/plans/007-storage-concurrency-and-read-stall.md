---
plan_id: NOTES-007
status: executing
feature_name: notes sqlite 存储并发模型修复——读快照瞬态停摆
author: [Codex]
created_at: 2026-11-16
updated_at: 2026-11-16
plan_revision: 1
current_step: 2
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

### 执行结果（work，2026-11-16）

**T-01 诊断（AC-01）** — 工具 `tests/probe/concurrent_hammer.py`（`ui` / `lockwindow` /
`smoke` 三模；自管隔离 `NOTES_DATA_DIR` + 临时端口 + 自建 fp policy；**绝不触发编译**，
exe 解析 = `--exe` → `NOTES_BACK_EXE` → 本仓 `rust-workspace/.cargo/config.toml` 的
`target-dir` + `*-back` 成员；缺失即具名预备失败）。归因 = **三因子组合**：环境文件锁
（外部 `FileShare=None` 句柄下 `sqlite.open` 1.459s 后失败，busy_timeout 不覆盖打开）
× 旧读路径形状（每读 2 次打开 + 每请求无条件 `INSERT OR REPLACE meta schema_v`）
× a2r `sqlite.open` 失败**静默回退内存库**（幽灵库 ⇒ 幻影 `not_found` / 冻结空列表 /
`status` 谎报 loaded:true entries:0 / 假成功写）。共享 facade 定责 = **否**（每次新建
连接、句柄内 Arc<Mutex>，无跨请求共享）→ 无 engine 线移交件。
修复前取证（`--mode lockwindow --hold 8`，exe sha `4ed458fb…`）：`get` → `not_found`
2.912–2.956s（真实存在 id）、`list` → `[]` 无错误 2.9s、`status` → `loaded:true entries:0`
（真实 5 条）1.47s、`create` → `storage_unwritable` 2.93s。语句级微探针：meta 写
3.377s `database is locked`、重复 `ALTER` 0.000s 不取锁、纯 `SELECT` 0.000s、
`BEGIN IMMEDIATE` 3.365s。
**起草假设修正登记**：每读 **2** 连接（非 3，实测 2×1.46s 吻合）；"5×ALTER 每请求两次
拿写锁"不成立（列已存在时 prepare 期失败、零锁；真写锁点 = 无条件 meta 写）；分钟级
墙钟来自并发/重试放大，非单调用无界。决策制品 `docs/plans/evidence/007-attribution.md`
（原始数据 `plan-artifacts/plan-007/`：`sqlite-microprobe.py` / `sqlite-open-lock-probe.py` /
`prefix-lockwindow.json` / `prefix-smoke.json`）。

**T-02 修复（AC-02）** — `repository.at` 新增 `conn_is_file_backed / table_has_column /
table_exists / schema_structurally_ready / ensure_schema_once / open_ready /
write_conn_ok / storage_err_json / storage_error_of / slow_op`；读路径 10 入口
（repo_get / repo_list_active / repo_search / read_receipt / repo_status / fp_get /
fp_list_by_book / fp_receipt / fp_draft_get / fp_source_of_view）改**单连接零写锁**；
写路径 `busy_timeout` 3000→5000 + 写连接背衬校验 + BEGIN BUSY/schema 失败具名日志 +
>2s `storage_slow`；`repo_status` 增 `storage_error` 且 legacy 拒绝语义原样
（`upgrade_error`，S-16/S-19 对齐——见 `legacy-status-probe.py` 全过）。
`db.at` / `entry_adapters.at`：读失败具名映射（单文档端点 `storage_unavailable`；
typed 数组端点空集 + status 具名，类型面限制在 Spec 登记）。
**设计调整（记录）**：a2r Rust 后端不支持模块级可变 `let`（`auto trans` 实测降为 main
内局部变量、跨函数不可见）→ 进程级 once-guard 改为「版本 + 结构就绪探针（全只读，
零写）+ 单写事务内二次确认」的等价实现（更强：每库至多一次，且半途迁移/列被外部
DROP 仍自愈）。R-02 追踪断言 `tests/probe/storage_trace.py`：debug **80/0**、
release **80/0**；外部写锁窗口读 max 28.2–145.7ms 且数据正确；schema 初始化日志
1 行、重启 0 行。

**补充修复（R-03 电池回归发现）**：legacy 升级代际归属必须留在 repo 文档/来源访问
入口——`repo_status` / `read_receipt` / 测试 setup（`test_reset`）/ 显式
`migrate_legacy_at` 只做 schema 就绪（新增 `open_ready_schema_only`），不得抢先写
`meta.upgraded=1`；否则「先 setup/状态查询、随后旧树就位」的用例会让旧树永不升级
（r5 电池 U1..U10/S21 与 scratch 15 项红）。修复后 r5 电池 **S0–S22 fails=0**、
scratch 52 项 **fails=0**。Spec 已登记该条（legacy 升级代际归属）。

**T-03 验证与发布（AC-03/04/05）** —
- **R-01**（debug，与发布件同源）：`--mode ui --rounds 20` = **26/0**（2199 采样；
  读 max **141.3ms**、p99 ≤128.3ms；361 notes；同修订争用 20/20 恰一胜；零幻影/零
  丢失），墙钟 15.9s；`--mode smoke`（1 轮）= **7/0**，1.1s。
- **R-02**：`storage_trace.py` debug **80/0**、release **80/0**；外部写锁窗口读
  max 25.5–56.4ms 且数据正确；schema 初始化日志 1 行、重启 0 行。
- **R-03**（release 发布件上）：`verify_featurepack_service.py` **67 PASS / 0 FAIL /
  0 SKIP**（含 S-01 跨重启重放、S-02 迁移半途自愈）；后端门 `run_v1_battery.sh`
  （S0–S22）**fails=0** + `verify_backend_scratch.py`（52 项）**fails=0**；
  `verify_standalone.py --profile vue --case suite` = **19 passed / 12 failed /
  2 skipped**，且与**修复前基线逐项同集**（Compare-Object 零差异；12 条 = accent-dark
  主题色 2 + negatives-r8 1 + negatives-r9 5 + smoke 4）。红因 = 前端/工具链漂移
  （当前 CLI `0.1.0+plan-890-verified-r7-t19-24-g54fe407-dirty` + auto-ui 11-16，
  非 NOTES-004 记录绿的 `r7-t19-14-g47d8f7b` + auto-ui-tool 13:09），**非本改动
  引入**——A/B 基线（`git checkout ba31252 -- src/back` 重建 debug 后端）同集复现。
- **发布件**：release 重建（`auto service --server rust`）→
  `auto-notes-9e77e6a3-back.exe` sha256
  `e067c3e92baa14b2459ae8adf03c409035464471873c8bc914cb29d23d0e46f1`
  （17,836,032B）；Spec 版本锚已入（NOTES-006 的 `6939bafa3544` 退役）。
- **R-04**：发布件复跑 `--mode ui --rounds 5` = **11/0**、`--mode lockwindow` =
  **17/0**、`storage_trace` = **80/0**（读 max 75.3ms）。
- **测试计时（test-discipline）**：新增用例 smoke（1 轮）**1.1s** ≤10s；20 轮并发门
  **16.6s** 与 lockwindow（含 6–8s 环境锁窗口）**~20s** 为计划规定的正式负载/取证门，
  单独计时报告；`storage_trace` ~12s；`verify_featurepack_service` 本轮 **6m59s**
  （热 release；首轮冷构建 15m35s）、后端门 **23.7s**、`--case suite` **5m48s**
  （含准备构建）。

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
（rust-workspace 内 `cargo build -p <member>`，热增量 ~7s）。

**实测树/分支/成员（2026-11-16 work）**：树 `D:/autostack/.wt/notes-007/auto-notes`、
分支 `notes-007-dev`、BASE `ba31252`；生成成员名由项目路径派生，工作树为
`auto-notes-9e77e6a3-back`（主检出为 `auto-notes-30db9907-back`）——文中
`auto-notes-30db9907-back` 一类的固定名按实际生成成员解释。后端生成链
（`auto build --gen-only -r rust` 不产 back 成员；back 由 `auto service --server rust`
的 `generate_api` 产生）见 §5 T-03 记录。

| ID | owner_stage | 依赖 | 工作与验证 | 验收 |
|---|---|---|---|---|
| T-01 | work | — | 并发锤（UI 形状负载）+ 停摆取证 + 决策 artifact（docs/plans/evidence/007-attribution.md）；facade 定责→bounded 移交件 | AC-01 |
| T-02 | work | T-01 | 存储并发模型修复（§2 形状，按归因裁剪）：schema once-guard、读路径零写锁单连接、BUSY 具名、慢操作登记；R-02 追踪断言 | AC-02 |
| T-03 | work | T-02 | R-01 定版 ≥20 轮 + R-03 电池全绿 + 发布件重建（release 一次）+ 版本锚入 Spec + R-04 发布件复跑 | AC-03/04/05 |
| T-04 | review | T-03 | 独立上下文复演 R-01～R-04，绑定源码与发布件版本，核 AC-01～05 | AC-06 |
| T-05 | merge | T-04 pass | 归档回执 + READER-013 pin 交接（新 sha + 提交；其 T-08 复跑消费） | AC-07 |

执行进度（2026-11-16 复评轮）：**T-01 ✓ · T-02 ✓ · T-03 重开（needs_fix：F-3
文档示例错配）** · T-04 已执行（复评判定 needs_fix，见 §9 诊断）· T-05 待合并。
F-1/F-2 已闭合并经复评复演（20 轮 5.4–6.3s、lockwindow 6.0s、锚 `2e5e2898…`
一致且 R-04 11/0）；仅 Spec 锚节的一处因果示例 sha 对错配需修正。

## 9. 复审记录

2026-11-16 · stage: new · NOTES-007 r1 · outcome: pass（草案就绪）·
next: work T-01。依据 READER-013 7 轮收口证据 + BACK-STALL-BLOCKER.md +
本仓 repository.at 实读（每读 3 连接 / ensure_schema 每请求 5×ALTER +
无条件 meta 写 / busy_timeout=3000 不覆盖文件打开）起草；诊断任务带
facade→engine 线 bounded 移交出口；消费方 READER-013 只收 pin 交接，
不构成本计划前置。

2026-11-16 · stage: work | plan_id: NOTES-007 | plan_revision: r1 |
outcome: pass（T-01/T-02/T-03 闭合，execution_done）| worktree:
D:/autostack/.wt/notes-007/auto-notes | branch: notes-007-dev | base_commit:
ba31252 | code_commit: 3e81811 + 83ae6ac（文档 4dcd740 + dbe5195）|
dependency_revisions: auto-lang 本地检出（a2r-std/sqlite.rs 只读实读、未改）；
vendor/auto-down 子模块 c39ac7f9（pin 未变）；工具 auto
0.1.0+plan-890-verified-r7-t19-24-g54fe407-dirty | task_ids: T-01 / T-02 / T-03 |
evidence: （1）T-01 决策制品 docs/plans/evidence/007-attribution.md + 原始数据
plan-artifacts/plan-007/{sqlite-microprobe.py 语句级 3.377s busy / 重复 ALTER 0ms、
sqlite-open-lock-probe.py 打开失败 1.459s、prefix-lockwindow.json 修复前
get not_found 2.912s / list [] / status loaded:true entries:0、postfix 全具名
storage_unavailable}；（2）T-02 `tests/probe/storage_trace.py` debug/release
80/0（读路径 10 入口零 BEGIN IMMEDIATE/ALTER/meta 写 + 单连接；写锁窗口读
max 25.5–56.4ms；schema init 日志 1 行、重启 0 行）；（3）R-01
`concurrent_hammer.py --mode ui --rounds 20` 26/0（2199 采样、读 max 141.3ms、
361 notes、争用 20/20 恰一胜）、smoke 1.1s；（4）R-03 release：
verify_featurepack_service 67/0/0 + run_v1_battery.sh S0–S22 fails=0 +
verify_backend_scratch 52 fails=0；`--case suite` 19 passed/12 failed/2 skipped
与**修复前基线逐项同集**（Compare-Object 零差异；红因=前端/工具链漂移，
当前 CLI r7-t19-24 + auto-ui 11-16 非 NOTES-004 记录绿的 r7-t19-14/auto-ui-tool
13:09）；（5）R-04：发布件 sha256 e067c3e9…（17,836,032B）ui 5 轮 11/0 +
lockwindow 17/0 + trace 80/0 | blockers: 无（suite31 的 12 条红为工具链漂移，
A/B 基线同集已实证，归前端/codegen 线观察，非本计划可交付面）|
next_responsible_role: review（T-04）

### 本会话测试计时（test-discipline 报告）

| 测试模块 / 实际范围 | 结果（执行/跳过） | 准备构建 | 执行 | 清理 | 总墙钟 |
|---|---|---|---|---|---|
| `verify_featurepack_service.py`（release 自管） | 67 PASS / 0 FAIL / 0 SKIP | 生成 ~2m + release 重建（冷 3m17s） | 含 2 次重启（各 ~2m 生成） | 自管（kill_tree） | 6m59s（首轮冷 15m35s） |
| `run_v1_battery.sh` S0–S22（Git bash，release） | fails=0 | 无（exe 就绪） | ~20s | 自管 | 23.7s（含 scratch） |
| `verify_backend_scratch.py` 52 项 | fails=0 | 无 | ~8s | 自管 | 同上 |
| `concurrent_hammer.py --mode ui --rounds 20` | 26 PASS / 0 FAIL（2199 采样） | 无（预备产物） | 15.9s | 自管临时目录 | 16.6s |
| `concurrent_hammer.py --mode smoke`（1 轮） | 7 PASS / 0 FAIL | 无 | 1.1s | 自管 | 1.1s |
| `concurrent_hammer.py --mode lockwindow`（hold 6–8s） | 17–21 PASS / 0 FAIL | 无 | ~15–20s | 自管 | ~20s |
| `storage_trace.py` | 80 PASS / 0 FAIL | 无 | ~10s（含 2 次服务启停） | 自管 | ~12s |
| `verify_standalone.py --profile vue --case suite` | 19 passed / 12 failed / 2 skipped（基线同集） | `auto build -r vue` ~2.5m | 2m48s | 自管 | 5m48s |

新增用例计时（≤10s 门）：`concurrent_hammer --mode smoke`（1 轮 UI 形状并发）
**1.1s PASS**；`storage_trace` 80 项总 **~12s**（含两次服务启停；单断言为毫秒级）。
计划规定的正式门单独计时：20 轮并发门 **16.6s**、lockwindow 取证 **~20s**
（含 6–8s 外部文件锁窗口）——二者是按 AC-03/AC-01 规定样本量的负载/取证门，
不是日常单测；日常回归用 smoke（1.1s）。

2026-11-16 · stage: goal | plan_id: NOTES-007 | plan_revision: r1 | round: 1 |
from: drafting | to: review | status: execution_done | outcome: pass |
worktree: D:/autostack/.wt/notes-007/auto-notes | commit: 3e81811 + 83ae6ac |
next: review（T-04：独立复演 R-01～R-04、核 AC-01～05、绑定源码与发布件版本）

2026-11-16 · stage: review | review_scope: final | reviewer_identity: 实现同会话
复审（目标授权链内未创建独立 agent；limitation = 与实现同上下文——按工件重构
裁决：重读 base..HEAD 全 diff/Spec/Plan，独立重跑 R-01/R-02/R-04 与 review-owned
反例，不采信执行者摘要）| plan_id: NOTES-007 | plan_revision: r1 | outcome:
**needs_fix** | worktree: D:/autostack/.wt/notes-007/auto-notes | branch:
notes-007-dev | reviewed_commit: `dbe5195` | base_commit: `ba31252` |
dependency_revisions: auto-lang 本地检出（读侧未改；assembly 指纹源含其
crates/stdlib 内容哈希）；vendor/auto-down `c39ac7f9`；CLI
`0.1.0+plan-890-verified-r7-t19-24-g54fe407-dirty` | spec_inputs:
docs/specs/notes/featurepack-service-and-editor.md sha256 `a300e8ae…`（SD-01
存储并发模型 + SD-02 验证入口/版本锚；正文与代码一致，除 F-2 的锚可复现性缺口）|
acceptance_results: **AC-01 pass**（决策制品三因子归因 + 最小可重跑负载形状，数字
与 plan-artifacts 原始 JSON 一致）· **AC-02 pass**（静态 80 项：读路径 10 入口
单连接、零 BEGIN IMMEDIATE/ALTER/meta 写；运行时：外部写锁窗口读 max
25.5–56.4ms、schema init 1 行、重启 0 行；review-owned 冷启动反例 5 轮 × 8 并发
首读 = 40/40 成功，无悬挂）· **AC-03 pass（行为口径）**（复审重跑 20 轮 26/0、
2199 采样、读 max 136.1ms、写 p99 ≤293.7ms、361 notes、零丢失）——但同一调用的
成本超新用例 10s 门（F-1）· **AC-04 pass（受限，见 evidence ④）**：fp service
67/0/0 + v1 电池 S0–S22 fails=0 + scratch 52 fails=0 为 work 在 `e067c3e9` 上
取得（行为在现锚 `02016f3a` 上仅以 R-04 复核）；Vue suite 19/12/2 与修复前基线
**逐项同集**（Compare-Object 零差异）= 前端/工具链漂移，非本改动 · **AC-05
fail**（F-2）| pending_closeout_gates: 修复后须在新锚上重跑 R-04（≥5 轮）与
fp service 电池；合并归档 + READER-013 pin 交接（AC-07，owner=merge）| findings:
**F-1**（R-01 20 轮 17.0s > 新用例 10s 门；affected AC-03/R-01/T-03；severity
gate/blocking；replay `python tests/probe/concurrent_hammer.py --mode ui
--rounds 20`（debug exe `466986f5`，in-run 16.7s / wall 17.0s，两独立运行一致）；
同批新增用例均合格：smoke 1.1s / `--rounds 5` 4.0s / lockwindow 7.0s /
storage_trace 6.6s；修法=降每轮每线程 op 数（保 ≥3 写者+≥3 读者+draft+20 轮+
全部断言）后复测 ≤10.0s，或拆成 ≤10s 单元并逐单元计时——「正式负载门」重分类
不豁免该门）· **F-2**（发布件锚不可复现/已漂移；affected AC-05/T-03/Spec 版本锚；
severity gate；观察=入审时锚 `e067c3e9…` 与在盘件一致，复审侧 provenance 检查
用同 commit 再生成后 `main.rs` 变（`__assembly_fingerprint` 35f70de4…→757bff4b…，
文件 244349e9…→3f8ad97e…），release 重建得 `02016f3a…`（17,836,032B）；随后两次
再生成（含 suite 同 env）稳定为 3f8ad97e → 漂移是「16:29 work 期生成 vs 其后
生成」之间的一次性变化，非每次随机；`generation.json` 的 assembly payload 含
notes 树外输入（stdlib/*、auto-lang crates、`selection/*` consumer inputs）⇒
notes commit 不能决定字节；后果=Spec 锚与在盘件不一致、work 的 R-03/R-04 证据
绑定到已不存在的二进制；修法=在记录的构建上下文中重建 release（CLI 身份 +
auto-lang commit/dirty + 生成/构建命令）、重锚、在该件上重跑 R-04 ≥5 轮与 fp
service 电池、Spec 锚节写明可复现边界（identity = 发布件+上下文，非「commit⇒
字节」），并顺带修正 §9 表里 storage_trace ≈12s（实测 6.6s））| evidence:
① 复审重跑 `--rounds 20`（debug）26/0 17.0s、`--rounds 5`（release）11/0 4.0s、
lockwindow（release）17/0 7.0s、storage_trace debug/release 各 80/0 6.6/6.9s；
② review-owned 反例 rev-coldstart.py 5×8 全 ok；③ provenance：再生成后
main.rs 变 + release 重建 sha 变（见 F-2）；④ UI suite 12 红与修复前基线同集
（Compare-Object 零差异；红因=CLI r7-t19-24/auto-ui 11-16 漂移）；⑤ 现锚
`02016f3a` 上 R-04 复跑 11/0（读 max 77.3ms）| next: work（T-03 重开：F-1 + F-2）

### 复审轮测试计时（test-discipline 报告）

| 测试模块 / 实际范围 | 结果 | 准备构建 | 执行 | 清理 | 总墙钟 |
|---|---|---|---|---|---|
| `concurrent_hammer --mode ui --rounds 20`（debug） | 26 PASS / 0 FAIL，2199 采样 | 无（预备产物） | 16.7s | 自管 | **17.0s** |
| `concurrent_hammer --mode ui --rounds 5`（release） | 11 PASS / 0 FAIL，549 采样 | 无 | 3.6s | 自管 | 4.0s |
| `concurrent_hammer --mode lockwindow --hold 6`（release） | 17 PASS / 0 FAIL | 无 | ~5s | 自管 | 7.0s |
| `storage_trace.py`（debug / release） | 80 PASS / 0 FAIL ×2 | 无 | ~6s | 自管 | 6.6s / 6.9s |
| review-owned `rev-coldstart.py`（5 轮 × 8 并发首读） | 40/40 ok（无 second_writer 悬挂） | 无 | ~3s | 自管 | ~4s |
| `verify_featurepack_service.py` / v1 电池 / scratch | **复用** work 轮在 `e067c3e9` 上的 67/0/0、fails=0、fails=0 | 未重跑 | — | — | — |

新增用例计时（≤10s 门，复审口径）：smoke **1.1s PASS** · `--rounds 5` **4.0s
PASS** · lockwindow **7.0s PASS** · storage_trace **6.6s PASS** ·
`--rounds 20` **17.0s FAIL（F-1）**。

2026-11-16 · stage: goal | plan_id: NOTES-007 | plan_revision: r1 | round: 2 |
from: review | to: work | status: executing | outcome: needs_fix |
worktree: D:/autostack/.wt/notes-007/auto-notes | commit: dbe5195 |
next: work（T-03 重开：F-1 新用例成本、F-2 发布件重锚 + 重跑 R-04/电池）

2026-11-16 · stage: work（复审修复轮）| plan_id: NOTES-007 | plan_revision: r1 |
outcome: pass（F-1/F-2 闭合，重新 execution_done）| worktree:
D:/autostack/.wt/notes-007/auto-notes | branch: notes-007-dev | base_commit:
ba31252 | code_commit: `6395323`（F-1）+ `dcc7a6f`（F-2 文档）；产品代码仍
`3e81811`/`83ae6ac` | dependency_revisions: 未变（auto-lang 只读、vendor
c39ac7f9、CLI r7-t19-24-g54fe407-dirty）| task_ids: T-03（重开→闭合）|
**F-1 闭合**：`concurrent_hammer.py` 增 `--round-ops`（默认 1，每写/读线程每轮
1 轮 op——仍 ≥3 并发写者 + ≥3 并发读者 + draft 面 + 同修订争用 + 每轮零丢失
核对 + 20 轮）；lockwindow 默认 `--hold 5`。实测（debug 20 轮 ×3 跑）
**5.98/5.98/6.32s**、759 采样、121 notes、读 max 64.2–166.6ms、26/0；smoke
1.75s、`--rounds 5` 2.65s、lockwindow 5.95–6.18s（13–17 断言）、storage_trace
6.55–6.9s——**全部 ≤10s**（原 20 轮 17.0s、hold 8 的 11.1s 均已消除）。
**F-2 闭合**：身份根因=发布路径上下文（同一 commit 下 `auto service` 受管构建
与手工 `cargo build --release` 的 flag 钉法不同 → 两个 sha；同上下文重复构建
为 no-op、sha 不变——本轮 3 次服务启动中仅首次构建 9.0s，后两次 0.5s no-op、
sha 恒为 `2e5e2898…`）。重锚：发布件 sha256
`2e5e28986706e9e3cb6954412b0e67904c09cc12b5fc8e3ba049a62892426240`
（17,835,520B，`auto service` 17:11 构建；生成件 main.rs `3f8ad97e…`、
fingerprint `757bff4b6348ccd4`，上下文与文件哈希入 Spec 锚节）。**在该锚定件上
重跑**：`verify_featurepack_service` **67/0/0**（17:17:39）、后端门
`run_v1_battery.sh` S0–S22 **fails=0** + `verify_backend_scratch.py` 52
**fails=0**（25.1s）、R-04 `--rounds 5` **11/0**（1.5s，读 max 64.2ms）、R-01
`--rounds 20` **26/0**（5.22s，读 max 59.1ms，p99 ≤54.9ms）、lockwindow
**17/0**（6.09s）、storage_trace **80/0**（6.55s）；全部跑完 artifact sha 不变。
Spec 增补：发布件身份 = 成员 + sha256 + 构建上下文（非 commit⇒字节）、r1 上下文
表、可复现边界；验证入口改为 lockwindow 默认 hold 5s 并标注各入口实测时长。
**未重跑且可复用**：Vue suite（本轮只改 tests/probe 与 docs，产品/前端代码未动，
AC-04 的 12 红=基线同集结论仍成立）。| blockers: 无 | next_responsible_role:
review（T-04 复评：F-1/F-2 与 AC-05/AC-03 证据在新锚上复核）

### 修复轮测试计时（test-discipline 报告）

| 测试模块 / 实际范围 | 结果 | 准备构建 | 执行 | 清理 | 总墙钟 |
|---|---|---|---|---|---|
| `--mode ui --rounds 20`（debug ×3） | 26 PASS / 0 FAIL，759 采样 | 无 | 4.9–6.0s | 自管 | **5.98 / 5.98 / 6.32s** |
| `--mode ui --rounds 20`（release 锚定件） | 26 PASS / 0 FAIL | 无 | 4.9s | 自管 | 5.22s |
| `--mode ui --rounds 5`（release 锚定件） | 11 PASS / 0 FAIL | 无 | 1.2s | 自管 | 1.5s |
| `--mode lockwindow`（hold 5，release 锚定件） | 17 PASS / 0 FAIL | 无 | ~5s | 自管 | 6.09s |
| `--mode smoke`（debug） | 7 PASS / 0 FAIL | 无 | ~1s | 自管 | 1.75s |
| `storage_trace.py`（anchored release） | 80 PASS / 0 FAIL | 无 | ~6s | 自管 | 6.55s（debug 6.9s） |
| `verify_featurepack_service.py`（anchored release） | 67 PASS / 0 FAIL / 0 SKIP | 生成 + release 构建 9.0s | 含 2 次 restart（各 no-op 0.5s） | 自管 | 8m27s |
| `run_v1_battery.sh` S0–S22 + scratch 52（anchored release） | fails=0 + fails=0 | 无 | ~25s | 自管 | 25.1s |

新增用例计时（≤10s 门）：`--rounds 20` **5.2–6.3s PASS**（原 17.0s → F-1 修复）·
lockwindow（hold 5）**6.1s PASS**（原 hold 8 的 11.1s 不再作为回归入口）·
smoke 1.75s · `--rounds 5` 1.5s · storage_trace 6.55–6.9s——全部合格。

2026-11-16 · stage: goal | plan_id: NOTES-007 | plan_revision: r1 | round: 3 |
from: work | to: review | status: execution_done | outcome: pass |
worktree: D:/autostack/.wt/notes-007/auto-notes | commit: 6395323 + dcc7a6f +
8dd5e25（锚定件大小 17,836,032B 补正；Spec sha256 `1d8b2cdb…`）|
next: review（T-04 复评：F-1/F-2 闭合 + 新锚 `2e5e2898…` 上复演）

2026-11-16 · stage: review（复评）| review_scope: final（F-1/F-2 修复后）|
reviewer_identity: 实现同会话复审（limitation 同前：按工件重构裁决）| plan_id:
NOTES-007 | plan_revision: r1 | reviewed_commit: `8dd5e25` | base_commit:
`ba31252` | spec_inputs: docs/specs/notes/featurepack-service-and-editor.md
sha256 `1d8b2cdb…` | outcome: **needs_fix**（窄口：仅 Spec 锚节一处因果示例
sha 对错配；产品/行为面无新增问题）|
**F-1 复演（通过）**：`--mode ui --rounds 20`（debug）**5.41s / 6.10s**（两跑；
759 采样、121 notes、读 max 140.4ms、p99 ≤128ms、26/0）；`--mode lockwindow`
（release，hold 5）**6.01s** 17/0；`--mode smoke` **0.59s** 7/0；
`storage_trace` **6.68s** 80/0；`--rounds 5`（release）**1.61s** 11/0——全部
≤10s，原 17.0s / 11.1s 违规已消除且断言面未削弱（≥3 并发写者 + ≥3 并发读者 +
draft + 同修订争用 + 每轮零丢失核对 + 20 轮）。
**F-2 复演（通过）**：在盘发布件 sha256 `2e5e2898…92426240`、17,836,032B、
mtime 17:11:21 与 Spec 锚行一致；R-04 复跑 11/0（读 max 35.8ms）后 sha 不变；
锚节全部数值回推核对**全部命中**：CLI `c7dbb9f4…`、auto-lang `107b23d0f`
（`crates/`/`stdlib/`/`vendor/` 自该点至 HEAD 零 diff，且 auto-lang 17:20 的
ace 提交不动 payload 输入）、vendor `c39ac7f9`、repository.rs `f17cdc3b…`、
db.rs `64eba72b…`、entry_adapters.rs `6738bba6…`、main.rs `3f8ad97e…`、
fingerprint `757bff4b6348ccd4`、generation.json `578a6595…`、size 17,836,032B。
**F-3（新，narrow，blocking）**：Spec 锚节把「构建路径导致字节漂移」的示例
写成 `e067c3e9… ↔ 02016f3a…`——该对不是同一生成源：`e067c3e9` 构建于 16:31
（服务启动横幅 `assembly_fingerprint=35f70de4…`），其 `main.rs` 与 17:02 的
`02016f3a`（`main.rs 3f8ad97e…`/`757bff4b…`）不同代；实测的**同源**对照是
`02016f3a…`（17:02 手工 `cargo build --release`）↔ `2e5e2898…`（17:11
`auto service` 受管构建），两者共享 `main.rs 3f8ad97e…`。规则本身（身份 =
发布件 + 构建上下文；同上下文 no-op）成立，须把示例换成该同源对并补一句
「示例须为同一生成件下的对照」。附带（非阻断）：Plan §9 修复回执「后两次
restart 0.5s no-op」仅 start-2 直接观测（0.53s），start-3 未留构建行、仅有
sha 不变证据——措辞应改为「start-2 实测 0.53s；全程 sha 不变」。
**AC 判定**：AC-01 pass（复用+复演一致）· AC-02 pass（trace 80/0 复跑）·
AC-03 pass（20 轮门 5.4–6.3s 且行为口径全绿）· AC-04 pass（受限边界不变：
本轮仅 tests/docs 改动，产品/前端代码未动，Vue suite 12 红=基线同集结论仍成立）·
AC-05 pass（锚行/上下文/R-04 全部核对一致）——结论 needs_fix 仅因 **SD-02
知识增量文本的示例不实**，不能对含错误陈述的 Spec delta 发 pass。
**诊断检查点（连续两次 final review 未过，按协议前置）**：
- 链：R2 needs_fix（F-1/F-2）→ 修复 6395323/dcc7a6f/8dd5e25 → R4 needs_fix（F-3）。
- 漏因：F-2 修复时用**时间线相关**（16:31 件 ↔ 17:02 件）拼示例，未用「同一
  生成件」作对照；上一轮 review 只核了规则与数值表，未把「每个因果示例的 sha
  对必须共享同一生成源」列为核对项。
- 校正后的 oracle（下轮适用）：①锚节每个 sha/尺寸/指纹须能从
  plan-artifacts/plan-007/anchor-context.json + 在盘文件**逐项回推**（本轮已
  执行、全部命中）；②任何因果示例必须附「同一 `main.rs`/fingerprint」前提；
  ③该回推与同源前提写入复评清单。| next_responsible_role: work（F-3 文本修正，
  不触代码/发布件；修完直接回 review 复评）

2026-11-16 · stage: goal | plan_id: NOTES-007 | plan_revision: r1 | round: 4 |
from: review | to: work | status: executing | outcome: needs_fix |
worktree: D:/autostack/.wt/notes-007/auto-notes | commit: 8dd5e25 |
next: work（F-3：Spec 锚节示例改为同源对 02016f3a↔2e5e2898 + Plan 回执措辞）

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
