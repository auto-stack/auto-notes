---
plan_id: NOTES-006
status: executing
feature_name: 共享笔记服务与可嵌入编辑器
author: [Codex]
created_at: 2026-11-07
updated_at: 2026-11-09
plan_revision: 1
current_step: 1
total_steps: 5
supersedes_spec_components: []
new_spec_components: [docs/specs/notes/featurepack-service-and-editor.md]
touched_goals: []
---

# NOTES-006 · 共享笔记服务与可嵌入编辑器

## 0. 变更摘要

将现有 Inbox 扩展为带来源的笔记服务，同时在主应用和外部宿主使用同一份轻量编辑组件。

[AutoOS 总计划](../../../auto-os/docs/plans/065-notes-featurepack-v0.md) · [Reader 宿主](../../../auto-reader/docs/plans/013-notes-featurepack-host.md)

## 1. 目标

首版交付范围见 AC-01、AC-02。动态加载、跨进程 UI、AutoLens、图片/公式、词典/AI、知识库加工以及 ACE/AGE 切换留给后续计划。

## 2. 架构方案

Notes 后台是持久笔记唯一写入者。编辑组件接收来源或 note_id、允许操作和宿主回调；每个实例持有草稿、修订号和未完成请求。主应用的列表和导航继续使用自己的 Store。

## 3. 技术栈

现有 .at API、repository、SQLite、AutoUI widget/props/emit 与双端构建。

## 4. 需求分析与背景调查

本次授权起草计划。2026-11-07 基线 16f3efb0；docs/specs/notes/durable-inbox.md、src/back/{api,repository}.at、src/front/{editor,notes_store}.at。当前 requests 与 notes 已同事务，编辑器依赖当前应用草稿。NOTES-002 的附件、NOTES-003 的知识转交仍由原计划负责。

## 5. 详细设计

捕获操作接受可信来源作用域、稳定操作 ID、不可变来源快照（书 ID、版本、作者、原句、可选章节和版本化定位数据）、可编辑正文。返回 note_id、revision 与提交回执。支持读取、按书分页、按 expected_revision 更新和查询回执。Notes 主应用按登录用户查询，Reader 的读写操作按系统授予的书籍范围校验。正文、书名、作者、来源版本均保留原始 Unicode。书键、分页游标、请求预算及保存大小上限在 T-01 对照旧库、真实 EPUB 样例和 F0/F1 边界定稿。校验来源包络，锚的语义由 Reader 负责。既有无来源便签照常使用。正文、来源关联和回执在同一事务中提交，相同主体和操作重放得到原结果；不同意图拒绝。

编辑组件接受创建/编辑两种输入，发出已保存和回访事件；两个实例可并存。按实例与来源持久暂存未提交草稿，恢复时以相同操作重试；并发修订冲突保留用户输入供重读、比较和再次提交。组件代码由 Notes 发布，复用构建方式由系统 T-01 探针确定。

### 规范增量

| delta_id | add/modify/retire | docs/specs/... target | before/after rule | rationale | acceptance IDs |
|---|---|---|---|---|---|
| SD-01 | add | docs/specs/notes/featurepack-service-and-editor.md | 从现有单应用或探针边界扩展为第 2、5 节的产品契约 | 固定真实宿主行为与数据归属 | AC-01/02 |

## 6. 测试设计

V-01 / AC-01：对隔离旧库取升级前后快照，实际 API 重放、改正文重放和并发更新，核笔记/来源/回执及 revision。V-02 / AC-02：两个实例编辑不同笔记，再编辑同一旧修订；关闭其中一个，用中文输入、重开并核草稿与服务端最终文本。

上述为拟验用例，owner_stage 为 work。第 8 节所列新脚本由对应任务建立，约定从本仓根运行 `python <脚本路径>`，默认使用隔离目录，双端用例分别记录 Vue 与 VM 结果，断言失败或缺少必需用例返回非零。最终复审复演风险用例，记录所用提交和实测结果。

## 7. 验收标准

| ID | owner_stage | 可观察结果 |
|---|---|---|
| AC-01 | work | 旧库升级后普通便签仍可读写；提交后丢回包并重启，相同操作仅生成一条笔记；变更意图或过期修订拒写，原内容和回执可读。 |
| AC-02 | work | 同一组件在双端可嵌入，主应用与宿主看到同一修订；关闭一个实例或收到迟到回包不改变另一个实例草稿，冲突输入可恢复。 |
| AC-03 | review | 在同一实现版本独立复演 V-01/02，证据绑定应用、引擎和服务版本。 |
| AC-04 | merge | 按评审版本交付，核对 SD-01 与实测边界，归档回执。 |

## 8. 执行步骤

拟实施位置 D:/autostack/auto-notes 独立 clone，main。从 T-01 开始，work 核实实际基线。跨仓依赖按具体交付任务推进，OS 汇总验收位于两子计划之后。

| ID | owner_stage | 依赖 | 工作与验证 | 验收 |
|---|---|---|---|---|
| T-01 | work | 无 | [x] 在 src/back/repository.at、src/front/editor.at 盘点迁移与实例依赖，提供旧库、重复请求和双实例样例，与系统 T-01 对齐。[✅ 已完成] 盘点结论：迁移依赖点=ensure_schema 幂等 ALTER 惯用法 + upgrade_if_legacy/repair_legacy_merge 状态机（schema_v=3 不动，fp 列附加式不改状态机）+ migrate_request_intents（v2c| 门不受扰）；实例依赖点=requests 表（request_id PK）复用为 fp 去重键 `fp:<principal>:<operation_id>`、replay_in_txn 规范化意图复用、BEGIN IMMEDIATE 单写者门同律。样例：旧库=tests/fixtures/inbox/legacy-v0/notes-valid.json（既有，3 条含中文/emoji）；重复请求=verify_featurepack_service.py F-03/F-04/F-06（同键重放/异载荷冲突/更新重试幂等）；双实例样例归 T-03 编辑器面（两实例并发编辑不同笔记 + 同旧修订冲突，见 §6 V-02）。OS-T-01 对齐：notes.fpack/1 版本串、凭据→policy 绑定、operation_id 去重、attempt 与 operation 分离（auto-os worktree featurepack-v0.md §2/§3）。 | AC-01/02 |
| T-02 | work | T-01、OS-T-01 接口冻结 | [x] 实现迁移及捕获/读写/按书列举/回执入口，接入现有事务门；拟建 tests/basic/verify_featurepack_service.py 验 V-01。[✅ 已完成 2026-11-09] repository.at fp 段（policy 文件凭据→(principal,operations,book_scopes) 绑定、作用域裁剪、fp_capture/fp_get/fp_list_by_book/fp_update/fp_receipt、notes 附加列 book_id/source_json——附加式 ALTER 不动 schema_v 与 legacy 升级状态机）+ db.at wire 门（unsupported_version / attempt_id）+ api.at 全 POST body 形态五端点（生成服务器不绑定「路径参数+query/body 混合」的非路径参数——实测裁定，REST 形态让位信封形态）+ /api/health 就绪探针（daemon 固定契约）。verify_featurepack_service.py **39 PASS / 0 FAIL**（F-01 旧库迁移3条含Unicode往返；F-02 捕获+来源逐字往返；F-03/04 同键重放 replayed=true/异载荷 request_conflict 无写入；F-05/06 条件更新 rev2+跨重试幂等；F-07 过期修订拒写+current_revision；F-08 并发同 revision 恰一胜；F-09 按书分页翻页+未授权书空；F-10 拒绝面五例全无写入；F-11 回执 committed/not_observed）。端点形态/凭据信封两处实测修订已同步 auto-os featurepack-v0.md。 | AC-01 |
| T-03 | work | T-01、OS-T-01 嵌入先证、T-02 | 抽取可导入组件，主应用改为第一个消费者，覆盖创建/编辑、冲突与输入恢复；拟建 tests/basic/verify_featurepack_editor.py 验双端 V-02。 | AC-02 |
| T-04 | review | T-03 | 复核提交与 V-01/02 实测，重新核查两项产品断言。 | AC-03 |
| T-05 | merge | T-04 通过 | 交付对应仓版本与规范，记录复用者可引用的提交。 | AC-04 |

## 9. 复审记录

2026-11-07 · stage: new · NOTES-006 r1 · outcome: pass（草案）· next: work T-01。新增 T-01～05、AC-01～04；实施及产品验证均待执行。

2026-11-09 · stage: work | plan_id: NOTES-006 | plan_revision: r1 | outcome: pass（T-01、T-02 完成）| worktree: D:/autostack/auto-notes（独立 clone，main）| branch: main | base_commit: 16f3efb | code_commit: 见本仓 T-02 提交 | dependency_revisions: auto@0.1.0+plan-890-r7-t19；OS-T-01 契约=auto-os worktree featurepack-v0.md | task_ids: T-01、T-02 | evidence: tests/basic/verify_featurepack_service.py 39 PASS / 0 FAIL（隔离目录 + legacy 样例迁移 + 全拒绝面；python tests/basic/verify_featurepack_service.py 自管服务生命周期）；实测修订两条（.at API 无 header 通道→cred 信封字段；路径参数+query/body 混合不绑定→全 POST body 形态）已同步 OS 契约文档 | blockers: 无 | next_responsible_role: work（T-03 编辑器组件，依赖 OS-T-01 嵌入先证已具备）

## 10. 待澄清事项

跨仓组件导入与正式服务接线以 OS-T-01 的实测决定。遇到需要更改旧引擎私有接口的情形，向 AutoUI 提交最小反例并评估单独立项。首版以构建时嵌入为验收边界。

**T-01 实测补充（2026-11-09）**：OS-T-01 已裁定组件导入机制成立、无需独立 AutoUI 引擎子计划（notes Vue 9/9、notes VM 10/10）；另发现 .at API 面无 HTTP header 通道——契约的 `X-FP-Credential` 头调整为请求信封字段 `cred`（v0 单用户诚实边界下与头等价，凭据仍为 policy 绑定的服务侧裁决、body 自报身份不可信语义不变；auto-os featurepack-v0.md §2.4 相应修订）。
