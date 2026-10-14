import os,time,json,subprocess
from pathlib import Path
os.environ['R5_WORK']=str(Path.cwd()/('.auto/review001-battery-'+str(time.time_ns())))
exec(compile(Path('tests/probe/evidence/r5-work/verify_backend_scratch.py').read_text(encoding='utf8').split('# ═══ U1/U2:')[0],'server-defs','exec'))
with Server('battery-server') as s:
    env=dict(os.environ,BASE=f'http://127.0.0.1:{s.port}',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    with open(RUN/'battery.log','wb') as log:
        r=subprocess.run(['C:/Program Files/Git/bin/bash.exe','tests/probe/run_v1_battery.sh',str(RUN/'battery').replace('\\','/')],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240)
    record={'exit_code':r.returncode,'run':str(RUN)}
    (RUN/'receipt.json').write_text(json.dumps(record,indent=2),encoding='utf8')
    print('Evidence:',RUN);print((RUN/'battery.log').read_text(encoding='utf8')[-1700:])
raise SystemExit(r.returncode)
