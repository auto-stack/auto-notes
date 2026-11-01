# auto-notes：独立可用性路线图

更新：2026-11-01。以Spec与真实交付为准，计划目标不表示已实现。

| 顺序 | 计划/成果 | 当前状态与边界 |
|---|---|---|
| 基础 | [001首轮能力](plans/archived/001-durable-inbox.md) | 001可靠Inbox已交付归档/r8、35/35。r9最终复审有Vue31项及API反例；VM当轮boot失败后复用同源旧证据，不表示当前工具首启已验。 |
| 当前优先 | [NOTES-004：独立启动与原生编辑恢复验收](plans/004-standalone-native-editing.md) | drafting/r1、0/8，未实施；先T-00核实当前工具/SDK与实际owner |
| 之后 | AutoOS统一装配 | 另立统一OS计划，接收各app单独验证/推送的精确提交；本轮不改pin |
| 之后 | Linux支持 | WAIT_DISTRO_M1，等Nix＋COSMIC发行版基础；不阻塞本app本机任务 |

复用001仓储/编辑器/正反例，补真实原生编辑、失败保稿、退出重开与下一次保存；004不等002/003。

002/003增强/跨app合同保持草案，004不以它们为前置；Reader→Notes交接不在本轮。

工作位D:/autostack/auto-notes独立clone main，实施与独立上下文复审顺序共用，一app一写入者。复用既有验证入口；真实UI/磁盘oracle对应本次源码和CLI/tool，无必需skip/零场景。失败控制要能检测实际错误，只回收本次进程/隔离数据，不清共享缓存。

本轮只规划/README/roadmap并push，不实现、不写现实现Spec/旧ledger或改001归档，不更新AutoOS子模块。Reader新目标由单独会话跟踪，Blog上游问题沿原合同继续，不作为本计划的全局前置。

[README](../README.md) · [现实现规范](specs/notes/durable-inbox.md)
