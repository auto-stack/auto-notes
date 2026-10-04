---
plan_id: NOTES-003
title: "Launcher、小组件与知识交接适配"
status: drafting
feature_name: "Launcher、小组件与知识交接适配"
author: [Codex]
created_at: 2026-10-04T00:00:00Z
updated_at: 2026-10-04T00:00:00Z
plan_revision: 1
current_step: 0
total_steps: 5
created: 2026-10-04
base_branch: v0.6-dev
base_commit: 28d5157b7ed8d4f49e55f835bf8a365d2f97a89a
depends_on: ["NOTES-002"]
supersedes_spec_components: []
new_spec_components: ["docs/specs/notes/entry-and-knowledge-adapters.md"]
touched_goals: ["auto-notes/first-real-release"]
---

# NOTES-003：Launcher、小组件与知识交接适配

## 0. 变更摘要

将导入demo的一项能力发展为可验证的真实产品模块。当前仅获授权编制设计/roadmap/实施计划，未执行代码开发。

## 1. 目标

覆盖需求：N07、N08、N09、N11（定义见[产品设计](../design/01-product-design.md)）。依赖：[NOTES-002](002-quick-card-assets.md)

原始导入commit用于识别来源，不要求后续计划回退到该commit；实际开工从最新v0.6-dev及已验收前序计划起步，在记录中填入实际HEAD。T0是有限能力核查；若需跨仓runtime改动，提交单独设计/计划，当前任务保留未完成验收，不偷偷将真实能力换成stub。

## 2. 架构方案

Notes 内能力协商/集成 adapter 和 demo host；外仓真实 Launcher/Jade/Scape/Lens 接入分别登记，当前计划不改系统宿主。

当前定位：`src/front/app.at`、`src/front/notes_store.at`、`src/front/editor.at`、`src/back/api.at`、`src/back/db.at`。新文件路径以设计表为准，开工核对实际布局后可小幅调整并记录。禁止修改源demo、SOURCE-IMPORT.json、source-sync基线、未同步的四大app及AutoOS主桌面协议。集成使用新增adapter；跨仓依赖单独登记。

## 3. 技术栈

AutoLang/AutoUI `.at`、既有Vue/VM宿主；后端纯.at。协议使用版本化数据，原生能力经adapter接入，不手改生成Rust。

## 4. 需求分析与背景调查

授权：用户要求在四个独立app仓准备需求/设计、首版roadmap和首批实施计划。允许本轮文档编制；产品方向讨论不是本计划代码实现已经批准/完成的证据。

版本证据：frontmatter base_commit与SOURCE-IMPORT.json；源码路径见§2。各app当前没有独立docs/specs模块规范；以代码为观察事实、产品设计为目标态，提案中列出待沉淀规范。AutoOS规约见其AGENTS.md，AutoLang知识规则见docs/specs/README.md。

## 5. 详细设计

### 规范增量

| delta_id | add/modify/retire | 目标 | before/after rule | 理由 | 验收 |
|---|---|---|---|---|---|
| SD-01 | add | docs/specs/notes/entry-and-knowledge-adapters.md | 本模块尚无app级current-state Spec → 记录实际实现的接口、恢复/错误及能力边界 | 供后续agent使用，设计提案不能冒充实现 | AC-01–AC-05 |

### 可执行任务

T-00先行；T-01→T-02→T-03→T-04顺序实施。T-00输出能力报告，T-01形成接口/fixture，T-02/03接入实现，T-04完成整体验证与文档。任务输出见每项说明；T-00/04核查AC-01–05全体，中间任务按对应行为覆盖。每项实测命令/证据写入§9，不把未创建的测试入口说成已有。

- [ ] T-00: 定义 capture/open/export 入口、capability 响应与失败码；用 envelope 文件先完成跨进程交接。
- [ ] T-01: 完成 Launcher caller fixture 和桌面小组件视图；卡片/管理页引用同一 note_id。
- [ ] T-02: 提供 Jade 交接包与收据，原资产/来源可导出；共享对象服务未实现时明确“导出副本”和映射，不能伪装同步。
- [ ] T-03: 为网页选区/截图区域/Reader locator 建立 Scape、Lens、Reader fixtures；验证重复/过期/缺字段行为。
- [ ] T-04: 保存手写图像及 InkAsset schema fixture，输出真实硬件/运行时笔输入能力探针报告；该步骤只验模型与证据，不要求完整画笔。

## 6. 测试设计

数据集：launcher-input、jade-receiver、web-selection、lens-region、reader-quote、ink-v1；tests/fixtures/integrations/（新建）。

在计划worktree根以匹配当前基线的auto CLI分别启动`auto run`与`auto run -r vm`，端口17818 / 17819，使用隔离存储目录。依赖准备见[仓根README](../../README.md)，不得把用户真实数据作为首次迁移样本。

Notes已有Vue测试：运行服务器后，在tests目录配置NOTES_URL=http://localhost:17818并执行npm run test:smoke；完整本计划新增场景追加到tests后按具体spec运行。VM已有autotest驱动，可从仓根运行python tests/run_autotest.py 015-notes.autotest --mode vm --url http://localhost:<实际MCP端口>/mcp；先检查现有case针对哪个窗口和数据。

正确性/恢复/协议测试与UI体验分开记录，至少覆盖一个成功与一个失败路径。现有AutoLang/AutoUI框架不改时不跑cargo全量；若另开框架计划按该仓AGENTS的作用域门禁。文档阶段不运行cargo t/docs_gen。

## 7. 验收标准（必须保留实际证据）

- [ ] AC-01: Launcher caller 到 Notes 完成真实文件交接并获得可复用收据；不要求修改外仓即可复现。
- [ ] AC-02: 同记录在卡片和管理视图打开 ID/revision 一致；适配器不可用有 fallback。
- [ ] AC-03: 一个接收端 stub 验证导出包含正文、资产及来源；报告明确 Jade 真联动是否完成，不能将 stub 标为完成。
- [ ] AC-04: 网页片段、截图与阅读摘录都能存下原文和 locator，并保留 producer；OCR/AI不可用不影响保存。
- [ ] AC-05: 手写原件及坐标模型可 round-trip；能力/设备报告对缺失 pressure 和移动平台范围如实记录。


## 8. 执行步骤与交接

真实宿主联动需要接收仓负责人共同验收；自动标签、完整 OCR/识别、云同步不在这份计划内。

新需求不得在执行中无限追加；发现必要遗漏先更新计划并讨论，不直接删验收项。知识系统/安装服务/AI等未交付依赖必须写明接口级与真实集成的差别。

## 9. 复审记录

- 实际起点HEAD/worktree/工具版本：未执行。
- T0能力与阻塞报告：未执行。
- 各AC项证据路径、命令及结果：未执行。
- 独立复审：未执行；重新对照代码检查AC项、遗漏/延后/workaround、格式/告警/调试输出，不信任已有勾选。
- 债务与风险：未登记；测试真实阻塞不得伪装通过。
- 沉淀：以frontmatter spec-impact候选登记实际实现组件，更新设计能力表与稳定规范；随后翻reviewed并归档。
- 合入目标：v0.6-dev；当前未实施，不合入master、不推进OS gitlink。

[整体roadmap](../roadmap-v0.6.md) · [agent执行说明](../README.md)

## 10. 待澄清事项

T-00需核实实际平台/运行时能力，负责者为本计划执行agent；输出具体API、可复现实验与独立阻塞提案。不存在先执行全局重构的隐含前置。核心验收变更须明确提出，不能用mock替换真实结果。

草案交接：stage=new；plan_revision=1；outcome=pass（可审查的草案，非代码验收）；next=work（选定计划并确认实施范围后）。当前均未实施。
