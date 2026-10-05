# NOTES-001 重新复审（2026-10-05）

结论：`needs_fix`。用户明确授权发现问题时重新激活计划001；计划恢复 `executing`，修订3新增 Phase 2。未实施修复，未改 canonical Spec，未合并代码。

## 基线与证据范围

- 代码提交：`9158fd5e9fbe83629c79bb626242f18ea014c38a`；diff base：`28d5157b7ed8d4f49e55f835bf8a365d2f97a89a`。`git merge-base --is-ancestor a84bce9 HEAD` 成功；`git diff a84bce9..HEAD -- src/back src/front tests/probe/run_v1_battery.sh` 无差异。
- 工作检出：`D:/autostack/auto-os/apps/015-notes`，`v0.6-dev`。`git worktree list --porcelain` 返回的主项是 submodule Git 元数据位置，不能将它当成实际代码目录；旧 Notes worktree HEAD=`8078502`，未用于本次测试。
- AutoLang 742：`bd1ae6ec93253687ee08424b0d621438b18ef7d2`；主检出：`965b368a20db7c97fab7d1b0d51863b3ccca0f11`；AutoDown：`fba6563ed2148ce85e68208863159b4ccccac710`。未修改依赖、未跑 AutoLang cargo 全量。
- 源码/Spec/工具/证据哈希见 [baseline.json](baseline.json)。[spec-delta-r2.md](spec-delta-r2.md) 是被冻结的原复审增量，[spec-delta-r3.md](spec-delta-r3.md) 是修复方案增量；旧 Spec 中的提交与锁保证与实测不符，不能沿用原 pass。
- 本次上下文未参与原实现；依据源码和独立实验复审，没有另建任务/子代理。原通过及归档记录保留为历史。
- Runtime 使用现存生成后端 `rust-workspace/target/debug/app-015-notes-back.exe`（SHA256 `1ae6dee3342d0c8b0c42ef3d5fc82bc14f709afac5a806336ac1fb3155bad1f8`）及现存生成 Vue。没有 fresh build，不能将结果当作当前标准工具链重新构建或 VM 验收通过。所列缺陷均核对 HEAD 对应源码。
- 实验均在 `.auto/review001-*` 的独立数据目录，后端由脚本创建并只终止自己的进程；未触碰用户数据。先前未跟踪的 `review-s10-recovery.json`、`seeded-review/` 与 vendor package-lock 保留。

## 验收结果

| AC | 任务 → 代码 | 本次证据 | 结果 |
|---|---|---|---|
| AC-01 | T-00/T-02/T-03/T-04 → repository.open/load/update | results.before_crash/restart_forced/restore：中文标签、rev2、稳定 ID、trash 状态经硬杀后显式接管读回；默认重启 second_writer。extra-results.torn_manifest_simulation：实体/journal/receipt仍在，但不完整 manifest 导致 corrupt，无恢复重放 | partial：正常持久读回成立，提交中断恢复未成立 |
| AC-02 | T-01/T-02 → create/update/journal/receipt | 成功创建重放同 ID 成立；after_manifest 后同 request_id 重放 n-2→n-3，留下两个对象；成功 update 重放却 revision_conflict；收据路径不可写时仍返回 ok/committed | fail |
| AC-03 | T-01/T-03 → migrate_legacy_at | `[valid(id10),null,valid(id11)]` 返回 migrated=1、corrupted=[]、saved=true，后项 n-11 未迁入；原件仍保留、常规 fixture 历史采证保留 | fail |
| AC-04 | T-02/T-04 → repository + api.update_note + notes_store | 8 请求同时 expected_revision=1：多个越过检查、返回 corrupt，最终正文 corrupt；持外部锁的迁移仍 saved=true；legacy 两客户端旧快照提交均200，B覆盖A且r2实体被删 | fail |
| AC-05 | T-03/T-04 → seed/CRUD/trash/restore | 隔离套件显式 NOTES_SEED=1，18/18 Playwright；默认 NOTES_SEED=0 场景无演示笔记；硬杀接管后 restore 成功 | pass：当前基本 CRUD，后续修复需重验 |

## 阻塞发现

### F-001-01 — P1：变量级锁不能保证仓储事务串行化，迁移也能绕过写者门禁

对应 AC-01/04、T-02；修复 T-05/T-06/T-08。`repository.at:1327` 中读取/比较 revision、写实体和重写 manifest 没有整个操作的排他区间；生成 `repository.rs` 将每个模块变量分别 Mutex 化，端点直接调用仓储，不能串行整个事务。8 个同时 expected_revision=1 的更新出现 5 个 corrupt、3 个 conflict，最终 n-1.r2.json 损坏，且两个错误结果带 committed 收据。并发实体可被反复 truncate，旧实体还会被相互当作 oldfile 删除。

`db.at:v1_migrate → migrate_legacy_at` 不调用 open_repository；有 writer.lock 时 GET 返回 second_writer，但 POST migrate 仍写入3条和 manifest。`open_repository` 的 exists→write_text 也不是原子锁，写入结果未检查；锁不会正常释放，force 无活写者验证。修正必须覆盖整事务、所有写入入口和实际双进程，不以变量锁/陈旧锁测试替代。

### F-001-02 — P1：提交与请求收据分离破坏幂等，更新可返回未持久化的成功收据

对应 AC-02、T-02；修复 T-07。`repo_create` 只用 receipt 查重；after_manifest 后对象 n-2 已可见、receipt缺失，同 request_id 再提交产生 n-3。原 S9 电池在 after_manifest 注入 `req-fault-2` 后却重放 `req-fault-1`，没有断言前者只有一个对象，因此原“AC-02 pass”不成立。

`repo_update` 不读取已有收据，成功 update-1 的原样重放直接 conflict；`write_receipt(rc)` 返回值被忽略。在收据文件位置预建目录模拟确定性 I/O 失败，仍返回 `ok=true,status=committed`。修正创建/更新的共同幂等边界、故障后请求映射与错误返回，不只改测试。

### F-001-03 — P1：迁移将 null 当数组结束，静默漏掉其后合法项

对应 AC-03、T-01；修复 T-08。`migrate_legacy_at` 的 n_probe→encode==null→break 无法区分数组内 null 与越界。最小输入 `[valid,null,valid]` 仅迁入首项，损坏报告为空，还提交 manifest，使再次迁移 skipped_existing，后项无法再导入。损坏报告目录创建/写入返回值同样未校验，报告失败也可能继续 saved=true（此子项为源码检查，未另造运行失败）。必须逐项完整遍历、报告损坏、可靠保存报告并在失败时回滚。

### F-001-04 — P1：legacy/UI 没有读取时 revision，陈旧编辑覆盖新内容且旧版被删除

对应 AC-04、T-04；修复 T-09。`api.at:264` 从服务器重新读当前 revision 再写入；Note/前端草稿无 revision，绕过用户编辑基线。两个客户端先读同一 Note，A保存后B仍基于旧快照提交；两个 PUT 均200，最终 rev3 是B内容、A的r2实体已被删除。顺序 v1 陈旧写入拒绝测试不能证明 UI 的 AC-04。

`notes_store.at` 忽略 API 结果的语义，没有冲突版本/可恢复草稿状态。HTTP失败在生成Vue可抛异常并中断 handler，本次不声称已实测所有失败都会清 dirty；实际已证明的缺陷是陈旧内容被 API 接受覆盖，且没有保留双方的恢复路径。修正需端到端携带读取 revision、稳定 request_id 与冲突恢复。

### F-001-05 — P1：manifest 会被原地截断，journal没有恢复入口，不能恢复上次已确认提交

对应 AC-01/02、T-02；修复 T-05/T-07。`save_manifest_to_disk` 用 truncate+write，I/O失败分支只回滚内存并假设磁盘未变；open_repository 只解析 manifest，失败即 corrupt，未扫描/replay journal。journal仅有ID/revision，无法完整重建独立变更的标签/state/folder；旧实体在更新时删除，没有完整历史检查点。

实验先成功创建/更新，再构造 manifest 截断状态，硬杀后的新进程用显式 FORCE_LOCK 开库仍 corrupt，journal与收据尚在。**这是对 truncate+write 中断状态的构造实验，不是准确在写入中硬杀，也不是实测掉电。** 已确认数据跨进程恢复的要求不能用“掉电窗口债务”掩盖进程/I/O中断丢失索引的问题。需可靠提交点、可恢复完整检查点与真实阶段中断回归。

### F-001-06 — P2：请求标识直接拼文件路径，变更型测试钩子未隔离

对应 AC-02/04/05、T-02/T-04；修复 T-10。request_id=`../escaped` 被接受，收据写成 `<data>/escaped.json`，逸出 receipts。`api.at` 的 setup/fault/open/loadmanifest/listloop 常驻、没有显式测试模式门禁；setup修改全进程环境且 test_reset 不清持锁目录状态，调用者可以改变仓储目录和故障状态。需编码/校验标识、统一写者门禁并默认关闭变更型测试端点，不能在生产接口留临时调试钩子。

## 检查、复现与限制

- 完整现有 Vue 套件：`NOTES_URL=http://127.0.0.1:17918 npm --prefix tests test` 的等价 Node Playwright入口，18/18通过（[playwright.log](playwright.log)）。显式 seed 的独立后端/前端由脚本启动，退出已清理。只说明现有成功/主题回归通过，不覆盖上述负例。
- 补充真实 HTTP、硬杀/重启、并发和 I/O失败记录：[results.json](results.json)、[extra-results.json](extra-results.json)。脚本成功生成证据，原控制台打印曾因GBK无法表示emoji失败；证据已落盘且所有实验已执行，交付的复现脚本使用ASCII打印修正输出编码。
- 在仓根运行 `python docs/plans/evidence/001-review-20261005/reproduce.py`：每次创建唯一 `.auto/review001-*` 目录，使用现存后端二进制；会产生原始观察结果，预期当前缺陷仍在。这是复审取证工具，不是将当前错误行为断言为正确的回归测试。并发具体失败数量受调度影响，应核查是否恰好一个成功且其余纯 conflict。
- 在仓根运行 `python docs/plans/evidence/001-review-20261005/run-playwright.py`：启动隔离seed后端和Vue、跑现有完整套件。要求本机既有 Node/Playwright/Vite环境与空闲17918/17919；不安装依赖。脚本中的平台工具定位沿本次环境，执行者可改为自己的有效Node路径。
- 没有重跑原battery脚本：它写死/删除 `tests/probe/evidence/v1/wk`，会重置既有数据，且无 pipefail，Python断言可被tee掩盖；本次用全新目录取证并检查旧脚本断言。后续 T-11 必须修复电池门禁。
- 未重新编译、未运行 VM UI；本次是失败复审，未把未验证要求记为 pass。Phase 2 必须在修复 commit/依赖版本重新构建并完成双端验证。
- `git fetch origin v0.6-dev` 因沙箱只读 submodule Git 元数据无法写 FETCH_HEAD；本次文档/证据修改留在工作区，未同步、提交、推送或推进父仓gitlink。Git身份/全局配置未修改。

## 下一步

执行 [计划001 Phase 2](../../001-durable-inbox.md) 的 T-05。先验证事务/锁/恢复能力，确认可行后按 T-06–T-11 修复并复审；旧pass作废，全部阻塞发现关闭前不归档。
