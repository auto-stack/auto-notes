# NOTES-001 r7 work 证据（Phase 6：T-28–T-33）

工作树：`D:/autostack/auto-os/apps/015-notes` / `v0.6-dev`（app 约定实现树）。
基线：`a2af202`（r6-recheck needs_fix 文档提交）。依赖：CLI auto
0.1.0+v0.4.2-2785-ga6e108f60；AutoLang main 897eb349（r7 复审同期）；AutoDown
96f095b（pin=实际）。终态后端 exe SHA256=5c187b2a…（[baseline.json](../../../tests/probe/evidence/r7-work/baseline.json)）。

## 诊断结论（第三次连续复审失败后的缺口分析）

前三轮的共同模式：**每轮修复引入的新状态机分支没有对应的区分性 oracle，且
测试脚手架自身的失败会被吞掉**（r6 的 S15"修复"实为静默 SyntaxError；本轮
复审再次发现注入未执行）。本轮按合同先补 oracle 再实施：复审的 5 API + 4 Vue
失败断言全部以独立脚本（原样/最小适配）固化为持久资产，battery 注入改为
独立脚本（后置校验 + INJECT_CONTROL 故障自检钩子 + `|| fail` 传播）。

## 六项发现的修复与验证

| 发现 | 修复 | 验证 |
|---|---|---|
| F-R7-01 manifest 身份/类型（T-28/SD-23） | `validate_legacy_entry`：entry 字段类型（revision/seq/legacy_id 整数或历史十进制串、tags 元素字符串、folder/state 字符串、pinned 布尔）+ 与实体 legacy_id/note_id 双向一致；fresh/repair 共用，合并前调用 | independent-api：manifest-identity/types/revision 三拒绝 + valid-control 通过（exit 0） |
| F-R7-02 修复假完成（T-29/SD-24） | repair 路径 UPDATE/凭据清理/代际/收据导入全部检查 exec 结果；失败 ROLLBACK + upgrade_error，凭据保留可重试 | independent-api：repair-update-failure（SQL trigger 合成拒绝）→ 凭据保留；移除后重试恢复权威 |
| F-R7-03 连续未知链（T-30/SD-25） | 未知意图链 prev2（容量 2）：轮换不丢祖先；裁决逐链匹配（server==prev→prev2），仅链上匹配才采纳 revision；槽位携带完整链上下文 | independent-ui repeated_unknown（C1 commit+abort、C2 abort、C3 落地）+ R7-VM-1（C2 真提交变体 4 断言） |
| F-R7-04 稳定动作目标（T-31/SD-26） | SelectNote 捕获目标 id、刷新后按 id 重定位（找不到回落首行）；TogglePinActive/TagAdded/TagRemoved/DeleteConfirmed 绑定 draft_id（pin 目标 flush 前捕获） | independent-ui filtered_navigation + filtered_recovery_pin（R pinned/Z 未动）+ R7-VM-2（4 断言） |
| F-R7-05 满槽状态副作用（T-32/SD-27） | SetSearch 的查询词赋值移入 flushed 分支——满槽阻止 = 查询词/工作集/选择/草稿全部原位 | independent-ui full_slots_search + R7-VM-3（3 断言，含 stash_blocked 可见） |
| F-R7-06 注入假绿（T-33/SD-28） | `tests/probe/inject_legacy_marker.py`：独立脚本 + 后置读回校验 + `INJECT_CONTROL=1` 故障自检；battery 调用点 `|| fail`；S15/S19b 双迁 | battery INJECT-OK ×2；[battery-injection-control.py](../../../tests/probe/evidence/r7-work/battery-injection-control.py) CONTROL PASSED（坏注入→battery 非零且原因在案）；复审 battery-control 亦 pass |

## 门（终态二进制 5c187b2a…）

| 门 | 结果 | 证据 |
|---|---|---|
| fresh gen/build | exit 0 | 本地日志（*.log 不入库） |
| battery S0–S19 | exit 0 PASSED（注入 INJECT-OK ×2） | [battery-summary.txt](../../../tests/probe/evidence/r7-work/battery-summary.txt) |
| 后端 scratch | 38/38 fails=0 | [scratch-summary.json](../../../tests/probe/evidence/r5-work/scratch-summary.json) |
| 独立 API（复审脚本原样） | exit 0，5 断言过 | [independent-api-green.log](../../../tests/probe/evidence/r7-work/independent-api-green.log) |
| 独立 Vue（复审脚本原样） | exit 0，4 场景过 | [independent-ui-r7-green.json](../../../tests/probe/evidence/r7-work/independent-ui-r7-green.json) |
| Vue 全套 | 24/24 suite_exit=0 | [vue-playwright.log](../../../tests/probe/evidence/r7-work/vue-playwright.log) |
| VM 原套件 | 19/19 suite_exit=0 | [vm-suite-result.json](../../../tests/probe/evidence/r7-work/vm-suite-result.json) |
| VM r5 负例 | 13/13 fails=[] | [vm-negative-r5-result.json](../../../tests/probe/evidence/r7-work/vm-negative-r5-result.json) |
| VM r7 负例（新增） | exit 0，7 断言过 | [run_vm_negative_r7.py](../../../tests/probe/evidence/r7-work/run_vm_negative_r7.py) / [vm-negative-r7-result.json](../../../tests/probe/evidence/r7-work/vm-negative-r7-result.json) |
| 注入失败控制 | CONTROL PASSED | [battery-injection-control.py](../../../tests/probe/evidence/r7-work/battery-injection-control.py) |
| 复审 battery-control | pass=true（断言失败传播） | 复审包原脚本，本轮重跑 exit 0 |

运行纪律沿前轮：动态端口、单实例单用途、VM 私有 MCP 端口 + 净库单轮、
PYTHONUTF8、VM 与持 exe 门串行。

## 过程发现（留档）

1. **VM 渲染序约束（延续 r6）**：stash 路径的 `.notes` 整表赋值破坏侧栏渲染
   ——刷新保持在 saved-only 分支。
2. **MCP 点击在重渲染后可能落在旧 vnode 上不分发**——驱动用
   "点击至状态生效"重试（标准 UI 自动化手段）；产品无恙（同路径 Vue 真实
   浏览器断言通过）。
3. **驱动自身的测试教训**：搜索过滤后点击行再清过滤 = 全量刷新 + LoadDraft
   把编辑器重置回首行（F-R7-04 的驱动版镜像）——驱动选择器一律
   "搜索定位并保留过滤"；跨会话断言必须用当前标题（会话 1 已改名）。
4. `.at` 单引号字面量在 == 比较上下文被发射为 char（i64）——字符串比较一律
   用 `"\""` 转义形式（本次 valid_int_field 曾踩）。
