# NOTES-001:r4 再次复审（客户端日期 2026-10-08）

结论：`needs_fix`，review_scope=`final`。本上下文参与前两轮复审，未参与本次实现；从提交、源码、重新构建的应用、HTTP、Vue浏览器及真实VM/MCP重新取证，未创建子agent。沿用用户原条件授权，恢复原计划为executing、修订5/Phase 4；不修产品代码、不发布canonical Spec、不合入代码。

## 绑定基线及范围

- reviewed_commit=`80770cc29ec1e4ffca47477c52820d370149069b`，实现为`c80d087`及`65e24e2`；diff base=`21c864be72ba3b77d2c6a513484227ef5d55ff83`。检出`D:/autostack/auto-os/apps/015-notes`，branch=`v0.6-dev`，按app仓约定在同一检出验证，未创建新worktree。
- 开始及结束核验均无产品源码未提交改动。预存未跟踪的r4-t12/r4-t13系列、review-r3/review-r4/review-r4-upg证据、review-s10-recovery.json和vm-min.autotest均保留、不纳入本次提交。
- AutoDown固定及实际检出均`96f095bfc41a8686331c5ccd3ce17b685147fcc1`；AutoLang main=`578794d9cc73d8b5b875617b2be3b2a5ee7634a6`，工作区干净。CLI=`auto 0.1.0+v0.4.2-2785-ga6e108f60`，CLI源码提交`a6e108f60b0c36a1ffdfea4410a3b11d81eda865`为main祖先；未冒称CLI来自main HEAD。SHA256及调用配置见[baseline.json](baseline.json)。
- Spec输入仍为r3 `docs/specs/notes/durable-inbox.md` blob `8f05b8ddb617d5d64e937e55027e782a2b0c0f85`。[spec-delta-reviewed-r4.md](spec-delta-reviewed-r4.md)冻结原提案（SHA256=e233f227cf89e406a212859738b255f345582f3aa4a1b43e681a51ad598621cd）；新[spec-delta-r5.md](spec-delta-r5.md)只是修复合同。
- `auto build -r vue --gen-only`重新生成，`cargo build -p app-015-notes-back --offline`应用级构建成功；未手改生成Rust、未跑AutoLang cargo全量。[generation.log](generation.log)、[build.log](build.log)。475项生成码警告保留，未宣称无警告构建。VM由同一CLI实际启动，使用私有MCP端口与全新seed目录。
- 初次默认沙箱拒绝loopback连接（10013），隔离测试经工具审批放行后运行成功；不是产品失败。所有实验仅使用本轮独立.auto目录或已提交样本的复制件，关闭自身创建的进程。客户端日期与日志宿主时间分别保留，不改写原日志时间。

## 通过部分与剩余验收

| 原发现 | 本次状态 |
|---|---|
| F-R4-01 旧JSON不可见 | wedge-snapshot正文/ID/revision可导入；但manifest元数据与失败边界仍失败，见F-R5-01 |
| F-R4-02 null/报告I/O/中文panic | 原三个负例已修复；新的严格类型反例失败，见F-R5-04 |
| F-R4-03 重放/故障 | 新请求的原收据rev2在rev3后重放仍rev2；跨目标及普通不同内容拒绝，update COMMIT前故障已执行；分隔符与旧行兼容仍失败，见F-R5-02 |
| F-R4-04 rid/标签丢字 | 非空稳定rid、原样丢响应重试、Tag冲突草稿和现有筛选回归通过；实际恢复与继续编辑仍失败，见F-R5-03 |
| F-R4-05 双端/依赖门 | AutoDown已固定；本次重新构建、Vue21/21、VM19/19成功；关闭记录/Spec仍未闭合，见F-R5-05 |

| AC | 结论 | 实际证据 |
|---|---|---|
| AC-01 | fail | 新SQLite中文正文/标签硬杀后默认重启一致；旧升级仍丢已保存标签、置顶、folder、回收站状态 |
| AC-02 | fail | 普通请求、故障、原收据回放pass；不同字段包含`\|`错误判同意图，旧行通配确认新操作/伪造revision；UI更改未确认意图无法保存 |
| AC-03 | fail | null/Unicode/报告I/O修复pass；boolean ID、非字符串body和tags元素不入报告，升级备份失败被忽略 |
| AC-04 | fail | 单进程/双进程8并发均1成功7冲突；Vue及VM Recover实测覆盖暂存草稿，Discard使用陈旧服务器缓存 |
| AC-05 | pass（基础CRUD） | 全新无seed、软删/restore电池、Vue/VM基本CRUD通过；旧升级状态保全失败归入AC-01 |

## F-R5-01 — P1，原要求缺口：升级读错元数据权威来源，失败仍确认完成

`repository.at:350–372`从实体文件读tags/pinned/state/folder；但已提交Phase1 `repo_set_meta`只写manifest，`load_doc`再以manifest覆盖实体元数据。见[phase1-metadata-source.txt](phase1-metadata-source.txt)（9158fd5源码摘录）。本轮复制wedge-snapshot，按该旧写入规则只修改manifest为tags=[已保存标签,important]、pinned=true、folder=saved-folder、state=trashed：升级结果tags=[]、pinned=false、folder为空、state=active，回收站条目出现在活动列表。此为旧格式有效状态反例，不是声称在旧程序内真实执行了元数据写入或写入中硬杀。

备份位置预建普通文件：三次fs_copy结果均忽略，仍导入成功、没有目录备份。唯一确认实体缺失：记录corrupted_r1后仍upgraded=1、loaded=true/err为空，并允许创建新笔记；修复旧实体后也被upgraded标记阻止重试。合法JSON但manifest={}同样空成功。T-12要求失败结构化错误和安全重试，不能只将坏项藏在meta后宣告完成。[deep-results.json](deep-results.json)的upgrade_*字段冻结观察。

修正T-17：按旧load_doc规则合并manifest权威元数据，校验旧布局/实体/路径与备份结果，明确损坏/不完整升级的完成和重试边界，保持源副本。已有SQLite与旧树并存或标记已误写的恢复需有明确策略，不静默忽略。对应AC-01/03/05、T-12/T-02/T-07。

## F-R5-02 — P1，原要求缺口：意图编码歧义、旧请求通配确认

`repository.at:462/523`以`|`直接拼任意title/body。实测同rid更新title=`a|b`,body=`c`成功；改为title=`a`,body=`b|c`仍ok=true/replayed=true，返回旧字段，第二意图没有执行。应明确request_conflict，不能假确认。[deep-results.json](deep-results.json) delimiter_intent。

`replay_in_txn:938–955`以空kind/intent通配，rev=0回退1：旧JSON的更新收据d-2复用于新create仍ok=true，未创建新笔记；模拟r3三列requests表，原update收据rev2重放变rev1，且不同正文仍成功。模拟表结构与r3一致，未冒称重新运行旧二进制。新v2普通请求回放已修复，这些兼容路径不能继承通过。

修正T-18：使用无歧义规范表示，迁移现有v2意图数据；旧行必须先有界调查能否从旧journal/收据/快照还原类型、原revision与意图。信息不足不得通配确认新操作或编造收据；若无法保持原兼容承诺，提交具体needs_replan提案，不能自行削弱AC。对应AC-02/04、T-14/T-07/T-10。

## F-R5-03 — P1，原要求缺口：恢复覆盖自己，Discard陈旧，更改未确认意图卡死

`notes_store.at:245–270 RecoverDraft`在current dirty时先StashDraft，覆盖将要读取的旧rec_*。Vue：Welcome失败草稿暂存→Shopping List继续输入→Recover，展示的还是新的Shopping草稿，原Welcome草稿不在服务器也不在恢复槽，has_recovery=false。VM同场景实际MCP状态：rec_title由`VM precious recovery draft`变为`VM new shopping draft`，draft也为后者，has_recovery=false。见[ui-deep-results.json](ui-deep-results.json)、[vm-negative-result.json](vm-negative-result.json)。多次冲突导航的单槽无保护覆盖同样需由T-19检查，不能以“单槽设计”取消双方可恢复。

`DiscardDraft:278–283`只LoadDraft不刷新列表。Vue/VM都在另一写者保存后Discard，仍展示旧内容/旧revision并标Saved，而服务器已有新版本；这不是实际选择最新服务器版本。

EditTitle/EditBody更改内容后沿用已分配rid。Vue先让服务端COMMIT再abort响应，随后修改正文保存两次：三个请求相同rid/expected_revision，后两次内容变了，服务器仍是第一个意图，Save一直可见。原样重试通过；本反例验证T-15明确要求的“变更内容需明确新意图”。仅换rid也不足，必须裁决未确认旧提交并恢复正确revision，且保留新草稿。

修正T-19：恢复时保护两份草稿和已有恢复槽，Discard刷新最新服务器版本，区分未确认提交与后续新意图，做Vue/VM失败场景回归。对应AC-02/04/05、T-15/T-04/T-09。

## F-R5-04 — P2，原要求缺口：严格迁移类型仍未满足

`migrate_legacy_at:798–839`仅排除引号和小数点，boolean true作为SQL字面量导入为legacy_id=1/note_id=n-true；legacy整数接口无法按n-1访问此条目。非字符串body={text:...}被静默转为空正文，tags=[7,null]转为空字符串数组；全部migrated=2/corrupted=[]，未报告坏项。对应T-13的严格整数/标题/标签类型、T-08错类型报告及AC-03。

修正T-20：完整类型验证，坏项逐项报告、不以默认值抹掉源内容，后续合法项继续；snippet保持声明的字符串契约。现snip存原JSON对象、API CorruptItem.snippet as_string后空，作为同路径诊断合同问题一并处理，不另冒称panic回归。

## F-R5-05 — P2，关闭记录缺口：交付归档却未沉淀规范/闭合计数

归档frontmatter current_step=8/17，实际checked=9；T-01/02/04及T-07–11仍未关闭，§0/5/8仍称Phase3未执行/4/17/executing。docs/README还链接不存在的活动计划。规范仍r3（三列requests、报告COMMIT后写、无恢复槽），归档收据将SD-07–11沉淀延到“下批或后续计划”，没有完成原T-16和交付关闭门。

修正T-21工作阶段准备与已验实现一致的Spec diff及回归证据，review验证；merge-owned closeout实际发布canonical Spec、索引及准确计数后才归档。实现正确性不能推迟到merge。原通过/归档记录保留，不修改canonical以制造通过。

## 命令、边界与重现

- Vue完整21/21（含原负例3项），[playwright.log](playwright.log)；VM原19/19，使用`auto run -r vm -B <私有端口>`和`python tests/run_autotest.py 015-notes.autotest --mode vm --url http://127.0.0.1:<MCP>/mcp`，见[vm-suite.log](vm-suite.log)及实际配置JSON。
- 当前battery S0–S14，EXIT=0/fails=0，[battery.log](battery.log)。单/双进程并发1/7成功，两个进程128次request_id本次全部唯一，不把源码序列疑点记为已复现缺陷。
- 原样响应丢失重试和Tag草稿保护通过；旧ui脚本folderFlush未等待异步SelectNote完成，观察不能作为新的筛选失败证据，采用现有R4-3断言通过结果。完整套件只跑一次；补充UI/VM仅验证未覆盖分支。VM启动重新生成后端、二进制SHA变化后，再复核API成功/失败路径，结果一致；initial JSON保留首轮，主JSON为最终后端复核。首轮API工具继承的runtime_note“no fresh build”是旧模板，实际此前已在独立构建步骤完成重新生成/构建，不能以该模板字段否认build.log，也不据此宣称脚本自行构建。
- 仓根运行本目录`api-reproduce.py`、`deep-reproduce.py`、`run-ui-deep.py`、`run-vm.py`、`run-vm-negative.py`、`run-battery.py`重现；预置Node/Vite/Playwright/requests及CLI路径在脚本中记录。脚本退出0表示观察完成，不等于所有AC通过。
- 进程kill后恢复测试真实执行，但没有声称硬件掉电保证。未覆盖全部笛卡尔组合；已检查默认/seed、旧JSON/旧SQLite/新请求、正常/故障/缺实体/备份失败、单/双进程、Vue/VM、空闲/dirty恢复/未确认提交等关键状态。
- 证据和方案保存为独立本地文档提交，Git SHA以历史为准。此前外部推送自动审批拒绝仍未获得材料/目的地授权，本轮不重试、不发布、不推进父仓gitlink；原用户WIP保留。

下一步：[计划001 Phase 4](../../001-durable-inbox.md) T-17/T-18/T-20，然后T-19/T-21；闭合后再进行独立final review。
