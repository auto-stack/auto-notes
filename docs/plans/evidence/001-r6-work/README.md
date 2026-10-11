# NOTES-001 r6 work 证据（Phase 5：T-22–T-27）

工作树：`D:/autostack/auto-os/apps/015-notes` / `v0.6-dev`（app 约定实现树）。
基线：`9a22886`（r5-recheck needs_fix 文档提交）。依赖：CLI auto 0.1.0+v0.4.2-2785-ga6e108f60；
AutoLang main c64b7135（复审同期）；AutoDown 96f095b（pin=实际）。SHA256 见
[baseline.json](../../../tests/probe/evidence/r6-work/baseline.json)。

## 诊断检查点（第二次连续复审失败后的契约/断言缺口分析）

r5 修复的五项失败均源于同一类缺口：**负例只覆盖了各自修复的主路径，未覆盖
修复自身引入的次生状态机分支**（冲突错误被当修复凭据、修复合并无条件覆盖、
实体只查语法、Recover 单分支加守卫、flush 无轮换）。r6 的回归资产直接把
复审的 3 API + 2 Vue + 2 VM 失败断言固化为持久测试（battery S19、
independent 脚本入库副本），并补 S15 空洞断言修复（mis-mark 注入此前静默
SyntaxError，断言空洞——已改参数化 SQL）。

## 门与命令（终态二进制 backend exe SHA256=cc422c9a…）

| 门 | 结果 | 证据 |
|---|---|---|
| fresh gen/build | exit 0 / 0 | build 日志本地（*.log 按仓规不入库） |
| battery S0–S19 | exit 0（39 断言，含新 S19a/b/c） | [battery-summary.txt](../../../tests/probe/evidence/r6-work/battery-summary.txt) |
| 后端 scratch | 38/38 fails=0（含新 U9 路径/U10 身份） | [scratch-summary.json](../../../tests/probe/evidence/r6-work/scratch-summary.json) |
| Vue 全套 | 24/24 suite_exit=0 | [vue-playwright.log](../../../tests/probe/evidence/r6-work/vue-playwright.log) |
| VM 原套件 | 19/19 suite_exit=0 | [vm-suite-result.json](../../../tests/probe/evidence/r6-work/vm-suite-result.json) |
| VM r5 负例 | 13/13 fails=[] | [vm-negative-r5-result.json](../../../tests/probe/evidence/r6-work/vm-negative-r5-result.json) |
| 独立 API（复审脚本原样） | exit 0 oracle_failures=[] | [independent-api-r6.json](../../../tests/probe/evidence/r6-work/independent-api-r6.json) |
| 独立 Vue（复审断言+环境适配） | exit 0 oracle_failures=[] | [independent-ui-r6.json](../../../tests/probe/evidence/r6-work/independent-ui-r6.json) / [适配副本](../../../tests/probe/evidence/r6-work/independent-ui-r6.cjs) |
| 独立 VM（复审断言+环境适配） | exit 0 IND-VM-1/2 PASS | [适配副本](../../../tests/probe/evidence/r6-work/run_independent_vm_r6.py)（vm-negative-result.json 落各自 run 目录） |

运行纪律沿 r5：动态端口、单实例单用途、VM 私有 MCP 端口、PYTHONUTF8、净库单轮。

## 环境适配与过程发现（均留档，不改变断言）

1. **独立驱动的三处适配**（动作差异是修复行为的直接结果，断言未动）：
   - UI：`.cjs` 以仓根为 cwd 启动（原包装 cwd=tests 使 `process.cwd()+'/tests/...'`
     解析失败——原脚本环境笔误）；Recover/Save 点击按状态守卫（修复后 C2 可在
     导航 flush 中被裁决直接落地，无恢复横幅可点）。
   - VM：同上状态守卫；R5-VM-3 的状态/服务端读取轮询到 dirty 清零
     （裁决链多跳 HTTP，autoui_state 会在 handler park 期间应答——读竞态非产品失败）。
2. **VM 渲染敏感点（产品代码已回退到 r5 验证过的位置）**：冲突入槽路径上的
   `.notes = list_notes()` 刷新曾使侧栏列表在 VM 渲染层整体消失（store 数据完好、
   visible 索引正常）。刷新已移回 saved-only 分支（与 r5 行为一致）；
   debug 脚本 [debug_vm_r5vm1.py](../../../tests/probe/evidence/r6-work/debug_vm_r5vm1.py) 留档复现路径。
3. **wait_ready 弱门补强**（tests/autotest/__init__.py）：静态壳先于 App_Init 渲染，
   Init park 于 list_notes 时套件即开跑（T0–T5 曾连锁失败）。现要求 draft_title
   非空（Init 完成的可观察信号）。
4. **battery S15 空洞断言修复**：mis-mark 注入块的转义引号曾产生静默 SyntaxError，
   注入从未执行、断言空洞——改参数化 SQL 后 S15 真实验证修复路径。

## T-26 决策制品

[t26-legacy-compat-table.md](t26-legacy-compat-table.md)：逐类旧请求兼容表 +
相对原 AC-02 承诺的具体差异 + 三个决策选项（ awaiting user decision）。

## Spec

SD-17–22 实现绑定 diff：[spec-delta-r6-implementation.md](spec-delta-r6-implementation.md)
（canonical 未动；发布=merge 门）。
