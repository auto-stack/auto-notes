# NOTES-001:r3 冻结规范增量（待实现与重新复审）

输入：`docs/specs/notes/durable-inbox.md` blob `240b889e6ab3d5794e049b5433cc056ac4934038`。原 SD-01 已发布；下列为对该模块的 modify 提案，本次不发布 canonical Spec，不将目标契约冒充已实现。

| delta_id | operation | target | before → after | rationale / AC |
|---|---|---|---|---|
| SD-02 | modify | docs/specs/notes/durable-inbox.md | 变量级Mutex、exists+write文件锁 → 整事务串行化、原子排他锁与持锁目录绑定、所有写入入口包含迁移均走同门禁 | F-001-01，AC-01/04；跨进程抢锁只能一个写者，8个同revision更新只能一个成功 |
| SD-03 | modify | docs/specs/notes/durable-inbox.md | journal仅意图、manifest/receipt分离、无恢复重放、更新忽略收据失败 → 可靠提交点/完整检查点、恢复上次已确认数据、request_id与实体同事务边界、创建/更新重放原收据、失败不返回虚假committed | F-001-02/05，AC-01/02；保留恢复必需历史，协议原语由T-05实证选择 |
| SD-04 | modify | docs/specs/notes/durable-inbox.md | null终止扫描、报告I/O可忽略 → 精确数组遍历、逐项报告坏项并打捞后续合法项、报告/实体/manifest失败回滚且原件备份保留 | F-001-03，AC-03；[valid,null,valid]→migrated=2,corrupted=1 |
| SD-05 | modify | docs/specs/notes/durable-inbox.md | legacy服务器现读revision再写、UI无版本与恢复草稿 → 客户端提交读取时revision/稳定request_id、冲突保留双方与失败草稿、durable后才清dirty/显示Saved | F-001-04，AC-02/04/05；双客户端陈旧提交拒绝、内容可恢复，Vue/VM一致 |
| SD-06 | modify | docs/specs/notes/durable-inbox.md | 任意request_id直接拼路径、测试端点常驻 → 标识编码/校验限定仓储路径、默认禁用变更型测试端点、仅显式隔离模式启用、移除TEMP调试入口 | F-001-06，AC-02/04/05；路径穿越负例不能越目录/改错对象 |

supersedes_spec_components=[docs/specs/notes/durable-inbox.md]；new_spec_components=[]；touched_goals=[auto-notes/first-real-release]。保持AC-01–AC-05原阈值、纯.at与app仓作用域；若需框架API，以独立依赖计划处理，不在本复审改框架。
