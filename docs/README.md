# auto-notes 产品规划与执行入口

更新：2026-11-01。001已交付；当前优先004独立运行收口，002/003增强草案保留。

- [产品设计（目标态）](design/01-product-design.md) · [路线图](roadmap-v0.6.md) · [调研](research/20261004-benchmarks.md)
- [现实现规范](specs/notes/durable-inbox.md)

## 计划

| 计划 | 当前状态/用途 |
|---|---|
| [001可靠Inbox](plans/archived/001-durable-inbox.md) | archived/r8、35/35；r9修复与终审已交付，VM当轮boot限制和证据复用保留 |
| [004独立启动与原生编辑恢复](plans/004-standalone-native-editing.md) | drafting/r1、0/8，未实施；复用001仓储/编辑器/反例，先当前工具首启探针 |
| [002快速卡片/多媒体/剪贴板接收](plans/002-quick-card-assets.md) | drafting/r2，原范围/任务未改，不作为004前置 |
| [003入口与知识交接](plans/003-entry-and-knowledge-adapters.md) | drafting/r2，跨app条件另排，不作为004前置 |

## 工作约定

计划/实施/顺序复审在D:/autostack/auto-notes独立clone main，一app一写入者；不以旧apps/015-notes或v0.6-dev作为开发入口，不建junction/symlink。旧草案工作位置条款按最新用户约定替代，本轮保留任务/AC原文。

本轮仅文档准备与push，不实现、不改现实现Spec/旧ledger、不更新OS子模块；独立验收完成后由OS统一计划装配。框架缺项先核验公共能力/实际owner，不等待Blog整份应用计划；Reader的新Readest路线由另会话跟踪。Linux仍等Nix＋COSMIC基础。

[运行与测试完整边界](../README.md) · [001最终复审](plans/evidence/001-r9-review-20261029/README.md)
