# NOTES-001 修订 9 work——F-R9-01/02/03 修复与 F-R8-04 关闭（2026-10-15）

入口：2026-10-15 再次复审结论 **needs_fix**（[复审报告](../001-r8-recheck-20261015/README.md)，
reviewed_commit=27cff918）。本轮在同一独立仓 `D:/autostack/auto-notes` / `main` 修复
三个阻断缺陷、关闭 F-R8-04 残留，并补齐区分性 oracle。入口工作区带有上轮被中断的
部分修复 WIP（pin/tag 结构化端点、no-legacy 事务、失败分支取回草案），本轮按复审
纠正方向复核后完成：F-R9-02 改为在**不变量点**（flush 成功块）同步 revision，并移除
失败分支的冗余 `get_note_r` 取回（F-R9-01/03 的 WIP 方向与合同一致，经复核保留并补全）。

## 不变量闭合表（finding → invariant → 影响面 → 修复与永久用例 → 当前结果）

| finding | invariant | 影响路径/状态 | 修复 | 永久用例（负例+正常控制） | 当前结果 |
|---|---|---|---|---|---|
| F-R9-01 pin/tag 失败 404 异常、错误分支不可达 | 动作失败必须有 UI 可接收的信封；横幅对应当前动作；陈旧失败状态不吞新动作 | `api.at` toggle_pin/update_tags（`?Note` None→404）；store 三 handler 的 `== None` 判定与 `if .conflict == false` 门禁 | 新增 `PATCH /api/notes/:id/pin/result`、`POST /api/notes/:id/tags/result`（RepoResult 信封，同 update_note_r 先例）；store 改信封判定；干净草稿（dirty=false）动作入口清陈旧 conflict/action_error，dirty 草稿 flush 冲突仍阻止动作 | battery **S22**（新端点 HTTP 200+ok:false storage_unwritable 负例+控制×2）；Vue **R9-1**（PATCH 真实发出/200 信封/横幅=pin/零 pageerror/解除后成功）、**R9-4**（删除失败后 pin 必发新 PATCH——掩盖检查） | S22 全过；R9-1/R9-4 过（31/31 之一）；复审 ui-probes pin/masked_pin 转绿 |
| F-R9-02 正文 flush 后元数据失败留旧 revision | 正文确认成功即同步确认版本；后续动作失败不得自我冲突 | TagAdded/TagRemoved flush 成功块（清 dirty/rid/链但不同步 revision——pin 路径经刷新+LoadDraft 本就同步） | flush 成功块加 `.draft_revision = fr2.doc.revision`（返回信封携带确认文档）；**不**在失败分支取回（单点不变量，少一次 HTTP） | Vue **R9-2**（flush 落 rev2→tags 200 信封拒绝→draft_revision=2→解除后保存落 rev3）、**R9-3**（TagRemoved 同路径）、**R9-5**（正常对照 rev2/rev3 同步） | R9-2/3/5 全过；复审 ui-probes dirty_tag 转绿 |
| F-R9-03 no-legacy 收尾非原子 | 清凭据+写代际同一写者事务；任一失败凭据保留可重试 | `repository.at` upgrade_if_legacy no-legacy 分支（原 DELETE→INSERT 无事务） | BEGIN IMMEDIATE→两写→COMMIT；任一失败 ROLLBACK→`storage_unwritable`（begin 失败=second_writer，与既有约定一致；分支在主 BEGIN 之前，无嵌套） | scratch **U13**（拒 repair_generation INSERT→凭据保留；解除后重试完成代际；正常控制） | U13 3 断言过（scratch 52/52）；复审 api-probes no-legacy 2 FAIL 转绿+控制 pass |
| F-R8-04 残留（链接/提案绑定） | 交付材料链接可解析；提案与实现一致 | r7 README 兄弟目录链接缺 `../`；r8 稿的 UI 接收/可重试声明与实现不符 | 链接补 `../`（12/12 realpath 解析）；提案以 [spec-delta-r9-implementation.md](spec-delta-r9-implementation.md) 修正绑定 | 链接逐一 realpath 核对 | broken: none |

兄弟出口核对：delete 失败通道本就是 `bool`（无 None→404 缺口，S20/U11 保留）；
folder 元数据共用 repo_set_meta（无独立 HTTP 端点，源码级覆盖）；恢复入口 state 写
共用同一必需写入检查（S20 保留）。

## 全套门终态（修复提交、同一工具链）

| 门 | 结果 | 证据 |
|---|---|---|
| CLI 重建（auto-lang e849e06f9 干净重建） | exit 0；`auto 0.1.0+v0.5.0-352-ge849e06f9` | SHA256 `3394469248b25d8d…`（完整值见 §9 收据）；r8 记录的 dirty 项均为文档/账本，不影响生成器 |
| `auto build -r vue --gen-only` | exit 0 | .auto/r9-gen-vue.txt（本地日志） |
| `cargo build -p auto-notes-back --offline` | exit 0（既有警告不新增） | exe SHA256 `35f47f7f5af443cb…` |
| 复审原输入 api-probes（F-R9-03+fresh 对照） | **9/9 PASS, exit 0**（复审时 no-legacy 2 FAIL） | [api-probes-results.json](api-probes-results.json) |
| 复审原输入 ui-probes（F-R9-01/02+掩盖检查+对照） | **4/4 pass, exit 0**（复审时 3 FAIL） | [ui-probes-results.json](ui-probes-results.json) |
| api-extra（r8 复审反例）/ navigation（F-R8-03 原输入） | 4/4 PASS exit0；pass=true exit0 | .auto/r9-api-extra.txt、.auto/r9-navigation.txt（本地） |
| battery S0–S22（S22 新增） | **PASSED, fails=0**（53 断言） | [battery-summary.txt](battery-summary.txt) |
| 后端 scratch（49 旧 + U13×3 = 52 断言） | fails=0 | [scratch.txt](scratch.txt) |
| Vue 全套（26 旧 + R9-1..R9-5 = 31） | **31 passed, suite_exit=0** | [vue-suite-summary.txt](vue-suite-summary.txt) |
| VM 原套件 19 / r7 负例 11 | **19 passed, 0 failed, suite_exit=0**；**11 断言 fails=0** | [vm-suite-summary.txt](vm-suite-summary.txt)、[vm-negative-r7-result.json](vm-negative-r7-result.json) |

## 身份与限制

- 工具链：CLI 自 auto-lang `e849e06f9`（r8 记录线）在临时 worktree
  `D:/autostack/.wt/notes-cli-r9/{auto-lang,auto-down}` 干净重建（原 r8 二进制随
  auto-lang target 清理丢失；r8 baseline 的 dirty 清单为 docs/plans 文档与
  ledger_770.py，不含生成器源——重建版与原线生成器同源）。AutoDown
  c39ac7f（pin=实际，与 r8 固定一致）；后端 exe 本轮重编。
- 合成 SQLite trigger 拒绝用于验证必需写入失败出口；不是物理掉电。所有实验使用
  独立临时数据目录与动态端口；未访问用户知识库。
- 本轮基建修正（不影响断言本体）：`run_vm_suite.py`/`run_vm_negative_r7.py` 的
  CLI 路径支持 `AUTO_CLI` 覆盖（原硬编码路径已随 target 清理失效）；前者 boot
  窗口 90s→600s（与 r7 驱动一致，冷编译期）。
- `src/front/tests/`（复审截图残留）按复审处置保留未跟踪。
- 未触碰：canonical spec（发布=merge）、AutoLang/AutoDown 源码、历史证据内容。

## 可复放入口（仓根）

```text
# 复审原输入复放（F-R9 三项的判据）：
PYTHONUTF8=1 python docs/plans/evidence/001-r8-recheck-20261015/api-probes.py
REVIEW_PYTHON=$(cygpath -w $(which python)) PYTHONUTF8=1 python docs/plans/evidence/001-r8-review-20261014/replay.py docs/plans/evidence/001-r6-recheck-20261012/run-independent-ui.py docs/plans/evidence/001-r8-recheck-20261015/ui-probes.cjs
# 持久门：
PYTHONUTF8=1 python tests/probe/evidence/r5-work/verify_backend_scratch.py
PYTHONUTF8=1 bash tests/probe/run_v1_battery.sh .auto/<OUTDIR>   # 需 TEST_MODE 后端
PYTHONUTF8=1 python tests/probe/evidence/r5-work/run_vue_suite.py
AUTO_CLI=<cli> PYTHONUTF8=1 python tests/probe/evidence/r5-work/run_vm_suite.py
AUTO_CLI=<cli> PYTHONUTF8=1 python tests/probe/evidence/r7-work/run_vm_negative_r7.py
```

限制：battery 的 OUTDIR 必须传**相对路径**（`.auto/...`）——脚本内的
`$(python -c open('$OUT/...'))` 命令替换无法被 MSYS 路径转换覆盖，POSIX 绝对路径
会让 Windows python 解析失败（本轮实测记录，属运行纪律）。
