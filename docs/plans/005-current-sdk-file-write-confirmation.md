---
plan_id: NOTES-005
status: reviewed
feature_name: 当前SDK文件写入确认兼容
author: [Codex]
created_at: 2026-11-06
updated_at: 2026-11-06
plan_revision: 2
current_step: 3
total_steps: 4
base_branch: main
base_commit: 38c7c8703a2f9fd4558684d5b80ee2765fedc040
supersedes_spec_components: [docs/specs/notes/durable-inbox.md]
new_spec_components: []
touched_goals: []
---

# NOTES-005：当前 SDK 文件写入确认兼容

## 0. 变更摘要

auto-os/PLAN-054 正式当前 SDK Rust 构建发现旧 `fs.write_text` 布尔用法与现行整数返回不匹配。保留应用的布尔确认边界，以目标为普通文件且全文读回一致确认所需状态；不改变标准库、公共API或存储格式。

## 1. 目标

- G1：当前固定 SDK 下正式 Rust 生成编译成功，既有用户任务成立。
- G2：写入拒绝/缺父目录/目录冒充文件时不得把旧或缺失内容确认成功。
- G3：一个已存在的辅助写函数；SQLite事务/收据协议不变。

## 2. 架构方案

唯一实施/复审目录 D:/autostack/auto-notes，独立真实clone/main（按用户2026-10-29应用规约覆盖通用技能的框架worktree惯例）。不在auto-os/apps内编辑；已知src/front临时未跟踪目录保留。实现函数 `fs_write` 使用现有 fs 写入、目录判断、存在与全文读取，不以状态码真假猜测。目标为目录先拒绝。既有相同普通文件内容可被再次确认；true不证明本次发生物理写入。失败的不同内容请求必须false并保留旧内容。

## 3. 技术栈

现有.at与fs；永久Python测试提取实际函数，用已选CLI执行真实VM/文件系统；正式原生生成编译与父054实机/网页消费验证。无新库。

## 4. 需求分析与背景调查

继承用户“解决问题并最终完成054”及独立复审授权；这是原8应用/双端任务所必需的兼容前置，无新功能、预算或支持收窄。基线38c7c8703a2f9fd4558684d5b80ee2765fedc040；Langf03226e10、UIa1db3d79、Man2a9b16e、OS5e186935，冻结SDK176。正式失败：Notes E0308 bool/i64；Calendar当前源码九个布尔调用，正式构建10个类型错误。读过docs/specs/notes/durable-inbox.md与Lang956字节/文件SDK实现；VM底层写入返回码也不能独立证明成功，因此须读回确认。原日志位于父唯一scratch D:/autostack/plan-artifacts/plan-054/t07；本子计划使用同一具名子目录，不复制到另一证据根。

## 5. 详细设计

T00定位已观察的真实调用与失败；T01完成 `fs_write` 及同因调用收口。调用参数单次传递，先拒绝目录，写入后检查存在并全文比对；不新增状态全局变量。永久测试实际提取生产函数，fixture和输出仅在显式仓外scratch。

### 规范增量

| delta_id | add/modify/retire | docs/specs/... target | before/after rule | rationale | AC |
|---|---|---|---|---|---|
| SD01 | modify | docs/specs/notes/durable-inbox.md | 保留原存储合同，补辅助文件写入按普通文件及全文读回确认；不承诺物理写次数 | 现行SDK整数返回与VM错误码不足以单独确认内容 | AC01/02 |

拟落地段落：辅助文件写入确认不依赖 `fs.write_text` 返回值真假；目录拒绝，普通文件存在且全文读回一致才返回true；目标为空时另须实际文件字节长度为0，避免文本读取失败默认空串造成误判。已存在相同内容允许幂等确认。SQLite事务/Calendar身份水位与删除协议不因此改变。

## 6. 测试设计

实施本会话；独立上下文在同一clone复审，沿用户已授权054独立复审前置；无实现委派。work做定向红绿/生成编译；父054共同SDK实机任务为必要集成，review可明确冻结其merge-owned执行点；无整仓cargo测试。

| case | owner/AC | 实际入口/输入 | 观察判据与边界 |
|---|---|---|---|
| V01 | work/AC01 | 正式auto build -r rust；生产fs_write | 旧版本已红，新版编译0；不得复用旧exe |
| V02 | work/AC02 | tests/sdk_file_write.py，提取生产函数→实际VM：中文多行创建/覆盖、空普通文件、缺父目录、目录+空内容、只读不同内容、已有相同内容 | 真bool结果与实际文件全文/旧数据一致；只读不同内容false且原件SHA不变；目录不能因空读默认值误绿 |
| V03 | merge/AC03 | 父054公开Vue/iced入口受影响真实任务 | Notes保存重开/辅助文件确认，Calendar增改删重开与恢复身份文件一致；最终共同SDK与pin具名绑定 |

## 7. 验收标准

- AC01 owner_stage=work：当前SDK正式Rust构建成功，实际源/生成/产物身份一致。
- AC02 owner_stage=work：V02实际执行，各有效/错误控制符合确认合同，无数据格式或API变更。
- AC03 owner_stage=merge：独立pass、规范落地、父054新SDK实际消费成功、main提交push、归档回执完整；所有未达项保持pending。

## 8. 执行步骤

- [x] T00 owner_stage=work：复核失败/生产路径/现行SDK，确认有界方案。
- [x] T01 owner_stage=work：实现兼容与永久V02，正式生成编译V01，提交工作完成。
- [x] T02 owner_stage=review：同一clone独立上下文复审当前源/Spec提案及结果。
- [ ] T03 owner_stage=merge：规范、父集成、提交push与归档；保留永久开发clone。

## 9. 复审记录

- stage:new | revision:r1 | outcome:pass | next:work/T00；父054授权覆盖原目标必要修复，禁止借本计划升级无关依赖或改应用功能。当前仅合同登记，未实施。

## 10. 待澄清事项

无新用户语义决定。独立复审、正式编译与父实际消费均未完成；不以新计划登记冒称已修复。


- stage:work | revision:r1 | round:1 | outcome:T00 complete/T01 in progress
  Source/repository/clone main ownership checked, pre-existing front tmp/tests directories preserved. Notes formal native E0308 and Calendar formal10 type errors reproduced with SDK176. Notes permanent extraction test on original helper actually returned seven numeric0 values instead of required Bool values (exit1), exposing the VM return-code ambiguity too. This is not a compile-only fix: full-content confirmation and directory-empty control close the common cause. All9 Calendar original call sites route through one helper; only its primitive call remains. New permanent production-helper execution is pending green; no execution_done or app pin upgrade.


### T03 跨仓整合的阶段顺序（有界合同澄清）

用户应用规约要求独立clone/main开发、提交验证push后再更新AutoOS组合。此计划源码已在main开发；独立review通过当前代码/规范提案与work全部AC后，先推送具名“已审源码阶段”供父054候选组合验证。该动作不代表本计划已归档或最终交付pass。父候选只消费已提交/push/独立审核的源码，正式AutoOS gitlink交付仍等父验收关闭。随后完成本计划要求的父新SDK实际任务、规范落地、最终文档提交push与归档；最终Doc后继须证明src/pac与已测源码完全相等。所有AC/实际任务及原协议不变，未完成项不被转为pass。此顺序解决“应用先可获取、组合才可验证”的源发布依赖，不删减或转移任何既定验收。

- stage:work | revision:r2 | round:4 | outcome:execution_done2/4 | code_commit:64f1647ea8cf85eaa48bb9809e9edd4a827b0686 | next: independent source/Spec review
  Actual currentSDK formal native build and scoped checks: r179 exit0/189.0s; VM7/7 + actual generated Rust write4/4. SDK CLI84ffcd0782475f4a9f77ac626042c7a1354b23270930b985531f74212602425b / UItool56e50b44b3ff33c44a7fd61c1860e0fefeaa0efe7dd55fd6d1e7c9cf60382ea7, selected Langf032/UIa1db/Man2a9/OS5e18. Published artifact hash, generation inputs and exact current core dependency were checked for the actual generated-Rust execution; no copied implementation, stale binary or GUI/OS input synthesis. Unknown untracked front tmp/tests remain untouched; Notes formal receipt has no untracked src input.
  Legacy generated GPU lock reconciliation is configuration only: cargo offline recursive update of allocator changes only its windows0.57→0.58 edge (no package version changes), identical to SDK. Before locks/logs retained; failed old-lock builds explicitly not counted. Scope ordinary app data files/directories, not arbitrary device/IPC resources. Existing unrelated application/UI/schema mechanisms remain unchanged; parent current-SDK actual tasks and final closeout still pending.
  Native evidence: D:/autostack/plan-artifacts/plan-054/t07/generated-file-confirm-r178.json SHA256 768fda79093f9a13bb559a556215814dd08309fa3605855318c51fadc9052a96.
  Native evidence: D:/autostack/plan-artifacts/plan-054/t07/generated-delete-confirm-r184.json SHA256 dc0b4d9fd5b0aef1eba8c7f2e80fa856d62de30d7ab8a6187138d60ae59ea5b5.


### Independent source / Spec review — 2026-11-06

- stage: review | review_scope: final | reviewer_identity: delegated independent Codex context /root/review_app_sdk (no implementation performed; model identity not exposed) | plan_revision: 2 | outcome: needs_fix
- worktree_path: D:/autostack/auto-notes | branch: main | reviewed_commit: 43d3cf9fd56cd2f3c7c0e0a3b6e319eb15e0c8cc | base_commit: 38c7c8703a2f9fd4558684d5b80ee2765fedc040. Existing real clone and single worktree verified with `git worktree list --porcelain`; user app-main rule governs. Implementation writes paused; tracked source clean at entry and verdict. Foreign untracked directories retained. Review skill and verification-contract read in full.
- dependency_revisions: Lang f03226e10 / UI a1db3d79 / Man 2a9b16e / OS 5e186935; SDK frozen-sdk-r176 CLI SHA256 84ffcd0782475f4a9f77ac626042c7a1354b23270930b985531f74212602425b.
- spec_inputs SHA256: 72bf06169f52c7250fcf5c9d3289ec1fd5b2dcac120b827aba5cd57717fad3f3; frozen proposed `### 规范增量` text SHA256: c2360cf065ce1e01d95feb9d950a6d7b0680fb4b417497e2c06cf34abe82ac78. Canonical Specs and legacy ledger untouched. `touched_goals: []` is appropriate: this is existing goal compatibility, no new goal identity.
- acceptance_results: AC01 pass — reuse formal native build r179 (Notes, exit0/189s) or r182 (Calendar, exit0/44.46s); independently matched generation.json pac/src input hashes to current files and published executable hashes to receipts. AC02 fail — original permanent VM write7/7 independently replayed exit0 with exact Bool and file assertions, but holdout F-SDK-EMPTY-01 below fails. Calendar delete5/5 independently replayed exit0 including real locked handle; original tombstone → all versions delete → manifest ordering remains unchanged. AC03 pending merge-owned, not claimed complete.
- source/provenance: complete baseline→HEAD source diff inspected; Notes only fs_write, Calendar all nine writes and one deletion predicate share helpers. No API/schema/SQLite/watermark/tombstone changes. Native generated helper evidence source extraction, current Cargo fingerprint→core RLIB linkage, published hash, ordinary-file controls inspected: generated-file-confirm-r178.json SHA256 768fda79093f9a13bb559a556215814dd08309fa3605855318c51fadc9052a96 (8 controls); generated-delete-confirm-r184.json SHA256 dc0b4d9fd5b0aef1eba8c7f2e80fa856d62de30d7ab8a6187138d60ae59ea5b5 (4 controls). GPU reconciliation changes only existing allocator windows dependency edge 0.57→0.58; no package version upgrade. No Cargo/global suite repeated.
- F-SDK-EMPTY-01 | P1 | AC02/T01 | existing rule failure: rejected different-content write must return false and old bytes survive. Setup a normal file containing bytes `ff fe 80`, mark readonly, invoke actual production write helper with empty string through frozen SDK real VM. Expected false + original bytes; observed true + original bytes `fffe80` in both Notes and Calendar, exit0. This is a regular file and a supported empty-content request, not a device, symlink or physical-write-count claim. Root cause: read failure falls back to empty string (`auto-lang-core/src/a2r_std.rs` fs::read_text uses read_to_string(...).unwrap_or_default()), so equality with empty desired text cannot prove successful full read. Runtime VM reproduces the ambiguity too. The directory guard closes only another empty-default path.
- minimal replay: run frozen-sdk-r176/auto.exe against the matching probe.at referenced in D:/autostack/plan-artifacts/plan-054/t07/review-app-sdk/invalid-utf8-review.json, with its readonly fixture re-established (otherwise the write can succeed). Receipt SHA256 3fee4497a43a26f6bbed5234bdcd1e8cc759f2c22e90a1ba3afb87778bbd559e; durable setup/expected/observed above permits recreation after scratch removal. Independent regular UTF-8 create/overwrite/empty, missing parent, directory, readonly different-text and readonly same-text controls all pass; retain them.
- closing oracle: permanent source-extracted test covers readonly non-UTF8 old bytes + empty desired content, false plus old-byte preservation, with existing legitimate empty-file and idempotent controls retained; independently verify affected VM/native confirmation behavior using actual supported SDK facilities. This receipt does not prescribe an unverified fix or require framework changes. SD01 proposal states the right enduring contract but implementation does not yet satisfy its full-content claim; source/Spec approval withheld.
- pending_closeout_gates: T03 parent054 common-SDK actual Vue/iced tasks, canonical Spec landing, source-bound final doc successor, push/pin and archive all remain pending. T03 ordering is explicit and self-consistent: after successful independent source/Spec review, publish named reviewed-source stage for candidate fetch, then actual parent tasks and final Spec/docs/push/archive. It grants no final delivery pass and does not waive any AC. This needs_fix prevents the source-stage publication until repaired/re-reviewed.
- next: work in the same clone, close F-SDK-EMPTY-01 with targeted checks, commit repair then independent affected re-review. T01 reopened; T00 retained; current_step=1/4.


- stage: work | revision:r2 | round:186 | outcome: execution_done2/4 | code_commit:317a847f24eafd07e40fc9d5afc9efb1d6a402bd | finding:F-SDK-EMPTY-01 repaired | next: independent affected re-review
  Permanent source-extracted V02 now has10 actual VM controls per application. Exact review counterexample bytes ff fe 80 + readonly + requested empty text reproduced before repair: true rather than expected false, exit1 of the strengthened Notes regression (t07/notes-write-red-r186.log). Both helpers now require fs.file_size(p)==0 for empty desired text in addition to existing directory/existence/full readback checks. Verified actual SDK VM alias fs.file_size→auto.fs.size and actual probe3bytes; generated Rust facade uses metadata.len. No inferred write-status coercion or framework change. This closes the ordinary-file non-UTF8 fallback ambiguity without rejecting writable non-UTF8 files successfully truncated to empty or legitimate readonly empty files/idempotence.
  Both actual VM10/10 pass with true Bool values, readonly ff fe 80 unchanged, writable invalid bytes become exactly0bytes, readonly legitimate empty remains empty. All original7 controls retained. Formal regenerated currentSDK176 native builds: Notes exit0/86.33s, Calendar exit0/44.19s, frozen source commits above; source did not change during generation/build. Actual emitted Rust helpers extracted from matching source-bound generation receipts, published exe hashes rechecked, exact Cargo fingerprint core dependency linked:14/14 real-file controls pass, including the same three new cases per app. D:/autostack/plan-artifacts/plan-054/t07/generated-file-confirm-r186.json SHA2560d7bf8c28b56b6d2b1efaf9e4d9f3ed42f60f6cd5b16cd2bbef5a5492f5ccde8. Old evidence/review failure retained, not relabelled green. No changes to Calendar deletion helper/order, Notes SQLite, API/schema or foreign WIP. T02 and all T03 final consumer/spec/push/archive gates pending; no final delivery claim.


### Independent affected re-review — F-SDK-EMPTY-01 closure

- stage: review | review_scope: final (affected repair; earlier unaffected checks retained) | reviewer_identity: independent Codex context /root/review_app_sdk, no implementation edits | plan_revision: 2 | outcome: pass | worktree_path: D:/autostack/auto-notes | branch: main | reviewed_commit: 1f57836bcf90771c7bc77058673907961c8021e2 | source_commit: 317a847f24eafd07e40fc9d5afc9efb1d6a402bd | base_commit: 38c7c8703a2f9fd4558684d5b80ee2765fedc040. Frozen HEAD and clean tracked implementation confirmed; foreign untracked WIP retained.
- dependency_revisions: unchanged Lang f03226e10 / UI a1db3d79 / Man 2a9b16e / OS 5e186935, SDK176 CLI SHA256 84ffcd0782475f4a9f77ac626042c7a1354b23270930b985531f74212602425b. Relevant Spec docs/specs/notes/durable-inbox.md SHA256 72bf06169f52c7250fcf5c9d3289ec1fd5b2dcac120b827aba5cd57717fad3f3; current proposed SD01 block SHA256 40da52af0a53c442729040fec18dcdf296f7f8ee376956827b8d874ed4c5c90b. No canonical Spec or legacy-ledger write.
- finding closure: F-SDK-EMPTY-01 closed for the agreed ordinary-file scope. Actual source diff adds only empty-desired-content byte-size guard; native metadata failure returns -1, therefore the guard rejects unavailable size. VM file_size alias maps to auto.fs.size. Empty-string read-error fallback can no longer confirm a nonempty readonly file. Full readback still checks nonempty content; directory/existence guards remain. No data schema/API/protocol or Calendar deletion changes. SD01 explicitly requires zero actual byte length for empty desired text; this clarifies the same pre-existing confirmation invariant, not a new support reduction.
- acceptance_results: AC01 pass via actual regenerated formal native r186 (Notes exit0/86.33s, Calendar exit0/44.19s), source-bound generation pac/src input hashes and published executable hashes independently rechecked. AC02 pass: independently executed `python tests/sdk_file_write.py --auto D:/autostack/plan-artifacts/plan-054/t04/frozen-sdk-r176/auto.exe --scratch D:/autostack/plan-artifacts/plan-054/t07/review-app-sdk` → exit0, 10/10 true Bool assertions. Original counterexample setup now false with exact fffe80 preserved; writable fffe80→empty succeeds with zero bytes; readonly legitimate empty remains true/zero bytes. All seven prior positive/negative controls retained. Permanent regression red-before-repair receipt inspected (Notes strengthened test exit1, only old invalid-readonly empty case wrong). Unchanged deletion/source/protocol evidence from first review retained.
- independent native replay: matched emitted helper hash to current generated source and helper.rs, reset actual seven fixture files/readonly attributes and reran existing helper.exe; each app returns [true,false,false,false,false,true,true], old readonly bytes preserved, writable invalid bytes truncated, legitimate readonly empty accepted. Reused valid formal/harness source→Cargo fingerprint→core RLIB binding from before concurrent parent builds, not a fabricated current-cache claim. At review first identity check the old core hash matched; concurrent legitimate parent C2 builds later made that RLIB unavailable, while the source-bound published artifacts and already-built helper executables remain verifiable and replayable. No Cargo, target mutation or full-group repetition by review.
- evidence: D:/autostack/plan-artifacts/plan-054/t07/generated-file-confirm-r186.json SHA256 0d7bf8c28b56b6d2b1efaf9e4d9f3ed42f60f6cd5b16cd2bbef5a5492f5ccde8; independent native replay review-app-sdk/native-r186-replay.json SHA256 b392c9ecab12d9f27b19b99c2867ea268a41b3ea4b1d937a626b80aaa4df1201; independent VM result review-app-sdk/confirmed-file-rr0jmdxl/result.json. Durable expected/actual values above survive scratch deletion.
- pending_closeout_gates: AC03/T03 parent054 actual common-SDK Vue/iced application tasks, canonical Spec landing, named reviewed-source push/candidate fetch, final source-equivalent doc successor, final push/pin/archive remain merge-owned pending. Source-stage ordering remains explicit/self-consistent and is now eligible on this reviewed baseline; no child final-delivery pass, push, pin or archive by this reviewer.
- next: merge owner can publish named reviewed-source stage, then complete all parent task and final closeout gates. T01/T02 complete, state reviewed/current_step3/4; historical failure retained, not relabelled green. Todo earlier source/Spec pass unchanged.


- stage:merge | checkpoint:prepared | reviewed_source_stage:bb064ca5ecdde8e39dfd3b0a9bac4e7f93902ae4 | dependency_integration:immutableSDK195 Langf032/UI9c/Webc36/Man2a9/OS39d | outcome:canonical delta prepared; publication/archive pending
  Independent final source/Spec pass retained from recorded review; this successor changes only approved canonical documentation and Plan bookkeeping. Parent054 actual SDK195 Vue/iced both8required8pass0fail, all6nativev15 formally rebuilt/18artifactbindings/67inputhashes. Current task/reopen/next native andVue independent receipts are in D:/autostack/plan-artifacts/plan-054/t04; native notes oracle and canonical-vue-notes-oracle-r195.json bind full current consumer behavior. Notes id9rev3 fullChinese, Calendar ev4delete/allversionsabsent/reopen/generationg-new/rev11→12/ev5next/oldev3exact, Todo id1edit/done1/reopen/nextedit, Blog workw-1793988759935-1fulltitle/multiline/reopen/nextSave/current+revision8; relevant app behavior is verified, not substituted by API prewrite. Blog oldnativework titles remain complete; sourcephase unchanged.
  Parent permanentpacket gates: icedSHA cd232e671e0aa7a3c1e0637a5a98e055eb9343345756faf231ca442e1e2cc042; VueSHA 9c91aadc95570bc78e24251bfa44939b99b7c12fed25cd096de55360eb09db1d. Each current validator actual8/8exit0; Vue description-only metadata corrected from copied194label without changingcases/SDK/data/frames. Work source tree 7dc6f336a81a1060aac95ce7af31b69cd4b81f3a / pacblob 48668e619a7519bf242d73b6801b587db36eb87e frozen for final Doc descendant check. No wholecatalog rerun. Canonical delta matches reviewed proposal; Todo no-impact Spec conclusion retained because privatecleanup result annotation only and all6callers ignore result.
  Permanent independent app clone is retained per user policy. Foreign untracked WIP is untouched. Shared raw evidence remains protected by active parent054 for its finalreview, not a separate archived-child raw scope or indefinite hold. Final push/archive and parentfinalpin are not yet claimed.
