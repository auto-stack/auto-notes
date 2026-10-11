# NOTES-001 r6 / Phase 5 规范增量（提案，未发布）

目标均为 `docs/specs/notes/durable-inbox.md`（当前r3，blob8f05b8dd…）。
基于冻结r5实施稿纠正SD-07–16；保留AC-01–05原文/阈值。

| delta | operation | before → required after | task / AC |
|---|---|---|---|
| SD-17 | modify | 任意 upgrade_error 可授予修复合并、残留重复重导 → 冲突与可修复凭据分离；匹配来源/目标才导入，不覆盖后续确认修订；成功修复可证明只执行一次 | T-22，AC-01/03/04 |
| SD-18 | modify | 实体仅JSON语法校验 → manifest/实体结构、身份、字段类型及路径校验；非法形状显式失败回滚且修正可重试 | T-23，AC-01/03 |
| SD-19 | modify | 双槽满时覆盖B → Stash/Recover/Recover2及所有入口不静默驱逐；容量不足显式阻止，或用户明确选择释放后再继续 | T-24，AC-04/05 |
| SD-20 | modify | Save专用裁决、入槽丢失快照 → 每个保存/自动flush/恢复路径共享意图身份和结果裁决，槽携带未确认上下文，原样重试和改内容重试均可判定 | T-25，AC-02/04 |
| SD-21 | modify（待决策） | 旧行一律拒绝后自称未改变AC → 明确JSON收据/v1三列/v2快照/新协议兼容表；无法保留原承诺时以具体diff取得用户裁决后更新规范，不恢复通配或伪收据 | T-26，AC-02 |
| SD-22 | modify | 9/22宣告全部work完成、矛盾Spec提案 → 原任务按AC证据逐一闭合、失败任务重开、计数真实；work备一致实现稿，review再验，merge才发布canonical | T-27，全部AC |

这些规则是待修复的验收目标，不宣称当前已实现。修复work须准备实际Spec全文/差异，
独立review绑定新提交与该稿；规范发布仍由merge执行。
