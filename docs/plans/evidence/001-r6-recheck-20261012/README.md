# NOTES-001 修订6独立 final review（2026-10-12）

结论：**needs_fix**。审查交付 `f0a3cab2485e750049e2e05bc2185dccee334c4f`，实现 `1757a906ea8a31f26cdbfa98e7e4625eced41266`，diff base `9a22886eaaaae203a65176fbfa8813180b6d6459`。本上下文参与过前次复审，未参与 Phase 5 实现，无子 agent；所有当前结论由源码、重新生成构建和隔离运行重建。

用户最新消息确认决策 A。T-26 已闭合：不可验证意图的旧行安全拒绝；新协议及正确迁移 v2 的相同意图仍重放原收据。此决策不需再次批准，不把它与下面实现缺陷混为一项。

工作树为 `D:/autostack/auto-os/apps/015-notes` / `v0.6-dev`。Git worktree 元数据显示 submodule 元数据目录，实际 top-level 和执行位置是该 app 检出；没有另建 review 树。提交、依赖、CLI/源/输入/最终 Vue 后端指纹见 [baseline.json](baseline.json)。AutoLang `897eb34911a4f496a28ba7cdfd8a82815fa043d1`，CLI 源为其祖先 `a6e108f60b0c36a1ffdfea4410a3b11d81eda865`，AutoDown pin=实际 `96f095bfc41a8686331c5ccd3ce17b685147fcc1`。其他会话的 AutoLang 文档和未跟踪 review fixtures 原样保留，运行源码/构建配置未漂移。

## 原回归与上轮示例

| 实际门 | 本轮结果 | 持久证据 |
|---|---|---|
| fresh Vue gen + 应用 backend build；VM 启动自身生成构建 | 成功 | [生成](final-build-vue.txt)、[构建](final-build-backend.txt)、VM 结果 |
| battery S0–S19 | exit 0，但 S15 注入未执行，不能签发全部场景通过 | [完整日志](battery.txt)、[summary](battery-summary.txt) |
| 后端 scratch | 38 PASS，fails=0 | [实际断言输出](scratch.txt) |
| Vue 全套 | 24/24，suite_exit=0 | [Playwright](vue-suite.txt) |
| VM 原套件 | 19/19，suite_exit=0 | [日志](vm-suite.txt)、[结果](vm-suite-result.json) |
| VM 原负例 | 13/13，fails=[] | [结果](vm-negative-result.json) |
| 上轮独立 API / Vue / VM | 3 / 2 / 2 断言通过 | [API](old-independent-api.json)、[Vue](old-independent-ui.json)、[VM](old-independent-vm.json) |
| 双进程同 expected_revision | 1 成功、7 revision_conflict | [实际响应](dual-process.json) |
| battery 故意失败对照 | 只将 S19a 断言改 false，实际 exit 1 | [控制记录](battery-control.json)、[完整输出](battery-control.txt) |

原检查确实修好了上一轮示例：混合库重读冲突、rev3 不被反复回退、实体 `{}` 拒绝、满槽 Recover 保全、C1→C2 单次未知响应的导航裁决。本轮没有把这些成功改判失败；下列失败是同一承诺的其他代表性分支。

原 wrapper 首跑在测试通过后因 GBK 输出字符失败；最终 UTF-8 重跑通过。第一次 VM 负例构建与自有浏览器后端同时占 exe，构建拒绝访问，属于本轮调度失误；所有实例退出后串行重跑 13/13。[失败记录](vm-attempt-environment-failure.json) 保留，不算产品回归。Vue 目标最终又生成构建，非 VM 门在该最终二进制上重跑。没有修改产品源码或手改生成 Rust；生成器已有未用代码/风格告警如实保留，未运行框架 cargo 全量。

## 当前发现与可重跑输入

所有发现属于已有升级、草稿保全、CRUD 和验证门契约，没有追加产品功能或规模阈值。SQL trigger 是隔离 SQLite UPDATE 拒绝的合成失败控制，不冒称实际磁盘断电。

| ID / 严重性 | AC / 任务 | 现象与原要求 | 修复边界 |
|---|---|---|---|
| F-R7-01 / P1 | AC-01/03，T-23/T-17/T-12 | manifest 的 `legacy_id="7"` 指向实体 n-1/legacy_id=1，仍导入 n-1/legacy_id=7；`revision=true,tags=[7,null],folder=42,pinned=1` 导入 rev0、错误 tags 并标 upgraded；`revision="2oops"` 被当 2 | authority 合并前校验清单字段和双向身份，允许历史合法十进制字符串，拒绝布尔/杂字符等非法形式；普通升级与修复共用验证，回滚且可修复重试 |
| F-R7-02 / P1 | AC-01/03，T-22/T-17/T-07 | `repair_legacy_merge` 已匹配行的 UPDATE 不检查结果；合成 SQL 拒绝后仍清 corrupted_r1、置 repair_generation、返回无错误；移除故障再读仍不恢复权威 tags/folder | 事务内所需更新失败须回滚、报错并保留重试凭据；成功完成标志只能跟随整个修复成功，不允许假完成 |
| F-R7-03 / P1 | AC-02/04，T-25/T-19/T-09 | C1 已提交但 HTTP 响应丢失；C2 请求在到后端前中止；编辑 C3 后重试，prev 被改成从未提交的 C2。服务器仍 C1 rev2，C3 永久 dirty/conflict | 不能在未知链扩展时丢掉仍可能已落地的祖先；先裁决未确认提交或保留足够可证明上下文；外部不同内容仍不得被强行覆盖 |
| F-R7-04 / P1 | AC-04/05，T-25/T-19/T-15/T-04 | 筛选内 A 改名后点击 B，成功保存刷新结果却继续用旧索引，LoadDraft 越界，界面仍 A；恢复筛选外 R 后点击 Pin，R 未置顶，另一条可见 Z 被置顶 | 保存/导航/恢复/动作按稳定目标身份绑定，刷新重排后重新定位；恢复目标不在工作集也不能用另一行的 active_id 执行 pin/tag/delete |
| F-R7-05 / P2 | AC-04/05，T-24/T-25 | 两槽 A/B 满且 C dirty，搜索 flush 冲突后被容量阻止，草稿和两槽保留，但 search 从空改 NeverMatch、工作集仍旧，违反原位/搜索词不变规则 | 容量判断覆盖完整动作状态，失败不提交查询/筛选/选择/新建副作用；两 Recover 及所有导航继续对称保全 |
| F-R7-06 / P2 | 全部 AC 的验证门，T-27/T-21/T-11 | S15 Python -c 外层双引号中的 JSON 内层引号未转义，SyntaxError 被忽略，事务 UPDATE 未执行；后续断言读已正确数据仍通过。r6 工作原始 battery-full.log 已有相同错误却宣称修复 | 注入必须可靠执行并验证前置状态；每次 required fixture/setup 失败都传播；故意破坏注入本身应非零，而不仅普通 assert false 非零 |

[API 实际记录](api-results.json) 含合法原快照正例、三种 manifest 坏值、SQL 失败/移除 trigger 后重试。五个新增断言失败，独立脚本 exit 1；源文件 hash 不变。

[Vue 实际记录](ui-results.json) 含四个失败场景，脚本 exit 1；读 store 只作观察，编辑/保存/搜索/导航/Recover/Pin 都是真实浏览器动作。C1/C2 的 route.abort 与恢复场景的实际 after_manifest 钩子分开记录。恢复场景服务端结果 R pinned=false、Z pinned=true；满槽时 A/B/C 三份均在状态中但 search 已错误变更。浏览器越界及 Failed to fetch 原始错误保留。

相关源码：`repository.at:619/642/704/810`（更新结果/凭据/实体校验/未经校验的权威清单），`notes_store.at:259/359/676/752/773/1001/1065/1079/1149`（加载/恢复/索引导航/祖先覆盖/错误目标/搜索提交），`run_v1_battery.sh:450–465`（无可靠注入传播）。行号只用于本次提交，修复后须重新核对。

## AC → 任务 → 证据与规范

| AC | 当前结论 | 通过部分 / 未闭合部分 |
|---|---|---|
| AC-01 | fail | 新 SQLite 正常/硬杀恢复通过；旧权威身份/类型及修复假成功失败（F01/F02） |
| AC-02 | partial | 决策 A 和请求协议正反例通过；连续未知响应的新意图不能继续保存（F03） |
| AC-03 | fail | notes.json 严格迁移/报告/Unicode/幂等通过，T-20 保持闭合；旧树 manifest 非法项和修复失败处理未闭合（F01/F02） |
| AC-04 | fail | 条件更新/双进程拒绝/上轮槽示例通过；连续未知链、恢复动作目标、容量阻止状态失败（F03–05） |
| AC-05 | fail | 默认无种子及原 CRUD 套件通过；筛选和恢复组合下 CRUD 操作错目标，原历史勾选不覆盖该分支（F04） |

已冻结 [输入计划 r6](plan-input-r6.md) 和 [提交的实现 Spec 稿](spec-delta-reviewed-r6.md)。后者冻结 SHA256 `a54bc1e0afceb9f515f9eccec2d20f743d01adf5213751c2e72b7d177af730cf`。SD-21 兼容决策通过；SD-17 的 UPDATE 失败边界、SD-18 清单类型/身份、SD-19 原位状态、SD-20 完整未知链/稳定目标仍不能按“已验实现”发布。canonical r3/blob `8f05b8ddb617d5d64e937e55027e782a2b0c0f85` 未动；[修订7增量](spec-delta-r7.md) 是修复合同，不是通过后的实现稿。

当前 r6 文档存在同段“决策 A 已闭合/待用户”、checked 任务旁“当前未完成”、§9 outcome 与 task_ids 相反、§10 仍称无决策；r6-work README 的 tests 链接层级也错，scratch-summary.json 实际不存在。本轮已统一当前计划/索引，旧原文留冻结输入作历史；T-33 负责修复真实证据链接和准备正确实现稿，不能再靠当前总数覆盖未验分支。

## 重跑与下一步

在 app 根运行，Python UTF-8；要求本机匹配 CLI、已有应用构建、Playwright 依赖。动态端口/隔离库由脚本负责；不得并行运行会重新生成/构建同 exe 的 VM 与持有该 exe 的浏览器/API 测试。

```powershell
$env:PYTHONIOENCODING='utf-8'
python docs/plans/evidence/001-r6-recheck-20261012/independent-api.py
python docs/plans/evidence/001-r6-recheck-20261012/run-independent-ui.py
python docs/plans/evidence/001-r6-recheck-20261012/battery-control.py
```

前两者当前 exit 1；修复后应 exit 0。battery-control 本身应 exit 0，因为它验证被故意改坏的电池实际 exit 1；它不证明 S15 注入已可靠，T-33 另需注入失败控制。完整门使用已有 r5-work/r6-work runners 和 `run_v1_battery.sh`，具体命令/参数在 baseline 与结果 JSON；新反例须固化产品 tests，并在 Vue 与实际 VM 上验证对应共享路径。

按原用户授权，计划转 **executing**、修订7新增 Phase6 T-28–T-33，重开 T-01/T-02/T-04/T-07/T-09/T-11/T-12/T-15/T-16/T-17/T-19/T-21/T-22/T-23/T-24/T-25/T-27；保留其他11项完成，T-26 决策 A 保持闭合，当前 **11/34**。next=work，修复提交后同树独立 final review；canonical 发布、索引派生、归档/恢复收据仍是 merge-owned pending，不能提前合入。未推送，未修改父仓 gitlink。

保留任务的闭合依据如下；这不代表受影响的完整 AC 已通过。

| 保留任务 | 当前闭合依据 |
|---|---|
| T-00/T-05 | 已冻结应用能力/SQLite 协议未改；本轮两目标 fresh build、持久提交/故障/重启通过，CLI与运行源指纹固定 |
| T-03 | 本轮 scratch 的源 hash、备份与隔离 seed，battery S5/迁移样本 |
| T-06 | battery 条件并发与实际双进程 1成功/7冲突；未发现写者门绕过 |
| T-08/T-13/T-20 | S1–4/S14/S18 与 scratch M1：损坏报告、null后项、Unicode、严格类型、报告失败重试、原件保留 |
| T-10 | S0 请求标识负例及默认关闭变更钩子，路径守卫仍通过 |
| T-14/T-18 | S12/13/17 与 scratch R1–3、旧同请求独立控制：编码、目标/意图与原收据；兼容差异按批准A |
| T-26 | 用户最新消息及决策制品批准A，原样/异图旧行均安全拒绝 |
