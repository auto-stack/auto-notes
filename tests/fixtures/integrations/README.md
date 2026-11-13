# tests/fixtures/integrations — NOTES-003 多入口适配样例（T-00 冻结形态）

版本化来源/交接样例，供 verify_entry_knowledge_adapters.py 直接消费；电池亦可
程序化构造同形输入。字段语义见 docs/specs/notes/entry-and-knowledge-adapters.md
（SD-01，交付时发布）。

| 文件 | producer | 用途 |
|---|---|---|
| launcher-capture-v1.json | launcher | 文件交接 envelope v1（capture：来源+正文） |
| source-scape-v1.json | scape | 网页选区来源（url locator + 选区 hash） |
| source-lens-v1.json | lens | 截图区域来源（region locator：坐标/坐标系/尺寸 + 原件 hash） |
| source-reader-013-v1.json | reader | 013 canonical 阅读来源（locator/source_hash 原样保留，锚语义归 READER-013） |
