# r7 work：VM/MCP 新反例（T-30/31/32 的 VM 共享路径）
# R7-VM-1 连续未知链（C2 真已提交变体）：C1 fault 提交丢响应 → C2 fault 提交丢
#          响应 → C3 保存经链式裁决（server==prev）落地
# R7-VM-2 恢复目标不在工作集时 Pin 绑定草稿身份（不钉另一行）
# R7-VM-3 满槽阻止搜索：查询词/工作集/草稿原位不变
# 说明：C2"到后端前失败"变体是 Vue route.abort 专属（独立 UI 覆盖）；VM 用
#       after_manifest 表达"提交但响应未知"的链上节点。
from pathlib import Path
import os, json, socket, subprocess, time, urllib.request

root = Path.cwd()
run = root / '.auto' / ('r7-vm-' + str(time.time_ns()))
run.mkdir(parents=True)

def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0)); return s.getsockname()[1]

mcp, back = port(), port()
env = dict(os.environ, NOTES_DATA_DIR=str(run / 'data'), NOTES_SEED='1', NOTES_TEST_MODE='1',
           AUTOUI_MCP_PORT=str(mcp), PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
for key in ['NOTES_FAULT', 'NOTES_FORCE_LOCK', 'NOTES_LEGACY_FILE', 'AUTO_HTTP_PROXY']:
    env.pop(key, None)
cmd = ['D:/autostack/auto-lang/target/debug/auto.exe', 'run', '-r', 'vm', '-B', str(back)]
record = {'command': cmd, 'mcp_port': mcp, 'backend_port': back, 'run_dir': str(run)}
print('Evidence:', run, flush=True)

results = {}
fails = []
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
                raw = adapter._call('autoui_state', fields=['draft_title', 'draft_revision', 'draft_id', 'dirty',
                                                            'conflict', 'has_recovery', 'rec_title', 'has_recovery2',
                                                            'rec2_title', 'stash_blocked', 'search', 'has_pend',
                                                            'pend_title', 'pend_revision', 'has_prev', 'prev_title',
                                                            'has_prev2', 'prev2_title', 'draft_request_id'])
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

            def click_until(label, cond_fn, attempts=8):
                # 重渲染后 vnode 换代，单次点击可能落在旧代上不分发——
                # 点击直至条件生效（标准 UI 自动化重试；not-found 吞掉重试）。
                last = None
                for _ in range(attempts):
                    try:
                        click(label)
                    except RuntimeError as e:
                        last = e
                        time.sleep(0.5)
                        continue
                    time.sleep(0.5)
                    if cond_fn(state()):
                        return
                raise RuntimeError(f'click_until exhausted: {label} ({last})')

            def wait_clean(timeout_s=12):
                st = {}
                for _ in range(int(timeout_s / 0.25)):
                    st = state()
                    if st.get('dirty') == 'false':
                        return st
                    time.sleep(0.25)
                return st

            def call(method, path, data=None):
                raw = json.dumps(data).encode() if data is not None else None
                req = urllib.request.Request(f'http://127.0.0.1:{back}' + path, data=raw, method=method,
                                             headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    return json.loads(response.read())

            def check(name, cond, detail=''):
                print(('[PASS] ' if cond else '[FAIL] ') + name, '' if cond else detail, flush=True)
                if not cond:
                    fails.append(name)

            def create_probe(title):
                return call('POST', '/api/v1/notes', dict(request_id='r7-create-' + title, title=title,
                                                          body='base', folder=''))

            def search_select_retry(title, attempts=4):
                for _ in range(attempts):
                    adapter._exec_when(Step('when', 'type_text', dict(label='Search notes', value=title, kind='input'), title))
                    time.sleep(0.6)
                    ex = adapter._call('autoui_exists', kind='button', label=title)
                    if 'FOUND' in ex:
                        click(title)
                        time.sleep(0.5)
                        return
                raise RuntimeError('search_select_retry: ' + title + ' not found')

            def search_select(title):
                # 搜索定位并保留过滤（清过滤会全量刷新+LoadDraft 重置回首行——
                # F-R7-04 驱动版教训）；同时承担工作集刷新（API 建号后可见）。
                adapter._exec_when(Step('when', 'type_text', dict(label='Search notes', value=title, kind='input'), title))
                time.sleep(0.6)
                click(title)
                time.sleep(0.5)

            # ── R7-VM-1: 连续未知链（C2 真已提交变体）──────────────────────
            search_select('Welcome')
            call('POST', '/api/v1/test/fault', dict(stage='after_manifest'))
            edit('Chain-C1')
            click('Save')
            s1 = state()
            pass
            call('POST', '/api/v1/test/fault', dict(stage='off'))
            server_c1 = call('GET', '/api/v1/notes/n-1')['doc']
            check('R7-VM-1 C1 fault-committed (chain node 1)',
                  server_c1['title'] == 'Chain-C1' and server_c1['revision'] == 2, server_c1)
            call('POST', '/api/v1/test/fault', dict(stage='after_manifest'))
            edit('Chain-C2')
            click('Save')
            call('POST', '/api/v1/test/fault', dict(stage='off'))
            server_c2 = call('GET', '/api/v1/notes/n-1')['doc']
            check('R7-VM-1 C2 actually committed (chain node 2)',
                  server_c2['title'] == 'Chain-C2' and server_c2['revision'] == 3, server_c2)
            edit('Chain-C3')
            click('Save')
            s3 = wait_clean()
            # 落地以服务端为准；编辑器此时显示的是过滤视图中的可见行（驱动
            # 保留了 'Welcome' 过滤），草稿字段不作为断言对象。
            check('R7-VM-1 chain adjudication lands C3', s3.get('dirty') == 'false', s3)
            server_c3 = call('GET', '/api/v1/notes/n-1')['doc']
            check('R7-VM-1 server final = C3', server_c3['title'] == 'Chain-C3' and server_c3['revision'] == 4,
                  server_c3)
            results['r7_vm_1'] = dict(s1=s1, s3=s3, server_c2=server_c2, server_c3=server_c3)

            # ── R7-VM-2: 恢复目标不在工作集时 Pin 绑定草稿身份 ─────────────
            # 编排与已验证的独立 UI 场景一致：C1 fault 提交丢响应 → C2 编辑 →
            # 导航 flush（fault 仍开）C2 故障提交+裁决失败入槽 → fault off →
            # 过滤使 R 不在工作集 → Recover → Pin 走同意图重放（ok）→ 钉 R。
            pr = create_probe('R7Recover-R')
            pz = create_probe('R7Only-Z')
            adapter._exec_when(Step('when', 'type_text', dict(label='Search notes', value='R7Recover', kind='input'), 'R7Recover'))
            time.sleep(0.6)
            click('R7Recover-R')
            time.sleep(0.5)
            call('POST', '/api/v1/test/fault', dict(stage='after_manifest'))
            edit('R7R-C1')
            click('Save')
            call('POST', '/api/v1/test/fault', dict(stage='off'))
            sr1 = call('GET', '/api/v1/notes/' + pr['doc']['note_id'])['doc']
            check('R7-VM-2 R C1 landed', sr1['title'] == 'R7R-C1', sr1)
            edit('R7R-C2')
            call('POST', '/api/v1/test/fault', dict(stage='after_manifest'))
            # 清过滤触发导航 flush：C2 故障提交 + 裁决失败入槽，回到全量列表
            adapter._exec_when(Step('when', 'type_text', dict(label='Search notes', value='', kind='input'), ''))
            time.sleep(0.8)
            call('POST', '/api/v1/test/fault', dict(stage='off'))
            sr2 = call('GET', '/api/v1/notes/' + pr['doc']['note_id'])['doc']
            check('R7-VM-2 C2 fault-committed on nav (stashed with context)',
                  sr2['title'] == 'R7R-C2', sr2)
            adapter._exec_when(Step('when', 'type_text', dict(label='Search notes', value='R7Only-Z', kind='input'), 'R7Only-Z'))
            time.sleep(0.6)
            # 搜索重渲染后 vnode 换代——诊断存在性并重试点击至生效
            ex = adapter._call('autoui_exists', kind='button', label='Recover')
            print('DEBUG Recover exists:', ex.strip()[:60], flush=True)
            s_rec = state()
            for _ in range(6):
                click('Recover')
                time.sleep(0.5)
                s_rec = state()
                if s_rec.get('dirty') == 'true':
                    break
            check('R7-VM-2 recover loads R draft outside working set',
                  s_rec.get('draft_title') == 'R7R-C2' and s_rec.get('dirty') == 'true'
                  and s_rec.get('draft_id') == str(pr['doc']['legacy_id']), s_rec)
            click('Pin note')
            s_pin = wait_clean()
            r_after = call('GET', '/api/v1/notes/' + pr['doc']['note_id'])['doc']
            z_after = call('GET', '/api/v1/notes/' + pz['doc']['note_id'])['doc']
            check('R7-VM-2 pin bound to recovered draft identity',
                  r_after['pinned'] is True and z_after['pinned'] is False,
                  dict(R=r_after['pinned'], Z=z_after['pinned'], s_pin=s_pin))
            results['r7_vm_2'] = dict(s_rec=s_rec, s_pin=s_pin, R=r_after, Z=z_after)

            # ── R7-VM-3: 满槽阻止搜索原位不变（独立会话：boot 未过滤列表）──
            record['negative_results'] = results
            record['fails'] = fails
        # 会话 1 结束；会话 2 用同一数据目录全新 boot（搜索态归零，列表未过滤）
        if p.poll() is None:
            subprocess.run(['taskkill', '/PID', str(p.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            p.wait(timeout=5)
        with open(run / 'boot2.log', 'wb') as log2:
            p = subprocess.Popen(cmd, cwd=root, env=env, stdout=log2, stderr=log2,
                                 creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
        ready2 = False
        for i in range(90):
            if p.poll() is not None:
                break
            try:
                data = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list', 'params': {}}).encode()
                req = urllib.request.Request(f'http://127.0.0.1:{mcp}/mcp', data=data,
                                             headers={'Content-Type': 'application/json', 'Connection': 'close'})
                with urllib.request.urlopen(req, timeout=1):
                    pass
                ready2 = True
                break
            except Exception:
                time.sleep(1)
        assert ready2, 'session 2 boot failed'
        import sys
        sys.path.insert(0, str(root / 'tests'))
        from autotest import McpAdapter, Step
        adapter = McpAdapter(mode='vm', url=f'http://127.0.0.1:{mcp}/mcp')
        assert adapter.wait_ready(timeout=30)

        def click(label):
            adapter._exec_when(Step('when', 'click_button', dict(label=label), label))

        def edit(value):
            adapter._exec_when(Step('when', 'type_text', dict(label='Untitled', value=value, kind='input'), value))

        def state2():
            raw = adapter._call('autoui_state', fields=['draft_title', 'dirty', 'conflict', 'has_recovery',
                                                        'rec_title', 'has_recovery2', 'rec2_title',
                                                        'stash_blocked', 'search'])
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

        def call2(method, path, data=None):
            raw = json.dumps(data).encode() if data is not None else None
            req = urllib.request.Request(f'http://127.0.0.1:{back}' + path, data=raw, method=method,
                                         headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read())

        def check(name, cond, detail=''):
            print(('[PASS] ' if cond else '[FAIL] ') + name, '' if cond else detail, flush=True)
            if not cond:
                fails.append(name)

        doc = call2('GET', '/api/v1/notes/n-1')['doc']
        call2('PUT', '/api/v1/notes/n-1', dict(expected_revision=doc['revision'], title='Full-A-ext',
                                              body='e', request_id='r7vm-fa'))
        click('Chain-C3')  # 会话 1 已把 n-1 改名为 Chain-C3
        edit('Full-slot-A')
        click('Save')
        s_a = state2()
        check('R7-VM-3 A conflict kept', s_a.get('dirty') == 'true', s_a)
        click('Shopping List')
        doc3 = call2('GET', '/api/v1/notes/n-3')['doc']
        call2('PUT', '/api/v1/notes/n-3', dict(expected_revision=doc3['revision'], title='Full-B-ext',
                                              body='e', request_id='r7vm-fb'))
        edit('Full-slot-B')
        click('Save')
        click('Quick Ideas')
        doc2 = call2('GET', '/api/v1/notes/n-2')['doc']
        call2('PUT', '/api/v1/notes/n-2', dict(expected_revision=doc2['revision'], title='Full-C-ext',
                                              body='e', request_id='r7vm-fc'))
        edit('Full-slot-C')
        s8 = state2()
        check('R7-VM-3 slots full + C dirty precondition',
              s8.get('has_recovery') == 'true' and s8.get('has_recovery2') == 'true'
              and s8.get('dirty') == 'true' and s8.get('draft_title') == 'Full-slot-C', s8)
        adapter._exec_when(Step('when', 'type_text', dict(label='Search notes', value='NeverMatch', kind='input'), 'NeverMatch'))
        time.sleep(0.8)
        s9 = state2()
        check('R7-VM-3 blocked search leaves search word unchanged',
              s9.get('search') == '' and s9.get('draft_title') == 'Full-slot-C'
              and s9.get('dirty') == 'true' and s9.get('stash_blocked') == 'true', s9)
        results['r7_vm_3'] = dict(s8=s8, s9=s9)
except Exception as error:
    record['error'] = repr(error)
    fails.append('script-error')
finally:
    if p is not None:
        if p.poll() is None:
            subprocess.run(['taskkill', '/PID', str(p.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            p.wait(timeout=5)
        except Exception:
            pass
record['fails'] = fails
(run / 'vm-negative-r7-result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf8')
print('R7 VM negatives done. fails =', len(fails), fails, flush=True)
raise SystemExit(1 if fails else 0)
