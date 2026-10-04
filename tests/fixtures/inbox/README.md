# Inbox 迁移 fixtures（NOTES-001 T-01）

旧版（导入 demo，v0 基线）持久化形态是 `data/notes.json`：顶层 JSON 数组，
条目字段 `id(int) / title / body / time / pinned / tags([]str)`，
`folder` 在部分历史写法中出现（db.at 种子有、导出文件没有）。

这些 fixture 供迁移与恢复测试使用；每个文件声明期望的迁移结果，
测试不得修改 fixture 原件（迁移测试先复制到独立临时目录再运行）。

| 文件 | 内容 | 期望迁移行为 |
|---|---|---|
| `notes-valid.json` | 3 条合法旧条目，含中文/emoji/多行正文/中文标签，一条带 `folder` | 全部迁入；旧整数 ID 映射到稳定 note_id；空 folder 归为默认 |
| `notes-corrupt.json` | 1 条合法 + 1 条截断损坏 + 1 条合法 | 合法条目迁入；损坏条目进报告并**保留原文件不改动**；不静默丢弃 |
| `notes-bad-types.json` | id 为字符串、tags 非数组、缺 body 字段 | 类型不合法的条目列入报告，不迁入；可救字段按缺失处理只限安全字段（title/body 缺失 → 空串还是拒绝：以实现测试为准，报告必须可读） |
| `notes-empty.json` | `[]` | 迁移为空库；不产生演示种子（AC-05） |

## 约定

- 旧整数 ID 只在首次迁移赋值一次稳定 note_id（`legacy_id → note_id` 持久映射）。
- 迁移前必须备份原文件；迁移失败不得改动原件（AC-03）。
- 重复执行迁移不得重复创建（幂等，AC-03）。
