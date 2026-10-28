# NOTES-001 修订8再次复审（2026-10-15）

结论：**needs_fix**。检查提交 `27cff918c5f9e9d14278adadbd76376c9f786f9e`（实现 `166a666`，diff base `1391bd7`），同一独立 Notes 仓 `D:/autostack/auto-notes` / `main`。本会话是前次审查者，未参与本轮修复，无子 agent。本次只审查并记录，不修改产品实现或 canonical Spec。

## 基线与运行范围

[baseline.json](baseline.json) 记录完整提交、工作区、依赖、CLI/源码指纹；[输入计划](plan-input-r8.md) 和[冻结的 Spec 提案](spec-delta-reviewed-r8.md) 保留入口内容。当前实现已经提交，入口只有预存未跟踪 `src/front/tests/`，保留不动。没有创建或迁移 worktree，也没有在 AutoOS 副本修改。

使用现有 CLI（`e849e06f9-dirty`，SHA256 `6e30c87f5c3eca157973ff6e2d6e8da9ddc850b4a276e7579244f0000f3524c5`）重新生成并构建。CLI dirty 源构成未被证明，未冒称 CLI 来自 AutoLang 当前 HEAD。后端编译开始时 AutoLang 为 `b2c77fa70`，审查期间前进的差异只有计划文档；实际源和制品指纹见 baseline。生成代码警告原样保存，不宣称零警告。

所有服务使用独立临时库、动态端口；UI 是真实 Chromium/HTTP，存储失败是 SQLite trigger 的 `RAISE(ABORT)` 合成拒绝，不是物理掉电。实际调用测试有失败传播和成功对照。此次已确定原合同缺陷，未再执行 VM 套件；work 的 VM 19/19、r7 VM 11/11 为历史修复采证，**不是本轮当前依赖的 VM 复验通过**。受影响双端检查仍须在修复后重跑。

## 前次发现的闭合情况

| 前次发现 | 本轮实测 | 当前结论 |
|---|---|---|
| F-R8-01 元数据/删除必需 UPDATE 假成功 | 原 `api-extra.py` pin/tags/state 三拒绝全部转绿；scratch U11 正常/拒绝/恢复通过 | 后端旧例关闭；UI pin/tags 的错误接收仍不成立，见 F-R9-01/02 |
| F-R8-02 fresh 升级完成标记失败仍提交 | 原 fresh 反例转绿；本轮额外分别拒绝 upgraded / upgrade_error / corrupted_r1，均回滚并可成功重试 | fresh 出口闭合；新增修复的 no-legacy 收尾出口不具备同一原子性，见 F-R9-03 |
| F-R8-03 SelectNote 旧下标覆盖 | 原 navigation.cjs：零错误、合法索引，B 两次保存均落地 | **该反例及其当前修复闭合，T-31 保留完成**；标签失败后的版本问题是另一条组合路径 |
| F-R8-04 证据链接/规范绑定 | r7 README 从12个失效链接修到11个可解析，尚余1个新引用缺少 `../`；新提案覆盖严格JSON边界，但错误接收/可重试声明与当前实现不符 | partial；保留原发现打开，由 T-33 关闭 |

## 本轮发现

### F-R9-01 / P1：Option 型 pin/tag 失败变成 HTTP 404，新增提示分支不会执行

类型：原 F-R8-01 的端到端修复缺口；不是新产品需求。影响 T-04/T-09/T-15 以及依赖验证任务，AC-05、SD-03/05。

`notes_store.at:1264–1265`、`:1824–1825`、`:1945–1946` 期望 `toggle_pin` / `update_tags` 返回 None，再置 `action_error`。实际后端用 `?Note` 的 None 返回 HTTP 404；本轮新生成的 API 客户端在非2xx处直接抛出 `Error("HTTP 404")`，根本不会返回 null。`pn == None` / `tn == None` 判断到不了。

实测：新建 clean 笔记，只拒绝 pinned UPDATE，再点 Pin。确实发出 PATCH，页面捕获 `HTTP 404`，`conflict=false`、`action_error=""`、错误横幅0个，服务器 pinned=false。移除 trigger 后同按钮正常置顶成功。标签入口的相同异常也已实跑，见下一项。

R8-2 的置顶断言还有假绿：前面的删除失败已经令 conflict=true / action_error=delete；紧接着点击 Pin，handler 的 `if .conflict == false` 门禁直接跳过调用。独立重放记录 **新增 PATCH 数量0**，旧 delete 横幅仍在，所以“横幅可见 + pinned未变”会通过而根本没执行 pin 故障。不能用该断言宣称真实 pin 失败链路通过。

纠正方向：让 `.at` API/adapter 与失败信封/异常协议一致，使请求失败有可见且正确的动作状态，保留草稿和重试能力；不要手改生成 TypeScript/Rust。永久测试必须独立建立每个动作前置状态，并断言实际发出了请求、收到了预期拒绝、提示对应当前动作，再验证恢复后的成功控制。

### F-R9-02 / P1：正文 flush 已提交，随后标签失败会留下旧 revision

类型：原 T-15“成功 flush 刷新 revision”未闭合；新的错误出口仍暴露旧问题。影响 T-04/T-09/T-15、AC-04/05、SD-05/10。

`notes_store.at:1804–1812` 在 TagAdded 的正文 flush 成功后清 dirty、rid、pending 链，却不更新 `draft_revision`。它依靠后面 update_tags 成功后刷新 notes/LoadDraft 才更新 revision；标签一旦失败/抛异常，这步不发生。TagRemoved 也使用同类结构（`:1930` 起），此次实际入口为 TagAdded，没有把 TagRemoved 的源码检查冒称运行证据。

复现：新笔记 rev1 → 编辑标题 one → 点击加标签（拒绝 tags UPDATE）。正文实际已保存为 one/rev2，但 UI dirty=false、draft_revision=1、无错误提示。去掉拒绝条件，再编辑标题 two 并点击 Save：携带 rev1，返回 revision_conflict；服务器仍 one/rev2，草稿 two 留在 dirty/conflict。没有外部写者，属于自身版本冲突。相同操作不注入标签失败的成功控制，随后保存 two/rev3 正常。

纠正方向：正文成功确认后立即同步当前草稿的确认版本和意图上下文；元数据失败不能撤销已发生的正文确认，也不能使后续编辑携带旧 revision。增加 dirty+元数据拒绝+重试/再次保存的 Vue/VM 断言，覆盖 tag add/remove 与同类动作。未观察到用户正文被覆盖或凭空消失，不把保留的 dirty 草稿称作数据丢失。

### F-R9-03 / P2：no-legacy 修复收尾未放在事务里，失败后凭据已删除

类型：F-R8-02 兄弟出口及其新增实现的合同缺口。影响 T-12/T-17、AC-01/03 的恢复完成/重试部分、SD-07/12/24。

`repository.at:410–415` 先 DELETE corrupted_r1，再 INSERT repair_generation；只检查返回值，没有 BEGIN/ROLLBACK。在 `upgraded=1`、`corrupted_r1="legacy upgrade incomplete"`、manifest不存在的明确前置下，仅拒绝代际 INSERT：凭据 DELETE 已提交，代际不存在；去掉 trigger 后再次读取，因为凭据不在而直接返回，再也不补代际。普通无拒绝控制则正确清凭据并记 generation=1。

本轮早期探针未设置 upgraded=1，会先走另一条新库出口而产生无效绿；已修正测试前置并重跑，最终报告和 raw 记录只取明确进入目标路径的那一轮。此处未证明笔记正文丢失，证明的是合同承诺的“失败回滚、保留重试条件”不成立。提案中的“部分清理可重试”与实际不可重试状态不符，不能作为关闭依据。

纠正方向：对清凭据与写代际使用同一写者事务/恢复协议，任一必需写入失败保持可重试，恢复后真正完成；以独立拒绝每条必需写入及正常控制验证。

### 原 F-R8-04 / P2：关闭材料仍不完整

`docs/plans/evidence/001-r7-work/README.md` 的 `001-r8-work-20261014/vue-suite.txt` 仍相对于 r7 子目录解析，实际应指向兄弟目录。其余11个链接本轮解析成功。工作计划 §7/§8/§10 还把旧 needs_fix 23/35称作“当前”，和入口35/35申报同时存在；本轮已加新的权威结论，不抹去历史。新规范提案的 UI错误接收和 no-legacy 可重试仍失败，发布必须等待实现及复审。

## 本轮验证与 AC 映射

| 验证 | 结果 | 证据 |
|---|---|---|
| fresh Vue gen / backend build | exit0 / exit0 | [生成](build-vue.txt)、[编译](build-backend.txt) |
| 原 api-extra | 4 PASS，exit0 | [结果](old-api-results.json)、[日志](old-api.txt) |
| 原 navigation | pass=true，exit0 | [结果](old-navigation-result.json)、[日志](old-navigation.txt) |
| 新 API sibling/failure controls | fresh三种拒绝+重试6 PASS；no-legacy 2 FAIL +正常控制 PASS | [结果](new-api-results.json)、[日志](new-api.txt) |
| 新真实 Vue 路径与成功控制 | pin提示、dirty-tag后续保存、R8-2掩盖检查3 FAIL；正常加标签后连续保存控制 PASS，exit1 | [请求/状态/错误](new-ui-results.json)、[日志](new-ui.txt) |
| API battery S0–S21 | fails=0，exit0 | [完整摘要](battery-summary.txt) |
| 后端 scratch | 49 PASS，fails=0，exit0 | [输出](scratch.txt) |
| Vue 全套 | 26 passed，suite_exit_code=0；R8-2仍会掩盖pin未执行，不能据总数关闭F-R9-01 | [完整日志](vue-suite.txt) |

| AC | 本轮判定 | 依据 |
|---|---|---|
| AC-01 确认内容/身份恢复 | partial | 正常/旧布局升级及硬重启的现有后端门通过；no-legacy恢复完成状态不可重试，未证明正文丢失，不能签完整恢复合同通过 |
| AC-02 request_id/故障收据 | pass（实跑代表性API协议范围） | S0–S21、scratch；本轮不把历史VM记录当成当前VM通过，不宣称全部输入组合 |
| AC-03 迁移幂等/报告/原件 | partial | 数组迁移、损坏报告、fresh升级拒绝/重试通过；no-legacy收尾不满足完整恢复/重试合同 |
| AC-04 陈旧版本拒绝且修改可恢复 | fail（完整UI合同） | 陈旧写仍被安全拒绝且草稿保留，但T-15要求的成功flush后版本刷新失败，产生自身冲突 |
| AC-05 空库/CRUD/软删恢复 | fail | 正常CRUD、存储错误后端传播通过；pin/tag失败仍无正确UI错误接收 |

## 规范增量、状态与后续

规范目标仍 `docs/specs/notes/durable-inbox.md`、goal仍 `auto-notes/first-real-release`，canonical内容/hash未改。冻结提案的 SD-03/05/07/12 不能完整通过；SD-26 的原 SelectNote 修复在本次旧输入上通过，保留对应任务完成。提案和 work 摘要不得把同例闭合扩张成全路径闭合。

原计划35项中重开 T-04/T-09/T-11/T-12/T-15/T-16/T-17/T-21/T-27/T-33，共10项；保留25项完成（包括 T-02 后端拒绝传播、T-31旧导航缺陷修复）。`current_step=25,total_steps=35,status=executing`，plan_revision仍8；仅记录发现/进度不改变语义修订。下一步同仓 work 修复、补实际HTTP失败协议与成功后版本的区分性oracle，再在新提交复审。VM受影响路径和修复后的回归仍待执行；canonical发布、索引、归档、恢复收据仍为merge-owned pending。

两轮共同诊断：前次“忽略必需写入返回值/只看当次标题”的问题已修；本轮遗漏的是**接口返回协议与调用点异常不一致**、**正文确认与后续动作失败的组合状态**以及**清理多写入的原子性**。R8-2又因沿用前一步错误状态漏掉实际请求，需要永久前置和网络调用断言；不能只再增加测试总数。

## 复放

从 Notes 仓根运行，测试进程设置 PYTHONUTF8=1 / PYTHONIOENCODING=utf-8。新 UI 还需 REVIEW_PYTHON 为实际 Python 路径。先用匹配CLI生成、编译后端，再：

```text
python docs/plans/evidence/001-r8-recheck-20261015/api-probes.py
python docs/plans/evidence/001-r8-review-20261014/replay.py docs/plans/evidence/001-r6-recheck-20261012/run-independent-ui.py docs/plans/evidence/001-r8-recheck-20261015/ui-probes.cjs
```

当前两入口应非零。测试载荷、明确前置、正常控制和原始结果已保留；不是只链接临时日志。未实施修复、合并、推送或归档。
