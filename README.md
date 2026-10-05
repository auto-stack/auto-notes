# auto-notes

便笺，使用 AutoLang / AutoUI 开发的独立应用。

本仓是首批产品源码基线；当前能力以导入版本为准，仓库描述中的产品方向不表示全部已实现。

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

AutoOS 通过 [`apps/015-notes`](https://github.com/auto-stack/auto-os/tree/v0.6-dev/apps/015-notes) submodule 固定本仓版本；教学 Demo 保留在来源仓。

已有测试随源导入；端口与平台相关测试需要按本仓配置准备运行环境。安装/启动与双端完整功能验收是不同检查项。

## 产品规划（2026-10-04）

[需求与设计、首版 roadmap、业界调研及前三个实施计划](docs/README.md)。

计划001的Phase 2修复已提交；2026-10-05再次复审仍为needs_fix，已重新激活[修订4/Phase 3修复方案](docs/plans/001-durable-inbox.md)，复现证据见[复审记录](docs/plans/evidence/001-r3-recheck-20261005/README.md)。其他计划与验收状态以各计划证据为准。
