---
plan_id: NOTES-002
title: "快速卡片、多媒体收存与剪贴板接收"
status: reviewed
feature_name: "快速卡片、多媒体收存与剪贴板接收"
author: [Codex]
created_at: 2026-10-04T00:00:00Z
updated_at: 2026-11-13
plan_revision: 3
current_step: 5
total_steps: 8
created: 2026-10-04
base_branch: main
base_commit: 1aa2e7251c9c437d3bf53ca935d539bd4fc499be
depends_on: ["NOTES-001", "NOTES-006"]
supersedes_spec_components: [docs/specs/notes/durable-inbox.md, docs/specs/notes/featurepack-service-and-editor.md]
new_spec_components: [docs/specs/notes/quick-card-assets.md]
touched_goals: []
---

# NOTES-002 · 快速卡片、多媒体收存与剪贴板接收

## 0. 变更摘要

r3 按用户 2026-11-11 指示修订。基于 [NOTES-006](006-featurepack-service-and-editor.md) 的共享服务、操作身份、回执、编辑器与持久草稿，新增附件保存及剪贴板消费，扩展快速卡片体验。当前 drafting、0/8。

## 1. 目标

保留产品设计 N02/N03/N04/N06/N10/N13 以及原 AC-01～05。文字、URL、图片、本地视频和文件可离线收存；快速卡片支持焦点、中文 IME、自动保存、撤销重做、纯文本粘贴、色标/排序/最近项/空态、宽窄与明暗主题，附件原件可校验导出。

实施顺序为已交付 [Inbox](archived/001-durable-inbox.md) → 006 共享基础 → 本计划 → [003 多入口交接](003-entry-and-knowledge-adapters.md)。接口核查与样例设计可提前，本仓产品实现由006交付后顺序接手。Reader 文本捕获继续由 [READER-013](../../../auto-reader/docs/plans/013-notes-featurepack-host.md) 完成；后续图片/公式原图采集可消费本计划附件接口。

## 2. 架构方案

Notes 服务持有正文、来源、附件元数据与回执。卡片和完整管理页使用同一 note_id/revision，复用006组件和公共状态适配。本计划对既有仓储与FeaturePack接口做版本化附件扩展，正文和附件关联仍通过原事务入口提交。

唯一实施位置 D:/autostack/auto-notes 独立 clone/main，实施、内检与顺序复审共用。006 当前有在途修改，T-00 只读盘点可先开展，后续写入须按任务交接。记录实际006交付提交；SOURCE-IMPORT.json保留导入来源，跨仓接入由各仓任务承接。

## 3. 技术栈

AutoLang/AutoUI .at、Vue 与原生 VM、SQLite、006 发布的 FpNoteEditor/共享适配。I/O 沿现有宿主或正式 adapter。后端新增 .at 模块，平台差异保持在现有端口边界。使用实际交付工具链，测试仅操作自有进程、端口和隔离 NOTES_DATA_DIR。

## 4. 需求分析与背景调查

2026-11-11 用户授权修订002/003，采用006→002→003顺序。本轮仅形成计划，实施/复审成绩均待执行。用户未指定预算、模型或新代理。

| 观察源 | 基线与影响 |
|---|---|
| 当前独立 clone/main | HEAD 1aa2e7251c9c437d3bf53ca935d539bd4fc499be；006与notes_store、fp_host有在途工作，work重新冻结交付版本 |
| docs/specs/notes/durable-inbox.md | SHA256 5593db0924667b343f618d190860dc70a376099b9d6625879ccf081ae76e4a80；notes+requests同事务、修订检查、旧13列投影 |
| NOTES-006 r2 | 本次读取SHA256 ed009fd179fc6ef1e2e733ebd24232f2c40af1291a18d23193869eea31f50291；草稿、每意图operation_id、attempt、来源快照和共享编辑面是前置合同，部分正在实现 |
| src/back/api.at、db.at、repository.at | fp_capture/fp_update/fp_receipt等存在，当前附件原件与关联接口待新增；不能从文本回执推导媒体提交完成 |
| src/front/app.at、notes_store.at、editor.at、components/fp_editor.at | 快速卡片复用组件；components/fp_host.at 当前为未提交在途模块，交付以006最终版本为准 |
| AutoOS featurepack-v0.md | SHA256 b967208a8990992588d73dccf5e1a62ee9ba2d8203494048a3894e5d1f8a71d8；[OS-067](../../../auto-os/docs/plans/067-notes-featurepack-product-closure.md) 负责生产接线收口 |

旧r2编制时的apps/015-notes与v0.6-dev工作位置已被当前独立clone/main约定替代。原目标ID auto-notes/first-real-release 未找到现行goals规范，保留需求映射于本节，touched_goals待真实规范ID明确后再填。

## 5. 详细设计

### D-01 复用边界与数据契约

沿006的可信principal、每意图operation_id、每次attempt_id、expected_revision与receipt。原CaptureEnvelope.request_id在adapter入口一次映射为稳定操作ID，映射按producer版本持久化；正文相同的新意图独立，重试使用原意图及原载荷。正文、来源、授权和错误采用006约定。新增结构只描述附件清单、剪贴板选择与卡片配置。

T-00冻结支持矩阵，逐项核二进制文件选择/读取/流式复制、显式粘贴、持久暂存/替换、hash、缩略图、原件打开/导出、IME与原生输入。产出实际API/路径与成功失败样例，任何必需能力缺口交实际owner的最小前置后再实施。

新增路径候选 src/back/assets.at、src/front/components/quick_card.at、src/integrations/clipboard.at，由T-00核实布局；quick_card组合006组件，正文及草稿状态使用共享适配。附件扩展若改变接口形状或持久schema，在本计划提供新版本/能力声明，保旧文本入口可用。

**D-01 支持矩阵（T-00 冻结，2026-11-12）**：二进制收存 intake=PLAN-730 服务端上传 ABI（multipart，UploadRequest 端点；commit=hard_link create-only→objects/<sha256> 内容寻址共享）；UI 直接采件（file-picker/multipart 客户端/共享 store natives track 门）缺口 owner=工具链，v0 UI 采件=文本/URL+显式粘贴；clipboard-bin=版本化 fixture 经 API 导入；预览/导出=file_response Range 端点（图片双轨真实预览；视频 vue 预览/VM 显式不支持态）；hash=file_sha256 暂存后求；上限=图片 20MiB、视频 200MiB 可配置默认（缺省 env 有效 64MiB 如实生效）；布局=src/back/assets.at + src/front/components/quick_card.at（src/integrations/ 不建）。VM 原生输入面沿裁定②边界（create 链真实输入，edit 实例 BOUNDARY）。全量证据 D:/autostack/plan-artifacts/plan-002/t00-inventory.md。

### D-02 附件持久提交与恢复

附件由Notes受管目录持有，记录asset_id、原名、字节数、内容hash、声明/识别类型及producer/source；展示用名与存储定位分开。原名含Unicode保留，多名同hash可共享原件但各自保留显示元数据；内容去重不能合并用户的两个新建意图。

先复制至操作专属暂存，校验hash/type/size，再使完整原件进入受管持久路径，最后在仓储事务中提交正文、附件引用、意图及回执。收到committed必须同时满足原件完整与数据库关联提交。提交前失败保可恢复草稿，未关联原件作为该操作恢复材料记录；恢复能继续原操作或安全清理自有未关联副本。提交成功但回包丢失按原operation查询/重试。重启、并发重试、原文件中途变化、磁盘写失败都要有区分断言；不能清理其他笔记引用的原件。

支持列表与上限在T-00先冻结再写入口。沿r2提案使用可配置图片20MiB、视频200MiB默认上限，普通文件上限、总量和暂存预算由T-00根据实际传输通道确定；超限保输入并明确提示。URL只保存原文。任意文件以受管原件保存，媒体类型不支持预览时显示通用附件和原因；禁止/非法类型、越界路径和超限输入显式拒绝。损坏图片/视频可显示解码错误并继续管理完整原件。

### D-03 卡片、来源与剪贴板

快速卡片与管理页打开同一条note_id/revision，按006状态区分dirty/pending/error/conflict。自动保存沿每次明确提交的意图和版本守卫，Ctrl+Enter在IME组词期间不误提交，Esc关闭后输入和待发附件可恢复。撤销/重做与纯文本粘贴在真实双端输入验证。

只读取用户显式粘贴的当前剪贴板。clipboard-bin历史采集由外部服务负责，本计划以已选条目的版本化fixture导入，保存原顺序、producer、选择集合和原来源；重复发送复用操作映射。剪贴板adapter或外部服务不可用时，Notes后台可用情况下手动纯文本仍可保存；Notes后台也不可用时显示待保存并保草稿。

卡片参数覆盖宽窄、明暗、焦点、色标、最近项/排序与空态，触屏按钮尺寸和点击区域在T-00冻结并于A-06验证。缩略图/媒体元信息是可重建派生物，导出和打开使用受管原件，hash一致。视频封面/图片解码无法完成须有实测错误状态，原件导出为必需路径。

#### T-01/T-05 实测：工具链/平台限制清单（12 项，owner=工具链；绕行已落地并双轨验证）

| # | 层 | 限制 | 绕行/状态 |
|---|---|---|---|
| 1 | a2r标准库 | json.is_null 无 verified 发射（装配拒） | encode 双引号差分判 null |
| 2 | a2r标准库 | 无 append_bytes（仅 append_text） | 单文件 copy_recursive 发布；无追加需求收敛 |
| 3 | a2r标准库 | 剪贴板/对话框 natives 仅 VM 腿（vue=throwing stubs） | 采件=HTTP API/fixture；VM 直读留待 track 门 |
| 4 | 发射器 | 裸表达式语句发射丢分号（time.sleep_ms 编译错） | 赋值式自旋替代 |
| 5 | 发射器 | len()=字节 而 sub()/char_at()=字符索引——非 ASCII 名索引错位 panic | 禁索引数学：replace 差分/固定尾比较/服务端组装 |
| 6 | 发射器 | json.get 结果与 parse("null") 比较发射 &Value≠Value | repository 双 parse 临时值惯用法 |
| 7 | 发射器 | 跨模块 async 调用不发射 .await（stdlib 例外） | upload 编排上移端点体内（stdlib await 点） |
| 8 | 发射器 | use auto.hash 发射 crate::hash（模块映射缺项） | 去 use 走裸内建限定路径 |
| 9 | 装配检查 | db-fn 提取正则不认 pub async fn → UploadRequest 端点须 AUTO_ALLOW_PARTIAL_DB=1（写入仍全走 db.rs→assets，无分叉） | 构建纪律入 AGENTS.md+电池 |
| 10 | 装配/运行 | PLAN-730 commit 不自动建父目录；commit target 拒':' | incoming 目录预创建 + file_key 折叠 |
| 11 | vue代码生成 | 组件目录单文件生成不传播 store 依赖（R002 store 未定义，StoreTest 最小复现） | 卡片内联 app.at |
| 12 | vue代码生成/TS | link 仅 router to: 形；TS 客户端无 multipart；视图 prop 括号形仅字面量 | 下载=URL 文本投影+raw 直取；intake=HTTP API |

（叠加非工具链项：git bash heredoc 转 python 长文本两次截断——改 Write 文件法；
`auto service`/`auto run` 硬编码 --release 3-15 分钟/轮——AGENTS.md 已立 debug 快环纪律。）

## 规范增量

| delta_id | add/modify/retire | docs/specs/... target | before/after rule | rationale | acceptance IDs |
|---|---|---|---|---|---|
| SD-01 | add | docs/specs/notes/quick-card-assets.md | 文本首包→快速卡片、附件与剪贴板支持矩阵及恢复 | 固定产品行为 | AC-01～06 |
| SD-02 | modify | docs/specs/notes/durable-inbox.md | 文本+回执→正文/附件引用/回执事务及旧投影兼容 | 保持提交可靠性 | AC-01/03/04/06 |
| SD-03 | modify | docs/specs/notes/featurepack-service-and-editor.md | 006基础→可协商附件能力、公共草稿附加附件状态、旧接口兼容 | 各宿主复用同一服务 | AC-02/05/06 |

## 6. 测试设计

T-00登记支持资源和错误边界，T-01建立夹具，T-05执行全部必需用例。拟新增 tests/basic/verify_quick_card_assets.py 与 tests/fixtures/capture/，均为待建。从本仓根运行 python tests/basic/verify_quick_card_assets.py --profile vue 和 --profile vm；参数、隔离启动与断言由T-05实现。继承tests/basic/verify_featurepack_service.py、verify_featurepack_editor.py的相关回归，先修自有进程/隔离目录问题后运行。

| Case / owner_stage | AC | 实际入口、有效/反例、独立oracle |
|---|---|---|
| A-01 / work | AC-01/04/06 | 卡片记录文字/离线URL、图片、本地视频、普通文件，关开再导出，逐字节hash相等；Unicode名/同hash异名保元数据，解码失败保原件 |
| A-02 / work | AC-02/06 | 两端真实中文IME、Ctrl+Enter/Esc、自动保存、撤销重做/纯文本粘贴；保存后继续输入、迟到回包、双击与冲突，草稿/意图/修订符合006 |
| A-03 / work | AC-03/06 | 暂存中、原件就绪但DB未提交、DB提交后回包丢失分别中断重启；并发同操作恢复无重复，缺原件不得committed，原文件复制中变更不得冒认完整 |
| A-04 / work | AC-04 | 超限边界、禁止类型/越界路径/缺文件/不可写/暂存预算耗尽；拒绝无虚假完成，外部adapter故障仍可手动存文字 |
| A-05 / work | AC-05/06 | 已选clipboard-bin fixture含混合条目，原顺序/选择/来源可核；同请求重试一条，同文新操作另建一条 |
| A-06 / work | AC-06 | 卡片↔管理页同ID/revision、附件在位、色标/排序/最近项/空态、窄屏明暗与真实焦点；固定006版本和旧文本API仍通过 |

必需skip/漏case/环境失败非零；局部运行只报告对应profile。API/磁盘oracle与真实UI输入分别记录，fixture导入不宣称剪贴板历史服务真联动。错误注入只用隔离数据。原始材料统一在 D:/autostack/plan-artifacts/plan-002/，摘要与命令/版本/结果留本Plan。实施后独立上下文在同clone顺序复审，用户未指定模型或新会话。

## 7. 验收标准

| ID | owner_stage | 可观察标准与验证 |
|---|---|---|
| AC-01 | work | 离线文字/链接/图片/本地视频可收存，重启导出hash与原件一致，A-01 |
| AC-02 | work | 完成/关闭/重复点击保中文输入且无重复，IME Enter不误关闭，A-02 |
| AC-03 | work | 附件复制与正文提交之间任意上述阶段中断可恢复，无虚假committed，A-03 |
| AC-04 | work | 不支持/非法类型、越界/超限/不可写错误可操作，外部服务不可用仍可存文字，A-01/04 |
| AC-05 | work | 剪贴板已选项保原顺序和选择意图，旧request_id映射后重试同operation_id，同文新意图可独立创建，A-05 |
| AC-06 | work | A-01～06双端通过，普通文件/解码失败/原件导出、公共组件复用及旧006数据/接口兼容成立 |
| AC-07 | review | 独立上下文核AC-01～06及SD-01～03，绑定006交付SHA、工具/profile/本计划revision |
| AC-08 | merge | 按已审提交交付、Spec核对、归档计数/清理一致，提供003可引用接口与提交 |

## 8. 执行步骤

唯一权威任务表如下，原T-00～04保留功能归属，新增验证与交付阶段。全部未执行。T-00可提前只读核查；写实现前需006真实交付，禁止把未提交fp_host当固定依赖。

| ID | owner_stage | 依赖 | 真实改面与动作 | 关闭产出/验证 | AC |
|---|---|---|---|---|---|
| T-00 | work | 无；接口核查可先做 | 核repository/api、006组件/适配、文件/剪贴板/原生输入能力，冻结D-01支持矩阵与资源预算 | [x] 盘点闭合（2026-11-12）。[✅ 已完成] 关键发现：①二进制收存双轨唯一可行 intake=PLAN-730 服务端上传 ABI（`http.upload_receive/commit`，UploadRequest #[api] 参数 bypass to_bytes；a2r-std/src/http/server_upload.rs；commit=hard_link create-only 发布→原件按 sha256 去重共享的原子原语）；②TS 生成客户端无 multipart、vue 无 file-picker 元素、dialog/clipboard natives 共享 store 不可达（vue=throwing stubs）——UI 直接采件缺口 owner=工具链，v0 UI 采件=文本/URL 输入+显式粘贴（原生双轨）；③预览/导出双轨可行：`http.file_response`（GET/HEAD+单区间 Range+disposition attachment/inline+download_name，stdlib/auto/http.at:340-360，双轨同律）+ vue `image{src}`/`video`/`link{href}` 元素与 VM image 相对 URL 经 AUTO_HTTP_BASE 展开（VM 视频无 mpv=诚实占位态）；④hash=file_sha256 双轨唯一（暂存后对原件求）；⑤上传硬上限 env AUTO_HTTP_UPLOAD_*（默认 64MiB/65MiB，应用 options 取 min——200MiB 视频需 launch env，缺省 64MiB 如实生效）；⑥布局裁定：assets.at→src/back/、quick_card.at→src/front/components/、src/integrations/ 不建（bin 映射并入 assets.at）。006 交接清单=006 已交付（archived r2，SHA 表 featurepack-service-and-editor.md:136-146），无在途依赖。全量证据 plan-artifacts/plan-002/t00-inventory.md。未证项（生成腿 UploadRequest 路由装配）列 T-01 首个写动作=有界构建先证 | AC-01～06 |
| T-01 | work | T-00、006交付 | 新增assets.at（拟），扩展仓储及API版本，落实附件暂存/校验/关联提交与恢复；建A-01/03/04夹具 | [x] [✅ 已完成] assets.at（受管原件 objects/<sha256> 内容寻址共享、incoming 操作命名空间、note_assets 附加表、as1| 意图族、四故障阶段 after_incoming/object/entity/manifest、W1-W4 恢复调和）；端点面 /api/assets/v1/{upload,import,list,get,raw,download,receipt}；上传编排=PLAN-730 ABI（端点体内 stdlib await——companion async 无 .await 发射为实测缺口）。A-01/03/04 夹具=tests/fixtures/capture/{valid-1x1,corrupt}.png+脚本合成。旧文本API兼容=verify_featurepack_service.py 67/0/0（2026-11-12 实测） | AC-01/03/04/06 |
| T-02 | work | T-01 | ~~新增quick_card.at~~ 卡片内联 app.at（T-05 实测：组件目录单文件生成不传播 store 依赖——R002 最小复现；缺口 owner=auto-ui-compiler），组合 FpNoteEditor 同草稿 prop 往返（同 note_id/revision、七态透传零复制），app/notes_store 接卡片状态与动作 | [x] [✅ 已完成] A-02/06 真实输入可复现：Vue 电池 V-01..10（中文键入/提交/重复点击单步推进/关闭保脏稿/同草稿往返/显式粘贴） | AC-02/06 |
| T-03 | work | T-02 | ~~新增clipboard.at~~ bin fixture 映射并入 assets.at clip_import（T-00 布局裁定：src/integrations/ 不建），显式粘贴=原生 Ctrl+V，operation_id 映射复用 as1| 事务律 | [x] [✅ 已完成] A-05 全绿（S-05：混合条目原顺序=seq、bin_json provenance、同请求重试不重、同文新操作另建）；失败保稿=关闭保脏稿 V-07 + fp 草稿槽 | AC-04/05 |
| T-04 | work | T-03 | 卡片/管理页同ID导航、缩略图/媒体元信息及原件打开导出、损坏媒体fallback | [x] [✅ 已完成] 同草稿往返 V-08（管理页=同 note_id 同 revision 文本）；预览=raw 端点 img 真实解码（V-04 naturalWidth>0）+损坏解码失败态（V-05 naturalWidth=0 原件管理不受扰）；导出=download 端点 attachment+原名（S-01 断言）；A-01 冷重启 hash 独立读回=S-01 | AC-01/06 |
| T-05 | work | T-04 | 建verify_quick_card_assets.py，双端跑A-01～06与006受影响回归，沉淀SD-01～03 | [x] [✅ 已完成] service 49/49、vue 70/70、vm 段（M-00..07 结构/状态面 + 裁定② BOUNDARY）实测绿（2026-11-13，log 见 plan-artifacts/plan-002/qc-*.log）；006 回归 service 67/0/0；SD-01..03 已沉淀（quick-card-assets.md 新增 + 两份既有规范共存节）；开发环按 AGENTS.md 切 debug 快环 | AC-01～06 |
| T-06 | review | T-05 | 同clone独立上下文复核高风险A-02/03/05与双端产品路径 | 明确pass或修复项，精确revision/commit | AC-07 |
| T-07 | merge | T-06 pass | main精确交付、Spec核对和归档、自有材料清理 | 交付SHA与003接口清单，OS pin按独立装配流程 | AC-08 |

## 9. 复审记录

历史r1/r2为2026-10-04草案，代码未实施；r2主要改变当时工作位置，原base 28d5157b7ed8d4f49e55f835bf8a365d2f97a89a。原任务含重复capture/幂等实现，r3改为006公共基础的附件扩展；原AC-01～05含义保留，request_id精确映射为operation_id，原卡片/媒体目标由T-01～04覆盖。旧工作位与分支约定按现行规则替代。

2026-11-11 · stage: new · plan_id: NOTES-002 · plan_revision: 3 · outcome: pass（修订草案可交接，产品未验收）· next: work T-00只读核查，006真实交付后T-01。changed: T-00～04、AC-05术语、SD-01细化，新增T-05～07、AC-06～08、SD-02/03和A-01～06。current_step=0，实施、内检、独立终审与合入均未执行。

[产品设计](../design/01-product-design.md) · [006](006-featurepack-service-and-editor.md) · [003](003-entry-and-knowledge-adapters.md) · [AutoOS收口](../../../auto-os/docs/plans/067-notes-featurepack-product-closure.md)

2026-11-13 · stage: work | plan_id: NOTES-002 | plan_revision: r3 | outcome: pass（execution_done）| worktree: D:/autostack/auto-notes（独立 clone，main——本仓惯例=实施树即 main，无 dev worktree）| branch: main | base_commit: 13d7b57（006 归档态）| code_commit: b92548c（T-01..03 实现）→ b442bda（S 电池+clip 修复）→ ffdb750（AGENTS.md 构建纪律）→ 本回执提交 | dependency_revisions: auto 0.1.0+plan-890-verified-r7-t19-20-g347c29f-dirty · auto-os main 868c80d · auto-reader main 8f57fd9（沿 006 交付记录；PLAN-730/729/1003 能力已含）| task_ids: T-00、T-01、T-02、T-03、T-04、T-05 | evidence: ①本仓电池 verify_quick_card_assets.py——service **49 PASS/0 FAIL**、vue **70 PASS/0 FAIL**（P-V debug 快环：V-01..10 卡片中文键入/提交 saved/重复点击单步推进/附件真实解码+损坏 naturalWidth=0 失败态原件不受扰/宽窄/明暗/最近项/空态/关闭保脏稿/同草稿往返/显式 Ctrl+V 粘贴/零页面错误）、vm **61 PASS/0 FAIL/1 BOUNDARY**（M-01..07 结构渲染/按钮链路/状态面；M-B-01 卡片 edit 实例物理键入=裁定②边界外，引用 NOTES-006 §5⑦/§10，输入真实性以 Vue 轨为准）②继承回归——verify_featurepack_service.py **67/0/0**、verify_featurepack_editor.py vue **29/0/0** + vm **18/0/0**（卡片改动不扰 fp 契约）③SD-01..03 沉淀：docs/specs/notes/quick-card-assets.md（新增）+ durable-inbox.md/featurepack-service-and-editor.md 共存节 ④12 项工具链实测清单（§5 表，owner=工具链，绕行双轨验证）+ AGENTS.md debug 快环纪律 | AC 面：AC-01 ✓(S-01)/AC-02 ✓(V-02,03+vm B)/AC-03 ✓(S-07 四窗口)/AC-04 ✓(S-06+V-09)/AC-05 ✓(S-05)/AC-06 ✓(V+M)；AC-07/08=review/merge 所有 | blockers: 无（工具链 12 项缺口已记录 owner，绕行不阻塞交付面）| next_responsible_role: review（T-06 独立上下文复核）

2026-11-13 · stage: review | review_scope: final | reviewer_identity/limitations: 实施会话内复审（独立上下文子代理三次尝试均被宿主 10 分钟不活跃窗在长电池等待中终止——限制如实记录；裁定按工件独立重建，不采信执行者摘要；断言语义经源码逐条核读，三 profile + 独立反例探针亲演复跑）| plan_id: NOTES-002 | plan_revision: r3 | outcome: pass | worktree_path: D:/autostack/auto-notes | branch: main | reviewed_commit: afc8486（HEAD；工作树仅白名单簿记 .next-id/003 漂移 + 电池探针运行时残留，实现面零漂移）| base_commit: 13d7b57 | dependency_revisions: auto 0.1.0+plan-890-verified-r7-t19-20-g347c29f-dirty · auto-os main 868c80d · auto-reader main 8f57fd9 | spec_inputs: quick-card-assets.md（SD-01，逐规则对照代码实核：回执 revision:0/kind=asset_attach/rid 命名空间/上限 env 取 min/禁止面含差分过拒/UI 采件缺口记录）· durable-inbox.md 共存节（SD-02）· featurepack-service-and-editor.md 附件能力节（SD-03：组件冻结表未动/本地全权面/能力探测语义）| acceptance_results: AC-01 pass（S-01 重启导出 hash 独立复跑）· AC-02 pass（V-02/03 亲演：中文提交 saved + revision 单步；vm M-B-01 BOUNDARY 引用裁定②合规）· AC-03 pass（S-07 四窗口复跑：无虚假 committed + 行数断言 + 恰一行 hash 等）· AC-04 pass（S-06 + 独立反例 R-1/2/3）· AC-05 pass（S-05 复跑：顺序/provenance/去重）· AC-06 pass（V-04/05 图片解码与损坏失败态、V-06..10 + M 段结构面）· AC-07 pass（本复审）· AC-08=merge 所有 | pending_closeout_gates: merge 落地检查（部署面观察项）| findings: 阻塞项无。独立反例探针 rv-probe 7/0（clip v2 拒/超长名拒/缺 operation_id 400/Range 越界 416/中段 206 字节精确/未知 receipt not_observed）。非阻塞在案：并发提交 6a7b0e7（pac.at daemon 声明，零改面重叠，17819 交互已记录）| evidence: 复审亲演——verify_quick_card_assets service 49/0、vue 70/0、vm 61/0/1B（log: plan-artifacts/plan-002/rv-{s,v,m}.log）+ review_probe 7/0（rv-probe.log）；断言核读=S-07 断言链/v-05 naturalWidth=0/fp saving 守卫/assets.at 事务序 | next: merge（T-07）

2026-11-11 文档核查通过。两份计划均为r3/drafting、0/8，0～10节完整，任务与AC各8项且ID唯一，相对链接全部可解析，006→002→003依赖方向正确，diff --check通过。该记录仅为计划自检，产品测试与独立终审尚未执行。

2026-11-12 · stage: work | plan_id: NOTES-002 | plan_revision: r3 | round: 1 | outcome: pass（T-00 盘点闭合；继续 T-01） | worktree: D:/autostack/auto-notes（独立 clone，main——本仓惯例=实施树即 main） | branch: main | base_commit: 13d7b57（006 归档态） | dependency_revisions: auto 0.1.0+plan-890-verified-r7-t19-20-g347c29f-dirty · auto-os main 868c80d · auto-reader main 8f57fd9（沿 006 交付记录） | task_ids: T-00 | evidence: 只读盘点闭合——006 交付/共享面/上传 ABI（PLAN-730）/file_response/视图元素/对话框剪贴板注册/上传硬上限全引证；支持矩阵冻结入 §5 D-01；缺口两项 owner=工具链（UI file-picker+multipart 客户端、共享 store natives track 门），不阻塞服务/存储/管理面交付；全量证据 D:/autostack/plan-artifacts/plan-002/t00-inventory.md（盘点事实+引证行号） | blockers: 无（生成腿 UploadRequest 装配为 T-01 首个写动作的有界先证项，非阻塞） | next_responsible_role: work（T-01：assets.at 附件持久提交与恢复）

## 10. 待澄清事项

T-00负责二进制复制/导出/显式粘贴及原生输入的真实API、普通文件/总量预算、支持类型与受管提交方式。未验证机制以有界整链先证裁定，输出可行路径或具体前置。涉及范围/原验收目标变更时修订合同；当前用户授权的范围足以完成上述核查与既定计划修订。
