# auto-notes

便笺，使用 AutoLang / AutoUI 开发的独立应用。

更新：2026-11-02。001可靠Inbox已交付归档。004独立启动与原生编辑恢复验收已完成双端门（当前工具链）：原生首启 + 015-notes autotest 19/19 + r7 VM 反例 11/11；Vue 31/31 + battery S0–S22 + scratch 52 全绿；双端强杀重启后下一次保存推进 revision。见[004](docs/plans/004-standalone-native-editing.md)及其[决策稿](docs/plans/evidence/004/standalone-decision.md)。

## 运行

安装对应版本的 `auto` CLI 后，从本仓根执行：

```sh
auto run
auto run -r vm
```

前端端口：`17818`。后端端口：`17819`。

Vue 富文本依赖来自固定的 `vendor/auto-down` 子模块。先执行 `git submodule update --init --recursive`，再在 `vendor/auto-down/autodown/packages/engine` 安装依赖并执行 `npm run build`。旧 editor/core 包已退役。

## 来源与组合

来源提交、路径与文件 hash 见 `SOURCE-IMPORT.json`。首次导入提交保留在 `source-sync` 分支；完整 v0.5 恢复后从该基线导入差异，再与产品开发线合并。

AutoOS 通过 [`apps/auto-notes`](https://github.com/auto-stack/auto-os/tree/main/apps/auto-notes) submodule 固定本仓版本；教学 Demo 保留在来源仓。

已有测试随源导入；端口与平台相关测试需要按本仓配置准备运行环境。安装/启动与双端完整功能验收是不同检查项。

## 产品规划（2026-10-04）

[需求与设计、首版 roadmap、业界调研及前三个实施计划](docs/README.md)。

001已交付归档，见[001归档](docs/plans/archived/001-durable-inbox.md)和[最终复审](docs/plans/evidence/001-r9-review-20261029/README.md)。原「当轮VM新跑boot限制」已由004在当前工具链补齐：原生首启与全套件通过（见004证据稿）。


## 当前后续计划（2026-11-02）

[NOTES-004：独立启动与原生编辑恢复验收](docs/plans/004-standalone-native-editing.md) 双端门已完成（T-01..T-05 全闭合）：复用001仓储/编辑器/正反例，补真实原生编辑、失败保稿、退出重开与下一次保存。既有测试入口全部复用；只用隔离数据/本次进程；不清共享target或终止用户实例。

[路线图](docs/roadmap-v0.6.md) · [现实现规范](docs/specs/notes/durable-inbox.md)。开发与顺序复审在D:/autostack/auto-notes独立clone main，一app一写入者；不在OS组合子模块开发，不建junction/symlink。各app独立验收后由统一OS计划装配，Linux仍WAIT_DISTRO_M1。

002快速卡片/多媒体/剪贴板接收、003入口/知识交接保留drafting/r2原文，004不等待它们。旧草案中的apps/015-notes、v0.6-dev及自动升级OSpin工作条款由现行独立clone/统一集成安排替代，继续维护时再修订。当前原生/普通dev引擎路径由004验证，不把Blog历史问题直接当本app故障。

## 主题（auto-os/PLAN-056 接入）

本产品已接入 AutoUI **官方主题包**正式消费面（2026-11-03，PLAN-056 T-02）：

- `vendor/themes` 为 UI 管理渠道发布的固定版本快照（`themes` 0.2.0，内容
  digest `9fa07742dc68aa5377ae06cb2d966386002063f184c515b6c5dddf8a6bef838e`），
  经 `pac.at` `dep themes` 消费；快照不可二次编辑、非第二权威源。
- 主合同（宿主策略/通知/持久化/拒绝语义）在 **auto-os/PLAN-056**
  （`auto-os` 仓 `docs/plans/056-productivity-products-theme-adoption.md`
  与其 canonical specs）：本产品 pac `theme` 键移除（原 `dark` 显式值退役）
  = **follow 宿主**（宿主策略完整快照 > 本 `design` 默认 > legacy 回退）；
  `src/front/app.at` `design { theme: "Auto", mode: dark_mode 派生 }` 为
  独立/无宿主环境的默认腿（默认暗色语义不变，`use themes.themes: Auto`
  注册收集链——C-11 合同）。
- 品牌与外观面板四色板（indigo/coral/ocean/sage）为 App 命名空间固定值
  豁免，不随主题映射；store `dark_mode`/`accent_color` 业务语义原样。
- 测试设施适配：`tests/desktop_mcp.py` 启动等待 30s→180s（本工具链代次
  back server 每次运行再生成+大仓重链 ~107s，unmodified todo 基线同现
  regen 行为——非本包回归；检查与不变量未改）。


当前 SDK 的文件写入确认兼容由 [计划 005](docs/plans/archived/005-current-sdk-file-write-confirmation.md) 跟踪，作为 [AutoOS PLAN-054](../auto-os/docs/plans/054-basic-apps-unified-assembly.md) 的具名组合前置。
