# NOTES-007 T-01 决策制品 · 读快照瞬态停摆归因（AC-01）

日期：2026-11-16 · 计划：NOTES-007（r1）· 执行树：`D:/autostack/.wt/notes-007/auto-notes`
（分支 `notes-007-dev`，基线 `ba31252`）· 原始数据：`D:/autostack/plan-artifacts/plan-007/`

## 结论（三因子组合，非单选）

停摆 = **环境文件锁（触发器）× 旧读路径调用形状（放大器）× a2r sqlite facade 的
静默内存回退（把失败变成"错数据"而非"错状态"）**。

| 因子 | 是否根因 | 证据 |
|---|---|---|
| 环境文件锁（AV/EDR 类排他扫描句柄） | **触发条件** | 外部 `FileShare=None` 句柄期间 `sqlite3_open` 在 **1.459s** 后失败（`unable to open database file`）——SQLite Windows VFS 对共享冲突的有界重试；`busy_timeout` 不覆盖文件打开阶段 |
| 旧读路径调用形状 | **放大器** | 每次读 **2 次** `sqlite.open`（`open_repository()` + 调用方各一次，基线 `repository.at:1382-1413`）+ 每请求一次无条件 `INSERT OR REPLACE meta schema_v='3'`（`repository.at:258`）；写锁被占时该 meta 写实测等待 **3.377s** 后失败（busy_timeout=3000），且旧代码忽略返回值 |
| a2r `sqlite.open` 失败回退内存库 | **症状决定项** | `a2r-std/src/sqlite.rs:31-43`：打开失败 → `Connection::open_in_memory()`，错误仅记 `sqlite.last_error`。旧读路径随后把这个**空内存库**当真实快照 → 已存在 id 的 `get`/`update` 返回 `not_found`、列表返回 `[]`、`status` 谎报 `loaded:true entries:0`、写入目标变成幽灵库 |
| 共享 facade（跨请求单连接/互斥） | **否** | `sqlite.open` 每次新建 `Connection`（`Arc<Mutex<Connection>>` 句柄私有），无跨请求共享；engine 线无需移交 |

**症状对账**（READER-013 §10 / BACK-STALL-BLOCKER.md 44+7 轮）：
health 全程 UP（health 不触 repository）；窗口内 update 已存在 id → not_found
（幽灵库）；"读快照冻结 60s+"（幽灵库空快照 + 锁解除后自恢复）；数据零丢失
（真实库从未被写）；10s～8.5min 的墙钟时长 = 单请求 2.9s（2×打开重试）或
3.4s（busy 等待）× UI 并发/重试队列，在环境锁持续期间累积——**不是单次调用无界挂起**。

## 可控复现（最小可重跑负载形状）

1. `python tests/probe/concurrent_hammer.py --mode lockwindow --hold 8`
   —— 外部进程以 `FileShare=None` 独占 `inbox.db`（模拟 AV/EDR 排他扫描），窗口内
   并发取样 create/get/list/status。**修复前**（exe sha `4ed458fb…`）：
    `get` → `ok:false not_found` 2.912–2.956s（3 样例）；`list` → `[]` 无错误 2.9s；
    `status` → `loaded:true entries:0`（真实 5 条）1.47s；`create` → `storage_unwritable` 2.93s。
   **修复后**（exe sha `832507f3…`）：全部具名 `storage_unavailable` ≈1.47–1.50s
   （单次打开上限），`status` → `loaded:false storage_error:storage_unavailable`，
    窗口结束数据完整 + 窗口内成功写已落盘。
2. `python tests/probe/concurrent_hammer.py --mode ui --rounds 20`
   —— UI 形状并发（3 写者 create/update/capture/draft put + 3 读者
   list/get/search/status/receipt/fp get/draft get + 同修订争用对）。修复前 1 轮冒烟
   读面 max 669.6ms / create max 781.2ms；修复后 20 轮 2199 采样读面 max **141.3ms**、
   零幻影 not_found、零丢失。
3. `python tests/probe/storage_trace.py` —— 写锁窗口内读延迟（修复后 17 采样
   max **30.5ms**，数据正确）；schema 初始化日志恰好 1 行、重启 0 行。
4. 语句级微探针 `plan-artifacts/plan-007/sqlite-microprobe.py`（写锁被占时的
   ensure_schema 语句行为）：重复 `ALTER TABLE ADD COLUMN` **0.000s 不拿锁**
   （列已存在时在 prepare 期即失败）、纯 `SELECT` 0.000s、`INSERT OR REPLACE meta`
   **3.377s** 后 `database is locked`、`BEGIN IMMEDIATE` 3.365s。

## 与起草假设的差异（记录在案）

- 起草写"每读 3 连接"：实读为 **2 次打开**（`open_repository()` + 调用方）。实测
  2.9s ≈ 2×1.46s 与 2 次打开一致。
- 起草写"5×ALTER 每请求两次拿写锁"：**不成立**。列已存在时 ALTER 在 prepare 期失败、
  0.000s 且不取写锁；旧读路径真正的写锁点是**无条件的 `INSERT OR REPLACE meta schema_v`**。
  （全新库/半途迁移时 ALTER 才真取锁——修复后该路径整体退到一次性慢路径。）
- 起草把 10s～8.5min 归给"busy_timeout 不覆盖文件打开"：更准确的链条是
  "打开失败 → 内存回退 → 错数据"，分钟级墙钟来自并发/重试放大，非单调用无界。

## owner 路由

全部修复点在 notes 存储层（本计划 G2 形状：单连接零写锁读 + schema 就绪探针 +
BUSY 具名 + 打开失败具名 + 慢操作登记），**无 engine 线移交件**。
环境侧（AV/EDR 排除目录/扫描策略）在仓控之外，仅建议：把 `NOTES_DATA_DIR`
（含 `inbox.db`/`-wal`/`-shm`）加入安全软件排除，或在部署文档中提示。