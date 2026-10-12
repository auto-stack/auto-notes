# Spec delta r6 — 实现绑定稿（SD-07..SD-22 → 已验实现）

> 状态：**work 阶段提案，未发布**（取代 r5 稿——其容量/flush 规则相互矛盾，
> 复审判定不可发布）。canonical `docs/specs/notes/durable-inbox.md` 仍为 r3
> （blob 8f05b8ddb617d5d64e937e55027e782a2b0c0f85）。供 independent review 对照
> 已验实现验证；merge 阶段以【提案全文】整体替换 canonical 并刷新索引/计数。
> 输入合同：spec-delta-r6.md（SD-17..22 冻结稿，SHA256=70d7f6da…）。
> T-26 兼容决策：[t26-legacy-compat-table.md](t26-legacy-compat-table.md)（若用户
> 选择非 A 选项，§"旧行裁决"须按决策更新后再发布）。

## SD → 实现绑定表

| delta | 规则变更 | 实现位置 | 验证 |
|---|---|---|---|
| SD-17 (r6) | 区分冲突/修复来源；修复合并只对可证明匹配行回收；成功清凭据（完成代际），冲突不得因重读授予合并 | `repository.at: upgrade_if_legacy` 入口裁决（凭据=corrupted_r1 legacy 标记唯一；upgraded=0+notes>0 恒 upgrade_conflict）+ `repair_legacy_merge`（行 revision/title/body 与实体全等才回收，更高修订/异文跳过；成功 DELETE corrupted_r1 + repair_generation=1） | battery S19a/S19b；独立 IND-API-1/2 |
| SD-18 (r6) | 实体/清单身份/结构/类型/路径严格校验，非法实体可修复重试 | `validate_legacy_entity`（note_id 非空且与 entry 一致、legacy_id/revision 严格整数字面量、title/blocks(text)/tags(元素)/folder/state 类型、pinned 布尔）+ `valid_legacy_file`（无分隔符/穿越）+ 显式 entity missing 检查；违反 → ROLLBACK + upgrade_error，不标完成 | battery S19c（{} 拒绝+修复重试）/S16；scratch U4/U5/U9/U10；独立 IND-API-3 |
| SD-19 (r6) | 全入口容量保全：满槽显式阻止（无驱逐），可见状态，调用者不清 dirty | `notes_store.at`: StashDraft（A→B→满则 stash_blocked）/RecoverDraft/RecoverDraft2 对称 can 检查/导航 handler 的 flushed 门（满槽=保持原位不清 dirty）+ editor 满槽横幅 | 独立 IND-VUE-1/IND-VM-1；Vue R5-1 |
| SD-20 (r6) | 保存与全部 flush 一致意图轮换+服务器裁决；槽携带完整未确认上下文 | 各 flush handler 内联轮换（BindIntent/prev）+ adjudication（revision_conflict/request_conflict → get_note_r 对比 prev → 采纳服务器 revision 重试）；rec_*_pend/prev ×2 槽随 stash/restore 搬运 | 独立 IND-VUE-2/IND-VM-2；VM r5 负例 R5-VM-3；Vue R5-3 |
| SD-21 (r6，已决：A) | 旧行逐类兼容表 + 承诺差异显式化 | [t26-legacy-compat-table.md](t26-legacy-compat-table.md)；实现=旧行重放一律 request_conflict（选项 A 现状） | battery S15/S17；scratch R1–R3 |
| SD-22 (r6) | 证据映射关闭原任务、真实计数、一致实现稿 | 本计划 §9 work 记录 + 计数核对（见下）+ 本稿 | 复审/merge |

原 r5 表中 SD-07..16 的实现绑定继续有效（S07/12 由 r6 重写修正后通过——见上
SD-17/18 行；S08/09/10/11/13/14/15 绑定不变，验证以本轮全套门为准）。

## 【提案全文】merge 时整体替换 docs/specs/notes/durable-inbox.md

```markdown
# durable-inbox — 015-notes 可靠收件箱（current-state）

> 状态：current-state（NOTES-001 r6 实施，SD-02..SD-06 与 SD-07..SD-22 随
> r4–r6 修复落地）· 更新：2026-10-12 · 计划：NOTES-001 + AutoLang 742

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
- 旧行裁决：intent 为空的行（升级导入收据、v1 三列行、残缺 v2 行）重放一律
  `request_conflict`——旧持久层不含意图内容，"完全同意图"不可证明；原收据经
  read_receipt 可查询，旧对象不受影响。r4 管道行经 v2→v3 从 doc 快照确定性
  重导。逐类兼容表与 AC-02 承诺差异见 T-26 决策制品（用户决策 A/B/C）。
- 条件更新：expected_revision ≠ 当前 → `revision_conflict`；8 并发同 revision
  恰好 1 成功。
- 故障点（NOTES_TEST_MODE=1 门禁内）：`after_entity`=COMMIT 前 ROLLBACK；
  `after_manifest`=COMMIT 后报 `fault_injected`。
- 软删 = state=trashed；restore 反转。

## Phase 1 JSON 布局升级（SD-07/SD-12/SD-17/SD-18）

- 入口裁决（升级状态机）：
  * 修复凭据唯一来源 = `meta.corrupted_r1` 含 "legacy upgrade"（r4 缺陷库标记）；
    `upgrade_error` 永不授予合并资格——冲突/普通 I/O 错误在前提消失前原样复现
    （重复读取/重启不得绕过，混合库恒 `upgrade_conflict`）。
  * 未升级 + 旧树在 + 库内已有 notes → `upgrade_conflict`（恒定）。
  * 未升级 + 旧树在 + 库空 → 全新升级（备份先行并校验：备份目录被普通文件
    占据/拷贝失败/备份 manifest 缺失 → `storage_unwritable` 不完成）。
  * 已升级 + 凭据在 + 旧树在 → 修复合并：manifest 引用实体逐一严格校验；
    行缺失（r4 跳过的坏实体）→ 补导；行与实体导入产物可证明一致
    （revision/title/body 全等）→ 回收 manifest 权威元数据；更高修订/同修订
    异文 → 跳过保护（用户确认内容绝不回退）。成功清除凭据并记
    repair_generation（后续读取/编辑不再重导）；失败保持凭据可重试。
  * 已升级 + 凭据在 + 旧树不在 → 清凭据记代际，不再重导。
- 元数据权威与旧 load_doc 一致：实体提供 title/body(blocks→换行)/color/时间戳；
  manifest entry 覆盖 tags/pinned/state/folder/revision/seq/legacy_id。trashed
  行不进活动列表。
- 实体/清单严格校验：note_id 非空且与 entry 身份一致；legacy_id/revision 严格
  整数字面量（布尔/字符串/小数拒绝）；title/blocks(每块 text)/tags(每元素)/
  folder/state 类型；pinned 布尔；file 路径无分隔符/穿越；缺字段容忍。任一违反
  → ROLLBACK + 显式 upgrade_error（可修复重试），绝不导成空 ID/空正文后置完成。
- 升级错误经 `/api/v1/status` 的 `upgrade_error` 显式可见。
- receipts → requests：只导入 committed；kind 按 rev 规则恢复；intent 留空。

## 迁移（notes.json 数组，SD-04/SD-15）

- 门禁内逐项校验；进 `corrupted`（index/reason/snippet）且后续合法项继续：
  null；缺 id；id 非严格整数字面量；源内重复 id；title 非 string；body 存在但
  非 string（缺省容忍 ""）；tags 非数组或元素含非字符串；folder 非 string；
  pinned 非 boolean。snippet 恒 JSON 字符串（>400 省略内容）。
- 非法 JSON 顶层：最短有效跨度打捞器（字符索引 + 字节偏移同步，Unicode 安全）。
- 报告与 meta 先于 COMMIT；报告写失败 → ROLLBACK 可重试；重跑 skipped_existing
  幂等；原件只读 + backup。

## UI/legacy 契约（SD-05/SD-10/SD-14/SD-19/SD-20）

- Note 视图携带 revision；`PUT /api/notes/:id` 条件更新 → bool；
  `PUT /api/notes/:id/result`（update_note_r）/`GET /api/notes/:id/result`
  （get_note_r）返回结构化 RepoResult（err_code 区分明确拒绝与传输层未知）。
- 草稿会话意图：rid 于保存点分配并立即绑定意图快照（BindIntent：内容+基线
  修订）；**保存与全部自动 flush（切换/搜索/筛选/标签/置顶/新建）使用一致的
  意图轮换与服务器裁决**：内容变更 → 轮换新 rid（旧意图快照转 prev）；未变
  → 原 rid 原样重试。
- 未确认提交裁决：保存/flush 被 revision_conflict/request_conflict 明确拒绝且
  存在 prev → 取服务器当前版本对比 prev——一致 ⇒ 旧提交已落地，采用服务器
  revision 重试新意图（保留新草稿）；不一致 ⇒ 双方版本保留（冲突横幅 +
  Discard）。传输层未知结果不裁决（快照已记，下次保存裁决）。
- 恢复槽双槽（容量 2）：**全入口容量保全，无驱逐**——Stash 入空闲槽；两槽全满
  → 显式阻止（stash_blocked 置位，不覆盖任何槽、不清会话上下文），编辑器显示
  满槽横幅，导航 handler 保持原位不清 dirty；Recover 双入口对称检查（当前
  dirty 需先入另一空闲槽，否则显式阻止）。槽条目携带完整未确认意图上下文
  （pend/prev），恢复时原样回装。
- Discard = 显式选择服务器版本：先刷新工作集再按 draft_id 装载最新版。
- 只有 durable 成功后才清 dirty/切草稿/显示 Saved；刷新 notes 仅在成功分支
  （VM 渲染序约束：stash 路径刷新会破坏列表渲染——实证后移回）。
- 自动 request_id 使用专用 req_seq 计数器。

## 标识与测试入口（SD-06）

- request_id 校验：非空、≤100 字符、仅 `[A-Za-z0-9._:-]` → 否则 invalid_request。
- 变更型测试端点默认关闭（test-mode-disabled）；电池在门禁未开启时立即退出 1。

## 端点面

- legacy：GET/POST `/api/notes`、GET/PUT/DELETE `/api/notes/:id`、
  PUT/GET `/api/notes/:id/result`、PATCH `:id/pin`、PUT `:id/tags`、
  GET `/api/notes/search`、GET `/api/request-id`。
- v1：`/api/v1/notes[...]`、`/api/v1/migrate`、`/api/v1/status`（含 upgrade_error）、
  `/api/v1/test/{setup,fault}`（门禁内）。
- 错误码：not_found | revision_conflict | request_conflict | upgrade_conflict |
  upgrade_incomplete | storage_unwritable | second_writer | invalid_request |
  fault_injected | test-mode-disabled。
- SQL 字面量一律 `sql_str()`；动态错误消息在 .at 层拼接后内插（SQLite `+` 为
  数值加，字符串拼接进 SQL 会静默失败——实证）；`db.exec` 成功判定 `< 0`。

## 回归资产（r6）

- 电池 S0–S19（S15 升级权威/旧行裁决/误写恢复、S16 失败边界、S17 意图编码/
  迁移、S18 严格类型、S19 混合库冲突恒定/修复保护/非法实体）。
- Vue：smoke + negatives-r4（glob 已随 /result 端点修正）+ negatives-r5
  （双槽恢复/Discard 最新版/丢响应裁决）。
- VM：015-notes.autotest（19 场景）+ r5-work 驱动（VM 原负例 13）+ r6-work
  独立驱动副本（复审断言入库，仅环境适配）。
- 测试基建：wait_ready 要求 draft_title 非空（App_Init 完成信号）后才放行场景。
- 依赖固定：AutoDown 96f095b；AutoLang main c64b7135 线（CLI a6e108f60）。

## 已登记债务

- D-742-1：`use api: Note` 跨模块解析 'undefined'——映射留在 api.at 绕开。
- 时间戳恒空串（无时钟原语），排序/版本用 seq/revision。
- 恢复槽容量 2：满槽显式阻止 + 用户释放（无驱逐）；更大容量/持久化恢复集合
  留待后续需求。
- VM 渲染序：flush 冲突路径禁止紧跟 `.notes` 整表赋值（实证破坏列表渲染）——
  刷新限成功分支；框架层根因留待 AutoLang 侧排查（不阻塞本模块契约）。
```

## 发布核对清单（merge 执行）

1. 【提案全文】替换 canonical（T-26 已决 A，"旧行裁决"段即最终语义），
   git blob/hash 记入合入收据。
2. 刷新 docs/README 计划索引（001 → archived，修正 Phase 状态描述）。
3. 计数核对：以计划 frontmatter 为准（T-26 决策后 re-count），归档副本一致。
4. merge-owned 其余关闭门按计划 §8 执行。
