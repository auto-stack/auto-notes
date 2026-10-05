# durable-inbox — 015-notes 可靠收件箱（current-state）

> 状态：current-state（NOTES-001 r3 实施，SD-02..SD-06 已落地）· 更新：2026-10-05 · 计划：NOTES-001 + AutoLang 742

## 存储契约（SQLite 单文件，r3）

- 存储：`<data>/inbox.db`（SQLite，a2r-std `sqlite` 模块；WAL + busy_timeout=3000）
  - `notes(note_id PK, legacy_id UNIQUE, revision, title, body, tags_json, color, pinned, state, folder, seq, created_at, updated_at)`
  - `requests(request_id PK, note_id, kind)` — request_id ↔ note_id 同事务绑定（AC-02 重放依据）
  - `meta(k, v)`：counter（笔记 seq）、req_seq（自动 request_id 专用单调序列）、seeded、migrated
- 文档 JSON（NoteDocument v1）：13 列固定序投影，`pinned` 为 JSON boolean（SQLite 整数 0/1 落文档时转换）；
  正文为单 `body` 文本（v1 只产生 text 块，blocks 语法糖随 NOTES-002 再议）
- 损坏隔离：`<data>/corrupted/report-r1.json`；迁移备份：`<data>/backup/notes.json.bak`
- 数据目录解析：`NOTES_DATA_DIR` env 覆盖 → `%APPDATA%`（Win）/ XDG / `~/.local/share` + `/auto-notes/data`；
  每次解析即 `mkdir_all` 兜底（sqlite.open 对缺父目录会静默回退内存库——禁止）

## 提交协议（SD-02/03：整事务串行化 + 原子提交点）

- 所有写入（create/update/set_meta/trash/restore/migrate）走同一门禁：
  `BEGIN IMMEDIATE` → 读 revision/幂等重放（事务内查 requests）→ 写 notes + requests → `COMMIT`。
  跨进程排他是原子取得的；同一目录两个写者只有一个进入（`second_writer`），无持锁标记可继承/伪造。
- 幂等重放先于 revision 检查：requests 命中 → 返回原收据+原文档（`replayed:true`，AC-02）。
- 条件更新：expected_revision ≠ 当前 → `revision_conflict`（附 current_revision，AC-04）；
  8 并发同 revision 更新恰好 1 成功（电池 S7b 实证）。
- 故障点（NOTES_TEST_MODE=1 时 `/api/v1/test/fault` 注入）：
  `after_entity` = COMMIT 前 ROLLBACK（无痕，AC-02 前半）；
  `after_manifest` = COMMIT 后报 `fault_injected`（已持久，重放裁决——kill 后重启同 request_id 重试无重复，S10 实证）。
- 软删 = state=trashed（行不动）；restore 反转（AC-05）。

## 迁移（SD-04，T-08）

- `BEGIN IMMEDIATE` 门禁内逐项校验：null 项 / 缺 id / id 非整数（引号开头或含 `.`）/ 源内重复 id
  → 逐项进 `corrupted`（index/reason/snippet，snippet ≤160 字符），**后续合法项继续打捞**（AC-03）。
- 非法 JSON 顶层：最短有效跨度打捞器（对每个 `{` 依次尝试其后每个 `}`，解析验证；坏对象报告后从
  下一字节续扫——失控字符串安全）。
- 元数据（counter/migrated）与实体同事务；任一步失败 ROLLBACK，原件只读 + `backup/notes.json.bak`；
  meta.migrated + 已有数据 → 重跑 `skipped_existing:true`（幂等）。
- 报告持久化 `corrupted/report-r1.json`（COMMIT 后写，失败不回滚迁移）。

## UI/legacy 契约（SD-05，T-09）

- Note 视图携带 `revision`；读取时保存，提交时回传。
- `PUT /api/notes/:id` 为条件更新（expected_revision + request_id）→ 返回 durable-bool；
  失败/冲突时 store 保持本地草稿（dirty 不清、conflict 置位、Editor 显示冲突提示），
  服务端版本保留在列表可恢复；只有 durable 成功后才清 dirty/切草稿/显示 Saved。
- request_id 由 UI 每个草稿会话取一次（`GET /api/request-id`）并稳定持有——重试同一意图复用同一 id（重放幂等）；
  create 同理（NewNote 每次点击一个 id，双击只建一条）。
- 自动 request_id 使用专用 `req_seq` 计数器，绝不复用笔记 seq（update 不推进 seq——
  复用会导致二次 update 命中回放假成功，已实证并修复）。
- Vue/VM 同构：手动 Save 与切换/搜索/筛选/新建的自动 flush 全部走同一条件更新路径。

## 标识与测试入口（SD-06，T-10）

- request_id 校验：非空、≤100 字符、仅 `[A-Za-z0-9._:-]` → 否则 `invalid_request`。
  SQLite 时代 request_id 是表键（sql_str 转义）不是路径，穿越类结构性消除；校验保留为语义/导出防线。
- 变更型测试端点（`/api/v1/test/setup|fault`）默认关闭（返回 `test-mode-disabled`），
  仅 `NOTES_TEST_MODE=1` 的显式隔离模式可用；TEMP 调试端点（test/open|loadmanifest|listloop）已移除。
- 电池（`tests/probe/run_v1_battery.sh`）在门禁未开启时立即退出 1（负例即门禁验证）。

## 端点面

- legacy（UI 契约，api.at → db.at 适配 → repository）：GET/POST `/api/notes`、GET/PUT/DELETE
  `/api/notes/:id`、PATCH `:id/pin`、PUT `:id/tags`、GET `/api/notes/search`、GET `/api/request-id`。
  视图映射：id=legacy_id、body=body、time=updated_at||"Just now"、revision=revision。
- v1（采证/测试面）：`/api/v1/notes[...]`（RepoResult 形状：ok/err_code/doc/receipt）、
  `/api/v1/migrate`（MigrationReport）、`/api/v1/status`、`/api/v1/test/{setup,fault}`（门禁内）。
- 错误码：not_found | revision_conflict | storage_unwritable | second_writer |
  invalid_request | fault_injected | test-mode-disabled。
- SQL 字符串字面量一律 `sql_str()`（单引号 + `''` 转义）——bundled SQLite DQS=0，
  json.encode 的双引号串在 VALUES/WHERE 必炸；`db.exec` 返回受影响行数（INSERT=1），
  成功判定用 `< 0`。

## 依赖的工具链修复（AutoLang plan-742，未合 master）

api.rs handler 体发射：D1 List 构造降级、D2 companion 导入收集、D4 dot→path、
D5 ?T 返回 Some/None→Ok/NOT_FOUND、D6 语句胶粘拆行、borrow 泛化到 companion；
SQLite 面（742 d98517f0c）：SqliteDb Clone（Arc<Mutex<Connection>>）+ open/exec/query
`impl AsRef<str>` + `a2r_std::sqlite` 根路径 qualify 保护；
D8（9f6481e8c）：App.vue 主题 bootstrap 同源播种 store.dark_mode（否则 App ref 与 store
分叉，light-scheme 下 Theme 快切失效）；fs.mkdir_all 模块面路由（005d148a0）+
facade mkdir_all（v0.6-dev 1cd4af1cf）。
**合入前 Notes 必须继续使用含 742 的工具链构建**（worktree lang-742 或 742 合入后）；
运行时 a2r-std 的 sqlite Clone/AsRef patch 已直补 v0.6-dev（ed2d00b90）。

## 已登记债务

- D-742-1：`use api: Note` 跨模块解析 'undefined'（api.at 本地构造正常）——映射留在 api.at 绕开。
- 引擎包 `files:["dist"]` 不含 src 而 exports development 条件指向 src：file: 快照缺 src，
  vite dev 必炸——vendor/auto-down 已补 `files:["dist","src"]`（未提交，跨仓登记）；
  历史方案 junction 会被 pnpm install 反复清除，勿再使用。
- VM/MCP 轨（`auto run -r vm` 保存冲突场景）与 T14 parity 探针在本轮未重跑
  （UI 视觉增量仅一处条件态冲突提示）；独立复审时按需补采。
- 时间戳：created_at/updated_at 恒空串（无时钟原语），排序/版本用持久化 seq/revision。
