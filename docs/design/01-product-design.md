# Auto Notes：需求、架构与 UI/UX

状态：proposed；版本：设计 0.1；日期：2026-10-04；面向 AutoOS v0.6 的首个真实应用版本。便签继续独立建仓，不合并入 jade-edit。

## 1. 产品目标与分工

在工作、阅读和浏览中，用户用最短路径留住灵感或资源，稍后在 Inbox 或 Jade 继续处理。默认入口是桌面小组件、Launcher 或轻量快速卡片；完整应用只是管理和回顾的入口。这里的 flash card 指快速记录卡片，不是首版必须实现的间隔复习记忆卡。

Notes 负责捕获、轻量编辑、附件、暂存、便签列表。Jade 负责长期知识组织、链接、专题、检索和深入编辑。copy-paste bin 负责短期复制历史；用户挑选后才成为持久记录。Notes 可以显示同一知识对象的简洁视图，不能为每个入口复制一个新笔记。

成功场景：复制一段链接和图片 → Launcher“记录到 Inbox” → 卡片补一句话 → 看到已保存 → 关闭 → 重启找回原文和图片 → 在 Jade 打开或导出同一个有来源的对象。

## 2. 当前代码审计

`src/front/app.at` 为导航树和 EditorPanel 的完整应用；`notes_store.at` 有选中项、目录/置顶筛选、搜索、草稿和标签；`editor.at` 有手动保存与删除确认。`src/back/api.at` 定义整数 ID 的 Note 和 CRUD；`src/back/db.at` 是种子数据与进程内列表。

数据库文件虽注释称 JSON persistence，本轮静态检查未发现磁盘读写实现；不能以此声称重启可恢复。Vue 富文本依赖固定的 `vendor/auto-down`；VM 编辑能力与 Vue 不能仅凭 UI 名称判断一致。现有能力保留为基线，首批新增独立捕获/存储模块，不先重写全应用。

## 3. 需求矩阵

| ID | 优先级/阶段 | 需求与验收定义 |
|---|---|---|
| N01 | P0 / M1 | 新 Inbox、稳定 note_id、真实本地保存；进程重启恢复，种子内容不冒充用户数据 |
| N02 | P0 / M2 | 快速卡片：标题可省略、自动保存、Ctrl+Enter 完成；Esc 不丢已输入内容 |
| N03 | P0 / M2 | 接收文本/链接/图片/本地视频文件/文件引用；原资产可导出，链接无需联网也能记录 |
| N04 | P0 / M2 | request_id 幂等接收；错误保留草稿与重试入口；明确存储不足/不可写 |
| N05 | P0 / M1–2 | 置顶、标签、搜索、清单、归档、回收站；这些动作不会改变稳定 ID |
| N06 | P0 / M2 | 撤销/重做、粘贴纯文本、剪贴板条目选择；不自动采集全历史 |
| N07 | P1 / M3 | Launcher 捕获、桌面小组件、现有知识对象打开；真实宿主可用前用适配器契约测试 |
| N08 | P1 / M3 | AutoScape 选区/页面来源、AutoLens 截图区域；先有 fixture 和 import，再接真实服务 |
| N09 | P1 / M3 | 文本/Markdown 与附件 manifest 导出；分享图片先作为增强项，不阻塞捕获 |
| N10 | P1 / M3 | 媒体元数据、图片缩略图、视频元信息/封面；播放器能力可复用 auto-video |
| N11 | P1 / 研究 | 手写图像保存；ink 模型与画笔探针；OCR/识别结果独立可校正 |
| N12 | P2 / v0.7+ | 提醒、同步、多端冲突、端到端加密、分享协作、完整笔记本/手写能力 |
| N13 | P1 / 首版体验 | 色标、排序、最近项、空列表、暗浅色、键盘焦点、窄屏卡片和触屏大按钮 |
| N14 | P2 / 原型 | 可取消 OCR、语音转写、摘要、标签建议；用户采纳后修改笔记，原资产保留 |

普通便利功能中的提醒是系统任务/通知服务的消费者；清单首版仅表示记录内勾选项，不等同项目管理任务。便签加锁需真实密钥管理，不能用 UI 隐藏伪装数据加密。

## 4. 数据与存储

NoteDocument：`schema_version, note_id, revision, title?, blocks[], tags[], color?, pinned, state(active/archived/trashed), created_at, updated_at, source_refs[], asset_refs[]`。Block 首批 text/markdown/checklist/asset/link；识别结果为 derived block，引用原 asset_id 和 processor 版本。

首版建议可移植目录：`manifest.json`、`notes/<id>.json`、`assets/<sha256>.<ext>`、`receipts/`、`journal/`。这是目标布局，不是已存在的路径。正式位置由 app-data adapter 选择；测试用独立临时目录。只有单写者的文件实现才采用原子临时文件替换；跨进程通过单一存储服务与条件 revision 写入。无法保证事务/锁时先拒绝第二写者，不能宣称双端同时安全编辑。

创建流程：暂存附件 → 校验/复制资产 → 记录提交意图 → 写实体及收据 → 原子更新 manifest → 确认 durable → 清理暂存。恢复按 journal 与收据检测未完成提交；临时文件不当作成功。计划 N01 必须用断点故障测试验证所选方案，允许用现有可靠存储库实现同样契约而不照搬文件布局。

导入旧整数 ID 使用 `legacy_id → note_id` 持久映射，只在迁移一次时赋值。迁移前备份；损坏项隔离且报告，不静默丢弃；恢复示例数据仅显式操作。垃圾资产先软删除并留宽限窗口，GC 检查所有对象引用后才执行。

## 5. 模块设计

| 模块/建议新路径 | 责任 | 输出与失败行为 |
|---|---|---|
| capture / src/back/capture.at | 验证 envelope、幂等创建、保留来源 | committed 收据或可重试错误；不抓全网内容 |
| repository / src/back/repository.at | note/revision、事务、迁移、恢复、检索 | 唯一写入入口；冲突保留两版 |
| assets / src/back/assets.at | 普通文件接收、hash、类型、缩略图任务 | pending/ready/failed；附件未就绪不伪称成功 |
| quick_card / src/front/quick_card.at | 最短记录表单、草稿/状态/键盘流 | 同 ID 在卡片和管理页打开 |
| inbox / src/front/inbox.at | 最近、标签、归档、回收站与批量选择 | 不把深度知识图谱塞入便签 |
| adapters / src/integrations/ | clipboard-bin、Launcher、Jade、Scape、Lens | mock/不可用状态明确，不以 stub 宣称已联动 |
| derived / 后续模块 | OCR、转写、摘要、建议 | 异步取消；不阻塞原件保存，不自动覆盖 |

quick_card 的纯文本 fallback 不依赖富文本 npm 引擎完成最基本记录；管理页继续复用 AutoDown 的能力。高级编辑一致性由明确的格式能力矩阵管理，不能用 Vue 可用代替 VM 已通过。

## 6. UI/UX 与交互状态

```text
┌ 快速记录                   Inbox  • 已保存 ┐
│ 灵感、链接或待处理资源……                   │
│ [图片缩略图] [video.mp4 · 已收存]           │
│ 来源：网页标题 / Reader章节 / 剪贴板        │
│ ＋附件  清单  标签       在 Jade 打开  完成 │
└───────────────────────────────────────────┘
```

桌面卡片建议 420–560px 宽，内容过长内部滚动；尺寸是设计起点，不是假定 AutoUI 单位已测量。首次召唤焦点在正文，标题取第一行作可编辑建议。Ctrl+Enter 等待保存完成后收起；Esc 有未提交数据时保留恢复草稿并显示保存状态，写入失败时留在卡片或提示恢复位置。中文 IME 候选阶段的 Enter/Esc 不触发完成/关闭。

状态机：empty → dirty → saving → saved；失败进 error 并可 retry；revision 冲突进 conflict。关闭窗体不等同删除；空卡片不创建空白垃圾项。自动保存采用短防抖加显式完成 flush，防抖时长在体验测试中调节。异步预览与 OCR 不改变“原件已保存”状态。

桌面小组件：最近一张/置顶便签 + 新建入口 + 接收拖放；小组件是宿主中的视图，不是 Notes 偷改 OS 桌面框架。窄屏用全宽单张卡片、底部操作条与系统分享入口设计；长按操作必须有可访问按钮替代。完整管理页为卡片列表/搜索 + 简洁编辑栏，保留列表视图；避免默认多层目录树挡住记录。

键盘：Ctrl+N 新卡片，Ctrl+F 管理页搜索，Ctrl+S 保存，Tab 可达附件/标签/完成，Delete 只在列表焦点中触发软删除。与宿主冲突的键可配置，绝不抢输入框常规编辑键。图片提供说明文字；保存失败状态使用文字/图标，不能只靠颜色；附件上传进度、空搜索和找不到来源都有明确行动。

## 7. 手写分层

H0（v0.6 必达）：手写照片/截图作为普通资产接收，原件可回看和导出。H1（v0.6 研究）：InkAsset 保存画布尺寸、坐标、stroke.points(x,y,t,pressure?)、颜色和粗细，另存可视预览；有实际设备再验证鼠标/触控笔事件、抬笔和缩放坐标。压力缺失可用固定宽度，不伪造硬件能力。

H2（研究）：识别输出为带 region/文字/置信信息的派生层，支持中文/英文、人工纠正、搜索及重新处理；服务不提供可信 confidence 时用 unknown。H3（v0.7+）：压感/掌托、套索、页面管理、公式/版面识别、录音笔迹同步与手写美化。首版不自研识别模型；先评估平台/本地/远程引擎，以质量、延迟、可离线性、许可和成本选择。

## 8. 首版质量与验收

目标：卡片热启动可输入 p95≤300ms；1000 条笔记本地查询 p95≤150ms；参考机、冷热状态和测量方法写入报告，不把目标当实测。正确性优先：重启/异常中断后已确认保存的正文与附件完整；重复请求只有一个对象；冲突/失败无静默丢字。输入内容过大应清晰提示或分块处理。

发布门槛是一个真人工作流在 Vue 与 VM 完成：记录链接和图片、重启、搜索、打开来源、导出、软删和恢复。实际平台范围、手写原型设备及尚未联动的系统服务写入 release notes；不以28个 demo“能打开”替代功能验收。


## 跨应用契约 v1（设计提案）

这些字段是本轮四个应用共同采用的草案，尚未成为 AutoOS 已实现的系统 API。首版用版本化 JSON 和应用内适配器实现；不得等待 HIR、Atom/Batom v2、AutoC 或完整知识系统才能运行。

| 对象 | 必需字段 | 规则 |
|---|---|---|
| EntityRef | namespace、entity_id、revision、kind | 应用生成稳定字符串 ID；改标题、路径或展示名不改 ID；跨仓引用带 namespace |
| AssetRef | asset_id、sha256、mime、size、storage_ref、original_name | 文件拷入受管理目录后才确认接收；storage_ref 是逻辑定位符，不是另一机器的绝对路径 |
| SourceRef | producer、original_uri、captured_at、locator、source_revision | 缺失字段显式 null；网页 URL、书内位置、截图区域分类型表示；保留原文 |
| CaptureEnvelope | schema_version=1、request_id、producer、text、asset_refs、source_refs、created_at | 一个请求的重试复用 request_id；同内容的新意图允许新请求；不以正文 hash 合并不同笔记 |
| CaptureReceipt | request_id、entity_ref、durable_at、status | 持久化正文及必需附件后才返回 committed；失败可重试，重复请求返回原收据 |

`request_id` 的幂等记录与实体创建在同一事务边界内提交。接收者不能只相信来自外部的 hash 或 MIME，须校验实际文件。建议附件交换采用显式授权的暂存目录加 manifest；只接受目录内的普通文件，不追随链接，不接受任意本机路径。

未决定的系统 transport 由 adapter 隔离：首个可验收版本支持导入/导出 envelope 文件或当前运行时已有的本地调用能力；本轮不擅自登记新的全局 URI scheme。未来 Launcher、AutoScape、AutoLens、copy-paste bin 使用相同语义，并以能力协商声明可用格式。

知识对象可以被多个应用访问，存储所有权不等于 Jade 的 UI 所有权。尚无共享知识服务时，Notes 持久化到可导出的本地 Inbox；提供外部引用与显式迁移收据。该阶段不声称已实现 Jade 双向共享编辑。共享服务就绪后，同一对象通过 revision 条件写入，冲突返回两版供选择，不用静默覆盖解决。


## 系统通信与 DevTools 的追加方向（2026-10-04）

用户确认应用通信/AutoAI和系统级DevTools是v0.6重点。本文的envelope、业务对象和provider是领域契约；注册/发现、会话、授权、错误、trace、stream与task复用公共系统层，应用不各自实现一套底层协议。

公共方案见[AutoOS通信RFC](https://github.com/auto-stack/auto-os/blob/v0.6-dev/docs/design/strategy/auto-app-communication-v0.6.md)与[系统DevTools RFC](https://github.com/auto-stack/auto-os/blob/v0.6-dev/docs/design/strategy/system-devtools-v0.6.md)。两份RFC尚未冻结；当前app计划仍可先完成独立本地数据与fixture闭环，之后把现有adapter接入公共服务，不以尚未实现的broker作为开始保存真实数据的前置。

应用提供业务Service及能力描述，UI/backend adapter提供观察树和允许动作；系统组件提供Inspector、Agent SDK与diff。复用现有AutoUI能力并显式声明Vue/VM/Rust的差异，不要求本app自行嵌入另一套DevTools面板。AI优先调业务能力，体验验证才走UI动作。

## 工程边界与实施约束

当前基线是 2026-10-04 的独立仓库导入版本；主力机器的 v0.5 尚有未公开工作。新增产品模块优先放新路径，用 adapter 接入既有页面；保留 SOURCE-IMPORT.json、source-sync 分支及教学来源。恢复 v0.5 后从 source-sync 基线做三方差异导入，不直接覆盖产品目录。

本次只是研究与设计，文档中“支持”“应当”均为目标；实现状态以计划验收证据为准。应用后端保持纯 Auto `.at`；不编辑 a2r 生成的 Rust。若现有运行时缺少必要平台能力，先输出最小能力探针和单独的跨仓提案，不把大规模框架改动塞进应用计划。

平台基线：Windows/Linux 桌面及 Web 先完成可用闭环；Harmony 是 v0.6 demo 与适配探针范围。窄屏设计纳入本轮，不能据此宣称已交付手机原生版。Android、iOS/macOS 及完整移动平台产品支持没有在本轮被追加为 v0.6 必达项。

AI 派生内容须标记来源、模型/处理器版本和生成时间；原文、原资产、人工更正均可追溯。未配置 AI 或断网时，核心本地流程仍能完成。任务可取消，可见错误，可重新执行。个人内容传给远程服务由用户选择；默认不自动上传整库。


## 配套文档

[调研依据](../research/20261004-benchmarks.md) · [首版路线](../roadmap-v0.6.md) · [执行入口](../README.md)
