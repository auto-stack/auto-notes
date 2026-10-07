# NOTES-001:r5 冻结规范增量（Phase 4，待实现）

输入：canonical `docs/specs/notes/durable-inbox.md` blob `8f05b8ddb617d5d64e937e55027e782a2b0c0f85`及r4提案SD-07–11。保留原AC-01–05，不在本次复审发布规范。

| delta_id | operation | target | before → after | rationale / acceptance |
|---|---|---|---|---|
| SD-12 | modify | docs/specs/notes/durable-inbox.md | 旧升级只读实体元数据、备份失败/坏实体仍标完成 → manifest权威元数据完整合并，校验备份与旧布局，失败显式且可恢复重试 | F-R5-01，AC-01/03/05；标签、置顶、folder、trash与旧load_doc一致 |
| SD-13 | modify | docs/specs/notes/durable-inbox.md | 任意字段管道拼接意图、旧行通配/原rev缺省1 → 无歧义意图与持久版本迁移、旧请求可恢复信息有界调查，不虚假确认不同操作/意图、不编造原收据 | F-R5-02，AC-02/04；含管道字段/旧JSON收据/旧SQLite行负例，未知兼容变更须显式提案 |
| SD-14 | modify | docs/specs/notes/durable-inbox.md | Recover先覆盖rec槽、Discard读旧列表、未确认请求更改内容沿用rid → 两份草稿及既有恢复槽安全保全、最新服务器版可选择、未确认提交与后续新意图正确裁决 | F-R5-03，AC-02/04/05；Vue/VM实测Recover/Discard、响应丢失后继续编辑 |
| SD-15 | modify | docs/specs/notes/durable-inbox.md | boolean ID/非字符串body/tags元素静默导入、snippet型别不符 → 完整逐项类型验证与可诊断字符串报告，保留原件并迁入后续合法项 | F-R5-04，AC-03；坏类型明确入报告而非默认值丢内容 |
| SD-16 | modify | docs/specs/notes/durable-inbox.md | r3 canonical与r4代码不符且归档后延后沉淀 → work准备实际契约diff、review验证、merge发布与准确索引/计数关闭记录 | F-R5-05，AC-01–05；不将关闭操作冒充实现正确性，不将未沉淀提案冒充current-state |

supersedes_spec_components=[docs/specs/notes/durable-inbox.md]；new_spec_components=[]；touched_goals=[auto-notes/first-real-release]。全部为原验收/关闭缺口修正，SQLite有效改进保留；框架修改另立最小依赖计划。T-18若证明旧请求信息不可重建，需先提交具体兼容决策，不自行减弱原AC。
