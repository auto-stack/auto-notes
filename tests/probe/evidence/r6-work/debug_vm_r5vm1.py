# debug: replay R5-VM-1 steps with UI snapshots after each click
from pathlib import Path
import os, json, socket, subprocess, time, urllib.request

root = Path.cwd()
run = root / '.auto' / ('r6-dbg-' + str(time.time_ns()))
run.mkdir(parents=True)

def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0)); return s.getsockname()[1]

mcp, back = port(), port()
env = dict(os.environ, NOTES_DATA_DIR=str(run / 'data'), NOTES_SEED='1', NOTES_TEST_MODE='1',
           AUTOUI_MCP_PORT=str(mcp), PYTHONUTF8='1')
for key in ['NOTES_FAULT', 'NOTES_FORCE_LOCK', 'NOTES_LEGACY_FILE', 'AUTO_HTTP_PROXY']:
    env.pop(key, None)
cmd = ['D:/autostack/auto-lang/target/debug/auto.exe', 'run', '-r', 'vm', '-B', str(back)]
p = None
try:
    log = open(run / 'boot.log', 'wb')
    p = subprocess.Popen(cmd, cwd=root, env=env, stdout=log, stderr=log,
                         creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
    ready = False
    for i in range(90):
        if p.poll() is not None: break
        try:
            data = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list', 'params': {}}).encode()
            req = urllib.request.Request(f'http://127.0.0.1:{mcp}/mcp', data=data,
                                         headers={'Content-Type': 'application/json', 'Connection': 'close'})
            urllib.request.urlopen(req, timeout=1)
            ready = True; break
        except Exception:
            time.sleep(1)
    assert ready
    import sys
    sys.path.insert(0, str(root / 'tests'))
    from autotest import McpAdapter, Step
    adapter = McpAdapter(mode='vm', url=f'http://127.0.0.1:{mcp}/mcp')
    assert adapter.wait_ready(timeout=30)

    def click(label):
        adapter._exec_when(Step('when', 'click_button', dict(label=label), label))

    def edit(value):
        adapter._exec_when(Step('when', 'type_text', dict(label='Untitled', value=value, kind='input'), value))

    def snap(tag):
        s = adapter._call('autoui_snapshot')
        buttons = [ln for ln in s.splitlines() if 'button' in ln or 'Welcome' in ln]
        st = adapter._call('autoui_state', fields=['draft_title', 'dirty', 'conflict', 'has_recovery', 'has_recovery2'])
        print(f'--- {tag}: state={st.strip()[:200]}')
        print('    welcome-in-snapshot:', 'Welcome' in s)

    def call(method, path, data=None):
        raw = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(f'http://127.0.0.1:{back}' + path, data=raw, method=method,
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read())

    click('Welcome')
    snap('after select Welcome')
    click('Shopping List')
    snap('after clean nav (no edit)')
    click('Welcome')
    snap('after clean nav back')
    doc = call('GET', '/api/v1/notes/n-1')['doc']
    call('PUT', '/api/v1/notes/n-1', dict(expected_revision=doc['revision'], title='VM ext bump', body='external', request_id='dbg-ext-1'))
    edit('VM precious recovery draft')
    click('Save')
    snap('after conflict Save')
    click('Shopping List')
    snap('after conflict nav')
    s = adapter._call('autoui_snapshot')
    print('===== FULL SNAPSHOT after nav Shopping =====')
    open("dbg-snapshot.txt", "w", encoding="utf8").write(s)
    print('===== state full =====')
    print(adapter._call('autoui_state', fields=['notes', 'search', 'active_folder', 'active_id', 'stash_blocked', 'visible_pinned', 'visible_notes', 'has_recovery', 'rec_title', 'has_recovery2', 'rec2_title', 'conflict', 'dirty']))
    edit('VM new shopping draft')
    click('Recover')
    snap('after Recover 1')
    click('Recover')
    snap('after Recover 2')
    click('Welcome')
    snap('after click Welcome')
finally:
    if p is not None:
        if p.poll() is None:
            subprocess.run(['taskkill', '/PID', str(p.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try: p.wait(timeout=5)
        except Exception: pass
    log.close()
