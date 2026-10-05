import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request

root=Path.cwd()
run=root/'.auto'/('notes-r3-suite-'+str(time.time_ns()))
run.mkdir(parents=True,exist_ok=False)
with socket.socket() as s:
    s.bind(('127.0.0.1',0)); back_port=s.getsockname()[1]
with socket.socket() as s:
    s.bind(('127.0.0.1',0)); front_port=s.getsockname()[1]
env=dict(os.environ,AUTO_HTTP_PORT=str(back_port),AUTO_FRONT_PORT=str(front_port),NOTES_DATA_DIR=str(run/'data'),NOTES_SEED='1',NOTES_TEST_MODE='0',TAURI_ENV='1',NOTES_URL=f'http://127.0.0.1:{front_port}',PYTHONIOENCODING='utf-8',REVIEW_RUN=str(run))
for key in ('NOTES_FORCE_LOCK','NOTES_FAULT','NOTES_LEGACY_FILE','AUTO_HTTP_PROXY'): env.pop(key,None)
processes=[]; logs=[]
try:
    commands=[([str(root/'rust-workspace/target/debug/app-015-notes-back.exe')],root,'backend'),(['D:/soft/nodejs/node.exe',str(root/'gen/front/vue/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port',str(front_port),'--strictPort'],root/'gen/front/vue','frontend')]
    for cmd,cwd,name in commands:
        log=open(run/(name+'.log'),'wb'); logs.append(log)
        processes.append(subprocess.Popen(cmd,cwd=cwd,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW))
    for _ in range(100):
        try: urllib.request.urlopen(env['NOTES_URL'],timeout=1).close(); break
        except Exception: time.sleep(.1)
    else: raise RuntimeError('frontend not ready')
    with open(run/'playwright.log','wb') as output:
        tests=subprocess.run(['D:/soft/nodejs/node.exe',str(root/'tests/node_modules/@playwright/test/cli.js'),'test'],cwd=root/'tests',env=env,stdout=output,stderr=subprocess.STDOUT,timeout=240)
    print('Evidence:',str(run)); print('suite_exit_code=',tests.returncode)
    print((run/'playwright.log').read_text(encoding='utf8',errors='replace')[-1600:])
    with open(run/'ui.log','wb') as output:
        ui=subprocess.run(['D:/soft/nodejs/node.exe',str(root/'docs/plans/evidence/001-r3-recheck-20261005/ui-reproduce.cjs')],cwd=root,env=env,stdout=output,stderr=subprocess.STDOUT,timeout=90)
    print('ui_exit_code=',ui.returncode)
    print((run/'ui.log').read_text(encoding='utf8',errors='replace')[-2000:])
finally:
    for p in reversed(processes):
        if p.poll() is None: p.kill()
        p.wait(timeout=5)
    for log in logs: log.close()
