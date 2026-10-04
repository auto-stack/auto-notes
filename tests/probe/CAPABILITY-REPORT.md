# NOTES-001 T-00 持久化能力探针报告

日期：2026-10-04 · 执行者：NOTES-001 计划 agent · worktree：
`D:/autostack/.wt/auto-notes-20261004-01/auto-notes`（分支 `codex/auto-notes-20261004-01`，
起点 v0.6-dev@7ecfa5d）· 工具：auto CLI `0.1.0+v0.4.2-2564-g168b56923`
（D:/autostack/auto-lang/target/debug/auto）。

## 0. 结论摘要（回答计划的四个问题）

1. **app-data 解析**：a2r 后端可经 `env.get("APPDATA")`（Windows）/`HOME`/`TEMP`
   解析用户目录并读写文件；stdlib 的 `env.local_data_dir()/home_dir()` 只有 VM
   实现，a2r 后端不可用（编译错误）。数据目录须用环境变量解析 + `NOTES_DATA_DIR`
   覆盖（T-03 依此实现）。
2. **文件/存储 API**：两条进程路径的**后端是同一类 a2r 生成的 Rust axum 服务**
   （`auto run -r vm` 日志明示 `split mode: frontend vm ↔ backend rust over HTTP`；
   `auto run` 为 vue↔rust）。可用面＝facade `auto_lang::a2r_std` 的
   `fs.*`（create_dir/write_text/read_text/exists/delete/file_size/append_text/
   copy_recursive/walk/read_text_range…）、`env.get/get_or/set/args`、
   `json.encode/is_valid/parse/get*`、字符串 `+` 拼接。
3. **原子提交**：**没有 rename/read_dir/原子替换原语**（`fs.rename/temp_dir/
   read_dir` 仅 stdlib `.at` 声明，无 a2r 路由 → E0423）。`write_text` 是
   truncate+write，无 fsync。⇒ 仓储必须用「新版本文件 + journal 先行 +
   manifest 更新为提交点 + 收据后置」的崩溃一致性协议（见 T-02 设计），
   不能宣称掉电级原子性。
4. **异常重启**：进程硬杀（taskkill /F）后重启，杀前写入的文件完整可读
   （marker + append 累积跨 2 次硬杀与 3 次进程存活）。真实磁盘持久化成立；
   `db.at` 注释所称 "JSON file persistence" 在基线代码中不存在（无任何磁盘
   调用），重启即丢——本报告为改 uuid 前的现状证据。

## 1. 两条进程路径的采证

| 路径 | 命令 | 证据文件 |
|---|---|---|
| VM 前端 ↔ rust 后端 | `auto run -r vm`（端口 17818/17819） | `evidence/vm-cap-run1.json`、`evidence/vm-json-run1.json`、`evidence/vm-cap-run2-after-crash.json` |
| Vue 前端 ↔ rust 后端 | `auto run`（引擎包构建后，端口同上） | `evidence/vue-cap-run1.json` |

- VM run1：13 步全过（env×4、create_dir、写读回环、file_size、append、
  copy/exists/delete 链、walk、str.concat、跨请求标记写）。
- 崩溃重启（VM 路径）：`taskkill /F /PID <back_pid>`（7864）→ 连接拒绝 →
  重启 → `restart.marker.previous` 读回杀前 payload ✓。
- Vue run1：12/13 ok；唯一 "fail" 是探针自身非幂等（append.txt 累积
  `ABABABABABAB`，恰证明追加跨两次硬杀持久）。
- `data/notes.json` 种子在两次重启后仍由内存种子重现（in-memory，非磁盘）。

## 2. a2r 后端可用面（编译级证据）

编译对象：`auto run` 生成的 `rust-workspace/auto-notes-back`（axum，789 包锁定）。
探针 v1（14 错）→ v2（10 错）→ v3（0 错）的差分即能力边界：

**可用（探针运行验证）**

| .at 写法 | 生成 Rust | 语义 |
|---|---|---|
| `fs.create_dir(p)` | `a2r_std::fs::create_dir` | bool，含父目录 |
| `fs.write_text(p,c)` / `fs.read_text(p)` | `a2r_std::fs::write_text/read_text` | bool / String（truncate+write） |
| `fs.exists` / `fs.delete` / `fs.is_dir` | 同名 | bool；**delete 的 String 参数按值移动（E0382 教训）** |
| `fs.file_size(p)` | `a2r_std::fs::file_size` | i64，-1 失败 |
| `fs.append_text(p,c)` | `a2r_std::fs::append_text` | 无返回值，续写 |
| `fs.copy_recursive(src,dst)` | `a2r_std::fs::copy_recursive` | bool（借传参 ✓） |
| `fs.walk(dir)` | `a2r_std::fs::walk` | JSON 数组字符串（绝对路径、正斜杠） |
| `fs.read_text_range(p,off,lim)` | facade 再导出 | 分块读（大文件用） |
| `env.get(k)` / `env.get_or(k,d)` | `a2r_std::env::get…` | String，缺失→"" |
| `json.encode(v)` | `serde_json::to_string(&v)` | 任意 serde 值（中文/emoji 转义 ✓） |
| `json.is_valid(s)` | `a2r_std::json::is_valid` | bool（损坏判定 ✓） |
| `json.parse(s)` | `a2r_std::json::parse` | Value；**损坏输入返回 Null，不 panic** ✓ |
| `json.get/get_at/get_owned/get_str_or` | facade | Value 导航（迁移打捞用） |
| `"a" + b` 字符串拼接 | String 拼接 | 路径拼装 ✓ |

**不可用（编译错误证据，跨仓缺口见 §4）**

| 符号 | 错误 | 原因 |
|---|---|---|
| `use auto.file` + `file.*` | E0432 | facade 无小写 `file` 模块（只有 `File`） |
| `use auto.path`、`path.join` | E0432 | facade 无 `path` 模块（纯 .at 实现不参与 a2r） |
| `use auto.time`、`time.now_ms()` | E0432 + E0433 | 路由表把 Dot 调用发到 `a2r_std::time`，facade 无该模块 |
| 裸名 `now_ms()` | E0425 | 裸名臂未覆盖后端场景 |
| `env.local_data_dir()/home_dir()` | E0423 | `#[vm]`-only，无 a2r 路由 |
| `fs.temp_dir/rename/read_dir/mtime/metadata` | E0423 | 同上（`auto/fs` 的 Plan-250 增强面无 Rust 侧） |
| `process.exit/current_dir` | E0432 | facade 无 `process` 模块（spawn 在另一路由） |
| `type X { f []T }`（db.at 风格）字段 | E0106 | 转译成 `&[T]`；API 类型须用 api.at 的
  `pub type X = { f: []T }` 风格（生成 Vec + serde derive） |
| 内联调用结果直接传 str 参数 | E0308 | 不自动借用——先落局部变量 |
| `fs.delete(f2)` 后继续用 f2 | E0382 | delete 路由按值移动参数 |

**其他工程约束（采证中发现）**

- `#[api]` 端点只能声明在 `api.at`（api_gen 仅扫描该文件）；且生成器要求
  api.at 每个端点在 `db.at` 有同名函数，否则拒绝生成（混合状态防护）。
  ⇒ T-02/T-04 的新端点必须 api.at（路由）+ db.at（服务层）成对出现。
- `auto build` 对后端生成有缓存判断；可靠再生路径是 `auto run`。
- sqlite 仅 Rust 侧（无 .vm.at），不可作为可移植存储层。

## 3. 对计划设计的修正

- 设计文档 §4 的目标目录布局（manifest/notes/<id>.json/assets/receipts/journal）
  在「无 read_dir」约束下仍可实现：**manifest 是唯一索引**，实体文件按
  note_id 寻址（不需要目录枚举）；恢复按 journal+收据而非扫描目录。
- 无 rename ⇒ 原子替换不可得；提交协议改为：journal intent（新文件）→
  写 `notes/<note_id>.r<rev>.json`（新文件，天然不可变完整）→ manifest 重写
  （提交点，小文件单写）→ 收据（新文件）。任何一步中断：无收据即未提交
  （AC-02），旧版本文件仍在 manifest 中（AC-01）。
- 无时钟 ⇒ created_at/updated_at 不能在后端生成真实墙钟。修订：
  版本/排序用**持久化单调计数器**（manifest 内），时间戳字段显式 null
  （设计文档"缺失字段显式 null"），并在 Spec 记录该能力边界。
  跨仓缺口登记见 §4。

## 4. 跨仓缺口登记（按计划 §10，不在本计划内修）

1. **a2r facade 缺 `time` 模块再导出**（`a2r_std::time` 路由指向不存在的模块，
   E0433）——时钟类函数在生成后端全不可用。建议 AutoLang 侧补
   `pub use a2r_std::time::*;` 或等价 facade。影响：created_at/updated_at。
2. **`fs.rename`/`read_dir`/`temp_dir` 无 a2r 面**（Plan-250 的 fs.at 只有 VM
   实现）——原子替换与目录枚举缺失。影响：只能采用 journal 协议（本计划），
   未来补齐可简化协议。
3. **`[]T` 用户类型字段 db.at 风格转译缺陷**（E0106 `&[T]`）——已在
   `a2r_std_signature_parity` 之外的新盲区（facade 内联模块 vs stdlib .rs.at
   的漂移）。API 风格类型可绕开。

## 5. 探针复现

见 [README.md](README.md)。探针源码：[probe.at](probe.at)（采证后已从
src/back 移出，避免进入产品代码）；原始证据：[evidence/](evidence/)。
