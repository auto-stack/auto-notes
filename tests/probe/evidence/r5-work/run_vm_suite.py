# r5 work：原 19 项 VM autotest 套件回归（净库种子基线，单轮单跑）
from pathlib import Path
import os, json, socket, subprocess, time, urllib.request

root = Path.cwd()
run = root / '.auto' / ('r5-vm-suite-' + str(time.time_ns()))
run.mkdir(parents=True)

def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

mcp, back = port(), port()
env = dict(os.environ, NOTES_DATA_DIR=str(run / 'data'), NOTES_SEED='1', NOTES_TEST_MODE='0',
           AUTOUI_MCP_PORT=str(mcp), PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
for key in ['NOTES_FAULT', 'NOTES_FORCE_LOCK', 'NOTES_LEGACY_FILE', 'AUTO_HTTP_PROXY']:
    env.pop(key, None)
cmd = ['D:/autostack/auto-lang/target/debug/auto.exe', 'run', '-r', 'vm', '-B', str(back)]
record = {'command': cmd, 'mcp_port': mcp, 'backend_port': back, 'run_dir': str(run), 'suite_exit': None}
print('Evidence:', run, flush=True)
p = None
try:
    with open(run / 'boot.log', 'wb') as log:
        p = subprocess.Popen(cmd, cwd=root, env=env, stdout=log, stderr=log,
                             creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
        record['pid'] = p.pid
        ready = False
        for i in range(90):
            if p.poll() is not None:
                record['boot_exit'] = p.returncode
                break
            try:
                data = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list', 'params': {}}).encode()
                req = urllib.request.Request(f'http://127.0.0.1:{mcp}/mcp', data=data,
                                             headers={'Content-Type': 'application/json', 'Connection': 'close'})
                with urllib.request.urlopen(req, timeout=1):
                    pass
                ready = True
                break
            except Exception:
                time.sleep(1)
        record['mcp_ready'] = ready
        if ready:
            with open(run / 'suite.log', 'wb') as output:
                result = subprocess.run(['C:/Python314/python.exe', 'tests/run_autotest.py', '015-notes.autotest',
                                         '--mode', 'vm', '--url', f'http://127.0.0.1:{mcp}/mcp'],
                                        cwd=root, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=240)
            record['suite_exit'] = result.returncode
            print((run / 'suite.log').read_text(encoding='utf8', errors='replace')[-1500:], flush=True)
finally:
    if p is not None:
        if p.poll() is None:
            subprocess.run(['taskkill', '/PID', str(p.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            p.wait(timeout=5)
        except Exception:
            pass
(run / 'vm-result.json').write_text(json.dumps(record, indent=2), encoding='utf8')
print('suite_exit =', record['suite_exit'], flush=True)
