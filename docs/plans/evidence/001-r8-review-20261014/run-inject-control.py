import os,time,subprocess
from pathlib import Path
os.environ['R5_WORK']=str(Path.cwd()/('.auto/review001-inject-control-'+str(time.time_ns())))
exec(compile(Path('tests/probe/evidence/r5-work/verify_backend_scratch.py').read_text(encoding='utf8').split('# ═══ U1/U2:')[0],'server-defs','exec'))
with Server('control-server') as s:
    os.environ['BASE']=f'http://127.0.0.1:{s.port}'
    exec(compile(Path('tests/probe/evidence/r7-work/battery-injection-control.py').read_text(encoding='utf8'),'inject-control','exec'))
