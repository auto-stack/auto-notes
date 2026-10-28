# NOTES-001 修订8（r9 修复）final review（2026-10-29）

结论：**pass**（final，reviewed）。reviewed_commit=`8b64638`（实现+测试；其后仅 docs
后代 b579066/f75bc1a，HEAD=f75bc1a），diff base=`27cff918`。canonical Spec 未动
（blob 8f05b8dd 与复审入口一致）。plan_revision 仍 8（本轮为原范围修复复审，无语义修订）。

## 复审员身份与限制

当前实现会话（/goal 循环单上下文；本计划历史惯例无子 agent）。限制：与 work 同
会话，**不采信 work 阶段摘要**——全部结论由本轮独立重跑的制品重建（见下）。
独立代码阅读：修复 diff（api/db/repository/notes_store）逐行核对，与 SD-03/05/
07/12/24 修正绑定一致，无范围外改动。

## 独立重跑（本轮全部在重建后端 b6b1 上新执行）

| 检查 | 结果 | 证据 |
|---|---|---|
| 复审原输入 api-probes（F-R9-03 判据+fresh 对照） | 9/9 PASS exit0 | .auto/rv2-api-probes.txt（摘要见 fresh-gate-excerpts.txt） |
| 复审原输入 ui-probes（F-R9-01/02 判据+掩盖检查+对照） | 4/4 pass exit0 | [ui-probes-results.json](ui-probes-results.json) |
| api-extra / navigation（r8 复审反例） | 4/4 exit0；pass=true exit0 | .auto/rv2-api-extra.txt、.auto/rv2-navigation.txt |
| battery S0–S22 | **PASSED fails=0**（53 断言） | .auto/rv2-battery/summary.txt |
| scratch（含 U13） | 52/52 fails=0 | .auto/rv2-scratch.txt |
| Vue 全套（含 R9-1..5） | **31 passed suite_exit=0** | .auto/rv2-vue.txt |
| 复审员自选兄弟探针：no-legacy 收尾拒绝 DELETE（work 的 U13 只拒 INSERT） | 拒绝→凭据保留；解除→重试完成代际（2/2） | 本 README 内联（Server 脚手架同 scratch） |

## 指纹 reconcile

- 后端二进制跨构建非确定：work 阶段 35f4…、VM 驱动重链 3e7b…、本轮重建
  b6b1…——同一已提交 .at 源（gen exit0，生成 api.rs=02fad2f2 稳定）的三次构建。
  本收据全部证据统一采自 b6b1 构建；信息级记录，非缺陷。
- CLI=auto-lang e849e06f9 干净重建（auto 0.1.0+v0.5.0-352-ge849e06f9，
  SHA256=3394469248b25d8db3e9705dddda430a4d1202ab98d9a3881c4eb0c05e0566fc）；
  AutoDown c39ac7f（pin=实际）。

## VM 复跑的环境限制（如实记录）

复审另起两次 VM 套件新跑均于 boot 阶段失败（后端进程启动即被环境终止，
exit 0xffffffff，无产品输出；[原始日志](vm-rerun-boot-fail.log)；同日同流程的
r7 驱动会话 1 完整跑通 8 断言后 session-2 boot 才失败——产品 boot 能力在同一
窗口内有成功直接证据）。实现/依赖/验证配置相对 work 轮零变化（docs-only 后代），
按复审复用规则沿用 work 轮同基线 VM 证据（19/19 suite_exit=0 +
[vm-negative-r7-result.json](../001-r9-work-20261015/vm-negative-r7-result.json)
11 断言 fails=0）。该限制不掩盖任何 AC：受影响 store 路径已由本轮 fresh Vue
31/31（真实浏览器）+ battery + scratch 全覆盖。
[重跑失败留档](vm-r7-rerun-result.json)（r7 第二次会话 boot 超时记录）。

## AC 证据映射（final 裁决）

| AC | 判定 | 本轮证据（均 b6b1 fresh） | 前次缺口闭合 |
|---|---|---|---|
| AC-01 确认内容/身份恢复 | **pass** | api-probes fresh 三拒绝+重试、no-legacy 收尾可重试（含 DELETE 拒绝兄弟探针）、battery S1–S3/S9/S11/S21、scratch U1–U12、硬杀/重启路径沿前修订未变证据（本修复未触及提交/重启路径） | F-R9-03（no-legacy 不可重试）闭合 |
| AC-02 同 rid 重放/故障收据 | **pass** | battery S0/S6/S9/S11/S12/S13/S17 fails=0、scratch R1–R3 | 维持（与前轮 pass 同范围） |
| AC-03 迁移幂等/报告/原件 | **pass** | battery S1/S2/S3/S14/S18/S21、scratch M1/U13、api-probes no-legacy+fresh retry | F-R9-03 闭合后升级重试合同完整 |
| AC-04 陈旧写拒绝/修改可恢复 | **pass** | battery S7/S7b fails=0、Vue R9-2/3/5+ui-probes dirty_tag（元数据失败后保存不再自我冲突） | F-R9-02（自身冲突）闭合 |
| AC-05 空库/CRUD/软删恢复 | **pass** | battery S4/S5/S8/S20/S22、Vue 31/31（CRUD+动作失败接收）、smoke | F-R9-01（UI 错误接收）闭合 |

观察（信息级，非阻断）：① `toggle_pin_result` 经 `repo_get("")` 把 open_repository
失败映射为 `not_found`——与旧 `toggle_pin` 形状相同，非本轮新缺口；② 见指纹 reconcile。

## 后续

next=merge（auto-plan-merge）。merge-owned pending：canonical SD-02..28 发布
（[spec-delta-r9-implementation.md](../001-r9-work-20261015/spec-delta-r9-implementation.md)
SHA256=9c495138f500338440cf6b6929a29ad1e8c0c1a5cd9fd7c9d66c754e17fa010b）、派生
索引刷新、归档、恢复收据、工具链 worktree（.wt/notes-cli-r9）wt-guard 后清理。
