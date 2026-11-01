# auto-notes

便笺，使用 AutoLang / AutoUI 开发的独立应用。

更新：2026-11-01。001可靠Inbox已交付归档/r8、35/35。r9最终复审有Vue31项及API反例；VM当轮boot失败后复用同源旧证据，不表示当前工具首启已验。 本轮未重跑产品验收。

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

001已交付归档，见[001归档](docs/plans/archived/001-durable-inbox.md)和[最终复审](docs/plans/evidence/001-r9-review-20261029/README.md)；当轮VM新跑boot限制仍按原记录保留，004补当前工具下独立原生运行。


## 当前后续计划（2026-11-01）

[NOTES-004：独立启动与原生编辑恢复验收](docs/plans/004-standalone-native-editing.md) 为 **drafting/r1、0/8，尚未实施**。复用001仓储/编辑器/正反例，补真实原生编辑、失败保稿、退出重开与下一次保存；004不等002/003。

先T-00核验实际源码/CLI/编译或渲染tool、已有SDK、冷准备与失败边界；实证缺项才转实际owner最小前置。既有测试入口继续复用，历史绿总数不能替代新必需UI操作。只用隔离数据/本次进程；不清共享target或终止用户实例。无实证业务缺口时不为完成计划强改业务源码。

[路线图](docs/roadmap-v0.6.md) · [现实现规范](docs/specs/notes/durable-inbox.md)。开发与顺序复审在D:/autostack/auto-notes独立clone main，一app一写入者；不在OS组合子模块开发，不建junction/symlink。本轮只准备/提交push计划和导航，不实现、不改Spec/旧ledger和归档，不更新AutoOSpin。各app独立验收后由统一OS计划装配，Linux仍WAIT_DISTRO_M1。

002快速卡片/多媒体/剪贴板接收、003入口/知识交接保留drafting/r2原文，004不等待它们。旧草案中的apps/015-notes、v0.6-dev及自动升级OSpin工作条款由现行独立clone/统一集成安排替代，继续维护时再修订。当前原生/普通dev引擎路径由004验证，不把Blog历史问题直接当本app故障。
