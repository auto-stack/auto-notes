from pathlib import Path
import os,json,socket,subprocess,time,urllib.request
root=Path.cwd(); run=root/'.auto'/('notes-r4-vm-negative-'+str(time.time_ns()));run.mkdir()
def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
mcp,back=port(),port(); env=dict(os.environ,NOTES_DATA_DIR=str(run/'data'),NOTES_SEED='1',NOTES_TEST_MODE='0',AUTOUI_MCP_PORT=str(mcp),PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
for key in ['NOTES_FAULT','NOTES_FORCE_LOCK','NOTES_LEGACY_FILE','AUTO_HTTP_PROXY']:env.pop(key,None)
cmd=['D:/autostack/auto-lang/target/debug/auto.exe','run','-r','vm','-B',str(back)]
record={'command':cmd,'mcp_port':mcp,'backend_port':back,'run_dir':str(run),'suite_exit':None}
print('Evidence:',run,flush=True)
with open(run/'boot.log','wb') as log:
    p=subprocess.Popen(cmd,cwd=root,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
    record['pid']=p.pid
    try:
        ready=False
        for i in range(90):
            if p.poll() is not None:record['boot_exit']=p.returncode;break
            try:
                data=json.dumps({'jsonrpc':'2.0','id':1,'method':'tools/list','params':{}}).encode()
                req=urllib.request.Request(f'http://127.0.0.1:{mcp}/mcp',data=data,headers={'Content-Type':'application/json','Connection':'close'})
                with urllib.request.urlopen(req,timeout=1) as response: response.read()
                ready=True;break
            except Exception:time.sleep(1)
        record['mcp_ready']=ready
        if ready:
            import sys
            sys.path.insert(0,str(root/'tests'))
            from autotest import McpAdapter,Step
            adapter=McpAdapter(mode='vm',url=f'http://127.0.0.1:{mcp}/mcp')
            assert adapter.wait_ready(timeout=30)
            def click(label):adapter._exec_when(Step('when','click_button',dict(label=label),label))
            def edit(value):adapter._exec_when(Step('when','type_text',dict(label='Untitled',value=value,kind='input'),value))
            def state():return adapter._call('autoui_state',fields=['draft_title','draft_body','draft_revision','dirty','conflict','has_recovery','rec_title','draft_request_id'])
            def api(method,path,data=None):
                raw=json.dumps(data).encode() if data is not None else None
                req=urllib.request.Request(f'http://127.0.0.1:{back}'+path,data=raw,method=method,headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(req,timeout=10) as response:return json.loads(response.read())
            click('Welcome');old=state()
            doc=api('GET','/api/v1/notes/n-1')['doc']
            server=api('PUT','/api/v1/notes/n-1',dict(expected_revision=doc['revision'],title='VM server latest',body='VM server latest body',request_id='vm-external'))
            edit('VM local conflict');click('Save');conflict=state();click('Discard');discard=state()
            edit('VM precious recovery draft');click('Save');click('Shopping List');stashed=state()
            edit('VM new shopping draft');click('Recover');recovered=state()
            record['negative_results']=dict(initial=old,external_update=server,conflict=conflict,discard=discard,stashed=stashed,recovered=recovered,server_final=api('GET','/api/v1/notes/n-1'))
            print(json.dumps(record['negative_results']),flush=True)
    except Exception as error:record['error']=repr(error)
    finally:
        if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:p.wait(timeout=5)
        except Exception:pass
(run/'vm-result.json').write_text(json.dumps(record,indent=2),encoding='utf8')
print(json.dumps(record),flush=True)
print((run/'boot.log').read_text(encoding='utf8',errors='replace')[-1400:],flush=True)
