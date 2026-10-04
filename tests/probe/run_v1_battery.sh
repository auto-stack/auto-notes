#!/usr/bin/env bash
# NOTES-001 T-01/T-02 采证电池（对运行中的 app 实例执行；前置：auto run，17819 就绪）
# 用法：bash tests/probe/run_v1_battery.sh [OUTDIR]
# 产物：OUTDIR 下每个场景一个 JSON + 摘要 summary.txt
set -u
BASE=${BASE:-http://localhost:17819}
OUT=${1:-tests/probe/evidence/v1}
FIX="tests/fixtures/inbox/legacy-v0"
mkdir -p "$OUT"
SUM="$OUT/summary.txt"
: > "$SUM"

log() { echo "$1" | tee -a "$SUM"; }
jq_get() { python -c "import json,sys;d=json.load(open(sys.argv[1]));print(eval(sys.argv[2]))" "$1" "$2" 2>/dev/null; }

setup() { # setup <data_dir> <legacy_file>
  curl -s -m 10 -X POST "$BASE/api/v1/test/setup" \
    -H "Content-Type: application/json" \
    -d "{\"data_dir\":\"$1\",\"legacy_file\":\"$2\"}"
}

work_win=$(python -c "import os;print(os.path.abspath('tests/probe/evidence/v1/wk').replace(chr(92),'/'))")
rm -rf tests/probe/evidence/v1/wk
mkdir -p tests/probe/evidence/v1/wk
payload() { # payload <file>（JSON 从 stdin 管道读入，避开 argv 代码页转换）
  python -c "import sys;open(sys.argv[1],'wb').write(sys.stdin.buffer.read())" "$1"
}
work="tests/probe/evidence/v1/wk"
log "== NOTES-001 v1 battery $(date -Iseconds) base=$BASE work=$work_win"

# ── T-01 场景 1：合法旧档全量迁入 ─────────────────────────────
D1="$work/t01-valid"; D1W="$work_win/t01-valid"; mkdir -p "$D1"; cp "$FIX/notes-valid.json" "$D1/notes.json"; log "[S1 valid] setup: $(setup "$D1W/data" "$D1W/notes.json")"
curl -s -m 10 -X POST "$BASE/api/v1/migrate" -o "$OUT/s1-migrate.json"
log "[S1 migrate] migrated=$(jq_get "$OUT/s1-migrate.json" "d['migrated']") corrupted=$(jq_get "$OUT/s1-migrate.json" "d['corrupted']")" 2>>"$SUM" || true
python -c "
import json
d=json.load(open('$OUT/s1-migrate.json'))
assert d['migrated']==3 and len(d['corrupted'])==0 and d['saved'], d
print('[S1] 3 migrated, 0 corrupted, saved ✓')
" | tee -a "$SUM"
ls "$D1/data/notes/" > "$OUT/s1-files.txt" 2>&1
cat "$D1/data/manifest.json" > "$OUT/s1-manifest.json"
# 幂等：重跑迁移
curl -s -m 10 -X POST "$BASE/api/v1/migrate" -o "$OUT/s1-migrate-again.json"
python -c "
import json
d=json.load(open('$OUT/s1-migrate-again.json'))
assert d['skipped_existing'], d
print('[S1] repeat migrate → skipped_existing ✓')
" | tee -a "$SUM"

# ── T-01 场景 2：损坏档打捞 + 报告 + 原件不动 ─────────────────
D2="$work/t01-corrupt"; D2W="$work_win/t01-corrupt"; mkdir -p "$D2"
cp "$FIX/notes-corrupt.json" "$D2/notes.json"
before=$(md5sum "$D2/notes.json" | cut -d' ' -f1)
log "[S2 corrupt] setup: $(setup "$D2W/data" "$D2W/notes.json")"
curl -s -m 15 -X POST "$BASE/api/v1/migrate" -o "$OUT/s2-migrate.json"
python -c "
import json
d=json.load(open('$OUT/s2-migrate.json'))
assert d['migrated']==2, d
assert len(d['corrupted'])==1, d
print('[S2] migrated=%s corrupted=%s backup=%s ✓' % (d['migrated'], len(d['corrupted']), d['backup_file']))
" | tee -a "$SUM"
after=$(md5sum "$D2/notes.json" | cut -d' ' -f1)
python -c "
before='$before'; after='$after'
assert before==after, 'original file was modified!'
print('[S2] original untouched ✓')
" | tee -a "$SUM"
ls "$D2/data/corrupted/" > "$OUT/s2-report-files.txt" 2>&1
ls "$D2/data/backup/" > "$OUT/s2-backup-files.txt" 2>&1
# 复位后重开（从磁盘 manifest）确认可恢复
log "[S2 reopen] setup: $(setup "$D2W/data" "$D2W/notes.json")"

# ── T-01 场景 3：坏类型条目拒绝/标注 ─────────────────────────
D3="$work/t01-badtypes"; D3W="$work_win/t01-badtypes"; mkdir -p "$D3"
cp "$FIX/notes-bad-types.json" "$D3/notes.json"
log "[S3 badtypes] setup: $(setup "$D3W/data" "$D3W/notes.json")"
curl -s -m 15 -X POST "$BASE/api/v1/migrate" -o "$OUT/s3-migrate.json"
python -c "
import json
d=json.load(open('$OUT/s3-migrate.json'))
for c in d['corrupted']:
    print('[S3] corrupted[%s] %s' % (c['index'], c['reason']))
" | tee -a "$SUM"
cat "$D3/data/corrupted/report-r1.json" > "$OUT/s3-report.json" 2>&1

# ── T-01 场景 4：空数组 + AC-05 全新目录无种子 ────────────────
D4="$work/t01-empty"; D4W="$work_win/t01-empty"; mkdir -p "$D4"
cp "$FIX/notes-empty.json" "$D4/notes.json"
log "[S4 empty] setup: $(setup "$D4W/data" "$D4W/notes.json")"
curl -s -m 10 -X POST "$BASE/api/v1/migrate" -o "$OUT/s4-migrate.json"
curl -s -m 10 "$BASE/api/v1/notes" -o "$OUT/s4-list.json"
python -c "
import json
m=json.load(open('$OUT/s4-migrate.json'))
l=json.load(open('$OUT/s4-list.json'))
assert m['migrated']==0 and l==[], (m,l)
print('[S4] empty legacy → 0 notes ✓')
" | tee -a "$SUM"
# 全新目录（无 legacy 文件）→ 空库不注入演示数据
D5="$work/t01-fresh"; D5W="$work_win/t01-fresh"; mkdir -p "$D5/data"
log "[S5 fresh] setup: $(setup "$D5W/data" "$D5W/nope.json")"
curl -s -m 10 "$BASE/api/v1/notes" -o "$OUT/s5-list.json"
python -c "
import json
l=json.load(open('$OUT/s5-list.json'))
assert l==[], l
print('[S5] fresh dir → empty store, no demo seed ✓ (AC-05)')
" | tee -a "$SUM"

# ── T-02 场景 6：幂等创建（request_id 重放）──────────────────
D6="$work/t02-idem"; D6W="$work_win/t02-idem"; mkdir -p "$D6/data"
log "[S6 idem] setup: $(setup "$D6W/data" "$D6W/nope.json")"
  payload $work/p1.json <<'JSONEOF'
  {"request_id":"req-create-001","title":"中文标题 🎉","body":"第一行\n第二行","folder":"work"}
JSONEOF
  curl -s -m 10 -X POST "$BASE/api/v1/notes" -H "Content-Type: application/json" --data-binary @"$work/p1.json" -o "$OUT/s6-create1.json"
  payload $work/p2.json <<'JSONEOF'
  {"request_id":"req-create-001","title":"中文标题 🎉","body":"第一行\n第二行","folder":"work"}
JSONEOF
  curl -s -m 10 -X POST "$BASE/api/v1/notes" -H "Content-Type: application/json" --data-binary @"$work/p2.json" -o "$OUT/s6-create2.json"
python -c "
import json
a=json.load(open('$OUT/s6-create1.json'))
b=json.load(open('$OUT/s6-create2.json'))
assert a['ok'] and b['ok'], (a,b)
assert a['doc']['note_id']==b['doc']['note_id'], (a['doc']['note_id'], b['doc']['note_id'])
assert a['receipt']['status']=='committed'
assert b['receipt']['request_id']=='req-create-001'
print('[S6] idempotent create: same note_id=%s ✓ (AC-02)' % a['doc']['note_id'])
" | tee -a "$SUM"
ls "$D6/data/receipts/" > "$OUT/s6-receipts.txt" 2>&1
ls "$D6/data/journal/" > "$OUT/s6-journal.txt" 2>&1

# ── T-02 场景 7：条件更新 + revision 冲突（AC-04）────────────
nid=$(jq_get "$OUT/s6-create1.json" "d['doc']['note_id']")
rev=$(jq_get "$OUT/s6-create1.json" "d['doc']['revision']")
payload "$work/p7a.json" <<'JSONEOF'
{"expected_revision":1,"title":"更新后","body":"新正文","request_id":"req-upd-001"}
JSONEOF
curl -s -m 10 -X PUT "$BASE/api/v1/notes/$nid" -H "Content-Type: application/json" --data-binary "@$work/p7a.json" -o "$OUT/s7-update-ok.json"
payload "$work/p7b.json" <<'JSONEOF'
{"expected_revision":1,"title":"旧版本写入","body":"应被拒绝","request_id":"req-upd-bad"}
JSONEOF
curl -s -m 10 -X PUT "$BASE/api/v1/notes/$nid" -H "Content-Type: application/json" --data-binary "@$work/p7b.json" -o "$OUT/s7-update-conflict.json"
curl -s -m 10 "$BASE/api/v1/notes/$nid" -o "$OUT/s7-after.json"
python -c "
import json
ok=json.load(open('$OUT/s7-update-ok.json'))
cf=json.load(open('$OUT/s7-update-conflict.json'))
after=json.load(open('$OUT/s7-after.json'))
assert ok['ok'] and ok['doc']['revision']==$rev+1, ok
assert cf['ok']==False and cf['err_code']=='revision_conflict', cf
assert after['doc']['title']=='更新后', after
print('[S7] stale revision rejected; user content intact ✓ (AC-04)')
" | tee -a "$SUM"

# ── T-02 场景 8：软删/恢复（AC-05）───────────────────────────
curl -s -m 10 -X DELETE "$BASE/api/v1/notes/$nid" -o "$OUT/s8-trash.json"
curl -s -m 10 "$BASE/api/v1/notes" -o "$OUT/s8-list.json"
curl -s -m 10 "$BASE/api/v1/notes/$nid" -o "$OUT/s8-get.json"
curl -s -m 10 -X POST "$BASE/api/v1/notes/$nid/restore" -o "$OUT/s8-restore.json"
curl -s -m 10 "$BASE/api/v1/notes" -o "$OUT/s8-list2.json"
python -c "
import json
t=json.load(open('$OUT/s8-trash.json'))
l=json.load(open('$OUT/s8-list.json'))
g=json.load(open('$OUT/s8-get.json'))
r=json.load(open('$OUT/s8-restore.json'))
l2=json.load(open('$OUT/s8-list2.json'))
assert t['ok'] and g['doc']['state']=='trashed', (t,g)
assert all(x['note_id']!='$nid' for x in l), l
assert r['ok'] and any(x['note_id']=='$nid' for x in l2), (r,l2)
print('[S8] trash→hidden→restore ✓ (AC-05)')
" | tee -a "$SUM"

# ── T-02 场景 9：故障注入（AC-02）────────────────────────────
D9="$work/t02-fault"; D9W="$work_win/t02-fault"; mkdir -p "$D9/data"
log "[S9 fault] setup: $(setup "$D9W/data" "$D9W/nope.json")"
curl -s -m 10 -X POST "$BASE/api/v1/test/fault" -H "Content-Type: application/json" -d '{"stage":"after_entity"}' -o /dev/null
  payload $work/p3.json <<'JSONEOF'
  {"request_id":"req-fault-1","title":"中断的提交","body":"body","folder":""}
JSONEOF
  curl -s -m 10 -X POST "$BASE/api/v1/notes" -H "Content-Type: application/json" --data-binary @"$work/p3.json" -o "$OUT/s9-fault-create.json"
curl -s -m 10 "$BASE/api/v1/notes" -o "$OUT/s9-list.json"
curl -s -m 10 -X POST "$BASE/api/v1/test/fault" -H "Content-Type: application/json" -d '{"stage":"after_manifest"}' -o /dev/null
  payload $work/p4.json <<'JSONEOF'
  {"request_id":"req-fault-2","title":"manifest后中断","body":"body","folder":""}
JSONEOF
  curl -s -m 10 -X POST "$BASE/api/v1/notes" -H "Content-Type: application/json" --data-binary @"$work/p4.json" -o "$OUT/s9-fault-create2.json"
curl -s -m 10 "$BASE/api/v1/notes/$nid" -o /dev/null
# 重放同一 request_id（无成功收据 ⇒ 允许重新提交）
curl -s -m 10 -X POST "$BASE/api/v1/test/fault" -H "Content-Type: application/json" -d '{"stage":"off"}' -o /dev/null
  payload $work/p5.json <<'JSONEOF'
  {"request_id":"req-fault-1","title":"重试成功","body":"body","folder":""}
JSONEOF
  curl -s -m 10 -X POST "$BASE/api/v1/notes" -H "Content-Type: application/json" --data-binary @"$work/p5.json" -o "$OUT/s9-retry.json"
python -c "
import json
f1=json.load(open('$OUT/s9-fault-create.json'))
l=json.load(open('$OUT/s9-list.json'))
f2=json.load(open('$OUT/s9-fault-create2.json'))
rt=json.load(open('$OUT/s9-retry.json'))
assert f1['ok']==False and f1['err_code']=='fault_injected', f1
assert l==[], l                      # after_entity：manifest 未动
assert f2['ok']==False and f2['err_code']=='fault_injected', f2
# after_manifest：无成功收据；重放 req-fault-1 不得命中半成品
assert rt['ok'] and rt['receipt']['status']=='committed', rt
print('[S9] fault leaves no success receipt; retry lands cleanly ✓ (AC-02)')
" | tee -a "$SUM"
ls "$D9/data/journal/" > "$OUT/s9-journal.txt" 2>&1
ls "$D9/data/receipts/" > "$OUT/s9-receipts.txt" 2>&1
cat "$D9/data/manifest.json" > "$OUT/s9-manifest.json"

# ── T-02 场景 10：真实崩溃重启（kill -9 后端 → 重启 → 数据仍在）─
log "[S10 crash] 请由外部驱动：kill 后端进程 → 重启 auto run → POST /api/v1/test/setup 同目录 → GET /api/v1/notes"
log "== battery done =="
echo "battery finished; artifacts in $OUT" | tee -a "$SUM"
