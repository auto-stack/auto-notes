# durable-inbox — 015-notes 可靠收件箱（current-state）

> 状态：current-state（NOTES-001 r9 实施，SD-02..SD-06 与 SD-07..SD-28 随
> r4–r9 修复落地；NOTES-004 补当前工具链双端再验）· 更新：2026-11-02 ·
> 计划：NOTES-001 + AutoLang 742 + NOTES-004

## 存储契约（SQLite 单文件）

- 存储：`<data>/inbox.db`（SQLite，a2r-std `sqlite` 模块；WAL + busy_timeout=3000）
  - `notes(note_id PK, legacy_id UNIQUE, revision, title, body, tags_json, color,
    pinned, state, folder, seq, created_at, updated_at)`
  - `requests(request_id PK, note_id, kind, rev, doc_json, intent)` — schema v3
  - `meta(k, v)`：counter、req_seq、seeded、migrated、schema_v、upgraded、
    upgrade_error、corrupted_r1、repair_generation
- 文档 JSON（NoteDocument v1）：13 列固定序投影，`pinned` 为 JSON boolean
- 旧格式隔离：`<data>/legacy-backup/`；损坏报告 `<data>/corrupted/report-r1.json`；
  迁移备份 `<data>/backup/notes.json.bak`
- 数据目录：`NOTES_DATA_DIR` 覆盖 → %APPDATA%/XDG/`~/.local/share` +
  `/auto-notes/data`；每次解析即 `mkdir_all` 兜底

## 提交协议（事务串行化 + 规范化意图）

- 所有写入同一门禁：`BEGIN IMMEDIATE` → 幂等重放（事务内查 requests）→
  revision 检查 → 写 notes + requests → `COMMIT`；跨进程 `second_writer`。
- 请求意图规范化（`v2c|` 前缀）：kind/目标/期望修订/每个内容字段独立 JSON
  编码后拼接——字段边界无歧义。
- 幂等重放先于 revision 检查：intent 完全匹配 → 返回存储的原收据与文档快照
  （`replayed:true`）；任何差异 → `request_conflict`。
- 旧行裁决（决策 A，2026-10-12 用户批准）：intent 为空的行（Phase 1 收据、
  v1 三列行、残缺 v2 行）重放一律 `request_conflict`——旧持久层不含意图内容，
  "完全同意图"不可证明；原收据经 read_receipt 可查询，旧对象不受影响。
  r4 管道行经 v2→v3 从 doc 快照确定性重导。
- 条件更新：expected_revision ≠ 当前 → `revision_conflict`；8 并发同 revision
  恰好 1 成功。
- **(r8) 元数据/删除/恢复写入**：state/pinned/tags/folder 的必需 UPDATE 在
  同一事务内逐一检查结果——RAISE(ABORT) 类存储拒绝只中止单条语句，不检查
  返回值会让后续 COMMIT 把失败冒充成成功。任一失败 → ROLLBACK +
  `ok:false storage_unwritable`；UI 侧不得刷新工作集/清草稿，置
  conflict+action_error 并显示失败横幅（删除/置顶/标签/恢复全入口）。
- 故障点（NOTES_TEST_MODE=1 门禁内）：`after_entity`=COMMIT 前 ROLLBACK；
  `after_manifest`=COMMIT 后报 `fault_injected`。
- 软删 = state=trashed；restore 反转。

## Phase 1 JSON 布局升级（SD-07/SD-12/SD-17/SD-18/SD-23/SD-24，**(r9) 收尾原子性**）

- 入口裁决（升级状态机）：
  * 修复凭据唯一来源 = `meta.corrupted_r1` 含 "legacy upgrade"（r4 缺陷库
    标记）；`upgrade_error` 永不授予合并资格——冲突/普通 I/O 错误在前提消失前
    原样复现（重复读取/重启不得绕过，混合库恒 `upgrade_conflict`）。
  * 未升级 + 旧树在 + 库内已有 notes → `upgrade_conflict`（恒定）。
  * 未升级 + 旧树在 + 库空 → 全新升级（备份先行并校验；备份目录被普通文件
    占据/拷贝失败/备份 manifest 缺失 → `storage_unwritable` 不完成）。
  * 已升级 + 凭据在 + 旧树在 → 修复合并：manifest 引用实体逐一共同验证后，
    行缺失（r4 跳过的坏实体）→ 补导；行与实体导入产物可证明一致
    （revision/title/body 全等）→ 回收 manifest 权威元数据；更高修订/同修订
    异文 → 跳过保护。**修复合并的所有必需写入（行 UPDATE/INSERT、凭据清理、
    代际记录、收据导入）逐一检查结果：任一失败 → ROLLBACK + 显式 upgrade_error，
    凭据保留可重试；成功标志只跟随整个修复成功**（SQL 拒绝合成实验验证，
    不冒称物理掉电）。
  * 已升级 + 凭据在 + 旧树不在 → 清凭据记代际，不再重导；**(r9) 清凭据与写
    代际在同一写者事务（BEGIN IMMEDIATE…COMMIT）内完成：任一写入失败 →
    ROLLBACK、凭据保留、显式 `storage_unwritable`，恢复后重试真正完成——
    不再出现"凭据已删而代际缺失"的不可重试中间态**。
  * **(r8) 未升级 + 旧树不在（全新库）→ upgraded 完成标记写入失败显式
    `storage_unwritable`，不得静默放行。**
- **(r8) 完成事务必需写入**：fresh 升级的 finalize（upgraded 标记、清
  upgrade_error、清 corrupted_r1 凭据）与两路 counter 导入，逐一检查——
  任一失败 → ROLLBACK + upgrade_error，旧树与库均保持可重试，绝不出現
  「笔记已入库但无完成标记、后续读取被 upgrade_conflict 挡死」的假完成。
- 权威清单与实体共同验证（合并前，两路共用）：实体——note_id 非空且与 entry
  一致、legacy_id/revision 严格整数字面量、title/blocks(每块 text)/tags(每元素)/
  folder/state 类型、pinned 布尔；manifest entry——note_id/legacy_id 为字符串、
  revision/seq/legacy_id 整数或**历史合法十进制字符串**（布尔/含杂字符如
  "2oops" 拒绝）、tags 数组且元素字符串、folder/state 字符串、pinned 布尔、
  file 路径无分隔符/穿越；**entry 与实体 note_id/legacy_id 双向一致**，不一致
  不导入错映射。任一违反 → ROLLBACK + 显式 upgrade_error，不标完成，修正后
  可重试；manifest-only 权威元数据与旧实体正文继续保留。
- 元数据权威与旧 load_doc 一致：实体提供 title/body(blocks→换行)/color/时间戳；
  manifest entry 覆盖 tags/pinned/state/folder/revision/seq/legacy_id。trashed
  行不进活动列表。升级错误经 `/api/v1/status` 的 `upgrade_error` 显式可见。
- receipts → requests：只导入 committed；kind 按 rev 规则恢复；intent 留空。

## 迁移（notes.json 数组，SD-04/SD-15，**(r8) 完成标记边界**）

- 门禁内逐项校验；进 `corrupted`（index/reason/snippet）且后续合法项继续：
  null；缺 id；id 非严格整数字面量；源内重复 id；title 非 string；body 存在但
  非 string（缺省容忍 ""）；tags 非数组或元素含非字符串；folder 非 string；
  pinned 非 boolean。snippet 恒 JSON 字符串（>400 省略内容）。
- 非法 JSON 顶层：最短有效跨度打捞器（字符索引 + 字节偏移同步，Unicode 安全）。
- 报告与 meta 先于 COMMIT；报告写失败 → ROLLBACK 可重试；重跑 skipped_existing
  幂等；原件只读 + backup。
- **(r8) `migrated`/`corrupted_r1` 完成标记写失败 → ROLLBACK + saved=false
  显式失败**——saved=true 而标记缺失会让重跑失去幂等判据重复迁移。

## UI/legacy 契约（SD-05/SD-10/SD-14/SD-19/SD-20/SD-25/SD-26/SD-27）

- Note 视图携带 revision；`PUT /api/notes/:id` 条件更新 → bool；
  `PUT|GET /api/notes/:id/result` 返回结构化 RepoResult。
- **(r9) pin/tag 动作失败信封**：UI 的置顶/标签写入走
  `PATCH /api/notes/:id/pin/result`、`POST /api/notes/:id/tags/result`
  （RepoResult）——`?Note` None 的 HTTP 404 在生成客户端直接抛异常、
  调用点错误分支不可达，故旧 `?Note` 端点仅保留兼容、不再被 UI 使用。
  存储拒绝 → HTTP 200 + `ok:false`（err_code 可见、对象不变）；UI 失败分支
  置 conflict+action_error、不刷新工作集/不清草稿。
- **(r8) JSON public face 严格读取（T-34）**：布尔一律与 `true` 比较、JSON 根
  经 `json.parse` 的 null sentinel 校验——兼容 AutoLang v0.6 候选的严格 JSON
  ABI，不扩大公开 API。
- 草稿会话意图：rid 于保存点分配并立即绑定意图快照（BindIntent）；保存与
  全部自动 flush 使用一致的意图轮换与服务器裁决。
- **(r9) 正文确认即同步版本**：TagAdded/TagRemoved 的 flush 成功块在清
  dirty/rid/意图链同时以返回 doc.revision 刷新 `draft_revision`——后续元数据
  动作失败不得让草稿携带旧 revision 自我冲突（无外部写者也成立）。
- **未确认提交链**（容量 2）：轮换时旧意图快照移入 prev2（不丢失仍可能已
  落地的祖先）；裁决按链逐个与服务器当前版本对比——匹配任一链节 ⇒ 该提交
  已落地，采用服务器 revision 重试当前草稿（保留新内容）；均不匹配（真实
  外部修改）⇒ 双方版本保留。传输层未知结果不裁决（快照已记，下次保存裁决）。
  链上下文（pend/prev/prev2）随恢复槽 stash/restore 完整搬运。
- **稳定动作目标**：点击导航在 flush 前捕获目标笔记 id，成功刷新/重排后按 id
  重新定位（找不到回落首可见行）；**(r8) 重定位结果不得被点击时的旧下标覆盖
  ——只有未发生刷新重载时旧下标才合法；LoadDraft 带下标上界兜底钳位，越界
  不解引用**；保存成功分支刷新 notes 再 LoadDraft ⇒ 草稿 revision 与服务器
  一致，连续保存不被自身旧 revision 拒绝。pin/tag/delete 绑定当前草稿身份
  （draft_id，pin 目标在 flush 前捕获）——目标不在当前筛选工作集时动作仍指向
  草稿身份，绝不作用到其他可见行。
- **(r9) 陈旧失败状态不阻断新动作**：干净草稿（dirty=false）上的
  conflict/action_error 是上一条动作残留；pin/tag 动作入口清除后正常执行，
  失败横幅对应当前动作。dirty 草稿的 flush 冲突仍阻止动作（草稿保护不变）。
- **恢复槽双槽（容量 2，无驱逐）**：全入口容量保全——Stash 入空闲槽；两槽
  全满 → 显式阻止（stash_blocked 可见状态 + 编辑器横幅），**被阻止动作的
  查询词/筛选/选择/工作集与草稿全部原位不变**，不做任何后续副作用；导航
  handler 保持原位不清 dirty。Recover 双入口对称检查。用户 Dismiss 释放后
  继续。
- Discard = 显式选择服务器版本：先刷新工作集再按 draft_id 装载最新版。
- 只有 durable 成功后才清 dirty/切草稿/显示 Saved；`.notes` 刷新仅在成功
  分支（VM 渲染序约束）。
- **(r8) 动作失败接收**：删除/置顶/标签/恢复的存储拒绝（非 revision 冲突）
  置 conflict+action_error，不刷新工作集/不清草稿；编辑器显示
  "Action failed: change not saved"（独立于 dirty 的冲突分支）。
- 自动 request_id 使用专用 req_seq 计数器。

## 标识与测试入口（SD-06/SD-28）

- request_id 校验：非空、≤100 字符、仅 `[A-Za-z0-9._:-]` → 否则 invalid_request。
- 变更型测试端点默认关闭（test-mode-disabled）；电池在门禁未开启时立即退出 1。
- **验证注入可靠性**：fixture/setup 类注入走独立脚本（写入后读回校验，
  失败非零），battery 调用点失败即 fail；注入故障自检钩子（INJECT_CONTROL）
  验证传播路径。**(r8) 合成 SQL trigger 的挂载/摘除同样 `|| fail`（S20/S21/S22）。**

## 端点面

- legacy：GET/POST `/api/notes`、GET/PUT/DELETE `/api/notes/:id`、
  PUT/GET `/api/notes/:id/result`、PATCH `:id/pin`、PUT `:id/tags`、
  **(r9) PATCH `:id/pin/result`、POST `:id/tags/result`（RepoResult 信封——
  UI 动作失败通道）**、GET `/api/notes/search`、GET `/api/request-id`。
  **(r8) 写入端点在存储拒绝时返回非成功形状**（pin/tags 的 `?Note` None →
  404 空体——**(r9) 该形状即 UI 弃用旧端点的原因**；DELETE → `false`；
  v1 信封 → `ok:false`+err_code）。
- v1：`/api/v1/notes[...]`、`/api/v1/migrate`、`/api/v1/status`（含 upgrade_error）、
  `/api/v1/test/{setup,fault}`（门禁内）。
- 错误码：not_found | revision_conflict | request_conflict | upgrade_conflict |
  upgrade_incomplete | storage_unwritable | second_writer | invalid_request |
  fault_injected | test-mode-disabled。
- SQL 字面量一律 `sql_str()`；动态错误消息在 .at 层拼接后内插；`db.exec`
  成功判定 `< 0`；字符串与引号字符比较用 `"\""` 转义形式（单引号字面量在
  比较上下文被发射为 char——实证）。

## 回归资产（r9）

- 电池 S0–S22（S20 元数据/删除/恢复失败传播+控制；S21 fresh finalize 回滚+
  控制；**S22 pin/tag /result 端点 200 信封协议负例+控制**；S15/S16/S17/S18/S19
  既有；注入 INJECT_CONTROL 非零自检）+ 挂载/摘除 `|| fail`。
- 后端 scratch 52 断言（U11 元数据失败传播 9、U12 升级 finalize 回滚 2、
  **U13 no-legacy 收尾原子性 3**、原 U1–U10/R1–R3/M1）。
- 独立反例资产：r6-recheck independent-api（5 断言）+ independent-ui（4 场景）
  + r7-work VM 驱动（11 断言）+ 复审原输入复跑（api-extra 4/4、navigation
  pass、**r9-recheck api-probes/ui-probes 转绿**）——全部 exit 0。
- Vue：smoke + negatives-r4 + negatives-r5 + negatives-r8 + **negatives-r9
  （R9-1 pin 200 信封；R9-2/R9-3 tag add/remove 后 revision 同步；R9-4 掩盖
  检查；R9-5 正常对照）= 31 项**。VM：015-notes.autotest（19 场景）+ r5 负例
  （13 项）+ r7 负例（11 断言）。
- 测试基建：wait_ready 要求 draft_title 非空；驱动点击用"点击至状态生效"
  重试（重渲染 vnode 换代）；VM 驱动 boot 等待 ≥600s（taskkill 后共享 target
  冷重编窗口）。
- 依赖固定（NOTES-004 再验工具链）：AutoDown c39ac7f9（pin=实际）；CLI
  `0.1.0+plan-890-verified-r7-t19-14-g47d8f7b`（auto-man 47d8f7b）+ auto-ui-tool
  （2026-11-02 重建）。**当前工具链双端再验（NOTES-004）**：battery S0–S22
  fails=0、后端 scratch 52 断言 fails=0、Vue 31/31 passed、原生
  015-notes.autotest 19/19 exit 0（当前 CLI 原生首启 176s MCP 就绪）、r7 VM
  反例 11/11 fails=0、双端 N-04 强杀重启后下一次真实编辑 rev 推进（SQLite 只读
  核实）——提交协议/幂等/revision/错误码/UI 契约零改动（证据：004 决策稿
  与聚合门记录）。

## 已登记债务

- D-742-1：`use api: Note` 跨模块解析 'undefined'——映射留在 api.at 绕开。
- 时间戳恒空串（无时钟原语），排序/版本用 seq/revision。
- 恢复槽容量 2：满槽显式阻止 + 用户释放；更大容量/持久化恢复集合留待后续。
- 未知意图链容量 2（pend+prev+prev2）：连续 3 次以上未知响应的场景退化为
  冲突保全（双方版本可读，需 Discard/手动处理）；更长链留待后续需求。
- VM 渲染序：flush 冲突路径禁止紧跟 `.notes` 整表赋值（实证破坏列表渲染）；
  MCP 点击在重渲染后可能落在旧 vnode（驱动用重试规避）——框架层根因留
  AutoLang 侧排查。
- **(r8) `auto run` 不把调用方 env 传入其后端子进程**（dev 后端落到自有临时
  数据目录）——门禁一律用直接 exe + env 或门禁驱动（run_vue_suite 等）；
  框架行为留 AutoLang 侧排查。
- **(r9) r8 工具链二进制未持久化**：r8 记录的 CLI（e849e06f9-dirty）随
  auto-lang target 清理丢失；本轮以同提交干净重建补齐。工具链二进制的持久
  保存留 AutoLang 分发侧（Plan 816 安装包线）解决。
