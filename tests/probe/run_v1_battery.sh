#!/usr/bin/env bash
# NOTES-001 v1 采证电池（r3 SQLite 版）
#
# 前置：
#   1. 后端已就绪（auto run 或 cargo run），BASE 默认 http://localhost:17819；
#   2. 服务器以 NOTES_TEST_MODE=1 启动（电池依赖 /api/v1/test/setup 隔离目录；
#      未开启时电池立即退出 1——这本身是 T-10 门禁的负例）；
#   3. 同一实例 NOTES_SEED 必须未设：seed 模式会对每个 setup 的新目录注入
#      6 条种子（T-03 设计行为），migrate 将全部 skipped_existing（F-R3-1）。
#      且单进程 env 全局——电池/冒烟/场景不要混跑同一实例（复审实证污染）。
# 用法：bash tests/probe/run_v1_battery.sh [OUTDIR]
#   OUTDIR 缺省为 mktemp 隔离目录（修复复审指出的「写死 wk/OUTDIR 不隔离」）。
# 退出码：任一断言失败 → 1（修复「失败被 tee 掩盖」）；全部通过 → 0。
set -u
export PYTHONUTF8=1
BASE=${BASE:-http://localhost:17819}
OUT=${1:-$(mktemp -d "${TMPDIR:-/tmp}/notes-battery-XXXXXX")}
FIX="tests/fixtures/inbox/legacy-v0"
mkdir -p "$OUT"
SUM="$OUT/summary.txt"
: > "$SUM"
: > "$OUT/.fails"
FAILS=0

log() { echo "$1" | tee -a "$SUM"; }
fail() { echo "$1" >> "$OUT/.fails"; echo "FAIL: $1" | tee -a "$SUM"; }
jq_get() { python -c "import json,sys;d=json.load(open(sys.argv[1]));print(eval(sys.argv[2]))" "$1" "$2" 2>/dev/null; }

# 断言运行器：python 代码从第 2 参读入，失败计入 FAILS（不再被 tee 掩盖）
assert_py() { # assert_py <name> <py-code>
  local name="$1" code="$2" rc
  OUT="$OUT" python -c "
import json, os, sys
OUT = os.environ['OUT']
$code
"
  rc=$?
  if [ $rc -ne 0 ]; then
    # 失败记录落文件（assert_py 常在 pipeline 子壳里跑，子壳内变量
    # 自增会丢——这正是复审指出的「tee 掩盖失败」，故用文件计数）
    fail "$name"
  fi
  return 0
}

setup() { # setup <data_dir> <legacy_file>
  curl -s -m 10 -X POST "$BASE/api/v1/test/setup" \
    -H "Content-Type: application/json" \
    -d "{\"data_dir\":\"$1\",\"legacy_file\":\"$2\"}"
}

work="$OUT/wk"
work_win=$(python -c "import os,sys;print(os.path.abspath(sys.argv[1]).replace(chr(92),'/'))" "$work")
rm -rf "$work"
mkdir -p "$work"
payload() { python -c "import sys;open(sys.argv[1],'wb').write(sys.stdin.buffer.read())" "$1"; }

log "== NOTES-001 r3 battery $(date -Iseconds) base=$BASE out=$OUT"

# ── 门禁探测（T-10）：未开 NOTES_TEST_MODE 时 setup 必须被拒 ──────────────
gate_probe=$(setup "$work_win/probe/data" "$work_win/probe/notes.json")
if [ "$gate_probe" = '"test-mode-disabled"' ]; then
  log "GATE: NOTES_TEST_MODE 未开启——电池需要显式隔离模式（NOTES_TEST_MODE=1 启动后端）。"
  exit 1
fi
log "[GATE] test mode active: $gate_probe"

# ── S0: request_id 校验负例（T-10/SD-06）─────────────────────────────────
D0="$work/t10-rid"; D0W="$work_win/t10-rid"; mkdir -p "$D0/data"
setup "$D0W/data" "$D0W/nope.json" > /dev/null
payload "$work/p-rid.json" <<'JSONEOF'
{"request_id":"../escaped","title":"rid-traversal","body":"x","folder":""}
JSONEOF
curl -s -m 10 -X POST "$BASE/api/v1/notes" -H "Content-Type: application/json" --data-binary @"$work/p-rid.json" -o "$OUT/s0-traversal.json"
payload "$work/p-rid2.json" <<'JSONEOF'
{"request_id":"bad\"quote","title":"rid-quote","body":"x","folder":""}
JSONEOF
curl -s -m 10 -X POST "$BASE/api/v1/notes" -H "Content-Type: application/json" --data-binary @"$work/p-rid2.json" -o "$OUT/s0-quote.json"
assert_py "S0 traversal/quote request_id rejected" "
trav=json.load(open(OUT+'/s0-traversal.json'))
quot=json.load(open(OUT+'/s0-quote.json'))
assert trav['ok']==False and trav['err_code']=='invalid_request', trav
assert quot['ok']==False and quot['err_code']=='invalid_request', quot
print('[S0] traversal/quote request_id -> invalid_request ✓')
" | tee -a "$SUM"

# ── T-01 场景 1：合法旧档迁移 + 幂等 ─────────────────────────
D1="$work/t01-valid"; D1W="$work_win/t01-valid"; mkdir -p "$D1/data"
cp "$FIX/notes-valid.json" "$D1/notes.json"
log "[S1 valid] setup: $(setup "$D1W/data" "$D1W/notes.json")"
curl -s -m 15 -X POST "$BASE/api/v1/migrate" -o "$OUT/s1-migrate.json"
assert_py "S1 valid migrate" "
d=json.load(open(OUT+'/s1-migrate.json'))
assert d['migrated']==3 and len(d['corrupted'])==0 and d['saved'], d
print('[S1] 3 migrated, 0 corrupted, saved ✓')
" | tee -a "$SUM"
curl -s -m 10 -X POST "$BASE/api/v1/migrate" -o "$OUT/s1-migrate-again.json"
assert_py "S1 repeat migrate skipped" "
d=json.load(open(OUT+'/s1-migrate-again.json'))
assert d['skipped_existing'], d
print('[S1] repeat migrate → skipped_existing ✓')
" | tee -a "$SUM"

# ── T-01 场景 2：损坏档打捞 + 报告 + 原件不动 ─────────────────
D2="$work/t01-corrupt"; D2W="$work_win/t01-corrupt"; mkdir -p "$D2/data"
cp "$FIX/notes-corrupt.json" "$D2/notes.json"
before=$(md5sum "$D2/notes.json" | cut -d' ' -f1)
setup "$D2W/data" "$D2W/notes.json" > /dev/null
curl -s -m 15 -X POST "$BASE/api/v1/migrate" -o "$OUT/s2-migrate.json"
assert_py "S2 corrupt salvage" "
d=json.load(open(OUT+'/s2-migrate.json'))
assert d['migrated']==2, d
assert len(d['corrupted'])==1, d
print('[S2] migrated=%s corrupted=%s backup=%s ✓' % (d['migrated'], len(d['corrupted']), d['backup_file']))
" | tee -a "$SUM"
after=$(md5sum "$D2/notes.json" | cut -d' ' -f1)
if [ "$before" != "$after" ]; then fail "S2 original file was modified!"; else log "[S2] original untouched ✓"; fi
ls "$D2/data/corrupted/" > "$OUT/s2-report-files.txt" 2>&1
if grep -q "report-r1.json" "$OUT/s2-report-files.txt"; then
  log "[S2] corrupted report persisted ✓"
else
  fail "S2 corrupted/report-r1.json missing"
fi

# ── T-01 场景 3：坏类型条目拒绝/标注 + 报告落盘 ───────────────
D3="$work/t01-badtypes"; D3W="$work_win/t01-badtypes"; mkdir -p "$D3/data"
cp "$FIX/notes-bad-types.json" "$D3/notes.json"
setup "$D3W/data" "$D3W/notes.json" > /dev/null
curl -s -m 15 -X POST "$BASE/api/v1/migrate" -o "$OUT/s3-migrate.json"
assert_py "S3 bad-types reported" "
d=json.load(open(OUT+'/s3-migrate.json'))
assert len(d['corrupted'])>=1, d
assert all(('index' in c and 'reason' in c and 'snippet' in c) for c in d['corrupted']), d
for c in d['corrupted']:
    print('[S3] corrupted[%s] %s' % (c['index'], c['reason']))
print('[S3] bad-type entries reported with index/reason/snippet ✓')
" | tee -a "$SUM"
if [ -f "$D3/data/corrupted/report-r1.json" ]; then
  cp "$D3/data/corrupted/report-r1.json" "$OUT/s3-report.json"
  log "[S3] report-r1.json persisted ✓"
else
  fail "S3 report file missing"
fi

# ── T-01 场景 4：空数组 + AC-05 全新目录无种子 ────────────────
D4="$work/t01-empty"; D4W="$work_win/t01-empty"; mkdir -p "$D4/data"
cp "$FIX/notes-empty.json" "$D4/notes.json"
setup "$D4W/data" "$D4W/notes.json" > /dev/null
curl -s -m 10 -X POST "$BASE/api/v1/migrate" -o "$OUT/s4-migrate.json"
curl -s -m 10 "$BASE/api/v1/notes" -o "$OUT/s4-list.json"
assert_py "S4 empty legacy" "
m=json.load(open(OUT+'/s4-migrate.json'))
l=json.load(open(OUT+'/s4-list.json'))
assert m['migrated']==0 and l==[], (m,l)
print('[S4] empty legacy → 0 notes ✓')
" | tee -a "$SUM"

D5="$work/t01-fresh"; D5W="$work_win/t01-fresh"; mkdir -p "$D5/data"
setup "$D5W/data" "$D5W/nope.json" > /dev/null
curl -s -m 10 "$BASE/api/v1/notes" -o "$OUT/s5-list.json"
assert_py "S5 fresh dir no seed" "
l=json.load(open(OUT+'/s5-list.json'))
assert l==[], l
print('[S5] fresh dir → empty store, no demo seed ✓ (AC-05)')
" | tee -a "$SUM"

# ── T-02 场景 6：幂等创建（request_id 重放，含中文/emoji/多行）──
D6="$work/t02-idem"; D6W="$work_win/t02-idem"; mkdir -p "$D6/data"
setup "$D6W/data" "$D6W/nope.json" > /dev/null
payload "$work/p1.json" <<'JSONEOF'
{"request_id":"req-create-001","title":"中文标题 🎉","body":"第一行\n第二行","folder":"work"}
JSONEOF
curl -s -m 10 -X POST "$BASE/api/v1/notes" -H "Content-Type: application/json" --data-binary @"$work/p1.json" -o "$OUT/s6-create1.json"
payload "$work/p2.json" <<'JSONEOF'
{"request_id":"req-create-001","title":"中文标题 🎉","body":"第一行\n第二行","folder":"work"}
JSONEOF
curl -s -m 10 -X POST "$BASE/api/v1/notes" -H "Content-Type: application/json" --data-binary @"$work/p2.json" -o "$OUT/s6-create2.json"
assert_py "S6 idempotent create" "
a=json.load(open(OUT+'/s6-create1.json'))
b=json.load(open(OUT+'/s6-create2.json'))
assert a['ok'] and b['ok'], (a,b)
assert a['doc']['note_id']==b['doc']['note_id'], (a['doc']['note_id'], b['doc']['note_id'])
assert a['receipt']['status']=='committed'
assert b['receipt']['request_id']=='req-create-001'
print('[S6] idempotent create: same note_id=%s ✓ (AC-02)' % a['doc']['note_id'])
" | tee -a "$SUM"
nid=$(jq_get "$OUT/s6-create1.json" "d['doc']['note_id']")
rev=$(jq_get "$OUT/s6-create1.json" "d['doc']['revision']")

# ── T-02 场景 7：条件更新 + revision 冲突（AC-04）────────────
payload "$work/p7a.json" <<JSONEOF
{"expected_revision":$rev,"title":"更新后","body":"新正文","request_id":"req-upd-001"}
JSONEOF
curl -s -m 10 -X PUT "$BASE/api/v1/notes/$nid" -H "Content-Type: application/json" --data-binary "@$work/p7a.json" -o "$OUT/s7-update-ok.json"
payload "$work/p7b.json" <<JSONEOF
{"expected_revision":$rev,"title":"旧版本写入","body":"应被拒绝","request_id":"req-upd-bad"}
JSONEOF
curl -s -m 10 -X PUT "$BASE/api/v1/notes/$nid" -H "Content-Type: application/json" --data-binary "@$work/p7b.json" -o "$OUT/s7-update-conflict.json"
curl -s -m 10 "$BASE/api/v1/notes/$nid" -o "$OUT/s7-after.json"
assert_py "S7 revision conflict" "
ok=json.load(open(OUT+'/s7-update-ok.json'))
cf=json.load(open(OUT+'/s7-update-conflict.json'))
after=json.load(open(OUT+'/s7-after.json'))
assert ok['ok'] and ok['doc']['revision']==$rev+1, ok
assert cf['ok']==False and cf['err_code']=='revision_conflict', cf
assert after['doc']['title']=='更新后', after
print('[S7] stale revision rejected; user content intact ✓ (AC-04)')
" | tee -a "$SUM"

# ── T-02 场景 7b：8 并发同 revision 更新恰好 1 成功（AC-01/04）─
cur_rev=$((rev+1))
for i in 1 2 3 4 5 6 7 8; do
  payload "$work/p7c-$i.json" <<JSONEOF
{"expected_revision":$cur_rev,"title":"并发-$i","body":"并发写入 $i","request_id":"req-conc-$i"}
JSONEOF
done
for i in 1 2 3 4 5 6 7 8; do
  curl -s -m 20 -X PUT "$BASE/api/v1/notes/$nid" -H "Content-Type: application/json" --data-binary "@$work/p7c-$i.json" -o "$OUT/s7c-$i.json" &
done
wait
assert_py "S7b 8-way concurrent same-revision -> exactly 1 success" "
oks=0; conflicts=0
for i in range(1,9):
    d=json.load(open(OUT+'/s7c-%d.json'%i))
    if d.get('ok'): oks+=1
    elif d.get('err_code')=='revision_conflict': conflicts+=1
    else: raise AssertionError(('unexpected', i, d))
assert oks==1 and conflicts==7, (oks, conflicts)
print('[S7b] concurrent 8 -> ok=%d conflict=%d ✓ (AC-01/04)' % (oks, conflicts))
" | tee -a "$SUM"

# ── T-02 场景 8：软删/恢复（AC-05）───────────────────────────
curl -s -m 10 -X DELETE "$BASE/api/v1/notes/$nid" -o "$OUT/s8-trash.json"
curl -s -m 10 "$BASE/api/v1/notes" -o "$OUT/s8-list.json"
curl -s -m 10 "$BASE/api/v1/notes/$nid" -o "$OUT/s8-get.json"
curl -s -m 10 -X POST "$BASE/api/v1/notes/$nid/restore" -o "$OUT/s8-restore.json"
curl -s -m 10 "$BASE/api/v1/notes" -o "$OUT/s8-list2.json"
assert_py "S8 trash/restore" "
t=json.load(open(OUT+'/s8-trash.json'))
l=json.load(open(OUT+'/s8-list.json'))
g=json.load(open(OUT+'/s8-get.json'))
r=json.load(open(OUT+'/s8-restore.json'))
l2=json.load(open(OUT+'/s8-list2.json'))
assert t['ok'] and g['doc']['state']=='trashed', (t,g)
assert all(x['note_id']!='$nid' for x in l), l
assert r['ok'] and any(x['note_id']=='$nid' for x in l2), (r,l2)
print('[S8] trash→hidden→restore ✓ (AC-05)')
" | tee -a "$SUM"

# ── T-02 场景 9：故障注入（AC-02）────────────────────────────
D9="$work/t02-fault"; D9W="$work_win/t02-fault"; mkdir -p "$D9/data"
setup "$D9W/data" "$D9W/nope.json" > /dev/null
curl -s -m 10 -X POST "$BASE/api/v1/test/fault" -H "Content-Type: application/json" -d '{"stage":"after_entity"}' -o /dev/null
payload "$work/p3.json" <<'JSONEOF'
{"request_id":"req-fault-1","title":"中断的提交","body":"body","folder":""}
JSONEOF
curl -s -m 10 -X POST "$BASE/api/v1/notes" -H "Content-Type: application/json" --data-binary @"$work/p3.json" -o "$OUT/s9-fault-create.json"
curl -s -m 10 "$BASE/api/v1/notes" -o "$OUT/s9-list.json"
curl -s -m 10 -X POST "$BASE/api/v1/test/fault" -H "Content-Type: application/json" -d '{"stage":"after_manifest"}' -o /dev/null
payload "$work/p4.json" <<'JSONEOF'
{"request_id":"req-fault-2","title":"manifest后中断","body":"body","folder":""}
JSONEOF
curl -s -m 10 -X POST "$BASE/api/v1/notes" -H "Content-Type: application/json" --data-binary @"$work/p4.json" -o "$OUT/s9-fault-create2.json"
curl -s -m 10 -X POST "$BASE/api/v1/test/fault" -H "Content-Type: application/json" -d '{"stage":"off"}' -o /dev/null
payload "$work/p5.json" <<'JSONEOF'
{"request_id":"req-fault-1","title":"重试成功","body":"body","folder":""}
JSONEOF
curl -s -m 10 -X POST "$BASE/api/v1/notes" -H "Content-Type: application/json" --data-binary @"$work/p5.json" -o "$OUT/s9-retry.json"
assert_py "S9 fault no phantom receipt" "
f1=json.load(open(OUT+'/s9-fault-create.json'))
l=json.load(open(OUT+'/s9-list.json'))
f2=json.load(open(OUT+'/s9-fault-create2.json'))
rt=json.load(open(OUT+'/s9-retry.json'))
assert f1['ok']==False and f1['err_code']=='fault_injected', f1
assert l==[], l
assert f2['ok']==False and f2['err_code']=='fault_injected', f2
assert rt['ok'] and rt['receipt']['status']=='committed', rt
print('[S9] fault leaves no success receipt; retry lands cleanly ✓ (AC-02)')
" | tee -a "$SUM"

# ── T-16 场景 S11：update 故障注入（F-R4-03：update 也消费 NOTES_FAULT）──
D11="$work/t14-ufault"; D11W="$work_win/t14-ufault"; mkdir -p "$D11/data"
setup "$D11W/data" "$D11W/nope.json" > /dev/null
payload "$work/p11c.json" <<'JSONEOF'
{"request_id":"uf-c1","title":"故障前的更新","body":"v1","folder":""}
JSONEOF
curl -s -m 10 -X POST "$BASE/api/v1/notes" -H "Content-Type: application/json" --data-binary @"$work/p11c.json" -o "$OUT/s11-create.json"
nid11=$(jq_get "$OUT/s11-create.json" "d['doc']['note_id']")
rev11=$(jq_get "$OUT/s11-create.json" "d['doc']['revision']")
curl -s -m 10 -X POST "$BASE/api/v1/test/fault" -H "Content-Type: application/json" -d '{"stage":"after_entity"}' -o /dev/null
payload "$work/p11u.json" <<JSONEOF
{"expected_revision":$rev11,"title":"update故障","body":"x","request_id":"uf-u1"}
JSONEOF
curl -s -m 10 -X PUT "$BASE/api/v1/notes/$nid11" -H "Content-Type: application/json" --data-binary "@$work/p11u.json" -o "$OUT/s11-ufault.json"
curl -s -m 10 -X POST "$BASE/api/v1/test/fault" -H "Content-Type: application/json" -d '{"stage":"off"}' -o /dev/null
curl -s -m 10 "$BASE/api/v1/notes/$nid11" -o "$OUT/s11-after.json"
payload "$work/p11r.json" <<JSONEOF
{"expected_revision":$rev11,"title":"update故障","body":"x","request_id":"uf-u1"}
JSONEOF
curl -s -m 10 -X PUT "$BASE/api/v1/notes/$nid11" -H "Content-Type: application/json" --data-binary "@$work/p11r.json" -o "$OUT/s11-retry.json"
assert_py "S11 update fault rollback + retry" "
f=json.load(open(OUT+'/s11-ufault.json'))
assert f['ok']==False and f['err_code']=='fault_injected', f
after=json.load(open(OUT+'/s11-after.json'))
assert after['doc']['title']=='故障前的更新' and after['doc']['revision']==$rev11, after
rt=json.load(open(OUT+'/s11-retry.json'))
assert rt['ok'] and rt['doc']['revision']==$rev11+1, rt
print('[S11] update fault: rollback无痕 + 同rid重试落地 ✓')
" | tee -a "$SUM"

# ── T-16 场景 S12/S13：同 rid 跨目标拒绝 + 原收据不漂移（SD-09）─────────────
D13="$work/t14-rid"; D13W="$work_win/t14-rid"; mkdir -p "$D13/data"
setup "$D13W/data" "$D13W/nope.json" > /dev/null
payload "$work/p13a.json" <<'JSONEOF'
{"request_id":"rid-A","title":"A-doc","body":"a","folder":""}
JSONEOF
curl -s -m 10 -X POST "$BASE/api/v1/notes" -H "Content-Type: application/json" --data-binary @"$work/p13a.json" -o "$OUT/s13-a.json"
nidA=$(jq_get "$OUT/s13-a.json" "d['doc']['note_id']")
revA=$(jq_get "$OUT/s13-a.json" "d['doc']['revision']")
payload "$work/p13x.json" <<'JSONEOF'
{"expected_revision":1,"title":"impersonate-A","body":"x","request_id":"rid-A"}
JSONEOF
curl -s -m 10 -X PUT "$BASE/api/v1/notes/n-2" -H "Content-Type: application/json" --data-binary "@$work/p13x.json" -o "$OUT/s12-cross.json"
# 先确保存在第二个目标（无则建）
curl -s -m 10 -X POST "$BASE/api/v1/notes" -H "Content-Type: application/json" --data-binary '{"request_id":"rid-B","title":"B-doc","body":"b","folder":""}' -o /dev/null
curl -s -m 10 -X PUT "$BASE/api/v1/notes/n-2" -H "Content-Type: application/json" --data-binary "@$work/p13x.json" -o "$OUT/s12-cross.json"
# update-1 / update-2 / 原样重放 update-1 → 原收据
payload "$work/p13u1.json" <<JSONEOF
{"expected_revision":$revA,"title":"A-upd1","body":"u1","request_id":"rid-u1"}
JSONEOF
curl -s -m 10 -X PUT "$BASE/api/v1/notes/$nidA" -H "Content-Type: application/json" --data-binary "@$work/p13u1.json" -o "$OUT/s13-u1.json"
revA1=$(jq_get "$OUT/s13-u1.json" "d['doc']['revision']")
payload "$work/p13u2.json" <<JSONEOF
{"expected_revision":$revA1,"title":"A-upd2","body":"u2","request_id":"rid-u2"}
JSONEOF
curl -s -m 10 -X PUT "$BASE/api/v1/notes/$nidA" -H "Content-Type: application/json" --data-binary "@$work/p13u2.json" -o "$OUT/s13-u2.json"
payload "$work/p13r.json" <<JSONEOF
{"expected_revision":$revA,"title":"A-upd1","body":"u1","request_id":"rid-u1"}
JSONEOF
curl -s -m 10 -X PUT "$BASE/api/v1/notes/$nidA" -H "Content-Type: application/json" --data-binary "@$work/p13r.json" -o "$OUT/s13-replay.json"
assert_py "S12/S13 cross-target conflict + original receipt" "
x=json.load(open(OUT+'/s12-cross.json'))
assert x['ok']==False and x['err_code']=='request_conflict', x
u1=json.load(open(OUT+'/s13-u1.json'))
u2=json.load(open(OUT+'/s13-u2.json'))
rp=json.load(open(OUT+'/s13-replay.json'))
assert u1['ok'] and u2['ok'], (u1,u2)
assert rp['ok'] and rp['replayed'], rp
assert rp['receipt']['revision']==u1['receipt']['revision'], (rp['receipt'], u1['receipt'])
assert rp['receipt']['revision']!=u2['receipt']['revision'], 'receipt drifted to latest'
print('[S12] same rid cross-target -> request_conflict, target unchanged ✓')
print('[S13] replay update-1 keeps original receipt rev=%s (latest is %s) ✓' % (rp['receipt']['revision'], u2['receipt']['revision']))
" | tee -a "$SUM"

# ── T-16 场景 S14：null 项报告（F-R4-02）──────────────────────────────────
D14="$work/t13-null"; D14W="$work_win/t13-null"; mkdir -p "$D14/data"
python - "$D14/notes-null.json" <<'PYEOF'
import json, sys
items = [
    {"id": 0, "title": "valid-0", "body": "ok", "folder": "", "pinned": False, "tags": []},
    None,
    {"id": 2, "title": "valid-2", "body": "ok", "folder": "", "pinned": False, "tags": []},
]
open(sys.argv[1], 'wb').write(json.dumps(items, ensure_ascii=False).encode('utf-8'))
PYEOF
setup "$D14W/data" "$D14W/notes-null.json" > /dev/null
curl -s -m 15 -X POST "$BASE/api/v1/migrate" -o "$OUT/s14-migrate.json"
assert_py "S14 null reported + later item salvaged" "
d=json.load(open(OUT+'/s14-migrate.json'))
assert d['migrated']==2, d
assert len(d['corrupted'])==1 and d['corrupted'][0]['reason']=='null entry', d
print('[S14] [valid,null,valid] -> migrated=2, corrupted=1(null entry) ✓')
" | tee -a "$SUM"

# ── S10：真重启恢复（外部驱动）：kill 后端 → 重启（NOTES_TEST_MODE=1）
# → setup 同目录 → GET /api/v1/notes；证据由执行记录留存。
log "[S10 crash] 外部驱动：kill 后端 → 重启（NOTES_TEST_MODE=1）→ setup 同目录 → GET /api/v1/notes"

FAILS=$(wc -l < "$OUT/.fails" | tr -d ' ')
log "== battery done; fails=$FAILS; artifacts in $OUT"
if [ "$FAILS" -gt 0 ]; then
  echo "BATTERY FAILED: $FAILS assertion(s)" | tee -a "$SUM"
  exit 1
fi
echo "BATTERY PASSED" | tee -a "$SUM"
exit 0
