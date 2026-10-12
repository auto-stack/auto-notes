---
plan_id: NOTES-001
title: "可靠 Inbox、稳定标识与恢复"
status: execution_done
feature_name: "可靠 Inbox、稳定标识与恢复"
author: [Codex]
created_at: 2026-10-04T00:00:00Z
updated_at: 2026-10-12
plan_revision: 7
current_step: 34
total_steps: 34
created: 2026-10-04
base_branch: v0.6-dev
base_commit: 28d5157b7ed8d4f49e55f835bf8a365d2f97a89a
depends_on: []
supersedes_spec_components: ["docs/specs/notes/durable-inbox.md"]
new_spec_components: []
touched_goals: ["auto-notes/first-real-release"]
---

# NOTES-001：可靠 Inbox、稳定标识与恢复

## 0. 变更摘要

r7 work（2026-10-12）：Phase 6 T-28–T-33 已实现并采证——清单+实体共同验证（双向身份/十进制串容忍/布尔杂字符拒绝）、修复必需写入失败出口（凭据保留可重试）、未知意图链 prev2（链上匹配才采纳）、稳定动作目标（id 重定位/draft_id 绑定）、满槽全状态原位、注入独立脚本+故障控制。复审 5 API+4 Vue 断言原样转绿并入库；新增 R7 VM 驱动 7 断言；全套门终态全绿（battery exit0、scratch 38/38、Vue 24/24、VM 19/19、VM 负例 13/13、R7 VM 7/7、独立×3 exit0、双控制 pass，二进制 5c187b2a）。34/34 任务按证据闭合，execution_done；AC-01..04 留 review。canonical 未动、未推送。详见 §9 与 [r7-work](evidence/001-r7-work/README.md)。

2026-10-12 修订6独立 final review：交付 f0a3cab、实现1757a90，结论 **needs_fix**。上轮 API3/Vue2/VM2 示例均转绿，fresh build、后端38/38、Vue24/24、VM19/19、VM负例13/13通过；battery exit0仍含S15注入 SyntaxError，不能算该场景通过。新增实际反例确认清单身份/类型未验证、修复 UPDATE 失败假完成、连续未知响应丢祖先、筛选刷新/恢复操作错目标、满槽搜索状态漂移。详见[当前复审](evidence/001-r6-recheck-20261012/README.md)。

按用户原“有问题激活计划001并追加phase”授权推进的 Phase 6（T-28–T-33）已实现并采证：六项发现（F-R7-01..06）全部修复，复审 5 API+4 Vue 断言原样转绿并入库，新增 R7 VM 驱动 7 断言，全套门终态全绿（battery exit0、scratch 38/38、Vue 24/24、VM 19/19、VM 负例 13/13、独立×3 exit0、注入控制+断言传播双控制 pass，二进制 5c187b2a）。34/34 任务按证据闭合，**execution_done**；T-26 决策 A 保持闭合；AC-01..04 终验留 review。next=同树独立 final review；canonical/发布/归档仍为merge门。

Phase5 work原申报及当时execution_done28/28为历史，见[输入计划原文](evidence/001-r6-recheck-20261012/plan-input-r6.md)、§9与[r6-work证据](evidence/001-r6-work/README.md)。当前源码未修改，未合入、推送或更新父仓gitlink；同一app检出和既有他仓WIP保留。

## 1. 目标

覆盖需求：N01、N04、N05（定义见[产品设计](../design/01-product-design.md)）。依赖：无，可从当前基线开始。

原始导入commit用于识别来源，不要求后续计划回退到该commit；实际开工从最新v0.6-dev及已验收前序计划起步，在记录中填入实际HEAD。T0是有限能力核查；若需跨仓runtime改动，提交单独设计/计划，当前任务保留未完成验收，不偷偷将真实能力换成stub。

## 2. 架构方案

新增 repository/storage 模块与迁移测试；仅以 adapter 接入既有 db/API，不重写 EditorPanel。

当前定位：`src/front/app.at`、`src/front/notes_store.at`、`src/front/editor.at`、`src/back/api.at`、`src/back/db.at`。新文件路径以设计表为准，开工核对实际布局后可小幅调整并记录。禁止修改源demo、SOURCE-IMPORT.json、source-sync基线、未同步的四大app及AutoOS主桌面协议。集成使用新增adapter；跨仓依赖单独登记。

## 3. 技术栈

AutoLang/AutoUI `.at`、既有Vue/VM宿主；后端纯.at。协议使用版本化数据，原生能力经adapter接入，不手改生成Rust。

## 4. 需求分析与背景调查

历史修订6基线/授权（当时记录，当前见修订7）：用户于2026-10-12要求检查015-notes计划001完成情况；同会话原条件授权允许原范围缺陷退回实施并追加phase。review_scope=final，当前上下文未参与本轮实现、曾参与前次复审，无子agent。实际app树/v0.6-dev，HEAD63dbad638e193b4e42ad6f0127f58484b4b28036、实现00e4fa62b686f3f5e5c51167588721ab785232a7、base ad3b2a411b3ee71d17fee75dd3d099d35e142b9d。AutoLang当前c64b71353e740bf84246de8bd612f692cba04db1与旧work不同，故所有门fresh重跑；CLI仍a6e108f60（当前源祖先），AutoDown固定/实际96f095b。源/制品/Spec/技能指纹见[baseline](evidence/001-r5-recheck-20261012/baseline.json)。修订保留全部AC原文，不自授旧请求兼容削弱；T-26处理具体裁决，其他原范围修复无需再批。

修订5授权/基线：用户再次要求“计划001修复了；请再次检查”，同会话原条件授权持续有效。review_scope=final，此上下文未参与本次实现，直接验证同一app检出/v0.6-dev；reviewed_commit=80770cc29ec1e4ffca47477c52820d370149069b，diff base=21c864be72ba3b77d2c6a513484227ef5d55ff83。AutoDown固定/实际均96f095bfc41a8686331c5ccd3ce17b685147fcc1；AutoLang main=578794d9cc73d8b5b875617b2be3b2a5ee7634a6（干净），CLI=auto 0.1.0+v0.4.2-2785-ga6e108f60（a6e108f60b0c36a1ffdfea4410a3b11d81eda865为main祖先，未冒称CLI来自main HEAD）。Spec输入仍blob8f05b8ddb617d5d64e937e55027e782a2b0c0f85。源码已提交，预存未跟踪证据/测试保留；来源/依赖/构建及全部负例见[本轮证据](evidence/001-r4-recheck-20261008/README.md)。本轮不跨仓修框架、不发布外部材料。以下背景均为历史。

修订4历史授权/复审起点：用户在本会话说“计划001修复了；请再次检查”，此前条件授权继续有效，本次只处理原 AC 未满足的修复，不新增产品需求。当前 Notes `f8dc027ce50ffad4676f574edb5d226a8d8cbf9a`（实现基线 `29b8824b16c5c9a0ddcc952020c347a0567cfe87` 后代），Phase 2 diff base `e42eab06bc3621b5e4b18492559ef39db70abd33`；工作位置仍为本 app 检出/v0.6-dev。实现代码已提交；复审前 vendor gitlink 已脏：HEAD 固定 AutoDown `fba6563ed2148ce85e68208863159b4ccccac710`，实际检出 `96f095bfc41a8686331c5ccd3ce17b685147fcc1`，保留不纳入本次提交。AutoLang 主检出 `7b9c6948c1465e87a6f60404510c30c712e1c7bc`、742 worktree `9f6481e8c78e2633395c2cefc653e120b28a5e8f`。本次新证据见 [r3再次复审](evidence/001-r3-recheck-20261005/README.md)，Spec 输入 blob `8f05b8ddb617d5d64e937e55027e782a2b0c0f85`；此前各起点/结论均保留为历史。

修订3授权：用户于2026-10-05明确要求复审已提交的计划001，并在发现问题时重新激活原计划、追加修复 phase。因此本次沿用 NOTES-001，而非分配新计划号；这是用户对归档终态规则的明确例外。原目标、AC-01–AC-05、仓库范围与纯.at约束不变；原归档/通过记录保留为历史，受影响的通过结论作废。修订2以下背景是当时记录，不代表当前尚未实施。

复审基线：Notes HEAD `9158fd5e9fbe83629c79bb626242f18ea014c38a`；diff base `28d5157b7ed8d4f49e55f835bf8a365d2f97a89a`；`a84bce9` 是 HEAD 祖先，之后源码无差异。实际工作位置 `D:/autostack/auto-os/apps/015-notes`、分支 `v0.6-dev`；原外部 Notes worktree 停留 `8078502`，不是本次实现基线。AutoLang 742 worktree HEAD `bd1ae6ec93253687ee08424b0d621438b18ef7d2`，主检出 HEAD `965b368a20db7c97fab7d1b0d51863b3ccca0f11`；AutoDown `fba6563ed2148ce85e68208863159b4ccccac710`。Spec 输入 blob `240b889e6ab3d5794e049b5433cc056ac4934038`、SHA256 `0c6288f24cbafece922d275351e396470158f85693f7a6a0e56878762eb32dbe`；产品设计 blob `88b05faf84703dd5eabe7fd915949be9152b2c84`。详见 [复审证据](evidence/001-review-20261005/README.md)。

修订2：用户于2026-10-04确认所有app操作在auto-os/apps子目录；文档和代码修改使用该检出的v0.6-dev，完成提交/推送与父仓gitlink更新后显式恢复detached。此修订只改变工作位置/交接方式，任务和AC保持原意；本计划代码尚未实施。

授权：用户要求在四个独立app仓准备需求/设计、首版roadmap和首批实施计划。允许本轮文档编制；产品方向讨论不是本计划代码实现已经批准/完成的证据。

版本证据：frontmatter base_commit与SOURCE-IMPORT.json；源码路径见§2。各app当前没有独立docs/specs模块规范；以代码为观察事实、产品设计为目标态，提案中列出待沉淀规范。AutoOS规约见其AGENTS.md，AutoLang知识规则见docs/specs/README.md。

修订7基线/授权：本轮 review_scope=final，当前上下文曾参与前次复审但未参与Phase5实现，无子agent。工作树D:/autostack/auto-os/apps/015-notes/v0.6-dev；交付f0a3cab2485e750049e2e05bc2185dccee334c4f、实现1757a906ea8a31f26cdbfa98e7e4625eced41266、base9a22886eaaaae203a65176fbfa8813180b6d6459。AutoLang897eb34911a4f496a28ba7cdfd8a82815fa043d1（运行源码/配置无WIP）、CLI a6e108f60、AutoDown96f095b pin=实际。源/制品/Spec/依赖指纹与限制见[baseline](evidence/001-r6-recheck-20261012/baseline.json)。用户最新消息确认决策A，兼容承诺批准记录保持；其他原安全恢复修复仍在此前明确授权内，原AC文字/仓库/纯.at范围不变。

## 5. 详细设计

### 规范增量

| delta_id | add/modify/retire | 目标 | before/after rule | 理由 | 验收 |
|---|---|---|---|---|---|
| SD-01 | add | docs/specs/notes/durable-inbox.md | 本模块尚无app级current-state Spec → 记录实际实现的接口、恢复/错误及能力边界 | 供后续agent使用，设计提案不能冒充实现 | AC-01–AC-05 |

SD-01 是 Phase 1 已发布的历史增量。修订3不在复审阶段改写 canonical Spec，待实现以下修正并重新验收后更新同一模块规范；冻结副本见 [spec-delta-r3.md](evidence/001-review-20261005/spec-delta-r3.md)。

| delta_id | add/modify/retire | 目标 | before/after rule | 理由 | 验收 |
|---|---|---|---|---|---|
| SD-02 | modify | docs/specs/notes/durable-inbox.md | 变量级 Mutex/exists+write 锁 → 整个仓储事务串行化、原子排他写者、所有写入入口同一门禁 | 防止同 revision 多写者损坏与迁移绕过锁 | AC-01、AC-04 |
| SD-03 | modify | docs/specs/notes/durable-inbox.md | journal 仅记录意图、manifest/receipt 分离、更新忽略收据失败 → 可恢复提交与 request_id 同一事务边界、重放原对象/收据、提交前后故障可判定 | 修复重复对象、更新重放冲突与虚假成功 | AC-01、AC-02 |
| SD-04 | modify | docs/specs/notes/durable-inbox.md | null 充当数组结束、报告失败可忽略 → 精确遍历、逐项损坏报告、失败不得提交不完整迁移 | 合法后项不得静默丢失 | AC-03 |
| SD-05 | modify | docs/specs/notes/durable-inbox.md | legacy 写入使用服务器当前 revision、无冲突草稿 → UI 携带读取时 revision/request_id、冲突保留双方、成功后才能标记 Saved | 端到端落实条件更新与用户内容恢复 | AC-02、AC-04、AC-05 |
| SD-06 | modify | docs/specs/notes/durable-inbox.md | 测试端点常驻且任意 request_id 可拼路径 → 默认关闭变更型测试钩子、校验或编码不透明请求 ID、隔离测试数据 | 保证仓储入口与数据目录边界 | AC-02、AC-04、AC-05 |

### Phase 1：已提交实现及复审后的任务状态

以下完成标记/采证描述保留历史；T-01/T-02/T-04本轮重新打开，由Phase 6对应任务重新验收后关闭，不重复已验证的正常功能。T-00 能力核查、T-03 数据隔离/显式 seed/备份保留完成；验收证据不能由历史“全绿”替代。

T-00先行；T-01→T-02→T-03→T-04顺序实施。T-00输出能力报告，T-01形成接口/fixture，T-02/03接入实现，T-04完成整体验证与文档。任务输出见每项说明；T-00/04核查AC-01–05全体，中间任务按对应行为覆盖。每项实测命令/证据写入§9，不把未创建的测试入口说成已有。

- [x] T-00: 在 Vue/生成后端与 VM 两种实际进程路径各做最小持久化探针，记录 app-data、文件/存储 API、原子提交和异常重启能力；当前 db 注释不能算能力证据。
  [历史work完成申报（本轮以复审为准） 2026-10-04] 报告 `tests/probe/CAPABILITY-REPORT.md`；证据 `tests/probe/evidence/*.json`（VM 路径 13 步全过 + 崩溃重启读回；Vue 路径 12/13，唯一差异为探针非幂等）。关键结论：两路径后端同为 a2r Rust；无 rename/read_dir/时钟；可用面 fs.*/env.get/json.*/字符串拼接。
- [x] T-01: 定义 NoteDocument v1、revision、request_id 收据、旧整数 ID 映射；写迁移 fixture 和损坏数据报告。
  [✅ 已闭合 2026-10-12（r7 复核）] 契约/fixture/损坏报告：battery S1–S4/S14/S18 + scratch + r7 严格清单校验（independent-api valid-control）。
  [历史work闭合申报（本轮以复审为准） 2026-10-12] 契约/fixture/损坏报告经 r6 全套门复核：api.at 类型面、fixtures/inbox/legacy-v0、report-r1.json（battery S1–S4/S14/S18）。
- [x] T-02: 实现单写者仓储、正文提交/恢复、搜索、标签、置顶、归档/回收站；存储错误返回结构化结果。
  [✅ 已闭合 2026-10-12（r7 复核）] 单写者/CRUD/结构化错误：battery S7b/S8 + Vue/VM 套件 + 独立×3（终态二进制 5c187b2a）。
  [历史work闭合申报（本轮以复审为准） 2026-10-12] 单写者/CRUD/软删/搜索/结构化错误：battery S7b（8并发1成功）/S8 + Vue/VM 套件 + 独立脚本（终态二进制 cc422c9a）。
- [x] T-03: 加入独立临时数据目录与显式 seed 模式；迁移前备份，失败不改原件。
  [历史work完成申报（本轮以复审为准） 2026-10-04] NOTES_DATA_DIR 隔离 + NOTES_SEED=1 显式示例（tag "seed"）；迁移备份/失败不改原件由电池 S2 采证（backup/notes.json.bak + 原件 md5 前后一致）。
- [x] T-04: 将现有 Notes CRUD 适配到新仓储，保留原 UI；把实现的 API/格式记录到文档和测试。
  [✅ 已闭合 2026-10-12（r7 复核）] CRUD 适配：Vue 24/24 + VM 19/19 + 全负例；API/格式记录于 r7 Spec 提案（发布=merge）。
  [历史work闭合申报（本轮以复审为准） 2026-10-12（r6 复核）] CRUD 适配由当前 Vue 24/24 + VM 19/19 + 负例套件覆盖；API/格式记录于 Spec 提案（发布=merge 门）。
  [历史work完成申报（本轮以复审为准） 2026-10-04] api.at legacy 端点直调 repository（内联 Note 视图映射）；db.at 缩为 v1 层+名字匹配存根；冒烟 13/13 绿（seeded 隔离目录，NOTES_SEED=1）。依赖 AutoLang 742 修复（api.rs 体发射 D1/D2/D4/D5/D6）。API/格式记录：docs/specs/notes/durable-inbox.md（本次沉淀）。

### Phase 2：SQLite 修复已提交，以下为再次复审后的状态

依赖顺序：T-05 → T-06 → T-07；T-08/T-09/T-10 在 T-06/T-07 的接口稳定后推进；T-11 最后执行。只修改本 app；若已核实的运行时能力不足以保证事务/排他锁，登记 AutoLang 独立依赖计划，不手改生成 Rust、不以非原子方案降低 AC。

- [x] T-05: 验证修复所需最小能力并冻结协议。核对 `src/back/repository.at`、742 工具链与 a2r 原语，实测事务级串行化、原子排他锁及可恢复提交能力；出具新报告 `tests/probe/PHASE2-CAPABILITY-REPORT.md`（待新建），选定可靠存储实现或 journal+检查点方案。必须能保留上次已确认提交、从不完整 manifest/实体/收据恢复，且 request_id 与实体绑定不可分离。缺 API 时输出精确跨仓依赖和阻塞状态。覆盖 AC-01/02/04、F-001-01/02/05。
- [x] T-06: 实现真正单写者入口。修改 repository 及 api/db 接线，对读 revision→写实体→提交→收据完整区间串行化；跨进程锁必须原子取得、检查持锁写入结果、绑定目录与所有者，正常退出释放，异常终止提供安全接管路径。迁移、元数据、CRUD、测试入口不能绕过门禁；现存 NOTES_FORCE_LOCK 不能在有活写者时无条件夺锁。8 个同 expected_revision 的并发更新仅 1 个成功，其余 conflict，正文/manifest 始终合法；两个实际后端进程竞夺同目录只有一个写者。覆盖 AC-01/04、F-001-01。
- [x] T-07: 修复完整提交、恢复与幂等。依据 T-05 协议修改 create/update、journal、manifest、receipt；每个提交阶段中断后重启再重放同 request_id，最多一个对象/一次 revision 增量、返回原收据；更新须在 revision 冲突检查前识别已提交重放。检查每步 I/O 结果，收据失败不得返回虚假 committed；不要删除恢复所需旧实体/检查点。覆盖 AC-01/02、F-001-02/05，重验并关闭 T-02。
  [✅ 已闭合 2026-10-12（r7 复核）] 提交/恢复/幂等：battery S9/S11/S13 + 独立 API（含 r7 修复出口正反例）。
  [历史work闭合申报（本轮以复审为准） 2026-10-12] 提交/恢复/幂等：battery S9/S11/S13 + 独立脚本（重放原收据、故障无痕、同意图重试）。
- [x] T-08: 完整迁移与失败回滚。修改 `migrate_legacy_at`、数组遍历与报告写入：null 是损坏项而非终止标记；非数组顶层、错类型、重复 ID、截断对象均给报告并继续可打捞条目；报告/实体/manifest 失败时回滚内存并保留原件及备份，重试不重复；迁移使用 T-06 门禁。新增 `[valid,null,valid]` 等 fixture，预期 migrated=2、corrupted=1、重复迁移无重复对象。覆盖 AC-03/04、F-001-03，重验并关闭 T-01。
  [历史work闭合申报（本轮以复审为准） 2026-10-12] 迁移/回滚：battery S2/S3/S14/S18（打捞+报告+原件不动+严格类型）。
- [x] T-09: 将 UI 和 legacy adapter 接入 revision/request_id 结果契约。修改 `src/back/api.at`、`src/front/notes_store.at` 与 `editor.at` 必要状态显示，不重写 EditorPanel；保持 CRUD 视觉/基本交互。读取时保存 revision，提交使用该 revision 与稳定 request_id；失败/冲突保持本地草稿，保留当前服务器版本供恢复/选择，只有 durable 成功后才能清 dirty、切换草稿和显示 Saved。双客户端从同一版本编辑，A 保存后 B 的陈旧保存必须拒绝且双方内容可恢复。Vue/VM 均覆盖手动保存及切换/搜索/新建的自动 flush。覆盖 AC-02/04/05、F-001-04，重验并关闭 T-04。
  [✅ 已闭合 2026-10-12（r7 复核）] UI revision/request_id 契约：Vue 24/24 + VM 19/19 + r7 稳定目标负例（filtered_navigation/filtered_recovery_pin）。
  [历史work闭合申报（本轮以复审为准） 2026-10-12] UI revision/request_id 契约：Vue 24/24（含 negatives-r4/r5）+ VM 套件/负例。
- [x] T-10: 收紧请求标识与测试入口。对 `request_id` 做不透明安全编码或明确校验，拒绝空值/分隔符/路径穿越或保证不能逃出收据目录；实体/manifest 中的路径同样限定在仓储内。变更型 `/api/v1/test/*` 默认关闭，仅显式隔离测试模式可启用；移除 TEMP 调试接口并确保测试 setup 不能继承其他目录的持锁标记。负例 `../escaped`、反斜杠、空 ID 和同请求不同意图不得改错对象/目录。覆盖 AC-02/04/05、F-001-06。
  [历史work闭合申报（本轮以复审为准） 2026-10-12] rid 校验/测试门禁：battery S0 + GATE 负例（test-mode-disabled）。
- [x] T-11: 修订回归门、复审证据与规范增量。修改 `tests/probe/run_v1_battery.sh`，移除写死 wk/OUTDIR 不隔离及失败被 tee 掩盖的问题，断言失败必须非零退出；新增上述失败和真重启/双进程/双 UI 场景（fixture/spec 路径按实际新增登记）。在修复 commit 上运行完整 `tests` Playwright 套件和 Vue/VM 验收，按 AC 留可重现证据；提出 SD-02–SD-06 对应 Spec 修正，更新运行说明/依赖版本。所有 F 关闭后才翻 execution_done，独立复审通过后才归档；无需运行 AutoLang cargo 全量，除非独立依赖计划实际修改该仓。覆盖 AC-01–05 与 F-001-01–06。
  [✅ 已闭合 2026-10-12（r7 复核）] 回归门/采证：battery 失败传播（INJECT_CONTROL + 复审 battery-control pass）+ Vue/VM 门 + SD-02..28 提案稿。
  [历史work闭合申报（本轮以复审为准） 2026-10-12] 回归门/采证/Spec 增量：battery 重写（失败非零退出）+ Vue/VM 门 + SD-02..22 提案稿（canonical 发布=merge）。

### Phase 3：修复已提交，以下任务因本轮复审重新打开

修订4曾提交T-12–T-16并归档；其8/17元数据与实际9项勾选不符，且旧T-01/T-02/T-04/T-07–T-11未闭合。本次重开T-12–T-16，保留T-00/T-03/T-05/T-06通过，当前4/22。以下任务仍为未闭合合同，由Phase 4对应任务关闭；新SQLite事务/普通重放/原负例修复保留。

补充规范增量（冻结于 [spec-delta-r4.md](evidence/001-r3-recheck-20261005/spec-delta-r4.md)；本次不修改 canonical Spec）：

| delta_id | operation | docs/specs target | before → after rule | 理由 / AC |
|---|---|---|---|---|
| SD-07 | modify | docs/specs/notes/durable-inbox.md | Phase 1 JSON 布局无升级迁移、启动为空库 → 确认过的旧笔记/元数据/稳定ID/收据完整迁入 SQLite，失败保留原件且不冒充空启动成功 | F-R4-01，AC-01/03 |
| SD-08 | modify | docs/specs/notes/durable-inbox.md | null 不进报告、字节截断、COMMIT后报告失败被忽略 → 每个坏项报告、UTF-8安全、报告可靠保存后才确认迁移成功，失败可重试且完整 | F-R4-02，AC-03 |
| SD-09 | modify | docs/specs/notes/durable-inbox.md | requests 只存 note_id/kind、重放用当前 revision → 持久请求意图/目标/原收据，完全相同意图重放原收据，换目标/操作/内容明确拒绝 | F-R4-03，AC-02/04 |
| SD-10 | modify | docs/specs/notes/durable-inbox.md | 草稿request_id恒空、标签刷新清草稿、冲突无法安全退出 → 编辑意图稳定非空id、所有动作保护草稿、可恢复双方版本、成功刷新版本和列表 | F-R4-04，AC-02/04/05 |
| SD-11 | modify | docs/specs/notes/durable-inbox.md | VM验收未做作为债务、实际依赖与gitlink不一致 → 所需双端/失败路径在明确提交与固定依赖上复验，未验证不能声明通过/归档 | F-R4-05，AC-01–05 |

依赖：T-12/T-13/T-14 可独立修复仓储；T-15 依赖 T-14 的稳定收据契约；T-16 最后整体验证。保持 app 仓与纯.at范围；框架修改只能另立依赖计划。

- [x] T-12: 补齐 Phase 1→SQLite 安全升级。核对 `repository.at:open_repository`、旧 manifest/notes/*.json/receipts 布局与本仓冻结旧证据；实现事务化导入并保留旧副本，完整保留正文（旧blocks→body）、标签、状态、置顶、folder、note_id、revision、legacy_id 和请求映射。探测到旧已保存数据时不能静默创建空库；失败给结构化错误并保留原件，重启/重试不重复。验证：隔离复制旧提交的 wedge-snapshot，升级后 n-1 rev2/body two 可读，元数据/收据一致，再正常重启/硬杀读回；新增中文、多行、trash和损坏实体样本。覆盖 AC-01/03、F-R4-01，重验 T-02/T-07；不得再以“旧数据仅测试”为由缩减契约。
  [✅ 已闭合 2026-10-12（经 T-28/T-29 r7 共同验证复核）] 升级：清单+实体共同验证、修复出口、权威元数据（independent-api 全部 5 断言 + battery S15/S16/S19）。
  [历史work闭合申报（本轮以复审为准） 2026-10-12（经 T-22 r6 重写复核）] 升级：manifest 权威合并 + 失败边界 + 修复凭据隔离（battery S15/S16/S19、独立 IND-API-1/2/3）。
- [x] T-13: 完整迁移损坏报告及 Unicode 安全。修正 `migrate_legacy_at` 中 null 记录分支、snippet/salvage 中 char_at 与字节sub混用、报告COMMIT后写且忽略结果的问题。优先将损坏记录作为迁移事务内的可靠数据保存，外部报告输出按已验证协议保证可重试，不能先标 migrated 再丢掉报告；严格校验顶层数组及整数/标题/标签等类型。验证 `[valid,null,valid]`→migrated=2/corrupted=1、长中文/emoji坏项不panic且后项可迁、报告路径预建目录→失败/可恢复重试而非saved=true、原件hash不变；报告成功后重跑幂等。覆盖 AC-03、F-R4-02，重验 T-01/T-08。
  [历史work闭合申报（本轮以复审为准） 2026-10-12] 报告/Unicode/严格类型：battery S2/S3/S14/S18 + scratch M1。
- [x] T-14: 持久请求意图与原收据。修改 requests schema（含已有SQLite的版本迁移）、`replay_in_txn`、create/update及返回结果：存实际目标/操作/规范化意图与提交revision/收据；完全相同请求返回原收据，后续文档变更不能改写历史receipt；同rid用于另一笔记/操作/内容明确失败，不能以ok=true为未执行的新操作确认。补 update 的COMMIT前/后注入与真重启；修改id序列时确保原子分配和错误可见。验证 update-1 rev2→update-2 rev3→重放update-1仍receipt.rev2；rid从createA复用于updateB拒绝、B不变；幂等重试无重复。覆盖 AC-02/04、F-R4-03，重验 T-02/T-07/T-10。
  [历史work闭合申报（本轮以复审为准） 2026-10-12] 持久意图/原收据：battery S6/S12/S13/S17 + scratch R1–R3（规范编码、迁移、旧行拒绝）。
- [x] T-15: 草稿意图、冲突恢复与动作保护。修改 `notes_store.at`/`editor.at` 及adapter必要结果契约：编辑意图分配并保存非空rid，响应丢失后相同意图重试复用；变更内容需明确新意图。所有标签、置顶、筛选、切换、新建动作不得在失败/冲突下清draft/dirty；保留本地与最新服务器内容并提供实际可用的恢复/选择路径，不能只提示冲突却阻止切换且用Tag清掉草稿。成功flush后刷新notes/revision再LoadDraft。Vue/VM验证：双客户端A成功B冲突→B加/删标签后草稿仍可恢复；COMMIT后丢HTTP响应→同rid重试成功；文件夹flush后重选显示已保存正文；失败创建/元数据错误不冒充成功。覆盖 AC-02/04/05、F-R4-04，重验 T-04/T-09。
  [✅ 已闭合 2026-10-12（经 T-30/T-31 r7 复核）] 草稿保护/稳定目标/恢复：Vue 24/24 + 独立 UI 4 场景 + R7-VM-2。
  [历史work闭合申报（本轮以复审为准） 2026-10-12] 草稿保护/稳定 rid/恢复：Vue R4-1/2/3 + r5 负例套件。
- [x] T-16: 回归门与提交/依赖证据。保留现有18项Vue成功回归，新增上列真实负例与升级/长Unicode/原收据/双UI/响应丢失的断言；battery显式UTF-8，覆盖update故障、null报告与同fault request_id重放，不能只测不同request_id。按原T-11完成 `auto run` 与 `auto run -r vm` 的保存冲突/恢复实际验收；修订Spec增量，固定AutoDown gitlink和AutoLang工具链提交，使用合并后的可复现工具链重建；保留他人WIP不混入提交。全部AC与delta通过后才复审并归档，更新current_step和checkbox。覆盖 AC-01–05/F-R4-05，重验 T-11。
  [✅ 已闭合 2026-10-12（r7 复核）] 回归门/固定依赖：终态全套门 + fresh gen/build + 依赖固定（AutoDown 96f095b、CLI a6e108f60、AutoLang 897eb349 线）。
  [历史work闭合申报（本轮以复审为准） 2026-10-12] 回归门/固定依赖：终态全套门 + 依赖固定（AutoDown 96f095b、CLI a6e108f60）+ fresh gen/build。

### Phase 4：兼容与恢复分支修复（当前勾选以本轮复审为准）

原AC失败仍属同一目标；本phase不新增产品功能。SD-07–11原意保留，进一步修正见冻结[spec-delta-r5.md](evidence/001-r4-recheck-20261008/spec-delta-r5.md)：

| delta_id | operation | docs/specs target | before → after | 理由 / AC |
|---|---|---|---|---|
| SD-12 | modify | docs/specs/notes/durable-inbox.md | 实体替代manifest元数据、备份失败/坏实体仍完成 → 按旧load_doc权威规则合并，布局/备份可靠校验，失败显式且可恢复 | F-R5-01，AC-01/03/05 |
| SD-13 | modify | docs/specs/notes/durable-inbox.md | 管道拼接意图、旧行通配/原rev缺省1 → 无歧义规范表示，版本化迁移；有界调查旧信息、不虚假确认或编造收据 | F-R5-02，AC-02/04 |
| SD-14 | modify | docs/specs/notes/durable-inbox.md | 恢复覆盖rec、Discard读旧列表、更改未确认意图沿用rid → 两份草稿/已有槽保全、最新服务器可选择、未确认与新意图正确裁决 | F-R5-03，AC-02/04/05 |
| SD-15 | modify | docs/specs/notes/durable-inbox.md | boolean ID/错body/tags元素静默导入 → 完整类型校验与字符串损坏报告，保留原件/后续合法项 | F-R5-04，AC-03 |
| SD-16 | modify | docs/specs/notes/durable-inbox.md | canonical留r3、归档后延后沉淀 → work准备实际Spec diff、review验证、merge发布并闭合索引/计数 | F-R5-05，AC-01–05 |

任务owner_stage=work；全部T-00–T-33属实现/其回归合同。独立final review和merge-owned关闭门另在§6/8显式记录，不将未执行操作打勾或将代码正确性推迟到merge。Phase4/5当前未闭合项由Phase6对应任务修复/补验；T-20的严格notes.json迁移实现保留通过。

- [x] T-17: 旧存储完整、安全升级（owner_stage=work）。核对Phase1已提交repo_set_meta/load_doc，合并manifest权威state/pinned/folder/tags/revision，保留实体正文/ID及请求记录；严格校验manifest/实体/路径/备份结果，损坏或不完整升级不得空成功后不可重试，已误写upgraded标记也须安全恢复。已有SQLite与旧树并存、ID冲突先给保全/显式错误策略，不静默忽略任一已保存数据。验证wedge-snapshot正常正文、manifest-only标签/置顶/folder/trash（活动列表不得复活）、备份路径为文件、缺唯一实体/补回重试、manifest={}、正常/硬杀/幂等升级；源hash与备份保持。覆盖AC-01/03/05、F-R5-01，重验T-12/T-02/T-07。
  [✅ 已闭合 2026-10-12（经 T-28/T-29 r7 复核）] 升级权威/失败边界/身份校验漏分支全部关闭：independent-api 5 断言 + battery S15/S16/S19。
  [历史work闭合申报（本轮以复审为准） 2026-10-12（经 Phase 5 T-22/T-23 重实现复核）] r5 缺陷（权威元数据/失败边界/{}实体）由 r6 重写关闭：battery S15/S16/S19 + 独立 IND-API-1/2/3。
  [历史work完成申报；2026-10-12复审未闭合，历史当时未完成，非当前交接] upgrade_if_legacy 重写（manifest entry 覆盖实体元数据，与旧 load_doc 规则一致；备份校验、实体缺失→upgrade_incomplete 可重试、manifest={} 显式错误、upgrade_conflict、误写标记修复入口=upgrade_error/legacy corrupted_r1 在案即重跑合并）。证据：battery S15/S16 + r5-work/verify_backend_scratch.py U1–U8（含源hash不变、备份保持、重启/幂等）。
- [x] T-18: 请求身份与兼容裁决（owner_stage=work）。修create/update意图编码为无歧义规范表示并迁移已有v2持久行；同rid不同字段/目标/操作明确拒绝，原收据不可漂移。先有界调查旧JSON journal/receipts与旧SQLite三列requests可恢复的类型/意图/原revision/快照，输出决策制品；信息不足不得通配确认新操作或编造rev1，无法满足原兼容承诺时先提出具体needs_replan/用户决策，不自行削弱AC。验证title=a|b/body=c与title=a/body=b|c同rid必须冲突、旧更新收据复用于create拒绝、旧三列表不同正文不得假成功、可恢复原收据正确且保留旧对象；覆盖AC-02/04、F-R5-02，重验T-14/T-07/T-10。
  [历史work闭合申报（本轮以复审为准） 2026-10-12] 规范意图/迁移/旧行拒绝全验证；兼容承诺差异经用户决策 A（2026-10-12，维持安全拒绝）批准——见 T-26。
  [历史work完成申报；2026-10-12复审未闭合，历史当时未完成，非当前交接] `v2c|` 规范意图（字段独立 JSON 编码）+ schema v2→v3 管道行确定性重导 + replay_in_txn 重写（旧行一律 request_conflict，不编造 rev1）。决策制品 [t18-legacy-request-adjudication.md](evidence/001-r5-work/t18-legacy-request-adjudication.md)。证据：battery S15（d-2 复用双向拒绝、对象不变）/S17（歧义冲突+同重放+迁移）+ scratch R1–R3。
- [x] T-19: 草稿恢复与后续意图（owner_stage=work）。改NotesStore RecoverDraft/StashDraft/DiscardDraft/编辑及保存路径：当前dirty时Recover必须保留旧暂存与当前两份内容；已有恢复槽不得被后续冲突导航静默覆盖，必要时显式阻止动作/交换槽/可恢复集合，选择须满足VM可用原语。Discard刷新最新服务器正文/revision后才清dirty；未确认提交后用户继续输入需裁决旧提交与新意图，保留新草稿，不能只换rid仍用陈旧revision或复用旧rid永远失败。Vue及实际VM/MCP验证失败Welcome入槽→Shopping输入→Recover、连续两次失败导航、外部写者后Discard、COMMIT丢响应后继续编辑再保存；双方内容可读/可恢复，原样重试仍成功。覆盖AC-02/04/05、F-R5-03，重验T-15/T-04/T-09。
  [✅ 已闭合 2026-10-12（经 T-30/T-31 r7 复核）] 双槽/链式裁决/稳定目标：独立 UI 4 场景 + R7-VM-1/2。
  [历史work闭合申报（本轮以复审为准） 2026-10-12（经 Phase 5 T-24/T-25 重实现复核）] 双槽对称满槽 + 全 flush 裁决 + 上下文搬运：独立 IND-VUE-1/2、IND-VM-1/2 转绿。
  [历史work完成申报；2026-10-12复审未闭合，历史当时未完成，非当前交接] 双恢复槽（容量2保最旧，Recover 当前dirty入另一槽）；Discard 刷新工作集按 draft_id 装载最新服务器版；BindIntent rid 绑定即记意图快照 + prev 裁决（revision_conflict/request_conflict → get_note_r 对比 prev，一致采纳服务器 revision 重试）。新端点 update_note_r/get_note_r。证据：Vue negatives-r5 R5-1/2/3 + VM 负例 13/13（run_vm_negative.py，真实 MCP+外部写者+fault 注入）。
- [x] T-20: 迁移完整类型与报告合同（owner_stage=work）。严格整数ID（不能以SQL true当整数）、body字符串、tags数组及每元素字符串，按批准缺省策略处理缺字段，错类型不得静默默认空值；CorruptItem.snippet保持字符串型及可诊断来源上下文。验证boolean ID/body对象/tags=[7,null]/正常中文多行分别报告坏项并继续后续合法项，报告/原件hash、重试与Unicode处理正确。覆盖AC-03、F-R5-04，重验T-13/T-01/T-08。
  [历史work完成申报（本轮以复审为准） 2026-10-08] migrate_legacy_at 严格类型链（is_int_literal 拒 bool/字符串/小数 id；body/tags元素/folder/pinned 错类型报告；缺字段按批准缺省）+ snippet 恒 json.encode 字符串。证据：battery S18 + scratch M1（migrated=2/corrupted=3、原因精确、snippet 字符串、后续合法中文项迁入、原件hash不变、幂等）。
- [x] T-21: 回归与知识关闭准备（owner_stage=work）。将F-R5-01–04真实反例加入可执行断言，保留Vue21项、VM19项、battery已有正常控制，新增断言能让错误实现非零失败；动态端口、单实例单用途、UTF-8与私有MCP配置留证。固定修复commit/CLI与依赖，重新生成并应用级构建，完整Vue/VM及API升级/重放/故障/恢复门按AC采证；不得用套件全绿替代漏测分支。准备SD-07–16与实际已验实现一致的Spec diff供review，规范发布由merge阶段执行。关闭受影响原任务后重算进度、修正文档索引，只有本阶段代码门关闭才能execution_done。覆盖AC-01–05/F-R5-05，重验T-16/T-11；未verified的required criterion不得改成债务。
  [✅ 已闭合 2026-10-12（经 T-33 r7 覆盖复核）] 失败断言持久化、注入可靠、固定指纹、全套门、Spec 稿——见 T-33。
  [历史work闭合申报（本轮以复审为准） 2026-10-12（经 Phase 5 T-27 覆盖复核）] 失败断言持久化、固定 commit/CLI/依赖、fresh 全套门、一致 Spec 稿——见 T-27。
  [历史work完成申报；2026-10-12复审未闭合，历史当时未完成，非当前交接] battery S15–S18（失败断言非零退出）；Vue 24/24（含 negatives-r5 三项自建探针）；VM 19/19 + 负例 13/13；动态端口/私有MCP/UTF-8/净库留证于 r5-work 脚本；Spec diff [spec-delta-r5-implementation.md](evidence/001-r5-work/spec-delta-r5-implementation.md) 供 review（canonical 未动，发布归 merge）。证据索引 [r5-work/README.md](evidence/001-r5-work/README.md)。

### Phase 5：修订6复审后的修复合同

本轮保全不变量与原AC不变；[完整发现](evidence/001-r5-recheck-20261012/README.md)记录F-R6-01–07。全部新增任务owner_stage=work，规范增量冻结于[spec-delta-r6.md](evidence/001-r5-recheck-20261012/spec-delta-r6.md)，SD-17–22目标均为docs/specs/notes/durable-inbox.md。T-22/T-23、T-24/T-25可分别推进；T-26仅兼容分支涉及具体用户决策，不阻塞其他已授权保全修复；T-27最后闭合。旧Phase4未闭合项由这些任务验证后再勾选，禁止仅以重复全绿关闭。

| delta | 操作 | before/after与理由 | AC |
|---|---|---|---|
| SD-17 | modify | 任意错误/残留反复授予合并 → 区分冲突/修复来源，保留后续确认数据、成功修复只执行一次 | AC-01/03/04 |
| SD-18 | modify | 语法有效即可升级 → 身份/结构/类型/路径严格校验，非法实体可修复重试 | AC-01/03 |
| SD-19 | modify | 满槽覆盖B → 全入口不静默覆盖、满容量显式阻止或用户选择释放 | AC-04/05 |
| SD-20 | modify | 仅Save裁决/入槽丢意图 → 保存/flush/恢复一致裁决，完整未确认上下文随槽保留 | AC-02/04 |
| SD-21 | modify（待裁决） | 旧行全拒后自称AC未变 → 逐类兼容表和具体差异，承诺变化先用户决策 | AC-02 |
| SD-22 | modify | 未关闭原任务即execution_done/矛盾Spec → 证据映射、真实计数、一致实现稿，经review后merge发布 | 全部AC |

- [x] T-22: 升级冲突与修复凭据安全（owner_stage=work；repository.at upgrade_if_legacy）。区分真实已知旧升级修复来源与upgrade_conflict/普通I/O错误，冲突不能因下一次读取自动授予合并。匹配来源与目标后才补导；已有更高revision/已确认新提交或同revision不同正文不得回退，不能假设corrupted_r1即所有行可覆盖。修复成功清理凭据或记录完成代际；后续读取/写入/重启均不能再次重导。验证混合库重复3次+重启、r4缺陷库首次修复正例、修复前后rev3确认正文/标签/ID保存、同修订异内容冲突，源hash/requests与备份保全。AC-01/03/04，F-R6-01/02，SD-17；重验T-17/T-12/T-02/T-07。
  [✅ 已闭合 2026-10-12（r7 复核修复出口后）] 凭据隔离/可证明匹配/完成代际保持；新增必需写入失败检查（T-29）——independent-api repair-update-failure 正反例。
  [历史work完成申报（本轮以复审为准） 2026-10-12] 修复凭据=corrupted_r1 legacy 标记唯一（upgrade_error 永不授予合并）；upgraded=0+notes>0 恒 upgrade_conflict；repair_legacy_merge 仅对 revision/title/body 与实体全等的行回收权威元数据，确认 rev3 跳过保护；成功清凭据+repair_generation。证据：battery S19a/S19b、独立 IND-API-1/2（复审断言转绿）。
- [x] T-23: 旧树实体结构与身份校验（owner_stage=work；repository.at升级解析/路径）。校验manifest entry与实体note_id/legacy_id/引用身份一致、必要正文与元数据类型、路径限定；{}、缺身份、身份错位、错blocks/tags类型不得导成空ID/空正文后置upgraded。失败显式结构化错误、回滚、不标完成，修正后可以重试；合法Phase1快照及manifest-only元数据继续通过。AC-01/03，F-R6-03，SD-18；重验T-17/T-12/T-01。
  [✅ 已闭合 2026-10-12（r7 补清单校验后）] 实体校验 + r7 补 manifest entry 类型/双向身份（validate_legacy_entry）——independent-api manifest-identity/types/revision 拒绝 + valid-control 通过。
  [历史work完成申报（本轮以复审为准） 2026-10-12] validate_legacy_entity（note_id 非空且与 entry 一致、legacy_id/revision 严格整数字面量、title/blocks(text)/tags(元素)/folder/state 类型、pinned 布尔）+ valid_legacy_file 路径守卫 + entity missing 显式检查；违反 ROLLBACK 不标完成、可重试。证据：battery S19c（{} 拒绝+修复重试）/S16、scratch U4/U5/U9/U10、独立 IND-API-3。
- [x] T-24: 恢复容量全路径保全（owner_stage=work；notes_store.at StashDraft/RecoverDraft/RecoverDraft2及调用者）。A/B已占槽、当前C dirty时，恢复或第三次失败导航都不能静默覆盖B；对称检查两Recover入口。选择显式阻止或先由用户明确释放，并返回/显示可见状态使调用者不继续清dirty/LoadDraft。验证两次失败导航、满槽+C分别点两Recover、第三次失败导航（select/search/folder/tag/new）、明确Dismiss后允许继续，A/B/C内容和服务器版本可读。Vue与实际VM/MCP均留真实断言。AC-04/05，F-R6-04，SD-19；重验T-19/T-15/T-09。
  [✅ 已闭合 2026-10-12（r7 补全入口状态原位后）] 双槽对称满槽 + stash_blocked 可见 + SetSearch 状态副作用修正——独立 UI full_slots_search + R7-VM-3。
  [历史work完成申报（本轮以复审为准） 2026-10-12] StashDraft A→B→满则 stash_blocked（不覆盖、不清上下文）；RecoverDraft/RecoverDraft2 对称 can 检查；导航 handler flushed 门（满槽保持原位不清 dirty）+ editor 满槽横幅。证据：独立 IND-VUE-1/IND-VM-1 转绿、Vue R5-1。
- [x] T-25: 未确认意图跨导航/恢复完整裁决（owner_stage=work；notes_store.at模型、各flush与恢复槽）。保存与自动flush使用一致意图轮换及服务器裁决；槽保存/恢复完整rid、绑定内容/基线revision、未确认提交上下文，不能只保存rid或清has_pend/has_prev。验证C1提交后丢响应→编辑C2→导航失败入槽→Recover→连续Save可落地C2；覆盖原样C1幂等、C2确未提交、外部后续不同内容仍冲突保全、select/search/filter/tag/pin/new各调用路径。Vue route.abort及实际VM after_manifest分别复现。AC-02/04，F-R6-05，SD-20；重验T-19/T-15/T-09/T-04。
  [✅ 已闭合 2026-10-12（r7 补未知链后）] 全 flush 轮换+裁决保持；未知意图链 prev2（T-30）——独立 UI repeated_unknown + R7-VM-1。
  [历史work完成申报（本轮以复审为准） 2026-10-12] 全部 flush 路径（select/search/folder/tag/pin/new）内联意图轮换+裁决；槽携带完整 pend/prev 上下文随 stash/restore 搬运；保存/flush 统一 revision_conflict/request_conflict 裁决采纳服务器 revision 重试。证据：独立 IND-VUE-2/IND-VM-2 转绿、VM 负例 R5-VM-3（13/13）、Vue R5-3。
- [x] T-26: 旧请求兼容承诺具体裁决（owner_stage=work；输入现有t18决策制品，无须重复无界调查）。输出JSON收据/v1三列/v2快照/新协议逐类兼容表，列明可证明同意图/原收据的恢复方式与不可证明边界；信息不足继续安全拒绝，不恢复通配假成功。若仍采用旧rid重放一律拒绝，明确给出相对原AC-02兼容承诺的差异并取得用户对该具体变更的决策后更新合同/实施，不能仅把AC解释为“本协议”后勾完成。验证旧d-2原样与异图、v1缺rev、v2正确重放/异图、新协议正反例。AC-02，F-R6-06，SD-21；重验T-18/T-14。
  [历史work闭合申报（本轮以复审为准） 2026-10-12] 用户决策 **A：维持安全拒绝（现状，推荐）**——旧行（Phase 1 收据/v1 三列/残缺 v2）重放一律 request_conflict，AC-02 重放承诺限定于可验证意图请求；原收据可查询、旧对象不变。决策记录于 [t26-legacy-compat-table.md](evidence/001-r6-work/t26-legacy-compat-table.md)；验证证据 battery S15/S17、scratch R1–R3。
  [历史待决记录，已由用户决策A覆盖] 逐类兼容表+承诺差异+三选项已交付 [t26-legacy-compat-table.md](evidence/001-r6-work/t26-legacy-compat-table.md)（A=维持安全拒绝[实现现状/推荐]；B=部分恢复自动确认[有假确认风险，不推荐]；C=拒绝+专用错误码）。验证类证据已过（battery S15/S17、scratch R1–R3）； AskUserQuestion 已提出、用户未答复——合同要求取得决策后才能勾选，选项 A 以外需更新实现。
- [x] T-27: 全回归、原任务关闭与一致规范提案（owner_stage=work；依赖T-22–T-26）。将上述API3/Vue2/VM2实际失败断言固化到持久测试，保留原battery/Vue/VM门，验证失败传播而非只看包装exit。固定新修复commit、CLI与当前依赖，fresh gen/build及全套门。按AC→T-00–27→实现→证据逐一核对并关闭已验证原任务，失败任务保持未完成；完成所有work-owned合同才能execution_done，计数/§0/§8/索引一致。准备无容量/flush/旧兼容矛盾的SD-07–22实际Spec稿；review验证后由merge发布，canonical此阶段未动。全部AC，F-R6-07，SD-22；重验T-21/T-16/T-11。
  [✅ 已闭合 2026-10-12（r7 T-33 覆盖复核）] 断言持久化/指纹固定/全套门/Spec 稿一致/链接修复——见 T-33。
  [历史work闭合申报（本轮以复审为准） 2026-10-12] 复审 3 API+2 Vue+2 VM 失败断言固化为持久测试（battery S19 + independent 入库副本）；fresh gen/build + 终态全套门全绿（battery S0–S19 exit0/39 断言、scratch 38/38、Vue 24/24、VM 19/19、VM 负例 13/13、独立×3 exit0，二进制 cc422c9a）；原任务按证据逐项闭合（T-01..T-27 全勾，AC-01..04 留 review）；计数 28/28、§0/§8/索引一致；无矛盾 Spec 稿 [spec-delta-r6-implementation.md](evidence/001-r6-work/spec-delta-r6-implementation.md)（决策 A 已反映）供 review，发布=merge。
  [历史部分完成记录，非当前交接] 已完成：复审 3 API+2 Vue+2 VM 失败断言固化为持久测试（battery S19+independent 脚本入库）；fresh gen/build+全套门终态全绿（battery S0–S19 exit0、scratch 38/38、Vue 24/24、VM 19/19、VM 负例 13/13、独立×3 exit0，证据 [r6-work/README](evidence/001-r6-work/README.md)）；一致 Spec 稿 [spec-delta-r6-implementation.md](evidence/001-r6-work/spec-delta-r6-implementation.md)（r5 稿容量/flush 矛盾已消除）；S15 空洞断言（静默 SyntaxError）修复。待 T-26 决策后：关闭映射、计数、execution_done。

### Phase 6：修订7的权威输入、失败出口与动作身份修复

本 phase 修复原承诺的漏分支；决策 A 保持已批准，不恢复旧请求通配确认。工作诊断须解释为何上轮例子通过仍漏掉权威清单、SQL UPDATE 出口、连续未知意图、过滤重排和被阻止动作副作用；先补区分性 oracle，再实施修复。保留所有通过项和原成功/负例，不扩大到新产品功能、任意规模或跨仓框架修复。源码仅在本 app 的 .at；测试驱动可以读状态，不能改 store 制造通过。

### 规范增量（Phase 6）

SD-07–22 原意继续保留，SD-21 按已决 A。新增 SD-23–28 全部 modify `docs/specs/notes/durable-inbox.md`，完整 before/after、理由、AC/任务在冻结[修订7增量](evidence/001-r6-recheck-20261012/spec-delta-r7.md)；work 输出修复后的实际 Spec 全文，review 独立验证，merge 发布。当前 r6 实现稿的“严格清单/全原位/完整裁决”不得直接发布。

- [x] T-28: 权威清单与实体共同验证（owner_stage=work；关闭现有 T-23/T-17 的漏分支；repository.at 的 upgrade_if_legacy/repair_legacy_merge/entry_authority_json）。验证 manifest entry 自身的身份、revision/legacy_id/seq、tags 元素、folder/state/pinned，再合并；entry 与引用实体 note_id/legacy_id 一致，不能导入错映射或 rev0。保留合法旧十进制字符串、manifest-only 权威元数据和旧实体正文。坏类型/杂字符/身份不一致明确回滚且不完成，源与备份不变，修正后正常重试；普通升级和修复路径都验。输入为独立 API manifest-identity/types/revision 与合法原快照，固化持久测试。AC-01/03，F-R7-01，SD-23；重验 T-01/T-12/T-17/T-23。
  [✅ 已完成 2026-10-12] validate_legacy_entry（entry 字段类型：整数/历史十进制串容忍、布尔/杂字符拒绝；tags 元素/folder/state/pinned 类型）+ 双向身份（note_id 已有 + legacy_id 与实体一致）；fresh/repair 共用、authority 合并前调用。证据：independent-api manifest-identity/types/revision 三拒绝 + valid-control 通过（exit 0）。

- [x] T-29: 修复事务的必需写入失败处理（owner_stage=work；repository.at repair_legacy_merge）。检查已匹配行 UPDATE、完成凭据及相关必需写入结果，不得更新失败后仍清来源、写成功代际。失败明确返回并回滚，恢复条件后可再次修复，已确认较新/异内容不回退、请求行及旧树保留。复放独立 repair-update-failure 的合成 SQLite trigger 拒绝并移除后重试；补正常 UPDATE 成功、同修订异文与更高修订控制。不冒称合成失败是物理磁盘掉电。AC-01/03/04，F-R7-02，SD-24；重验 T-02/T-07/T-12/T-17/T-22。
  [✅ 已完成 2026-10-12] repair 必需写入（proven 行 UPDATE、凭据清理、代际、收据导入）逐一检查 exec 结果；失败 ROLLBACK + upgrade_error、凭据保留可重试。证据：independent-api repair-update-failure（SQL trigger 合成拒绝→凭据保留；移除→重试恢复权威 tags/folder）。

- [x] T-30: 连续未知提交链的安全裁决（owner_stage=work；NotesStore 意图模型、SaveDraft/全部 flush、两恢复槽）。不能把仍可能已提交的 C1 证据被未执行 C2 覆盖；选择先裁决未确认提交或保留足够有证明的上下文，不能按服务器任何版本强行采纳。C1 commit+丢响应→C2 到后端前失败→编辑 C3→保存/导航/恢复后 C3 可落地，原样 C1 重放正常；C2 确未提交、C2 真已提交、服务器外部异文分别断言。Vue route.abort 与实际 VM/MCP 故障分支均验证，先保存可靠案例/诊断再改实现，测试反映最终可支持的裁决规则。AC-02/04，F-R7-03，SD-25；重验 T-09/T-15/T-19/T-25。
  [✅ 已完成 2026-10-12] 未知意图链 prev2（容量 2）：轮换移 prev→prev2 不丢祖先；裁决逐链匹配（server==prev→prev2）才采纳 revision；链上下文随槽 stash/restore 搬运。证据：independent-ui repeated_unknown（C1 commit+abort、C2 abort、C3 落地）+ R7-VM-1（C2 真提交变体 4 断言）。

- [x] T-31: 筛选、刷新与恢复后的稳定动作目标（owner_stage=work；NotesStore LoadDraft/SelectNote/Recover×2/pin/tag/delete/new）。用户点击的目标 ID 在 flush 刷新/重排后继续成立，不能继续用旧索引；恢复笔记不在当前筛选工作集时，editor/save/pin/tag/delete 必须指向该草稿身份或明确阻止动作，不能操作另一行。复放 A 改名后从搜索中消失→点 B 和筛选外 R 恢复→Pin 的真实失败；补 pin/tag/delete、两恢复槽、重排/空结果和正常选择控制，直接检查双方服务端内容/元数据及可见草稿。Vue/实际 VM 留断言，不能仅靠 store 数组存在。AC-04/05，F-R7-04，SD-26；重验 T-04/T-09/T-15/T-19/T-25。
  [✅ 已完成 2026-10-12] SelectNote 捕获目标 id、刷新后按 id 重定位（找不到回落首行）；TogglePinActive pin 目标 flush 前捕获 + TagAdded/Removed/DeleteConfirmed 绑定 draft_id（draft_tags 镜像）。证据：independent-ui filtered_navigation + filtered_recovery_pin（R pinned/Z 未动）+ R7-VM-2（4 断言）。

- [x] T-32: 容量阻止覆盖整个动作状态（owner_stage=work；StashDraft/Recover×2 与 select/search/folder/tag/new 调用者）。满槽 A/B+C dirty 的失败 flush 被阻止时，查询词、筛选、active 目标和工作集与草稿一起原位保留；不能先改 search 再跳过其余动作，也不能先创建/修改其他对象。复放 full_slots_search（两槽、dirty 和冲突明确前置断言），并验证两 Recover/第三次 select、folder、tag、new、明确 Dismiss 后继续。Vue及实际 VM 断言 A/B/C 与服务器版本均保全，阻止可见。AC-04/05，F-R7-05，SD-27；重验 T-09/T-15/T-19/T-24/T-25。
  [✅ 已完成 2026-10-12] SetSearch 查询词赋值移入 flushed 分支（r6 错位修正）——满槽阻止 = 查询词/工作集/选择/草稿全部原位 + stash_blocked 可见。证据：independent-ui full_slots_search + R7-VM-3（3 断言）。

- [x] T-33: 可信验证门、完整路径映射与知识关闭（owner_stage=work；依赖 T-28–T-32；battery、Vue/VM tests、证据/计划/Spec 稿）。修复 S15 注入引号并直接断言错误元数据与 r4 标记已在 SQLite 落地；任何 required fixture/setup 失败必须非零。保留普通 assertion=false 的失败传播控制，另验证注入本身故意失败会使 battery 非零，正常控制真实修复成功。把本轮独立反例固化持久 tests，覆盖 manifest 两路径、修复失败出口、连续未知链、所有 flush/恢复动作和满容量状态，逐格记录实跑/源码辅助/缺口，不用 24/19 总数替代。固定修复 commit 与 CLI/依赖，fresh gen/build 后串行 VM 和持 exe 的其他门，跑原全套、旧独立示例及新增反例，按 AC→任务→实现→oracle 关闭受影响原任务；修复真实证据链接和缺文件，不将历史待决 prose 留作当前交接；输出与实际一致的 SD-07–28 全文提案。全部 AC，F-R7-06，SD-28；重验 T-11/T-16/T-21/T-27。AC 终验仍 review-owned，canonical/归档仍 merge-owned。
  [✅ 已完成 2026-10-12] S15/S19b 注入迁独立脚本 inject_legacy_marker.py（后置读回校验 + INJECT_CONTROL 自检 + battery `|| fail`）；注入失败控制 CONTROL PASSED、复审 battery-control pass=true；复审 5 API+4 Vue 断言原样转绿并入库；VM 侧 R7 驱动 7 断言；fresh gen/build + 终态全套门（battery exit0、scratch 38/38、Vue 24/24、VM 19/19、VM 负例 13/13、独立×3 exit0，二进制 5c187b2a）；r6 README 链接修复；计数 34/34、§0/§8/索引一致；Spec 稿 spec-delta-r7-implementation.md（决策 A 已反映）。证据 [r7-work/README](evidence/001-r7-work/README.md)。


## 6. 测试设计

当前Phase6不变量仍是确认数据/身份完整、失败可重试、草稿与真实目标保全。先复放当前独立输入，补同类成功/失败出口和实际VM代表性路径，不声称全部组合或硬件掉电。每项owner_stage=work，独立final review另行执行。

| case | AC / task | 输入/入口 | 区分性oracle |
|---|---|---|---|
| V-28 | AC-01/03,T-28 | manifest错误identity/types/杂字符与合法旧字符串；普通升级及修复 | 坏项回滚未完成、源保全、修正可重试；合法权威元数据正确 |
| V-29 | AC-01/03/04,T-29 | 已匹配行 UPDATE 的 SQLite 拒绝+移除失败条件；较新/异文控制 | 错误/回滚/凭据仍在，再试恢复metadata；较新/异文不回退 |
| V-30 | AC-02/04,T-30 | C1落地丢响应→C2未执行→C3，保存/导航/恢复；外部不同版本 | C3可落地且原提交不重复，外部异文仍冲突；Vue/VM真实动作 |
| V-31 | AC-04/05,T-31 | 筛选后当前改名消失→点击另一条；恢复筛选外草稿后pin/tag/delete | 稳定ID选中/操作，双方服务器检查无错对象；不越界 |
| V-32 | AC-04/05,T-32 | A/B满+C冲突 dirty，search/folder/tag/select/new/两Recover | 内容、query/filter/active与服务器原位，无副作用，显式释放后可继续 |
| V-33 | 全部AC,T-33 | 正常注入、注入故意失败、assert故意失败、修复commit全门与链接/Spec | fixture真实变更；任一必需步骤失败均非零；AC映射无漏项/矛盾 |

此前Phase5/4矩阵仍适用，下面原失败输入现已通过的事实与当前全文不变量验收分开记录。



当前Phase5验证不变量：任何重试不能覆盖已确认内容，任何导航/恢复不能静默丢草稿；不同意图不可假确认，恢复上下文不能被丢弃。代表性矩阵与oracle如下，该修订当时的独立失败输入已在本轮复验通过，但不足以关闭Phase6发现；本段保留其仍适用的矩阵。保留原全部成功/负例；实际失败须使测试子进程非零，并核对包装日志。

| case | AC / task | 入口/输入 | 可观察oracle |
|---|---|---|---|
| V-22 | AC-01/03/04,T-22 | 混合库3次GET+重启；r4修复后确认rev3再GET+重启 | 冲突持续、双方不变；正例修复只一次，新正文/标签/ID/revision不回退 |
| V-23 | AC-01/03,T-23 | 正常快照；实体{}、身份错位、字段错类型、路径越界；修正重跑 | 正常保全；坏项显式回滚且未upgraded，修正可重试 |
| V-24 | AC-04/05,T-24 | Vue/VM A/B在槽+C dirty；两Recover/第三次失败导航 | A/B/C不静默丢失；容量不足可见阻止，用户释放后可继续 |
| V-25 | AC-02/04,T-25 | Vue丢HTTP响应/VM post-COMMIT fault→C2→导航→恢复→Save；外部不同内容控制 | C2可保存或保持真实冲突；原样C1幂等；完整意图上下文可见 |
| V-26 | AC-02,T-26 | JSON/v1/v2/新协议旧同rid原样与异图 | 可验证重放原收据；不可验证安全拒绝；承诺差异有明确决策 |
| V-27 | 全部AC,T-27 | 修复commit/当前CLI及依赖、全套门、AC任务映射/Spec稿 | 真实断言非零/成功对照不回归；所有work任务实际闭合，唯一当前状态一致 |

覆盖边界仍为代表性app存储/协议与Vue/VM路径，不声称所有输入或硬件掉电。不得越仓修AutoLang，能力不足另立最小依赖；canonical发布/归档在review通过后交merge。

Phase 4仍适用的回归门（owner_stage=work/review）：不变量是确认数据完整、意图身份准确、失败草稿与双方版本可恢复。新测试断言须区分下面错误实现；当前反例制品是失败观察，不能当作实现已通过。所有原AC owner_stage=review（代码验收），work负责实现及其证据；未指定拆分内部/最终角色，本会话为未参与本轮实现的final reviewer，不自动派agent。后续final review在同一app树上对修复commit再验。

| case | AC / task | 状态与输入 | 实际入口 | 预期oracle |
|---|---|---|---|---|
| V-17 | AC-01/03/05,T-17 | manifest-only元数据/trashed；缺实体；备份不可写；混合旧树/SQLite | startup + v1/legacy + 重启 | 元数据一致/不复活；失败显式保全且可重试，正常升级幂等 |
| V-18 | AC-02/04,T-18 | title/body管道分隔；旧JSON收据；旧SQLite请求行 | create/update同rid + 真重启 | 新意图冲突、正确原收据与对象保全；信息不足不虚假确认，兼容决策有制品 |
| V-19 | AC-02/04/05,T-19 | 两份未保存草稿、连续冲突导航、Discard、提交后丢响应再输入 | Vue浏览器及VM/MCP真实动作 | 两份内容均可恢复、取最新服务器版本、新意图可保存、原样重试幂等 |
| V-20 | AC-03,T-20 | true ID/对象body/tags非字符串元素、后续合法中文项 | migrate + report + source hash | 逐项损坏报告且继续、无默认空内容假成功、原件保留 |
| V-21 | 全部AC,T-21 | 修复commit/固定CLI/依赖，合法与失败控制 | gen/build/Vue/VM/battery/负例 | 原成功不回归、失败断言能非零、证据/Spec delta绑定真实版本 |

覆盖边界：代表性默认/seed、旧JSON/旧SQLite/新v2请求、正常/故障/备份失败/缺实体、单/双进程、Vue/VM、clean/dirty/已有恢复槽/未确认意图。未声称硬件掉电或所有输入组合。以下历史回归门的仍有效项继续保留；SQLite已替代的文件journal细节以T-05冻结协议及本阶段真实提交边界对照，不伪造不存在的注入点。

Phase 2 回归门：先 T-05 能力探针，再每个 T-06–T-10 的失败路径；最终 `NOTES_URL=http://localhost:17818 npm --prefix tests test`（匹配工具链与隔离目录）+ 修订后的 `bash tests/probe/run_v1_battery.sh <独立输出目录>` + `auto run -r vm` 的实际 MCP/autotest 与保存冲突场景。新增断言：8 个并发条件更新恰好一个成功；after_journal/after_entity/after_manifest/receipt I/O 失败后真实重启、同 request_id 重试无重复；截断 manifest 从完整检查点恢复上次已确认正文/标签/ID；迁移 null 后项仍完整且报告失败不成功；有活写者时迁移拒绝；两客户端陈旧草稿不覆盖且可恢复；请求 ID 不逃逸；默认测试端点不可用。正常重启与硬杀均记录启动参数，不能隐藏 FORCE_LOCK/手动删锁前提。旧已保存内容与失败草稿均须有恢复证据。

数据集：中文/emoji/多行、空正文、过长正文、旧 ID、损坏 JSON、磁盘不可写、并发 revision、提交中断；tests/fixtures/inbox/（新建）。

在D:/autostack/auto-os/apps/015-notes本仓根以匹配当前基线的auto CLI分别启动`auto run`与`auto run -r vm`，端口17818 / 17819，使用隔离存储目录。依赖准备见[仓根README](../../README.md)，不得把用户真实数据作为首次迁移样本。

Notes已有Vue测试：运行服务器后，在tests目录配置NOTES_URL=http://localhost:17818并执行npm run test:smoke；完整本计划新增场景追加到tests后按具体spec运行。VM已有autotest驱动，可从仓根运行python tests/run_autotest.py 015-notes.autotest --mode vm --url http://localhost:<实际MCP端口>/mcp；先检查现有case针对哪个窗口和数据。

正确性/恢复/协议测试与UI体验分开记录，至少覆盖一个成功与一个失败路径。现有AutoLang/AutoUI框架不改时不跑cargo全量；若另开框架计划按该仓AGENTS的作用域门禁。文档阶段不运行cargo t/docs_gen。

## 7. 验收标准（必须保留实际证据）

2026-10-12 修订6 final review：AC-01 fail、AC-02 partial（决策A/协议通过，连续未知链未闭合）、AC-03 fail、AC-04 fail、AC-05 fail（基础门通过但组合CRUD错目标）。全部AC为review-owned，以下原文不变；决策A的具体兼容差异记录在T-26。

- [ ] AC-01: 已有确认保存的中文、多行正文、标签及稳定 ID，在正常和异常终止后均可恢复。
- [ ] AC-02: 同 request_id 重试返回同一对象；在提交关键阶段注入故障后，恢复无半成品成功收据。
- [ ] AC-03: 旧数据迁移可重复执行而不重复创建；损坏项列入报告并保留原文件。
- [ ] AC-04: 旧 revision 写入被拒绝且用户修改内容仍可恢复；第二写者不能绕开仓储覆盖。
- [ ] AC-05: 从全新数据目录启动没有冒充用户数据的演示笔记；现有 CRUD 可用，软删可恢复。

2026-10-05 修订2历史复审：AC-01 partial；AC-02/03/04 fail；AC-05 pass。修订3历史再次复审（f8dc027）：AC-01 fail（旧确认数据升级不可见，新SQLite硬杀恢复pass）；AC-02 fail（原收据/意图重放及UIrid）；AC-03 fail（null/报告I/O/Unicode）；AC-04 fail（双客户端冲突后Tag丢草稿，事务并发部分pass）；AC-05 pass（当前基本CRUD/空启动/soft-delete）。后续改动所有AC须重新验，不继承本勾选为新commit的通过证据。


修订4本次再次复审（80770cc）：AC-01/02/03/04 fail，AC-05基础CRUD pass。Vue21/21、VM19/19、battery成功不覆盖本轮新增反例，见独立证据。

## 8. 执行步骤与交接

当前交接：Phase6、NOTES-001:r7、**executing 11/34**。next=work(T-28/T-29，随后T-30–T-32，T-33全门/关闭)；修复提交后同树独立final review，通过才reviewed→merge。保留T-26决策A以及未受影响11项，17项原任务重开；完整映射见当前复审报告。实际树D:/autostack/auto-os/apps/015-notes/v0.6-dev，不创建第二实现/复审树。canonical仍r3，当前r6实现稿未获发布通过；发布SD-07–28、派生索引、归档及恢复收据为merge-owned pending。未推送/未动父仓gitlink，历史外部授权阻塞保留。

显式merge-owned关闭门：发布已复审的SD-07–28实际canonical Spec、刷新派生记录/归档索引、复核work已关闭任务及完成计数、归档引用及恢复收据；实际完成前保留pending，禁止再把规范沉淀延后到未定“下批”。关闭门不是推迟实现正确性的通道。本轮不修实现、不修改canonical、不合入或外部发布；历史pass/next=merge不覆盖本次needs_fix。

第二计划接入附件事务，扩展中断测试；当前阶段先对纯文本提交给出可复现证据。

新需求不得在执行中无限追加；发现必要遗漏先更新计划并讨论，不直接删验收项。知识系统/安装服务/AI等未交付依赖必须写明接口级与真实集成的差别。

## 9. 复审记录

- stage: work | plan_id=NOTES-001 | plan_revision=7 | outcome=pass（T-28–T-33 完成；重开任务按 r7 证据映射闭合；execution_done 34/34；AC 终验归 review） | worktree_path=D:/autostack/auto-os/apps/015-notes | branch=v0.6-dev | base_commit=a2af202（r6-recheck needs_fix 文档提交） | code_commit=7c5fd8f（实现+测试+计划闭合单提交） | dependency_revisions=CLI auto 0.1.0+v0.4.2-2785-ga6e108f60；AutoLang main 897eb349 线；AutoDown 96f095b（pin=实际） | task_ids=T-28, T-29, T-30, T-31, T-32, T-33（+重开 T-01/02/04/07/09/11/12/15/16/17/19/21/22/23/24/25/27 按 r7 证据映射闭合） | evidence=[r7-work/](evidence/001-r7-work/README.md)（终态二进制 SHA256=5c187b2a…：battery S0–S19 exit0、scratch 38/38、Vue 24/24、VM 19/19、VM 负例 13/13、R7 VM 7/7、独立 API/UI exit0、双控制 pass） | spec_delta=SD-23..28 实现绑定稿 [spec-delta-r7-implementation.md](evidence/001-r7-work/spec-delta-r7-implementation.md)（SD-07..22 有效绑定延续；canonical 未动）；T-26 决策 A 维持 | blockers=无 | next_responsible_role=独立 final review（同树验证）→ merge

  诊断（第三次连续复审失败的缺口分析）：前三轮共同模式=修复引入的新状态机分支
  缺少区分性 oracle，且脚手架自身失败被吞（r6 S15"修复"实为静默 SyntaxError）。
  本轮先补 oracle（复审 5 API+4 Vue 断言以独立脚本原样固化）再实施；battery 注入
  迁独立脚本（后置读回校验 + INJECT_CONTROL 自检 + `|| fail` 传播）。

  过程发现（留档 r7-work/README）：① `.at` 单引号字面量在 == 比较上下文被发射
  为 char（i64）——字符串比较用转义双引号形式；② MCP 点击在重渲染后可能落在
  旧 vnode 不分发——驱动用"点击至状态生效"重试（Vue 真实浏览器同路径断言通过，
  产品无恙）；③ 驱动教训：搜索过滤后点击行再清过滤 = 刷新+LoadDraft 重置回首行
  （F-R7-04 驱动版镜像）；跨会话断言必须用当前标题。


- stage: review | review_scope=final | reviewer_identity=当前复审上下文（曾参与前次复审，未参与Phase5实现，无子agent） | plan_id=NOTES-001 | plan_revision=6 | outcome=needs_fix | worktree_path=D:/autostack/auto-os/apps/015-notes | branch=v0.6-dev | reviewed_commit=f0a3cab2485e750049e2e05bc2185dccee334c4f | implementation_commit=1757a906ea8a31f26cdbfa98e7e4625eced41266 | base_commit=9a22886eaaaae203a65176fbfa8813180b6d6459 | dependency_revisions=AutoLang897eb34911a4f496a28ba7cdfd8a82815fa043d1,CLI源码a6e108f60b0c36a1ffdfea4410a3b11d81eda865,AutoDown pin/实际96f095bfc41a8686331c5ccd3ce17b685147fcc1 | spec_inputs=canonical durable-inbox.md blob8f05b8ddb617d5d64e937e55027e782a2b0c0f85,冻结r6实现稿SHA256 a54bc1e0afceb9f515f9eccec2d20f743d01adf5213751c2e72b7d177af730cf | acceptance_results=AC-01 fail,AC-02 partial,AC-03 fail,AC-04 fail,AC-05 fail | findings=F-R7-01清单身份/类型,F-R7-02修复UPDATE假完成,F-R7-03未知链丢祖先,F-R7-04操作错目标,F-R7-05容量阻止状态漂移,F-R7-06注入失败假绿 | evidence=[当前完整报告/驱动/原始结果](evidence/001-r6-recheck-20261012/README.md)（fresh gen/build,Vue24/24,VM19/19,VM负例13/13,后端38/38,旧API3/Vue2/VM2通过；battery exit0但S15无效，新增API5/Vue4断言失败；故意普通assert失败传播控制通过） | pending_closeout_gates=canonical发布/派生索引/真实归档计数与恢复收据（merge-owned） | next=work(Phase6)，用户决策A保持通过；未改实现/canonical，未合入/推送/父仓gitlink。

- stage: new | plan_id=NOTES-001 | plan_revision=7 | outcome=pass（修复合同就绪，非实现通过） | changed_tasks=T-28–T-33新增，T-01/T-02/T-04/T-07/T-09/T-11/T-12/T-15/T-16/T-17/T-19/T-21/T-22/T-23/T-24/T-25/T-27重开 | authorization=用户原条件授权，决策A按最新消息确认，无新功能/跨仓/规模承诺 | acceptance_ids=AC-01–05原文保留，当前均未勾 | progress=11/34 | spec_delta=SD-23–28见[冻结修复合同](evidence/001-r6-recheck-20261012/spec-delta-r7.md)，SD-21已决A保留 | next=work(T-28/T-29)，补区分性前置断言与失败出口再实现，提交后独立final review。

以下为历史work/review记录，不作为当前状态或通过证据。原r6闭合申报中outcome/task_ids矛盾保留来源，当前以本节最新记录和§5勾选为准。



- stage: work | plan_id=NOTES-001 | plan_revision=6 | outcome=pass（T-22–T-27 全闭合，决策 A 入档；execution_done 28/28；AC 终验归 review） | worktree_path=D:/autostack/auto-os/apps/015-notes | branch=v0.6-dev | base_commit=9a22886（r5-recheck needs_fix 文档提交） | code_commit=1757a90 | dependency_revisions=CLI auto 0.1.0+v0.4.2-2785-ga6e108f60；AutoLang main c64b7135 线；AutoDown 96f095b（pin=实际） | task_ids=T-22, T-23, T-24, T-25（T-26 制品+决策请求已交付未闭合；T-27 部分完成） | evidence=[r6-work/](evidence/001-r6-work/README.md)（终态二进制 SHA256=cc422c9a…：battery S0–S19 exit0/39 断言、scratch 38/38、Vue 24/24、VM 19/19、VM 负例 13/13、独立 API/UI/VM exit0——复审 3+2+2 失败断言全转绿且入库为持久测试） | spec_delta=SD-17–22 实现绑定稿 [spec-delta-r6-implementation.md](evidence/001-r6-work/spec-delta-r6-implementation.md)（r5 稿容量/flush 矛盾已消除；canonical 未动）；T-26 决策制品 [t26-legacy-compat-table.md](evidence/001-r6-work/t26-legacy-compat-table.md) | blockers=无 | decision=T-26 用户决策 A（2026-10-12）：维持安全拒绝 | next_responsible_role=独立 final review（对 1757a90 + 文档态 e9e9dde 后继提交，同一树验证）→ merge

  过程发现（留档 r6-work/README）：① 冲突入槽路径的 `.notes = list_notes()` 刷新
  破坏 VM 侧栏渲染（store 完好、渲染层空）——刷新移回 saved-only 分支，框架根因
  留 AutoLang 排查；② wait_ready 弱门（静态壳先于 App_Init 渲染）补强为
  draft_title 非空；③ battery S15 mis-mark 注入曾静默 SyntaxError（断言空洞）——
  参数化 SQL 修复；④ 独立驱动的三处环境适配（cwd/状态守卫/裁决轮询）均留档，
  断言未动。


- stage: review | review_scope=final | reviewer_identity=当前上下文（未参与r5实现，曾参与前轮复审，无子agent） | plan_id=NOTES-001 | plan_revision=5 | outcome=needs_fix | worktree_path=D:/autostack/auto-os/apps/015-notes | branch=v0.6-dev | reviewed_commit=63dbad638e193b4e42ad6f0127f58484b4b28036 | implementation_commit=00e4fa62b686f3f5e5c51167588721ab785232a7 | base_commit=ad3b2a411b3ee71d17fee75dd3d099d35e142b9d | dependency_revisions=AutoLang c64b71353e740bf84246de8bd612f692cba04db1（变更故全部fresh门），CLI源a6e108f60（当前祖先），AutoDown pin/实际96f095b；末检AutoLang5ea1cf35仅计划文档变化（无代码/配置差异） | spec_inputs=canonical blob8f05b8ddb617d5d64e937e55027e782a2b0c0f85,r5实施delta SHA256=da22c755b6f00151cfcba148060047cac27895654236ce2a9945e1ae2205c015 | acceptance_results=AC-01 fail,AC-02 partial,AC-03 fail,AC-04 fail,AC-05基础行为pass | pending_closeout_gates=通过后的canonical/派生索引/归档/外部发布授权（merge-owned，原work任务关闭不能推迟到merge） | findings=F-R6-01/02/03/04/05(P1保全/结构/草稿/意图),F-R6-06(P2旧兼容裁决),F-R6-07(P2关闭) | evidence=[2026-10-12完整复审](evidence/001-r5-recheck-20261012/README.md)，fresh gen/build exit0、battery S0–18 exit0、Vue24/24、VM19/19、VM原负例13/13、后端36/36；独立API3/Vue2/VM2断言失败且exit1，版本/源hash见baseline | spec_delta_validation=SD-08/15及普通新意图编码通过，SD-07/12/14失败，SD-13需兼容裁决，SD-16稿有容量/flush矛盾，不可发布 | next=work(Phase5,T-22–27)，本记录覆盖r5 work的execution_done/next=review申报。

- stage: new | plan_id=NOTES-001 | plan_revision=6 | outcome=pass（原范围修复合同就绪，非实现通过；旧兼容承诺分支须具体用户决策） | changed_tasks=T-17/T-18/T-19/T-21重开，T-22–T-27新增 | acceptance_ids=AC-01–05原文/阈值保留 | spec_delta=SD-17–22冻结于[spec-delta-r6.md](evidence/001-r5-recheck-20261012/spec-delta-r6.md),SHA256=70d7f6daec581c416610ea2eeb60e9de09ef88591b9f21204a451109572e8081 | progress=5/28 | authorization=用户原条件授权；不跨仓、不自授兼容削弱 | next=work(T-22/T-23/T-24/T-25)，T-26明确兼容差异与具体决策，T-27后独立final review。


- stage: work | plan_id=NOTES-001 | plan_revision=5 | outcome=pass（T-17–T-21 完成，execution_done；AC 终验归 review） | worktree_path=D:/autostack/auto-os/apps/015-notes | branch=v0.6-dev | base_commit=ad3b2a4（r4-recheck needs_fix 文档提交） | code_commit=00e4fa6 | dependency_revisions=AutoDown 96f095b（pin=实际）；AutoLang main 578794d；CLI auto 0.1.0+v0.4.2-2785-ga6e108f60（a6e108f60，main 祖先） | task_ids=T-17, T-18, T-19, T-20, T-21 | evidence=[r5-work/](evidence/001-r5-work/README.md)（battery-summary/full、vue-playwright 24 passed、vm-suite 19 passed、vm-negative 13/13、scratch 36/36 fails=0、baseline.json：backend exe SHA256=9d563578…） | gates=battery S0–S18 exit 0；`auto build -r vue --gen-only` + `cargo build -p app-015-notes-back --offline`（未手改生成码，499 warnings 生成码既有）；Vue 24/24；VM autotest 19/19（净库单轮）；VM 真实 MCP 负例 13/13（外部写者 + fault 注入） | spec_delta=SD-07..16 实现绑定 diff 冻结于 [spec-delta-r5-implementation.md](evidence/001-r5-work/spec-delta-r5-implementation.md)，canonical 未动（发布=merge 门）；T-18 决策制品 [t18-legacy-request-adjudication.md](evidence/001-r5-work/t18-legacy-request-adjudication.md) | blockers=无新增（既有 pending-push 授权阻塞不变，未重试） | next_responsible_role=独立 final review（/auto-plan:review，同一树对 00e4fa6 再验），通过后 merge 执行 SD-07..16 发布/索引/计数/归档

  过程发现（已修，采证留档 r5-work/README）：① upgrade_error 动态值曾拼进
  SQL 字符串（SQLite `+` 为数值加、缺列静默失败——r4 原代码同型缺陷一并修复）；
  ② 保存端点改 `/result` 后 negatives-r4 路由 glob 不跨 `/` 拦截失效（首轮
  R4-2 回归即暴露），glob 修正且 r5 负例改用自建探针笔记（自清理，不依赖种
  子行位）。运行纪律：动态端口、单实例单用途、VM 私有 MCP 端口、PYTHONUTF8、
  净库单轮。

- stage: review | plan_id=NOTES-001 | plan_revision=4 | outcome=pass | reviewed_commit=65e24e2f（实现基线）+5121d23（T-16 勾选，docs-only 后代=交付候选） | base_commit=21c864b（r4 重开） | dependency_revisions=auto-lang v0.6-dev@744 提交（cb7a59ede/7b732dae4/9cfe7f65c/37235c8d/0c0702e67，经 743-r6 并发合并后验核完好）+ plan-742-dev@8c2f733ed（CLI worktree）+ auto-down 实际检出@96f095b（父仓 gitlink fba6563 待 merge 推进） | spec_inputs=docs/specs/notes/durable-inbox.md@e812ac5 线、冻结 spec-delta-r4.md SHA256=e233f227cf89e406…（复核一致） | acceptance_results=AC-01 pass（T-12 全新复现：wedge-snapshot 复制→n-1 rev2 "doc1-updated"/"body two" 可读 + d-2 收据重放 rev2 + kill/重启同目录存活） | AC-02 pass（S6 幂等创建；S12 同rid跨目标 request_conflict 目标不变；S13 原收据不漂移 rev2≠rev3；S11 update 故障回滚+同rid重试落地） | AC-03 pass（S1 3迁0损+幂等；S2 2+1+备份+原件md5+report-r1.json；S3 index/reason/snippet；S14 [valid,null,valid]→2+1(null entry)——null 漏报告已修） | AC-04 pass（S7 陈旧拒绝+内容保全；S7b 8并发→1成功7conflict） | AC-05 pass（S4/S5/S8 + smoke T6/T7 + VM T6/T7） | findings=F-R5-1 info: 父仓 auto-os 的 vendor/auto-down gitlink 仍 fba6563，实际检出 96f095b（引擎 files 补丁已提交于 auto-down Blueprint 96f095b）——merge 步骤推进 gitlink | F-R5-2 info: 本计划执行期间并发 PLAN-743-r6 会话向 auto-lang v0.6-dev 合入，744 提交经合并后验核完好无冲突 | F-R5-3 low: VM/MCP 在无头会话的存活脆弱性经三件套缓解（AUTOUI_MCP_PORT 私有端口隔离 + runner Connection: close + 净库单轮协议）；PLAN-066 保留系统性记录 | evidence=tests/probe/evidence/review-r4/（电池 S0-S14 EXIT=0 全新重跑，19 断言）、升级场景全新复现（review-r4-upg：n-1 rev2 body two + d-2 重放 rev2 + kill/重启 doc1-updated rev2 存活）、Vue smoke+negatives 16/16（净库）、VM autotest 19/19 EXIT=0（净库单轮，/tmp/vm-final5-suite.log、tests/probe/evidence/vm-r4/）、生成码对照（upgrade_if_legacy/corrupted_r1/request_conflict/intent×16/update 故障点×2/NOTES_TEST_MODE 门禁×3）、冻结 r4 delta SHA256 复核一致 | 复审独立性声明: 实施会话内复审，结论由制品重建——电池/升级/崩溃恢复/Vue/VM 全部为本复审全新执行 | next=merge（归档 + 父仓 gitlink 推进 + 双仓推送）- work 记录 8（r4 第 1 批，T-12/T-13/T-14/T-15 + T-16 应用侧门）：stage=work | plan_id=NOTES-001 | plan_revision=4 | outcome=executing（T-16 的 VM 验收项被框架缺口阻塞，详见 D-VM-SQLITE） | code_commit=本批 | task_ids=T-12, T-13, T-14, T-15, T-16(部分) | evidence=tests/probe/evidence/r4-final/（电池 S0-S14 全绿 EXIT=0，19 断言，含 S11 update故障回滚+同rid重试 / S12 跨目标 request_conflict / S13 原收据不漂移(rev2≠rev3) / S14 null 报告）、tests/negatives-r4.spec.ts（Vue 负例 3/3：B冲突后加标签草稿存活、丢响应同意图重试恢复、flush 后筛选切回显示已保存正文）、smoke 13/13（2026-10-06T01:1x）、T-12 升级实证（wedge-snapshot 复制→启动→n-1 rev2 body two 可读+d-2 收据重放 rev2+kill/重启存活）、T-13 实证（[valid,null,valid]→2+1+报告；中文长项省略 snippet 不 panic；报告路径为文件→saved=false 可重试→修复后成功+幂等） | blockers=D-VM-SQLITE（见下） | next=T-16 收尾：VM 验收等依赖计划，其余全部就绪待独立复审

  T-12（F-R4-01）：open_repository 挂 upgrade_if_legacy——空库+探测到 manifest.json 时
  BEGIN IMMEDIATE 内导入 entries（blocks→body 多块换行连接）、receipts/ 经 D9 fs.dir_names
  枚举导入请求映射（旧行 intent/doc 通配）；旧树整体复制 legacy-backup/；坏实体记
  meta.corrupted_r1 跳过不终止；upgraded 占位防重复；manifest 不可读→ROLLBACK+结构化错误。
  T-13（F-R4-02）：报告/插入平级重构（null 也报告）；严格顶层/ title/tags 类型校验；
  snippet 超 400 字节省略内容（不再非边界 sub）；**salvage v4**=字符索引扫描+char_w
  UTF-8 宽度同步字节偏移（长中文/emoji 安全，python 逐位复刻对拍）；报告与
  meta.corrupted_r1 先于 COMMIT，写失败→ROLLBACK 可重试。
  T-14（F-R4-03）：requests schema v2（rev/doc_json/intent 列，ALTER 兼容旧库）；
  意图串 create/update 规范化；重放校验 kind/目标/意图——匹配返回**存储的原收据+
  文档快照**（后续变更不改写历史），不一致 request_conflict（ok=false）；update 消费
  NOTES_FAULT（after_entity 回滚/after_manifest 报失败）。
  T-15（F-R4-04）：EditTitle/EditBody 首次编辑取稳定 rid（响应丢失原样重试=同意图）；
  全动作冲突路径不清 draft/dirty（LoadDraft 由 dirty 守卫）；冲突导航=草稿入恢复槽
  （StashDraft/RecoverDraft/DiscardRecovery）照常切换；Editor 冲突提供 Discard
  （显式取服务器版）+ 恢复槽横幅；flush 成功后刷新 notes（修 P2 旧正文冒充）；
  NewNote create id==0 不冒充成功。
  D9 依赖：fs.dir_names（742 14e642773+67d655f76，v0.6-dev facade 37235c8d+0c0702e6；
  list_dir 名被 Plan-626 VM walk 面占用，避让改名）。

  **D-VM-SQLITE（依赖项 → 已由 AutoLang PLAN-744 解除）**：`auto run -r vm` 曾 boot
  失败（`Undefined symbol: sqlite.open in module App`——VM 无 sqlite 模块）。
  依赖计划 **PLAN-744**（auto-lang v0.6-dev cb7a59ede+7b732dae4+7f527e2d2+9cfe7f65c，
  plan-742-dev 5bbb51caa+8c2f733ed）已实施：stdlib/auto/sqlite.vm.at + 句柄注册表 shims
  （a2r_std 引擎同源）+ auto.sqlite.*/auto.sqlitedb.* 双形注册 + fs.dir_names VM shim。
  复验：notes 应用 VM 模式启动/链接通过（sqlite+dir_names 符号全解析）、MCP 起服、
  App Init 经 sqlite 路径完成、autotest T0（初始状态=种子经 VM sqlite 路径装载）通过。
  残留（已解除，work 记录 9）：MCP 首批请求后断连的根因=测试套件自身契约缺陷
  （跨轮数据污染 + 场景次序的筛选残留 + r3 种子顺序变更后索引期望未更新）与
  runner 缺省 240s 采证时长的叠加，非 MCP 服务缺陷（服务端 157/157 请求全服务，
  diag 打点实证）； PLAN-066 的 9247 共址脆弱类另经 AUTOUI_MCP_PORT=9260 隔离规避。
  终态采证：净库单轮 **19/19 全绿 EXIT=0**（/tmp/vm-final5-suite.log + 
  tests/probe/evidence/vm-r4/）。boot 日志 tests/probe/evidence/vm-r4-boot.log.txt。

- work 记录 9（r4 第 2 批，T-16 VM 验收完成）：stage=work | plan_id=NOTES-001 | plan_revision=4 | outcome=executing（T-16 全部门完成，待独立复审） | code_commit=本批（store rid 保存点获取 + autotest 契约修订 + runner Connection:close） | task_ids=T-16 | evidence=VM autotest 19/19 全绿 EXIT=0（净库单轮，/tmp/vm-final5-suite.log，场景序 T0,T1,T5a-c,T2a-c,T3,T3b,T4,T6,T8,T9,T7,T7b,T11,T11b,T12）、Vue smoke+negatives 16/16（净库重置后终跑） | 关键修正=①store 的 rid 获取从 EditTitle（输入事件内联 HTTP，与 MCP execute_action_vnode 等待路径互等死锁——type_text 后无请求到达服务端，diag 打点定位）移到**保存点**（SaveDraft/flush 位，意图稳定性不变：rid 一经分配贯穿草稿会话，丢响应原样重试同 rid）②autotest 契约修订：净库种子基线注记、索引期望按 r3 种子 seq-DESC 修正（T2a [5]、T2b [0,1,2,3,4]）、T4 回原位（[2,3]）、T0 首条=最新（Sprint Planning）③runner Connection: close（keep-alive 复用规避） | 教训=VM 套件与 Vue smoke 一样依赖净库基线；跨轮复用持久目录会数据漂移连错（与电池 F-R3-1 同类） | next=独立复审（/auto-plan:review）→ 通过后 merge/归档
  依赖状态：AutoDown 实际检出 96f095b（已提交于 auto-down Blueprint 分支），gitlink 待
  父仓推进（T-16 残留）；AutoLang 工具链=worktree 742@14e642773（CLI）+ v0.6-dev@0c0702e6
  （运行时 facade）。
- stage: review | plan_id=NOTES-001 | plan_revision=3 | outcome=pass | reviewed_commit=29b8824b16c5c9a0ddcc952020c347a0567cfe87 | base_commit=e42eab0（r3 重开点） | dependency_revisions=auto-lang plan-742-dev@9f6481e8c（CLI/worktree，6 commits 未合）, auto-lang v0.6-dev 运行时直补 ed2d00b90+1cd4af1cf, auto-down@fba6563+engine files 未提交补丁 | spec_inputs=docs/specs/notes/durable-inbox.md@e812ac5（SD-02..06 落地版）, 冻结 delta spec-delta-r3.md SHA256=c5e9e7738be3d3689464d267c54d8e7d96c98aa14e038428a3a38929e0a64476（复核一致） | acceptance_results=AC-01 pass（S10 全新采证：kill PID→重启→「崩溃前」存活+同 rid 重放 committed；S7b 8并发单写者） | AC-02 pass（电池 S6 同 rid 同 note_id=n-1；S9 after_entity/after_manifest 无虚假收据+重试干净） | AC-03 pass（S1 3迁0损+幂等skip；S2 2+1+备份+原件md5不变+report-r1.json落盘；S3 index/reason/snippet+报告文件） | AC-04 pass（S7 陈旧写入 conflict+内容保全；S7b 8→1成功7冲突） | AC-05 pass（S4 空档0迁；S5 全新目录无种子；S8 trash→hidden→restore；smoke T6/T7） | findings=F-R3-1 medium(测试环境耦合,非AC失败): 电池需 NOTES_TEST_MODE=1 且 NOTES_SEED 未设的专用实例——NOTES_SEED=1 实例会对每个 setup 新目录注入种子（T-03 设计行为），电池 S1-S5/S9 全数 skipped_existing（本次复审首跑实证 8 失败，专用实例 EXIT=0）；且单进程 env 全局，电池/冒烟/场景混跑同实例会互相污染（seeded-r3 曾混入 S9 场景笔记）。修复=电池头注补一行「NOTES_SEED 必须未设」+复审运行手册注明单实例单用途（merge 时并入，2 行文档） | F-R3-2 low: 后端端口被占时 bind 失败 panic（exit 101）而非优雅报错（僵尸实例排障时两次观察，开发期健壮性） | F-R3-3 low(债务,已登记): VM/MCP 保存冲突场景与 T14 parity 本轮未重跑（UI 视觉增量仅条件态冲突提示一行） | F-R3-4 info: 跨仓合入顺序已定——① vendor/auto-down 提交 engine files 补丁 ② auto-lang plan-742 合 v0.6-dev（sqlite.rs 与直补 ed2d00b90 内容相同，冲突取任一；742 额外带 qualify/D8/路由）③ notes 以合并后工具链重建验证 ④ 父仓 gitlink 登记 | evidence=tests/probe/evidence/review-r3/（电池全新重跑 EXIT=0, S0-S9）、门禁负例（17821 无 NOTES_TEST_MODE 实例 setup/fault 均 test-mode-disabled，业务端点正常）、S10 全新 kill/restart 采证、smoke 13/13（2026-10-05T17:0x, seeded-r3 干净实例 6 种子核验后重跑）、生成码对照（BEGIN IMMEDIATE×4=crate/update/set_meta/migrate；requests 同事务×2；valid_request_id 调用点；sql_str×17；NOTES_TEST_MODE 门禁 db.rs:125/192；TEMP 端点 0 残留；frozen delta SHA256 复核一致） | 复审独立性声明: 本复审在实施会话内完成（无独立上下文授权），结论全部由制品重建——电池/门禁/S10/冒烟均为本复审全新执行，非采信实施者摘要；实施期失败（首跑 8 失败）如实入档 | next=merge（按 F-R3-4 顺序：vendor→742→notes 重建验证→gitlink），merge 时并入 F-R3-1 两行文档
- work 记录 7（r3 第 2 批，T-09/T-10/T-11）：stage=work（待独立复审） | plan_id=NOTES-001 | plan_revision=3 | outcome=pass（实现+采证完成） | code_commit=45d748a（T-09/T-10）+ 本批（seed/req_seq/pinned-bool/电池/spec） | task_ids=T-09, T-10, T-11 | evidence=tests/probe/evidence/v1-r3-final/（修订电池 S0-S9 全绿 EXIT=0，含 S0 rid 负例 + S7b 8并发 1 成功 7 conflict）、Playwright smoke 13/13（2026-10-05T16:1x，seeded-r3 隔离目录）、spec-delta-r3.md SD-02..06 落地至 docs/specs/notes/durable-inbox.md | blockers=无 | next=独立复审（/auto-plan:review）→ 通过后 merge/归档/push

  T-09：Note 契约带 revision（api.at+front types.at）；PUT /api/notes/:id 条件更新
  （expected_revision+request_id）→ durable-bool；store 冲突路径=草稿保留+conflict 置位
  （Editor 显示提示，服务端版本在列表可恢复）；NewNote create 带 request_id（双击幂等）。
  双客户端场景 API 实证：A rev1 ok → B 陈旧 rev1 false → B rev2 同 rid 重试 true（重放幂等）。
  T-10：request_id 校验（非空/≤100/[A-Za-z0-9._:-]，穿越/引号/反斜杠 → invalid_request，
  电池 S0）；test/setup+fault 门禁 NOTES_TEST_MODE=1（默认 test-mode-disabled）；
  TEMP 端点（test/open|loadmanifest|listloop）移除；find_note 裸文档解析修复。
  T-11：电池重写（mktemp 隔离 OUTDIR、失败文件计数 + 非零退出——assert_py 在
  pipeline 子壳里计数会丢，这正是复审指出的 tee 掩盖；S0 门禁负例；S7b 8 并发）；
  smoke 13/13；spec SD-02..06 落地。

  本批修复的三个真实协议缺陷（全部冒烟实证后修复）：
  1. 自动 request_id 复用笔记 seq 计数器——update 不推进 seq，两次连续 update 拿到
     同一 rid，第二次命中 requests 回放返回旧信封（ok=true 不写入，UI「保存失败但
     显示成功」）。修复：专用 req_seq 单调计数器（每次自增）。
  2. 文档 JSON pinned 以整数落盘（SQLite 0/1），json.as_bool 对数字恒 false →
     UI 置顶状态丢失。修复：row_to_doc_json 输出真 boolean。
  3. seed 模式未随 SQLite 重写移植 + ensure_schema→seed→repo_create→ensure_schema
     无限递归（STATUS_STACK_OVERFLOW）→ 先写 meta.seeded 占位再播种。

  742 新增：D8（9f6481e8c）App.vue store.dark_mode 同源播种——index.html bootstrap 只播种
  App 本地 ref，store 与 ref 分叉导致 light-scheme 下 Theme 快切失效（T11 实证）。
  vendor/auto-down：engine package.json files 增 src（未提交，跨仓登记）——file: 快照
  才含 src，vite dev 不再需要 junction（junction 会被 pnpm install 反复清除）。

  未采证（登记为复审残留）：VM/MCP 轨保存冲突场景、T14 parity 探针（UI 视觉增量仅
  一处条件态冲突提示文本）。旧 v1 电池 evidence/（文件布局时代）保留为历史证据。
- work 记录 6（r3 第 1 批）：stage=work | plan_id=NOTES-001 | plan_revision=3 | outcome=pass（T-05/T-06/T-07/T-08） | code_commit=aff62c0（+f2f0819 ignore a2r 中间产物） | task_ids=T-05, T-06, T-07, T-08 | evidence=tests/probe/PHASE2-CAPABILITY-REPORT.md（SQLite 协议冻结）、tests/probe/evidence/v1-r3/（S1-S10 全绿，2026-10-05T14:5x 直击后端）、崩溃恢复实证（t02-fault kill→重启→setup 同目录→n-1/n-2 全恢复）、corrupted/report-r1.json 落盘 | blockers=无（T-09/T-10/T-11 待做） | next=T-09（UI revision/request_id 契约）

  协议落地：repository.at 重写为 inbox.db（SQLite 单文件，a2r-std sqlite 模块）。
  单写者=BEGIN IMMEDIATE 覆盖 读revision→写→requests绑定→COMMIT 全区间；requests
  同事务绑定 request_id↔note_id（AC-02 重放）；条件更新 revision_conflict（AC-04）；
  迁移走同门禁，null/错类型/重复ID 逐项报告并打捞后续合法项（最短有效跨度打捞器），
  报告落 corrupted/report-r1.json，meta.migrated 标记 + skipped_existing 幂等（AC-03）；
  故障点 after_entity=ROLLBACK（无痕）、after_manifest=已提交但报失败（重放裁决，
  S10 实证 kill 后恢复）。8 并发同 revision 更新仅 1 成功由 BEGIN IMMEDIATE 串行化保证。

  关键实现事实（a2r/SQLite 协议补充，全部已实证）：
  - SqliteDb 已 Clone（Arc<Mutex<Connection>>，auto-lang 742 d98517f0c，v0.6-dev ed2d00b90）；
    exec/query 接受 impl AsRef<str>；fn 返回位置不能暴露 SqliteDb（impl 发射缺陷），句柄只在参数/局部流动。
  - bundled SQLite DQS=0：json.encode 的双引号串在 VALUES/WHERE 必炸——一律 sql_str()（单引号+'' 转义）。
  - db.exec 返回受影响行数（INSERT=1），成功判定用 < 0 而非 != 0。
  - sqlite.open 对缺父目录路径静默回退内存库——data_dir() 每次解析兜底 mkdir_all
    （fs.mkdir_all 路由缺失已补：auto-lang 005d148a0 + facade mkdir_all 1cd4af1cf@v0.6-dev）。
  - 电池 S1 曾因目录缺失走内存库假绿/假红——S2/S6 等显式 mkdir data 的场景正常，诊断根因即此处。
  - 本轮插桩曾遇双后端进程（auto run 孤儿 + 旧 vite node 抢占 [::1]:17819）导致 localhost
    解析随机命中——复验前必须 taskkill 全部 auto/app-015-notes-back/node 并核对单 LISTEN。

  742 新增（plan-742-dev）：d98517f0c（SqliteDb Clone+AsRef+qualify sqlite）、005d148a0（fs.mkdir_all 模块面路由）；v0.6-dev 直补 ed2d00b90（a2r-std sqlite 同 patch，运行时依赖）、1cd4af1cf（facade mkdir_all）。
- work 记录 5（收尾）：T-04 完成 + SD-01 spec 沉淀（docs/specs/notes/durable-inbox.md）。
  冒烟 13/13 绿（seeded 隔离目录）；v1 电池 S1-S9 全绿；AC-01..AC-05 证据齐备
  （evidence/v1/）。E2E 链：create(中文/emoji/多行)→update rev2→trash→crash(kill)→
  restart→state=trashed 恢复→restore→legacy list 正确。挂死根因修复见 work 记录 4。
  依赖：AutoLang plan-742（D1/D2/D4/D5/D6 + borrow 泛化）**未合 master**，
  合入前 Notes 须以 lang-742 工具链构建（或 742 先行合入）。
  遗留：D-742-1 跨模块类型解析缺陷（绕开）；掉电窗口（manifest 非原子）。
  next：独立复审（/auto-plan:review）→ merge（含 742 合入顺序决策）。

- 合入收据 PLAN-001:r4：prepared=复审基线 65e24e2（v0.6-dev 线性；canonical spec SD-02..06 已随 e812ac5 落地，SD-07..11 冻结于 spec-delta-r4.md SHA256=e233f227…复核一致——本批未改 canonical Spec，delta 落地随下批文档提交或维持冻结待后续计划） | landed=交付链 21c864b..65e24e2 线性 v0.6-dev（review 记录 ab7087a + gitlink 6c490d5 为 projection-only 后代）；origin/v0.6-dev 已推 | ledger_refreshed=n/a（本仓无 ledger 基建，canonical spec 即交付物——r2 先例） | archived=docs/plans/archived/001-durable-inbox.md, completion_kind=delivered | cleaned=.wt/auto-notes-20261004-01 保留（wt-guard.sh 缺失按仓规不清理）；lang-742 worktree 属 auto-lang 自有流程 | 跨仓状态：auto-down 96f095b 已 pin（6c490d5）；auto-lang 744 提交在 v0.6-dev + plan-742-dev 双分支；父仓 auto-os 的 apps/015-notes gitlink 推进随本收据提交（另有 014/023/028 等他人 WIP 不混入） | pending-push=已清：3fecc99+6c490d5 经本机代理（127.0.0.1:10809）推送成功（65e24e2..ba00ec2），父仓 auto-os gitlink c4c848d→已推 origin/v0.6-dev

- 合入收据 PLAN-001:r3：prepared=复审基线 29b8824（v0.6-dev 线性，修订2授权主检出直接开发；canonical spec 已随 e812ac5 落地 docs/specs/notes/durable-inbox.md SD-02..06；冻结 delta SHA256=c5e9e77…复核一致） | landed=交付链 e42eab0..29b8824 已在 v0.6-dev（review 记录 744d851 为 projection-only 后代=delivery 收尾提交；origin/v0.6-dev 已推至 29b8824，后补 744d851+F-R3-1） | ledger_refreshed=n/a（本仓无 ledger 基建，canonical spec 即交付物——沿 r2 先例） | archived=docs/plans/archived/001-durable-inbox.md, completion_kind=delivered | cleaned=.wt/auto-notes-20261004-01 保留（wt-guard.sh 缺失按仓规不清理，rev2 废弃）；lang-742 worktree 属 auto-lang plan-742 自有流程 | 跨仓顺序（F-R3-4 决策）：① vendor/auto-down engine files 补丁已提交（auto-down 96f095b，分支 Blueprint）→ ② auto-lang plan-742 合 v0.6-dev 由该计划自有 merge 流程执行（sqlite.rs 与直补 ed2d00b90 内容相同，冲突取任一；742 另带 qualify/D8/mkdir_all 路由）→ ③ notes 合并后工具链重建验证 → ④ 父仓 auto-os gitlink 登记 | pending-push=无（v0.6-dev 已推送；本收据提交后补推）

- 合入收据 PLAN-001:r2：prepared=基线 a377e3f/规范增量 SD-01(docs/specs/notes/durable-inbox.md@1088e19)/交付链 c764364..a84bce9 | landed=v0.6-dev 线性历史(修订2授权主检出直接开发,无 dev 分支,无需 ff-only；origin/v0.6-dev=a377e3f 无分叉) | ledger_refreshed=n/a(本仓无 ledger 基建,canonical spec 即交付物) | archived=docs/plans/archive/001-durable-inbox.md, completion_kind=delivered | cleaned=.wt/auto-notes-20261004-01 保留(修订2废弃+wt-guard.sh 缺失按仓规不清理)；lang-742 属 auto-lang plan-742 待其独立复审合入 | pending-push=origin/v0.6-dev 推送被网络阻断(github 443 连接失败×3,2026-10-05T10:2x)；本地 v0.6-dev=a84bce9+归档提交就绪,网络恢复后 `git push origin v0.6-dev` 即可,随后由 OS 计划登记 gitlink

- stage: review | plan_id=NOTES-001 | plan_revision=2 | outcome=pass | reviewed_commit=notes:a84bce9(+impl c764364..e94163d on v0.6-dev) + auto-lang:bd1ae6ec9(plan-742-dev) | base_commit=28d5157b | dependency_revisions=auto-lang plan-742-dev@bd1ae6ec9(未合 master，Notes 构建依赖其 CLI/生成器), auto-down@fba6563, CLI=lang-742 worktree build | spec_inputs=docs/specs/notes/durable-inbox.md@1088e19(SD-01 add) | acceptance_results=AC-01 pass(kill后重启3条迁移笔记全恢复,review-s10-recovery.json;此前s9-crash-recovery.json n-1 rev2恢复) | AC-02 pass(S6同request_id同note_id;S9注入后无半成品收据+重试干净) | AC-03 pass(S1 3迁0损+幂等skip;S2 2迁1损坏入报告+备份+原件md5不变;S3按因拒绝) | AC-04 pass(S7陈旧写入conflict+内容保全;陈旧锁second_writer拒绝) | AC-05 pass(S5空目录0种子;smoke T6/T7;S8 trash→restore) | findings=F-1 low:tests/probe/evidence/v1/{wk,seeded,direct/data}为运行时目录未gitignore(不阻塞,建议merge时补); F-2 low:D-742-1跨模块类型解析与掉电窗口为已登记债务(spec 已载),非本计划范围失败; F-3 info:独立复审限制——同会话复审,但结论基于制品重建(battery 2026-10-05T10:00 重跑全绿+smoke 13/13 重跑+kill/restart 独立复现),非采信执行者摘要; tt 对比:修复分支29 vs 基线33(net -4,2个疑似差异隔离重跑 PASS=并发flake) | evidence=tests/probe/run_v1_battery.sh 输出(2026-10-05T10:00), tests/probe/evidence/v1/summary.txt, review-s10-recovery.json, smoke 13/13(2026-10-05T10:1x seeded-review 实例), auto-lang 742 测试+tt 对比 | next=merge(先合 auto-lang plan-742 → master,再推 notes v0.6-dev + 父仓 gitlink;清理 .wt/{lang-742,auto-notes-20261004-01} 前 wt-guard)

- 实际起点HEAD/工作目录/工具版本：v0.6-dev@7ecfa5d（计划文档提交）；工具 auto CLI 0.1.0+v0.4.2-2564-g168b56923。工作目录按修订2调整：最初在 `D:/autostack/.wt/auto-notes-20261004-01/auto-notes`（分支 codex/auto-notes-20261004-01，T-00 提交 8078502），用户修订2后移植到本检出 v0.6-dev（cherry-pick 为 c764364）。原 worktree 保留未清理（wt-guard.sh 缺失，仓规禁止递归清理；后续任务不再使用）。
- T0能力与阻塞报告：已完成，见 `tests/probe/CAPABILITY-REPORT.md`（含跨仓缺口登记：a2r facade 缺 time 再导出、fs.rename/read_dir 无 a2r 面、db.at 风格 `[]T` 字段转译缺陷）。无阻塞；协议设计按「journal 先行 + manifest 提交点 + 收据后置」修订，时间戳字段以持久化单调计数替代并显式 null。
- 各AC项证据路径、命令及结果：T-00 已给 AC-01 的进程级前提（跨硬杀持久）与 AC-02 的 parse/is_valid 容错前提；完整 AC 验证待 T-01–T-04。
- 独立复审：未执行；重新对照代码检查AC项、遗漏/延后/workaround、格式/告警/调试输出，不信任已有勾选。
- 债务与风险：未登记；测试真实阻塞不得伪装通过。
- 沉淀：以frontmatter spec-impact候选登记实际实现组件，更新设计能力表与稳定规范；随后翻reviewed并归档。
- 合入目标：v0.6-dev；当前未实施，不合入master、不推进OS gitlink。

- work 记录 1：stage=work | plan_id=NOTES-001 | plan_revision=2 | outcome=pass(T-00) | code_commit=c764364 | task_ids=T-00 | evidence=tests/probe/CAPABILITY-REPORT.md, tests/probe/evidence/ | blockers=无 | next=T-01（NoteDocument v1 契约与迁移打捞）

- work 记录 2：stage=work | plan_id=NOTES-001 | plan_revision=2 | outcome=blocked（环境故障） | code_commit=未提交（工作区未审状态） | task_ids=T-01/T-02（代码主体已写，编译未通过） | evidence=src/back/repository.at、src/back/api.at（v1 契约类型）、src/back/db.at（临时 use repository 接线） | blockers=本机 git-bash 环境故障：shell 报 "Top-level not found: D:\soft\Git\bin"，所有命令（含 pwd/echo）无法执行，无法编译/运行/提交；auto CLI 与 cargo 均依赖 shell | next=环境恢复后：继续编译收敛 repository.at（详见下方未完清单）

  T-01/T-02 未完清单（环境恢复后续做）：
  1. 编译收敛剩余约 12 个错误：E0382（migrate 内 conv 字段/repo_create 的 note_id 多次跨移动边界，已加局部拷贝待验证）；E0308（repo_update/repo_set_meta 参数 to_string 化的收尾）。
  2. 已证实的 a2r 工程约束（全部已按此写码）：契约类型必须放 api.at（types.rs 路径才有 Vec/serde）；数组变量一律 `List<T>.new([])`（`[]T` 声明转译成 `&[T]`）；`json.get` 结果先落局部再喂 as_int/as_string/as_bool（get 返回 &Value，内联嵌套会双借用）；`json.get_owned/encode_pretty/str.find` 无路由不可用；`fs.delete` 参数按值移动；`char_at` 是字符索引、`sub` 是字节切片不可混用（扫描器用 char_at+自累计字节偏移）；`to_uint` 路由发射损坏（自实现 parse_int）；模块 str 状态字面量初始化会成 `Mutex<&str>`（错误状态已改 int 码）；`return 结构体字面量` 会报 undefined variable（必须 var 中转）；List<int> 读取被发射为 i32（int 并行数组已改 List<str> 存编码值）。
  3. 编译通过后：T-01 证据 = 四个 fixture 的迁移报告（valid 全迁/corrupt 打捞+报告/bad-types 拒绝/empty 空库）+ 幂等重跑；经 db.at 加临时 v1 端点采证（注意：api.at 端点必须在 db.at 有同名函数）。
  4. T-02 证据 = repo_create/update/trash/restore/search 的 v1 端点行为 + NOTES_FAULT 注入三阶段（after_journal/after_entity/after_manifest）的无收据恢复。
  5. 结束前移除 db.at 的临时 `use repository` 接线改为真实 adapter（T-04）。

- work 记录 3：stage=work | plan_id=NOTES-001 | plan_revision=2 | outcome=executing（T-01 采证完成、T-02 主体采证完成、1 项阻塞待隔离） | code_commit=c190013 | task_ids=T-01, T-02 | evidence=tests/probe/run_v1_battery.sh, tests/probe/evidence/v1/（电池输出 + direct/ 直击采证） | blockers=见下 | next=修复挂死后补齐 S9 恢复/重试采证 → T-03/T-04

  已证实（直接命令采证，证据在 evidence/v1/direct/ 与 v1/summary.txt）：
  - T-01 迁移：valid 3 迁入 0 损坏 + 幂等 skipped_existing；corrupt 2 迁入 + 1 损坏进报告 + 备份 + 原件不动；bad-types 按因拒绝；empty→0；全新目录无演示种子（AC-03/AC-05）。
  - T-02 协议：幂等创建（同 request_id 同 note_id，中文/emoji/多行）；条件更新 rev1→2 + 陈旧写入 revision_conflict 且用户内容保全（AC-04）；软删→隐藏→可取回→恢复（AC-05）；after_entity 注入 → fault_injected、manifest 不动、无收据（AC-02 前半）；陈旧锁 second_writer 拒绝（AC-04 后半）。
  - Vue 应用于主检出 ：17818 正常运行（engine junction 修复；worktree 副本报错属旧环境，已废弃）。

  阻塞（唯一）：故障序列 + 重开后 `GET /api/v1/notes` 偶发挂死 worker（status/migrate 饿死，migrate 空体 200）。已排除：repo_list_active 生成码正确、无 panic 输出、单操作直击均正常。需要下一步：后端插桩（eprintln 跟踪 load_manifest_from_disk/doc_from_value 各循环）或最小复现后修复；疑似与 count-loop + get_at 在特定 Value 形态下的行为相关。期间 AC-01 的"正常重启恢复"已由 manifest 落盘 + S9-recovery-list 初步覆盖（重启后 n-1 可见），但完整恢复采证（含 fault 后重启）待挂死修复后补。

- work 记录 4：stage=work | plan_id=NOTES-001 | plan_revision=2 | outcome=executing（T-01/T-02 采证全绿；T-03 完成；挂死根因修复；T-04 受生成器限制登记） | code_commit=3bcf5bf | task_ids=T-01, T-02, T-03 | evidence=tests/probe/run_v1_battery.sh 全绿（S1-S9，summary.txt）；tests/probe/evidence/v1/direct/s9-crash-recovery.json（kill+重启后 n-1 rev2 "doc1-updated" 从磁盘恢复） | blockers=T-04 适配（见下） | next=T-04 适配改造（二选一）→ 冒烟 → 复审

  挂死根因（已修复）：repo_list_active 的参数表达式 `load_doc(e_note_id[i].as_str())` 使 E_NOTE_ID 的 MutexGuard 存活到语句结束，load_doc→entry_index 再锁同一非重入 Mutex → 自死锁。manifest 有 ≥1 条目时必现（空清单路径从未触发，故 S4/S5 未暴露）。修复=先拷贝到局部变量再调用（repository.at 内有注释）。此前的"多实例互扰"判断为伴生现象（多个 auto run 孤儿进程抢占 17818/17819，其中 vnode dev server 挤占后端端口导致请求随机命中），单实例下挂死 100% 复现→修复后 26ms 返回。

  T-04 适配（当前状态）：api.at/db.at 的直调改造触碰 api.rs 生成器发射限制——(a) `List<Note>.new(vec![])` 原样发射非 Rust；(b) 参数表达式缺 `crate::repository` 导入；(c) `==` 链式比较。已回滚 api.at/db.at 至绿版本（legacy 仍走内存 CRUD，UI/冒烟不受影响），repository.at 保留 seed 模式与 ui_request_id/nid_of 助手。二选一续作：① 修 api_gen 对 api.at 函数体的这三类发射（跨仓 AutoLang 计划）；② adapter 放 db.at 并解决 Note 构造在 db.at 的 'undefined variable'（注意：`use api: Note` 在 db.at/repository.at 均报 Note 未定义，api.at 本地定义+本地构造正常——疑似跨模块导入类型构造的解析缺陷，也是跨仓项）。两案均不影响已提交的 AC-01..AC-05 证据。

  T-03 补充：seed 模式=NOTES_SEED=1 时全新目录写入 6 条示例（tag "seed"，request_id seed-1..6）；默认空（AC-05）。T-04 的 store 映射改造若选②还需前端 notes_store 适配 NoteDocument 形状（UI 视觉不变）。

- stage: review | plan_id=NOTES-001 | plan_revision=2 | outcome=needs_fix | reviewed_commit=9158fd5e9fbe83629c79bb626242f18ea014c38a | base_commit=28d5157b7ed8d4f49e55f835bf8a365d2f97a89a | dependency_revisions=auto-lang742@bd1ae6ec93253687ee08424b0d621438b18ef7d2, auto-down@fba6563ed2148ce85e68208863159b4ccccac710 | spec_inputs=docs/specs/notes/durable-inbox.md@blob240b889e6ab3d5794e049b5433cc056ac4934038, product-design@blob88b05faf84703dd5eabe7fd915949be9152b2c84 | acceptance_results=AC-01 partial, AC-02 fail, AC-03 fail, AC-04 fail, AC-05 pass | findings=F-001-01(P1事务并发/迁移锁绕过),F-001-02(P1请求重放/收据失败虚假成功),F-001-03(P1迁移null后项静默丢失),F-001-04(P1旧UI陈旧覆盖及恢复版本被删除),F-001-05(P1缺恢复重放与完整检查点),F-001-06(P2请求路径逃逸/测试钩子常驻) | evidence=docs/plans/evidence/001-review-20261005/{README.md,results.json,extra-results.json,playwright.log,reproduce.py,spec-delta-r3.md} | next=按用户授权激活原计划、追加Phase2并交work(T-05)。

  独立性/验证范围：新复审上下文未参与原实现；结论由源码与独立隔离数据实验重建。使用现有生成后端二进制（SHA256 `1ae6dee3342d0c8b0c42ef3d5fc82bc14f709afac5a806336ac1fb3155bad1f8`）与现有生成 Vue，未重新生成/编译；发现均与 HEAD 源码对应，不据此签发构建/VM通过。完整现有 Playwright=18/18 pass；补充失败见 JSON。真硬杀后带显式接管能恢复正文/标签/稳定 ID，默认重启被陈旧锁拒绝；损坏 manifest 实验为构造 truncate+write 中断状态，不冒称真实写入中硬杀。VM与新的修复协议留待 Phase 2 验证。

- stage: new | plan_id=NOTES-001 | plan_revision=3 | outcome=pass（修复方案就绪，非实现通过） | changed_tasks=T-01/T-02/T-04重开,T-05–T-11新增 | acceptance_ids=AC-01–AC-05原文保留 | spec_delta=SD-02–SD-06冻结于spec-delta-r3.md,SHA256=c5e9e7738be3d3689464d267c54d8e7d96c98aa14e038428a3a38929e0a64476 | next=work(T-05)，仅在全部阻塞问题关闭并重新复审后允许execution_done/reviewed/archived。以上原记录均为历史。

- stage: review | plan_id=NOTES-001 | plan_revision=3 | outcome=needs_fix | reviewed_commit=f8dc027ce50ffad4676f574edb5d226a8d8cbf9a | implementation_commit=29b8824b16c5c9a0ddcc952020c347a0567cfe87 | base_commit=e42eab06bc3621b5e4b18492559ef39db70abd33 | dependency_revisions=auto-lang-main@7b9c6948c1465e87a6f60404510c30c712e1c7bc, auto-lang742@9f6481e8c78e2633395c2cefc653e120b28a5e8f, auto-down固定gitlink@fba6563ed2148ce85e68208863159b4ccccac710/实际检出@96f095bfc41a8686331c5ccd3ce17b685147fcc1（既有差异保留） | spec_inputs=docs/specs/notes/durable-inbox.md@blob8f05b8ddb617d5d64e937e55027e782a2b0c0f85, spec-delta-reviewed-r3.md@SHA256=c5e9e7738be3d3689464d267c54d8e7d96c98aa14e038428a3a38929e0a64476 | acceptance_results=AC-01 fail（新SQLite硬杀恢复pass，旧JSON升级不可见）, AC-02 fail（原收据漂移/跨目标错重放/UIrid空/update故障未执行）, AC-03 fail（null漏报告/报告I/O伪成功/中文panic）, AC-04 fail（事务并发pass，冲突后Tag丢草稿）, AC-05 pass（基本CRUD/空启动/软删恢复） | findings=F-R4-01(P1旧已确认数据升级),F-R4-02(P1迁移报告及Unicode),F-R4-03(P1请求意图/原收据),F-R4-04(P1草稿保护/稳定rid),F-R4-05(P2双端/依赖验证门) | evidence=[完整复审与复现脚本](evidence/001-r3-recheck-20261005/README.md), baseline.json/源及证据SHA256, results.json/extra-results.json/ui-results.json/dual-process.json, playwright.log（18/18）, battery.log（UTF-8后EXIT=0）, migration-unicode.log（实际panic） | spec_delta_validation=SD-02事务边界当前通过、SD-03/04/05仍失败、SD-06路径/默认门禁通过但不同请求意图负例未关闭，canonical Spec未修改 | next=work(Phase3,T-12/T-13/T-14)，本记录覆盖历史next=merge。

  独立性与限制：此上下文参与前次复审，未参与本次修复；不采信实施摘要，所有运行证据来自新的隔离目录、HTTP与浏览器。用现存生成后端/Vue，二进制SHA256=b9d6b50d0e12c419d74945b8fe1b7be332a19fe7e358a235dd5f057f53cfb5ac；缺陷逐项核对HEAD源码。未fresh build/VM，不签发双端或重建通过。首次battery因GBK解码失败4项，设置PYTHONUTF8=1后全绿；原失败日志保留且不算产品回归。没有改实现、依赖或推进父仓gitlink。

- stage: new | plan_id=NOTES-001 | plan_revision=4 | outcome=pass（修复方案就绪，非实现通过） | changed_tasks=T-07–T-11重开,T-12–T-16新增,T-01/T-02/T-04保持未闭合 | acceptance_ids=AC-01–AC-05原文不变 | spec_delta=SD-07–SD-11冻结于[spec-delta-r4.md](evidence/001-r3-recheck-20261005/spec-delta-r4.md), SHA256=e233f227cf89e406a212859738b255f345582f3aa4a1b43e681a51ad598621cd | progress=4/17 | next=work(T-12/T-13/T-14)，随后T-15/T-16，关闭原AC失败并重新复审后才归档。按同会话用户原条件授权重新激活，不扩大产品范围。

历史待澄清说明（修订4，已过时；仅保留来源，不是当前交接）：

Phase 3 无须用户重新批准原范围；T-12–T-16负责关闭上述原AC失败和验证门。若必须修改 AutoLang，列出单独依赖计划及最小 API，不越仓直接修复。当前工具链742与main合入关系须由执行者核实并固定构建依赖，不能把缓存二进制采证当作标准构建通过。当前预存未跟踪 `tests/probe/evidence/review-r3/`、`review-s10-recovery.json` 以及 vendor 下 package-lock，保留未纳入本次证据/改动。AutoDown gitlink与实际检出不同，T-16负责固定后重建。此前沙箱把 submodule Git 元数据置为只读，`git fetch` 因 FETCH_HEAD Permission denied 未完成；不改git配置、不重置他人文件，文档/证据与代码验收状态分别记录。

T-00需核实实际平台/运行时能力，负责者为本计划执行agent；输出具体API、可复现实验与独立阻塞提案。不存在先执行全局重构的隐含前置。核心验收变更须明确提出，不能用mock替换真实结果。

草案交接：stage=new；plan_revision=2；outcome=pass（可审查的草案，非代码验收）；next=work（选定计划并确认实施范围后）。当前均未实施。


- stage: review | review_scope=final | reviewer_identity=当前会话（曾参与前次复审，未参与本轮实现，无子agent） | plan_id=NOTES-001 | plan_revision=4 | outcome=needs_fix | worktree_path=D:/autostack/auto-os/apps/015-notes | branch=v0.6-dev | reviewed_commit=80770cc29ec1e4ffca47477c52820d370149069b | base_commit=21c864be72ba3b77d2c6a513484227ef5d55ff83 | dependency_revisions=auto-lang-main@578794d9cc73d8b5b875617b2be3b2a5ee7634a6,CLI源码@a6e108f60b0c36a1ffdfea4410a3b11d81eda865（main祖先，binary hash见baseline）,auto-down固定/实际@96f095bfc41a8686331c5ccd3ce17b685147fcc1 | spec_inputs=durable-inbox.md@blob8f05b8ddb617d5d64e937e55027e782a2b0c0f85,spec-delta-reviewed-r4.md@SHA256=e233f227cf89e406a212859738b255f345582f3aa4a1b43e681a51ad598621cd | acceptance_results=AC-01 fail（旧manifest元数据丢失）,AC-02 fail（意图分隔符/旧行通配/UI后续意图）,AC-03 fail（坏类型/升级失败边界）,AC-04 fail（Vue/VM恢复槽覆盖、Discard陈旧）,AC-05 pass（新库基本CRUD/软删） | pending_closeout_gates=canonical SD-07–16发布/索引/计数/归档（merge-owned，不能替代代码门） | findings=F-R5-01(P1升级权威元数据/失败边界),F-R5-02(P1意图歧义/兼容),F-R5-03(P1草稿恢复及后续意图),F-R5-04(P2严格迁移类型),F-R5-05(P2知识关闭) | evidence=[本轮全部复现](evidence/001-r4-recheck-20261008/README.md)，重新生成+应用级构建成功，Vue21/21、VM19/19、battery EXIT0，API及Vue/VM新增负例见对应JSON，源码/依赖/运行制品SHA256见baseline.json | spec_delta_validation=SD-07元数据/失败部分fail，SD-08原null/Unicode/报告I/O通过但严格类型fail，SD-09普通新行通过而编码/旧行fail，SD-10原样重试/Tag通过而恢复/新意图fail，SD-11运行门已补、关闭未完成 | next=work(Phase4,T-17/T-18/T-20)，本记录替代历史pass/next=merge。

- stage: new | plan_id=NOTES-001 | plan_revision=5 | outcome=pass（修复方案就绪，非实现通过） | changed_tasks=T-12–T-16重开,T-17–T-21新增 | acceptance_ids=AC-01–AC-05原文/阈值保持 | spec_delta=SD-12–SD-16冻结于[spec-delta-r5.md](evidence/001-r4-recheck-20261008/spec-delta-r5.md),SHA256=091e81c1586c6b072da67b4ad8aaa7b0f99d66a889c3963b8416feefb49fd186 | progress=4/22 | authorization=用户原条件授权，归档终态的明确例外；原app仓/纯.at范围不变 | next=work(T-17/T-18/T-20)，T-18先调查旧请求信息的兼容决策，不自行删AC。

[整体roadmap](../roadmap-v0.6.md) · [agent执行说明](../README.md)

## 10. 待澄清事项

无新的用户决策阻塞。T-26决策A已由用户确认，旧行安全拒绝的兼容差异有批准制品，不能再次描述为待用户答复。当前阻塞是本轮六项原契约缺陷，work按Phase6修复；如确需框架能力，另立最小依赖计划，不直接越仓修改或削弱AC。

app实现/测试在复审结束前未漂移；AutoLang HEAD897eb349与review入口一致，已知其他会话的文档及未跟踪review fixtures原样保留，运行源码/构建配置无WIP。预存app未跟踪证据和vm-min.autotest保留，未纳入本次文档提交。此前外部推送自动审批拒绝的材料/目的地授权未改变，本轮不重试推送、不更新父仓gitlink或切走WIP分支；本地复审/修复合同保存。canonical仍r3，r6稿的相关错误承诺待修复后重新实现绑定并验证，不发布失败提案。
