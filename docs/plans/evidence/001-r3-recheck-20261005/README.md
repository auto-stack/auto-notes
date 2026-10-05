# NOTES-001 修订3再次复审（2026-10-05）

结论：`needs_fix`。SQLite 修复有效，但原 AC 仍有失败，不能沿用先前 pass/archived。按同会话用户既有条件授权，重新激活计划001并追加修订4/Phase 3；本轮只复审和修订计划，未修实现或 canonical Spec。

## 基线与验证范围

- Notes reviewed_commit=`f8dc027ce50ffad4676f574edb5d226a8d8cbf9a`；实现基线=`29b8824b16c5c9a0ddcc952020c347a0567cfe87`；diff base=`e42eab06bc3621b5e4b18492559ef39db70abd33`。之后源代码/前端测试/Spec无差异，最新提交是review/archive与battery前置说明。
- 当前代码检出=`D:/autostack/auto-os/apps/015-notes`，分支v0.6-dev；旧外部worktree仍8078502，未用作基线。实现代码无未提交改动；预存未跟踪旧review证据保留。
- 依赖：AutoLang main=`7b9c6948c1465e87a6f60404510c30c712e1c7bc`，742 worktree=`9f6481e8c78e2633395c2cefc653e120b28a5e8f`。HEAD固定AutoDown=`fba6563ed2148ce85e68208863159b4ccccac710`，实际checkout=`96f095bfc41a8686331c5ccd3ce17b685147fcc1`（本次前已脏gitlink，未改动）；vendor的未跟踪package-lock保留。
- Spec 输入 `docs/specs/notes/durable-inbox.md` blob=`8f05b8ddb617d5d64e937e55027e782a2b0c0f85`。源码、规范、冻结delta与证据SHA256见 [baseline.json](baseline.json)。[spec-delta-reviewed-r3.md](spec-delta-reviewed-r3.md) 冻结本次审查的原提案；[spec-delta-r4.md](spec-delta-r4.md) 为修复提案，不能当作已实现。
- 此上下文参与了前次独立复审，但未参与本次修复实现；依据源码、HTTP、实际浏览器场景和新隔离目录重新验证，没有另派agent。原执行/复审摘要不作为通过依据。
- 运行现存生成二进制（2026-10-05 16:00，SHA256=`b9d6b50d0e12c419d74945b8fe1b7be332a19fe7e358a235dd5f057f53cfb5ac`）和生成Vue，未fresh build/VM验收；缺陷均与HEAD源码对应。没有把缓存运行结果签为新构建/双端通过。
- 所有实验使用独立 `.auto/notes-r3-*` 目录，脚本仅kill自己创建的进程。旧存储升级实验复制仓库已提交的wedge-snapshot，未访问用户真实数据。

## 已修复的行为与原发现状态

| 原发现 | 本次实际改善 | 剩余 |
|---|---|---|
| F-001-01 事务并发/写者绕过 | 单后端8并发与两个实际后端进程同时写同revision均1成功/7conflict、文档合法 | 当前事务门禁采证通过；不回滚SQLite方案 |
| F-001-02 幂等/收据 | 成功create重放及即时update重放成功；COMMIT前rollback/后相同rid重放不重复 | F-R4-03/04：原收据漂移、跨目标错重放、UIrid为空 |
| F-001-03 迁移完整性 | null之后合法项可继续迁入，正常badtypes/截断fixture通过 | F-R4-02：null未报告、报告I/O失败被忽略、中文截断panic |
| F-001-04 UI条件写入 | Note含revision；双UI陈旧保存拒绝，初始冲突保留草稿 | F-R4-04：加标签又清掉冲突草稿，响应丢失不能同意图重试 |
| F-001-05 崩溃恢复 | 新SQLite确认过的正文/中文标签/稳定ID硬杀后默认重启可读，无FORCE_LOCK | F-R4-01：旧JSON确认数据升级后不可见 |
| F-001-06 路径/钩子 | ../escaped拒绝；默认setup/fault拒绝；request_id已不是路径 | F-R4-03：同rid换目标/操作/内容未验证，原T-10负例未闭合 |

## 当前验收

| AC | result | evidence |
|---|---|---|
| AC-01 | fail | 新SQLite before_crash/after_crash完全一致；但phase1_upgrade返回not_found/空列表，旧manifest/实体/committed收据完整存在 |
| AC-02 | fail | update-1原receipt.rev2，后续update-2后重放变rev3；createA的rid用于updateB仍ok=true但B未改；UI丢响应后请求id始终空，重试进入冲突；update故障点未执行 |
| AC-03 | fail | valid/null/valid→2迁入0损坏报告；报告路径不可写→saved=true且重试skip；长中文坏项HTTP断开及panic |
| AC-04 | fail | 单/双进程事务及陈旧写入拒绝pass；双UI冲突后TagAdded把未提交正文丢弃，dirty清除且Saved |
| AC-05 | pass（基本CRUD） | 全新库无seed、现有Vue18/18、battery soft-delete/restore；本通过不覆盖后续代码 |

## 发现与具体修正

### F-R4-01 — P1：已确认的旧JSON笔记升级后不可见

`repository.at:256 open_repository`只创建SQLite schema，不读旧manifest/实体/收据。能力报告把旧数据称为“仅测试数据，不自动迁移”，这不是取消AC-01的授权。复制已提交的wedge-snapshot（manifest含n-1 rev2、正文body two、d-1 committed收据）后启动新版：GET n-1=not_found，list=[]；原件还在但产品无法恢复它。

修复T-12：旧格式到SQLite的安全事务化升级，保留元数据、稳定ID、revision与收据，并备份/可重复执行；失败显式阻止空启动成功。对应AC-01/03、T-02/T-07。不能用“测试数据”标签规避旧确认数据恢复。

### F-R4-02 — P1：损坏报告漏项/写失败被忽略，中文损坏项触发panic

`migrate_legacy_at`遇null先赋reason，然后整个报告分支位于 `if reason==""` 内，导致null无报告。实测valid/null/valid→migrated=2,corrupted=[],无report文件；AC-03仍失败。

`repository.at:666–677`先设置migrated并COMMIT，之后fs_write报告且忽略结果。在报告文件位置预建目录：saved=true/corrupted包含坏项，但没有报告文件；下次skip且corrupted=[]，坏项永久丢出持久报告。

`repository.at:642`的snippet.sub(0,160)按字节截断；含较长中文的坏ID条目导致 `repository.rs:582` panic：`end byte index 160 is not a char boundary`。客户端连接断开，后面的合法条目无法迁移。[migration-unicode.log](migration-unicode.log) 是实际后端日志。salvage_objects也混用字符下标与字节sub，需一并修正。

修复T-13：损坏项完整报告、UTF-8安全截断/扫描、报告和迁移完成同可靠边界、失败可重试。对应AC-03/T-01/T-08。

### F-R4-03 — P1：请求重放不验证目标/操作/意图，原收据会被当前revision替换

`replay_in_txn`只SELECT note_id，requests.kind未校验，revision从当前文档重新计算。实测update-1提交rev2，update-2提交rev3，重放update-1得到receipt.rev3；同createA请求id拿去PUT n-2返回ok=true和A文档，B保持旧内容。通过legacy bool适配会把这当作B保存成功，丢掉新修改。

同rid换内容create也直接返回ok=true原内容，不符合T-10“同请求不同意图不得改错对象/目录”的负例契约。update流程没消费NOTES_FAULT：注入after_entity后update仍成功COMMIT，现电池只测create故障。

修复T-14：保存请求目标/类型/规范化意图、原提交revision/收据；匹配才重放，不匹配明确错误；update覆盖事务前/后故障与真重启。对应AC-02/04、T-02/T-07/T-10。

### F-R4-04 — P1：UI没有稳定请求ID，标签动作丢冲突草稿

`draft_request_id`初始化/LoadDraft时为空，后续只清空，从未为编辑分配非空id；`next_request_id`只在NewNote取局部rid。实际Save PUT两次均request_id=""，服务器每次生成新id。浏览器取证先让后端保存成功，再abort HTTP响应，原样重试不能识别原意图，只会以旧revision失败；保存内容虽然在服务器，UI仍停在未保存/冲突态。

双浏览器从同revision编辑：A保存后B正常冲突，本地正文仍在；B添加标签触发TagAdded→list_notes→LoadDraft，本地 `client-B conflict draft must survive` 被A正文替换、Save按钮消失，呈Saved。TagRemoved同路径。现Editor说明让用户“切走再切回”恢复，但所有切换遇冲突都会被阻止，没有实际恢复路径；Tag不是安全恢复入口。

补充P2观察：SelectFolder/SelectTag/ClearTag成功flush后不刷新notes，重选Shopping List会显示旧Milk正文并标Saved，服务器已有新正文；容易误导下一次编辑。[ui-results.json](ui-results.json) 冻结实际行为。

修复T-15：编辑意图稳定非空id、丢响应重试、全部动作保护草稿、双方内容可恢复、成功后刷新列表/revision。对应AC-02/04/05、T-04/T-09。

### F-R4-05 — P2（验证门阻塞）：双端验收和提交/依赖证据未闭合

T-11明确要求Vue/VM及保存冲突场景；上次pass/spec却写VM未跑、作为债务，不满足原门禁。归档时T-01/T-02/T-04未勾选、current_step=2/12，与Phase2七项已完成和“交付归档”不一致。其固定vendor gitlink仍fba6563，实际跑96f095b；若要签pass，需固定可复现依赖并重建，不能仅绑定Notes HEAD。

修复T-16：必要负例成为回归、依赖固定、修复commit重新构建、Vue/VM实际验收、逐AC与delta留证据，更新勾选/完成计数。未验不能降为不阻塞债务。对应T-11/AC-01–05。

## 检查命令与运行结果

- 完整Vue：Node Playwright CLI `test`（等价 `NOTES_URL=<隔离前端> npm --prefix tests test`），**18/18 pass**。[playwright.log](playwright.log)。没有重跑第二次完整套件；修改取证脚本后只重跑UI负例。
- 原battery：独立NOTES_TEST_MODE=1、NOTES_SEED=0实例，Git Bash执行 `bash tests/probe/run_v1_battery.sh <新隔离目录>`，**EXIT=0/fails=0**。[battery.log](battery.log)。首次本机默认GBK读UTF-8 JSON失败4项；设置PYTHONUTF8=1后通过，不记为产品回归。[battery-default-encoding.log](battery-default-encoding.log)保留首跑失败。后续脚本应显式UTF-8，门禁确实能非零失败。
- 单/双进程8请求：均1成功/7conflict，最终文档合法；[results.json](results.json)与[dual-process.json](dual-process.json)。硬杀由脚本kill自己的后端后默认重启，同一库读回中文标签/ID/revision，未用FORCE_LOCK。
- 补充API失败：[results.json](results.json)、[extra-results.json](extra-results.json)；浏览器失败：[ui-results.json](ui-results.json)、[ui.log](ui.log)。脚本退出0表示观察完成，**不是验收通过**。
- 不可打开DB路径场景create返回storage_unwritable，未观察到虚假committed；32次同时取请求id本次32个唯一，不把源码疑点当作已复现缺陷。
- 在仓根运行 `python docs/plans/evidence/001-r3-recheck-20261005/reproduce.py` 重现API观察；运行 `python .../run-playwright.py` 跑完整Vue及浏览器负例，需既有Node/Vite/Playwright。所有输出进唯一.auto目录，只关闭自己的进程。取证工具不把当前缺陷写成正确行为的测试。
- 未重新生成/编译，也未跑VM；以上为needs_fix复审，不是新构建/最终发布门通过。未改依赖、未合并/推送/推进父仓gitlink；文档/证据作为本轮独立复审提交保存，提交SHA以Git历史为准。

下一步：[计划001 Phase 3](../../001-durable-inbox.md) T-12/T-13/T-14，随后T-15/T-16。旧通过与归档记录保留，不覆盖本次needs_fix。

提交/发布状态：复审文档与证据已保存为独立本地提交（SHA以Git历史为准）；推送到 origin 的 auto-stack/auto-notes v0.6-dev 被自动审批拒绝，理由为内部文档/日志/证据的外部发布缺少材料与目的地的明确授权。未推送、未推进父仓gitlink；已有WIP保留在v0.6-dev。此为发布阻塞，不能改变needs_fix验收结论。
