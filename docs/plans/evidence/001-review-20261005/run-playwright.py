import os
from pathlib import Path
import subprocess
import time
import urllib.request

root = Path.cwd()
run = root / '.auto' / ('review001-suite-' + str(time.time_ns()))
run.mkdir(parents=True, exist_ok=False)
env = dict(os.environ, AUTO_HTTP_PORT='17919', AUTO_FRONT_PORT='17918', NOTES_DATA_DIR=str(run/'suite-data'), NOTES_SEED='1', TAURI_ENV='1', NOTES_URL='http://127.0.0.1:17918', PYTHONIOENCODING='utf-8')
for key in ('NOTES_FORCE_LOCK','NOTES_FAULT','NOTES_LEGACY_FILE'): env.pop(key,None)
processes = []
logs = []
try:
    for cmd,cwd,name in [([str(root/'rust-workspace/target/debug/app-015-notes-back.exe')],root,'suite-back'),(['D:/soft/nodejs/node.exe',str(root/'gen/front/vue/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','17918','--strictPort'],root/'gen/front/vue','suite-front')]:
        log = open(run/(name+'.log'),'wb'); logs.append(log)
        processes.append(subprocess.Popen(cmd,cwd=cwd,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW))
    for _ in range(100):
        try:
            urllib.request.urlopen('http://127.0.0.1:17918',timeout=1).close()
            break
        except Exception: time.sleep(.1)
    else: raise RuntimeError('frontend not ready')
    with open(run/'suite.log','wb') as output:
        test = subprocess.run(['D:/soft/nodejs/node.exe',str(root/'tests/node_modules/@playwright/test/cli.js'),'test'],cwd=root/'tests',env=env,stdout=output,stderr=subprocess.STDOUT,timeout=240)
    print('suite_exit_code=',test.returncode)
    print((run/'suite.log').read_text(encoding='utf8',errors='replace')[-6500:])
finally:
    for p in reversed(processes):
        if p.poll() is None: p.kill()
        p.wait(timeout=5)
    for log in logs: log.close()
