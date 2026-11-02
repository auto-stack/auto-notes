# standalone-runtime — 015-notes 独立准备/启动与运行门（current-state）

> 状态：current-state（NOTES-004 实施）· 更新：2026-11-02 ·
> 证据：docs/plans/evidence/004/standalone-decision.md + 计划 §9 收据

## 数据根与门禁

- 数据根：`NOTES_DATA_DIR` 覆盖；未设时 Windows `%APPDATA%` / XDG / 
  `~/.local/share` + `/auto-notes/data`（`src/back/repository.at:33-42`），
  每次解析 `mkdir_all` 兜底。
- 测试端点门禁 `NOTES_TEST_MODE=1`（`src/back/db.at:181`）；电池同一实例不得
  设 `NOTES_SEED`（种子与 migrate 冲突）。

## 正式准备（有界、可重入；verify_standalone S1..S5）

顺序与预算（任一阶段失败非零并保留阶段日志；共享机器缓存允许温加速，
运行自有状态——数据目录/端口——永远新建）：

| 阶段 | 就绪判定 | 预算 |
|---|---|---|
| S1 submodule pin | `git submodule status` 无 `+/-/U` 漂移（c39ac7f9） | 即判 |
| S2 引擎 workspace install | node_modules 在位（pnpm install） | 600s |
| S3 引擎 dist | `dist/index.js`+`style.css` 在位（缺则 `npm run build`，记录 dist-stamp） | 600s |
| S4 前端 scaffold 依赖 | vite.js 在位 | 600s |
| S5 生成+后端 | `auto build -r vue` exit 0（工具宿主间歇静默失败→有界重试×3）+ 后端 exe 在位（缺则 cargo build），exe SHA256 入记录 | 900s/1200s |

## Profile

- **P-V（Vue dev，正式 Vue 门）**：直启后端 exe + vite dev（调用方 env 全程
  控制）；引擎 dev 条件走 `src`（生产条件需 dist）。就绪判定 =
  `/api/v1/status` + 前端 HTTP（≤150s，实测 ~1s）。
- **P-N（原生门）**：`auto run -r vm -B <port>` + `AUTOUI_MCP_PORT`；就绪判定
  = MCP tools/list 应答（≤600s，实测 172–217s）；015-notes.autotest --mode vm
  驱动；N-04 原生形态 = 建存 → `taskkill /T /F` 强杀整树 → 同数据目录重启 →
  重开保真 + 下一次真实编辑保存（revision 推进，SQLite 只读核实）。
- **P-B（构建健康检查）**：`auto build -r vue` 产物构建成功（vue-tsc + vite
  build；生产条件消费引擎 dist）。

## npm 依赖声明（pac.at 形态）

- 受支持形态：`npm_deps: { "@autodown/engine": { file: "path" } }`（对象形态）。
- **数组形态 `"@scope/pkg:file:path"` 不可用**：当前工具链数组解析按首个 `@`
  裸切分，scoped 名必然解析失败并写坏 package.json（NOTES-004 G1 实证）。

## 失败控制（N-05）

- 坏 exe 路径 → spawn 期命名失败非零；端口被占 → 就绪超时/早期退出非零。
- 清理只回收本次 spawn 树（taskkill /T /F 按本次 PID）；旁观实例与共享 target
  不触碰；后端 exe 落点为框架钉定的共享 generated-consumers target——只增不清理。

## 运行纪律（实证入档）

- `CREATE_NO_WINDOW` 下 auto 工具链子进程（tool host/pnpm/cargo）会静默失败
  （同命令带旗标 exit 1、不带 exit 0）——门内一律进程组隔离，不用该旗标。
- bash 门（电池）必须用 Git bash 显式路径：WSL bash 丢弃 Windows 环境变量。
- battery 的 OUTDIR 用相对路径（`.auto/...`，MSYS 命令替换纪律）。
- 已知边界：工具宿主在高并发构建机器上有间歇性静默失败——门内对生成阶段
  有界重试；候选 owner 缺口经 auto-ui plan-007 线修复后未再复现。

## 永久门入口

`tests/basic/verify_standalone.py`（`--profile vue|vm` × `--case n01|n04|suite|all`）：
编排上述准备/隔离启动/用例与失败控制；`vm` profile 在原生门不可用时命名非零
（无静默跳过）。`tests/standalone-recovery.spec.ts` 为 N-04 Vue 形态驱动。
