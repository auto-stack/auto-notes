# NOTES-001 修订 8 work——F-R8-01/02/03 修复与 F-R8-04 证据关闭（2026-10-14）

入口：r8 独立 final review 结论 **needs_fix**（[复审报告](../001-r8-review-20261014/README.md)，
reviewed_commit=1391bd7）。本轮在同一独立仓 `D:/autostack/auto-notes` / `main` 修复
三个阻断缺陷并补齐验证 oracle 与证据绑定，全部门在修复提交上重跑转绿。
工作位置说明：本仓无 worktree 约定（历史各轮均直接在 app 检出工作；review 已确认
旧 `auto-os/apps/015-notes` 目录属 AutoOS main），本轮按复审指示同仓工作。

## 不变量闭合表（finding → invariant → 影响面 → 修复与永久用例 → 当前结果）

| finding | invariant | 影响路径/状态 | 修复 | 永久用例（负例+正常控制） | 当前结果 |
|---|---|---|---|---|---|
| F-R8-01 元数据/删除写失败假成功 | 必需 UPDATE 失败必须 ROLLBACK+显式失败；UI 接收失败不冒充成功 | `repo_set_meta` 的 state/pinned/tags/folder 四个 UPDATE（trash/archive/restore/pin/tags/move 六个入口共用）；UI DeleteConfirmed/TogglePinActive/TagAdded/TagRemoved | `repository.at` 四写入逐一检查 `<0`→ROLLBACK+`ok:false storage_unwritable`；store 失败分支置 conflict+action_error、不刷新工作集/不清草稿；`editor.at` 新增 "Action failed" 横幅（独立于 dirty 的 conflict 分支） | battery **S20**（pin/tags/state/restore 负例+控制，trigger 合成拒绝，挂载/摘除 `\|\| fail`）；scratch **U11**（同四入口 + 最终一致性）；Vue **negatives-r8 R8-2**（真实浏览器：横幅可见/行仍在/服务端 active，控制删除成功） | battery S20 全过；U11 10 断言全过；R8-2 过（26/26 之一） |
| F-R8-02 升级完成标记失败假完成 | 升级/迁移完成事务内全部必需写入逐一检查；失败显式回滚保留重试条件 | fresh 升级 finalize（upgraded/清错误/清凭据）；两路 counter 导入；no-legacy 完成/凭据清理出口；修复合并 finalize（r7 嵌套 if 实为「全部失败才回滚」→ 改析取）；数组迁移 migrated/corrupted_r1 标记 | `repository.at` `upgrade_if_legacy`（finalize+counter+no-legacy 两出口）、`repair_legacy_merge`（counter+finalize OR）、`migrate_legacy_at`（标记写失败→ROLLBACK+saved=false） | battery **S21**（wedge+拒写 upgraded trigger→整体回滚/二次读取恒定/去 trigger 控制成功 n-1 rev2）；scratch **U12**（同场景自包含 exe）；复审原输入 **api-extra.py 复跑 4/4 PASS**（review 时 4 FAIL） | S21 全过；U12 2 断言全过；api-extra exit 0 |
| F-R8-03 导航旧下标覆盖 | 刷新/重排后动作目标必须保持身份与合法下标；保存后草稿 revision 与服务器一致 | `notes_store.at` SelectNote 尾部 `active_id = i` 覆盖按 id 重定位的结果；LoadDraft 无越界防护 | 尾部仅未刷新时用旧下标（`refreshed` 局部标记）；LoadDraft 上界兜底钳位；成功分支本就刷新 notes 再 LoadDraft（重定位正确后 revision 自然刷新） | Vue **negatives-r8 R8-1**（搜索改名移出→点 B：最终下标合法+身份正确+两次连续保存 rev2/rev3 落地+零 pageerror）；复审原输入 **navigation.cjs 复跑 pass:true, exit 0**（review 时 FAIL：第二次保存被自身旧 revision 拒绝）；r7 VM 负例重跑 11/11（R7-VM-2 恢复/Pin 身份、R7-VM-3 满槽原位不受回归） | R8-1 过；navigation exit 0；R7-VM fails=0 |
| F-R8-04 证据链接/绑定失效 | 交付材料链接可解析、绑定与当前源码/工具链/计数一致 | r7 README 12 个相对链接失效（历史目录层级）；两个 *.log 未入库却被链接；docs/README 计数过时；spec 提案未含 T-34 严格 JSON 边界 | r7 README 链接深度修正（11 处）+2 个未入库 .log 改诚实标注；docs/README 更新为本轮状态；本目录提供 r8 实现绑定稿 [spec-delta-r8-implementation.md](spec-delta-r8-implementation.md)（含 T-34 边界、当前工具链指纹、35/35 计数） | 链接逐一 realpath 核对（9 解析 OK，2 标注）；r7 保留历史不改写结论 | 本轮 README 即证据 |

兄弟出口核对（同因不同穴，均已修+覆盖或源码级共用）：folder 元数据与 pinned/tags/state
同函数（repo_move 共用修复，无独立 HTTP 端点——源码级覆盖）；restore 走 state 必需写入
（S20/U11 负例+控制实跑）；repair 合并 finalize 的嵌套-if 缺陷（OR 修正，与 SD-24 声称一致化）。

## 全套门终态（修复提交、同一工具链）

| 门 | 结果 | 证据 |
|---|---|---|
| `auto build -r vue --gen-only` | exit 0 | [build 输出摘录](../001-r8-review-20261014/build-vue.txt)同管线，本轮日志 .auto |
| `cargo build -p auto-notes-back` | exit 0（既有警告不新增） | rust-workspace/target/debug/auto-notes-back.exe |
| battery S0–S21（含 INJECT-OK ×2、S20/S21 新增） | **PASSED, fails=0** | [battery-summary.txt](battery-summary.txt) |
| 后端 scratch（38 旧 + U11×9 + U12×2 = 49 断言） | fails=0 | [scratch-summary.json](scratch-summary.json) |
| Vue 全套（24 旧 + R8-1/R8-2 = 26） | **26 passed** | [vue-suite.txt](vue-suite.txt)（canonical run_vue_suite.py 驱动：种子基线+TEST_MODE） |
| VM 原套件 | 19 passed, suite_exit=0 | run_vm_suite.py 驱动（.auto/r5-vm-*） |
| VM r7 负例 | 11 断言 fails=0（boot 窗口 90s→600s 修复 taskkill 后冷重编超时，纯基建） | [vm-negative-r7-result.json](vm-negative-r7-result.json) |
| 复审反例复跑 api-extra（F-R8-01/02 原输入） | 4/4 PASS, exit 0（review 时全 FAIL） | [api-extra-results.json](api-extra-results.json) |
| 独立 UI 4 场景（r6 oracle）+ navigation（F-R8-03 原输入） | ui_exit=0；navigation pass:true exit 0（review 时 FAIL） | [navigation-result.json](navigation-result.json) |

## 身份与限制

- 工具链：CLI `auto 0.1.0+v0.5.0-352-ge849e06f9-dirty`（/d/autostack/auto-lang/target/debug/auto，
  与复审 baseline 同一二进制指纹线）；AutoDown c39ac7f（pin=实际）；后端 exe 本轮重编。
- 合成 SQLite trigger 拒绝用于验证必需写入失败出口；不是物理掉电。所有实验使用独立
  临时数据目录与动态端口（battery 用 .auto/r9-battery-final；Vue 用 run_vue_suite.py
  自建种子目录；VM 用驱动自建目录），未访问用户知识库。
- `run_vue_suite.py` 本轮修正：exe 名 app-015→auto-notes-back、node 走 PATH、
  TEST_MODE=0→1（使 R8-2 可跑；R8-2 结束还原服务器原数据目录，不影响后续 spec）。
  `verify_backend_scratch.py` 修正 EXE 名（旧名经 replay.py 归一化才能跑，属基建债）。
- `run_vm_negative_r7.py` 仅放宽两处 boot 等待 90s→600s（session 1 被 taskkill 后
  共享 target 冷重编超时的基建抖动；昨日复审 11/11 通过，断言本体未动）。
- 未触碰：canonical spec（发布=merge）、AutoLang/AutoDown 源码、历史证据内容。
- `src/front/tests/screenshots/vm_initial.png` 按复审处置保留未跟踪。

## 可复放入口（仓根，固定工具链）

```text
# battery：先起后端（NOTES_TEST_MODE=1 隔离目录），再：
PYTHONUTF8=1 bash tests/probe/run_v1_battery.sh <OUTDIR>
# scratch（自包含）：
PYTHONUTF8=1 python tests/probe/evidence/r5-work/verify_backend_scratch.py
# Vue 全套（自包含，种子基线）：
PYTHONUTF8=1 python tests/probe/evidence/r5-work/run_vue_suite.py
# VM 套件 / r7 负例（自包含）：
PYTHONUTF8=1 python tests/probe/evidence/r5-work/run_vm_suite.py
PYTHONUTF8=1 python tests/probe/evidence/r7-work/run_vm_negative_r7.py
# 复审原输入复放：
PYTHONUTF8=1 python docs/plans/evidence/001-r8-review-20261014/replay.py docs/plans/evidence/001-r8-review-20261014/api-extra.py
PYTHONUTF8=1 python docs/plans/evidence/001-r8-review-20261014/replay.py docs/plans/evidence/001-r6-recheck-20261012/run-independent-ui.py docs/plans/evidence/001-r8-review-20261014/navigation.cjs
```
