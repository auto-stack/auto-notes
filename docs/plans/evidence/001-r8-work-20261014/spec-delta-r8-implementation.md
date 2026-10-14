# Spec delta r8 — 实现绑定稿（取代 r7 稿；SD-03/05/07/12/24/26 本轮修正绑定）

> 状态：**work 阶段提案，未发布**。基础：复审冻结稿
> [spec-delta-reviewed-r8.md](../001-r8-review-20261014/spec-delta-reviewed-r8.md)
> （其 SD→实现绑定表经复审判定 SD-07/12 全新升级失败边界、SD-03/05 错误出口、
> SD-26 持续身份/版本行为**不成立**、SD-11/16/28 证据关闭不完整）。本轮（r8 work）
> 修复对应实现并补 oracle 后重新绑定如下。canonical
> `docs/specs/notes/durable-inbox.md` 仍为 r3（blob 8f05b8ddb617d5d64e937e55027e782a2b0c0f85），
> 发布=merge。SD-21 按用户决策 A（2026-10-12）。供 independent review 对照
> [r8-work 证据](../001-r8-work-20261014/README.md)验证；merge 以【提案全文】整体替换。

## 本轮修正的 SD → 实现绑定（r8）

| delta | 规则变更 | 实现位置 | 验证 |
|---|---|---|---|
| SD-03/05 (r8) | 元数据/删除/恢复必需 UPDATE（state/pinned/tags/folder）失败传播：任一语句失败 → ROLLBACK + `ok:false storage_unwritable`；**UI 接收失败**——动作失败置 conflict+`action_error`，不刷新工作集/不清草稿，编辑器显示 "Action failed" 横幅（独立于 dirty 的 revision-conflict 分支） | `repository.at: repo_set_meta` 四写入逐一检查；`notes_store.at` DeleteConfirmed/TogglePinActive/TagAdded/TagRemoved 失败分支；`editor.at` action_error 横幅 | battery S20（pin/tags/state/restore 负例+正常控制，trigger 合成拒绝，挂载 `\|\| fail`）；scratch U11（9 断言含最终一致性）；Vue negatives-r8 R8-2（真实浏览器全链路） |
| SD-07/12 (r8) | 升级/迁移**完成事务内全部必需写入**逐一检查：fresh finalize（upgraded 标记/清 upgrade_error/清凭据）、两路 counter 导入、no-legacy 完成/凭据清理出口、repair finalize（r7 嵌套 if 实为「三者全败才回滚」→ 改析取）、数组迁移 migrated/corrupted_r1 标记。任一失败 → ROLLBACK + 显式 upgrade_error + 保留重试条件，绝不「笔记已入库但无完成标记」 | `repository.at: upgrade_if_legacy`（finalize/counter/两 no-legacy 出口）、`repair_legacy_merge`（counter/finalize OR）、`migrate_legacy_at`（标记写失败→ROLLBACK+saved=false） | battery S21（拒写 upgraded → 整体回滚/二次读取恒定/控制成功）；scratch U12；复审 api-extra 原输入复跑 4/4 |
| SD-26 (r8) | 稳定动作目标补全：flush 成功分支按目标 id 重定位后，**尾部不得用点击时的旧下标覆盖**（未刷新时旧下标才合法）；`LoadDraft` 上界兜底钳位（防越界解引用）；保存成功刷新 notes 再 LoadDraft ⇒ 草稿 revision 与服务器一致，连续保存不被自身旧 revision 拒绝 | `notes_store.at: SelectNote`（refreshed 局部标记）、`LoadDraft`（边界钳位） | Vue negatives-r8 R8-1（最终下标/身份/revision/两次保存/零 pageerror）；复审 navigation.cjs 原输入复跑 pass；r7 VM 负例 11/11（兄弟出口不回退） |
| SD-11/16/28 (r8) | 证据关闭：r7 README 链接修正（11 处深度+2 处诚实标注）；docs/README 计数刷新；本稿含 T-34 边界与当前工具链指纹；回归资产扩展（S20/S21、U11/U12、R8-1/R8-2） | docs/plans/evidence 各 README；tests 下持久驱动 | 链接 realpath 逐一核对；全套门终态见 r8-work README |

r6 的 SD-17..20、r7 的 SD-23/25/27/28（除上表修正外）绑定继续有效；
SD-08/15/21 及 SD-07/09..14 绑定不变。

## 【提案全文】merge 时整体替换 docs/specs/notes/durable-inbox.md

以下为复审冻结稿全文 + 本轮内联修正（修正处以 **(r8)** 标注）。

```markdown
# durable-inbox — 015-notes 可靠收件箱（current-state）

> 状态：current-state（NOTES-001 r8 实施，SD-02..SD-06 与 SD-07..SD-28 随
> r4–r8 修复落地）· 更新：2026-10-14 · 计划：NOTES-001 + AutoLang 742

## 存储契约（SQLite 单文件）

- 存储：`<data>/inbox.db`（SQLite，a2r-std `sqlite` 模块；WAL + busy_timeout=3000）
  - `notes(note_id PK, legacy_id UNIQUE, revision, title, body, tags_json, color,
    pinned, state, folder, seq, created_at, updated_at)`
  - `requests(request_id PK, note_id, kind, rev, doc_json, intent)` — schema v3
  - `meta(k, v)`：counter、req_seq、seeded、migrated、schema_v、upgraded、
    upgrade_error、corrupted_r1、repair_generation
- 文档 JSON（NoteDocument v1）：13 列固定序投影，`pinned` 为 JSON boolean
- 旧格式隔离：`<data>/legacy-backup/`；损坏报告 `<data>/corrupted/report-r1.json`；
  迁移备份 `<data>/backup/notes.json.bak`
- 数据目录：`NOTES_DATA_DIR` 覆盖 → %APPDATA%/XDG/`~/.local/share` +
  `/auto-notes/data`；每次解析即 `mkdir_all` 兜底

## 提交协议（事务串行化 + 规范化意图）

- 所有写入同一门禁：`BEGIN IMMEDIATE` → 幂等重放（事务内查 requests）→
  revision 检查 → 写 notes + requests → `COMMIT`；跨进程 `second_writer`。
- 请求意图规范化（`v2c|` 前缀）：kind/目标/期望修订/每个内容字段独立 JSON
  编码后拼接——字段边界无歧义。
- 幂等重放先于 revision 检查：intent 完全匹配 → 返回存储的原收据与文档快照
  （`replayed:true`）；任何差异 → `request_conflict`。
- 旧行裁决（决策 A，2026-10-12 用户批准）：intent 为空的行（Phase 1 收据、
  v1 三列行、残缺 v2 行）重放一律 `request_conflict`——旧持久层不含意图内容，
  "完全同意图"不可证明；原收据经 read_receipt 可查询，旧对象不受影响。
  r4 管道行经 v2→v3 从 doc 快照确定性重导。
- 条件更新：expected_revision ≠ 当前 → `revision_conflict`；8 并发同 revision
  恰好 1 成功。
- **(r8) 元数据/删除/恢复写入**：state/pinned/tags/folder 的必需 UPDATE 在
  同一事务内逐一检查结果——RAISE(ABORT) 类存储拒绝只中止单条语句，不检查
  返回值会让后续 COMMIT 把失败冒充成成功。任一失败 → ROLLBACK +
  `ok:false storage_unwritable`；UI 侧不得刷新工作集/清草稿，置
  conflict+action_error 并显示失败横幅（删除/置顶/标签/恢复全入口）。
- 故障点（NOTES_TEST_MODE=1 门禁内）：`after_entity`=COMMIT 前 ROLLBACK；
  `after_manifest`=COMMIT 后报 `fault_injected`。
- 软删 = state=trashed；restore 反转。

## Phase 1 JSON 布局升级（SD-07/SD-12/SD-17/SD-18/SD-23/SD-24，**(r8) 完成写入边界**）

- 入口裁决（升级状态机）：
  * 修复凭据唯一来源 = `meta.corrupted_r1` 含 "legacy upgrade"（r4 缺陷库
    标记）；`upgrade_error` 永不授予合并资格——冲突/普通 I/O 错误在前提消失前
    原样复现（重复读取/重启不得绕过，混合库恒 `upgrade_conflict`）。
  * 未升级 + 旧树在 + 库内已有 notes → `upgrade_conflict`（恒定）。
  * 未升级 + 旧树在 + 库空 → 全新升级（备份先行并校验；备份目录被普通文件
    占据/拷贝失败/备份 manifest 缺失 → `storage_unwritable` 不完成）。
  * 已升级 + 凭据在 + 旧树在 → 修复合并：manifest 引用实体逐一共同验证后，
    行缺失（r4 跳过的坏实体）→ 补导；行与实体导入产物可证明一致
    （revision/title/body 全等）→ 回收 manifest 权威元数据；更高修订/同修订
    异文 → 跳过保护。**修复合并的所有必需写入（行 UPDATE/INSERT、凭据清理、
    代际记录、收据导入）逐一检查结果：任一失败 → ROLLBACK + 显式 upgrade_error，
    凭据保留可重试；成功标志只跟随整个修复成功**（SQL 拒绝合成实验验证，
    不冒称物理掉电）。
  * 已升级 + 凭据在 + 旧树不在 → 清凭据记代际，不再重导；**(r8) 清理/代际
    写入失败显式 `storage_unwritable`（部分清理可重试）**。
  * **(r8) 未升级 + 旧树不在（全新库）→ upgraded 完成标记写入失败显式
    `storage_unwritable`，不得静默放行。**
- **(r8) 完成事务必需写入**：fresh 升级的 finalize（upgraded 标记、清
  upgrade_error、清 corrupted_r1 凭据）与两路 counter 导入，逐一检查——
  任一失败 → ROLLBACK + upgrade_error，旧树与库均保持可重试，绝不出現
  「笔记已入库但无完成标记、后续读取被 upgrade_conflict 挡死」的假完成。
- 权威清单与实体共同验证（合并前，两路共用）：实体——note_id 非空且与 entry
  一致、legacy_id/revision 严格整数字面量、title/blocks(每块 text)/tags(每元素)/
  folder/state 类型、pinned 布尔；manifest entry——note_id/legacy_id 为字符串、
  revision/seq/legacy_id 整数或**历史合法十进制字符串**（布尔/含杂字符如
  "2oops" 拒绝）、tags 数组且元素字符串、folder/state 字符串、pinned 布尔、
  file 路径无分隔符/穿越；**entry 与实体 note_id/legacy_id 双向一致**，不一致
  不导入错映射。任一违反 → ROLLBACK + 显式 upgrade_error，不标完成，修正后
  可重试；manifest-only 权威元数据与旧实体正文继续保留。
- 元数据权威与旧 load_doc 一致：实体提供 title/body(blocks→换行)/color/时间戳；
  manifest entry 覆盖 tags/pinned/state/folder/revision/seq/legacy_id。trashed
  行不进活动列表。升级错误经 `/api/v1/status` 的 `upgrade_error` 显式可见。
- receipts → requests：只导入 committed；kind 按 rev 规则恢复；intent 留空。

## 迁移（notes.json 数组，SD-04/SD-15，**(r8) 完成标记边界**）

- 门禁内逐项校验；进 `corrupted`（index/reason/snippet）且后续合法项继续：
  null；缺 id；id 非严格整数字面量；源内重复 id；title 非 string；body 存在但
  非 string（缺省容忍 ""）；tags 非数组或元素含非字符串；folder 非 string；
  pinned 非 boolean。snippet 恒 JSON 字符串（>400 省略内容）。
- 非法 JSON 顶层：最短有效跨度打捞器（字符索引 + 字节偏移同步，Unicode 安全）。
- 报告与 meta 先于 COMMIT；报告写失败 → ROLLBACK 可重试；重跑 skipped_existing
  幂等；原件只读 + backup。
- **(r8) `migrated`/`corrupted_r1` 完成标记写失败 → ROLLBACK + saved=false
  显式失败**——saved=true 而标记缺失会让重跑失去幂等判据重复迁移。

## UI/legacy 契约（SD-05/SD-10/SD-14/SD-19/SD-20/SD-25/SD-26/SD-27）

- Note 视图携带 revision；`PUT /api/notes/:id` 条件更新 → bool；
  `PUT|GET /api/notes/:id/result` 返回结构化 RepoResult。
- **(r8) JSON public face 严格读取（T-34）**：布尔一律与 `true` 比较、JSON 根
  经 `json.parse` 的 null sentinel 校验——兼容 AutoLang v0.6 候选的严格 JSON
  ABI，不扩大公开 API。
- 草稿会话意图：rid 于保存点分配并立即绑定意图快照（BindIntent）；保存与
  全部自动 flush 使用一致的意图轮换与服务器裁决。
- **未确认提交链**（容量 2）：轮换时旧意图快照移入 prev2（不丢失仍可能已
  落地的祖先）；裁决按链逐个与服务器当前版本对比——匹配任一链节 ⇒ 该提交
  已落地，采用服务器 revision 重试当前草稿（保留新内容）；均不匹配（真实
  外部修改）⇒ 双方版本保留。传输层未知结果不裁决（快照已记，下次保存裁决）。
  链上下文（pend/prev/prev2）随恢复槽 stash/restore 完整搬运。
- **稳定动作目标**：点击导航在 flush 前捕获目标笔记 id，成功刷新/重排后按 id
  重新定位（找不到回落首可见行）；**(r8) 重定位结果不得被点击时的旧下标覆盖
  ——只有未发生刷新重载时旧下标才合法；LoadDraft 带下标上界兜底钳位，越界
  不解引用**；保存成功分支刷新 notes 再 LoadDraft ⇒ 草稿 revision 与服务器
  一致，连续保存不被自身旧 revision 拒绝。pin/tag/delete 绑定当前草稿身份
  （draft_id，pin 目标在 flush 前捕获）——目标不在当前筛选工作集时动作仍指向
  草稿身份，绝不作用到其他可见行。
- **恢复槽双槽（容量 2，无驱逐）**：全入口容量保全——Stash 入空闲槽；两槽
  全满 → 显式阻止（stash_blocked 可见状态 + 编辑器横幅），**被阻止动作的
  查询词/筛选/选择/工作集与草稿全部原位不变**，不做任何后续副作用；导航
  handler 保持原位不清 dirty。Recover 双入口对称检查。用户 Dismiss 释放后
  继续。
- Discard = 显式选择服务器版本：先刷新工作集再按 draft_id 装载最新版。
- 只有 durable 成功后才清 dirty/切草稿/显示 Saved；`.notes` 刷新仅在成功
  分支（VM 渲染序约束）。
- **(r8) 动作失败接收**：删除/置顶/标签/恢复的存储拒绝（非 revision 冲突）
  置 conflict+action_error，不刷新工作集/不清草稿；编辑器显示
  "Action failed: change not saved"（独立于 dirty 的冲突分支）。
- 自动 request_id 使用专用 req_seq 计数器。

## 标识与测试入口（SD-06/SD-28）

- request_id 校验：非空、≤100 字符、仅 `[A-Za-z0-9._:-]` → 否则 invalid_request。
- 变更型测试端点默认关闭（test-mode-disabled）；电池在门禁未开启时立即退出 1。
- **验证注入可靠性**：fixture/setup 类注入走独立脚本（写入后读回校验，
  失败非零），battery 调用点失败即 fail；注入故障自检钩子（INJECT_CONTROL）
  验证传播路径。**(r8) 合成 SQL trigger 的挂载/摘除同样 `|| fail`（S20/S21）。**

## 端点面

- legacy：GET/POST `/api/notes`、GET/PUT/DELETE `/api/notes/:id`、
  PUT/GET `/api/notes/:id/result`、PATCH `:id/pin`、PUT `:id/tags`、
  GET `/api/notes/search`、GET `/api/request-id`。
  **(r8) 写入端点在存储拒绝时返回非成功形状**（pin/tags 的 `?Note` None →
  404 空体；DELETE → `false`；v1 信封 → `ok:false`+err_code）。
- v1：`/api/v1/notes[...]`、`/api/v1/migrate`、`/api/v1/status`（含 upgrade_error）、
  `/api/v1/test/{setup,fault}`（门禁内）。
- 错误码：not_found | revision_conflict | request_conflict | upgrade_conflict |
  upgrade_incomplete | storage_unwritable | second_writer | invalid_request |
  fault_injected | test-mode-disabled。
- SQL 字面量一律 `sql_str()`；动态错误消息在 .at 层拼接后内插；`db.exec`
  成功判定 `< 0`；字符串与引号字符比较用 `"\""` 转义形式（单引号字面量在
  比较上下文被发射为 char——实证）。

## 回归资产（r8）

- 电池 S0–S21（S20 元数据/删除/恢复失败传播+控制；S21 fresh finalize 回滚+
  控制；S15/S16/S17/S18/S19 既有；注入 INJECT_CONTROL 非零自检）+ 挂载/摘除
  `|| fail`。
- 后端 scratch 49 断言（U11 元数据失败传播 9、U12 升级 finalize 回滚 2、
  原 U1–U10/R1–R3/M1）。
- 独立反例资产：r6-recheck independent-api（5 断言）+ independent-ui（4 场景）
  + r7-work VM 驱动（11 断言）+ 复审原输入复跑（api-extra 4/4、navigation
  pass）——全部 exit 0。
- Vue：smoke + negatives-r4 + negatives-r5 + **negatives-r8（R8-1 导航身份/
  revision/连续保存；R8-2 存储拒绝 UI 接收）= 26 项**。VM：015-notes.autotest
  （19 场景）+ r5 负例（13 项）+ r7 负例（11 断言）。
- 测试基建：wait_ready 要求 draft_title 非空；驱动点击用"点击至状态生效"
  重试（重渲染 vnode 换代）；VM 驱动 boot 等待 ≥600s（taskkill 后共享 target
  冷重编窗口）。
- 依赖固定（本轮工具链）：AutoDown c39ac7f；CLI auto 0.1.0+v0.5.0-352-
  ge849e06f9-dirty（SHA256 见复审 baseline）；AutoLang 构建输入 c171c1a。

## 已登记债务

- D-742-1：`use api: Note` 跨模块解析 'undefined'——映射留在 api.at 绕开。
- 时间戳恒空串（无时钟原语），排序/版本用 seq/revision。
- 恢复槽容量 2：满槽显式阻止 + 用户释放；更大容量/持久化恢复集合留待后续。
- 未知意图链容量 2（pend+prev+prev2）：连续 3 次以上未知响应的场景退化为
  冲突保全（双方版本可读，需 Discard/手动处理）；更长链留待后续需求。
- VM 渲染序：flush 冲突路径禁止紧跟 `.notes` 整表赋值（实证破坏列表渲染）；
  MCP 点击在重渲染后可能落在旧 vnode（驱动用重试规避）——框架层根因留
  AutoLang 侧排查。
- **(r8) `auto run` 不把调用方 env 传入其后端子进程**（dev 后端落到自有临时
  数据目录）——门禁一律用直接 exe + env 或门禁驱动（run_vue_suite 等）；
  框架行为留 AutoLang 侧排查。
```

## 发布核对清单（merge 执行）

1. 【提案全文】替换 canonical，git blob/hash 记入合入收据。
2. 刷新 docs/README 计划索引（001 → archived）。
3. 计数核对：以计划 frontmatter 为准（35/35），归档副本一致。
4. merge-owned 其余关闭门按计划 §8 执行。
