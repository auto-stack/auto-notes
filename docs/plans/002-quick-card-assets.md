---
plan_id: NOTES-002
title: "快速卡片、多媒体收存与剪贴板接收"
status: drafting
feature_name: "快速卡片、多媒体收存与剪贴板接收"
author: [Codex]
created_at: 2026-10-04T00:00:00Z
updated_at: 2026-10-04T00:00:00Z
plan_revision: 1
current_step: 0
total_steps: 5
created: 2026-10-04
base_branch: v0.6-dev
base_commit: 28d5157b7ed8d4f49e55f835bf8a365d2f97a89a
depends_on: ["NOTES-001"]
supersedes_spec_components: []
new_spec_components: ["docs/specs/notes/quick-card-assets.md"]
touched_goals: ["auto-notes/first-real-release"]
---

# NOTES-002：快速卡片、多媒体收存与剪贴板接收

## 0. 变更摘要

将导入demo的一项能力发展为可验证的真实产品模块。当前仅获授权编制设计/roadmap/实施计划，未执行代码开发。

## 1. 目标

覆盖需求：N02、N03、N04、N06、N10、N13（定义见[产品设计](../design/01-product-design.md)）。依赖：[NOTES-001](001-durable-inbox.md)

原始导入commit用于识别来源，不要求后续计划回退到该commit；实际开工从最新v0.6-dev及已验收前序计划起步，在记录中填入实际HEAD。T0是有限能力核查；若需跨仓runtime改动，提交单独设计/计划，当前任务保留未完成验收，不偷偷将真实能力换成stub。

## 2. 架构方案

新增 quick_card/capture/assets 模块及可导入的 clipboard envelope；保留完整管理页与既有富文本依赖。

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
| SD-01 | add | docs/specs/notes/quick-card-assets.md | 本模块尚无app级current-state Spec → 记录实际实现的接口、恢复/错误及能力边界 | 供后续agent使用，设计提案不能冒充实现 | AC-01–AC-05 |

### 可执行任务

T-00先行；T-01→T-02→T-03→T-04顺序实施。T-00输出能力报告，T-01形成接口/fixture，T-02/03接入实现，T-04完成整体验证与文档。任务输出见每项说明；T-00/04核查AC-01–05全体，中间任务按对应行为覆盖。每项实测命令/证据写入§9，不把未创建的测试入口说成已有。

- [ ] T-00: 给 capture envelope 写验证器和幂等收据逻辑；实现文字、URL、图片、本地视频与文件资产复制，拒绝不支持格式并保留输入。
- [ ] T-01: 完成 hash/type/大小校验、暂存到持久化的恢复流程；首版建议图片20MiB、视频200MiB默认上限并可配置，超限不自动压缩原件。
- [ ] T-02: 实现卡片焦点、自动保存、IME、Ctrl+Enter/Esc、错误重试、附件状态和来源显示。
- [ ] T-03: 实现当前剪贴板显式粘贴及 bin 多项 fixture 导入；由 bin 负责历史采集，Notes 只消费用户选择。
- [ ] T-04: 增加卡片到管理页同 ID 导航、图片缩略图、视频原件打开/导出；媒体解码失败仍可管理文件。

## 6. 测试设计

数据集：URL+选区、文本+图片混合、损坏图片、Unicode 文件名、同 hash 不同名称、缺失文件、200MiB边界、IME录屏；tests/fixtures/capture/（新建）。

在计划worktree根以匹配当前基线的auto CLI分别启动`auto run`与`auto run -r vm`，端口17818 / 17819，使用隔离存储目录。依赖准备见[仓根README](../../README.md)，不得把用户真实数据作为首次迁移样本。

Notes已有Vue测试：运行服务器后，在tests目录配置NOTES_URL=http://localhost:17818并执行npm run test:smoke；完整本计划新增场景追加到tests后按具体spec运行。VM已有autotest驱动，可从仓根运行python tests/run_autotest.py 015-notes.autotest --mode vm --url http://localhost:<实际MCP端口>/mcp；先检查现有case针对哪个窗口和数据。

正确性/恢复/协议测试与UI体验分开记录，至少覆盖一个成功与一个失败路径。现有AutoLang/AutoUI框架不改时不跑cargo全量；若另开框架计划按该仓AGENTS的作用域门禁。文档阶段不运行cargo t/docs_gen。

## 7. 验收标准（必须保留实际证据）

- [ ] AC-01: 断网下文字、链接、图片、一个本地视频均可收存并在重启后导出，导出 hash 与原件一致。
- [ ] AC-02: 完成/关闭/快速重复点击不丢中文输入、不创建重复笔记；IME Enter 不误关闭。
- [ ] AC-03: 含附件的请求在复制和正文提交之间中断，恢复不会返回虚假的 committed。
- [ ] AC-04: 不支持 MIME、越界文件、超限/不可写均给出可操作错误；外部服务不可用时纯文本卡片仍可记录。
- [ ] AC-05: 剪贴板多项保留来源顺序与选择意图；重复发送用同 request_id；正文相同的新记录可独立创建。


## 8. 执行步骤与交接

依赖尚不存在的 clipboard-bin 历史服务使用明示 fixture，不把 fixture 算真实系统联动。

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
