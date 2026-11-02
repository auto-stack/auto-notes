# NOTES-004 Spec 增量候选稿（T-04，2026-11-02）

状态：候选（canonical 未发布；merge 阶段按本稿落 docs/specs 并核验）·
依据：[standalone-decision.md](standalone-decision.md) + 门证据
（verify-standalone-1793587845、verify-standalone-1793588185、backend-gates4、scratch-run）

## SD-01 modify — docs/specs/notes/durable-inbox.md

- **before**（现 §回归资产/身份）：「VM 当轮两次 boot 失败，按同源规则复用旧 VM
  19/19 与 11 负例；该裁决保留，但不证明当前工具链独立原生首启」；依赖固定记录
  r9 冻结 CLI（auto-lang e849e06f9 重建）。
- **after**：依赖固定改记当前工具链（auto 0.1.0+plan-890-verified-r7-t19-14-g47d8f7b，
  tool=auto-ui-tool 重建于 2026-11-02 13:09，auto-ui plan-007 合并线；vendor pin
  c39ac7f9 不变）；新增「当前工具链再验（NOTES-004）」小节：battery S0–S22
  fails=0、后端 scratch 52 fails=0、Vue 31/31 passed、原生 015-notes.autotest
  19/19 + r7 VM 反例 11/11 fails=0、双端 N-04 强杀重启后下一次真实编辑成功
  （rev 推进，SQLite 只读核实）——协议面（提交协议/幂等/revision/错误码/UI 契约）
  零改动。
- **rationale**：001 的冻结 CLI 已失存（r9 债项），协议回归须绑定可重建的当前
  工具链；本次双端全绿再验使「协议未回归」不依赖已丢失二进制。
- **acceptance IDs**：AC-02/03/04。

### 回填位（已闭合 2026-11-02）
原生门在 owner 修复落地后复跑通过：P-N 首启 MCP 就绪 176.4s、015-notes.autotest
--mode vm **19/19 exit 0**（当前 CLI 首证）、r7 VM 负例 **11/11 fails=0**。§回归资产
据实增补并删除「不表示当前工具首启已验」caveat；merge 阶段按本稿落 canonical。

## SD-02 add — docs/specs/notes/standalone-runtime.md（新文档）

拟新增 current-state 文档，要点（全部已实证或已定界）：

1. **数据根**：`NOTES_DATA_DIR` 覆盖 → 未设时 `%APPDATA%`（Win）/`XDG_DATA_HOME`/
   `~/.local/share` + `/auto-notes/data`（repository.at:33-42）；每次解析 mkdir_all。
2. **门禁**：测试端点 `NOTES_TEST_MODE=1`（db.at:181）；电池同实例不得设
   `NOTES_SEED`（种子与 migrate 冲突，battery 前置）。
3. **正式准备（有界，verify_standalone S1..S5）**：submodule pin（c39ac7f9，漂移
   即非零）→ 引擎 workspace install（≤600s）→ 引擎 dist（缺则 build，≤600s，
   dist-stamp 记录）→ 前端 scaffold 依赖（≤600s）→ `auto build -r vue` 生成
   （≤900s，工具宿主静默失败有界重试 ×3）→ 后端 cargo build（≤1200s，exe
   SHA256 入记录）。任一阶段失败非零并保留阶段日志。
4. **Profile**：
   - P-V（Vue dev，正式 Vue 门）：直启后端 exe + vite dev，调用方 env 全程控制，
     引擎 dev 条件走 src；就绪判定 = `/api/v1/status` + 前端 HTTP（≤150s）。
   - P-N（原生门，已启用）：`auto run -r vm -B <port>` + AUTOUI_MCP_PORT
     就绪判定（tools/list ≤600s，实测 172–217s）；015-notes.autotest --mode vm
     驱动；N-04 原生形态 = 建存 → taskkill /T /F 强杀整树 → 同数据目录重启 →
     重开保真 + 下一次真实编辑保存。
   - P-B（构建健康检查）：`auto build -r vue` 产物构建成功。
5. **失败控制（N-05）**：坏 exe 路径 → spawn 期命名失败非零；端口被占 → 就绪
   超时/早期退出非零；清理只回收本次 spawn 树；旁观实例/共享 target 不触碰。
6. **运行纪律（实证入档）**：`CREATE_NO_WINDOW` 下工具链子进程静默失败——门内
   一律进程组隔离不用该旗标；bash 门（电池）必须 Git bash（WSL bash 丢弃
   Windows env）；battery OUTDIR 用相对路径。
7. **已知边界**：G4（run_ui vm+rust split 工具宿主静默死亡，owner=auto-ui，
   plan-910 收口后重探）；工具宿主间歇性静默失败与机器并发构建相关（重试纪律）。
- **acceptance IDs**：AC-01/04。

## 未决（已清空）

- G4 已由 owner 修复解除（auto-ui plan-007 线，工具 2026-11-02 13:09 重建）；
  SD-01 回填位与 SD-02 P-N 段均按复跑证据收口。无遗留未决。
