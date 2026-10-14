# NOTES-001 修订 8 独立复审（2026-10-14）

结论：**needs_fix**。实施曾申报 35/35，但当前提交仍有三个原合同内的实现缺陷，以及验证材料的关闭缺口；不能转 reviewed 或归档。检查当前用户工作区 `D:/autostack/auto-notes` / `main`，提交 `1391bd7eb2f6b3b08e9841d30b25125e47ced058`。本会话未参与 Phase 6/7 实现，无子 agent。

## 基线与限制

- [baseline.json](baseline.json) 记录完整 Notes/依赖提交、CLI 与运行制品指纹、源文件指纹、规范输入与审查技能指纹。[输入计划](plan-input-r8.md) 保存本轮入口合同。
- 计划记载的旧实施目录如今是 AutoOS `main` 的普通目录，属于 AutoOS 仓库；本轮按用户提供的独立 Notes 工作区检查。确认 Notes r7/r8 实现提交是当前 HEAD 祖先；没有在 AutoOS 修改或生成另一份实现树。
- Notes 实现源码已提交，无实现 WIP；入口未跟踪的 `src/front/tests/screenshots/vm_initial.png` 保留。仅新增本轮审查材料和计划状态，不修改产品实现。
- 使用当前 CLI 重新生成 Vue/后端并编译成功。CLI 版本为 `e849e06f9-dirty`，实际构建时的 dirty 源不可恢复，未冒称它来自 AutoLang 当前 HEAD。后端编译依赖 AutoLang `c171c1a`；期间依赖 HEAD 前进的差异仅为文档，运行源码没有漂移。
- VM 启动按现有流水线重建后端，制品 hash 与 Vue/API 轨不同；两轨分别绑定，不能把后一次制品 hash 倒填到前一次测试。当前 .at 实现指纹稳定。生成器的非组件文件提示及生成 Rust 告警保存在构建日志，未声称零告警。
- 合成 SQLite trigger 拒绝用于验证必需写入失败出口；不是物理掉电。所有实验使用独立临时数据目录与动态端口，未访问用户知识库。

## 验证与验收映射

| 验证 | 本轮结果 | 证据 |
|---|---|---|
| Vue 生成 + generated backend 编译 | exit 0 / exit 0 | [Vue 生成](build-vue.txt)、[后端编译](build-backend.txt) |
| API battery S0–S19 | exit 0，fails=0；INJECT-OK 两次 | [电池](battery-summary.txt) |
| 后端升级/意图/迁移 scratch | 38 个 PASS，fails=0 | [逐项输出](scratch.txt) |
| 前次独立 API 反例与正常控制 | 6 个 PASS，exit 0 | [结果](api-results.json)、[输出](api.txt) |
| Vue 原套件 | 24 passed，子套件 exit 0 | [完整日志](vue-suite.txt) |
| VM 原套件 | 19 passed，0 failed/skipped，suite_exit=0 | [结果](vm-result.json)、[日志](vm-suite.txt) |
| r7 VM 补充 | 3 场景、11 个实际 PASS（含前置条件），fails=[]，exit 0 | [输出](vm-r7.txt)、[结果](vm-r7-result.json) |
| 原独立 Vue 四场景 | 原 oracle 全绿，但有未计入 oracle 的越界错误，不能当作完整通过 | [原始状态](independent-ui.json)、[输出](independent-ui.txt) |
| assertion 故意失败传播 | battery exit 1；只有目标 S19a 记失败，控制通过 | [控制](assert-control.json) |
| 注入器故意失败传播 | battery exit 1，记录 S15 注入失败，控制通过 | [输出](inject-control.txt) |
| 新增元数据/升级失败出口 | 4 个 FAIL | [原始输入与结果](extra-results.json) |
| VM 重建后的后端再次复验 | 同四个 FAIL，确认制品变更未消除缺陷 | [结果](extra-postvm-results.json)、[输出](extra-postvm.txt) |
| 新增导航后连续两次保存 | FAIL：第二次被自己的旧 revision 拒绝 | [原始结果](navigation-result.json) |
| 删除 UI 失败观察 | 接口 true、服务端 active；dirty 草稿仍在，**未复现草稿丢失** | [结果](delete-result.json) |

| AC | 判定 | 任务/实现/证据 |
|---|---|---|
| AC-01 已确认内容/标签/稳定 ID 正常及异常恢复 | fail | scratch/电池正常与硬重启通过；T-12/T-17 的升级完成标记失败导致后续内容不可见，F-R8-02 |
| AC-02 request_id 幂等及故障收据 | pass（所列代表性协议路径） | T-07/T-14/T-18/T-26/T-30；电池 S6/S9/S11/S13/S17、scratch 原收据/兼容控制、连续未知响应 Vue/VM 路径；不扩张为所有输入组合 |
| AC-03 可重试迁移、损坏报告与原件 | fail | 数组迁移/报告/Unicode、严格清单正常与坏项通过；旧布局升级必需完成写失败未回滚，F-R8-02 |
| AC-04 陈旧版本拒绝、草稿恢复、第二写者 | fail（完整 UI 合同） | 电池并发/锁、Vue 恢复通过；T-09/T-15/T-31 导航后未刷新读取 revision，后续保存产生自身冲突，F-R8-03；修改内容仍在，未声称数据被覆盖 |
| AC-05 空库、CRUD、软删恢复 | fail | 默认空库、正常 CRUD/软删恢复通过；T-02/T-04 元数据与删除必需写失败被假报成功，F-R8-01 |

## 发现与下一步

### F-R8-01 / P1：元数据和删除写入失败仍确认成功

原要求：T-02 结构化存储错误、T-15 元数据错误不冒充成功、AC-01/05、SD-03/05。`src/back/repository.at:1242–1251` 忽略 state/pinned/tags/folder 的 UPDATE 返回值；SQLite `RAISE(ABORT)` 只终止失败语句，后续 COMMIT 可以成功，函数因此返回 `ok:true`。

实际 HTTP：拒绝 pinned UPDATE 后 PATCH 返回一个成功 Note（pinned 仍 false）；拒绝 tags UPDATE 后 PUT 返回成功 Note（tags 未改变）；拒绝 state UPDATE 后 DELETE 返回 `true`，文档仍 active。移除 trigger 后的同入口正常控制有效。真实浏览器删除也返回 true，但原文档依旧存在。修复所有必需 UPDATE 的失败传播/回滚，并让 UI 接收失败结果；按 pinned/tags/state/folder 及恢复入口覆盖负例和正常控制。当前确证前三个字段，folder 为同函数源码覆盖，未冒称已运行 folder API。

影响：T-02/T-04/T-09/T-15 及其依赖验证任务；AC-01/05、SD-03/05。

### F-R8-02 / P1：旧布局升级完成标记失败仍提交笔记

原要求：T-12/T-17 失败保全、完整事务升级及可恢复重试，AC-01/03，SD-07/12/17/24。`repository.at:530–532` 在 fresh 升级出口没有检查 `upgraded`、清错误及清凭据写入结果。

在净库移除 `upgraded` 标记，挂载原 wedge-snapshot，并用 trigger 拒绝 INSERT meta(upgraded)：第一次 GET 返回已导入的 n-1/rev2；第二次 GET 返回 `[]`，状态错误为 `legacy tree present but repository already contains notes`。库已提交 notes，却没有完成标记，错误状态阻止后续读取。源码另有 no-legacy 凭据清理/完成出口及数组迁移 meta 写入未检查，交 work 一并核对同类必需写入，不把未实跑支路记为失败证据。

修复应检查完成事务内全部必需写入，失败显式回滚并保留重试条件；重放本反例、成功旧布局控制、补 no-legacy 修复出口与失败恢复后的再次读取/重启。影响 T-12/T-17 及依赖验证任务；不撤销已通过的独立 repair UPDATE 反例闭合。

### F-R8-03 / P1：稳定 ID 重定位被尾部旧下标覆盖

原要求：T-31 flush 刷新/重排后目标 ID 继续成立、T-09/T-15 成功刷新读取 revision，AC-04/05，SD-26。`notes_store.at:848` 在前面按稳定 ID 重定位后，尾部重新执行 `.active_id = i`。

复现：搜索 NavProbe（A 原下标 0、B 原下标 1），将 A 改名使其移出过滤结果，再点击 B。列表仅剩 B，active_id 却是 1，Vue 报 undefined.id/title；表面 draft_id/title 仍正确，所以旧 oracle 的 `pass` 是 true。编辑 B 第一次保存后服务器 rev2、草稿仍 rev1；第二次编辑保存返回 conflict，服务器保留第一次内容。本轮新增后续操作 oracle 为 fail。

修复：整个动作沿用当前 ID 重定位后的合法索引，LoadDraft 前确保上下界与身份；对刷新为空、目标消失、恢复目标筛选外等路径补正常和失败控制。Vue/VM 应验证最终索引、草稿 revision、无越界错误及后续至少一次保存，不只检查当次标题。影响 T-04/T-09/T-15/T-31 及验证任务。

### F-R8-04 / P2：复审材料仍有失效链接及过时实施绑定

T-33 要求真实证据链接、当前计数/交接以及实际 Spec 提案。r7 README 的 12 个相对链接均解析到不存在路径（[完整核对](link-check.json)）；即便调整目录层级，部分被引用 `.log` 文件也不存在。入口时 docs/README 仍写 r7/34/34；r7 Spec 提案冻结的 AutoDown/AutoLang、发布核对 34/34 与本轮 r8/35 项不符，也未体现 T-34 的严格 JSON 读取边界。canonical 尚未发布本身属于 merge-owned，**不是本轮实现缺陷**。

修复：准备与最终源码、CLI/依赖、验收命令一致的提案与 durable receipts，修真实链接；保留历史证据。当前 review 已建立可解析证据，不代表旧交付材料已修好。影响 T-11/T-16/T-21/T-27/T-33。

## 对知识增量的裁决

[冻结的待审提案](spec-delta-reviewed-r8.md) SHA256 见 baseline。目标仍为 `docs/specs/notes/durable-inbox.md`，goal 仍 `auto-notes/first-real-release`，impact 无缩减。SD-07/12 的全新升级失败边界、SD-03/05 的错误出口、SD-26 的持续身份/版本行为不成立；SD-11/16/28 的证据关闭不完整。严格类型、原收据、兼容决策 A、repair UPDATE 失败重试、双槽阻止和链裁决的已验证部分保留。不能发布全文或从历史全绿推导当前 pass。canonical hash 未变，未改 live ledger。

## 收敛诊断

前轮已登记“新状态分支缺 oracle、脚手架吞失败”，本轮两个失败传播控制都通过，吞失败缺陷已关闭。剩余问题是 oracle 覆盖语义不足：只测 repair 的 UPDATE，漏 metadata/fresh finalize；只看导航当次 draft_id/title，漏合法索引与后续保存。因此同一实现可同时产生 24/19/38 全绿和本轮真实失败。下一次 readiness 须给这三类不变量的闭合表、兄弟出口与成功控制，不能只重放旧例或汇报总数。

## 可复放入口

从独立 Notes 仓根，使用匹配工具链生成/构建后执行；这些脚本只改测试启动路径，不改产品代码、输入语义或原断言。Windows shell 将 `PYTHONUTF8=1` / `PYTHONIOENCODING=utf-8` 设入测试进程环境。

```text
python docs/plans/evidence/001-r8-review-20261014/replay.py docs/plans/evidence/001-r8-review-20261014/api-extra.py
python docs/plans/evidence/001-r8-review-20261014/replay.py docs/plans/evidence/001-r6-recheck-20261012/run-independent-ui.py docs/plans/evidence/001-r8-review-20261014/navigation.cjs
python docs/plans/evidence/001-r8-review-20261014/replay.py docs/plans/evidence/001-r8-review-20261014/run-battery.py
```

以上两个新增反例当前应返回 1；控制和旧全套结果见各 receipt。删除 UI 脚本另需 `REVIEW_PYTHON` 指向实际 Python，其观察是 false-success，未复现草稿丢失。下一步交同仓 work 修复/补测试，再在新提交独立复审；本次仅检查，未实现修复、追加产品范围、合并、推送、发布规范或归档。

范围边界：r5 VM 历史 13 项补充未在本轮重跑；当前已实跑 VM 原19项与r7的3个场景、Vue24项和上述独立输入。已确认原合同缺陷后，不再以补齐全套数量为签发 pass 的理由；work 仍须在修复提交与固定工具链上闭合受影响完整矩阵。合并时的 canonical 发布、派生索引、归档及恢复收据都保持 pending。
