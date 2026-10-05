# NOTES-001:r4 冻结规范增量（Phase 3，待实现）

输入：docs/specs/notes/durable-inbox.md blob `8f05b8ddb617d5d64e937e55027e782a2b0c0f85`，当前SQLite r3实现。全部操作modify同一模块，不新增canonical组件，本复审不发布规范。

| delta_id | operation | target | before → after | rationale / acceptance |
|---|---|---|---|---|
| SD-07 | modify | docs/specs/notes/durable-inbox.md | Phase1 JSON不迁移、启动空库 → 旧确认实体/元数据/稳定ID/revision/收据安全事务升级并保留副本，失败显式错误不冒充空启动成功 | F-R4-01，AC-01/03；中文、多行、标签、trash、请求映射正常/硬杀/重试恢复 |
| SD-08 | modify | docs/specs/notes/durable-inbox.md | null无报告、snippet按字节截断、COMMIT后报告失败忽略 → 完整逐项报告与UTF-8安全处理、损坏记录可靠持久化后确认迁移完成、输出失败可重试恢复 | F-R4-02，AC-03；valid/null/valid=2+1、中文无panic、报告I/O失败不得saved成功后skip丢报告 |
| SD-09 | modify | docs/specs/notes/durable-inbox.md | requests只存note_id/kind、当前revision代替原收据 → 存请求目标/类型/规范化意图及原提交revision/收据；匹配才幂等重放，换意图明确拒绝；update故障验证覆盖真实事务边界 | F-R4-03，AC-02/04；rev2请求在rev3后重放仍原收据、跨note/rid不同操作内容不得假成功 |
| SD-10 | modify | docs/specs/notes/durable-inbox.md | 编辑rid恒空、Tag刷新丢草稿、冲突无恢复动作 → 编辑意图稳定非空rid、响应丢失原样重试、所有动作保护草稿与双方版本、成功刷新列表/revision后清dirty | F-R4-04，AC-02/04/05；双UI冲突后tag不丢字、回放恢复Saved、folder flush显示已保存内容，Vue/VM一致 |
| SD-11 | modify | docs/specs/notes/durable-inbox.md | 未跑VM列债务、固定gitlink与实际依赖不符 → 修复commit与固定依赖上重新构建并通过原双端/负例门，不用未验证债务替代required criterion | F-R4-05，AC-01–05；补足测试、逐AC证据和完成计数后才通过/归档 |

supersedes_spec_components=[docs/specs/notes/durable-inbox.md]；new_spec_components=[]；touched_goals=[auto-notes/first-real-release]。

旧AC-01–AC-05原文与门槛保持。SQLite替代文件事务本身有效；本增量修正未满足的旧数据恢复/报告/请求/草稿/验收，不回滚正常改进、不新增产品功能。框架修改须另立最小依赖计划。
