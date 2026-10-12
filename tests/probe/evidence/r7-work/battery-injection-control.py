# T-33/F-R7-06 注入失败传播控制：INJECT_CONTROL=1 使注入器故意失败，
# 电池必须因此非零（验证"注入失败被忽略"类别缺陷已关闭）。
# 运行前置：NOTES_TEST_MODE=1 后端已在 BASE（默认 17819）就绪。
import os
import subprocess
import time
from pathlib import Path

root = Path.cwd()
out = root / '.auto' / ('r7-inject-control-' + str(time.time_ns()))
env = dict(os.environ, INJECT_CONTROL='1', PYTHONUTF8='1')
outdir_arg = str(out).replace(os.sep, '/')
result = subprocess.run(['D:/soft/Git/bin/bash.exe', 'tests/probe/run_v1_battery.sh', outdir_arg],
                        cwd=root, env=env, capture_output=True, text=True,
                        timeout=300, encoding='utf8', errors='replace')
out.mkdir(parents=True, exist_ok=True)
log = out / 'battery-control-full.log'
log.write_text(result.stdout, encoding='utf8', errors='replace')
inj_fail = 'S15 injection (mismark) did not execute' in result.stdout
print('battery exit:', result.returncode)
print('injection failure recorded:', inj_fail)
print('evidence:', out)
if result.returncode == 0:
    print('CONTROL FAILED: battery passed despite broken injection')
    raise SystemExit(1)
if not inj_fail:
    print('CONTROL FAILED: battery non-zero but injection failure not the recorded cause')
    raise SystemExit(1)
print('CONTROL PASSED: broken injection -> battery non-zero with cause recorded')
