# featurepack-service-and-editor — 015-notes 共享笔记服务与可嵌入编辑器（current-state）

> 状态：current-state（NOTES-006 r2 实施：T-02/T-03/T-06/T-07/T-08 交付面；
> NOTES-007 增补「存储并发模型」+ 并发锤/追踪验证入口 + 发布件版本锚）·
> 更新：2026-11-16 · 计划：NOTES-006（联合合同见 auto-os OS-067 / featurepack-v0 ·
> Reader 宿主 READER-013）、NOTES-007（存储并发模型修复）· SD-01（产品契约）+
> SD-03（操作身份/持久草稿/公共状态/参数事件/失败恢复协议）+ NOTES-007 SD-01/02

## 来源快照（T-06 冻结闭集，不可变）

写入（fp capture）与读投影共用一个校验器；7 键闭集，`chapter` 可选，其余必需：

| 字段 | 类型/约束 | 说明 |
|---|---|---|
| book_id | str 非空 ≤128 | 书目域名（`book:<id>`） |
| source_hash | str 非空 ≤128；拒绝哨兵 `"v1"` | 真实内容哈希——Reader 负责真实性，服务端核在场/类型/长度（G-06 在案） |
| title | str 非空 ≤256 | 书目原文（Unicode 保留） |
| author | str 非空 ≤256 | 书目原文（Unicode 保留） |
| quote | str 非空 ≤256 | 原句（不可变；note.title = quote） |
| chapter | int 可选 | 章节号 |
| locator | object：kind 非空 ≤64、value 非空 ≤1024、v 可选 int | canonical 定位（CFI）；锚语义归 Reader |

- 校验失败 → `invalid_request`（err_detail 指名性），业务前拒绝、零写入。
- **闭集**：对象键数 >7 = 未知来源结构/版本 → 拒绝（前向冲突显式化，升版走
  `interface_version` 升级，不静默扩字段）。在案局限：chapter 的 int 类型性
  与数值字符串的 as_int 宽容度未核——错类型反例走 locator/数组/缺字段面。
- **快照原文存储**（source_json 原样入库，不重组不规范化）；`quote` 缺失不再
  回落正文（r1 行为随冻结 schema 移除——title 与 quote 关系固定为原句）。

## 读投影（fp get / fp list）

- 信封在 13 列文档外附加：`book_id`、`source`（快照原文或 null）、
  **`source_status`**：`ok`（过冻结校验，回访入口可用）| `incomplete`（旧 fp
  行只有 book_id / 残缺 / 异构——行保持可读，宿主显示「来源不完整」，回访
  入口不可用）。普通便签（book_id=''）不出现在 fp 面。
- **免 substr 拼接**（G-10 规避，2026-11-11 实测）：信封由 `row_to_doc_fields`
  字段段直接续接——不依赖 `substr(0, len()-1)`（当前生成器对局部字符串变量
  的 len() 产字符数而 substr 按字节，含中文 doc 错位产坏 JSON；服务脚本
  F-09a 崩溃复现后改为纯拼接，两轨一致）。

## 操作身份（每次意图分配，两宿主同律）

- `operation_id` = 单元意图稳定 ID：新建/用户确认更新每次新；**同意图重试
  复用**（同文同基修订）。换文、换基修订或成功确认后更换。
- `attempt_id` = 每次调用新（wire 门拒绝空值）。
- 去重键：`fp:<principal>:<operation_id>`（requests 表复用，intent 全匹配 →
  原收据重放 `replayed:true`；差异 → `request_conflict`）。内容相同的新建
  仍产生不同笔记——领域去重与内容匹配分开。
- 主应用路径以 `fp_edit_op/fp_create_op` 兼作主 API 的 request_id：同 ID
  重试经服务端意图重放幂等（丢回包恢复不二次推进）。

## 草稿状态机（fpack.fp_host 共享适配；组件零网络依赖）

每宿主实例持：draft_key、generation、note_id、base_revision、operation_id、
待提交输入、用户输入版本、保存状态。状态转移统一经 `fp_state_next`：

- `idle → dirty`（键入）`→ saving`（提交；saving 在途忽略重复提交）`→
  saved`（ack）/ `pending`（回包未观察）/ `error`（传输/磁盘失败）/ `conflict`
  （修订冲突）。`rebase`：认领服务器修订为新基底，用户输入不动 → `dirty`
  （再提交是新意图）。`discard` → `idle`。
- **守卫**：异步结果先核 draft_key/generation/输入版本；成功只清除已提交那
  一版输入（`fp_*_sent`），提交后继续键入保留并仍为未保存。
- 传输/磁盘失败不投影为可 Rebase 的修订冲突；重新指定服务端 revision 后是
  新更新意图。

## 持久草稿（宿主检查点 + 服务端 fp_drafts 表）

- 表：`fp_drafts(draft_key PK, text, state, op, base_rev, input_ver)`——分列
  存（前端免 JSON 解析）；上限 64KiB/槽。
- draft_key = `fpdraft|<本地用户>|<宿主>|<书目/笔记>|<实例>`（fp_host.fp_draft_key）；
  v0 本地服务单用户诚实边界（Notes 主应用 user=local；不引入登录前置）。
- 本地 scratch 面（`/api/fp/draft/put|get|delete`）：**不属于 notes.fpack/1
  外部契约**，不经过 fp policy 门（数据归属与 /api/notes 同源）；Reader 宿主
  草稿自持。
- 检查点（异步安全点；同步输入 handler 禁 HTTP）：提交前落盘（丢回包/关页
  后同操作恢复重试）、冲突态落盘、SelectNote 切换落盘；Init 恢复（持久
  `saving` → 投影 `pending`）；提交成功/同文已随主路径提交 → 清槽；用户显式
  Discard → 清槽。保留或丢弃须有明确用户动作。

## FpNoteEditor 参数/事件（冻结，fp_editor.at 实际契约）

- props：`mode`（create|edit）、`note_label`、`draft_text`（草稿 prop 往返）、
  `save_state`（七态字符串；组件渲染 saving/saved/pending/error/conflict
  徽标，dirty/idle 无徽标）、`conflict_revision`、`server_body`。
- 回调：`on_draft_edit(v)`、`on_submit_text(text)`、`on_rebase`。
- 组件零网络依赖（I/O 宿主执行）；导入形态：同仓 store 点路径
  `use components.fp_host: <函数>`（`fpack` 包名形态在 vue 生成器 use-fn 池
  静默跳过——实测修订①，勿用）+ 组件包
  `use { package: official from "./components" }`；跨仓 `dep notesfp
  { path: <auto-notes>/src/front/components }`（pac.at）后
  `use notesfp.fp_host: <函数>`。

## 来源回访统一出口（T-06 唯一出口）

- `OpenSource(note_id, source)`：组件事件或宿主来源卡统一经
  `fp_open_source_payload(note_id, source_json)` 构造载荷，两个应用一致消费。
- Notes 主应用 v0 消费 = 来源卡（`fp_src_*`：title/author/quote/book +
  source_status）与 OpenSource 详情卡；**回访入口仅在 source_status=ok 时
  可用**，incomplete 显示「来源不完整（旧来源，回访不可用）」。配置不提升
  服务权限——只投影本地已读数据（`/api/fp/source/of`，主应用本地全权面，
  不经过 fp policy 门；Reader 读写仍走 cred 端点按书籍范围校验）。
- 配置与默认值（两宿主声明面）：create/edit 双输入默认启用；只读/禁提交由
  宿主以 save_state 投影面控制（组件无独立只读 prop——冻结参数表不变式）；
  来源回访默认 = 仅 ok 来源。

## 服务端点面（notes.fpack/1 + 本地面）

| 端点 | 门 | 说明 |
|---|---|---|
| POST /api/fp/v1/capture | version+attempt+policy+冻结来源校验 | 幂等按 `fp:<principal>:<operation_id>` |
| POST /api/fp/v1/get | version+policy | 13 列 + book_id + source + source_status |
| POST /api/fp/v1/list | version+policy | 按书分页（seq 降序；cursor/limit 1..100） |
| POST /api/fp/v1/update | version+attempt+policy | 仅正文；expected_revision 条件 |
| POST /api/fp/v1/receipt | version+policy | committed（原收据）| not_observed |
| GET /api/health | — | `{status:ok, interface:"notes.fpack/1"}` |
| POST /api/fp/draft/put|get|delete | 本地面（无 fp 门） | 宿主草稿持久暂存 |
| POST /api/fp/source/of | 本地面（无 fp 门） | 来源卡投影（FpSourceView） |

## 存储并发模型（NOTES-007，SD-01）

服务存储层为 `repository.at`（SQLite 单写者，WAL）。并发契约（`notes.fpack/1`
端点面/幂等语义/来源闭集不变，本节省略）：

- **读路径零写锁、单连接**：`repo_get / repo_list_active / repo_search /
  read_receipt / repo_status / fp_get / fp_list_by_book / fp_receipt /
  fp_draft_get / fp_source_of_view` 每次请求恰好一次 `sqlite.open`，只发
  只读语句（就绪探针 + SELECT）——**不发 `BEGIN IMMEDIATE`、不发
  `ALTER TABLE`、不发 meta 写**。WAL 下读写并行；外部写锁（另一连接
  `BEGIN IMMEDIATE` 持有）期间读请求实测 p99 ≪ 2s（R-02/R-03）。
- **schema/迁移就绪探针（零写）**：`meta.schema_v='3'` + 结构哨兵
  （`notes.book_id`、`notes.source_json`、`requests.intent` 三列存在 +
  `fp_drafts` 表存在）。全部满足 → 直连；任一不满足（全新库、v1/v2 旧库、
  **半途迁移/列被外部 DROP**）→ 进入**一次性慢路径**：`BEGIN IMMEDIATE`
  内二次确认（并发首请求/多进程同时初始化只有一个建表）→ 完整 DDL →
  `schema_v` 同事务提交 → 播种。慢路径每库生命周期至多一次（`storage_schema_init`
  日志计数；重启不重跑）。半途故障自愈语义原样保留（S-02）。
- **legacy 升级代际归属**：`upgrade_if_legacy`（SD-17/SD-18 状态机）只由 repo
  文档/来源访问入口驱动（`repo_get`/`repo_list_active`/`repo_search`/`fp_*` 与写
  路径）；诊断面 `repo_status`、`read_receipt`、测试 setup（`/api/v1/test/setup`）、
  显式迁移（`/api/v1/migrate`）只做 schema 就绪，**不得**抢先写 `meta.upgraded`
  ——否则先到的一次状态/回执查询会让随后就位的旧树永不升级（r5 电池
  U1..U10/S21 实测回归面）。状态面只**报告** `meta.upgrade_error`，不驱动升级。
- **写路径**：单连接 + `BEGIN IMMEDIATE` + `busy_timeout=5000`；BUSY/超时
  一律具名 `second_writer` 快速失败（有界 ≤5s，绝不悬挂）。写连接在
  `BEGIN` 前做文件背衬校验（见下）。
- **打开失败具名化（`storage_unavailable`）**：a2r `sqlite.open` 在文件打开
  失败时静默回退内存库（`a2r-std/sqlite.rs:31-43`）。存储层每次打开后用
  `PRAGMA database_list` 的 `main.file` 验证文件背衬，失败一律具名
  `storage_unavailable`——**绝不把幽灵空库当真实快照**（幻影 `not_found`/
  冻结空列表/假成功写禁令）。单文档读/写端点返回该具名码；typed 数组端点
  （`GET /api/v1/notes`、`/api/notes/search`）受类型面限制返回空集，同一
  失败由 `/api/v1/status.storage_error` 与 stderr 的 `storage_error` 行具名
  （可观测性由状态面承担，不静默）。
- **诊断面与 health 分离**：`/api/health` 不触存储（存活探针）；存储态经
  `/api/v1/status`：健康 `loaded:true, storage_error:""`；不可用
  `loaded:false, storage_error:<具名码>, upgrade_error:<原因>`；legacy 升级被拒
  （`upgrade_conflict`/`upgrade_incomplete`）不算存储不可用——库体照常报告，
  原因入 `upgrade_error`（S-16/S-19 语义）。
- **慢操作登记**：打开+就绪、写事务耗时 >2000ms 打印单行
  `storage_slow op=<name> phase=<phase> ms=<n>`（停摆取证与回归观测；不引入
  异步重排，仍为同步面）。
- **预算**：并发写负载（≥3 写者 + ≥3 读者 + draft 面，≥20 轮）下读 p99
  ≤ 2s；零 >2s 读停摆、零幻影 `not_found`、数据零丢失（R-01 口径）。

## 验证入口

- `python tests/basic/verify_featurepack_service.py`——F-01..11 + S-01（提交
  成功丢回包→重启→同操作同文重放）+ S-02（冻结 schema 拒绝面/迁移半途故障
  自愈/残缺来源 incomplete 可读）。
- `python tests/basic/verify_featurepack_editor.py --profile vue|--profile vm`
  ——双实例/保存中键入/关页重启恢复/丢回包 pending 同 ID 续查/冲突保输入
  Rebase/零页面错误；VM 轨 type_text 真实输入 + 进程重启恢复（必需 case 无
  skip，缺失即非零）。
- **并发锤（NOTES-007 R-01）**：`python tests/probe/concurrent_hammer.py
  --mode ui --rounds 20`——UI 形状并发（≥3 写者 create/update/capture/draft put
  + ≥3 读者 list/get/search/status/receipt/fp get/draft get + 同修订争用对），
  断言零 >2s 读、零幻影 `not_found`、capture 幂等回执不变、错误全部具名、
  数据零丢失。`--mode smoke`（1 轮）为日常快验入口。每个入口实测 ≤10s
  （test-discipline 新用例门）：`--rounds 20` ≈5–6s、`--rounds 5` ≈2s、
  `smoke` ≈1.7s；`--round-ops` 加码属自担时长的加严模式。
- **停摆放大器取证/回归（NOTES-007）**：`python
  tests/probe/concurrent_hammer.py --mode lockwindow`（默认 hold 5s，≈6s）——
  外部进程以 Windows `FileShare=None` 独占 `inbox.db`（AV/EDR 排他扫描形状），
  断言窗口内「要么正确数据、要么具名失败」，绝不允许静默空库/幻影 not_found；
  释放后数据完整且窗口内成功写已落盘。加长窗口（`--hold`）属取证自担时长。
- **存储并发模型追踪（NOTES-007 R-02）**：`python tests/probe/storage_trace.py`
  ——生成后端读路径函数体静态断言（零 `BEGIN IMMEDIATE`/`ALTER TABLE`/meta 写、
  恰好一次 `sqlite::open`）+ 运行时（schema 初始化日志恰好 1 行、重启 0 行、
  外部写锁下读 ≤2s 且数据正确、健康态 `storage_error` 为空；实测 ≈6.6s）。

## 发布件版本锚（NOTES-007，SD-02）

发布件 = `auto service --server rust` 生成的 Rust 服务二进制（`cargo run
--release`，AGENTS.md：release 仅交付门）。**身份 = 成员目录名 + 发布件 sha256 +
构建上下文**，不是「commit ⇒ 字节」：

- 成员目录名由项目路径派生（跨检出不同）；
- 生成件 `main.rs` 内嵌 assembly consumer 指纹，其输入含 notes 树之外的
  stdlib / auto-lang / selection 来源闭包（指纹随生成路径/时序可漂移：
  `35f70de4…` → `757bff4b…` 历史实测）；且**构建 env 的 flag 钉法参与 cargo
  指纹**——同 commit 且**同一生成件**（`main.rs 3f8ad97e…`）下，
  `cargo build --release`（17:02）产 `02016f3a…`，`auto service` 受管构建
  （17:11）产 `2e5e2898…`；同上下文重复构建为 no-op、sha 不变。**因果示例必须
  取自同一生成件**——混用不同生成件的 sha 会把指纹漂移错记成构建路径差异；
- 因此发布件复核以「文件 sha256 + 下表上下文」为准；跨上下文/跨检出重建须由
  发布流程重发并更新本表，不得假定可从 commit 复现。

| 版本 | 成员 | sha256 | 代码提交 | 状态 |
|---|---|---|---|---|
| NOTES-006 r2 交付件 | auto-notes-57d3816f-back | `6939bafa3544…` | 80a6d98 代际 | **退役**（NOTES-007 起被下表取代；Reader 的 6939bafa pin 随之升级） |
| NOTES-007 r1 | auto-notes-9e77e6a3-back | `2e5e28986706e9e3cb6954412b0e67904c09cc12b5fc8e3ba049a62892426240` | `83ae6ac`（代码；其后仅测试脚本/文档提交） | current |

**r1 锚定件构建上下文（构建 17:11；验收 17:17–17:19，2026-11-16）**：

- 发布路径：`auto service --server rust -B <port>`（生成 → release 构建 → 直启）；
  同一上下文内重复构建为 no-op（start-2 实测 0.53s），三次启动前后 sha 恒为
  `2e5e2898…`。
- CLI：`auto 0.1.0+plan-890-verified-r7-t19-24-g54fe407-dirty`，
  sha256 `c7dbb9f4eba8de88f03b6725e9c3bcb3024456d5243521ee397d73772f65df97`。
- auto-lang `107b23d0f`（`crates/`/`stdlib/`/`vendor/` 干净）；vendor/auto-down
  `c39ac7f9`。
- 生成件 sha256：repository.rs `f17cdc3b…`、db.rs `64eba72b…`、
  entry_adapters.rs `6738bba6…`、main.rs `3f8ad97e…`；assembly consumer 指纹
  `757bff4b6348ccd4`。
- 文件：17,836,032 B。

发布件复跑：`python tests/probe/concurrent_hammer.py --mode ui --rounds 5
--exe <release exe>`（R-04，≥5 轮零停摆；r1 锚定件实测 11/0）。

## 附件能力面（NOTES-002，SD-03：可协商附件扩展）

- FpNoteEditor 组件契约不变（props/回调/零网络依赖冻结表照旧）；快速卡片在
  宿主侧组合该组件（app.at 内联，见 quick-card-assets.md 组合边界）——编辑器
  无需感知附件。
- 附件端点 `/api/assets/v1/*` 为本地全权面（不经 fp policy 门，数据归属同
  /api/notes）；Reader 宿主后续可按 cred 范围协商消费（v0 仅 Notes 主应用）。
- 上传走 PLAN-730 服务端上传 ABI（UploadRequest 端点 + AUTO_HTTP_UPLOAD_* 硬
  上限 + 应用 NOTES_ASSET_MAX_* 取 min）；构建装配需 AUTO_ALLOW_PARTIAL_DB=1
  （实测缺口 owner=工具链）。
- 能力协商规则：宿主经 `/api/health` 的 interface 字段识别基础服务；附件面以
  端点探测（/api/assets/v1/receipt 404/200）为准，不做版本字段扩展（v0 前向
  冲突显式化同源冻结策略）。

## 三仓消费清单（AC-07）

| 仓 | 消费面 | 版本锚 |
|---|---|---|
| auto-notes（本仓） | `src/front/components/{fp_editor,fp_host}.at` + `components/{package,pac}.at`；主应用第一消费者（app.at FP 区 + notes_store 共享适配消费） | 本文件 + 2026-11-12 内容 SHA（下表） |
| auto-reader | `pac.at dep notesfp { path: "../auto-notes/src/front/components" }`（08d4932 起在案）→ FpNoteEditor 同版 + fp_host 函数（`use notesfp.fp_host: <函数>`；store 侧点路径形态见计划 §5 r2 实测修订 ①） | READER-013（宿主集成独立推进） |
| auto-os | OS-067 M1 冻结（manifest/daemon/注入键/health/端点形态表）；pack=notes-fpack 0.1.0，back.interface=notes.fpack/1，port 17819 | OS-067 §5 M1（G-01/02/03/09 桌面装配缺口 owner=OS T-02） |

组件内容 SHA（2026-11-12 交付态，NOTES-006 r2 work；sha256 前 16 位）：

| 文件 | SHA-256[:16] |
|---|---|
| fp_editor.at | `355cab805b644a9c` |
| fp_host.at | `3342f3e267276442` |
| pac.at | `8c802c147f870ee2` |
| package.at | `ee1cb036ad1751b0` |

path-only 依赖以本表 SHA 固定来源；组件内容变更 = 版本变更
（package.at 0.1.0 起，破坏性变更须升 interface/pac 版本）。

## 多入口适配消费面（NOTES-003，SD-02：多入口配置、来源事件/打开与 adapter 能力投影）

- 006 冻结组件契约不变（FpNoteEditor props/回调/零网络依赖冻结表照旧）；小组件
  视图（notes_widget.at）以 props 驱动复用 FpNoteEditor（edit 实例）与 002 附件
  投影——**组件零改动、零 store 引用**（组件目录单文件生成不传播 store deps，
  R002 在案）；小组件/快速卡片/管理页按同一 note_id/revision 打开（宿主传同一
  draft props 三处同源），关闭不清草稿不 flush（重开即恢复）。
- 多入口来源事件：Launcher 文件交接（entry/v1/launcher/scan）、Scape/Lens/
  Reader 来源 capture（entry/v1/source/capture）均经 repository.fp_capture
  提交——**同一冻结来源 schema 与幂等键**（`fp:<principal>:<operation_id>`），
  与 006 既有 capture 端点语义一致，无新增重复基础协议。来源回访统一出口
  （fp_host.fp_open_source_payload / fp_source_of_view）原样适用：入口来源
  经冻结校验 → source_status=ok；残缺/未知版本 → incomplete（明确不可回访）。
- adapter 能力投影：入口只消费服务真实支持集（来源 7 键闭集、受管原件、
  授权书 scope），无法协商的能力以 permission_denied/invalid_request 明确
  不可用，不伪造完整来源或回访能力。

