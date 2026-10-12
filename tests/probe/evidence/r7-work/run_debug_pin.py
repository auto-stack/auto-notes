# launcher: backend+vite for debug_pin_flow.cjs (repo-root cwd for the cjs)
import os, socket, subprocess, time, urllib.request
from pathlib import Path
root = Path.cwd()
run = root / '.auto' / ('r7-dbg-pin-' + str(time.time_ns()))
run.mkdir(parents=True)
with socket.socket() as s: s.bind(('127.0.0.1',0)); back = s.getsockname()[1]
with socket.socket() as s: s.bind(('127.0.0.1',0)); front = s.getsockname()[1]
env = dict(os.environ, AUTO_HTTP_PORT=str(back), AUTO_FRONT_PORT=str(front),
           NOTES_DATA_DIR=str(run/'data'), NOTES_SEED='1', NOTES_TEST_MODE='1', TAURI_ENV='1',
           NOTES_URL=f'http://127.0.0.1:{front}', R5_RUN=str(run), PYTHONUTF8='1')
procs=[]; logs=[]
try:
    for cmd,cwd,name in [
        ([str(root/'rust-workspace/target/debug/app-015-notes-back.exe')], root, 'backend'),
        (['D:/soft/nodejs/node.exe', str(root/'gen/front/vue/node_modules/vite/bin/vite.js'), '--host','127.0.0.1','--port',str(front),'--strictPort'], root/'gen/front/vue', 'frontend')]:
        lg=open(run/(name+'.log'),'wb'); logs.append(lg)
        procs.append(subprocess.Popen(cmd,cwd=cwd,env=env,stdout=lg,stderr=lg,creationflags=subprocess.CREATE_NO_WINDOW))
    for _ in range(100):
        try: urllib.request.urlopen(env['NOTES_URL'],timeout=1).close(); break
        except Exception: time.sleep(.1)
    r=subprocess.run(['D:/soft/nodejs/node.exe', str(root/'tests/probe/evidence/r7-work/debug_pin_flow.cjs')],
                     cwd=root, env=env, capture_output=True, text=True, timeout=180, encoding='utf8', errors='replace')
    print(r.stdout[-3000:])
    print('exit=', r.returncode)
finally:
    for pr in reversed(procs):
        if pr.poll() is None: pr.kill()
        pr.wait(timeout=5)
    for lg in logs: lg.close()
