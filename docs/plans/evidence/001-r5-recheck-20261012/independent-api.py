import json, os, shutil, sqlite3
from pathlib import Path
ROOT=Path.cwd()
source=(ROOT/'tests/probe/evidence/r5-work/verify_backend_scratch.py').read_text(encoding='utf8').split('# ═══ U1/U2:')[0]
scope={'__name__':'probe'}
exec(compile(source,'server-definitions','exec'),scope)
Server=scope['Server']; RUN=scope['RUN']; WEDGE=scope['WEDGE']
results={}
def legacy(data):
    for name in ('manifest.json','notes','receipts','journal'):
        src=WEDGE/name; dst=data/name
        if src.is_dir(): shutil.copytree(src,dst)
        else: shutil.copyfile(src,dst)
def rows(data):
    with sqlite3.connect(data/'inbox.db') as db:
        return dict(notes=db.execute('SELECT note_id,revision,title,body FROM notes').fetchall(),requests=db.execute('SELECT request_id,note_id,rev,intent FROM requests ORDER BY request_id').fetchall(),meta=db.execute('SELECT k,v FROM meta ORDER BY k').fetchall())
with Server('mixed') as s:
    created=s.call('POST','/api/v1/notes',dict(request_id='current-create',title='已确认的新数据',body='不得覆盖',folder=''))
    legacy(s.data)
    with sqlite3.connect(s.data/'inbox.db') as db: db.execute("DELETE FROM meta WHERE k='upgraded'")
    before=rows(s.data)
    calls=[]
    for _ in range(3):
        calls.append(dict(response=s.call('GET','/api/v1/notes'),state=rows(s.data)))
    results['mixed_conflict_retries']=dict(created=created,before=before,calls=calls)
with Server('r4-repair') as s:
    legacy(s.data)
    first=s.call('GET','/api/v1/notes')
    saved=s.call('PUT','/api/v1/notes/n-1',dict(request_id='confirmed-later',expected_revision=2,title='升级后确认保存的新正文',body='必须保留 rev3'))
    with sqlite3.connect(s.data/'inbox.db') as db: db.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('corrupted_r1','[\"legacy upgrade\",[{\"index\":0}]]')")
    before=rows(s.data)
    after=s.call('GET','/api/v1/notes/n-1')
    later=s.call('PUT','/api/v1/notes/n-1',dict(request_id='saved-after-repair',expected_revision=2,title='修复完成后再次确认保存',body='后续编辑必须存活'))
    again=s.call('GET','/api/v1/notes/n-1')
    results['repair_overwrites_newer']=dict(first=first,saved=saved,before=before,after=after,state=rows(s.data),saved_after_repair=later,after_next_read=again)
with Server('bad-entity') as s:
    legacy(s.data)
    (s.data/'notes/n-1.r2.json').write_text('{}',encoding='utf8')
    results['entity_empty_object']=dict(response=s.call('GET','/api/v1/notes'),state=rows(s.data))
with Server('old-same-intent') as s:
    legacy(s.data)
    before=s.call('GET','/api/v1/notes/n-1')
    replay=s.call('PUT','/api/v1/notes/n-1',dict(request_id='d-2',expected_revision=1,title='doc1-updated',body='body two'))
    results['legacy_same_intent']=dict(before=before,replay=replay,after=s.call('GET','/api/v1/notes/n-1'))
failures=[]
mixed=results['mixed_conflict_retries']
if any(call['state']['notes']!=mixed['before']['notes'] for call in mixed['calls']): failures.append('IND-API-1 mixed conflict retries preserve current data')
repair=results['repair_overwrites_newer']
if repair['after']['value']['doc']['revision']!=3 or repair['after_next_read']['value']['doc']['revision']!=3: failures.append('IND-API-2 repair preserves confirmed later revision')
if dict(results['entity_empty_object']['state']['meta']).get('upgraded')=='1': failures.append('IND-API-3 malformed entity cannot complete upgrade')
results['oracle_failures']=failures
(RUN/'independent-api.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
print('Evidence:',RUN)
for key,value in results.items(): print(key,json.dumps(value,ensure_ascii=False))
raise SystemExit(1 if failures else 0)
