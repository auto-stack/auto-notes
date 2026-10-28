import os,time,json,sqlite3,shutil
from pathlib import Path
os.environ['R5_WORK']=str(Path.cwd()/('.auto/review001-20261015-api-'+str(time.time_ns())))
exec(compile(Path('tests/probe/evidence/r5-work/verify_backend_scratch.py').read_text(encoding='utf8').split('# ═══ U1/U2:')[0],'server-defs','exec'))
records={}
for key in ['upgraded','upgrade_error','corrupted_r1']:
    with Server('fresh-'+key) as s:
        c=sqlite3.connect(s.data/'inbox.db');c.execute("DELETE FROM meta WHERE k='upgraded'");c.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('corrupted_r1','legacy upgrade incomplete')")
        trigger=("BEFORE DELETE ON meta WHEN OLD.k='corrupted_r1'" if key=='corrupted_r1' else "BEFORE INSERT ON meta WHEN NEW.k='"+key+"'")
        c.execute("CREATE TRIGGER reject_final "+trigger+" BEGIN SELECT RAISE(ABORT,'r9 finalize rejection'); END");c.commit();c.close()
        temp=copy_wedge(s.data/'incoming')
        for name in ('manifest.json','notes','receipts','journal'):shutil.move(str(temp/name),str(s.data/name))
        first=s.call('GET','/api/v1/notes');state=dict(sql(s.data/'inbox.db','SELECT k,v FROM meta'));n=sql(s.data/'inbox.db','SELECT COUNT(*) FROM notes')[0][0]
        records['fresh-'+key]={'first':first,'meta':state,'count':n}
        check('fresh '+key+' rejection rolls back notes and credential',n==0 and bool(state.get('corrupted_r1')) and state.get('upgraded')!='1',records['fresh-'+key])
        c=sqlite3.connect(s.data/'inbox.db');c.execute('DROP TRIGGER reject_final');c.commit();c.close();retry=s.call('GET','/api/v1/notes');records['fresh-'+key]['retry']=retry
        check('fresh '+key+' retry succeeds',len(retry['value'])==1 and retry['value'][0]['revision']==2,retry)
with Server('no-legacy-finalize') as s:
    def snapshot():return dict(sql(s.data/'inbox.db','SELECT k,v FROM meta'))
    c=sqlite3.connect(s.data/'inbox.db');c.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('upgraded','1')");c.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('corrupted_r1','legacy upgrade incomplete')");c.execute("DELETE FROM meta WHERE k='repair_generation'");c.execute("CREATE TRIGGER reject_generation BEFORE INSERT ON meta WHEN NEW.k='repair_generation' BEGIN SELECT RAISE(ABORT,'r9 generation rejection'); END");c.commit();c.close()
    records['before']=snapshot();first=s.call('GET','/api/v1/notes');records['after_failure']={'response':first,'meta':snapshot()}
    check('no-legacy finalize failure keeps retry credential',bool(records['after_failure']['meta'].get('corrupted_r1')),records['after_failure'])
    c=sqlite3.connect(s.data/'inbox.db');c.execute('DROP TRIGGER reject_generation');c.commit();c.close()
    retry=s.call('GET','/api/v1/notes');records['after_retry']={'response':retry,'meta':snapshot()}
    check('no-legacy finalize retry completes generation',records['after_retry']['meta'].get('repair_generation')=='1' and not records['after_retry']['meta'].get('corrupted_r1'),records['after_retry'])
    c=sqlite3.connect(s.data/'inbox.db');c.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('corrupted_r1','legacy upgrade incomplete')");c.commit();c.close()
    control=s.call('GET','/api/v1/notes');records['normal_control']={'response':control,'meta':snapshot()}
    check('no-legacy finalize normal control completes generation',records['normal_control']['meta'].get('repair_generation')=='1' and not records['normal_control']['meta'].get('corrupted_r1'),records['normal_control'])
(RUN/'new-api-results.json').write_text(json.dumps({'records':records,'failures':fails},ensure_ascii=False,indent=2),encoding='utf8');print('Evidence:',RUN)
raise SystemExit(bool(fails))
