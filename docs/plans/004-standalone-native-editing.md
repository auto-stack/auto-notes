---
plan_id: NOTES-004
status: drafting
feature_name: "独立启动与原生编辑恢复验收"
author: [Codex]
created_at: 2026-11-01
updated_at: 2026-11-01
plan_revision: 1
current_step: 1
total_steps: 8
base_branch: main
base_commit: 82b4d2f4b87e3fc6a3cc455a263b4ab1ef45aa4b
depends_on: ["NOTES-001"]
supersedes_spec_components: ["docs/specs/notes/durable-inbox.md"]
new_spec_components: ["docs/specs/notes/standalone-runtime.md"]
touched_goals: []
---

# NOTES-004：独立启动与原生编辑恢复验收

## 0. 变更摘要

接续NOTES-001可靠Inbox，补当前工具链下独立准备/启动、真实原生编辑与退出恢复门。001保持归档；002快速卡片/多媒体/剪贴板接收、003入口/知识交接已有用途，保留草案原文，不为这次运行收口重写或捆绑它们。

## 1. 目标

从本仓独立准备并启动Vue＋Rust或原生VM＋Rust，真实界面完成创建、中文正文编辑、保存、标签/置顶、软删恢复和重开后的下一次保存。失败/冲突保留文本，稳定ID与revision/幂等协议沿001。

非目标：新卡片/附件系统、剪贴板历史采集、Launcher/Jade/Reader交接、同步、Linux/OS装配；不重做编辑器或SQLite仓储。

## 2. 架构方案

本仓为主导仓，开发/检查/最终复审顺序使用 `D:/autostack/auto-notes` 独立clone的 `main`，一app一写入者，复审时暂停实现写入；不在AutoOS子模块开发，不建junction/symlink。框架若确有缺项，先核实现有公共能力和当前实际owner，再在owner仓另立最小前置并遵守其worktree规约，本计划不授权越仓改实现。

应用业务保持纯.at；复用既有仓储、UI、测试，不手写业务Rust、不改生成Rust/Vue来交付。源知识为docs/specs；本轮只列Spec提案，不写canonical、旧specs.json或手工索引。未知技术方案由T-00有界调查，不能靠占位/必需skip关闭验收。

独立运行门使用新建且本次拥有的临时数据/端口/构建输出；不删除既有app/框架target、不停止他人实例。CLI和真实编译/渲染tool都记版本/hash及发现路径；进程清理按本次spawn归属，不凭端口或命令行相似就杀进程。冷准备允许耗时，但须有阶段、就绪判定、有界超时和非零失败；预算及资源边界在T-00先冻结。

复用api/db/repository、notes_store和editor以及固定vendor/auto-down。先确认当前公开npm依赖声明和tool发现链，不能凭旧monorepo路径准备环境。编辑器非空稿/空稿分别核验；需要降级时必须可见并保稿，不能用降级永远替代已有可用富文本。框架共享问题可复用Blog等已有最小前置的实际交付，不等待Blog整个应用计划。

## 3. 技术栈

AutoLang/AutoUI .at、生成Rust服务、SQLite、固定AutoDown；Vue Playwright和原生MCP。复用tests/package.json、run_autotest.py、015-notes.autotest、run_v1_battery.sh与001的r9正反例，不把历史编号改名当新能力。

## 4. 需求分析与背景调查

用户2026-11-01要求接续其余原B类应用的下一步计划，沿上一轮“计划/README/roadmap、提交push，不开始实现、不更新OS子模块”的范围执行。Reader已转另一个会话按Readest新目标跟踪；Blog现有上游阻塞由原计划继续，Chat/Charts不在本轮改面。应用单独运行不等OS装配或其他app；Linux仍WAIT_DISTRO_M1（Nix＋COSMIC基础）。

001最终复审有Vue31项、电池S0–S22和52个scratch断言；当轮VM两次boot失败，按同源规则复用旧VM19/19和11个负例。该裁决保留，但不能证明当前工具链的独立原生首启。README/roadmap仍有旧needs_fix/未开始、旧apps/015-notes和v0.6-dev说明，需要修正。

当前pac声明Rust后端和vendor引擎npm依赖；001冻结的CLI已很旧。是否存在引擎dev挂载/依赖声明/工具部署缺口，只能由T-00对同一真实app做新探针，不根据Blog历史故障直接定案。

| 来源文件 | SHA256 |
|---|---|
| `docs/specs/notes/durable-inbox.md` | `82f9d252648541c089f6bfaf80b7c864b90a4226512c69822a079af7c29cb4bb` |
| `docs/plans/evidence/001-r9-review-20261029/README.md` | `635cbc7c652879b19e28afa6a02cf53d700b9589b11b6e82823413b3eca5e0e0` |
| `src/front/editor.at` | `1f1016695c10da347c68c94341b7062d421dc7980583542c2fc3c9d1a5f518be` |
| `src/front/notes_store.at` | `e224ff9e631c2954f86a3fd17509e6ba1dcb83d6107ae4ff4dc17e57dfdd47e2` |
| `pac.at` | `b44932988243d2f17ad12daec71a245843b50b0f668d1c9359875f7b75001225` |
| `tests/probe/run_v1_battery.sh` | `3a41839dd87d6b5539b7b67317dd8e94890cc0f7efd145e68c6496e4cbfa9aa4` |
| `tests/run_autotest.py` | `d850faca9bccbc0b3f1dca82ca98d34de5831de591f41e8490a90b16adc2a410` |

## 5. 详细设计

T-00新建决策稿 `docs/plans/evidence/004/standalone-decision.md`：固定源码、vendor pin、CLI/tool、实际npm依赖路径、空缓存准备/失败预算；分开记录Vue dev、已有构建模式与原生真实页面，选择文档化的正式profile。普通dev若有现存基本可用性问题须修接缝或消费具名最小前置，不能只引用preview成功。

拟新增 `tests/basic/verify_standalone.py --profile vue|vm`（T-04落地）负责编排隔离服务、既有Vue/原生用例和r9反例；旧autotest中的直接store消息/API步骤仅作辅助，不计真实输入/按钮保存证明。数据根和测试模式名称在T-00从当前源码核实，不凭历史默认路径删库。UI发起变更，HTTP/独立SQLite只读查询核对数据，不预写UI任务。

建立当前原生的编辑/标签失败后继续保存、同一笔记ID导航和真实冲突保稿证据。正常/强杀重开后下一次真实编辑必须成功，不能只读旧内容便宣布恢复完成。UI输入中文/引号/换行，编辑器内容和磁盘保真；001迁移、request_id重放与损坏保全语义不变。

### 规范增量

| delta_id | add/modify/retire | docs/specs/... target | before/after rule | rationale | acceptance IDs |
|---|---|---|---|---|---|
| SD-01 | modify | docs/specs/notes/durable-inbox.md | 旧冻结VM复用边界→当前实证运行/恢复与错误UI，不改001协议 | 补实际双端证据 | AC-02/03/04 |
| SD-02 | add | docs/specs/notes/standalone-runtime.md | 新增独立准备/启动、引擎/工具身份、失败与永久门 | 自足运行可复验 | AC-01/04 |

## 6. 测试设计

所有N用例owner_stage=work，由T-04建立永久入口后执行。复用001合法与负例输入，原始日志本地留存，不在用户库试验。

| Case ID | AC | 输入/真实入口 | 区分性oracle与预期 | 边界 |
|---|---|---|---|---|
| N-01 | AC-01 | 无本次缓存的正式准备、Vue/原生分别首启，坏tool/端口占用 | 真正编辑器可操作、自有后端/数据根正确；失败非零，不触碰旁观实例 | 不依赖OS |
| N-02 | AC-02 | 真实UI建笔记→中文编辑→保存→标签/置顶→导航重开 | UI/API/只读SQLite的note_id、正文、revision对应；原生不得API预保存代替 | 保留r9协议 |
| N-03 | AC-03 | 001元数据写拒绝/陈旧revision、软删恢复；解除失败再保存 | 横幅对应当前动作、正文不丢；重试无自身冲突；失败不能用旧横幅蒙混 | r9正负例+正常对照 |
| N-04 | AC-02/03 | 正常退出、强杀后重开并再次编辑 | 已确认内容/身份在位，下一次保存推进revision；实际UI输入法不抢键 | 两profile |
| N-05 | AC-04 | 故意遮蔽编辑器挂载/实际保存失败或期望负控 | 门确实检测失败并非零；还原正常通过，无必需skip/零场景 | T-04建立、非本轮已验 |

最终review冻结源码/工具版本，从工件独立重建判断；未满足的原生门不能留到merge。只跑本应用触面和必要框架消费验证，不跑无关语言Cargo全量。

## 7. 验收标准

- AC-01（owner_stage=work）：文档准备与Vue/原生独立首启可重复，N-01通过。
- AC-02（owner_stage=work）：真实双端编辑/保存/导航/重开、下一次保存与身份保真，N-02/N-04通过。
- AC-03（owner_stage=work）：r9失败接收/冲突/软删恢复不回归，文本保全且解除后可写，N-03通过。
- AC-04（owner_stage=work）：永久门汇总N-01..05与必要001回归，无必需skip/零场景，失败控制非零；README/SD对应实际运行。
- AC-05（owner_stage=review）：独立上下文复审AC-01..04、SD-01/02与依赖版本。
- AC-06（owner_stage=merge）：仅app规范/文档/新计划归档计数/提交push收尾；002/003与001历史保留，OSpin不变。

## 8. 执行步骤

- [x] T-00（owner_stage=work；依赖001；AC-01..03）：完成有界运行/依赖探针和决策稿，核实实际数据根/测试模式及最小owner前置。[✅ 已完成] 决策稿 [standalone-decision.md](evidence/004/standalone-decision.md)（G1 npm_deps 对象形态修复、G2 引擎 dist 冷准备、G3 旧生成 member 清理、G4 原生 split 框架缺口+owner=auto-ui）；数据根 `NOTES_DATA_DIR`/默认 `%APPDATA%/auto-notes/data`、门禁 `NOTES_TEST_MODE=1`（源码 repository.at:33/db.at:181 核实）；P-V 首启过 + Vue 31/31；P-N 10+ 次 0 过（merge vm+vm 可过，隔离矩阵在案）。
- [ ] T-01（owner_stage=work；依赖T-00；AC-01）：收口独立准备/启动和自有进程/数据隔离，明确空缓存与错误结果。**（Vue 半区收口：`tests/basic/verify_standalone.py --case n01` PASS——S1..S5 有界准备、空缓存首启就绪、坏 exe/端口占用两负控非零且不触碰旁观实例；CREATE_NO_WINDOW 会致工具链子进程静默失败已实证绕开；原生半区待 G4 解除）**
- [ ] T-02（owner_stage=work；依赖T-01和确需的实际前置；AC-02）：完成当前真实Vue/原生编辑与引擎路径；只修实证缺口，保留现有正确能力。**（Vue 半区：31/31 套件 + recovery spec 真实编辑保存 + 引擎 dist（dev/src 与 build/dist 双路径）✓；原生半区待 G4）**
- [ ] T-03（owner_stage=work；依赖T-02；AC-03）：回放失败保稿/冲突/软删和退出恢复后的下一次保存，关闭N-03/N-04。**（Vue 半区：N-04 PASS——真实 UI 中文/引号/换行落库 rev2 → 硬杀后端 → 同数据目录重启 → 正文逐字保真 + 下一次编辑 rev3（SQLite 磁盘核实）；N-03 由套件 R8/R9 负例 + battery S20..S22 fails=0 + scratch U11..U13 覆盖；原生半区待 G4）**
- [ ] T-04（owner_stage=work；依赖T-03；AC-04）：建立聚合入口，复用既有门并跑N-01..05及失败控制，准备SD候选。**（Vue 半区收口：`--case all` PASS——n01+n04+套件31+battery S0-S22+scratch 52 exit 0；SD 候选稿 [spec-delta-standalone.md](evidence/004/spec-delta-standalone.md)（SD-01/SD-02，含 G4 回填位）；vm profile 在 G4 解除前命名非零（无静默跳过））**
- [ ] T-05（owner_stage=work；依赖T-04；AC-01..04）：核对源码/依赖漂移、README/roadmap与证据覆盖，提交execution_done。
- [ ] T-06（owner_stage=review；依赖T-05；AC-05）：同clone独立上下文最终复审。
- [ ] T-07（owner_stage=merge；依赖T-06 pass；AC-06）：仅app规范/归档/提交push收尾，不集成OS。

## 9. 复审记录

- stage: new | plan_id: NOTES-004 | plan_revision: 1 | outcome: pass（有界T-00准备就绪；本轮没有实现或产品验收） | next: work/T-00（等待后续实施指令）。
- 已归档001、现实现Spec和产品源码保持不变；规划结构/链接通过不等于功能通过。review以同一clone的独立上下文核验，不自动创建agent/chat或指定模型。
- stage: work | plan_id: NOTES-004 | plan_revision: 1 | round: 1 | outcome: blocked | worktree: D:/autostack/auto-notes（本仓独立clone main，计划§2规约） | branch: main | base_commit: 82b4d2f | code_commit: （本轮实现提交=pac.at npm_deps 形态修复+决策稿+本记录） | dependency_revisions: vendor/auto-down c39ac7f9；工具链 auto 0.1.0+plan-890-verified-r7-t19-5-g55c98c7（auto-man 67add3c，tool=auto-ui 2f43b4f 含 plan-910 rust-ui 重写）；后端依赖 auto-lang 5923d4dee/auto-web | task_ids: T-00（完成）；T-01..T-05 Vue 半区部分推进、原生半区未开 | evidence: docs/plans/evidence/004/standalone-decision.md + D:/autostack/plan-artifacts/plan-004/t00/（P-V 首启 PASS 0.9s；Vue 全套 31/31 exit0；P-N 10+ 次 0 过：`run -r vm` split vm↔rust 工具宿主静默死亡，4s 速死与 96–132s 生成后死亡两形态；隔离矩阵 merge vm+vm 过/hello 过/stub-back 可达 cargo 具名错误） | blockers: G4 原生门=auto-ui owner 缺口（plan-910 rust-ui 重写当日落地强相关；auto-database plan-002 同症先例在案），跨仓修复超出本计划授权（§2），验收调整需用户裁决（§10） | next_responsible_role: user（裁决后回 work：T-01 起）
- stage: goal | plan_id: NOTES-004 | plan_revision: 1 | round: 2 | from: blocked | to: work | status: executing | outcome: pass | note: 用户裁决选 §10 选项1——等 plan-910 收口+工具重建后重探原生门（P-N），期间 Vue 轨 T-01..T-05 继续推进；G4 保持挂起、受影响原生半区任务保持未完成。 | next: work/T-01（Vue 半区收口）
- stage: work | plan_id: NOTES-004 | plan_revision: 1 | round: 2 | outcome: pass（Vue 半区） | worktree: D:/autostack/auto-notes | branch: main | code_commit: 0f44298 + 本轮聚合/SD 稿 | task_ids: T-01/T-02/T-03/T-04（Vue 半区收口） | evidence: D:/autostack/plan-artifacts/plan-004/（t01-n01-vue.log N-01 三控 PASS；t03-n04-vue.log N-04 rev2→3；t03-battery-retry3.log S0-S22 fails=0；t03-scratch.log 52 fails=0；t04-all-vue.log 聚合 exit 0） | blockers: 原生半区待 G4（plan-910 未落地，轮末复查） | next_responsible_role: work（G4 解除→原生半区；未解除→waiting）
- stage: goal | plan_id: NOTES-004 | plan_revision: 1 | round: 3 | from: waiting-check | to: waiting | status: executing | outcome: waiting | note: 复探条件未满足——auto-ui master 仅新增 plan-029 文档提交（cc18ef8a/150bab3e，doc-surface 记录），无解析层修复；auto-ui-tool.exe 仍为 11-02 07:21 构建；ui-029 分支在 doc-surface 特性线上。等待计数 1/3，继续挂起（每轮一次落地检查；3 连空转后按协议挂起 blocked）。 | next: waiting（条件=auto-ui master 解析修复+工具重建）

## 10. 待澄清事项

**当前阻断（2026-11-02，T-00 后）：原生门被工具链框架缺口 G4 阻塞，需要用户裁决。**
现状：`auto run -r vm`（vm↔rust split，原生真实页面唯一入口）在当前工具链（auto g55c98c7 + auto-ui 2f43b4f 含当日落地的 plan-910 rust-ui 重写）上 10+ 次有界尝试 0 次成功——工具宿主静默死亡；merged vm+vm、Vue 轨、最小 hello、直启后端全部正常（隔离矩阵见决策稿 G4/§6）。owner=auto-ui（跨仓修复本计划不授权）；auto-database plan-002 有同症记录与 owner 前置先例。

请裁决原生门走法（受影响任务保持未完成，不做静默降级）：
1. **等 plan-910 收口**：auto-ui 的 rust-ui 重写正在另一会话进行（review R1 修复已落），待其合并+工具重建后重探原生门（推荐——不动验收，最小新增范围）；**← 用户 2026-11-02 裁决选此**。期间 Vue 轨（T-01..T-05 的一半）继续不受阻推进；plan-910 合并+工具重建后重探 P-N，重开原生半区。
2. **另立 owner 最小前置**：按计划 §2 在 auto-ui 仓新建最小修复计划（跨仓写入范围扩大，需明确授权）；
3. **调整验收**：临时以 Vue 轨 + 001 r9 同源旧 VM 证据收口（削减 AC-02/04 的当前工具链原生半区——验收变更，需明确批准）。

**重探条件精化（2026-11-02 轮2末）**：用户裁决的"plan-910 收口"已发生（auto-ui master 01f99fd + 工具 07:21 重建），原生门仍红但诊断精化——**G4a 宿主静默死亡已被 plan-910 修复**（现给出具名错误）；**G4b 现存**：当前 VM 解析层拒绝本仓 r9 有效源码的样式名构造（`sidebar.at:111` 条件分支样式名、`editor.at:106` 跨包命名导入配方名；Reader/Musk 同族构造可行），owner=auto-ui，其 ui-029 线（更新工具构建）可能已含修复。**重探条件 = auto-ui master 含 ui-029 线解析修复（或等价）+ 工具重建**；届时每轮一次 `run -r vm` 有界复探（MCP 就绪判定），仍红则继续等待计数。Vue 轨全部完成不受影响。

其余事项：当前没有需要用户重复确认的产品方向。技术不确定性由T-00记录真实证据、owner与依赖任务；若需要改变目标、削减必需验收或扩大跨仓写入范围，先明确报告，受影响任务保持未完成。归档/merge只完成本app的Spec/计划/提交push与自有临时产物收尾，不更新AutoOS gitlink、manifest或.gitmodules；后续OS统一计划接收已单独验证的固定SHA。
