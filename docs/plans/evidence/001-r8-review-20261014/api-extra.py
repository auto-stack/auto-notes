import os,time,json,sqlite3,shutil
from pathlib import Path
os.environ['R5_WORK']=str(Path.cwd()/('.auto/review001-extra-'+str(time.time_ns())))
exec(compile(Path('tests/probe/evidence/r5-work/verify_backend_scratch.py').read_text(encoding='utf8').split('# ═══ U1/U2:')[0],'server-defs','exec'))
records={}
with Server('metadata-failures') as s:
    created=s.call('POST','/api/v1/notes',{'request_id':'meta-base','title':'确认中文','body':'第一行\n第二行','folder':''})['value']['doc']
    nid=created['note_id'];lid=created['legacy_id']
    for field,method,endpoint,payload in [('pinned','PATCH',f'/api/notes/{lid}/pin',None),('tags_json','PUT',f'/api/notes/{lid}/tags',{'tags':['必须保存']}),('state','DELETE',f'/api/notes/{lid}',None)]:
        c=sqlite3.connect(s.data/'inbox.db');c.execute(f"CREATE TRIGGER reject_meta BEFORE UPDATE OF {field} ON notes BEGIN SELECT RAISE(ABORT,'independent metadata rejection'); END");c.commit();c.close()
        before=s.call('GET',f'/api/v1/notes/{nid}')['value'];result=s.call(method,endpoint,payload);after=s.call('GET',f'/api/v1/notes/{nid}')['value']
        records[field]={'before':before,'result':result,'after':after}
        value=result.get('value');rejected=value is False or value is None or (isinstance(value,dict) and value.get('ok') is False)
        check(f'{field} SQL rejection is reported',rejected,records[field])
        c=sqlite3.connect(s.data/'inbox.db');c.execute('DROP TRIGGER reject_meta');c.commit();c.close()
        control=s.call(method,endpoint,payload);records[field]['normal_control']=control
    restored=s.call('POST',f'/api/v1/notes/{nid}/restore');records['restored']=restored
with Server('fresh-upgrade-finalize') as s:
    c=sqlite3.connect(s.data/'inbox.db');c.execute("DELETE FROM meta WHERE k='upgraded'");c.execute("CREATE TRIGGER reject_upgraded BEFORE INSERT ON meta WHEN NEW.k='upgraded' BEGIN SELECT RAISE(ABORT,'independent finalize rejection'); END");c.commit();c.close()
    temp=copy_wedge(s.data/'incoming')
    for name in ('manifest.json','notes','receipts','journal'):shutil.move(str(temp/name),str(s.data/name))
    first=s.call('GET','/api/v1/notes');second=s.call('GET','/api/v1/notes');st=status(s)
    records['fresh-finalize']={'first':first,'second':second,'status':st,'notes':sql(s.data/'inbox.db','SELECT note_id,revision FROM notes'),'meta':sql(s.data/'inbox.db','SELECT k,v FROM meta')}
    check('fresh upgrade required finalize failure rolls back',sql(s.data/'inbox.db','SELECT COUNT(*) FROM notes')[0][0]==0,records['fresh-finalize'])
(RUN/'extra-results.json').write_text(json.dumps({'records':records,'fails':fails},ensure_ascii=False,indent=2),encoding='utf8')
print('Evidence:',RUN)
raise SystemExit(bool(fails))
