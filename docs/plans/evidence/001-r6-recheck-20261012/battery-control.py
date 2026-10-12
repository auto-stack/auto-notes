import os,time,json,subprocess,hashlib
from pathlib import Path
os.environ['R5_WORK']=str(Path.cwd()/('.auto/review001-r6-20261012/battery-control-'+str(time.time_ns())))
exec(compile(Path('tests/probe/evidence/r5-work/verify_backend_scratch.py').read_text(encoding='utf8').split('# ═══ U1/U2:')[0],'server-defs','exec'))
original=Path('tests/probe/run_v1_battery.sh').read_text(encoding='utf8')
old="assert rows==[('已确认的新数据', 1)], rows"
assert original.count(old)==1
mutated=original.replace(old,"assert False, 'independent deliberately failing S19a control'")
script=RUN/'failing-battery.sh';script.write_text(mutated,encoding='utf8',newline='\n')
with Server('control') as s:
    env=dict(os.environ,BASE=f'http://127.0.0.1:{s.port}',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    with open(RUN/'battery-control.log','wb') as log:
        r=subprocess.run(['D:/soft/Git/bin/bash.exe',str(script),str(RUN/'battery')],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=130)
    record={'actual_exit':r.returncode,'expected_exit':1,'mutation':old+' -> assert False (only S19a)','original_sha256':hashlib.sha256(original.encode()).hexdigest(),'mutated_sha256':hashlib.sha256(mutated.encode()).hexdigest(),'failure_file':(RUN/'battery/.fails').read_text(encoding='utf8'),'pass':r.returncode==1}
    (RUN/'control.json').write_text(json.dumps(record,indent=2),encoding='utf8')
    print('Evidence:',RUN);print(json.dumps(record))
raise SystemExit(not record['pass'])
