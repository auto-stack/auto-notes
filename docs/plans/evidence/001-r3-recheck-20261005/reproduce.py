import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path.cwd()
EXE = ROOT/'rust-workspace/target/debug/app-015-notes-back.exe'
RUN = ROOT/'.auto'/('notes-r3-recheck-'+str(time.time_ns()))
RUN.mkdir(parents=True,exist_ok=False)
results = {}

class Server:
    def __init__(self,name,data=None,**extra):
        self.data = data or RUN/name
        self.data.mkdir(parents=True,exist_ok=True)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); self.port=sock.getsockname()[1]
        env=dict(os.environ,AUTO_HTTP_PORT=str(self.port),NOTES_DATA_DIR=str(self.data),NOTES_SEED='0',NOTES_TEST_MODE='1')
        for key in ('NOTES_FORCE_LOCK','NOTES_FAULT','NOTES_LEGACY_FILE','NOTES_P2PROBE'): env.pop(key,None)
        env.update(extra)
        self.log=open(RUN/(name+'.log'),'wb')
        self.p=subprocess.Popen([str(EXE)],cwd=ROOT,env=env,stdout=self.log,stderr=self.log,creationflags=subprocess.CREATE_NO_WINDOW)
        for _ in range(100):
            try: self.call('GET','/api/v1/status'); break
            except Exception: time.sleep(.05)
        else: self.close(); raise RuntimeError('server unavailable')
    def call(self,method,path,payload=None):
        body=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None
        request=urllib.request.Request(f'http://127.0.0.1:{self.port}{path}',data=body,method=method,headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(request,timeout=10) as response:
                raw=response.read().decode()
                return {'http':response.status,'value':json.loads(raw) if raw else None}
        except urllib.error.HTTPError as error: return {'http':error.code,'body':error.read().decode()}
    def close(self):
        if self.p.poll() is None: self.p.kill()
        self.p.wait(timeout=5); self.log.close()
    def __enter__(self): return self
    def __exit__(self,*args): self.close()

def create(s,rid='create-1',title='中文🎉',body='第一行\n第二行'):
    return s.call('POST','/api/v1/notes',dict(request_id=rid,title=title,body=body,folder='work'))
def update(s,nid,rev,rid,body):
    return s.call('PUT',f'/api/v1/notes/{nid}',dict(expected_revision=rev,request_id=rid,title=body,body=body))
def safe(call):
    try: return call()
    except Exception as error: return {'error':str(error)}

with Server('protocol') as s:
    a=create(s)
    replay=create(s)
    first=update(s,'n-1',1,'update-1','更新一')
    immediate=update(s,'n-1',1,'update-1','更新一')
    second=update(s,'n-1',2,'update-2','更新二')
    late=update(s,'n-1',1,'update-1','更新一')
    b=create(s,'create-2','第二笔记','B')
    cross=update(s,'n-2',1,'create-1','应该修改B')
    results['idempotency']=dict(first=a,replay=replay,update_first=first,update_immediate=immediate,update_second=second,update_late_replay=late,cross_note_update=cross,after_cross=s.call('GET','/api/v1/notes/n-2'))
    s.call('PUT','/api/notes/1/tags',dict(tags=['中文标签','🎉']))
    results['before_crash']=s.call('GET','/api/v1/notes/n-1')

with Server('restart',data=RUN/'protocol') as s:
    results['after_crash']=s.call('GET','/api/v1/notes/n-1')
    results['post_restart_replay']=update(s,'n-1',1,'update-1','更新一')

with Server('faults') as s:
    for stage in ('after_entity','after_manifest'):
        s.call('POST','/api/v1/test/fault',{'stage':stage})
        failed=create(s,'fault-'+stage)
        s.call('POST','/api/v1/test/fault',{'stage':'off'})
        retry=create(s,'fault-'+stage)
        results[stage]=dict(fault=failed,retry=retry)
    results['fault_final_list']=s.call('GET','/api/v1/notes')

with Server('concurrent') as s:
    create(s)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        calls=list(pool.map(lambda i:safe(lambda:update(s,'n-1',1,'concurrent-'+str(i),'writer-'+str(i))),range(8)))
    results['concurrent_updates']=dict(calls=calls,final=s.call('GET','/api/v1/notes/n-1'))
    s.call('GET','/api/request-id?prefix=initialize')
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        ids=list(pool.map(lambda i:safe(lambda:s.call('GET','/api/request-id?prefix=bulk')),range(32)))
    values=[x.get('value') for x in ids if isinstance(x.get('value'),str)]
    results['concurrent_request_ids']=dict(calls=ids,count=len(values),unique_count=len(set(values)))

with Server('migration-null') as s:
    legacy=s.data/'legacy.json'
    legacy.write_text(json.dumps([{'id':10,'title':'前项','body':'A','tags':[]},None,{'id':11,'title':'后项','body':'B','tags':[]}],ensure_ascii=False),encoding='utf8')
    s.call('POST','/api/v1/test/setup',dict(data_dir=str(s.data),legacy_file=str(legacy)))
    results['migration_null']=dict(report=s.call('POST','/api/v1/migrate'),notes=s.call('GET','/api/v1/notes'),report_exists=(s.data/'corrupted/report-r1.json').exists())

with Server('migration-report-failure') as s:
    legacy=s.data/'legacy.json'
    legacy.write_text(json.dumps([{'id':20,'title':'valid','body':'A'},{'id':'bad','title':'invalid'}]),encoding='utf8')
    (s.data/'corrupted/report-r1.json').mkdir(parents=True)
    s.call('POST','/api/v1/test/setup',dict(data_dir=str(s.data),legacy_file=str(legacy)))
    results['migration_report_failure']=dict(first=s.call('POST','/api/v1/migrate'),retry=s.call('POST','/api/v1/migrate'),report_is_directory=(s.data/'corrupted/report-r1.json').is_dir())

with Server('migration-unicode') as s:
    legacy=s.data/'legacy.json'
    legacy.write_text(json.dumps([{'id':'bad','title':'中文'*100,'body':'a'},{'id':30,'title':'after','body':'ok'}],ensure_ascii=False),encoding='utf8')
    s.call('POST','/api/v1/test/setup',dict(data_dir=str(s.data),legacy_file=str(legacy)))
    results['migration_unicode']=safe(lambda:s.call('POST','/api/v1/migrate'))

snapshot=RUN/'phase1-snapshot'
shutil.copytree(ROOT/'tests/probe/evidence/v1/wedge-snapshot',snapshot)
with Server('phase1-startup',data=snapshot) as s:
    results['phase1_upgrade']=dict(old_manifest=json.loads((snapshot/'manifest.json').read_text()),old_confirmed_receipt=json.loads((snapshot/'receipts/d-1.json').read_text()),get=s.call('GET','/api/v1/notes/n-1'),list=s.call('GET','/api/v1/notes'))

with Server('default-gates',NOTES_TEST_MODE='0') as s:
    results['test_gates']=dict(setup=s.call('POST','/api/v1/test/setup',dict(data_dir=str(s.data),legacy_file='none')),fault=s.call('POST','/api/v1/test/fault',{'stage':'after_entity'}),traversal=create(s,'../escaped'),empty=create(s,''))

with Server('sqlite-open-failure') as s:
    other=RUN/'bad-database'; other.mkdir()
    (other/'inbox.db').mkdir()
    results['sqlite_open_failure']=dict(setup=s.call('POST','/api/v1/test/setup',dict(data_dir=str(other),legacy_file=str(other/'missing.json'))),create=create(s),notes=s.call('GET','/api/v1/notes'))

with Server('update-fault') as s:
    create(s)
    s.call('POST','/api/v1/test/fault',{'stage':'after_entity'})
    results['update_fault']=update(s,'n-1',1,'update-fault','must not commit before fault')
    results['update_fault_after']=s.call('GET','/api/v1/notes/n-1')

with Server('changed-request') as s:
    first=create(s,'same-intent','original','body-A')
    changed=create(s,'same-intent','different','body-B')
    results['changed_intent']=dict(first=first,changed=changed)


out=dict(reviewed_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),binary=str(EXE),binary_sha256=hashlib.sha256(EXE.read_bytes()).hexdigest(),runtime_note='Existing generated binary, no fresh build. Source findings cross-checked against current HEAD.',run_dir=str(RUN),results=results)
(RUN/'results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print('Evidence:',str(RUN/'results.json'))
for key,value in results.items():
    if key in ('concurrent_updates','concurrent_request_ids'):
        print(key, json.dumps({k:v for k,v in value.items() if k!='calls'},ensure_ascii=True))
    else: print(key,json.dumps(value,ensure_ascii=True))
