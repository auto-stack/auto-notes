# NOTES-001 Phase 2 / T-05 能力核查与协议冻结

日期：2026-10-05 · 执行：NOTES-001:r3 Phase 2 agent · 工具链：lang-742 worktree CLI（742 分支 bd1ae6ec9 + 未提交修复）· 探针模块：`src/back/p2probe.at`（NOTES_P2PROBE=1 门禁）

## 1. 结论

a2r 后端的 `auto.sqlite` 模块（rusqlite bundled，后端构建已链接 libsqlite3-sys）
提供 T-05 要求的全部能力：事务级串行化（BEGIN IMMEDIATE）、原子排他
（SQLITE_BUSY）、崩溃安全提交（WAL + 回滚）、参数化转义、Unicode 往返。
选定方案：**SQLite 单文件可靠存储**（`<data>/inbox.db`，WAL），
放弃 Phase 1 的 JSON 文件布局（产品 §4 明确允许"用现有可靠存储库实现
同样契约而不照搬文件布局"）。

## 2. 探针实测（live backend，p2probe 端点）

| 探针 | 结果 |
|---|---|
| open + PRAGMA journal_mode=WAL/busy_timeout=3000 + 建表 + 插入/查询 | ✓（last_error=""）|
| BEGIN IMMEDIATE + INSERT + COMMIT 单 exec batch | ✓ value="committed" |
| 双连接写排他：A 连接 BEGIN IMMEDIATE 持锁，B 连接 BEGIN IMMEDIATE | ✓ b=-1，"database is locked"（原子排他实证）|
| BEGIN + INSERT + ROLLBACK | ✓ rows_after=0（回滚干净）|
| 单引号注入转义（`'`→`''`）+ 中文/emoji 往返 | ✓ roundtrip_ok=true |

原始输出（重跑可复现）：端点 `/api/p2/{open,txn,busy,rollback,escape}`，
NOTES_P2PROBE=1 + NOTES_P2DB=<path> 门禁；探针期间后端日志无异常。

## 3. 冻结协议（Phase 2 存储）

- DB：`<data>/inbox.db`；打开后执行 `PRAGMA journal_mode=WAL` + `PRAGMA busy_timeout=3000`（连接级）。
- schema：
  - `notes(note_id TEXT PRIMARY KEY, legacy_id INTEGER UNIQUE, revision INTEGER, title, body, tags_json, color, pinned INTEGER, state TEXT, folder TEXT, seq INTEGER, created_at TEXT, updated_at TEXT)`
  - `requests(request_id TEXT PRIMARY KEY, note_id TEXT, kind TEXT)` — request_id 与实体同事务绑定（F-001-02 根治）
  - `meta(k TEXT PRIMARY KEY, v TEXT)` — counter、migrated 标记
- 写事务（每个变更端点）：每请求独立 `sqlite.open` → `BEGIN IMMEDIATE` →
  以 DB 当前状态做检查（幂等重放/revision 冲突/存在性）→ INSERT/UPDATE →
  `INSERT INTO requests` → `COMMIT`。任一步失败 → `ROLLBACK` + 结构化错误，
  绝无部分状态；SQLite 写锁覆盖整个检查+写区间 ⇒ 事务级串行化（F-001-01）。
- 幂等：requests 表同事务查询；命中 → 返回原 note（不再新建/不再 revision+1）。
  COMMIT 后、响应前崩溃 ⇒ 请求已持久（notes+requests 同事务）⇒ 重放命中 ⇒ 无重复、无假成功。
- 双进程：BEGIN IMMEDIATE 由 SQLite 文件锁排他；后到者 BUSY → `second_writer`/
  可重试冲突映射。无活写者时的陈旧文件不存在（锁在 DB 内部，非文件系统残留）⇒
  废除 NOTES_FORCE_LOCK 文件锁语义。
- 迁移（T-08）：legacy notes.json 在 .at 解析（json 模块），逐项校验写入；
  `meta.migrated=1` + legacy_id UNIQUE 保证重试幂等；损坏项（null/错类型/重复 id）
  进 `corrupted` 报告（meta 或 JSON 报告表），不终止、不静默。
- 崩溃恢复（T-07）：打开时 SQLite 自恢复；孤儿实体文件不存在（无文件布局）；
  Phase 1 的 JSON 实体目录（仅测试数据）不做自动迁移——登记为已知限制。
- Phase 1 JSON 布局（manifest/notes/*.json/receipts/journal）整体退役（SD 增量）。

## 4. 跨仓/依赖登记

- sqlite 模块 Rust 轨可用（a2r-std + rusqlite bundled）；**VM 轨无 sqlite**
  ——本应用为 split 模式（前端 vm/vue ↔ 后端恒 rust），不受影响；纯 VM 单体
  应用需等 415-B2（登记，非本计划范围）。
- 742 工具链修复（api.rs 体发射 D1/D2/D4/D5/D6 + borrow 泛化）为本方案前置。

## 5. 限制

- 探针未实测掉电（需硬件）；以 SQLite WAL + 默认 synchronous 语义为准。
- request_id 以 `''` 转义插入 SQL 字面量；T-10 另加显式校验（拒绝空/分隔符/
  路径穿越）双保险。
