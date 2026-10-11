# r5 work 快速验证（T-17/T-18/T-20 后端负例；通过后断言固化进 run_v1_battery.sh）
import hashlib
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path.cwd()
EXE = ROOT / 'rust-workspace/target/debug/app-015-notes-back.exe'
WEDGE = ROOT / 'tests/probe/evidence/v1/wedge-snapshot'
RUN = Path(os.environ.get('R5_WORK', ROOT / '.auto' / ('r5-work-' + str(time.time_ns()))))
RUN.mkdir(parents=True, exist_ok=True)
results = {}
fails = []


def check(name, cond, detail=''):
    tag = 'PASS' if cond else 'FAIL'
    print(f'[{tag}] {name} {detail if not cond else ""}', flush=True)
    if not cond:
        fails.append(name)
    return cond


class Server:
    def __init__(self, name, data=None, **extra):
        self.data = data or RUN / name
        self.data.mkdir(parents=True, exist_ok=True)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        env = dict(os.environ, AUTO_HTTP_PORT=str(self.port), NOTES_DATA_DIR=str(self.data), NOTES_SEED='0', NOTES_TEST_MODE='1')
        for key in ('NOTES_FORCE_LOCK', 'NOTES_FAULT', 'NOTES_LEGACY_FILE', 'NOTES_P2PROBE'):
            env.pop(key, None)
        env.update(extra)
        self.log = open(RUN / (name + '.log'), 'wb')
        self.p = subprocess.Popen([str(EXE)], cwd=ROOT, env=env, stdout=self.log, stderr=self.log,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
        for _ in range(100):
            try:
                self.call('GET', '/api/v1/status')
                break
            except Exception:
                time.sleep(.05)
        else:
            self.close()
            raise RuntimeError('server unavailable')

    def call(self, method, path, payload=None):
        body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
        request = urllib.request.Request(f'http://127.0.0.1:{self.port}{path}', data=body, method=method,
                                         headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                raw = response.read().decode()
                return {'http': response.status, 'value': json.loads(raw) if raw else None}
        except urllib.error.HTTPError as error:
            return {'http': error.code, 'body': error.read().decode()}

    def close(self, kill=False):
        if self.p.poll() is None:
            if kill:
                self.p.kill()
            else:
                self.p.terminate()
        try:
            self.p.wait(timeout=5)
        except Exception:
            self.p.kill()
            self.p.wait(timeout=5)
        self.log.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def copy_wedge(dst, manifest_patch=None):
    dst = Path(dst)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(WEDGE, dst)
    if manifest_patch:
        m = json.loads((WEDGE / 'manifest.json').read_text(encoding='utf8'))
        e = m['entries'][0]
        e.update(manifest_patch)
        (dst / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False), encoding='utf8')
    return dst


def status(s):
    return json.loads(s.call('GET', '/api/v1/status')['value'])


def legacy_hash(data_dir):
    # 只哈希旧树文件本身（manifest/notes/receipts/journal）——升级会在同一
    # 数据目录新增 inbox.db 与 legacy-backup/，那不属于"原件不动"的范围。
    h = hashlib.sha256()
    for name in ('manifest.json', 'notes', 'receipts', 'journal'):
        f = Path(data_dir) / name
        if f.is_file():
            h.update(name.encode())
            h.update(f.read_bytes())
        elif f.is_dir():
            for g in sorted(f.rglob('*')):
                if g.is_file():
                    h.update(str(g.relative_to(f)).encode())
                    h.update(g.read_bytes())
    return h.hexdigest()


def sql(dbpath, q):
    conn = sqlite3.connect(dbpath)
    rows = conn.execute(q).fetchall()
    conn.close()
    return rows


# ═══ U1/U2: wedge 升级 + manifest 权威元数据 ═══
with Server('u1') as s:
    src = copy_wedge(s.data / 'legacy')
    # 旧布局根 = data_dir 本身（manifest.json/notes/receipts 直接在 data 下）
    for item in ('manifest.json', 'notes', 'receipts', 'journal'):
        shutil.move(str(s.data / 'legacy' / item), str(s.data / item))
    shutil.rmtree(s.data / 'legacy')
    before = legacy_hash(s.data)
    lst = s.call('GET', '/api/v1/notes')['value']
    check('U1 wedge upgraded body/rev', len(lst) == 1 and lst[0]['note_id'] == 'n-1' and lst[0]['revision'] == 2
          and lst[0]['title'] == 'doc1-updated' and lst[0]['body'] == 'body two', lst)
    st = status(s)
    check('U1 no upgrade_error', st.get('upgrade_error', 'x') == '', st)
    # U2: manifest-only 权威元数据
with Server('u2') as s:
    src = copy_wedge(s.data / 'legacy')
    for item in ('manifest.json', 'notes', 'receipts', 'journal'):
        shutil.move(str(s.data / 'legacy' / item), str(s.data / item))
    shutil.rmtree(s.data / 'legacy')
    m = json.loads((s.data / 'manifest.json').read_text(encoding='utf8'))
    m['entries'][0].update({'tags': ['saved-tag', 'important'], 'pinned': True, 'folder': 'saved-folder', 'state': 'trashed'})
    (s.data / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False), encoding='utf8')
    before = legacy_hash(s.data)
    got = s.call('GET', '/api/v1/notes/n-1')['value']
    d = got['doc']
    check('U2 manifest metadata authority',
          d['tags'] == ['saved-tag', 'important'] and d['pinned'] is True and d['folder'] == 'saved-folder'
          and d['state'] == 'trashed' and d['revision'] == 2, d)
    active = s.call('GET', '/api/v1/notes')['value']
    check('U2 trashed not resurrected in active list', active == [], active)
    # receipts 导入：d-2（update rev2）复用于 create 必须拒绝；复用于 update 也拒绝
    r1 = s.call('POST', '/api/v1/notes', dict(request_id='d-2', title='new', body='x', folder=''))
    check('U7 legacy update receipt reused for create rejected',
          r1['value']['ok'] is False and r1['value']['err_code'] == 'request_conflict', r1)
    n_after = s.call('GET', '/api/v1/notes')['value']
    check('U7 no note created by rejected replay', n_after == [], n_after)
    r2 = s.call('PUT', '/api/v1/notes/n-1', dict(expected_revision=2, request_id='d-2', title='T', body='B'))
    check('U7 legacy row update reuse also rejected (intent unverifiable)',
          r2['value']['ok'] is False and r2['value']['err_code'] == 'request_conflict', r2)
    d2 = s.call('GET', '/api/v1/notes/n-1')['value']['doc']
    check('U7 legacy object untouched', d2['title'] == 'doc1-updated' and d2['revision'] == 2, d2)
    rc = s.call('GET', '/api/v1/notes/n-1')  # read_receipt 无直接端点；对象保留已验
    # U6: 源 hash + 备份 + 幂等（重启后数据一致、无重复）
    src_after = legacy_hash(s.data)
    check('U6 legacy source untouched by upgrade', before == src_after, (before[:12], src_after[:12]))
    bak = s.data / 'legacy-backup'
    check('U6 backup manifest exists', (bak / 'manifest.json').exists())
    rows = sql(s.data / 'inbox.db', 'SELECT intent, rev, kind FROM requests ORDER BY request_id')
    check('U6 legacy request rows intent empty (unverifiable)',
          all(r[0] == '' for r in rows) and len(rows) == 2, rows)

with Server('u2-restart', data=RUN / 'u2') as s:
    got = s.call('GET', '/api/v1/notes/n-1')['value']['doc']
    check('U6 hard-restart metadata survives',
          got['tags'] == ['saved-tag', 'important'] and got['pinned'] is True and got['folder'] == 'saved-folder'
          and got['state'] == 'trashed' and got['revision'] == 2, got)
    rows = sql(RUN / 'u2' / 'inbox.db', 'SELECT COUNT(*) FROM notes')
    check('U6 no duplicate notes after retry', rows[0][0] == 1, rows)

# ═══ U3: 备份位置为普通文件 → 显式失败，不完成；清除后重试成功 ═══
with Server('u3') as s:
    src = copy_wedge(s.data / 'legacy')
    for item in ('manifest.json', 'notes', 'receipts', 'journal'):
        shutil.move(str(s.data / 'legacy' / item), str(s.data / item))
    shutil.rmtree(s.data / 'legacy')
    (s.data / 'legacy-backup').write_text('not a directory', encoding='utf8')
    lst = s.call('GET', '/api/v1/notes')['value']
    st = status(s)
    check('U3 backup blocked -> no silent success', lst == [] and st.get('upgrade_error', '') != '', (lst, st))
    (s.data / 'legacy-backup').unlink()
    lst2 = s.call('GET', '/api/v1/notes')['value']
    check('U3 retry after unblocking succeeds', len(lst2) == 1 and lst2[0]['note_id'] == 'n-1', lst2)

# ═══ U4: 唯一实体缺失 → 显式失败；补回后重试成功 ═══
with Server('u4') as s:
    src = copy_wedge(s.data / 'legacy')
    for item in ('manifest.json', 'notes', 'receipts', 'journal'):
        shutil.move(str(s.data / 'legacy' / item), str(s.data / item))
    shutil.rmtree(s.data / 'legacy')
    (s.data / 'notes' / 'n-1.r2.json').unlink()
    lst = s.call('GET', '/api/v1/notes')['value']
    st = status(s)
    check('U4 missing entity -> explicit failure', lst == [] and 'entity missing' in st.get('upgrade_error', ''), (lst, st))
    shutil.copy(WEDGE / 'notes' / 'n-1.r2.json', s.data / 'notes' / 'n-1.r2.json')
    lst2 = s.call('GET', '/api/v1/notes')['value']
    check('U4 retry after restoring entity succeeds', len(lst2) == 1 and lst2[0]['note_id'] == 'n-1', lst2)

# ═══ U5: manifest={} → 显式错误，不是空成功 ═══
with Server('u5') as s:
    (s.data / 'manifest.json').write_text('{}', encoding='utf8')
    (s.data / 'notes').mkdir(exist_ok=True)
    shutil.copy(WEDGE / 'notes' / 'n-1.r2.json', s.data / 'notes' / 'n-1.r2.json')
    lst = s.call('GET', '/api/v1/notes')['value']
    st = status(s)
    check('U5 manifest {} rejected explicitly', lst == [] and 'entries' in st.get('upgrade_error', ''), (lst, st))

# ═══ U8: r4 误写 upgraded 标记的缺陷库 → 安全恢复重跑（元数据回收） ═══
with Server('u8') as s:
    src = copy_wedge(s.data / 'legacy')
    for item in ('manifest.json', 'notes', 'receipts', 'journal'):
        shutil.move(str(s.data / 'legacy' / item), str(s.data / item))
    shutil.rmtree(s.data / 'legacy')
    m = json.loads((s.data / 'manifest.json').read_text(encoding='utf8'))
    m['entries'][0].update({'tags': ['must-survive'], 'pinned': True, 'folder': 'keep', 'state': 'archived'})
    (s.data / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False), encoding='utf8')
    # 模拟 r4 缺陷库：实体元数据直接进库 + upgraded=1 + legacy corrupted_r1
    conn = sqlite3.connect(s.data / 'inbox.db')
    conn.execute("UPDATE notes SET tags_json='[]', pinned=0, state='active', folder='' WHERE note_id='n-1'")
    conn.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('upgraded','1')")
    conn.execute('INSERT OR REPLACE INTO meta(k,v) VALUES(\'corrupted_r1\',\'["legacy upgrade",[{"index":0}]]\')')
    conn.commit()
    conn.close()
    lst = s.call('GET', '/api/v1/notes')['value']
    st = status(s)
    check('U8 mis-marked DB repaired on open', st.get('upgrade_error', 'x') == '', st)
    got = s.call('GET', '/api/v1/notes/n-1')['value']['doc']
    check('U8 authority metadata recovered', got['tags'] == ['must-survive'] and got['pinned'] is True
          and got['folder'] == 'keep' and got['state'] == 'archived', got)

# ═══ R1: 管道歧义意图必须冲突 ═══
with Server('r1') as s:
    a = s.call('POST', '/api/v1/notes', dict(request_id='rid-pipe', title='a|b', body='c', folder=''))
    check('R1 create a|b/c ok', a['value']['ok'] is True, a)
    b = s.call('PUT', '/api/v1/notes/n-1', dict(expected_revision=1, request_id='rid-pipe', title='a', body='b|c'))
    check('R1 delimiter intent differs -> request_conflict (not replayed ok)',
          b['value']['ok'] is False and b['value']['err_code'] == 'request_conflict', b)
    d = s.call('GET', '/api/v1/notes/n-1')['value']['doc']
    check('R1 second intent not executed', d['title'] == 'a|b' and d['body'] == 'c' and d['revision'] == 1, d)
    # 同内容原样重试仍幂等
    c = s.call('POST', '/api/v1/notes', dict(request_id='rid-pipe', title='a|b', body='c', folder=''))
    check('R1 identical retry replays', c['value']['ok'] is True and c['value'].get('replayed') is True, c)

# ═══ R2: v2 管道行版本化迁移（模拟 r4 库）═══
with Server('r2') as s:
    c1 = s.call('POST', '/api/v1/notes', dict(request_id='mig-c', title='M1', body='b1', folder='fw'))
    u1 = s.call('PUT', '/api/v1/notes/n-1', dict(expected_revision=1, request_id='mig-u', title='M2', body='b2'))
    check('R2 setup create/update ok', c1['value']['ok'] and u1['value']['ok'], (c1, u1))
    doc_json = json.dumps(u1['value']['doc'], ensure_ascii=False)
    conn = sqlite3.connect(s.data / 'inbox.db')
    # 降级模拟 r4 行：管道意图 + rev=2 + doc 快照
    conn.execute("UPDATE requests SET intent=? WHERE request_id='mig-u'",
                 ('update|n-1|1|M2|b2',))
    conn.execute("UPDATE meta SET v='2' WHERE k='schema_v'")
    conn.commit()
    conn.close()
with Server('r2-restart', data=RUN / 'r2') as s:
    rp = s.call('PUT', '/api/v1/notes/n-1', dict(expected_revision=1, request_id='mig-u', title='M2', body='b2'))
    check('R2 migrated pipe row replays original receipt rev2',
          rp['value']['ok'] is True and rp['value'].get('replayed') is True
          and rp['value']['receipt']['revision'] == 2, rp)
    rx = s.call('PUT', '/api/v1/notes/n-1', dict(expected_revision=1, request_id='mig-u', title='M2', body='CHANGED'))
    check('R2 migrated row different content -> conflict', rx['value']['ok'] is False
          and rx['value']['err_code'] == 'request_conflict', rx)

# ═══ R3: 旧三列请求行（无 rev）不得假成功/编造 rev1 ═══
with Server('r3') as s:
    conn = sqlite3.connect(s.data / 'inbox.db')
    conn.execute("INSERT INTO requests(request_id, note_id, kind, rev, doc_json, intent) VALUES('old3', 'n-1', 'update', 0, '', '')")
    conn.execute("INSERT INTO notes(note_id, legacy_id, revision, title, body, tags_json, color, pinned, state, folder, seq, created_at, updated_at) VALUES('n-1', 1, 3, 't3', 'b3', '[]', '', 0, 'active', '', 1, '', '')")
    conn.commit()
    conn.close()
    r = s.call('PUT', '/api/v1/notes/n-1', dict(expected_revision=3, request_id='old3', title='x', body='y'))
    check('R3 legacy 3-col row replay rejected (no fabricated receipt)',
          r['value']['ok'] is False and r['value']['err_code'] == 'request_conflict', r)
    d = s.call('GET', '/api/v1/notes/n-1')['value']['doc']
    check('R3 row untouched', d['title'] == 't3' and d['revision'] == 3, d)

# ═══ M1: 严格迁移类型（T-20/SD-15）═══
with Server('m1') as s:
    legacy = s.data / 'notes-m1.json'
    s.call('POST', '/api/v1/test/setup', dict(data_dir=str(s.data), legacy_file=str(legacy)))
    items = [
        {'id': 0, 'title': 'valid-0', 'body': 'ok', 'folder': '', 'pinned': False, 'tags': []},
        {'id': True, 'title': 'bool-id', 'body': 'x', 'tags': []},
        {'id': 5, 'title': 'obj-body', 'body': {'text': 'nested'}, 'tags': []},
        {'id': 6, 'title': 'bad-tags', 'body': 'x', 'tags': [7, None]},
        {'id': 9, 'title': '合法中文项：多行\n与 emoji 🎉', 'body': '正文保持', 'folder': '', 'pinned': False, 'tags': ['中文']},
    ]
    legacy.write_text(json.dumps(items, ensure_ascii=False), encoding='utf8')
    mig = s.call('POST', '/api/v1/migrate')['value']
    check('M1 migrated=2 (valid-0 + chinese), corrupted=3',
          mig['migrated'] == 2 and len(mig['corrupted']) == 3, mig)
    reasons = sorted(c['reason'] for c in mig['corrupted'])
    check('M1 reasons strict', reasons == ['bool id -> id not an integer', 'body not a string', 'tags element not a string']
          or reasons == ['body not a string', 'id not an integer', 'tags element not a string'], reasons)
    check('M1 snippet is string for every corrupted item',
          all(isinstance(c['snippet'], str) for c in mig['corrupted']),
          [type(c['snippet']).__name__ for c in mig['corrupted']])
    lst = s.call('GET', '/api/v1/notes')['value']
    check('M1 later valid chinese item migrated', any('合法中文项' in n['title'] for n in lst), lst)
    rep = json.loads((s.data / 'corrupted' / 'report-r1.json').read_text(encoding='utf8'))
    check('M1 persisted report snippet strings', all(isinstance(c['snippet'], str) for c in rep['corrupted']), rep)
    src_h = hashlib.sha256(legacy.read_bytes()).hexdigest()
    bak_h = hashlib.sha256((s.data / 'backup' / 'notes.json.bak').read_bytes()).hexdigest()
    check('M1 source untouched + backup equal', src_h == bak_h)
    mig2 = s.call('POST', '/api/v1/migrate')['value']
    check('M1 retry idempotent', mig2['skipped_existing'] is True, mig2)

# ═══ U9/U10 (r6/T-23): entity path safety + identity mismatch ═══
with Server('u9') as s:
    (s.data / 'manifest.json').write_text(json.dumps({
        'schema_version': 1, 'counter': 3,
        'entries': [{'note_id': 'n-9', 'revision': '2', 'file': '../escape.json', 'state': 'active',
                     'folder': '', 'tags': [], 'pinned': False, 'seq': '9', 'legacy_id': '9'}],
    }), encoding='utf8')
    (s.data / 'notes').mkdir(exist_ok=True)
    shutil.copy(WEDGE / 'notes' / 'n-1.r2.json', s.data / 'notes' / 'escape.json')
    lst = s.call('GET', '/api/v1/notes')['value']
    st = status(s)
    check('U9 path-unsafe fid rejected', lst == [] and 'path unsafe' in st.get('upgrade_error', ''), (lst, st))

with Server('u10') as s:
    (s.data / 'manifest.json').write_text(json.dumps({
        'schema_version': 1, 'counter': 3,
        'entries': [{'note_id': 'n-9', 'revision': '2', 'file': 'n-1.r2.json', 'state': 'active',
                     'folder': '', 'tags': [], 'pinned': False, 'seq': '9', 'legacy_id': '9'}],
    }), encoding='utf8')
    (s.data / 'notes').mkdir(exist_ok=True)
    shutil.copy(WEDGE / 'notes' / 'n-1.r2.json', s.data / 'notes' / 'n-1.r2.json')
    lst = s.call('GET', '/api/v1/notes')['value']
    st = status(s)
    check('U10 identity mismatch rejected', lst == [] and 'does not match' in st.get('upgrade_error', ''), (lst, st))

print()
print('R5 backend verify done. fails =', len(fails), fails)
results_summary = {'fails': fails, 'run': str(RUN)}
(RUN / 'scratch-summary.json').write_text(json.dumps(results_summary, ensure_ascii=False, indent=2), encoding='utf8')
raise SystemExit(1 if fails else 0)
