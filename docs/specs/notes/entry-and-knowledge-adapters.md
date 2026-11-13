# entry-and-knowledge-adapters — 015-notes 多入口适配与知识交接（current-state）

> 状态：current-state（NOTES-003 r3 实施：T-01..T-05 交付面）· 更新：2026-11-13 ·
> 计划：NOTES-003 · 依赖：NOTES-001（durable-inbox）+ NOTES-002（quick-card-assets）+
> NOTES-006（featurepack）· SD-01（本文件：多入口能力映射/文件交接/快照导出/
> 来源与手写引用契约）+ SD-02（featurepack 多入口消费节）+ SD-03（quick-card 附件导出消费节）

## 能力矩阵（T-00 冻结，2026-11-13）

| 能力 | 消费面 | capture 实际方法 | 回执 | 不可用结果 |
|---|---|---|---|---|
| Launcher 文件交接 | NOTES_HANDOFF_DIR（incoming/outgoing） | repository.fp_capture / fp_update（006 共享服务，policy 门） | 回执文件 outgoing/<op>.json | 半写/错版本/未知 producer/无授权/未知 note_id/过期修订 → 确定 rejected |
| Jade 快照导出 | NOTES_EXPORT_DIR/<export_id>/ | repository.repo_get + assets 受管原件读取 | 包 ID + note_id/revision 映射 | 缺原件/写失败 → 可重试 err；异 note/revision 撞包 → request_conflict |
| Scape 网页来源 | source/capture（book:web 域） | repository.fp_capture | fp 原收据 | 缺字段/未知版本 → 冻结校验业务前拒绝 |
| Lens 截图区域 | source/capture + 002 附件 | repository.fp_capture + assets.import_attach | fp 原收据 + asset 收据 | 同上 |
| Reader 013 阅读来源 | source/capture（canonical locator/source_hash） | repository.fp_capture | fp 原收据 | 同上；真实链验收归 READER-013 |
| Ink 手写 | ink/save + ink/get | assets.import_attach ×2（图像+模型文本资产） | asset 收据 | 设备缺席 → 能力报告明确未验证项 |

能力投影原则：adapter 只消费系统/服务真实支持集（006 冻结来源 schema、002 受管
原件）；无法协商的能力明确不可用（permission_denied / invalid_request），绝不
伪造可回访或完整来源（source_status 由 006 读投影权威投影）。

## Launcher 文件交接契约（v1）

- envelope v1（文件名 = `<operation_id>.json`，caller harness 写 incoming/）：
  `schema_version`(=1)、`producer`(=launcher，冻结注册表)、`producer_version`、
  `operation_id`（[A-Za-z0-9._:-] 1..=100）、`intent`(capture|update)、`text`
  （1..=16384）；capture 另需 `source`（006 冻结 7 键闭集）；update 另需
  `note_id`（正整数）、`expected_revision`（>=1）。
- 适配器校验序：文件存在且可解析 → schema_version → producer 注册表 →
  operation_id 与文件名一致 → intent/字段。source 冻结 schema 由
  repository.fp_capture 权威校验（业务前拒绝、零写入）。
- 提交通道：capture → fp_capture（幂等按 `fp:<principal>:<operation_id>`）；
  update → fp_update（条件修订）。最终入库由 006/002 完成——文件适配是服务客户端。
- 回执：outgoing/<op>.json，`status`=committed（含 note_id/revision/receipt/
  replayed）| rejected（含 err_code/err_detail）。处理后删除 incoming 文件；
  回执写失败保留 incoming（重试幂等调和）。
- 确定性结果表：半写（解析失败/空）→ invalid_request；错版本 → invalid_request；
  名不匹配 → invalid_request；未知 producer → permission_denied；无授权 cred
  （policy 无条目）→ permission_denied；未知 note_id → not_found；过期修订 →
  revision_conflict；同 operation_id 异载荷 → request_conflict；同包重放 →
  committed + replayed:true（同 note，不重复）。无虚假 committed（任何失败
  均不标 committed）。

## Jade 快照导出契约（v1）

- 触发：`POST /api/entry/v1/jade/export`（note_id、export_id）；包目录
  `NOTES_EXPORT_DIR/<export_id>/`（缺省 `<data>/exports/`）。
- 包内容（已提交修订读取时点快照）：`note.json`（NoteDocument 原样）、
  `note.md`（`# title` + body）、`note.txt`（body）、`source.json`（fp 来源
  快照原文或 `null`）、`attachments/<seq>-<净化名>`（002 受管原件，hash 核验）、
  `manifest.json`（export_id/note_id/revision/producer/source/attachments——
  最后写=完整性标记）。
- 固定映射：同 (note_id, revision, export_id) 重投 → 原包原映射（replayed:true，
  文件不改写）；note 已更新后同 export_id 重投 → request_conflict（明确快照
  失效重试，旧包文件不变、不混合多 revision）；不同 note 撞 export_id →
  request_conflict。
- 可重试状态：缺原件（objects/<sha> 缺失或 hash 失配）→ asset_missing；
  写失败 → storage_unwritable；均无 manifest（未完成标记），恢复后同
  export_id 重试收敛。附件净化名（Windows 非法字符 → '-'）在 manifest
  `file` 字段供接收端定位；`name` 保留原显示名。

## 来源 capture（scape / lens / reader）

- producer 注册表：scape|lens|reader（未知 → permission_denied）。
- scape：网页选区 → fp 来源（book_id=`book:<域>`、source_hash=选区内容哈希、
  title/author/quote 原文、locator={kind:"url", value}）+ 正文 → fp_capture。
- lens：截图区域 → fp 来源（locator={kind:"region", value: 坐标/坐标系/尺寸
  JSON}）+ 正文 → fp_capture；截图原件经 002 import_attach（source="lens"，
  同 note 附件，hash 核验）。
- reader：013 发布的 canonical locator/source_hash 原样保留（锚字段不重组）；
  真实选择与回访验收归 READER-013，本计划只消费其版本化来源样例。
- 重复投递（同 operation_id 同载荷）→ replayed；缺字段/未知版本/哨兵 hash →
  fp 冻结校验业务前拒绝，零写入，不误认完整来源（source_status 投影 ok/
  incomplete 权威区分）。

## Ink 模型契约（v1）

- 触发：`POST /api/entry/v1/ink/save`（note_id、operation_id、image_path、
  image_name、model_json）；`POST /api/entry/v1/ink/get`（note_id）。
- 存储：图像原件走 002 附件（source="ink"）；模型 JSON 文本资产
  （name=`ink-<op>.json`、source="ink"）同 note 第二附件，逐字存储（不重组
  不规范化）。模型内容含 `schema_version`/`canvas`/`coords`/可选 `strokes`/
  `pressure_missing`——缺失 pressure 状态原样保留。
- round-trip：ink_get 返回该 note 全部 ink 资产（模型含对象文本）；坐标/压力
  标志/图像字节与 hash 逐项可核。OCR/AI 是派生结果，缺席不影响保存原件与来源。
- 设备能力报告：测试探针输出实际平台/接口与未验证边界（无真实手写硬件时
  明确 absent/unverified，不跳过图像/模型必需用例）。

## 端点面（本地全权面——不经 fp policy 门；数据归属同 /api/notes）

| 端点 | 说明 |
|---|---|
| POST /api/entry/v1/launcher/scan | 扫描 NOTES_HANDOFF_DIR/incoming/ 逐文件验/提交/写回执/删源；返回 processed/committed/rejected |
| POST /api/entry/v1/jade/export | 快照导出（note_id、export_id） |
| POST /api/entry/v1/source/capture | 来源 capture（cred、producer、operation_id、source_json、text、attachment_path?、attachment_name?——body 信封全字段，非 lens 传空串） |
| POST /api/entry/v1/ink/save | Ink 保存（图像+模型双附件） |
| POST /api/entry/v1/ink/get | Ink 读取（round-trip 核验面） |

实现注：`/api/entry/v1/source/capture` 的 body 信封要求全部字段在位（生成
服务反序列化约束——非 lens producer 传空串）；跨模块用户函数调用收进
entry_adapters 同模块包装（生成器对本地变量/调用表达式不做 &str 转换——
T-00 实测，owner=工具链）。

## 验证入口

- `python tests/basic/verify_entry_knowledge_adapters.py --profile service`
  ——S-01..S-05（I-01 Launcher 全负例+重启重放 / I-03 Jade 快照+可重试 /
  I-04 来源逐项保真+拒绝面 / I-05 Ink round-trip+能力报告 / I-06 收窄拒绝+
  兼容+固定 SHA）。
- `--profile vue`——S 段 + V 段（I-02 小组件/卡片/管理页同 note、真实键入
  提交、外部更新冲突、关闭回主应用、关闭保脏稿）。
- VM 轨：I-02 编辑实例物理输入 = 006 裁定②边界外（BOUNDARY 引用不计退出码）。

## 已登记边界（v0）

- 生成器跨模块 &str 转换缺口（entry_adapters 包装规避，owner=工具链）。
- VM edit 实例物理输入 = 006 裁定②（I-02 输入真实性以 Vue 轨为准）。
- 组件目录单文件生成不传播 store deps（R002 在案）——notes_widget 纯 props
  驱动规避。
- 真实外仓联动（Launcher 桌面/桌面小组件/Jade/Scape/Lens）由各接收仓独立
  计划验收；本计划提供 caller harness/stub 与版本化样例证明接收契约。
