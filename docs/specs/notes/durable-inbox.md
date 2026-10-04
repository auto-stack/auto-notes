# durable-inbox — 015-notes 可靠收件箱（current-state）

> 状态：current-state（NOTES-001 实施）· 更新：2026-10-04 · 计划：NOTES-001 + AutoLang 742

## 存储契约（NoteDocument v1）

- 实体文件：`<data>/notes/<note_id>.r<rev>.json`（不可变，提交后只增修订）
- manifest：`<data>/manifest.json`（唯一索引：entries[{note_id,revision,file,state,folder,tags,pinned,seq,legacy_id}] + counter）
- 收据：`<data>/receipts/<request_id>.json`（committed 收据存在 ⇒ manifest 已含该提交）
- journal：`<data>/journal/intent-<seq>.json`（提交意图，恢复扫描依据）
- 损坏隔离：`<data>/corrupted/report-r1.json`；迁移备份：`<data>/backup/notes.json.bak`
- 数据目录解析：`NOTES_DATA_DIR` env 覆盖 → `%APPDATA%`（Win）/ XDG / `~/.local/share` + `/auto-notes/data`

## 提交协议（无 rename/无时钟能力下的崩溃一致性）

写序 = journal intent → 实体文件（新文件，天然完整）→ manifest 重写（提交点）→ 收据。
任何一步中断：无收据即未提交；manifest 仍指旧版（AC-01/AC-02）。
旧整数 id 映射：`legacy_id → note_id("n-<id>")`，持久于 manifest，仅迁移时赋值一次。
revision 条件写入；陈旧写入返回 `revision_conflict`（AC-04）。
软删 = manifest state=trashed（实体不动）；restore 反转（AC-05）。

## 能力边界（T-00 探针实证）

- a2r 后端无 rename/read_dir/时钟 ⇒ 无原子替换（掉电窗口=manifest 小文件单写）；
  时间戳字段显式空串，排序/版本用持久化单调 seq。
- 跨进程并发：writer.lock 拒绝第二写者（`NOTES_FORCE_LOCK=1` 或删锁显式接管）。
- seed 模式：`NOTES_SEED=1` 仅全新目录写入 6 条示例（tag "seed"，Welcome 置顶）；
  默认空启动，绝不冒充用户数据（AC-05）。

## 端点面

- legacy（UI 契约，api.at 直调 repository）：GET/POST `/api/notes`、GET/PUT/DELETE
  `/api/notes/:id`、PATCH `:id/pin`、PUT `:id/tags`、GET `/api/notes/search`。
  视图映射：id=legacy_id、body=blocks[0].text、time=updated_at||"Just now"。
- v1（采证/测试面）：`/api/v1/notes[...]`（RepoResult 形状：ok/err_code/doc/receipt）、
  `/api/v1/migrate`、`/api/v1/status`、`/api/v1/test/{setup,fault}`（测试专用）。
- 错误码：not_found | revision_conflict | storage_unwritable | second_writer |
  corrupt | invalid_request | fault_injected。

## 依赖的工具链修复（AutoLang plan-742，未合 master）

api.rs handler 体发射：D1 List 构造降级、D2 companion 导入收集、D4 dot→path、
D5 ?T 返回 Some/None→Ok/NOT_FOUND、D6 语句胶粘拆行、borrow 泛化到 companion。
**合入前 Notes 必须继续使用含 742 的工具链构建**（worktree lang-742 或 742 合入后）。

## 已登记债务

- D-742-1：`use api: Note` 跨模块解析 'undefined'（api.at 本地构造正常）——映射留在 api.at 绕开。
- 掉电窗口：manifest 重写非原子（无 rename）；掉电可能丢最后一次提交点更新（journal 可手工恢复）。
- 迁移打捞的括号配平扫描按字节偏移实现（ASCII 标记间切片，UTF-8 安全但实现复杂）。
