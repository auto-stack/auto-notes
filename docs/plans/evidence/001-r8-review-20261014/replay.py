import os, sys, shutil
from pathlib import Path

os.environ['PYTHONUTF8']='1'
os.environ['PYTHONIOENCODING']='utf-8'
def normalize(source):
    return source.replace('app-015-notes-back.exe','auto-notes-back.exe').replace('D:/soft/nodejs/node.exe',shutil.which('node').replace('\\','/')).replace('D:/soft/Git/bin/bash.exe','C:/Program Files/Git/bin/bash.exe')
original_read=Path.read_text
def read(self,*args,**kwargs):
    value=original_read(self,*args,**kwargs)
    return normalize(value) if self.suffix=='.py' else value
Path.read_text=read
source=normalize(Path(sys.argv[1]).read_text(encoding='utf-8'))
if len(sys.argv)>2:
    source=source.replace('docs/plans/evidence/001-r6-recheck-20261012/independent-ui.cjs',sys.argv[2])
exec(compile(source,sys.argv[1],'exec'))
