from pathlib import Path
import json,sqlite3,hashlib,shutil,subprocess,concurrent.futures
root=Path.cwd(); ns={}
defs=(root/'docs/plans/evidence/001-r4-recheck-20261008/api-reproduce.py').read_text(encoding='utf8').split("with Server('protocol') as s:")[0].replace("'notes-r4-recheck-'","'notes-r4-deep-'")
exec(compile(defs,'definitions','exec'),ns)
Server=ns['Server']; create=ns['create']; update=ns['update']; RUN=ns['RUN']; safe=ns['safe']; results={}

with Server('intent-separator') as s:
    create(s)
    first=s.call('PUT','/api/v1/notes/n-1',dict(expected_revision=1,request_id='ambiguous',title='a|b',body='c'))
    second=s.call('PUT','/api/v1/notes/n-1',dict(expected_revision=1,request_id='ambiguous',title='a',body='b|c'))
    results['delimiter_intent']=dict(first=first,second=second,actual=s.call('GET','/api/v1/notes/n-1'))

snapshot=root/'tests/probe/evidence/v1/wedge-snapshot'
def clone(name):
    data=RUN/name; shutil.copytree(snapshot,data); return data

data=clone('upgrade-metadata')
m=json.loads((data/'manifest.json').read_text()); m['entries'][0].update(state='trashed',tags=['已保存标签','important'],folder='saved-folder',pinned=True)
(data/'manifest.json').write_text(json.dumps(m,ensure_ascii=False),encoding='utf8')
with Server('upgrade-metadata',data=data) as s:
    results['upgrade_metadata']=dict(expected_manifest=m,get=s.call('GET','/api/v1/notes/n-1'),list=s.call('GET','/api/v1/notes'),replay_create=s.call('POST','/api/v1/notes',dict(request_id='d-2',title='new intent',body='should reject',folder='')))

data=clone('upgrade-all-missing'); (data/'notes/n-1.r2.json').unlink()
with Server('upgrade-all-missing',data=data) as s:
    results['upgrade_all_missing']=dict(status=s.call('GET','/api/v1/status'),get=s.call('GET','/api/v1/notes/n-1'),create=create(s,'unexpected-empty-success'))
    with sqlite3.connect(data/'inbox.db') as db: results['upgrade_all_missing']['meta']=db.execute('SELECT * FROM meta').fetchall()

data=clone('upgrade-bad-backup'); (data/'legacy-backup').write_text('blocked backup',encoding='utf8')
with Server('upgrade-bad-backup',data=data) as s:
    results['upgrade_backup_failure']=dict(get=s.call('GET','/api/v1/notes/n-1'),backup_is_file=(data/'legacy-backup').is_file())

data=RUN/'upgrade-bad-manifest'; data.mkdir(); (data/'manifest.json').write_text('{}',encoding='utf8')
with Server('upgrade-bad-manifest',data=data) as s:
    results['upgrade_manifest_shape']=dict(status=s.call('GET','/api/v1/status'),list=s.call('GET','/api/v1/notes'),create=create(s))

with Server('v1-schema') as s:
    create(s)
    first=update(s,'n-1',1,'old-update','original successful update')
    with sqlite3.connect(s.data/'inbox.db') as db:
        db.execute('ALTER TABLE requests RENAME TO old_requests')
        db.execute('CREATE TABLE requests(request_id TEXT PRIMARY KEY,note_id TEXT NOT NULL,kind TEXT NOT NULL)')
        db.execute('INSERT INTO requests SELECT request_id,note_id,kind FROM old_requests')
        db.execute('DROP TABLE old_requests'); db.commit()
    results['existing_sqlite_requests']=dict(first=first,replay=update(s,'n-1',1,'old-update','different intent'),note=s.call('GET','/api/v1/notes/n-1'))

for name,items in [('boolean-id',[{'id':True,'title':'boolean must be rejected'},{'id':20,'title':'valid','body':'ok'}]),('bad-body',[{'id':21,'title':'valid title','body':{'text':'must report'}},{'id':22,'title':'valid','body':'ok'}]),('bad-tags-item',[{'id':23,'title':'valid','tags':[7,None]},{'id':24,'title':'valid','body':'ok'}])]:
    with Server(name) as s:
        legacy=s.data/'legacy.json'; legacy.write_text(json.dumps(items),encoding='utf8')
        s.call('POST','/api/v1/test/setup',dict(data_dir=str(s.data),legacy_file=str(legacy)))
        results[name]=dict(report=s.call('POST','/api/v1/migrate'),notes=s.call('GET','/api/v1/notes'))

with Server('two-process-A') as a:
    create(a)
    with Server('two-process-B',data=a.data) as b:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            calls=list(pool.map(lambda i:update(a if i%2==0 else b,'n-1',1,'dual-'+str(i),'writer-'+str(i)),range(8)))
        results['dual_process_updates']=dict(calls=calls,final=a.call('GET','/api/v1/notes/n-1'))
        a.call('GET','/api/request-id?prefix=init')
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
            calls=list(pool.map(lambda i:safe(lambda:(a if i%2==0 else b).call('GET','/api/request-id?prefix=cross-process')),range(128)))
        values=[v.get('value') for v in calls if isinstance(v.get('value'),str)]
        results['dual_process_request_ids']=dict(count=len(values),unique=len(set(values)),calls=calls)

out=dict(reviewed_commit=subprocess.check_output(['git','-c','safe.directory='+str(root).replace('\\','/'),'rev-parse','HEAD'],cwd=root,text=True).strip(),run_dir=str(RUN),results=results)
(RUN/'deep-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print('Evidence:',RUN)
for k,v in results.items(): print(k,json.dumps({a:b for a,b in v.items() if a!='calls'},ensure_ascii=True))
