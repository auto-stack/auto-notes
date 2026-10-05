from pathlib import Path
import json
import os
import subprocess

ROOT=Path.cwd()
definitions=(ROOT/'docs/plans/evidence/001-r3-recheck-20261005/reproduce.py').read_text(encoding='utf8').split("with Server('protocol') as s:")[0]
namespace={'__file__':str(ROOT/'docs/plans/evidence/001-r3-recheck-20261005/reproduce.py'),'__name__':'battery'}
exec(compile(definitions,'review-definitions','exec'),namespace)
Server=namespace['Server']; create=namespace['create']; RUN=namespace['RUN']
output=RUN/'battery'
assert output.resolve().is_relative_to(ROOT.resolve()) and not (output/'wk').exists()
with Server('battery-backend') as s:
    env=dict(os.environ,BASE=f'http://127.0.0.1:{s.port}',PYTHONIOENCODING='utf-8',PYTHONUTF8='1')
    with open(RUN/'battery.log','wb') as log:
        result=subprocess.run(['D:/soft/Git/bin/bash.exe','tests/probe/run_v1_battery.sh',str(output).replace('\\','/')],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    print('Evidence:',str(RUN)); print('Battery exit:',result.returncode)
    print((RUN/'battery.log').read_text(encoding='utf8',errors='replace')[-1400:])

with Server('process-A') as a:
    create(a)
    with Server('process-B',data=a.data) as b:
        from concurrent.futures import ThreadPoolExecutor
        update=namespace['update']; safe=namespace['safe']
        with ThreadPoolExecutor(max_workers=8) as pool:
            calls=list(pool.map(lambda i:safe(lambda:update(a if i%2==0 else b,'n-1',1,'dual-'+str(i),'writer-'+str(i))),range(8)))
        record=dict(calls=calls,final=a.call('GET','/api/v1/notes/n-1'))
        (RUN/'dual-process.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
        print('Dual process:',sum(r.get('value',{}).get('ok',False) for r in calls),'ok,',sum(r.get('value',{}).get('err_code')=='revision_conflict' for r in calls),'conflict')
