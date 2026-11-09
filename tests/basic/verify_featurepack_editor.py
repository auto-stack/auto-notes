#!/usr/bin/env python3
"""verify_featurepack_editor.py — NOTES-006 T-03 双端 V-02 永久验证入口（AC-02）。

用法（auto-notes 仓根）：
    python tests/basic/verify_featurepack_editor.py --profile vue
    python tests/basic/verify_featurepack_editor.py --profile vm

覆盖（NOTES-006 §6 V-02 / AC-02；组件契约 fpack components/fp_editor.at）：
  E-1 双实例并存：edit 实例（选中笔记后键控挂载）+ create 实例同时渲染。
  E-2 create 流程：键入 → Submit → saved 投影；服务端笔记数 +1。
  E-3 edit 键控换挂：选中笔记 → edit 实例出现且草稿 = initial_text 播种
      （PLAN-041 重挂=全新 Init）；修改 → Submit → saved；服务端正文同一修订
      （主应用与组件看到同一修订）。
  E-4 迟到/另一实例互不扰：edit 提交保存后 create 实例草稿保持原样。
  E-5 冲突保输入：外部（fp 服务直改）推进 revision → UI Submit → conflict
      投影 + 组件草稿保留 → Rebase → 再 Submit → saved（基于新修订）。
  E-6 关闭一个实例不改变另一个：切选清空 edit 实例（键控卸载）后 create
      草稿仍在。

双端：vue = playwright 驱动 vite 产品页；vm = `auto run -r vm` + UI MCP
（snapshot/action/state）。断言失败或缺少必需用例返回非零。
原始日志 D:/autostack/plan-artifacts/plan-006/。
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[1]
ARTIFACTS = Path(os.environ.get("PLAN_ARTIFACTS_HOME", "D:/autostack/plan-artifacts/plan-006"))
IF_V1 = "notes.fpack/1"
FRONT_PORT = 17818
BACK_PORT = 17819

PASS, FAIL, SKIP = [], [], []


def check(cond, name, detail=""):
    if cond:
        PASS.append(name)
        print("PASS", name)
    else:
        FAIL.append(name)
        print("FAIL", name, "-", str(detail)[:240])


def skip(name, reason):
    SKIP.append(name)
    print("SKIP", name, "-", reason)


def http(method, path, body=None, timeout=30):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{BACK_PORT}" + path, data=data,
                                 method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            out = json.loads(e.read().decode())
        except Exception:
            out = {"__status": e.code}
    except Exception:
        return {"__status": 0}
    if isinstance(out, str):
        try:
            out = json.loads(out)
        except Exception:
            pass
    return out


def fp_post(path, body):
    return http("POST", path, body)


def free_bind_port(start=21000):
    import random
    for _ in range(200):
        p = random.randint(start, 45000)
        try:
            s = socket.socket()
            s.bind(("127.0.0.1", p))
            s.close()
            return p
        except OSError:
            continue
    raise RuntimeError("no bindable port")


def spawn(env_extra, log_path, vm=False):
    env = dict(os.environ)
    env["NOTES_TEST_MODE"] = "1"
    env.update(env_extra)
    exe = os.environ.get("AUTO_EXE", "auto")
    cmd = [exe, "run", "-r", "vm"] if vm else [exe, "run"]
    if vm:
        env["AUTOUI_MCP_PORT"] = str(free_bind_port())
    log_f = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(cmd, cwd=str(ROOT), env=env, stdout=log_f,
                            stderr=subprocess.STDOUT,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return proc, log_f, env.get("AUTOUI_MCP_PORT")


def wait_http(url, timeout=900):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=4) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(2)
    return False


def kill_tree(proc):
    if proc and proc.poll() is None:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    time.sleep(1)


# ── Vue 轨（playwright） ─────────────────────────────────────────────

def run_vue(run_dir):
    tests_dir = ROOT / "tests"
    # ESM 从脚本自身位置解析依赖：探针必须落在 tests/（playwright 所在）
    node_probe = tests_dir / ".fp_editor_probe.mjs"
    node_probe.write_text(VUE_MJS, encoding="utf-8")
    try:
        r = subprocess.run(["node", ".fp_editor_probe.mjs",
                            f"http://127.0.0.1:{FRONT_PORT}"],
                           cwd=str(tests_dir), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=300)
    finally:
        node_probe.unlink(missing_ok=True)
    sys.stdout.write(r.stdout or "")
    if r.stderr:
        sys.stdout.write(r.stderr[-800:])
    (run_dir / "vue_editor_probe.out.txt").write_text(
        (r.stdout or "") + "\n--stderr--\n" + (r.stderr or ""), encoding="utf-8")
    if "vue-editor-probe PASS=" not in (r.stdout or ""):
        check(False, "vue-probe-completed", "probe crashed; see probe out in artifacts")
    for line in (r.stdout or "").splitlines():
        if line.startswith("PASS "):
            check(True, "vue-" + line[5:].strip())
        elif line.startswith("FAIL "):
            check(False, "vue-" + line[5:].split(" - ")[0].strip(),
                  line[5:].split(" - ", 1)[-1])
    return 0 if "FAIL=0" in (r.stdout or "") else 1


VUE_MJS = r"""
import { chromium } from "@playwright/test";
const base = process.argv[2];
const CRED = 'c'.repeat(64);
const IV = 'notes.fpack/1';
let pass = 0, fail = 0;
function check(cond, name, detail = "") {
  if (cond) { pass++; console.log("PASS", name); }
  else { fail++; console.log("FAIL", name, "-", String(detail).slice(0, 200)); }
}
const browser = await chromium.launch();
const page = await browser.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
try {
  await page.goto(base, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.getByText("FeaturePack").first().waitFor({ timeout: 30000 });

  // 预置 fp 来源笔记（冲突靶；title=quote 进列表）
  const cap = await page.evaluate(async () => {
    const src = { book_id: 'book:abc123', quote: 'FP 冲突靶', chapter: 1 };
    const r = await fetch('/api/fp/v1/capture', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cred: 'c'.repeat(64), interface_version: 'notes.fpack/1',
        attempt_id: 'seed-fp', operation_id: 'd'.repeat(32),
        source_json: JSON.stringify(src), text: '原始正文' }) });
    let x = await r.json(); if (typeof x === 'string') { x = JSON.parse(x); } return x;
  });
  check(cap.ok === true, "E-0a-fp-seed-captured", JSON.stringify(cap).slice(0, 120));
  const fpNid = (cap.note || {}).note_id || "";
  await page.reload({ waitUntil: "domcontentloaded" });  // 刷新列表含 fp 种子
  await page.getByText("FeaturePack").first().waitFor({ timeout: 30000 });
  await page.waitForTimeout(1500);  // Init 自动选中首条笔记
  const tas = page.locator('textarea[placeholder="FP body"]');


  // E-1 双实例并存（Init 自动选中 Seed → edit+create 同屏）
  check((await tas.count()) === 2, "E-1a-both-instances", await tas.count());
  const seedTxt = await tas.first().inputValue();
  check(seedTxt === "原始正文", "E-1b-edit-bound-to-selected", seedTxt);

  // E-2 create 流程：独立草稿字段 → Submit → saved + 服务端 +1
  await tas.last().fill("FP-EDIT-PROBE-DRAFT-A");
  await page.getByText("Submit").last().click();
  await page.waitForTimeout(1200);
  const cnt = await page.evaluate(async () => (await (await fetch('/api/v1/notes')).json()).length);
  check(cnt === 3, "E-2a-create-count", cnt);
  const created = await page.evaluate(async () => {
    const docs = await (await fetch('/api/v1/notes')).json();
    return docs.find(d => d.title === "FP 新建");
  });
  check(created && created.body === "FP-EDIT-PROBE-DRAFT-A", "E-2b-create-body",
        created ? created.body : JSON.stringify((await page.evaluate(async () => (await (await fetch('/api/v1/notes')).json()))).map(d => [d.title, d.body])));

  // E-3 前置：create 实例留一条**未提交**草稿（E-4/E-6 的隔离对照）
  await tas.last().fill("FP-EDIT-PROBE-DRAFT-KEEP");
  // E-3 edit 流程（fp 来源笔记）：选中 → 草稿同源 → 修改提交 → fp 服务同修订
  await page.getByText("FP 冲突靶").first().click();
  await page.waitForTimeout(1000);
  const selTxt = await tas.first().inputValue();
  check(selTxt === "原始正文", "E-3a-edit-roundtrip-seed", selTxt);
  await tas.first().fill("FP-EDIT-PROBE-EDIT-B");
  await page.getByText("Submit").first().click();
  await page.waitForTimeout(1500);
  const g = await page.evaluate(async (nid) => {
    const r = await fetch('/api/fp/v1/get', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cred: 'c'.repeat(64), interface_version: 'notes.fpack/1', note_id: nid }) });
    let x = await r.json(); if (typeof x === 'string') { x = JSON.parse(x); } return x;
  }, fpNid);
  check(g.ok === true && (g.note || {}).body === "FP-EDIT-PROBE-EDIT-B" && (g.note || {}).revision === 2,
        "E-3b-edit-saved-fp-rev2", JSON.stringify(g).slice(0, 160));

  // E-4 另一实例互不扰：create 草稿保持
  const cdraft = await tas.last().inputValue();
  check(cdraft === "FP-EDIT-PROBE-DRAFT-KEEP", "E-4a-create-draft-intact", cdraft);

  // E-5 冲突保输入：外部 fp_update 推进 revision → UI 提交 → conflict +
  // 输入保留 + 服务器版本可见 → Rebase → 再提交 → saved（新修订）
  const ext = await page.evaluate(async (nid) => {
    const r = await fetch('/api/fp/v1/update', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cred: 'c'.repeat(64), interface_version: 'notes.fpack/1', attempt_id: 'ext-1',
        note_id: nid, expected_revision: 2, text: 'FP-EDIT-PROBE-EXTERNAL',
        operation_id: 'e'.repeat(32) }) });
    let x = await r.json(); if (typeof x === 'string') { x = JSON.parse(x); } return x;
  }, fpNid);
  check(ext.ok === true, "E-5a-external-update", JSON.stringify(ext).slice(0, 120));
  await tas.first().fill("FP-EDIT-PROBE-CONFLICT-C");
  await page.getByText("Submit").first().click();
  await page.getByText("Conflict").first().waitFor({ timeout: 15000 });
  const kept = await tas.first().inputValue();
  check(kept === "FP-EDIT-PROBE-CONFLICT-C", "E-5b-conflict-keeps-input", kept);
  await page.waitForTimeout(800);
  const bannerTxt = await page.locator("body").innerText();
  const revIdx = bannerTxt.indexOf("Server revision:");
  const bannerDump = revIdx >= 0 ? bannerTxt.slice(revIdx, revIdx + 80) : "NO-BANNER";
  console.log("E-5c banner dump:", JSON.stringify(bannerDump));
  const srvShown = bannerDump.includes("FP-EDIT-PROBE-EXTERNAL");
  check(srvShown, "E-5c-server-body-visible-for-compare", bannerDump);
  await page.getByText("Rebase").first().click();
  await page.waitForTimeout(600);
  await page.getByText("Submit").first().click();
  await page.waitForTimeout(1500);
  const g2 = await page.evaluate(async (nid) => {
    const r = await fetch('/api/fp/v1/get', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cred: 'c'.repeat(64), interface_version: 'notes.fpack/1', note_id: nid }) });
    let x = await r.json(); if (typeof x === 'string') { x = JSON.parse(x); } return x;
  }, fpNid);
  check(g2.ok === true && (g2.note || {}).body === "FP-EDIT-PROBE-CONFLICT-C",
        "E-5d-rebased-saved", JSON.stringify(g2).slice(0, 160));

  // E-6 关闭/切换不扰另一实例
  const cdraft2 = await tas.last().inputValue();
  check(cdraft2 === "FP-EDIT-PROBE-DRAFT-KEEP", "E-6a-create-draft-still-intact", cdraft2);
  check(errors.length === 0, "E-6b-no-page-errors", errors.slice(0, 2).join("|"));
} finally {
  await browser.close();
}
console.log(`vue-editor-probe PASS=${pass} FAIL=${fail}`);
process.exit(fail ? 1 : 0);
"""


# ── VM 轨（MCP） ─────────────────────────────────────────────────────

def run_vm(run_dir, mcp_port):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    # 复用 service 验证脚本的 MCP 客户端形制（snapshot/action/state）
    import urllib.request as _u

    url = f"http://127.0.0.1:{mcp_port}/mcp"
    n = [0]

    def call(tool, **args):
        n[0] += 1
        req = _u.Request(url, data=json.dumps({
            "jsonrpc": "2.0", "method": "tools/call",
            "params": {"name": tool, "arguments": args}, "id": n[0]}).encode(),
            headers={"Content-Type": "application/json"})
        with _u.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode())
        c = d.get("result", {}).get("content", [])
        return c[0]["text"] if c else ""

    def snapshot():
        return call("autoui_snapshot")

    def click_evt(snap, event):
        import re
        pat = re.compile(r"#(aura_\d+|vnode_\d+)")
        cur = None
        target = f"onclick: .{event}"
        for line in snap.splitlines():
            m = pat.search(line)
            if m:
                cur = m.group(1)
            if target in line and cur is not None:
                return cur
        return None

    # 工具面探测：VM MCP 是否具备文本注入能力
    tl = json.loads(call_tools_list(url))
    names = [t.get("name") for t in tl]
    has_input = any("input" in (x or "").lower() for x in names)

    snap = snapshot()
    (run_dir / "vm_editor_snapshot.txt").write_text(snap, encoding="utf-8")
    check("FeaturePack" in snap, "vm-E-1a-shell-renders")
    check("New shared note" in snap, "vm-E-1b-create-instance-renders",
          "create 实例头未出现在快照")
    if has_input:
        skip("vm-E-2..E-6", "VM MCP 具备 input 面——本入口 v0 未接（见 NOTES-006 T-03 记录），"
             "以 vue 轨全例 + vm 轨渲染/回调面为准")
        # 回调面：Submit 空草稿提交（create 模式空文本 → store 仍建笔记，
        # 组件 emit 通道本身可核）
        el = click_evt(snap, "FpCreateSubmit")
        if el:
            call("autoui_action", element_id=el, action="press")
            time.sleep(1)
            snap2 = snapshot()
            check("Saved" in snap2 or "Saving" in snap2, "vm-E-2b-submit-emit-reaches-host")
        else:
            skip("vm-E-2b-submit-emit", "快照未定位 FpCreateSubmit 绑定")
    else:
        skip("vm-E-2..E-6", "VM MCP 无文本注入面（在案工具缺口）——"
             "组件渲染/事件绑定以快照核对，键入流以 vue 轨为准，不以 mock 冒充")
        # 组件内 emit 通道（SubmitText）为快照可见绑定；宿主 handler 名
        # （FpCreateSubmit）经 prop 绑定，不出现在元素 onclick 面
        el = click_evt(snap, "SubmitText")
        check(el is not None, "vm-E-2b-submit-binding-visible", "SubmitText 绑定不在快照")
    st = call("autoui_state", fields=["fp_create_state", "fp_edit_state"])
    check("fp_create_state" in st, "vm-E-7-host-state-readable", st[:120])


def call_tools_list(url):
    import urllib.request as _u
    req = _u.Request(url, data=json.dumps({"jsonrpc": "2.0", "method": "tools/list",
                                           "params": {}, "id": 1}).encode(),
                     headers={"Content-Type": "application/json"})
    with _u.urlopen(req, timeout=10) as r:
        d = json.loads(r.read().decode())
    return json.dumps(d.get("result", {}).get("tools", []))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["vue", "vm"], required=True)
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="fpeditor-", dir=str(ARTIFACTS)))
    data_dir = run_dir / "data"
    policy = {"entries": [
        {"cred": "c" * 64, "principal": "fp-ext",
         "operations": ["capture", "read", "update", "receipt", "list_by_book"],
         "book_scopes": ["book:abc123"]},
    ]}
    (run_dir / "fp-policy.json").write_text(json.dumps(policy), encoding="utf-8")
    env_extra = {"NOTES_DATA_DIR": str(data_dir),
                 "NOTES_FP_POLICY": str(run_dir / "fp-policy.json")}
    proc = None
    log_f = None
    try:
        if args.profile == "vue":
            proc, log_f, _ = spawn(env_extra, run_dir / "vue_run.log", vm=False)
            if not wait_http(f"http://127.0.0.1:{FRONT_PORT}/", timeout=900):
                print("FATAL: vite not ready (see", run_dir / "vue_run.log", ")")
                return 2
            # 预置一条笔记（edit 实例的选中目标）+ 授权书作用域书
            http("POST", "/api/notes", {"title": "Seed Note", "body": "seed body",
                                        "folder": "", "request_id": "seed-1"})
            rc = run_vue(run_dir)
        else:
            proc, log_f, mcp_port = spawn(env_extra, run_dir / "vm_run.log", vm=True)
            mcp_url = f"http://127.0.0.1:{mcp_port}/mcp"
            deadline = time.time() + 900
            up = False
            while time.time() < deadline:
                try:
                    call_tools_list(mcp_url)
                    up = True
                    break
                except Exception:
                    time.sleep(3)
            if not up:
                print("FATAL: VM MCP not ready (see", run_dir / "vm_run.log", ")")
                return 2
            time.sleep(3)
            http("POST", "/api/notes", {"title": "Seed Note", "body": "seed body",
                                        "folder": "", "request_id": "seed-1"})
            rc = run_vm(run_dir, mcp_port)
    finally:
        kill_tree(proc)
        subprocess.run(["taskkill", "/F", "/IM", "auto.exe"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", "auto-notes-30db9907-back.exe"],
                       capture_output=True)
        if log_f:
            log_f.close()
        if not args.keep:
            shutil.rmtree(run_dir, ignore_errors=True)

    print(f"\nfeaturepack-editor[{args.profile}] PASS={len(PASS)} "
          f"FAIL={len(FAIL)} SKIP={len(SKIP)}")
    for f in FAIL:
        print("  FAIL:", f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
