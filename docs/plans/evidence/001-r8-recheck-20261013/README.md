# NOTES-001 r8 JSON API integration recheck

This recheck adapts the Notes backend to the strict public `auto.json` face while
keeping the public API unchanged. Boolean reads now compare the returned value
with `true`; JSON-root validation uses the public `json.parse` null sentinel.
No generated Rust or AutoLang declaration was edited in the Notes repository.

## Revisions and build input

- Notes source: branch `v0.6-dev`, base HEAD `61e83f81eff06165b18e776081d7b66a78dbd036`.
- AutoLang candidate: branch `plan-775-dev`, final source HEAD
  `8bc11d2fc8ef35d384e9061a07bec4d9efdddf46`.
- Runtime changes used by the Notes build are in AutoLang commits
  `924273fa5` (VM task-owned SQLite handle cleanup) and `b1230e767`
  (verified generic `json.encode[T]` adapter). The later `8bc11d2fc` commit
  changes only the Plan 394 test harness.
- CLI used by the VM scenario: `D:/autostack/.wt/lang-775/auto-lang/target/debug/auto.exe`,
  SHA-256 `71F7052A81B0760A28B64DF4050C1ABA149FDBDD8362D88973D7D9F32EB8109E`.
- The ignored local `rust-workspace/Cargo.toml` was restored after generation to
  the normal `../../../../auto-lang` dependency paths; restored SHA-256 is
  `2C3468E7A07285700E5CC8F4F8CACC6E18C74D155230DB4C879FAD4157732B1C`.

## Results

| Gate | Result | Durable receipt |
|---|---|---|
| API behavior battery S0–S19 | PASS, `fails=0` | [battery-summary.txt](battery-summary.txt) |
| Vue/Playwright suite | PASS, 24 passed | [vue-playwright.log](vue-playwright.log) |
| VM normal suite | PASS, 19 passed, 0 failed, 0 skipped | [vm-suite.log](vm-suite.log) |
| R7 VM scenarios 1–3 | PASS, `fails=[]` | [r7-vm-result.json](r7-vm-result.json) |
| Independent API combinations | PASS, 6/6 | [api-combinations.json](api-combinations.json) |

The Vue and VM child suites both completed with exit code 0. Their outer Python
wrappers then returned 1 while printing a GBK-incompatible Unicode status line;
the captured child-suite logs contain the completed pass summaries above. This
is a wrapper-output encoding issue after the test run, not a test assertion
failure.

## SHA-256 receipts

| File | SHA-256 |
|---|---|
| `battery-summary.txt` | `1E384944FF8481BD4C43FB55FA97ED6D4B3D2E82884C46835ADAC85385159FE1` |
| `r7-vm-result.json` | `140616E92EEF3FF33F10F5E792125558F4E1C9AE9C91EEA909DB4DFB611B809F` |
| `vue-playwright.log` | `72F95060B15FFC8D4414576B22DBC0DF59BA498AA4BB8638209B6DF837DBD794` |
| `vm-suite.log` | `9047B9D6C6413A65358F7A01C0E495E3F36783E873993C089962C890430BBC6E` |
| `api-combinations.json` | `809AC46FF9412C56AAF1DD79C2F790AF11046C8B852473FB6828C2F474FB6A52` |

Source outputs were copied from the corresponding `.auto/` run directories on
2026-10-13. The original ignored run directories remain untouched.
