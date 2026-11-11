---
plan_id: NOTES-006
status: executing
feature_name: 共享笔记服务与可嵌入编辑器
author: [Codex]
created_at: 2026-11-07
updated_at: 2026-11-10
plan_revision: 2
current_step: 4
total_steps: 8
supersedes_spec_components: [docs/specs/notes/durable-inbox.md]
new_spec_components: [docs/specs/notes/featurepack-service-and-editor.md]
touched_goals: []
---

# NOTES-006 · 共享笔记服务与可嵌入编辑器

## 0. 变更摘要

将现有 Inbox 扩展为带来源的笔记服务，同时在主应用和外部宿主使用同一份轻量编辑组件。

[AutoOS 总计划](../../../auto-os/docs/plans/archived/065-notes-featurepack-v0.md) · [Reader 宿主](../../../auto-reader/docs/plans/013-notes-featurepack-host.md)

## 1. 目标

首版交付范围见 AC-01、AC-02。动态加载、跨进程 UI、AutoLens、图片/公式、词典/AI、知识库加工以及 ACE/AGE 切换留给后续计划。

## 2. 架构方案

Notes 后台是持久笔记唯一写入者。编辑组件接收来源或 note_id、允许操作和宿主回调；每个宿主实例通过 Notes 公共适配持有草稿、修订号和未完成请求。主应用的列表和导航继续使用自己的 Store。

## 3. 技术栈

现有 .at API、repository、SQLite、AutoUI widget/props/emit 与双端构建。

## 4. 需求分析与背景调查

本次授权起草计划。2026-11-07 基线 16f3efb0；docs/specs/notes/durable-inbox.md、src/back/{api,repository}.at、src/front/{editor,notes_store}.at。当前 requests 与 notes 已同事务，编辑器依赖当前应用草稿。NOTES-002 的附件、NOTES-003 的知识转交仍由原计划负责。

## 5. 详细设计

捕获操作接受可信来源作用域、稳定操作 ID、不可变来源快照（书 ID、版本、作者、原句、可选章节和版本化定位数据）、可编辑正文。返回 note_id、revision 与提交回执。支持读取、按书分页、按 expected_revision 更新和查询回执。Notes 主应用按本地 OS 用户查询，Reader 的读写操作按系统授予的书籍范围校验。正文、书名、作者、来源版本均保留原始 Unicode。书键、分页游标、请求预算及保存大小上限在 T-01 对照旧库、真实 EPUB 样例和 F0/F1 边界定稿。校验来源包络，锚的语义由 Reader 负责。既有无来源便签照常使用。正文、来源关联和回执在同一事务中提交，相同主体和操作重放得到原结果；不同意图拒绝。

编辑组件接受创建/编辑两种输入，发出已保存和回访事件；两个实例可并存。按实例与来源持久暂存未提交草稿，恢复时以相同操作重试；并发修订冲突保留用户输入供重读、比较和再次提交。组件代码由 Notes 发布，复用构建方式由系统 T-01 探针确定。

### 2026-11-10 r2 执行合同

联合计划改由 [OS-067](../../../auto-os/docs/plans/067-notes-featurepack-product-closure.md) 承接，历史 OS-065 位于 archived。本节落实 F-02/03/05/06/07，替代上文“草稿按实例暂存”中未明确持久所有者的描述。基线 auto-notes@1aa2e7251c9c437d3bf53ca935d539bd4fc499be；本次为计划审核，原起草会话，无产品实跑。当前服务成绩仅覆盖已执行的 API 用例，T-02/03 在新增闭合条件满足前保持 partial。

- 领域身份由可信主体和 operation_id 决定。每次新建、每次用户确认更新分配独立操作 ID；同一意图的同 payload 重试复用 ID，attempt 每次重新分配。内容相同的新建仍可产生不同笔记，领域去重与内容匹配分开。更新意图绑定 note_id、expected_revision 与正文。保存前先持久记录本地操作包络。
- Notes 提供共享宿主适配逻辑，集中维护 draft_key、generation、note_id、base_revision、operation_id、待提交 payload、用户输入版本与保存状态。草稿按本地用户、宿主、书目/笔记和实例区分，命名空间稳定至重启恢复，保留或丢弃须有明确用户动作。组件为受控 props 与回调，宿主逐实例持状态，异步结果先核 draft_key/generation/输入版本。成功只清除已提交那一版输入，提交后继续键入的文字保留并仍为未保存。
- 草稿读取/写入/替换失败保留当前输入并明确反馈。已提交但回包丢失时查询 receipt 或同 ID 重试；not_observed 保留待确认状态。冲突保用户稿和服务端稿。明确区分 idle/dirty/saving/saved/pending/error/conflict，传输或磁盘失败不投影为可 Rebase 的修订冲突；重新指定服务端 revision 后是新更新意图。
- API 核验来源结构的类型、版本、长度和必要字段，保存完整不可变快照；Reader 负责语义锚验证。既有只有 book_id 的 fp 行与普通便签保持可读，字段缺失显示来源不完整，定位入口不可用；新 Reader 提交使用 OS M1 固定的来源版本。来源含书目 ID、真实 source_hash、标题/作者、quote、章节和 canonical locator。创建正文 title 与不可变 quote 的关系固定，更新正文不改变来源。
- SQLite 迁移把 book_id/source_json 附加列、requests 原语义、13列旧投影的兼容边界写进 durable-inbox；恢复/普通便签编辑不能意外抹掉来源。对附加列失败与事务中间写失败做隔离反例。
- 组件发布使用实际 FpNoteEditor 与 components/pac.at，明确 create/edit、只读/禁提交、来源回访是否可用的配置及默认值；配置不得提升服务权限。来源回访可由组件事件或宿主来源卡发出统一 OpenSource(note_id,source) 事件，T-06 冻结唯一出口，两个应用一致消费。包提供逐字段参数/事件清单和完整 SHA/组件 hash，path-only 依赖通过交付清单固定来源。
- 本地服务身份采用 OS 用户/policy，不增加登录账号前置。旧 T-03 中 model/Init/回调适配结论保留为历史观察；现在是否成立由双端同一测试输入复核，不把未经验证的引擎规避扩大成新规范。


### T-06 冻结（2026-11-11，基线 auto-notes@1aa2e72 + OS-067 M1）

以下冻结为双宿主共同合同，实现与测试以此为准。

**来源 schema（不可变快照）**：

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| book_id | str 非空 ≤128 | 书目域名（book:<id>） |
| source_hash | str 真实内容哈希 | Reader 负责，禁固定 v1/空 |
| title / author | str 保留 Unicode | 书目原文 |
| quote | str 非空 | 原句（不可变） |
| chapter | int 可选 | 章节号 |
| locator | JSON 对象（kind/v/value） | canonical 定位（CFI），Reader 验证 |

**操作身份（每次意图分配）**：operation_id = 单元意图稳定 ID（新建/用户确认更新每次新；同意图重试复用）；attempt_id = 每次调用新。去重键：fp:<principal>:<operation_id>（requests 表复用）；内容相同的新建仍可产生新笔记（领域去重与内容匹配分开）。

**草稿状态机（共享适配）**：每宿主实例持：draft_key（本地用户+宿主+书目/笔记+实例）、generation（每次外部变化递增）、note_id/base_revision/operation_id/待提交 payload/用户输入版本/保存状态。state 值：idle / dirty / saving / saved / pending（回包未观察）/ error / conflict。异步结果先核 draft_key/generation/输入版本；成功只清除已提交那一版输入。传输/磁盘失败不投影为可 Rebase 的修订冲突；重新指定服务端 revision 后是新更新意图。

**FpNoteEditor 参数/事件（冻结，以 fp_editor.at 实际契约为准）**：props：mode（create|edit）、note_label、draft_text（草稿 prop 往返）、save_state、conflict_revision、server_body；回调：on_draft_edit(v)、on_submit_text(text)、on_rebase。组件零网络依赖（I/O 宿主执行）。

**共享适配模块路径（T-07 新建）**：src/front/components/fp_host.at（逻辑模块，非组件），package.at 添加导出；两宿主经 `use notesfp.fp_host: <函数>` 导入，确认可导入后 T-07 实现。
### r2 执行实测修订（2026-11-12，work T-02/03/07）

以下为 r7-t19-20 工具链实测裁定，修订上文对应描述；契约语义不变：

1. **共享适配导入形态**：主应用 store 用点路径 `use components.fp_host: <函数>`
   （点路径→文件解析）。`fpack.fp_host` 包名形态在 vue 生成器 use-fn 池**静默
   跳过**（不解析不告警）→ 运行期 ReferenceError；reader 跨仓仍用
   `use notesfp.fp_host: <函数>`（dep 物化面，READER-013 消费）。
2. **前端无 int→str 原语**：vue 生成面对 store 体/use-fn 池的 `json.*` 不映射
   （ts_adapter 的 json 映射只在 widget 表达式路径生效）。草稿键的 int 段改由
   服务端组装（/api/fp/draft/*/note 端点，int id + instance）；键格式契约不变
   （fpdraft|local|notes-main|note:<id>|<instance>）。
3. **组件回调名（裁定③复证）**：emit 用组件内部消息名原样发出，App 监听
   on_rebase 派生名 `Rebase`——内部名必须同为 `Rebase`（r1 的 RebaseTap 在本
   工具链为死路）。另：`.at` 注释只能 `//`（`#` 破坏解析→组件静默回退旧产物，
   且 ui-cache 对组件源不追踪 hash，改组件后须手清 `.auto/ui-cache.json`）。
4. **传输失败恢复路径**：vue 客户端网络失败为异常中断（handler 死在 await，
   不返回零值 RepoResult）——会话内不可达 pending；「已提交但回包未观察」的
   恢复 = 重启（Init/SelectNote 把持久 saving 映射 pending 并把观察态写回槽），
   同 ID 重试经意图重放幂等（S-3c 实证）。
5. **生成器借参**：fn 调用结果直接作 `str` 形参不自动借参（E0308）——先落
   局部变量再传（仓内惯例）。
6. **G-10 实锤与规避**：fp list 对含中文 title 行产出坏 JSON（`substr(0,
   len()-1)` 在局部字符串变量上 len 产字符数、substr 按字节，F-09a 崩溃复现；
   即 OS-067 G-10 同源）。fp 信封改 `row_to_doc_fields` 纯拼接（免 substr/len）；
   13 列投影对 legacy_id NULL 行防御为 0（S-02 注入实证）。
7. **VM 引擎缺口（AutoUI，仓外依赖，阻塞 VM edit 实例输入面）**：同一
   FpNoteEditor、同一绑定、同一 type_text 工具——**无条件分支实例**（create）
   键入→oninput→宿主回调链全通（VM M-1/M-2/M-2b 绿：中文/emoji 真实输入、
   提交、服务端逐字核对），**条件分支实例**（`if .store.draft_id != 0` 内的
   edit 实例）type_text/clear 后 store 状态恒 idle（M-3c/M-5a0 红，现取快照
   id + 3× 重试 + clear 分辨非空初值后仍死）；Vue 轨同结构全绿（25/25）。
   键控重挂假设已排除（初始选中即靶行、无中途重挂仍死）。最小反例 =
   015-notes FP 区（app.at if 分支内 FpNoteEditor）双实例差分。owner=AutoUI
   （VM 条件子树内组件回调注册）；按 §10 预案评估单独立项。r2「由双端同一
   测试输入复核」要求的复核在本缺口上完成并留证。

### r2 规范增量补充

| delta_id | add/modify/retire | docs/specs/... target | before/after rule | rationale | acceptance IDs |
|---|---|---|---|---|---|
| SD-02 | modify | docs/specs/notes/durable-inbox.md | 旧13列/requests→来源附加列与旧API共存、迁移回滚/回执权限 | 覆盖真实持久层改面 | AC-01/05 |
| SD-03 | add | docs/specs/notes/featurepack-service-and-editor.md | SD-01 细化为操作身份/持久草稿/公共状态/参数事件/失败和恢复协议 | 可由两宿主一致执行 | AC-02/05/06/07/08 |


### 规范增量

| delta_id | add/modify/retire | docs/specs/... target | before/after rule | rationale | acceptance IDs |
|---|---|---|---|---|---|
| SD-01 | add | docs/specs/notes/featurepack-service-and-editor.md | 从现有单应用或探针边界扩展为第 2、5 节的产品契约 | 固定真实宿主行为与数据归属 | AC-01/02 |

## 6. 测试设计

V-01 / AC-01：对隔离旧库取升级前后快照，实际 API 重放、改正文重放和并发更新，核笔记/来源/回执及 revision。V-02 / AC-02：两个实例编辑不同笔记，再编辑同一旧修订；关闭其中一个，用中文输入、重开并核草稿与服务端最终文本。

上述为拟验用例，owner_stage 为 work。第 8 节所列新脚本由对应任务建立，约定从本仓根运行 `python <脚本路径>`，默认使用隔离目录，双端用例分别记录 Vue 与 VM 结果，断言失败或缺少必需用例返回非零。最终复审复演风险用例，记录所用提交和实测结果。

### r2 必需补充用例

| ID / owner_stage | AC | 入口与区分断言 |
|---|---|---|
| S-01 / work | AC-01/05 | verify_featurepack_service.py 新增提交成功丢回包→重启→同操作同文重放；note/receipt/revision 不增加。同 ID 改文返回 request_conflict，另一个新 ID 同文创建新笔记 |
| S-02 / work | AC-05 | 旧普通便签与旧 fp 行、附加列迁移半途故障、未知来源版本、超限来源、错类型；失败无半写，旧内容可读，已知残缺来源有明确不可回访状态 |
| S-03 / work | AC-02/06 | verify_featurepack_editor.py 两实例真实输入，保存过程中继续键入、切实例、关页/重启恢复、迟到回包；新输入保留，另一实例不变，原操作可续查 |
| S-04 / work | AC-06/07 | 服务断开、磁盘拒写、修订冲突再 Rebase，三类状态区分；来源动作及配置收窄在两宿主可观察；配置不能开放未授权操作 |
| S-05 / work | AC-08 | Vue/VM 两端中文/emoji真实输入和提交、冲突/恢复全部实跑；强制必需 skip/漏 case 时非零，测试只操作自有 PID/端口和隔离库 |

命令在 work 完成脚本后分别运行 python tests/basic/verify_featurepack_service.py、python tests/basic/verify_featurepack_editor.py --profile vue 和 --profile vm。S-01/02 在 T-02/S-03～05 在 T-08 建立可执行断言。原 VM 脚本即使检测到 input 工具也主动 skip，属于测试入口未接，不能据此判断引擎无输入能力。采用现有真实工具或原生自动化完成输入，缺失保持未通过。全局 taskkill /IM 清理改为只回收自有进程后才运行脚本。

## 7. 验收标准

| ID | owner_stage | 可观察结果 |
|---|---|---|
| AC-01 | work | 旧库升级后普通便签仍可读写；提交后丢回包并重启，相同操作仅生成一条笔记；变更意图或过期修订拒写，原内容和回执可读。 |
| AC-02 | work | 同一组件在双端可嵌入，主应用与宿主看到同一修订；关闭一个实例或收到迟到回包不改变另一个实例草稿，冲突输入可恢复。 |
| AC-05 | work | 新旧库与来源 schema 兼容、来源不变、每意图 ID/提交丢回复恢复通过 S-01/02。 |
| AC-06 | work | S-03/04 成立，跨重启草稿、输入版本与迟到响应隔离，通用错误/待确认/修订冲突可区分。 |
| AC-07 | work | 真实组件/公共状态适配和来源事件有完整参数表及版本清单，两宿主消费同版，配置收窄可见。 |
| AC-08 | work | S-01～05 必需格无 skip/缺失，Vue 与 VM 均真实输入，进程与数据隔离成立。 |
| AC-03 | review | 独立上下文复演第6节原有与r2补充用例，核全部work验收，证据绑定应用、引擎、服务和包版本。 |
| AC-04 | merge | 按评审版本交付，核对 SD-01 与实测边界，归档回执。 |


## 8. 执行步骤

拟实施位置 D:/autostack/auto-notes 独立 clone，main。work 先核实际基线与 OS067 M1，就绪任务按下表依赖执行；旧进度以r2复核结果为准。跨仓依赖按具体交付任务推进，OS 汇总验收位于两子计划之后。

| ID | owner_stage | 依赖 | 工作与验证 | 验收 |
|---|---|---|---|---|
| T-01 | work | 无 | [x] 在 src/back/repository.at、src/front/editor.at 盘点迁移与实例依赖，提供旧库、重复请求和双实例样例，与系统 T-01 对齐。[✅ 已完成] 盘点结论：迁移依赖点=ensure_schema 幂等 ALTER 惯用法 + upgrade_if_legacy/repair_legacy_merge 状态机（schema_v=3 不动，fp 列附加式不改状态机）+ migrate_request_intents（v2c| 门不受扰）；实例依赖点=requests 表（request_id PK）复用为 fp 去重键 `fp:<principal>:<operation_id>`、replay_in_txn 规范化意图复用、BEGIN IMMEDIATE 单写者门同律。样例：旧库=tests/fixtures/inbox/legacy-v0/notes-valid.json（既有，3 条含中文/emoji）；重复请求=verify_featurepack_service.py F-03/F-04/F-06（同键重放/异载荷冲突/更新重试幂等）；双实例样例归 T-03 编辑器面（两实例并发编辑不同笔记 + 同旧修订冲突，见 §6 V-02）。OS-T-01 对齐：notes.fpack/1 版本串、凭据→policy 绑定、operation_id 去重、attempt 与 operation 分离（auto-os worktree featurepack-v0.md §2/§3）。 | AC-01/02 |
| T-02 | work | T-01、T-06 的字段冻结 | [x] 冻结 schema 服务端校验（闭集 7 键/类型/长度/哨兵 hash 拒绝）、读投影 source_status（ok|incomplete）、迁移半途故障自愈反例、S-01 重启重放幂等、S-02 拒绝面/兼容面。[✅ 已完成 2026-11-12] verify_featurepack_service.py **67 PASS / 0 FAIL / 0 SKIP**（F-01..11 旧 39 项全数保持 + S-01 11 例 + S-02 17 例；G-10 免 substr 信封后 F-09 中文翻页修复）。fn 局部 str 的 substr/len 生成器漂移（G-10）在 F-09a 崩溃复现，fp 信封改 row_to_doc_fields 纯拼接规避；legacy_id NULL 行投影防御（S-02 注入实证）。 | AC-01/05 |
| T-03 | work | T-02、T-07 | [x] 两实例（edit/create）经 fpack.fp_host 公共机制（fp_state_next 七态/draft_key 命名空间/OpenSource 统一出口载荷）；组件七态徽标投影（pending/error 增补）；主应用来源卡（source_status=ok 才可回访，incomplete 明确不可回访）+ OpenSource 消费卡。[✅ 已完成 2026-11-12] verify_featurepack_editor.py --profile vue **25 PASS / 0 FAIL / 0 SKIP**（E-0..E-6 + S-3a 保存中键入只清已提交版 + S-3b 关页重启恢复 + S-3c 丢回包→重启→pending→同 ID 重试 saved + 冲突保输入 Rebase 再提交）。实测修订四条见 §5 r2 增补：①store 用点路径 components.fp_host（fpack 包名形态在 use-fn 池静默跳过→ReferenceError）；②vue 生成面 store 池不映射 json.*（键组装移服务端 note-scoped 端点）；③组件内部消息名=派生监听名（RebaseTap→Rebase，裁定③复证；`#` 注释破坏解析致组件静默回退旧产物，须 // 且手清 .auto/ui-cache.json）；④vue 客户端传输失败为异常中断，回包未观察恢复走重启映射 pending。 | AC-02/06/07 |
| T-06 | work | T-01、OS-067 T-01 | [x] 冻结来源schema、ID/草稿状态、FpNoteEditor参数/事件/配置；新建共享适配的实际路径在本步列明，确认两个宿主可导入。[✅ 已完成 2026-11-11] 冻结落§5 T-06 冻结节：来源 schema（book_id/source_hash/title/author/quote/chapter/locator）、操作身份（operation_id 单元意图 / attempt_id 每次新 / 去重键 fp:<principal>:<operation_id>）、草稿状态机（draft_key/generation/note_id/base_revision/operation_id/payload/输入版本/save_state；state=idle|dirty|saving|saved|pending|error|conflict）、FpNoteEditor 参数/事件表。共享适配路径=src/front/components/fp_host.at + package.at 导出；导入形态：主应用 `use { package: official from "./components" }`，reader `use notesfp.fp_host: <函数>`（跨仓 dep notesfp 已指 components 目录）。 | AC-05/06/07 |
| T-07 | work | T-06、T-02 | [x] fp_host.at 共享适配（七态状态机/守卫/draft_key/OpenSource 载荷，纯逻辑零网络）+ notes_store.at 接入（意图稳定 op 兼主路径 rid、输入版本守卫、成功只清已提交版、检查点持久/恢复、Discard 显式清槽）+ fp_drafts 表（分列存，64KiB/槽）+ /api/fp/draft/*（通用键）与 /api/fp/draft/*/note（int id 服务端组装键——前端无 int→str 原语）+ /api/fp/source/of[/note] 来源投影。[✅ 已完成 2026-11-12] 服务 67/0/0 + Vue 25/0/0 实证；S-3 系列断言检查点落盘/恢复/清槽与服务端终态。editor.at 无需改动（fp edit 实例与主编辑器同源 draft_body，共享机制在 store 层）。 | AC-02/06/07 |
| T-08 | work | T-03 | [x] partial——脚本重写完成：VM 轨接真实输入（autoui type_text，r1「无输入面」系测试入口未接）、press/type 至状态生效（vnode 换代现取 id）、必需 case 无 skip（缺失即 FAIL 非零）、进程清理只回收自有 PID 树（全局 /IM 清扫移除，OS-067 G-04/G-05 关闭）、资源隔离（隔离目录/policy/端口自检）。S-01/02 服务脚本 67/0/0、S-03(S-3a/b/c)+冲突 Rebase Vue 轨 25/0/0、S-05 VM 轨 create 链真实输入绿。SD-01/03=docs/specs/notes/featurepack-service-and-editor.md、SD-02=durable-inbox.md FeaturePack 共存节、三仓消费清单入 spec。**[🔴 blocked 子面]** VM edit 实例输入面：AutoUI 引擎对条件子树内组件回调注册失效（§5 实测修订 ⑦ 最小反例）——M-3c/M-4 系/M-5a/M-6 如实 FAIL 非零，不 skip 不 mock；解除条件=AutoUI 修复或用户裁定边界。 | AC-01/02/05/06/07/08 |
| T-04 | review | T-08 | 独立上下文在同实现提交复演 S-01～05，核全部 work AC 与 Spec；OS 联合验收另在067进行。 | AC-03 |
| T-05 | merge | T-04 pass | 按固定版本落地与 Spec 核对，发布组件/适配清单并回填 OS M2。 | AC-04 |


## 9. 复审记录

2026-11-07 · stage: new · NOTES-006 r1 · outcome: pass（草案）· next: work T-01。新增 T-01～05、AC-01～04；实施及产品验证均待执行。

2026-11-09（二） · stage: work | plan_id: NOTES-006 | plan_revision: r1 | outcome: pass（T-03 完成）| task_ids: T-03 | evidence: tests/basic/verify_featurepack_editor.py vue 14/14 + vm 4/0/1（--profile vue|vm，自管生命周期）；组件契约实测五条（§10） | blockers: 无 | next_responsible_role: work（T-03 剩余面=READER-013 宿主集成，OS-T-03 组合验收；属 PLAN-065 协调，见 OS 计划）

2026-11-09 · stage: work | plan_id: NOTES-006 | plan_revision: r1 | outcome: pass（T-01、T-02 完成）| worktree: D:/autostack/auto-notes（独立 clone，main）| branch: main | base_commit: 16f3efb | code_commit: 见本仓 T-02 提交 | dependency_revisions: auto@0.1.0+plan-890-r7-t19；OS-T-01 契约=auto-os worktree featurepack-v0.md | task_ids: T-01、T-02 | evidence: tests/basic/verify_featurepack_service.py 39 PASS / 0 FAIL（隔离目录 + legacy 样例迁移 + 全拒绝面；python tests/basic/verify_featurepack_service.py 自管服务生命周期）；实测修订两条（.at API 无 header 通道→cred 信封字段；路径参数+query/body 混合不绑定→全 POST body 形态）已同步 OS 契约文档 | blockers: 无 | next_responsible_role: work（T-03 编辑器组件，依赖 OS-T-01 嵌入先证已具备）



2026-11-10 · stage: review/new（计划与证据审核） · review_scope: phase · reviewer_identity/limitations: 原起草会话，未执行产品测试 · plan_revision: 2 · outcome: needs_replan（r1）；本r2已分配修订任务，next: work T-06（OS067 M1接口冻结后）。AC-01/02与新增AC仍为partial/pending，不能记独立终审pass。旧任务行仅作历史记录，当前合同以§5～8为准。
> | T-02 | work | T-01、OS-T-01 接口冻结 | [x] 实现迁移及捕获/读写/按书列举/回执入口，接入现有事务门；拟建 tests/basic/verify_featurepack_service.py 验 V-01。[✅ 已完成 2026-11-09] repository.at fp 段（policy 文件凭据→(principal,operations,book_scopes) 绑定、作用域裁剪、fp_capture/fp_get/fp_list_by_book/fp_update/fp_receipt、notes 附加列 book_id/source_json——附加式 ALTER 不动 schema_v 与 legacy 升级状态机）+ db.at wire 门（unsupported_version / attempt_id）+ api.at 全 POST body 形态五端点（生成服务器不绑定「路径参数+query/body 混合」的非路径参数——实测裁定，REST 形态让位信封形态）+ /api/health 就绪探针（daemon 固定契约）。verify_featurepack_service.py **39 PASS / 0 FAIL**（F-01 旧库迁移3条含Unicode往返；F-02 捕获+来源逐字往返；F-03/04 同键重放 replayed=true/异载荷 request_conflict 无写入；F-05/06 条件更新 rev2+跨重试幂等；F-07 过期修订拒写+current_revision；F-08 并发同 revision 恰一胜；F-09 按书分页翻页+未授权书空；F-10 拒绝面五例全无写入；F-11 回执 committed/not_observed）。端点形态/凭据信封两处实测修订已同步 auto-os featurepack-v0.md。 | AC-01 |
> | T-03 | work | T-01、OS-T-01 嵌入先证、T-02 | [x] 抽取可导入组件，主应用改为第一个消费者，覆盖创建/编辑、冲突与输入恢复；拟建 tests/basic/verify_featurepack_editor.py 验双端 V-02。[✅ 已完成 2026-11-09] 组件发布 src/front/components/fp_editor.at（FpNoteEditor：双输入 mode、prop 往返草稿、save_state/conflict_revision/server_body 投影、on_draft_edit/on_submit_text/on_rebase 回调；目录包形态 components/ 先例，reader 经 dep notes-fp 消费）。主应用第一消费者：app.at FeaturePack 编辑区双实例（edit 与主编辑器同源 .draft_body 同修订 + create 独立字段）+ notes_store 宿主回调臂（I/O 内联 await 纪律；冲突保输入——宿主不写回草稿字段；Rebase 认领服务器修订）。verify_featurepack_editor.py：**vue 14 PASS / 0 FAIL**（双实例并存/创建流程/edit 同修订/迟到与另一实例互不扰/外部推进 revision→conflict 保输入+服务器版本可见/Rebase 再提交 saved/零页面错误）、**vm 4 PASS / 0 FAIL / 1 SKIP**（VM MCP 无文本注入面——在案工具缺口如实 SKIP，渲染/事件绑定/host 状态以快照核对，键入流以 vue 轨为准）。实测裁定五条见 §10。 | AC-02 |
> | T-04 | review | T-03 | 复核提交与 V-01/02 实测，重新核查两项产品断言。 | AC-03 |
> | T-05 | merge | T-04 通过 | 交付对应仓版本与规范，记录复用者可引用的提交。 | AC-04 |


2026-11-10 文档自检通过。四份计划各有0～10节；任务数依次为7/8/8/8，ID唯一、当前相对文档链接有效、限定仓归属后的任务依赖图无环，改动文件 diff --check 通过。仅记录文档检查，产品验收待work。
2026-11-12 · stage: work | plan_id: NOTES-006 | plan_revision: r2 | round: 1 | outcome: blocked（局部：VM edit 实例输入面待 AutoUI/用户裁定；其余 work 交付完成并验证） | worktree: D:/autostack/auto-notes（独立 clone，main） | branch: main | base_commit: 1aa2e72 | code_commit: 本回合作业树（见提交） | dependency_revisions: auto 0.1.0+plan-890-verified-r7-t19-20-g347c29f-dirty · auto-os main 868c80d（OS-067 M1 冻结）· auto-reader main 8f57fd9（dep notesfp 在案） | task_ids: T-02、T-03、T-06（前轮）、T-07、T-08(partial) | evidence: python tests/basic/verify_featurepack_service.py → **67 PASS / 0 FAIL / 0 SKIP**（退出码 0；F-01..11 全数保持 + S-01 重启重放 11 例 + S-02 冻结校验/半途故障自愈/incomplete 投影 17 例）；python tests/basic/verify_featurepack_editor.py --profile vue → **25 PASS / 0 FAIL / 0 SKIP**（E-0..E-6 + S-3a 保存中键入只清已提交版 + S-3b 关页重启恢复 + S-3c 丢回包→重启→pending→同 ID 重试 saved + 冲突保输入 Rebase 再提交；exit 0）；--profile vm → 12 PASS / 16 FAIL（create 链真实输入绿：type_text 中文/emoji→dirty→submit→saved→服务端逐字；edit 实例输入面=AutoUI 引擎条件子树回调缺口，§5 修订⑦/§10 在案，如实 FAIL 非 skip）；SD-01/03+三仓消费清单=docs/specs/notes/featurepack-service-and-editor.md · SD-02=durable-inbox.md 共存节 | blockers: AC-08 partial——VM edit 实例输入面待 AutoUI 引擎修复或用户裁定边界（§10 三选一） | next_responsible_role: user/AutoUI（裁定后 work 复跑 VM 轨收口）→ review（T-04）

## 10. 待澄清事项

**[2026-11-12 · work 阻塞面 → 用户/AutoUI 裁定]** VM 引擎对**条件子树内组件回调注册失效**（§5 r2 实测修订 ⑦ 最小反例：同组件无条件分支回调通、条件分支死、Vue 双活；非空初值/键控重挂均已排除）。影响面仅 VM 轨 edit 实例输入用例（M-3c/M-4 系/M-5a/M-6 如实 FAIL）；服务面、Vue 轨、VM create 链全绿。解除路径三选一：① AutoUI 修复（评估单独立项，反例已留证）；② 用户裁定 v0 验收边界=「VM 真实输入以 create 链 + 渲染/状态面为准，edit 实例输入以 Vue 轨为准」；③ 等引擎修复后复跑 `python tests/basic/verify_featurepack_editor.py --profile vm` 至全绿。未解除前 AC-08 记 partial。

跨仓组件导入与正式服务接线以 OS-T-01 的实测决定。遇到需要更改旧引擎私有接口的情形，向 AutoUI 提交最小反例并评估单独立项。首版以构建时嵌入为验收边界。

**T-01 实测补充（2026-11-09）**：OS-T-01 已裁定组件导入机制成立、无需独立 AutoUI 引擎子计划（notes Vue 9/9、notes VM 10/10）；另发现 .at API 面无 HTTP header 通道——契约的 `X-FP-Credential` 头调整为请求信封字段 `cred`（v0 单用户诚实边界下与头等价，凭据仍为 policy 绑定的服务侧裁决、body 自报身份不可信语义不变；auto-os featurepack-v0.md §2.4 相应修订）。

**T-03 实测裁定（2026-11-09，五条）**：① **组件草稿机制**：本地 model + Init 臂播种与冲突保输入互斥——Vue 端 Init 臂编译为 onMounted + props 深监听回放（任一 prop 变化重放 Init），宿主投影 save_state 必然覆写本地草稿；故 v0 草稿经 **prop 往返**承载（宿主每实例一对字段；PLAN-041 实例 model 不承载草稿——AC-02 可观察结果逐条保住，机制偏差在本节在案）。② **纯 emit 通道的 @input 提取**：组件内 msg 无 on{} 臂时，textarea `@input` 绑定裸 handler（事件对象直传宿主）；需一个**使用参数的臂**（镜像字段）使生成器产出 target.value 提取。③ **emit 事件名映射**：父监听名由 prop 派生（on_rebase→Rebase），组件内部消息名必须与派生名一致（RebaseTap≠Rebase 则回调死路）。④ **App 层转发臂必需**：组件 emit→App on 臂缺 arm 时生成 TODO 桩（静默丢事件）——每个组件回调 prop 在宿主 widget 都需对应 msg+on 臂。⑤ **引擎注意**：`pub const` 使 VM 面 db.at 解析中断（其后符号全部 undefined——fp_version_gate 链接错误假象）；组件目录**必须命名 components/** 才被 SFC 发射扫描；`.auto/ui-cache.json` 不因 back 编辑失效（改 back 后需手清）。
