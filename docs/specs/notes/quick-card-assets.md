# quick-card-assets — 015-notes 快速卡片、多媒体收存与剪贴板接收（current-state）

> 状态：current-state（NOTES-002 r3 实施：T-01..T-05 交付面）· 更新：2026-11-13 ·
> 计划：NOTES-002 · 依赖：NOTES-001（durable-inbox）+ NOTES-006（featurepack）·
> SD-01（本文件：附件服务/快速卡片产品契约）+ SD-02（durable-inbox 附加表共存）+
> SD-03（featurepack 附件能力面）

## 能力矩阵（T-00 冻结，2026-11-12）

| 能力 | Vue 轨 | VM 轨 | 交付通道 |
|---|---|---|---|
| 文本/URL 收存 | 原生输入 | 原生输入 | 卡片输入（真实 UI） |
| 显式纯文本粘贴 | textarea 原生 Ctrl+V | 原生 | 真实 UI（V-09） |
| 二进制收存 | 无 file-picker 元素；TS 客户端无 multipart | dialog natives 共享 store 不可达 | **HTTP multipart API（PLAN-730 ABI）=双轨唯一 intake** |
| clipboard-bin 条目 | fixture 经 API 导入 | 同 | `clip_import`（版本化 v1） |
| 图片预览 | `<img src>` raw 端点（Range） | image 相对 URL 经 AUTO_HTTP_BASE 展开 | 双轨真实预览 |
| 视频预览 | video 元素（Range 拖动） | mpv 未启用=诚实占位 | vue 预览；VM 显式不支持态 |
| 原件 serve/导出 | `http.file_response`（inline/attachment + 单区间 Range + download_name RFC5987） | 同（双轨同律） | raw/download 端点 |
| hash | `hash.file_sha256`（暂存后对原件求） | 同 | 字节级 oracle |

UI 直接采件缺口（owner=工具链，v0 记录）：vue file-picker 元素缺失、TS 生成客户端
无 multipart、共享 store 调 VM natives 在 vue 面为 throwing stubs（track 门缺失）、
键盘快捷键绑定（Ctrl+Enter/Esc——提交走按钮，saving 在途忽略守卫兜重复）、
textarea 无 autofocus prop。

## 存储契约（SQLite + 受管目录）

- 受管根：`<data>/assets/`；内容寻址原件 `assets/objects/<sha256>`（多名同 hash
  共享原件，行级显示元数据独立；内容去重不合并用户意图）；操作暂存
  `assets/incoming/<file-key>`（`<rid>` 的 `:`→`-` 折叠——':' 非法路径字符）；
  PLAN-730 接收暂存根 `<data>/assets-staging`（与 root 同卷、互不嵌套）。
- 附加式表（不动 schema_v/notes/requests 既有列与升级状态机）：
  `note_assets(asset_id TEXT PK "a-<n>", note_id TEXT "n-<k>", name, bytes,
  sha256, mime, source, bin_json, seq, created_at)` + `idx_note_assets_note`；
  asset 序号在 `meta.asset_seq`（独立计数器，不占 notes counter）。
- 上限（NOTES_ASSET_MAX_* 可配置）：图片 20MiB、视频 200MiB、文件 64MiB；
  与服务硬上限 env `AUTO_HTTP_UPLOAD_*`（默认 64MiB/65MiB wire）取 min，
  应用 options 不得无界扩大；缺省 env 时有效上限 64MiB 如实生效。
- 禁止类型：`.exe/.bat/.cmd/.com/.scr/.msi/.ps1`（含差分判定——任意位置出现
  即拒，安全方向，过拒在案如 "a.exe.bak"）。

## 提交协议（incoming → objects → 事务；committed ⇔ 双成立）

调用序：暂存获取（multipart `upload_commit` hard_link create-only 到
`incoming/<file-key>`，或路径复制/clipbin 文本写字节）→ `file_sha256` 求哈希 →
objects 发布（exists-check + copy + size/hash 双核不冒认）→ `BEGIN IMMEDIATE`
→ 意图重放 → 写 note_assets + requests → 逐语句查返回值 → COMMIT → 清 incoming。

- 意图规范化：`as1|attach|<nid>|<kind>|<source>|<canonical JSON 全量语义>`
  （name/bytes/sha256/mime 或 clipbin producer+entries 清单）——同 rid 异文
  `request_conflict`，全匹配重放原收据 `replayed:true`；requests 复用，
  kind=`asset_attach`，rid=`ui-asset:<operation_id>`（收据 `revision:0`——
  附件不推进笔记修订）。
- 恢复四窗口（A-03）：W1 接收半途=PLAN-730 lease 看门狗自清；W2/W3
  incoming/objects 孤儿=同 operation_id 重试调和（commit create-only：既有
  incoming 为权威恢复材料，重传副本拒收 409）；W4 DB 提交后回包丢失=同 rid
  意图重放原收据。rejected/校验失败只清本操作命名空间，绝不动 objects。
- 故障注入（NOTES_TEST_MODE=1 门内，v1_test_fault 设 NOTES_FAULT）：
  `after_incoming`（暂存后）/`after_object`（objects 后、DB 前）/`after_entity`
  （COMMIT 前 ROLLBACK）/`after_manifest`（COMMIT 后报错）——注意
  after_entity/after_manifest 阶段 repo_create 等既有写入同样受检（种子须先于
  故障环境完成，电池按此编排）。

## 端点面（本地全权面——不经 fp policy 门；数据归属同 /api/notes）

| 端点 | 说明 |
|---|---|
| POST /api/assets/v1/upload | PLAN-730 multipart/raw（`UploadRequest` bypass to_bytes）；上下文走 multipart text_fields（operation_id/note_id/name/mime/kind/source）；回执即 HTTP status（201 committed/409 create-only/403 路径拒/400 应用上限 `too_large`；413 仅存在于 AUTO_HTTP_UPLOAD_* wire 硬上限层）| DB/对象失败保留 incoming 恢复材料并回 upload_error |
| POST /api/assets/v1/import | 路径导入（VM 通道：对话框/剪贴板文件路径经 HTTP 参数）；name 必填 |
| POST /api/assets/v1/clip_import | clipboard-bin fixture（v1：text/url 字节化 + file/image 路径复制；原顺序=seq；bin_json=producer/kind/entry/selected_at/origin）；单事务全量行 + 单 requests 意图 |
| POST /api/assets/v1/list | 按 note seq 升序；类型化 AssetView（含服务端组装 raw_url/download_url） |
| POST /api/assets/v1/get | 单条投影 |
| GET /api/assets/v1/:aid/raw | 预览：inline + content_type + 单区间 Range（file_response，双轨同律）；未知 asset → serve 时 404 不冒认 |
| GET /api/assets/v1/:aid/download | 导出：attachment + download_name（原名 RFC5987） |
| POST /api/assets/v1/receipt | committed（原资产集，含 bin_json）| not_observed |

构建纪律：UploadRequest 端点的再生成装配检查需 `AUTO_ALLOW_PARTIAL_DB=1`
（db.rs `pub async fn` 不被 db-fn 提取正则识别——T-01 实测缺口，owner=工具链；
写入仍全走 db.rs→assets 单写者核心，无 State<Db> 分叉）。

## 快速卡片（App 内联组合面；006 组件零改动复用）

- 正文编辑组合 006 冻结组件 FpNoteEditor（edit 实例，同草稿 prop 往返）：
  卡片与管理页打开同一条 note_id/revision，七态/意图/回执语义零复制；
  on_* 直绑 App 既有 FpEdit* 消息链。打开期间双 edit 实例并存（与 create+edit
  双实例同款共存面）。
- 卡片自有状态（NotesStore 附加）：card_open/card_wide/card_sort_title/
  card_assets/card_recent。动作：CardOpened（开+重载附件）/CardClosed（**不清
  草稿不 flush**——脏稿与七态保留，重开即恢复）/CardAssetsReload/
  CardWidthToggled/CardSortToggled/CardRecent(k)。内部消息派发必须带 `()`
  （缺括号被发射为裸引用不调用——T-05 实测）。
- 附件条：seq 升序投影；图片四 mime 分支真实预览（`<img src=raw_url>`，
  vue `<img>` / VM image 经 AUTO_HTTP_BASE 展开；损坏 → 解码失败态
  naturalWidth=0 且原件管理不受扰）；下载 URL 文本投影（link 元素仅 router
  `to:` 形——外链缺口 owner=工具链）。空态文案：No attachments / No recent notes。
- 最近项：工作集前 6 的索引表（card_sort_title 时标题字典序重排）；视图行
  经 CardRecent(k,title) 传值（view fn 不反引 .store）。
- 布局注（T-05 实测）：快速卡片内联于 app.at（组件目录单文件生成不传播
  store 依赖——R002 store 未定义，最小复现在案；缺口 owner=auto-ui-compiler）。

## 已登记边界（v0）

- UI 二进制采件缺口四项（见能力矩阵）——owner=工具链；v0 二进制采件经
  multipart API（HTTP 客户端/测试/外部集成），VM 通道=路径导入。
- 附件无删除端点（笔记 trash/restore 模型下原件只增；GC 留待需求）。
- 上传 409（create-only 撞既有恢复材料）=契约回复形态：客户端以 receipt/list
  收敛确认（操作已服务端提交或重试调和）。
- src/integrations/ 不建（计划原文"候选"经 T-00 裁定并入 assets.at）。

## 验证入口

- `python tests/basic/verify_quick_card_assets.py --profile service`——S-01..07
  （A-01 重启导出 hash/A-03 四窗口恢复/A-04 拒绝面+cap 真实执法点/A-05
  fixture 顺序·provenance·去重）。
- `--profile vue`——S 段 + V-01..10（卡片键入中文/提交/重复点击、附件真实解码
  +损坏失败态、宽窄/明暗、最近项/空态、关闭保脏稿、同草稿往返、显式粘贴、
  零页面错误）。P-V 形态：debug 后端 exe + vite dev（AGENTS.md 构建纪律）。
- `--profile vm`——S 段 + M 段（结构渲染/按钮链路/状态面；卡片编辑器 edit
  实例物理输入=裁定②边界外，BOUNDARY 引用不计退出码）。
- 继承回归：verify_featurepack_service.py 67/0/0、verify_featurepack_editor.py
  双轨（assets 附加面与 fp 契约共存不互扰）。

## 多入口导出消费（NOTES-003，SD-03：导出快照、producer/区域/手写引用的实际消费规则）

- **快照导出原件读取**：Jade 导出（entry/v1/jade/export）经 assets 受管接口
  （`objects/<sha256>` 行定位 + `hash.file_sha256` 核验）读取附件原件，
  **不改动受管原件**（只读消费；缺原件返回 asset_missing 可重试，重试经同
  export_id 收敛，不产生半包——manifest 最后写=完整性标记）。
- **producer/区域/手写引用**：Lens 截图原件经 import_attach（source="lens"，
  同 note 附件）与 Ink 手写图像（source="ink"）均落入 002 受管附件面——
  manifest 导出时按 seq 升序全量投影（asset_id/name/sha256/bytes/mime/seq +
  净化文件名），原件 hash 与接收端逐项可核；区域/坐标/压力等模型元数据走
  来源 locator 或 ink 模型文本资产（ink-<op>.json），不经附件 mime 猜测。
- 附件上限/禁止类型/去重/事务恢复语义（见上）对入口附件同样生效；入口
  adapter 提交的附件与卡片/管理页同属本地全权面，数据归属不变。

