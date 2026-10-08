# NOTES-001 r5 work 证据（Phase 4：T-17–T-21）

实现提交：见计划 §9 work 记录（code_commit 字段）；基线 `ad3b2a4`（r4-recheck
needs_fix 文档提交）之后。工作树：`D:/autostack/auto-os/apps/015-notes`，分支
`v0.6-dev`（app 约定实现树，无独立 worktree）。

## 绑定

- CLI：`auto 0.1.0+v0.4.2-2785-ga6e108f60`；AutoDown 96f095b（pin=实际）；
  AutoLang main 578794d。SHA256 见 [baseline.json](baseline.json)。
- 构建：`auto build -r vue --gen-only` + `cargo build -p app-015-notes-back
  --offline`（未手改生成 Rust）。
- 结论门：battery S0–S18 exit 0；Vue 24/24（含 r4 负例 3 + r5 负例 3）；
  VM autotest 19/19；VM r5 负例 13/13；后端 scratch 负例 36/36。

## 门与命令

| 门 | 命令 | 证据 |
|---|---|---|
| battery | `NOTES_TEST_MODE=1` 实例（动态隔离目录、无 seed）+ `bash tests/probe/run_v1_battery.sh <独立输出目录>` | [battery-summary.txt](battery-summary.txt)（完整 stdout 落本地 battery-full.log，`*.log` 按仓规不入库，可由命令再生） |
| Vue 全套 | `python tests/probe/evidence/r5-work/run_vue_suite.py`（动态双端口 + seeded 净库） | vue-playwright.log（本地产物，同上）；关键行：`24 passed` |
| VM 原套件 | `python tests/probe/evidence/r5-work/run_vm_suite.py`（`auto run -r vm -B <动态>` + 私有 AUTOUI_MCP_PORT） | [vm-suite-result.json](vm-suite-result.json)（suite_exit=0，19 passed）/ [vm-suite.log](vm-suite.log)（本地产物） |
| VM 负例 | `python tests/probe/evidence/r5-work/run_vm_negative.py`（真实 MCP 驱动 + HTTP 外部写者 + fault 注入） | [vm-negative-result.json](vm-negative-result.json)（fails=[]，13 断言全过） |
| 后端负例 | `python tests/probe/evidence/r5-work/verify_backend_scratch.py`（升级/意图/严格类型全负例） | [scratch-summary.json](scratch-summary.json)（fails=0，36 断言） |

运行纪律：单实例单用途（seeded/电池/负例互不混跑）；动态端口；VM 用私有
MCP 端口隔离；`PYTHONUTF8=1`；每轮净库目录；进程用后即杀。

## 决策制品与 Spec

- [t18-legacy-request-adjudication.md](t18-legacy-request-adjudication.md)：
  旧请求信息有界调查（可恢复 kind/rev、不可恢复内容）与兼容裁决
  （旧行重放一律显式拒绝，不编造收据）。
- [spec-delta-r5-implementation.md](spec-delta-r5-implementation.md)：
  SD-07..16 实现绑定表 + canonical 替换提案全文（merge 阶段发布，本阶段未改
  canonical）。

## 实现修复中的两个过程发现（已修，采证留档）

1. `upgrade_error` 写入曾把动态值拼进 SQL 字符串（SQLite 无 `+` 字符串连接，
   缺列静默失败）——改为 .at 层拼接 + `sql_str` 内插（r4 原代码同型缺陷一并
   修复；scratch U4 首跑即暴露）。
2. UI 保存端点改为 `/api/notes/:id/result` 后，negatives-r4 的路由 glob
   `**/api/notes/*` 不跨 `/` 导致拦截失效（首轮 Vue 套件 R4-2 回归）——
   glob 改 `**/api/notes/**`；r5 负例改用自建探针笔记（自清理），不再依赖
   种子笔记的具体行位。
