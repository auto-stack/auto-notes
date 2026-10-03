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
