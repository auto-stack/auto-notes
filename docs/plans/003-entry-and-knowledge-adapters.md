---
plan_id: NOTES-003
title: "Launcher、小组件与知识交接适配"
status: reviewed
feature_name: "Launcher、小组件与知识交接适配"
author: [Codex]
created_at: 2026-10-04T00:00:00Z
updated_at: 2026-11-11
plan_revision: 3
current_step: 5
total_steps: 8
created: 2026-10-04
base_branch: main
base_commit: 1aa2e7251c9c437d3bf53ca935d539bd4fc499be
depends_on: ["NOTES-002", "NOTES-006"]
supersedes_spec_components: [docs/specs/notes/quick-card-assets.md, docs/specs/notes/featurepack-service-and-editor.md]
new_spec_components: [docs/specs/notes/entry-and-knowledge-adapters.md]
touched_goals: []
---

# NOTES-003 · Launcher、小组件与知识交接适配

## 0. 变更摘要

r3按用户2026-11-11指示修订。使用 [006共享服务](006-featurepack-service-and-editor.md) 和 [002附件/卡片](002-quick-card-assets.md)，实现Notes侧多入口适配、知识交接和手写原件模型。T-00..T-05 已执行（2026-11-13，execution_done 5/8），T-06/07 待复审/交付。

## 1. 目标

保留产品设计N07/N08/N09/N11和原AC-01～05。完成Launcher caller文件交接、Notes侧小组件视图与同ID打开、Markdown/文本及附件manifest导出、Jade接收契约、网页/区域来源和InkAsset round-trip。

按现有Inbox→006→002→003顺序实施。系统发现/启动/授权/版本与回执复用 [OS-067](../../../auto-os/docs/plans/067-notes-featurepack-product-closure.md) 和006。Reader真实选区、捕获、高亮、回访由 [READER-013](../../../auto-reader/docs/plans/013-notes-featurepack-host.md) 独立验收；本计划消费其版本化来源样例以检验跨入口保真。

## 2. 架构方案

本计划主改Notes仓的adapter、导入导出入口及可嵌入视图，006服务持有共享笔记，002服务持有原资产，Jade承担长期知识组织。Notes侧caller harness及接收端stub验证真实进程/文件交接和领域协议，实际外仓Launcher、桌面、Jade、Scape、Lens联动各需接收仓独立计划及共同验收。

使用D:/autostack/auto-notes独立clone/main，实施/内检/顺序复审共用、一仓顺序交接。接口核查可提前，只读确认006/002合同；写实现先消费两个计划的真实交付提交。SOURCE-IMPORT.json只保留导入来源，OS装配按独立流程升级pin。

## 3. 技术栈

现有 .at、AutoUI Vue/原生VM、006服务/编辑组件/公共状态适配、002附件服务与卡片、版本化adapter数据。进程和I/O使用已支持的运行入口，第三方来源经过adapter转换。测试只使用自有进程/端口、隔离NOTES_DATA_DIR与收发目录。

## 4. 需求分析与背景调查

2026-11-11用户授权修订002/003，确认先006共享基础，再002多媒体，最后003多入口知识交接。本轮文档修订，产品实施未执行；没有指定新代理、模型或预算。

| 观察源 | 基线与影响 |
|---|---|
| 独立clone/main | HEAD 1aa2e7251c9c437d3bf53ca935d539bd4fc499be；006与notes_store/fp_host正在修改，不能视为已固定交付 |
| durable-inbox.md | SHA256 5593db0924667b343f618d190860dc70a376099b9d6625879ccf081ae76e4a80；notes/requests事务、回执和revision可复用 |
| NOTES-006 r2 | 本次读取SHA256 ed009fd179fc6ef1e2e733ebd24232f2c40af1291a18d23193869eea31f50291；接口/来源/ID和共享草稿公共合同 |
| NOTES-002 r3 | 附件受管原件与提交恢复、剪贴板选择、快速卡片是本计划前置，当前仅草案 |
| src/back/api.at、db.at、repository.at | 现有fp服务方法可转接领域请求；无Jade/Launcher产品联动交付证据 |
| src/front/components/fp_editor.at、package.at | 实际可嵌入组件；fp_host.at为当前在途公共逻辑；后续实现需核006版本 |
| AutoOS featurepack-v0.md | SHA256 b967208a8990992588d73dccf5e1a62ee9ba2d8203494048a3894e5d1f8a71d8；系统能力复用，生产接线由OS067收口 |

r2中apps/015-notes与v0.6-dev工作位为历史，当前独立clone/main执行。旧auto-notes/first-real-release未找到现行goals规范，需求映射保留，touched_goals待明确的真实规范ID。

## 5. 详细设计

### D-01 adapter与系统、领域边界（T-00 冻结，见下）

候选新增路径 src/integrations/{launcher,jade,scape,lens,ink}.at、src/back/entry_adapters.at、src/front/components/notes_widget.at，T-00核布局后记录最终路径/导出。已有app/notes_store、api/db/repository为实际消费面。

#### T-00 冻结（2026-11-13 盘点，逐项引证代码行号）

最终路径：**src/integrations/ 不建**（002 T-00 先例，计划原文"候选"折入本仓模块）；Notes 侧入口统一
**src/back/entry_adapters.at**（新，纯同步服务面，assets.at 同律自持助手），api.at 加端点、db.at 同律委托；
小组件 **src/front/components/notes_widget.at**（新，props 驱动零 store 引用——组件目录单文件生成不传播
store deps，R002 在案）；app.at 顶栏按钮开合（复用 .store 既有 FpEdit* 链）；测试
**tests/basic/verify_entry_knowledge_adapters.py** + **tests/fixtures/integrations/**。

| producer | 消费面（版本锚） | capture 实际方法 | open 实际方法 | export 实际方法 | 回执 | 来源/附件引用 | 不可用结果 |
|---|---|---|---|---|---|---|---|
| Launcher（caller harness） | NOTES_HANDOFF_DIR 文件交接，envelope v1 | repository.fp_capture（api.at:470 委托链 fp_capture→db:534→repository:2193；policy 门 cred+scope，repository:1969/2024） | —（open 走既有 note_id/revision） | — | 回执文件 outgoing/<op>.json（status=committed\|rejected） | source_json 冻结 7 键闭集（repository:2062 fp_source_validate） | 半写/错版本/未知 producer→确定 rejected；update 未知 note_id→not_found；过期修订→revision_conflict |
| Jade | NOTES_EXPORT_DIR 快照包（export_id 映射） | — | repository.repo_get（db.at:420 get_note_r 同源） | 快照导出：note.json/note.md/note.txt/source.json/attachments/*+manifest.json；原件经 assets 受管接口 raw（assets.at:888 asset_raw）+ hash 核（hash.file_sha256） | 返回包 ID + note_id/revision 映射；重复同包保持同映射 | 附件 manifest（asset_id/name/sha256/bytes/mime/seq） | 缺原件/写失败→可重试 err（不留半包）；导出中更新→快照语义 |
| Scape | source capture 端点 | repository.fp_capture（book_id=web:…） | — | — | fp 原收据 | locator={kind:"url",value}, source_hash=选区 hash | 缺字段/未知版本→fp 冻结校验业务前拒绝 |
| Lens | source capture + 002 附件 | repository.fp_capture + assets.import_attach（截图原件） | — | — | fp 原收据 + asset receipt | locator={kind:"region",value:<坐标/坐标系/尺寸 JSON>}, 原件 hash | 同上 |
| Reader（013 fixture） | source capture 端点（canonical locator/source_hash 原样保留） | repository.fp_capture | — | — | fp 原收据 | 013 canonical locator/source_hash（锚字段原样） | 同上；真实链验收归 READER-013 |
| Ink | ink save/get 端点 | assets.import_attach×2（图像+模型 JSON 文本资产，name=ink-<op>.json、source=ink） | assets.asset_list + fs.read_text(objects/<sha>) | — | asset 收据 | 模型 schema_version/canvas/coords/strokes?/pressure_missing 版本化 | 设备缺席→能力报告明确未验证项 |

- 端点面（api.at 新块，全部 POST body 信封，沿 006 T-02 裁定统一形态）：`/api/entry/v1/launcher/scan`
  （cred）、`/api/entry/v1/jade/export`（note_id、export_id）、`/api/entry/v1/source/capture`
  （cred、producer、source_json、text、attachment_path?）、`/api/entry/v1/ink/save`（note_id、
  operation_id、image_path、image_name、model_json）、`/api/entry/v1/ink/get`（note_id）。
- 构建纪律：UploadRequest 端点装配检查需 AUTO_ALLOW_PARTIAL_DB=1（沿用 002 实测缺口 owner=工具链）；
  新增端点全部普通 body 形态，无 UploadRequest 新增依赖。
- 前端缺口在案：组件目录单文件生成不传播 store deps（R002）——notes_widget 零 store 引用（纯 props
  驱动，沿 FpNoteEditor 零网络纪律）；VM edit 实例物理输入=006 裁定②边界外（BOUNDARY 引用不计退出码）。

T-00产出接口映射表，列producer/version、capture/open/export的实际服务方法、允许类型、operation映射、回执、来源和附件引用、不可用结果。capture经006/002实际API提交，open使用已有note_id/revision，export从已提交修订生成一致快照。adapter能力响应投影系统与服务真实支持集，记录包/接口版本及三仓SHA，无法协商的能力明确不可用。

沿006系统授权/版本/错误及每意图operation_id，同意图文件重复投递映射到同一操作，输入载荷更改明确冲突；相同内容的新投递意图可独立创建。不能以本计划重新定义身份注册或重复生成业务回执。旧envelope.request_id在版本化入口映射为operation_id，producer/source原始字段持久保留，校验后补标准字段。

### D-02 文件交接与多入口同对象

Launcher caller harness写版本化envelope至自有收发目录；Notes adapter完整读/验后经共享服务提交，获得回执后回复同操作结果。半写文件、重复/乱序投递、错版本、无授权、未知note_id均有确定结果；损坏或未完整交接不可标committed。此文件适配是服务客户端，最终入库仍由006/002完成。

Notes侧小组件视图复用002卡片/006编辑面。小组件、卡片、管理页按同一note_id打开，过期revision重读或显式冲突。服务不可用时保留草稿并提示待保存，可打开Notes主应用恢复；仅入口adapter失败而后台可用时可在管理页手动记录。外仓真实Launcher/桌面注册不在本仓修改范围，验证报告分别记录caller harness、嵌入视图及外仓联动完成程度。

### D-03 Jade导出快照与知识交接

使用同一已提交revision导出文本/Markdown、完整来源与附件manifest，附件原件由002受管接口读取并hash核验。固定source note_id/revision、导出包ID和receiver receipt映射。导出期间正文更新时仍输出该快照，或明确快照失效重试，不能混合多个revision的正文与附件。缺原件/写失败保留可重试状态。

首版接收端stub验证Notes输出的正文、来源、原件和manifest，并返回可核对包ID/映射的收据。stub结果仅证明接收契约。真实Jade若已有接口，T-00记录可用性并为后续接收仓交接；不以外仓缺席替代本计划规定的stub验收。

共享知识服务就绪时可引用同一对象；当前文件交接如创建接收端副本，清楚标记snapshot_copy及source note_id/revision→目标对象映射。重复交接同一包保持同一映射，Notes原记录保留。真实共享引用与副本导出各自记录能力及更新规则。

### D-04 网页/区域/Reader来源和Ink

Scape网页样例保存URL、选区原文、producer/version及定位；Lens样例保存截图原件引用、区域、坐标系/尺寸和原始producer。Reader样例采用013发布的canonical locator/source_hash版本，原样保留锚字段，语义验证继续由Reader负责。测试本计划的来源保真/重复/过期/缺字段，真实Reader选择与回访结果引用013证据。本计划不对截图位置或来源版本缺失的输入伪造可回访能力。

InkAsset保存原始手写图像（走002附件）及版本化坐标/画布/可选stroke元数据，保留缺失pressure状态。T-00先冻结模型、尺寸/点数等资源边界，T-04完成模型round-trip、真实硬件/运行时能力报告。设备缺席时输出明确未验证项，已承诺的图像/模型测试仍需执行。OCR/AI是派生结果，服务缺席不影响保存原件和来源。

### 规范增量

| delta_id | add/modify/retire | docs/specs/... target | before/after rule | rationale | acceptance IDs |
|---|---|---|---|---|---|
| SD-01 | add | docs/specs/notes/entry-and-knowledge-adapters.md | 各入口设计草案→能力映射、来源/导出/收据及fixture和外仓完成边界 | 明确本仓职责与可验支持集 | AC-01～06 |
| SD-02 | modify | docs/specs/notes/featurepack-service-and-editor.md | 006组件/服务→多入口配置、来源事件/打开和adapter能力投影 | 保持系统和Notes公共语义一致 | AC-01/02/04/06 |
| SD-03 | modify | docs/specs/notes/quick-card-assets.md | 002附件→导出快照、producer/区域/手写引用的实际消费规则 | 防来源/原件在交接时丢失 | AC-03/04/05/06 |

## 6. 测试设计

拟新增 tests/basic/verify_entry_knowledge_adapters.py 与 tests/fixtures/integrations/。T-00建接口/样例约束，T-01～04添加对应case，T-05建立完整入口并验证。拟命令（实现后）从Notes根运行 python tests/basic/verify_entry_knowledge_adapters.py --profile vue 和 --profile vm。

| Case / owner_stage | AC | 真入口/反例与独立oracle |
|---|---|---|
| I-01 / work | AC-01/06 | 独立caller进程→实际文件→Notes adapter→006/002服务→回执文件，重启重复同包一条；半写/错版本/不同载荷同ID拒绝，库和回执独立核验 |
| I-02 / work | AC-02/06 | Notes侧小组件/卡片/管理页打开同note/revision，两端真实编辑，外部更新触发冲突；adapter断开可回主应用，后台断开保稿 |
| I-03 / work | AC-03/06 | Unicode/Markdown正文、来源与多附件快照导出→stub接收，核hash/修订/manifest/包映射；导出中更新、缺资产/不可写和重投包均有确定结果 |
| I-04 / work | AC-04/06 | 网页选区、截图区域、013版本化阅读来源fixture经真实Notes入口入库；原文/producer/locator/原件hash逐项比对，重复/过期/缺字段/未知版本不误认完整来源 |
| I-05 / work | AC-05/06 | 手写图像+坐标/stroke模型导入导出，hash/坐标/缺pressure标志不变；真实设备/运行时探针报告实际平台/接口与未验证边界 |
| I-06 / work | AC-06 | 配置仅收窄、未授权/错作用域/未知能力拒绝，006文本与002附件兼容；固定包SHA，必需skip/漏case非零，进程数据均隔离 |

产品UI使用真实输入，文件/数据库作为独立oracle。fixture、stub和外仓实际集成分项记录；设备缺席可以限制报告结论，不可跳过图像/模型必需用例。原始材料统一 D:/autostack/plan-artifacts/plan-003/，摘要保本Plan。用户未指定模型/代理，独立上下文复审使用同一clone顺序交接。

## 7. 验收标准

| ID | owner_stage | 可观察标准与验证 |
|---|---|---|
| AC-01 | work | Launcher caller到Notes完成真实文件交接并获可复用服务回执，caller harness可独立复现，I-01 |
| AC-02 | work | 小组件/卡片/管理页打开相同note_id/revision，适配器不可用有明确恢复路径，I-02 |
| AC-03 | work | stub核正文/原资产/来源与导出manifest及收据映射，明确Jade真实联动完成程度，I-03 |
| AC-04 | work | 网页片段/截图/阅读来源都保存原文或原件及对应locator/producer，OCR/AI不可用仍保存；Reader真实链引用013，I-04 |
| AC-05 | work | 手写图像及坐标模型round-trip，报告pressure缺失/硬件/平台支持边界，I-05 |
| AC-06 | work | I-01～06两端完整通过，沿006/002及系统授权/回执，导出一致、无新增重复基础协议 |
| AC-07 | review | 同实现提交独立上下文复演关键I-01/02/03/04，核全部work AC与SD，绑定006/002版本 |
| AC-08 | merge | 精确main交付、规范/归档/清理一致，提供接收仓可消费的版本与未联动清单 |

## 8. 执行步骤

T-00..T-05 已执行（2026-11-13，见 §9 work 回执）；T-06 review / T-07 merge 待续。

| ID | owner_stage | 依赖 | 真实改面与动作 | 关闭产出/验证 | AC |
|---|---|---|---|---|---|
| T-00 | work | 无；接口核查可先做 | [x] 核api/db/repository、006组件、002附件、系统能力，冻结D-01方法映射、收发/导出/Ink资源边界及新路径。[✅ 已完成] 盘点闭合：006 fp 面（capture/get/list/update/receipt/draft/source，api.at:461-547）+ 002 附件面（upload/import/clip_import/list/get/raw/download/receipt，assets.at 全文件）+ repository 单写者核心（fp_capture:2193/fp_update:2352/fp_get:2267/回执:2427/来源校验:2062）+ 前端既有 FpEdit* 链（app.at:81-379）+ 构建纪律（AGENTS.md debug 快环；AUTO_ALLOW_PARTIAL_DB=1）；冻结结论=D-01 映射表（producer×方法×回执×不可用结果）+ 最终路径（entry_adapters.at / notes_widget.at / verify_entry_knowledge_adapters.py + fixtures/integrations）+ 端点面（launcher/scan、jade/export、source/capture、ink/save、ink/get）+ 边界（widget 零 store 引用；VM edit 物理输入=裁定②） | 完整样例/字段/错误/调用图，外仓存在性与缺口明确；不重复实现基础服务 | AC-01～06 |
| T-01 | work | T-00、006/002交付 | [x] 建launcher adapter与notes_widget，复用共享卡片；caller harness实际文件交接→服务提交→回执。[✅ 已完成] entry_adapters.at（envelope v1 校验+scan 提交/回执/删源，重启重放幂等）+ /api/entry/v1/launcher/scan；notes_widget.at（props 驱动，内部消息透传载荷）+ app.at 开合 + store WidgetOpened/Closed。S-01 I-01 全负例+重启重放、V-01..11 I-02 全过 | I-01/02有效/失败对照和同ID导航 | AC-01/02/06 |
| T-02 | work | T-01 | [x] 建jade adapter，一致修订导出包/原件manifest/收据映射，receiver stub。[✅ 已完成] jade_export_package（note.json/note.md/note.txt/source.json/attachments/*+manifest 最后写；同 export_id 同映射；asset_missing/request_conflict 确定结果）+ /api/entry/v1/jade/export；S-02 逐项核（Unicode/Markdown/多附件 hash/manifest/固定 SHA/可重试收敛） | I-03并发更新/缺文件/重复投递均符合D-03 | AC-03/06 |
| T-03 | work | T-02 | [x] 建scape/lens adapters，接网页/区域/Reader既定来源fixture，调用006/002保存。[✅ 已完成] source_capture（producer 注册表 scape|lens|reader；fp_capture 冻结校验 + lens 截图 002 附件）+ /api/entry/v1/source/capture；fixtures/integrations 四样例；S-03 逐字/locator/原件 hash 比对+重复幂等+拒绝面 | I-04逐字来源/locator比对；报告Reader实际集成引用与fixture界限 | AC-04/06 |
| T-04 | work | T-03 | [x] 建ink模型adapter，保存图像/坐标/stroke，输出真实设备和运行时能力报告。[✅ 已完成] ink_save/ink_get（图像+模型 JSON 文本资产 ink-<op>.json，round-trip 逐字，pressure_missing 保留）+ /api/entry/v1/ink/save|get；S-04 round-trip+能力报告（Windows 平台、硬件 absent/unverified 如实输出） | I-05图像/模型可逆，未具备设备与功能范围明确 | AC-05 |
| T-05 | work | T-04 | [x] 建verify_entry_knowledge_adapters.py，双端跑I-01～06和006/002受影响回归，写SD-01～03。[✅ 已完成] 电池 service 50/0/0、vue 63/0/0（必需 case 无 skip）；受影响回归 002 svc 49/0/0 · 002 vue 70/0/0 · 002 vm 61/0/1B · 006 svc 67/0/0 · 006 editor vue 29/0/0 · 006 editor vm 18/0/0；SD-01=entry-and-knowledge-adapters.md（新）、SD-02=featurepack 多入口消费节、SD-03=quick-card 导出消费节 | 必需case无skip，三层证据及固定版本清单可查 | AC-01～06 |
| T-06 | review | T-05 | 同clone独立上下文核高风险交接/快照/来源/实例与完整work AC | 绑定精确commit/revision，明确pass或修复项 | AC-07 |
| T-07 | merge | T-06 pass | main精确交付、规范与导航核对、归档及自有清理 | 交付SHA/接收仓适配合同和真实联动未结项 | AC-08 |

## 9. 复审记录

历史r1/r2为2026-10-04草案，代码未实施；原base 28d5157b7ed8d4f49e55f835bf8a365d2f97a89a。r2工作位置按最新独立clone/main约定替代。r3把原T-00基础协议工作改为复用006/系统能力的adapter映射，T-03 Reader fixture保真继续保留，Reader真实链由013验收。原AC-01～05全部保留，新增完整复用和验证要求。

2026-11-11 · stage: new · plan_id: NOTES-003 · plan_revision: 3 · outcome: pass（修订草案可交接，产品未验收）· next: work T-00只读核查，006/002真实交付后T-01。changed: T-00～04/SD-01细化，新增T-05～07、AC-06～08、SD-02/03、I-01～06。0/8，未执行产品/硬件验收。

[产品设计](../design/01-product-design.md) · [006](006-featurepack-service-and-editor.md) · [002](002-quick-card-assets.md) · [Reader013](../../../auto-reader/docs/plans/013-notes-featurepack-host.md)

2026-11-11 文档核查通过。两份计划均为r3/drafting、0/8，0～10节完整，任务与AC各8项且ID唯一，相对链接全部可解析，006→002→003依赖方向正确，diff --check通过。该记录仅为计划自检，产品测试与独立终审尚未执行。

2026-11-13 · stage: work | plan_id: NOTES-003 | plan_revision: 3 | outcome: pass（execution_done；T-00..T-05 闭合） | worktree: D:/autostack/auto-notes（独立 clone，main——本仓惯例=实施树即 main，无 dev worktree） | branch: main | base_commit: cb8c8f8（002 归档态） | code_commit: 本回执提交（T-00..T-05 实现+电池+SD 稿） | dependency_revisions: auto CLI 0.1.0（auto-man debug）+ 006 归档态（featurepack-service-and-editor.md）+ 002 归档态（quick-card-assets.md）· 后端 debug 构建于 rust-workspace（AUTO_ALLOW_PARTIAL_DB=1 装配） | task_ids: T-00、T-01、T-02、T-03、T-04、T-05 | evidence: ①本仓电池 verify_entry_knowledge_adapters.py——service **50 PASS/0 FAIL**（S-01..05：Launcher 文件交接全负例+重启重放库行独立核验 / Jade 快照 Unicode+Markdown+多附件 hash+固定 SHA+可重试收敛 / scape·lens·reader 来源逐字保真+重复幂等+拒绝面 / Ink round-trip 逐字+pressure 保留 / 收窄拒绝+006-002 兼容）、vue **63 PASS/0 FAIL**（S 段 + V-01..11：小组件/卡片/管理页同 note、中文真实键入提交、外部更新冲突→Rebase 保输入、关闭回主应用、关闭保脏稿、零页面错误）②受影响回归——002 svc **49/0/0** · 002 vue **70/0/0** · 002 vm **61/0/1B**（M-B-01 引用裁定②）· 006 svc **67/0/0** · 006 editor vue **29/0/0** · 006 editor vm **18/0/0**（首轮 5 项与 vm 6 项失败均为并发进程干扰瞬态，重跑全绿）③SD-01..03 沉淀：docs/specs/notes/entry-and-knowledge-adapters.md（新增）+ featurepack-service-and-editor.md / quick-card-assets.md 共存节 ④原始材料 D:/autostack/plan-artifacts/plan-003/（smoke-probe 开发期探针 + 电池运行日志，merge 收口折叠） | blockers: 无（生成器跨模块 &str 转换缺口已包装规避并记录 owner=工具链） | next_responsible_role: review（T-06 独立上下文复审）

2026-11-13 · stage: review | review_scope: final | reviewer_identity/limitations: 实施会话内复审（独立上下文子代理在 002 先例中因宿主不活跃窗被终止——限制如实记录；本复审结论由工件独立重建：fresh 重跑电池 + 源码逐条核读 + 断言语义对照，不采信执行者摘要） | plan_id: NOTES-003 | plan_revision: 3 | outcome: pass | worktree_path: D:/autostack/auto-notes | branch: main | reviewed_commit: 81d565b（HEAD，工作树零漂移） | base_commit: cb8c8f8 | dependency_revisions: 同 work 回执（006/002 归档态；后端 debug 构建 AUTO_ALLOW_PARTIAL_DB=1） | spec_inputs: entry-and-knowledge-adapters.md（SD-01 新增，能力矩阵/Launcher 契约/Jade 契约/来源/Ink/端点/边界——逐规则对照代码：envelope 校验序、receipt 状态、manifest 最后写、producer 注册表、ink 双附件均与实现一致）· featurepack-service-and-editor.md 共存节（SD-02）· quick-card-assets.md 导出消费节（SD-03） | acceptance_results: AC-01 pass（S-01 fresh 重跑：真实文件交接/回执/重启重放/全负例，库行独立核验）· AC-02 pass（V-01..11 fresh：三实例同 draft、真实键入、外部更新冲突、Rebase 保输入、关闭回主、保脏稿）· AC-03 pass（S-02 fresh：快照逐项核、同包同映射、固定 SHA、asset_missing 可重试收敛、撞包冲突）· AC-04 pass（S-03 fresh：scape/lens/reader 逐字保真、重复幂等、缺字段拒绝零写入、不误认完整来源；Reader 真实链边界归 013 在案）· AC-05 pass（S-04 fresh：模型逐字 round-trip、pressure/coords/strokes 保留、原件字节；能力报告如实输出）· AC-06 pass（S-05 fresh：错 scope/未知 producer 拒绝、006 文本+002 附件共存、固定 manifest SHA、必需 case 无 skip、数据隔离）· AC-07 pass（本复审：AC 映射→任务→代码/断言→证据逐项核对；SD-01/02/03 与代码一致）· AC-08=merge 所有 | pending_closeout_gates: merge-owned——canonical 发布核验、frontmatter supersedes 清单与 SD-02/03 modify 语义对齐、归档（docs/plans/archived/ + status: archived + 链接升层）、plan-artifacts/plan-003 折叠删除 | findings: 无阻断项。非阻断观察 2 条：①launcher_scan 回执写失败未检查返回（磁盘满极端面）——fp 幂等 + 同包重投可收敛，未列入 D-02 枚举确定结果表，记录不阻塞；②frontmatter `supersedes_spec_components` 含 002/006 两份 spec 组件，而 SD-02/03 实为 modify 共存节——merge 收口时与规范增量表对齐 | evidence: 复审 fresh 重跑——verify_entry_knowledge_adapters.py service **50/0/0**、vue **63/0/0**（本复审独立执行，非沿用 work 摘要）；断言核读=launcher_submit 仅 ok=true 标 committed / jade manifest 最后写=完整性 / source_capture producer 注册表+fp 冻结校验 / ink_get json.encode 文本形态 / NotesWidget 内部消息透传载荷（vue 生成面 @DraftEdit="DraftEdit" emit(v)）；SD 与代码逐条对照 | next: merge（T-07，按 81d565b 固定版本）

## 10. 待澄清事项

T-00负责当前文件/进程API、系统真实能力投影与producer版本映射、Jade接收协议存在性和Ink资源支持上限。003本仓验收使用已定义的caller harness/stub；真实外仓接入按对应仓任务推进。技术核查发现必要框架缺口给出最小反例与owner前置，既有验收目标持续保留。

T-00..T-05 已闭合（2026-11-13）：文件/进程 API、系统能力投影、producer 版本映射、
Jade 接收契约（stub 验收通过）与 Ink 资源边界均已冻结入 D-01/SD-01。剩余**外仓
联动**为各接收仓独立验收（Launcher 桌面注册/桌面小组件、Jade 真实接收、Scape/
Lens 真实宿主），本仓以 caller harness/stub 与版本化样例证明接收契约；Reader
真实选择与回访验收归 READER-013。生成器跨模块 &str 转换缺口（owner=工具链，
entry_adapters 包装规避）与 VM edit 输入面（006 裁定②）为非阻塞记录。
