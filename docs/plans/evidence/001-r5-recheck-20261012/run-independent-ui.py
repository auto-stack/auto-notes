from pathlib import Path
ROOT=Path.cwd()
source=(ROOT/'tests/probe/evidence/r5-work/run_vue_suite.py').read_text(encoding='utf8')
source=source.replace("str(root / 'tests/node_modules/@playwright/test/cli.js'), 'test'", "str(root / 'docs/plans/evidence/001-r5-recheck-20261012/independent-ui.cjs')")
exec(compile(source,'isolated-vue-runner','exec'))
