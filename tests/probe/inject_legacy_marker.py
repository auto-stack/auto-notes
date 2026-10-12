#!/usr/bin/env python
"""battery 注入器（T-33/F-R7-06）：把 r4 缺陷库状态可靠写入隔离 SQLite。

用法: python inject_legacy_marker.py <mode> <db_path>
  mode = mismark : S15 —— 实体元数据清零 + upgraded=1 + corrupted_r1 legacy 标记
  mode = marker  : S19b —— 仅 corrupted_r1 legacy 标记

可靠性合同（F-R7-06）：
  * 任何失败（库不存在/表缺失/写入异常/后置校验不过）→ 非零退出；
  * 后置校验直接读回 SQLite 确认标记与状态真实落地；
  * INJECT_CONTROL=1 时故意失败（自检钩子：验证 battery 对注入失败的传播）。
"""
import os
import sqlite3
import sys

MARKER = '["legacy upgrade",[{"index":0,"reason":"entity unreadable"}]]'


def fail(msg):
    print('INJECT-FAIL: ' + msg, file=sys.stderr)
    raise SystemExit(1)


def main():
    if len(sys.argv) != 3:
        fail('usage: inject_legacy_marker.py <mismark|marker> <db_path>')
    mode, db_path = sys.argv[1], sys.argv[2]
    if mode not in ('mismark', 'marker'):
        fail('bad mode: ' + mode)
    if os.environ.get('INJECT_CONTROL') == '1':
        fail('INJECT_CONTROL self-test: deliberate injection failure')
    if not os.path.isfile(db_path):
        fail('db not found: ' + db_path)
    conn = sqlite3.connect(db_path)
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'notes' not in tables or 'meta' not in tables:
            fail('required tables missing: ' + repr(sorted(tables)))
        if mode == 'mismark':
            n = conn.execute("SELECT COUNT(*) FROM notes WHERE note_id='n-1'").fetchone()[0]
            if n != 1:
                fail('expected exactly one n-1 row, got ' + str(n))
            conn.execute("UPDATE notes SET tags_json='[]', pinned=0, state='active', folder='' WHERE note_id='n-1'")
            conn.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('upgraded','1')")
        conn.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('corrupted_r1',?)", (MARKER,))
        conn.commit()
        # 后置校验：读回确认真实落地
        row = conn.execute("SELECT v FROM meta WHERE k='corrupted_r1'").fetchone()
        if row is None or 'legacy upgrade' not in row[0]:
            fail('postcondition failed: corrupted_r1 marker not readable back')
        if mode == 'mismark':
            up = conn.execute("SELECT v FROM meta WHERE k='upgraded'").fetchone()
            tg = conn.execute("SELECT tags_json FROM notes WHERE note_id='n-1'").fetchone()
            if up is None or up[0] != '1':
                fail('postcondition failed: upgraded != 1')
            if tg is None or tg[0] != '[]':
                fail('postcondition failed: entity metadata not zeroed')
        conn.close()
    except sqlite3.Error as e:
        fail('sqlite error: ' + repr(e))
    print('INJECT-OK ' + mode + ' -> ' + db_path)


main()
