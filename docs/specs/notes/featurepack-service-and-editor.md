# featurepack-service-and-editor — 015-notes 共享笔记服务与可嵌入编辑器（current-state）

> 状态：current-state（NOTES-006 r2 实施：T-02/T-03/T-06/T-07/T-08 交付面）·
> 更新：2026-11-11 · 计划：NOTES-006（联合合同见 auto-os OS-067 / featurepack-v0 ·
> Reader 宿主 READER-013）· SD-01（产品契约）+ SD-03（操作身份/持久草稿/公共
> 状态/参数事件/失败恢复协议）

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
- 组件零网络依赖（I/O 宿主执行）；导入形态：同仓 `use fpack.fp_host: <函数>`
  + `use { package: official from "./components" }`；跨仓 `dep notesfp
  { path: <auto-notes>/src/front/components }`（pac.at）。

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

## 验证入口

- `python tests/basic/verify_featurepack_service.py`——F-01..11 + S-01（提交
  成功丢回包→重启→同操作同文重放）+ S-02（冻结 schema 拒绝面/迁移半途故障
  自愈/残缺来源 incomplete 可读）。
- `python tests/basic/verify_featurepack_editor.py --profile vue|--profile vm`
  ——双实例/保存中键入/关页重启恢复/丢回包 pending 同 ID 续查/冲突保输入
  Rebase/零页面错误；VM 轨 type_text 真实输入 + 进程重启恢复（必需 case 无
  skip，缺失即非零）。

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
