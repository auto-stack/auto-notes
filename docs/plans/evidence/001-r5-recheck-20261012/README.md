# NOTES-001 修订5 final review（2026-10-12）

结论：**needs_fix**。实现提交 `00e4fa62b686f3f5e5c51167588721ab785232a7`，
交付 HEAD `63dbad638e193b4e42ad6f0127f58484b4b28036`，diff base `ad3b2a4…`。
本上下文未参与本轮实现、曾参与前轮复审；无子agent，结论从源码和新的运行实验重建。
实际路径 `D:/autostack/auto-os/apps/015-notes` / `v0.6-dev`，实现已提交且无脏改动；
既有未跟踪 r4/review 证据和 vm-min.autotest 原样保留。[基线与指纹](baseline.json)。

AutoLang 当前为 `c64b71353e740bf84246de8bd612f692cba04db1`，与 work 的 `578794d…`
不同，因此全部门重新执行；CLI 源仍 a6e108f60，版本/hash及祖先关系已核对。
末检 AutoLang HEAD=`5ea1cf35b85efdad530c262a47f7ef9b864fad51`；与入场 c64b7135 的差异只有三份计划文档，源码/构建配置不变，本轮证据有效。
AutoDown pin=实际 `96f095b…`。重新生成 Vue + app 级离线构建成功；未手改生成 Rust。

## 本轮真实门

| 门 | 实际结果 | 证据 |
|---|---|---|
| fresh Vue gen / backend build | exit 0 / 0（499 既有生成警告） | build-vue.log / build-backend.log |
| battery S0–S18 | exit 0，fails=0 | [原始电池](battery-raw.log) |
| 双进程同 revision 8 写 | 1 成功、7 revision_conflict | [结果](dual-process.json) |
| 后端原负例 | 36/36，exit 0，VM 后最终制品又复验 | scratch.log / scratch-final.log |
| Vue 原套件 | 24/24（2.0m） | [完整日志](vue-suite-raw.log) |
| VM 原套件 | 19/19、suite_exit=0 | vm-suite-raw.log / vm-suite-result.json |
| VM 原负例 | 13/13、fails=[] | vm-negative-result.json / vm-negative.log |
| 独立 API 反例 | 3 个保全断言失败、exit 1；另记录原样旧请求拒绝 | [结果](independent-api.json) |
| 独立 Vue 反例 | 2 个断言失败，Node exit 1 | [结果](independent-ui.json) / independent-ui-raw.log |
| 独立 VM 反例 | 同样 2 个断言失败，exit 1 | [结果](independent-vm.json) / independent-vm-asserted.log |

失败断言是本轮正确拒绝通过的证据。原 run_vue_suite.py/run_vm_suite.py 的包装进程
可能 exit 0，实际 suite_exit/日志也逐项核对；不以包装进程返回值判 pass。
初次独立驱动是观察采证，后已加真实断言重跑；这里保留的是加断言后的结果。

## 发现与纠正要求

| ID / severity | AC / task | 触发与可观察结果 | 修复要求与 Phase 5 |
|---|---|---|---|
| F-R6-01 / P1 | AC-01/03/04，T-17/T-12/T-07 | SQLite n-1 已确认中文正文，与旧树并存且未 upgraded。第一次 list 写 upgrade_error/返回空；第二次 list 把该错误当 need_repair，直接把新正文覆盖成旧 doc1-updated。第三次不再报错 | T-22：冲突错误不能授予合并资格；重复读取/重启仍冲突且双方数据/请求不变 |
| F-R6-02 / P1 | AC-01/04，T-17/T-02/T-07 | r4 legacy-upgrade corrupted_r1 残留触发无条件重导；已确认 rev3 被回退到 rev2。成功后残留不清，修复后再确认保存 rev3，下一次 GET 又回到 rev2 | T-22：修复来源与目标行可证明匹配，保护更高修订/同修订不同内容；成功清理修复凭据或记录完成代际，后续编辑不能再次重导 |
| F-R6-03 / P1 | AC-01/03，T-17/T-12 | 引用实体文件存在且 JSON={}; 仅语法校验，插入 note_id='' 的空文档，upgraded=1，收据仍指向 n-1 | T-23：校验实体/manifest 结构、身份一致、正文/元数据类型及路径；失败回滚、显式可重试，不标完成 |
| F-R6-04 / P1 | AC-04/05，T-19/T-15/T-09 | A/B 两次失败导航已占两槽；编辑 C 后点击第一行 Recover，直接把槽 B 改成 C，B 消失。Vue 和 VM 均 b_preserved=false，没有丢弃确认 | T-24：所有 Stash/Recover/Recover2/导航路径统一检查容量；不能静默覆盖，满槽显式阻止或先由用户选择释放 |
| F-R6-05 / P1 | AC-02/04，T-19/T-15/T-09/T-04 | C1 已 COMMIT 但丢响应（Vue route.abort，VM after_manifest）；继续编辑 C2 后导航。自动 flush 复用 C1 rid 被拒，Stash 清 has_pend/has_prev，只保留 rid。Recover 后 Save 两次仍同 rid/旧 revision，request_conflict，服务器仍 C1 | T-25：所有 flush 使用相同意图轮换/裁决，恢复槽携带完整未确认意图上下文；恢复后保留 C2 并可裁决保存，不能只改 rid |
| F-R6-06 / P2，合同裁决 | AC-02，T-18/T-14 | 原样旧 d-2 请求（expected_revision=1,title=doc1-updated,body=body two）被 request_conflict；决策制品把 AC 限为新协议，但现行合同明确要求兼容承诺改变须用户决策。旧行安全拒绝是合理候选，不等于原承诺已验收 | T-26：以既有有界调查输出逐类兼容表/具体承诺差异；不能证明的请求继续安全拒绝，涉及旧重放承诺变化先明确用户决策，不能凭实现摘要自授豁免 |
| F-R6-07 / P2，关闭缺口 | 全部 AC，T-21/T-16/T-11 | 全部22任务 owner=work，却 execution_done 9/22，13个原任务未闭合；docs索引仍说Phase4待执行；Spec提案同时写“三份显式不动作”和“第三份驱逐B”，且所有flush/dirty描述与实现不符 | T-27：关闭映射到通过证据的原任务，失败项保持未完成；核对唯一当前交接、计数及Spec实际规则，不能把 work 任务关闭推迟到 merge |

F-R6-01/02/04/05 是新修复实现仍违反原保全合同；F-R6-03 是 T-17 原声明的完整校验未实现。
F-R6-06 是已有兼容裁决要求未完成，不要求恢复通配假成功；F-R6-07 为关闭缺口。
对应源码：repository.at:390–422、575–579、638–643、491–496；
notes_store.at:283–327、530–554、577–648。以 baseline 的源hash定位，未来行号可能变动。

## AC 与 Spec delta

| AC | 结果 | 依据 |
|---|---|---|
| AC-01 | fail | 新库正常/故障重启在 battery 通过；混合/修复旧库确认数据可覆盖/回退 |
| AC-02 | partial | 新协议同rid/原收据/fault门通过；继续编辑恢复路径 fail，旧重放兼容待具体裁决 |
| AC-03 | fail | notes.json 严格类型、报告、Unicode/后续合法项通过；旧树非法实体仍空成功 |
| AC-04 | fail | 并发/陈旧拒绝通过；草稿B静默丢失，恢复C2卡死，升级可覆盖已确认内容 |
| AC-05 | pass（基础行为） | 空库无默认seed、CRUD/软删恢复及Vue/VM原套件通过；不覆盖AC04的草稿失败 |

[冻结的 r5 Spec diff](spec-delta-reviewed-r5.md) hash见baseline。
SD-08/15（严格迁移类型）与普通SD-09无歧义编码通过；SD-07/12/14未完全符合代码保全合同，
SD-13旧兼容需裁决，SD-16准备稿的容量/flush规则相互矛盾。**不能发布该稿**。
canonical r3 保持原样，发布/派生索引/归档仍为通过后的 merge-owned 门。

## 复现

从 app 根运行，使用记录的CLI及依赖；先 `auto build -r vue --gen-only`，然后在
rust-workspace 运行 `cargo build -p app-015-notes-back --offline`。

```
python docs/plans/evidence/001-r5-recheck-20261012/independent-api.py
python docs/plans/evidence/001-r5-recheck-20261012/run-independent-ui.py
python docs/plans/evidence/001-r5-recheck-20261012/run-independent-vm.py
```

使用 PYTHONUTF8=1；动态 loopback 端口、净库、私有MCP，清理自身进程；Windows
默认沙箱阻止 loopback，因此本轮经限定本机测试的自动审批运行。API/VM 预期 exit 1，
Vue包装日志的 suite_exit_code=1 为真实子进程失败。持久脚本仅修正证据目录路径，
动作/断言与本轮执行一致。原门命令见 r5-work/README，完整调用/版本在本包日志与baseline。
不接触真实用户库、不声称硬件掉电；未修改实现、canonical、父仓gitlink或推送。

next=work(Phase 5,T-22–T-27)，修复后重新独立 final review。

证据文本归一LF；日志仅去行尾空白/多余末尾空行，诊断/JSON结果未改。原临时日志仍保留。
