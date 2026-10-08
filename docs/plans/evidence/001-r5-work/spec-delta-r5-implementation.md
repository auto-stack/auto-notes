# Spec delta r5 — 实现绑定稿（SD-07..SD-16 → 已验实现）

> 状态：**work 阶段提案，未发布**。canonical `docs/specs/notes/durable-inbox.md`
> 仍为 r3（blob 8f05b8ddb617d5d64e937e55027e782a2b0c0f85）。本稿供 independent
> review 对照已验实现验证；merge 阶段以下文【提案全文】整体替换 canonical 并
> 刷新索引/计数（F-R5-05 / SD-16 关闭门）。
> 输入合同：evidence/001-r4-recheck-20261008/spec-delta-r5.md（SD-12..16 冻结稿，
> SHA256=091e81c1…）；SD-07..11 载于 001-r3-recheck-20261005/spec-delta-r4.md。

## SD → 实现绑定表

| delta | 规则变更 | 实现位置 | 验证 |
|---|---|---|---|
| SD-07 (r4) | Phase 1 JSON → SQLite 升级，manifest 权威元数据完整迁入 | `repository.at: upgrade_if_legacy`（r5 重写：实体打底 + manifest entry 覆盖 tags/pinned/state/folder/revision/seq/legacy_id，与旧 load_doc 规则一致） | battery S15；scratch U1/U2 |
| SD-08 (r4) | 迁移逐项损坏报告、Unicode 安全、报告可靠保存后才确认 | `migrate_legacy_at`（r3 已落地）；r5 补严格类型与 snippet 契约（SD-15） | battery S2/S3/S14/S18 |
| SD-09 (r4) | 持久请求意图/目标/原收据；同rid异图拒绝 | `requests` schema v2（rev/doc_json/intent）+ r5 `v2c|` 规范编码 + `replay_in_txn` 重写 | battery S6/S12/S13/S17 |
| SD-10 (r4) | 草稿意图稳定 rid、动作保护草稿、恢复路径 | `notes_store.at`（r4 T-15）；r5 双槽扩展（SD-14） | Vue R4-1/2/3；VM 套件 |
| SD-11 (r4) | 双端/固定依赖复验后才可声明通过 | 重新生成+构建+Vue/VM/battery 全套（本轮证据） | run_vue_suite / run_vm_suite / battery 日志 |
| SD-12 (r5) | 升级失败边界：备份/实体/布局校验、误写 upgraded 恢复、并存冲突显式 | `upgrade_if_legacy`：备份校验（mkdir/copy/存在性）、manifest entries 严格、实体缺失→`upgrade_incomplete` 可重试、`upgrade_conflict`、修复入口（upgrade_error/legacy corrupted_r1 在案即重跑合并） | battery S15/S16；scratch U3/U4/U5/U6/U8 |
| SD-13 (r5) | 意图无歧义规范表示 + 版本化迁移 + 旧行不虚假确认/不编造收据 | `canonical_*_intent`、`migrate_request_intents`（schema v3）、`replay_in_txn` 旧行一律 request_conflict；决策制品 [t18-legacy-request-adjudication.md](t18-legacy-request-adjudication.md) | battery S17；scratch R1/R2/R3 |
| SD-14 (r5) | 双恢复槽、Discard 取最新服务器版、未确认提交裁决 | `notes_store.at`：StashDraft/RecoverDraft(+2)/DiscardRecovery(+2)、DiscardDraft 刷新、BindIntent/prev 快照 + revision_conflict/request_conflict 裁决；`update_note_r`/`get_note_r` 端点 | Vue negatives-r5（R5-1/2/3）；VM r5 负例 13 项 |
| SD-15 (r5) | 迁移严格类型 + snippet 字符串契约 | `migrate_legacy_at`：is_int_literal（拒绝 bool/字符串/小数 id）、body/tags元素/folder/pinned 类型校验、snippet 恒 json.encode 字符串 | battery S18；scratch M1 |
| SD-16 (r5) | work 备实际 Spec diff、review 验证、merge 发布并闭合索引/计数 | 本文件即 diff；发布由 merge 执行 | 本表 + 复审 |

## 【提案全文】merge 时整体替换 docs/specs/notes/durable-inbox.md

```markdown
# durable-inbox — 015-notes 可靠收件箱（current-state）

> 状态：current-state（NOTES-001 r5 实施，SD-02..SD-06 已落地；SD-07..SD-16 随
> r4/r5 修复落地）· 更新：2026-10-08 · 计划：NOTES-001 + AutoLang 742

## 存储契约（SQLite 单文件）

- 存储：`<data>/inbox.db`（SQLite，a2r-std `sqlite` 模块；WAL + busy_timeout=3000）
  - `notes(note_id PK, legacy_id UNIQUE, revision, title, body, tags_json, color,
    pinned, state, folder, seq, created_at, updated_at)`
  - `requests(request_id PK, note_id, kind, rev, doc_json, intent)` — schema v3：
    rev = 提交时收据修订；doc_json = 提交时文档快照（历史收据不随后续变更漂移）；
    intent = 规范化意图串（`v2c|` 前缀，见提交协议）
  - `meta(k, v)`：counter、req_seq、seeded、migrated、schema_v、upgraded、
    upgrade_error、corrupted_r1
- 文档 JSON（NoteDocument v1）：13 列固定序投影，`pinned` 为 JSON boolean；
  正文为单 `body` 文本
- 旧格式隔离：`<data>/legacy-backup/`（Phase 1 JSON 树整体备份，原件不动）；
  损坏报告 `<data>/corrupted/report-r1.json`；迁移备份 `<data>/backup/notes.json.bak`
- 数据目录解析：`NOTES_DATA_DIR` 覆盖 → %APPDATA%/XDG/`~/.local/share` +
  `/auto-notes/data`；每次解析即 `mkdir_all` 兜底

## 提交协议（事务串行化 + 规范化意图）

- 所有写入走同一门禁：`BEGIN IMMEDIATE` → 幂等重放（事务内查 requests）→
  revision 检查 → 写 notes + requests → `COMMIT`；跨进程 `second_writer`。
- 请求意图规范化（`v2c|` 前缀）：kind/目标/期望修订/每个内容字段独立 JSON
  编码后拼接——字段边界无歧义，`title="a|b",body="c"` 与 `title="a",body="b|c"`
  必为不同意图（F-R5-02 修复）。
- 幂等重放先于 revision 检查：requests 命中且 kind/目标/意图完全一致 → 返回
  **存储的原收据与文档快照**（`replayed:true`；update-1 rev2 → update-2 rev3 →
  重放 update-1 仍 rev2）。同 rid 不同操作/目标/内容 → `request_conflict`。
- **旧行裁决（SD-13）**：intent 为空的行（升级导入的旧收据、v1 三列行）不可
  验证原始意图——重放一律 `request_conflict`，不通配确认、不编造 rev1 收据；
  原收据经 read_receipt 仍可查询，旧对象不受影响。r4 管道行经 schema v2→v3
  迁移从 doc 快照确定性重导（决策制品：t18-legacy-request-adjudication.md）。
- 条件更新：expected_revision ≠ 当前 → `revision_conflict`（附 current_revision）；
  8 并发同 revision 恰好 1 成功。
- 故障点（NOTES_TEST_MODE=1 门禁内注入）：`after_entity` = COMMIT 前 ROLLBACK；
  `after_manifest` = COMMIT 后报 `fault_injected`（已持久，重放裁决）。
- 软删 = state=trashed（行不动）；restore 反转。

## Phase 1 JSON 布局升级（SD-07/SD-12）

- 触发：notes 空且未升级时探测 `<data>/manifest.json`；备份先行且必须校验
  （legacy-backup 被普通文件占据/拷贝失败/备份 manifest 缺失 → `storage_unwritable`，
  不完成）。
- 元数据权威与旧 load_doc 一致：实体提供 title/body(blocks→换行连接)/color/
  时间戳；manifest entry 覆盖 tags/pinned/state/folder/revision/seq/legacy_id
  （旧 repo_set_meta 只写 manifest）。trashed 行不进活动列表。
- 失败边界（不空成功、可重试）：manifest 不可读或缺 entries 数组（含 `{}`）→
  显式错误；manifest 引用实体缺失/不可读 → ROLLBACK + `upgrade_incomplete`
  （修复实体后重试成功）；成功才在事务内置 upgraded；重启/重跑幂等（合并式
  导入对已存在行做权威元数据回收）。
- 修复入口：upgrade_error 在案或 legacy-upgrade corrupted_r1 残留（r4 缺陷库
  误写 upgraded）→ 清标记按正确规则重跑。未升级库已有 notes 且旧树并存 →
  `upgrade_conflict`，不静默忽略任一侧。升级错误经 `/api/v1/status` 的
  `upgrade_error` 字段显式可见。
- receipts/journal → requests：只导入 status=committed 收据；kind 按旧协议规则
  恢复（create=rev1 / update=rev≥2）；intent 留空（不可验证旧行，见提交协议）。

## 迁移（notes.json 数组，SD-04/SD-15）

- `BEGIN IMMEDIATE` 门禁内逐项校验；以下均逐项进 `corrupted`（index/reason/
  snippet）且后续合法项继续打捞：null 项；缺 id；id 非严格整数字面量（布尔
  true/false、字符串、小数一律拒绝——SQL TRUE→1 的静默转换已消除）；源内
  重复 id；title 非 string；body 存在但非 string（缺省容忍为 ""）；tags 存在
  但非数组或元素含非字符串；folder 存在但非 string；pinned 存在但非 boolean。
- snippet 恒为 JSON 字符串（诊断文本经 json.encode；>400 字符省略内容），
  API CorruptItem.snippet 契约成立。
- 非法 JSON 顶层：最短有效跨度打捞器（字符索引 + char_w 字节偏移同步，
  长 Unicode 安全）。
- 报告与 meta 先于 COMMIT；报告写失败 → ROLLBACK 可重试，绝不 saved=true 丢
  报告；meta.migrated + 已有数据 → 重跑 skipped_existing（幂等）；原件只读 +
  `backup/notes.json.bak`。

## UI/legacy 契约（SD-05/SD-10/SD-14）

- Note 视图携带 revision；读取时保存，提交时回传；`PUT /api/notes/:id` 为条件
  更新 → durable-bool。
- `PUT /api/notes/:id/result`（update_note_r）返回结构化 RepoResult：UI 按
  err_code 区分「明确拒绝」（revision_conflict/request_conflict——未执行）与
  「传输层未知」（err_code 空——可能已提交）。
- 草稿会话意图：rid 于保存点分配并**立即绑定意图快照**（BindIntent：内容 +
  基线修订）；保存失败后内容变更再保存 → 轮换新 rid，旧意图快照转入 prev；
  内容未变 → 原 rid 原样重试（服务端重放幂等）。
- 未确认提交裁决：保存被 revision_conflict/request_conflict 明确拒绝且存在
  prev 时，取服务器当前版本（`GET /api/notes/:id/result`）对比 prev——一致
  ⇒ 旧提交已落地，采用服务器 revision 为新意图基线重试（保留新草稿）；
  不一致 ⇒ 双方版本保留（冲突横幅 + Discard）。
- 双恢复槽（容量 2，保最旧）：冲突导航将失败草稿入空闲槽；Recover 先把当前
  dirty 草稿保全到另一槽再装载目标槽（绝不自我覆盖）；两份内容同时可恢复
  （第二槽独立横幅 Recover/Dismiss）；三份并存超出容量时显式不动作。
- Discard = 显式选择服务器版本：先刷新工作集（list/search）再按 draft_id
  装载最新版，不用陈旧列表冒充。
- 所有动作（标签/置顶/筛选/切换/搜索/新建）在 flush 失败/冲突时绝不清
  draft/dirty；只有 durable 成功后才清 dirty/切草稿/显示 Saved。
- 自动 request_id 使用专用 req_seq 计数器，绝不复用笔记 seq。

## 标识与测试入口（SD-06）

- request_id 校验：非空、≤100 字符、仅 `[A-Za-z0-9._:-]` → 否则 invalid_request。
- 变更型测试端点（/api/v1/test/setup|fault）默认关闭（test-mode-disabled），
  仅 NOTES_TEST_MODE=1 显式隔离模式可用；电池在门禁未开启时立即退出 1。

## 端点面

- legacy：GET/POST `/api/notes`、GET/PUT/DELETE `/api/notes/:id`、
  PUT `/api/notes/:id/result`（update_note_r）、GET `/api/notes/:id/result`
  （get_note_r）、PATCH `:id/pin`、PUT `:id/tags`、GET `/api/notes/search`、
  GET `/api/request-id`。
- v1（采证/测试面）：`/api/v1/notes[...]`（RepoResult）、`/api/v1/migrate`、
  `/api/v1/status`（含 upgrade_error）、`/api/v1/test/{setup,fault}`（门禁内）。
- 错误码：not_found | revision_conflict | request_conflict | upgrade_conflict |
  upgrade_incomplete | storage_unwritable | second_writer | invalid_request |
  fault_injected | test-mode-disabled。
- SQL 字符串字面量一律 `sql_str()`（DQS=0）；`db.exec` 成功判定用 `< 0`；
  错误消息含动态值时在 .at 层拼接后再经 sql_str 内插（SQL 内 `+` 拼接在
  SQLite 是数值加法且缺列即静默失败——已实证并修复）。

## 回归资产（r5）

- 电池 `tests/probe/run_v1_battery.sh`：S0–S18（含 S15 升级权威/旧行裁决/
  误写恢复、S16 升级失败边界、S17 意图编码/迁移、S18 严格类型）。
- Vue：`tests/smoke.spec.ts` + `tests/negatives-r4.spec.ts`（保存端点改为
  /result 后路由 glob 同步）+ `tests/negatives-r5.spec.ts`（R5-1 双槽恢复、
  R5-2 Discard 最新版、R5-3 丢响应后新意图裁决）。
- VM：`tests/015-notes.autotest`（19 场景）+ `tests/probe/evidence/r5-work/`
  驱动脚本（动态端口、私有 MCP 端口、净库单轮、UTF-8 显式）。
- 依赖固定：AutoDown 96f095b（gitlink 已 pin）；AutoLang main 578794d + CLI
  a6e108f60；app 级构建 `cargo build -p app-015-notes-back --offline`。

## 已登记债务

- D-742-1：`use api: Note` 跨模块解析 'undefined'——映射留在 api.at 绕开。
- 引擎包 files 缺 src 的 file: 快照问题——vendor/auto-down 已补（已提交）。
- 时间戳：created_at/updated_at 恒空串（无时钟原语），排序/版本用 seq/revision。
- 恢复槽容量 2：第三份未保存草稿触发显式驱逐（保最旧），横幅可见；
  更大容量或恢复集合持久化留待后续需求。
```

## 发布核对清单（merge 执行）

1. 以上【提案全文】替换 canonical，git blob/hash 记入合入收据。
2. 刷新 docs/README 计划索引（001 → archived，链接修正）。
3. 计数核对：checked=9（T-00/T-03/T-05/T-06/T-17..T-21），与 frontmatter
   current_step/total_steps=9/22 一致；归档副本同计数。
4. merge-owned 关闭门其余项按计划 §8 执行（本稿不预先勾选任何 merge 操作）。
