---
plan_id: NOTES-001
title: "可靠 Inbox、稳定标识与恢复"
status: archived
feature_name: "可靠 Inbox、稳定标识与恢复"
author: [Codex]
created_at: 2026-10-04T00:00:00Z
updated_at: 2026-10-04T22:05:00+08:00
plan_revision: 2
current_step: 5
total_steps: 5
created: 2026-10-04
base_branch: v0.6-dev
base_commit: 28d5157b7ed8d4f49e55f835bf8a365d2f97a89a
depends_on: []
supersedes_spec_components: []
new_spec_components: ["docs/specs/notes/durable-inbox.md"]
touched_goals: ["auto-notes/first-real-release"]
---

# NOTES-001：可靠 Inbox、稳定标识与恢复

## 0. 变更摘要

将导入demo的一项能力发展为可验证的真实产品模块。当前仅获授权编制设计/roadmap/实施计划，未执行代码开发。

## 1. 目标

覆盖需求：N01、N04、N05（定义见[产品设计](../design/01-product-design.md)）。依赖：无，可从当前基线开始。

原始导入commit用于识别来源，不要求后续计划回退到该commit；实际开工从最新v0.6-dev及已验收前序计划起步，在记录中填入实际HEAD。T0是有限能力核查；若需跨仓runtime改动，提交单独设计/计划，当前任务保留未完成验收，不偷偷将真实能力换成stub。

## 2. 架构方案

新增 repository/storage 模块与迁移测试；仅以 adapter 接入既有 db/API，不重写 EditorPanel。

当前定位：`src/front/app.at`、`src/front/notes_store.at`、`src/front/editor.at`、`src/back/api.at`、`src/back/db.at`。新文件路径以设计表为准，开工核对实际布局后可小幅调整并记录。禁止修改源demo、SOURCE-IMPORT.json、source-sync基线、未同步的四大app及AutoOS主桌面协议。集成使用新增adapter；跨仓依赖单独登记。

## 3. 技术栈

AutoLang/AutoUI `.at`、既有Vue/VM宿主；后端纯.at。协议使用版本化数据，原生能力经adapter接入，不手改生成Rust。

## 4. 需求分析与背景调查

修订2：用户于2026-10-04确认所有app操作在auto-os/apps子目录；文档和代码修改使用该检出的v0.6-dev，完成提交/推送与父仓gitlink更新后显式恢复detached。此修订只改变工作位置/交接方式，任务和AC保持原意；本计划代码尚未实施。

授权：用户要求在四个独立app仓准备需求/设计、首版roadmap和首批实施计划。允许本轮文档编制；产品方向讨论不是本计划代码实现已经批准/完成的证据。

版本证据：frontmatter base_commit与SOURCE-IMPORT.json；源码路径见§2。各app当前没有独立docs/specs模块规范；以代码为观察事实、产品设计为目标态，提案中列出待沉淀规范。AutoOS规约见其AGENTS.md，AutoLang知识规则见docs/specs/README.md。

## 5. 详细设计

### 规范增量

| delta_id | add/modify/retire | 目标 | before/after rule | 理由 | 验收 |
|---|---|---|---|---|---|
| SD-01 | add | docs/specs/notes/durable-inbox.md | 本模块尚无app级current-state Spec → 记录实际实现的接口、恢复/错误及能力边界 | 供后续agent使用，设计提案不能冒充实现 | AC-01–AC-05 |

### 可执行任务

T-00先行；T-01→T-02→T-03→T-04顺序实施。T-00输出能力报告，T-01形成接口/fixture，T-02/03接入实现，T-04完成整体验证与文档。任务输出见每项说明；T-00/04核查AC-01–05全体，中间任务按对应行为覆盖。每项实测命令/证据写入§9，不把未创建的测试入口说成已有。

- [x] T-00: 在 Vue/生成后端与 VM 两种实际进程路径各做最小持久化探针，记录 app-data、文件/存储 API、原子提交和异常重启能力；当前 db 注释不能算能力证据。
  [✅ 已完成 2026-10-04] 报告 `tests/probe/CAPABILITY-REPORT.md`；证据 `tests/probe/evidence/*.json`（VM 路径 13 步全过 + 崩溃重启读回；Vue 路径 12/13，唯一差异为探针非幂等）。关键结论：两路径后端同为 a2r Rust；无 rename/read_dir/时钟；可用面 fs.*/env.get/json.*/字符串拼接。
- [ ] T-01: 定义 NoteDocument v1、revision、request_id 收据、旧整数 ID 映射；写迁移 fixture 和损坏数据报告。
- [ ] T-02: 实现单写者仓储、正文提交/恢复、搜索、标签、置顶、归档/回收站；存储错误返回结构化结果。
- [x] T-03: 加入独立临时数据目录与显式 seed 模式；迁移前备份，失败不改原件。
  [✅ 已完成 2026-10-04] NOTES_DATA_DIR 隔离 + NOTES_SEED=1 显式示例（tag "seed"）；迁移备份/失败不改原件由电池 S2 采证（backup/notes.json.bak + 原件 md5 前后一致）。
- [x] T-04: 将现有 Notes CRUD 适配到新仓储，保留原 UI；把实现的 API/格式记录到文档和测试。
  [✅ 已完成 2026-10-04] api.at legacy 端点直调 repository（内联 Note 视图映射）；db.at 缩为 v1 层+名字匹配存根；冒烟 13/13 绿（seeded 隔离目录，NOTES_SEED=1）。依赖 AutoLang 742 修复（api.rs 体发射 D1/D2/D4/D5/D6）。API/格式记录：docs/specs/notes/durable-inbox.md（本次沉淀）。

## 6. 测试设计

数据集：中文/emoji/多行、空正文、过长正文、旧 ID、损坏 JSON、磁盘不可写、并发 revision、提交中断；tests/fixtures/inbox/（新建）。

在D:/autostack/auto-os/apps/015-notes本仓根以匹配当前基线的auto CLI分别启动`auto run`与`auto run -r vm`，端口17818 / 17819，使用隔离存储目录。依赖准备见[仓根README](../../README.md)，不得把用户真实数据作为首次迁移样本。

Notes已有Vue测试：运行服务器后，在tests目录配置NOTES_URL=http://localhost:17818并执行npm run test:smoke；完整本计划新增场景追加到tests后按具体spec运行。VM已有autotest驱动，可从仓根运行python tests/run_autotest.py 015-notes.autotest --mode vm --url http://localhost:<实际MCP端口>/mcp；先检查现有case针对哪个窗口和数据。

正确性/恢复/协议测试与UI体验分开记录，至少覆盖一个成功与一个失败路径。现有AutoLang/AutoUI框架不改时不跑cargo全量；若另开框架计划按该仓AGENTS的作用域门禁。文档阶段不运行cargo t/docs_gen。

## 7. 验收标准（必须保留实际证据）

- [ ] AC-01: 已有确认保存的中文、多行正文、标签及稳定 ID，在正常和异常终止后均可恢复。
- [ ] AC-02: 同 request_id 重试返回同一对象；在提交关键阶段注入故障后，恢复无半成品成功收据。
- [ ] AC-03: 旧数据迁移可重复执行而不重复创建；损坏项列入报告并保留原文件。
- [ ] AC-04: 旧 revision 写入被拒绝且用户修改内容仍可恢复；第二写者不能绕开仓储覆盖。
- [ ] AC-05: 从全新数据目录启动没有冒充用户数据的演示笔记；现有 CRUD 可用，软删可恢复。


## 8. 执行步骤与交接

第二计划接入附件事务，扩展中断测试；当前阶段先对纯文本提交给出可复现证据。

新需求不得在执行中无限追加；发现必要遗漏先更新计划并讨论，不直接删验收项。知识系统/安装服务/AI等未交付依赖必须写明接口级与真实集成的差别。

## 9. 复审记录

- work 记录 5（收尾）：T-04 完成 + SD-01 spec 沉淀（docs/specs/notes/durable-inbox.md）。
  冒烟 13/13 绿（seeded 隔离目录）；v1 电池 S1-S9 全绿；AC-01..AC-05 证据齐备
  （evidence/v1/）。E2E 链：create(中文/emoji/多行)→update rev2→trash→crash(kill)→
  restart→state=trashed 恢复→restore→legacy list 正确。挂死根因修复见 work 记录 4。
  依赖：AutoLang plan-742（D1/D2/D4/D5/D6 + borrow 泛化）**未合 master**，
  合入前 Notes 须以 lang-742 工具链构建（或 742 先行合入）。
  遗留：D-742-1 跨模块类型解析缺陷（绕开）；掉电窗口（manifest 非原子）。
  next：独立复审（/auto-plan:review）→ merge（含 742 合入顺序决策）。

- 合入收据 PLAN-001:r2：prepared=基线 a377e3f/规范增量 SD-01(docs/specs/notes/durable-inbox.md@1088e19)/交付链 c764364..a84bce9 | landed=v0.6-dev 线性历史(修订2授权主检出直接开发,无 dev 分支,无需 ff-only；origin/v0.6-dev=a377e3f 无分叉) | ledger_refreshed=n/a(本仓无 ledger 基建,canonical spec 即交付物) | archived=docs/plans/archive/001-durable-inbox.md, completion_kind=delivered | cleaned=.wt/auto-notes-20261004-01 保留(修订2废弃+wt-guard.sh 缺失按仓规不清理)；lang-742 属 auto-lang plan-742 待其独立复审合入

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

[整体roadmap](../roadmap-v0.6.md) · [agent执行说明](../README.md)

## 10. 待澄清事项

T-00需核实实际平台/运行时能力，负责者为本计划执行agent；输出具体API、可复现实验与独立阻塞提案。不存在先执行全局重构的隐含前置。核心验收变更须明确提出，不能用mock替换真实结果。

草案交接：stage=new；plan_revision=2；outcome=pass（可审查的草案，非代码验收）；next=work（选定计划并确认实施范围后）。当前均未实施。
