import os, json, sqlite3, shutil
from pathlib import Path
import time
os.environ['R5_WORK'] = str(Path.cwd()/('.auto/review001-r6-20261012/api-combinations-'+str(time.time_ns())))
defs=(Path('tests/probe/evidence/r5-work/verify_backend_scratch.py')).read_text(encoding='utf8').split('# ═══ U1/U2:')[0]
exec(compile(defs,'scratch-defs','exec'))
records={}
def mount(s, patch=None):
    temp=copy_wedge(s.data/'incoming', patch)
    for name in ('manifest.json','notes','receipts','journal'):
        shutil.move(str(temp/name),str(s.data/name))
def snapshot(s):
    return {'notes':sql(s.data/'inbox.db','SELECT note_id,legacy_id,revision,title,tags_json,folder FROM notes'), 'meta':sql(s.data/'inbox.db','SELECT k,v FROM meta ORDER BY k')}
for name,patch in [('valid-control',{}),('manifest-identity',{'legacy_id':'7'}),('manifest-types',{'revision':True,'tags':[7,None],'folder':42,'pinned':1}),('manifest-revision',{'revision':'2oops'})]:
    with Server(name) as s:
        mount(s,patch); before=legacy_hash(s.data)
        r=s.call('GET','/api/v1/notes'); st=status(s); db=snapshot(s)
        records[name]={'patch':patch,'response':r,'status':st,'db':db,'source_unchanged':before==legacy_hash(s.data)}
        if name=='valid-control': check(name,len(db['notes'])==1 and db['notes'][0][2]==2)
        else: check(name+' rejected', len(db['notes'])==0 and bool(st.get('upgrade_error')),records[name])
with Server('repair-update-failure') as s:
    mount(s); s.call('GET','/api/v1/notes')
    c=sqlite3.connect(s.data/'inbox.db')
    c.execute("UPDATE notes SET tags_json='[]',folder='' WHERE note_id='n-1'")
    c.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('corrupted_r1','legacy upgrade incomplete')")
    c.execute("CREATE TRIGGER review_abort BEFORE UPDATE ON notes BEGIN SELECT RAISE(ABORT,'independent repair failure'); END")
    c.commit();c.close()
    m=json.loads((s.data/'manifest.json').read_text());m['entries'][0].update(tags=['authority'],folder='authority-folder');(s.data/'manifest.json').write_text(json.dumps(m))
    before=snapshot(s); r=s.call('GET','/api/v1/notes'); after=snapshot(s)
    records['repair-update-failure']={'before':before,'response':r,'after':after,'status':status(s)}
    check('repair UPDATE failure retains retry credential',any(k=='corrupted_r1' for k,v in after['meta']) and any(k=='upgrade_error' and v for k,v in after['meta']),records['repair-update-failure'])
    c=sqlite3.connect(s.data/'inbox.db');c.execute('DROP TRIGGER review_abort');c.commit();c.close()
    r2=s.call('GET','/api/v1/notes'); final=snapshot(s)
    records['repair-update-failure']['retry']={'response':r2,'db':final}
    check('repair retry restores authority',final['notes'][0][4]=='["authority"]' and final['notes'][0][5]=='authority-folder',final)
(RUN/'combinations.json').write_text(json.dumps({'results':records,'oracle_failures':fails},ensure_ascii=False,indent=2),encoding='utf8')
print('Evidence:',RUN,flush=True)
raise SystemExit(bool(fails))
