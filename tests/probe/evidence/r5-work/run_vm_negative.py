# r5 work：VM/MCP 真实驱动负例（V-19 对应 F-R5-03 / SD-14）
# R5-VM-1 Recover 保全两份草稿（含第二恢复槽状态）
# R5-VM-2 Discard 取最新服务器版本（外部写者后）
# R5-VM-3 未确认提交裁决：after_manifest 故障（提交已落地、UI 报失败）→
#         继续编辑再保存 → 新意图经 revision 冲突裁决采用服务器 revision → 成功
from pathlib import Path
import os, json, socket, subprocess, time, urllib.request

root = Path.cwd()
run = root / '.auto' / ('r5-vm-' + str(time.time_ns()))
run.mkdir(parents=True)

def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

mcp, back = port(), port()
env = dict(os.environ, NOTES_DATA_DIR=str(run / 'data'), NOTES_SEED='1', NOTES_TEST_MODE='1',
           AUTOUI_MCP_PORT=str(mcp), PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
for key in ['NOTES_FAULT', 'NOTES_FORCE_LOCK', 'NOTES_LEGACY_FILE', 'AUTO_HTTP_PROXY']:
    env.pop(key, None)
cmd = ['D:/autostack/auto-lang/target/debug/auto.exe', 'run', '-r', 'vm', '-B', str(back)]
record = {'command': cmd, 'mcp_port': mcp, 'backend_port': back, 'run_dir': str(run)}
print('Evidence:', run, flush=True)

def api(method, path, data=None):
    raw = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(f'http://127.0.0.1:{back}' + path, data=raw, method=method,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read())

results = {}
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
            import sys
            sys.path.insert(0, str(root / 'tests'))
            from autotest import McpAdapter, Step
            adapter = McpAdapter(mode='vm', url=f'http://127.0.0.1:{mcp}/mcp')
            assert adapter.wait_ready(timeout=30)

            def click(label):
                adapter._exec_when(Step('when', 'click_button', dict(label=label), label))

            def edit(value):
                adapter._exec_when(Step('when', 'type_text', dict(label='Untitled', value=value, kind='input'), value))

            def state():
                raw = adapter._call('autoui_state', fields=['draft_title', 'draft_revision', 'dirty', 'conflict',
                                                            'has_recovery', 'rec_title', 'has_recovery2', 'rec2_title',
                                                            'draft_request_id', 'has_pend', 'pend_title', 'has_prev'])
                out = {}
                for line in raw.splitlines():
                    tt = line.strip()
                    if ': ' in tt and tt.endswith(')') and ' (' in tt:
                        name, rest = tt.split(': ', 1)
                        v = rest.rsplit(' (', 1)[0].strip()
                        if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
                            v = v[1:-1]
                        out[name.strip()] = v
                return out

            def call(method, path, data=None):
                raw = json.dumps(data).encode() if data is not None else None
                req = urllib.request.Request(f'http://127.0.0.1:{back}' + path, data=raw, method=method,
                                             headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    return json.loads(response.read())

            fails = []

            def check(name, cond, detail=''):
                print(('[PASS] ' if cond else '[FAIL] ') + name, '' if cond else detail, flush=True)
                if not cond:
                    fails.append(name)

            # ── R5-VM-1: Recover 保全两份草稿 ──────────────────────────
            click('Welcome')
            doc = call('GET', '/api/v1/notes/n-1')['doc']
            call('PUT', '/api/v1/notes/n-1', dict(expected_revision=doc['revision'],
                                                  title='VM ext bump', body='external', request_id='r5vm-ext-1'))
            edit('VM precious recovery draft')
            click('Save')
            s1 = state()
            check('R5-VM-1 conflict kept dirty', s1.get('conflict') == 'true', s1)
            click('Shopping List')
            s2 = state()
            check('R5-VM-1 stashed to slot A', s2.get('has_recovery') == 'true'
                  and s2.get('rec_title') == 'VM precious recovery draft', s2)
            edit('VM new shopping draft')
            click('Recover')
            s3 = state()
            check('R5-VM-1 recover shows OLD stashed draft (not self-overwrite)',
                  s3.get('draft_title') == 'VM precious recovery draft', s3)
            check('R5-VM-1 current draft preserved in slot B',
                  s3.get('has_recovery2') == 'true'
                  and s3.get('rec2_title') == 'VM new shopping draft', s3)
            click('Recover')
            s4 = state()
            check('R5-VM-1 second slot recoverable back',
                  s4.get('draft_title') == 'VM new shopping draft', s4)
            results['r5_vm_1'] = dict(after_conflict=s1, after_nav=s2, after_recover=s3, after_recover2=s4)

            # ── R5-VM-2: Discard 取最新服务器版本 ──────────────────────
            # 回到 Welcome（服务器此刻 = 'VM ext bump'），本地陈旧编辑后再被
            # 外部写者推进一次 → Save 冲突 → Discard 必须显示最新外部标题
            click('Welcome')
            s4b = state()
            check('R5-VM-2 welcome fresh load after recovery flow',
                  s4b.get('draft_title') == 'VM ext bump' and s4b.get('dirty') == 'false', s4b)
            edit('VM stale local edit')
            call('PUT', '/api/v1/notes/n-1', dict(expected_revision=2, title='VM ext bump 2',
                                                  body='external 2', request_id='r5vm-ext-2'))
            click('Save')
            s5a = state()
            check('R5-VM-2 stale save conflicts', s5a.get('dirty') == 'true' and s5a.get('conflict') == 'true', s5a)
            click('Discard')
            s5 = state()
            check('R5-VM-2 discard shows latest server title',
                  s5.get('draft_title') == 'VM ext bump 2' and s5.get('dirty') == 'false', s5)
            results['r5_vm_2'] = dict(fresh_load=s4b, after_conflict=s5a, after_discard=s5,
                                      server=call('GET', '/api/v1/notes/n-1'))

            # ── R5-VM-3: 未确认提交裁决（after_manifest 故障）──────────
            call('POST', '/api/v1/test/fault', dict(stage='after_manifest'))
            edit('VM unconfirmed C1')
            click('Save')
            s6 = state()
            check('R5-VM-3 fault keeps draft dirty', s6.get('dirty') == 'true', s6)
            call('POST', '/api/v1/test/fault', dict(stage='off'))
            server_after_c1 = call('GET', '/api/v1/notes/n-1')['doc']
            check('R5-VM-3 faulted commit actually landed server-side',
                  server_after_c1['title'] == 'VM unconfirmed C1' and server_after_c1['revision'] == 4,
                  server_after_c1)
            edit('VM unconfirmed C1 EDITED C2')
            click('Save')
            # 裁决链（get_note_r+retry）在 handler 内多跳 HTTP——autoui_state 可能
            # 在 handler park 期间应答，轮询到 dirty 清零再断言（读竞态非产品失败）。
            s7 = {}
            for _ in range(40):
                s7 = state()
                if s7.get('dirty') == 'false':
                    break
                time.sleep(0.25)
            check('R5-VM-3 adjudicated new intent saved',
                  s7.get('dirty') == 'false' and s7.get('draft_title') == 'VM unconfirmed C1 EDITED C2', s7)
            server_final = call('GET', '/api/v1/notes/n-1')['doc']
            # Welcome: ext-2 推进到 rev3；C1 故障落地 rev4；C2 裁决采纳 rev4 → 提交 rev5
            check('R5-VM-3 server final = C2 at adopted revision',
                  server_final['title'] == 'VM unconfirmed C1 EDITED C2' and server_final['revision'] == 5,
                  server_final)
            # 原样重试幂等（同内容再保存一次）
            click('Save')
            s8 = state()
            check('R5-VM-3 retry idempotent still Saved', s8.get('dirty') == 'false', s8)
            results['r5_vm_3'] = dict(after_fault=s6, after_edit_save=s7, server_final=server_final, after_retry=s8)

            record['negative_results'] = results
            record['fails'] = fails
        else:
            record['error'] = 'mcp not ready'
except Exception as error:
    record['error'] = repr(error)
finally:
    if p is not None:
        if p.poll() is None:
            subprocess.run(['taskkill', '/PID', str(p.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            p.wait(timeout=5)
        except Exception:
            pass
(run / 'vm-negative-result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf8')
fails = record.get('fails', ['script-error'])
print('VM negatives done. fails =', len(fails), fails, flush=True)
print((run / 'boot.log').read_text(encoding='utf8', errors='replace')[-1200:], flush=True)
raise SystemExit(1 if fails else 0)
