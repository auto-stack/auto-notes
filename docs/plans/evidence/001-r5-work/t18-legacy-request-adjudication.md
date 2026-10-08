# T-18 决策制品：旧请求信息的有界调查与兼容裁决

计划：NOTES-001 修订5 / Phase 4 / T-18（F-R5-02 / SD-13）。
输入：canonical `docs/specs/notes/durable-inbox.md` r3（blob 8f05b8dd…）；
旧格式样本 `tests/probe/evidence/v1/wedge-snapshot/`（已提交 Phase 1 快照复制件）。

## 1. 有界调查：旧持久层各源可恢复的字段

调查对象为两代旧请求记录 + 旧 journal；以下为逐字段核对结果（非推测）。

### 1a. Phase 1 JSON 布局（manifest/notes/receipts/journal）

| 源 | 字段 | 可恢复性 |
|---|---|---|
| `receipts/<rid>.json` | request_id, note_id, revision, status | 完整（收据本体） |
| `journal/intent-<seq>.json` | seq, request_id, note_id, revision | 完整（意图绑定，无 kind、无内容） |
| `notes/*.json` | note_id, revision, title, blocks→body, tags, … | 当前快照（非历史意图内容） |
| `manifest.json` entries | note_id, revision, file, state, folder, tags, pinned, seq, legacy_id | 权威元数据（revision/seq/legacy_id 为字符串） |

结论：**kind 可精确恢复**（旧协议 create 恒 rev1、update 恒 prev+1 ≥ 2，二者不相交；
journal+receipts 交叉印证目标与原 revision）；**意图内容不可恢复**（journal 不含
title/body，实体只有终态快照，无法重构任意历史请求提交时的字段）。

### 1b. 旧 SQLite 三列 requests（r3 schema v1：request_id, note_id, kind）

kind 与目标可恢复（列即有）；原 revision 不可恢复（无列，ALTER 缺省 0）；
内容不可恢复（无 doc_json）。r3→r4 期间的 v2 行另有 rev/doc_json/intent 列：
rev>0 且 doc_json 在案时，create/update 的意图可从快照**确定性重导**（见 §2）。

## 2. 裁决

1. **新协议意图规范化**（`v2c|` 前缀）：每字段独立 JSON 编码后拼接
   （`canonical_create_intent` / `canonical_update_intent`，repository.at）。
   JSON 字符串字面量边界唯一，固定字段数下拼接串与字段元组一一对应——
   `title="a|b",body="c"` 与 `title="a",body="b|c"` 不再可能同串。
2. **v2 管道行版本化迁移**（schema_v 2→3，`migrate_request_intents`）：
   rev>0 且 doc 快照在案的行按提交语义重导规范意图（create 用文档
   title/body/folder、tags 参数恒 "[]"；update 用 note_id、expected_revision
   =快照 revision−1、title/body）。无法重导的行保持原 intent：与新请求的
   规范串必不相同 → 重放明确 request_conflict（安全默认，绝不假确认）。
3. **旧行（intent 为空：升级导入收据 / v1 三列行）**：一律 request_conflict，
   不通配确认任何新操作、不编造 rev1 收据（`replay_in_txn`）。理由：
   - 旧客户端已不在范围内，新 UI 的每个 rid 都是全新意图；携带旧 rid 的
     请求按定义是"复用"，而意图内容不可验证 ⇒ 不能确认。
   - 原收据仍可查询（read_receipt：note_id/status=committed），旧对象不受
     影响（battery S15 实证：d-2 复用于 create/update 均拒绝、对象原样）。
   - kind/rev 已尽量恢复并入行（升级导入 kind 按 rev 规则、rev 取收据值），
     但仍不足以验证"完全相同意图"，故不放宽。
4. **兼容承诺边界**：AC-02 的"同 request_id 重放返回同一对象"适用于**本协议
   下发出的请求**（rid 绑定完整持久意图）；旧行为"任意字段管道拼接 + 空 kind
   通配 + rev 缺省 1"正是复审确认的缺陷（F-R5-02），不构成被保留的兼容面。
   本裁决不削弱 AC——它把"重放确认"限定在可验证意图上，其余显式拒绝。

## 3. 验证绑定

- battery S15：旧收据 d-2 复用 create/update 均拒绝、对象与原树不变。
- battery S17：管道歧义意图冲突 + 同内容重放；rev 缺失旧行拒绝（不编造
  rev1）；r4 管道行迁移后同意图重放原收据、换内容冲突。
- 后端负例（r5-work/verify_backend_scratch.py）R1/R2/R3 与上述一致。
- 决策影响面：`repository.at` 的 `canonical_*_intent` / `migrate_request_intents`
  / `replay_in_txn` / `upgrade_if_legacy`（receipts 导入段）。
