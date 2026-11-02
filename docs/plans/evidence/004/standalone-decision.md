# NOTES-004 T-00 决策稿：独立准备/启动 profile（草稿，随探针回填）

状态：T-00 进行中（探针日期 2026-11-02）· 计划：NOTES-004 r1
原始日志：`D:/autostack/plan-artifacts/plan-004/t00/`（不入口）

## 1. 固定身份（本轮工具链实测）

| 项 | 值 | 发现路径/证据 |
|---|---|---|
| 固定源码 | auto-notes main @ `4a09b0d` + 本轮 pac.at 修复（T-00 起实现提交另行记录） | 本仓 git |
| vendor pin | `vendor/auto-down` submodule @ `c39ac7f9`（与 001 r9 pin 相同） | git submodule status |
| CLI | `auto 0.1.0+plan-890-verified-r7-t19-5-g55c98c7`，exe `D:/autostack/auto-man/target/debug/auto` | `auto --version`；源 auto-man @ `67add3c`（main） |
| 工具发现链 | `C:/Users/zhaop/.auto/auto-man/am.at` → index store `C:/Users/zhaop/.auto/auto-man/index/default`（gitee auto-index）→ port builder `windows_ninja`；UI 工程 build/run/gen 经工具进程（auto-ui-tools，源 `D:/autostack/auto-ui` @ `2f43b4f` 构建期检出） | `auto info` 输出 |
| 后端依赖仓 | rust-workspace workspace deps → `D:/autostack/auto-lang` @ `5923d4dee`（plan-910 线）、`D:/autostack/auto-web` | rust-workspace/Cargo.toml 生成物 |
| 其余工具 | cargo/rustc 1.98.0、node v25.2.1、pnpm v11.6.0、Python 3.14.2（tests 走系统 python） | `--version` |
| 后端 exe 落点 | 生成 workspace 的 `.cargo/config.toml` 把 target-dir 钉到共享 `D:/autostack/auto-lang/target/generated-consumers/f3f98a9e`（框架管理；exe `auto-notes-30db9907-back.exe`，SHA256 `f6ad7af6…47`）——共享消费 target，本计划只增不清理 | rust-workspace/.cargo/config.toml + sha256sum |

## 2. 实证缺口与本次处置（T-00 探针，均在当前真实 app 上复现）

| # | 缺口 | 证据 | 处置 | owner |
|---|---|---|---|---|
| G1 | pac.at `npm_deps: ["@autodown/engine:file:path"]` 数组形态被当前工具误解析：`auto-ui-tools` `npm_deps_from_value` 对数组项按首个 `@` 裸切分，scoped 名首字符即 `@` → 整串成为包名 + `latest` 版本，写入非法 package.json → `pnpm install` 失败（`ERR_PNPM_INVALID_DEPENDENCY_NAME`）；重试还会清空既有 node_modules | t00/build-vue.log（EXIT=1） | **app 侧改用受支持的对象形态** `{ "@autodown/engine": { file: "…engine" } }`（vue.rs 显式支持 `{link/file: path}`），复测 install 通过（350 包，t00/build-vue-2.log） | auto-ui（数组形态 scoped 解析），本计划不改越仓实现，仅记录 |
| G2 | Vue 生产构建需引擎 `dist`（`./style.css` default → `dist/style.css`）；vendored engine 无预构建 dist | t00/build-vue-2.log（rollup resolve 失败） | 按 README 冷准备：`pnpm install`（autodown workspace）+ `npm run build`（packages/engine）→ exit 0，dist-stamp `f46a2f188e86faab`（t00/engine-build.log） | 无（文档化准备步骤） |
| G3 | 新 CLI 生成后端改写 `rust-workspace/auto-notes-30db9907-back/`（hash 后缀）并把旧 `auto-notes-back`（10-14 旧 CLI 产物，要求 feature `image-pipeline`，当前 auto-lang 0.2.0 已移除）留在 members → 整 workspace 解析失败（cargo exit 101） | t00/cargo-back-build.log | 清除本仓旧生成物目录并收敛 members 为新 crate（生成物 git-ignored，非产品源码）；复测 cargo 构建通过（t00/cargo-back-build-2.log） | 无（旧生成物清理属本仓常规生命周期；CLI 不清理旧 member 属工具债，记录） |
| G4 | `auto run -r vm`（vm↔rust split）当前工具链**间歇性**失败：工具宿主静默消失（`run_ui failed: tool host closed the control stream`）或长时间静默无输出；固定复现因素为本仓 back 源 + api:"rust"（merged vm+vm 同 app stub 可过、stub back 可走到 cargo 具名错误）；同期机器上有他session重 cargo/nextest 竞争共享 target | t00/vm-fg.log、vm-bisect-v0*.log、vm-retry-*.log | 按 auto-database plan-002 同症先例（evidence/002/native-ui-decision.md：间歇性、再生期多见、**重试可通过**）以**有界重试 + MCP 就绪客观判定**推进（r9 驱动同款，boot 窗 600s）；复现矩阵与责任归 auto-ui/auto-man（run_ui vm+rust split 链路，含 plan-910 managed cargo context 新路径），本计划不越仓改实现 | auto-ui（owner） |

## 3. 数据根/测试模式（当前源码核实，非历史默认）

- `NOTES_DATA_DIR` 覆盖数据根；未设时 Windows `%APPDATA%/auto-notes/data`（`src/back/repository.at:33-42`）。
- 测试端点门禁 `NOTES_TEST_MODE=1`（`src/back/db.at:181`）；种子 `NOTES_SEED=1`；故障/迁移 fixture 同 001（v1/test/* 门禁内）。

## 4. Profile 记录（分开）

### P-V（Vue dev——r9 既证模式，候补正式 Vue profile）
- 组成：直启后端 exe（`rust-workspace/target/debug/auto-notes-<hash>-back.exe`）+ `vite` dev server（`gen/front/vue`），env 全程调用方控制；引擎经 vite `development` condition 走 `src/index.ts`（无需 dist）。Playwright 套件（31 项）+ r9 反例。
- 首启复验：见 §6。

### P-B（Vue 构建模式）
- `auto build -r vue` → vue-tsc + `vite build`（生产条件 → 需引擎 dist）；产物 `gen/front/vue/dist`。与 P-V 的差异仅解析条件与产物形态；本轮验收以 P-V 为 Vue 正式入口，P-B 作为构建健康检查记录（G2 后已可构建，终态见 §6）。

### P-N（原生真实页面——正式 native profile）
- `auto run -r vm -B <back>`（CLI 进程内 AutoVM+iced 原生窗口）+ `AUTOUI_MCP_PORT` 暴露 MCP；驱动 `tests/run_autotest.py 015-notes.autotest --mode vm --url http://127.0.0.1:<mcp>/mcp`（001 同款）；隔离 `NOTES_DATA_DIR`。
- 首启复验：见 §6（当前 CLI 的 VM/MCP 链路为本轮新增必验项——r9 的 VM 证据来自 auto-lang e849e06f9 重建 CLI，不覆盖本工具链）。

### 正式 profile 选择
Vue 门 = P-V（复用 r9 套件与反例，环境可控）；原生门 = P-N（唯一原生真实页面证据源）。两者都在 verify_standalone.py 中编排（T-04）。

## 5. 冷准备预算（实测回填）

| 阶段 | 就绪判定 | 实测 | 预算上限 |
|---|---|---|---|
| submodule 状态 | `git submodule status` 无 `+/-` | 本轮 c39ac7f9 干净 | 记录即判 |
| 引擎 workspace install | pnpm exit 0 | 5.7s（温缓存） | 600s |
| 引擎 build（dist） | `npm run build` exit 0 + dist-stamp 写入 | ~5s（温）+ 4.4s vite | 600s |
| 前端 scaffold install | pnpm install exit 0（auto build 内含） | ~1.1s（温） | 600s |
| 后端生成 | `auto build`/`auto run` 生成日志 Rust server 完成 | <5s | 120s |
| 后端 cargo build | exe 存在且 exit 0 | 见 §6 回填 | 1200s |
| 失败语义 | 任一阶段非零 → 中止并保留日志，非零退出 | G1/G3 均非零暴露 ✓ | — |

失败控制（N-01 负控）沿用：坏 tool 路径（AUTO_CLI/直启 exe 不存在）→ 非零；端口占用 → 就绪等待超时非零；不触碰旁观实例（进程按本次 spawn 树 taskkill /T）。

## 6. 首启复验（终态 2026-11-02）

- [x] **P-V 首启 PASS**：空缓存数据目录 + 动态端口，直启 exe + vite dev，就绪 0.9s；真实 UI 冒烟 exit 0（t00/pv-first/）。**全套 31/31 passed（3.5m，t00/vue-full.log）**——当前工具链 + 新后端 exe，Vue 轨回归绿。
- [x] P-B 构建：`auto build -r vue` 走到 vue-tsc + vite build（引擎 dist 就位后经 G1 修复可安装依赖；生产构建产物生成）。作为构建健康检查记录。
- [x] 后端 cargo build：exit 0，3m06s（共享 target 温依赖；日志 t00/cargo-back-build-2.log）。
- [x] **P-N 首启 FAIL——框架缺口 G4**：`auto run -r vm`（vm↔rust split）10+ 次有界尝试（4s 速死 / 96–132s 生成完成后静默死亡两种形态，t00/pn-boot/、vm-suite-t00*.log）0 次到达 MCP 就绪；merged vm+vm（同 app 去 api）与最小 hello app 均可过（隔离矩阵 t00/vm-bisect-*.log）；直接驱动工具内部执行臂可获真实 VM 编译诊断（stylekit 依赖在宿主流外不解析，非产品缺口）。结论：**原生门当前工具链不可用，owner=auto-ui**（run_ui vm+rust split 链路；plan-910 rust-ui 重写恰好于当日 02:23–06:48 落地、工具 07:21 重建，与故障强相关）；auto-database plan-002 有同症先例（11-01 工具间歇性、重试可通过——plan-910 落地后本仓 0/10+，更严）。按计划 §2/§10 挂起等待用户裁决，不越仓改实现。
- [ ] （解除 G4 后）P-N 首启 + 015-notes.autotest --mode vm + r9 VM 反例，重开 T-01/T-02/T-03/T-04 原生半区。
- [x] 数据根/门禁 env 传播：直启 exe `NOTES_DATA_DIR` 隔离有效（t00/pv-first/data/inbox.db 落位；status 端点回显 data_dir）。
