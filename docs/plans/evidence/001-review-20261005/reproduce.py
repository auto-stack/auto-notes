import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path.cwd()
EXE = ROOT / 'rust-workspace/target/debug/app-015-notes-back.exe'
RUN = ROOT / '.auto' / ('review001-' + str(time.time_ns()))
RUN.mkdir(parents=True, exist_ok=False)
results = {}

class Server:
    def __init__(self, name, data=None, **extra):
        self.data = data or RUN / name
        self.data.mkdir(parents=True, exist_ok=True)
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            self.port = s.getsockname()[1]
        env = dict(os.environ, AUTO_HTTP_PORT=str(self.port), NOTES_DATA_DIR=str(self.data), NOTES_SEED='0')
        env.pop('NOTES_FORCE_LOCK', None)
        env.pop('NOTES_FAULT', None)
        env.pop('NOTES_LEGACY_FILE', None)
        env.update(extra)
        self.log = open(RUN / (name + '.log'), 'wb')
        self.p = subprocess.Popen([str(EXE)], cwd=ROOT, env=env, stdout=self.log, stderr=self.log, creationflags=subprocess.CREATE_NO_WINDOW)
        for _ in range(100):
            try:
                self.call('GET', '/api/v1/status')
                break
            except Exception:
                time.sleep(.05)
        else:
            self.close()
            raise RuntimeError('server did not start')
    def call(self, method, path, payload=None):
        body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
        req = urllib.request.Request(f'http://127.0.0.1:{self.port}{path}', data=body, method=method, headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=8) as r:
                raw = r.read().decode()
                return {'http':r.status, 'value':json.loads(raw) if raw else None}
        except urllib.error.HTTPError as e:
            return {'http':e.code, 'body':e.read().decode()}
    def close(self):
        if self.p.poll() is None:
            self.p.kill()
        self.p.wait(timeout=5)
        self.log.close()
    def __enter__(self): return self
    def __exit__(self, *args): self.close()

def create(s, rid='create-1'):
    return s.call('POST','/api/v1/notes',{'request_id':rid,'title':'中文 🎉','body':'第一行\n第二行','folder':'work'})

with Server('idempotency') as s:
    a = create(s)
    b = create(s)
    s.call('POST','/api/v1/test/fault',{'stage':'after_manifest'})
    fault = create(s, 'create-fault')
    before = s.call('GET','/api/v1/notes')
    retry = create(s, 'create-fault')
    after = s.call('GET','/api/v1/notes')
    results['create_retry'] = dict(first=a,replay=b,fault=fault,before=before,retry=retry,after=after)
    nid = a['value']['doc']['note_id']
    payload = {'expected_revision':1,'title':'更新','body':'新正文','request_id':'update-1'}
    update = s.call('PUT',f'/api/v1/notes/{nid}',payload)
    replay = s.call('PUT',f'/api/v1/notes/{nid}',payload)
    stale = s.call('PUT',f'/api/v1/notes/{nid}',dict(payload, title='未保存草稿',request_id='stale-1'))
    results['update_retry'] = dict(first=update,replay=replay,stale=stale)
    s.call('PUT','/api/notes/1/tags',{'tags':['中文标签','emoji🎉']})
    s.call('DELETE',f'/api/v1/notes/{nid}')
    results['before_crash'] = s.call('GET',f'/api/v1/notes/{nid}')

with Server('restart', data=RUN/'idempotency') as s:
    results['restart_without_override'] = s.call('GET','/api/v1/notes/n-1')
with Server('restart-forced', data=RUN/'idempotency', NOTES_FORCE_LOCK='1') as s:
    results['restart_forced'] = s.call('GET','/api/v1/notes/n-1')
    results['restore'] = s.call('POST','/api/v1/notes/n-1/restore')

with Server('receipt-failure') as s:
    create(s)
    (s.data/'receipts/update-blocked.json').mkdir()
    payload = {'expected_revision':1,'title':'应确认收据','body':'内容','request_id':'update-blocked'}
    results['receipt_failure'] = s.call('PUT','/api/v1/notes/n-1',payload)
    results['receipt_failure']['receipt_is_directory'] = (s.data/'receipts/update-blocked.json').is_dir()

legacy = RUN/'legacy-null.json'
legacy.write_text(json.dumps([{'id':10,'title':'前项','body':'a','tags':[]},None,{'id':11,'title':'后项','body':'b','tags':[]}],ensure_ascii=False),encoding='utf8')
with Server('migration-null', NOTES_LEGACY_FILE=str(legacy)) as s:
    results['migration_null'] = s.call('POST','/api/v1/migrate')
    results['migration_null_list'] = s.call('GET','/api/v1/notes')

locked = RUN/'migration-locked'
locked.mkdir()
(locked/'writer.lock').write_text('other-writer',encoding='utf8')
with Server('migration-locked',data=locked, NOTES_LEGACY_FILE=str(ROOT/'tests/fixtures/inbox/legacy-v0/notes-valid.json')) as s:
    rejected = s.call('GET','/api/v1/notes/n-0')
    bypass = s.call('POST','/api/v1/migrate')
    results['migration_lock_bypass'] = dict(open=rejected,migrate=bypass,manifest_created=(locked/'manifest.json').exists())

with Server('concurrent') as s:
    create(s)
    def update_one(i):
        try:
            return s.call('PUT','/api/v1/notes/n-1',{'expected_revision':1,'title':f'writer-{i}','body':f'body-{i}','request_id':f'update-{i}'})
        except Exception as e: return {'error':str(e)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        calls = list(pool.map(update_one,range(8)))
    try: final = s.call('GET','/api/v1/notes/n-1')
    except Exception as e: final = {'error':str(e)}
    results['concurrent_revision'] = dict(calls=calls,final=final)

with Server('legacy-stale') as s:
    create(s)
    a = s.call('GET','/api/notes/1')
    b = s.call('GET','/api/notes/1')
    save_a = s.call('PUT','/api/notes/1',{'title':'client-A','body':'client-A new content'})
    save_b = s.call('PUT','/api/notes/1',{'title':'client-B stale','body':'client-B based on stale snapshot'})
    final = s.call('GET','/api/v1/notes/n-1')
    results['legacy_stale'] = dict(snapshot_a=a,snapshot_b=b,save_a=save_a,save_b=save_b,final=final,old_revision_exists=(s.data/'notes/n-1.r2.json').exists())
    escape = create(s,'../escaped')
    results['request_id_path'] = dict(response=escape,outside_receipts_exists=(s.data/'escaped.json').exists())

# Model an interrupted truncate+write of manifest; this is not a real mid-write kill.
data = RUN/'legacy-stale'
(data/'manifest.json').write_text('{"schema_version":1,"entries":[',encoding='utf8')
with Server('torn-manifest',data=data,NOTES_FORCE_LOCK='1') as s:
    results['torn_manifest_simulation'] = dict(get=s.call('GET','/api/v1/notes/n-1'),journal_files=len(list((data/'journal').glob('*.json'))),receipt_files=len(list((data/'receipts').glob('*.json'))))

out = {'reviewed_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
       'binary':str(EXE),'binary_sha256':hashlib.sha256(EXE.read_bytes()).hexdigest(),
       'binary_mtime':EXE.stat().st_mtime,'runtime_note':'Existing generated backend binary; no fresh generation/build in this review.',
       'results':results}
(RUN/'results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
for k,v in results.items():
    if k=='concurrent_revision':
        print(k, 'success_count=',sum(x.get('value',{}).get('ok',False) for x in v['calls']), 'final=',json.dumps(v['final'],ensure_ascii=True))
    else: print(k,json.dumps(v,ensure_ascii=True))
