#!/usr/bin/env python3
"""verify_featurepack_editor.py — NOTES-006 T-03/T-08 双端 V-02/S-03/04/05 永久验证入口。

用法（auto-notes 仓根）：
    python tests/basic/verify_featurepack_editor.py --profile vue
    python tests/basic/verify_featurepack_editor.py --profile vm

覆盖（NOTES-006 §6 V-02 + r2 S-03/04/05；组件契约 fpack components/fp_editor.at
+ 共享适配 fp_host.at，T-06 冻结七态状态机）：
  E-1 双实例并存：edit 实例（选中笔记后键控挂载）+ create 实例同时渲染。
  E-2 create 流程：键入 → Submit → saved 投影；服务端笔记数 +1；成功清持久槽。
  E-3 edit 同源：选中 fp 来源笔记 → 草稿同源 → 修改提交 → fp 服务同一修订。
  S-3a 保存过程中继续键入（路由闸门延迟提交）：服务端落提交版，编辑器保留
       新输入（仍未保存），持久槽记 dirty 新版——成功只清已提交那一版输入。
  S-3b 切实例 + 关页/重启恢复：create 未提交草稿经检查点（切换）持久，
       重开页面后由 Init 恢复（命名空间稳定至重启）。
  S-3c 丢回包 → pending → 同 ID 重试续查：路由中断传输层失败 → pending
       （可观察徽标/状态）→ 恢复路由原操作重试 → saved（服务端一次生效）。
  E-4/S-4 迟到与另一实例互不扰；错误/待确认/冲突三态可区分（pending vs
       error vs conflict 的状态投影各自断言）。
  E-5 冲突保输入：外部（fp 服务直改）推进 revision → UI Submit → conflict
       投影 + 组件草稿保留 → Rebase → 再 Submit → saved（基于新修订）。
  E-6 关闭一个实例不改变另一个；零页面错误。
  VM 轨：type_text 真实输入（中文/emoji）+ 提交 + 冲突/Rebase + 进程重启
       恢复全部实跑（r2：不以「工具面未接」skip；必需 case 缺失即非零）。

双端：vue = playwright 驱动 vite 产品页；vm = `auto run -r vm` + UI MCP
（snapshot/action/state，type_text 真实注入）。断言失败或缺少必需用例返回非零。
进程清理只回收自有 PID 树（kill_tree /T /F /PID），不做全局 /IM 清扫。
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
    # r2 S-05：必需 case 不允许 skip——本入口当前没有可合法 skip 的必需面，
    # 保留通道仅为显式环境豁免（调用即计入 SKIP 并在汇总可见）。
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
            out = {"__badjson": out}
    return out


def fp_src(hash_hex):
    """T-06 冻结 schema 七字段闭集来源。"""
    return {"book_id": "book:abc123", "source_hash": hash_hex,
            "title": "冲突靶书名", "author": "冲突靶作者",
            "quote": "FP 冲突靶", "chapter": 1,
            "locator": {"kind": "cfi", "v": 1, "value": "epubcfi(i/2!)"}}


def draft_key(target, instance):
    """与 notes_store/fp_host.fp_draft_key 同构（fpdraft|user|host|target|instance）。"""
    return f"fpdraft|local|notes-main|{target}|{instance}"


def slot_of(target, instance):
    return http("POST", "/api/fp/draft/get", {"draft_key": draft_key(target, instance)})


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


def port_free(port):
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


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
    """只回收自有进程树（r2/S-05、OS-067 G-04/G-05：禁止全局 /IM 清扫）。"""
    if proc and proc.poll() is None:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        time.sleep(1)


def wait_ports_free(timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_free(FRONT_PORT) and port_free(BACK_PORT):
            return True
        time.sleep(1)
    return False


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
const updUrl = /\/api\/notes\/\d+\/result$/;
const browser = await chromium.launch();
const page = await browser.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
try {
  await page.goto(base, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.getByText("FeaturePack").first().waitFor({ timeout: 30000 });

  // 预置 fp 来源笔记（冻结 schema；冲突靶）+ 普通种子
  const cap = await page.evaluate(async (src) => {
    const r = await fetch('/api/fp/v1/capture', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cred: 'c'.repeat(64), interface_version: 'notes.fpack/1',
        attempt_id: 'seed-fp', operation_id: 'd'.repeat(32),
        source_json: JSON.stringify(src), text: '原始正文' }) });
    let x = await r.json(); if (typeof x === 'string') { x = JSON.parse(x); } return x;
  }, { book_id: 'book:abc123', source_hash: '3f2a'.repeat(16), title: '冲突靶书名',
       author: '冲突靶作者', quote: 'FP 冲突靶', chapter: 1,
       locator: { kind: 'cfi', v: 1, value: 'epubcfi(i/2!)' } });
  check(cap.ok === true, "E-0a-fp-seed-captured", JSON.stringify(cap).slice(0, 120));
  const fpNid = (cap.note || {}).note_id || "";
  const fid = Number(fpNid.slice(2));
  await page.reload({ waitUntil: "domcontentloaded" });  // 刷新列表含 fp 种子
  await page.getByText("FeaturePack").first().waitFor({ timeout: 30000 });
  await page.waitForTimeout(1500);  // Init 自动选中首条笔记 + 草稿/来源恢复窗
  const tas = page.locator('textarea[placeholder="FP body"]');

  // E-1 双实例并存（Init 自动选中 Seed → edit+create 同屏）
  check((await tas.count()) === 2, "E-1a-both-instances", await tas.count());
  const seedTxt = await tas.first().inputValue();
  check(seedTxt === "原始正文", "E-1b-edit-bound-to-selected", seedTxt);

  // E-2 create 流程：独立草稿字段 → Submit → saved + 服务端 +1 + 槽清
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
        created ? created.body : "missing");
  const slotC1 = await page.evaluate(async (k) => {
    const r = await fetch('/api/fp/draft/get', { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ draft_key: k }) });
    return await r.json();
  }, "fpdraft|local|notes-main|create|create");
  check(slotC1.found === false, "E-2c-create-slot-cleared-on-ack", JSON.stringify(slotC1).slice(0, 120));

  // E-3 edit 流程（fp 来源笔记）：选中 → 草稿同源 → 修改提交 → fp 服务同修订
  await tas.last().fill("FP-EDIT-PROBE-DRAFT-KEEP");
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

  // S-3a 保存过程中继续键入（路由闸门延迟提交）：提交版落服务端，编辑器
  // 保留新输入（仍未保存），持久槽记 dirty 新版——只清已提交那一版输入。
  let releaseSave;
  const gate = new Promise((r) => { releaseSave = r; });
  await page.route(updUrl, async (route) => { await gate; await route.continue(); });
  await tas.first().fill("FP-EDIT-PROBE-SAVEKEEP");
  await page.getByText("Submit").first().click();
  await page.waitForTimeout(400);  // 提交已在途（闸门未放行）
  await tas.first().fill("FP-EDIT-PROBE-AFTER");
  const slotDuring = await page.evaluate(async (k) => {
    const r = await fetch('/api/fp/draft/get', { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ draft_key: k }) });
    return await r.json();
  }, "fpdraft|local|notes-main|note:" + fid + "|edit");
  check(slotDuring.found === true && slotDuring.text === "FP-EDIT-PROBE-SAVEKEEP" &&
        slotDuring.state === "saving", "S-3a0-submit-checkpoint-persisted",
        JSON.stringify(slotDuring).slice(0, 160));
  releaseSave();
  await page.waitForTimeout(1500);
  const gA = await page.evaluate(async (nid) => {
    const r = await fetch('/api/fp/v1/get', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cred: 'c'.repeat(64), interface_version: 'notes.fpack/1', note_id: nid }) });
    let x = await r.json(); if (typeof x === 'string') { x = JSON.parse(x); } return x;
  }, fpNid);
  check((gA.note || {}).body === "FP-EDIT-PROBE-SAVEKEEP", "S-3a1-server-has-submitted-version",
        (gA.note || {}).body);
  check((await tas.first().inputValue()) === "FP-EDIT-PROBE-AFTER", "S-3a2-typing-during-save-kept",
        await tas.first().inputValue());
  const slotAfter = await page.evaluate(async (k) => {
    const r = await fetch('/api/fp/draft/get', { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ draft_key: k }) });
    return await r.json();
  }, "fpdraft|local|notes-main|note:" + fid + "|edit");
  check(slotAfter.found === true && slotAfter.text === "FP-EDIT-PROBE-AFTER" &&
        slotAfter.state === "dirty", "S-3a3-slot-holds-new-input-dirty",
        JSON.stringify(slotAfter).slice(0, 160));

  // S-3b 切实例 + 关页/重启恢复：create 未提交草稿经检查点持久，重开恢复。
  await tas.last().fill("KEEP-DRAFT-reload");
  await page.getByText("Seed Note").first().click();   // 触发 SelectNote 检查点
  await page.waitForTimeout(800);
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByText("FeaturePack").first().waitFor({ timeout: 30000 });
  await page.waitForTimeout(1500);
  const tas2 = page.locator('textarea[placeholder="FP body"]');
  check((await tas2.last().inputValue()) === "KEEP-DRAFT-reload", "S-3b-create-draft-restored-after-reload",
        await tas2.last().inputValue());

  // S-3c 丢回包 → pending → 同 ID 重试续查：路由中断 → pending 可观察 →
  // 恢复路由原操作重试 → saved（服务端一次生效，无重复推进）。
  await page.getByText("FP 冲突靶").first().click();
  await page.waitForTimeout(800);
  const tas3 = page.locator('textarea[placeholder="FP body"]');
  await page.route(updUrl, async (route) => { await route.abort("connectionreset"); });
  await tas3.first().fill("FP-EDIT-PROBE-PEND-X");
  await page.getByText("Submit").first().click();
  await page.waitForTimeout(800);
  // vue 客户端传输失败为异常中断（handler 死在 await，state 停 saving、
  // op 保留）——回包未观察的恢复路径 = 重启：Init 把 saving 映射 pending
  // 并把观察态写回槽（r2「关页/重启恢复…原操作可续查」的主链）。
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByText("FeaturePack").first().waitFor({ timeout: 30000 });
  await page.waitForTimeout(1500);
  // boot 活动笔记 = 列表首条（非必然是 fp 靶）——点回 fp 靶走 SelectNote
  // flushed 恢复链（槽 + saving→pending 映射）。
  await page.getByText("FP 冲突靶").first().click();
  await page.waitForTimeout(1000);
  const pendState = await page.locator("body").innerText();
  check(/pending/i.test(pendState), "S-3c1-pending-observable",
        (pendState.match(/pending|saving|idle|error/g) || []).join(","));
  const slotPend = await page.evaluate(async (k) => {
    const r = await fetch('/api/fp/draft/get', { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ draft_key: k }) });
    return await r.json();
  }, "fpdraft|local|notes-main|note:" + fid + "|edit");
  check(slotPend.found === true && slotPend.state === "pending" && slotPend.op !== "",
        "S-3c2-pending-slot-with-op", JSON.stringify(slotPend).slice(0, 160));
  await page.unroute(updUrl);
  const tas3b = page.locator('textarea[placeholder="FP body"]');
  const pendKept = await tas3b.first().inputValue();
  check(pendKept === "FP-EDIT-PROBE-PEND-X", "S-3c2b-pending-input-restored", pendKept);
  await page.getByText("Submit").first().click();
  await page.waitForTimeout(1500);
  const gP = await page.evaluate(async (nid) => {
    const r = await fetch('/api/fp/v1/get', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cred: 'c'.repeat(64), interface_version: 'notes.fpack/1', note_id: nid }) });
    let x = await r.json(); if (typeof x === 'string') { x = JSON.parse(x); } return x;
  }, fpNid);
  check((gP.note || {}).body === "FP-EDIT-PROBE-PEND-X", "S-3c3-retry-same-op-saved",
        JSON.stringify(gP).slice(0, 160));
  const slotPend2 = await page.evaluate(async (k) => {
    const r = await fetch('/api/fp/draft/get', { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ draft_key: k }) });
    return await r.json();
  }, "fpdraft|local|notes-main|note:" + fid + "|edit");
  check(slotPend2.found === false, "S-3c4-slot-cleared-after-ack", JSON.stringify(slotPend2).slice(0, 120));

  // E-5 冲突保输入：外部 fp_update 推进 revision → UI 提交 → conflict +
  // 输入保留 + 服务器版本可见 → Rebase → 再提交 → saved（新修订）。
  const gcur = await page.evaluate(async (nid) => {
    const r = await fetch('/api/fp/v1/get', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cred: 'c'.repeat(64), interface_version: 'notes.fpack/1', note_id: nid }) });
    let x = await r.json(); if (typeof x === 'string') { x = JSON.parse(x); } return x;
  }, fpNid);
  const curRev = (gcur.note || {}).revision || 0;
  const ext = await page.evaluate(async ([nid, rev]) => {
    const r = await fetch('/api/fp/v1/update', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cred: 'c'.repeat(64), interface_version: 'notes.fpack/1', attempt_id: 'ext-1',
        note_id: nid, expected_revision: rev, text: 'FP-EDIT-PROBE-EXTERNAL',
        operation_id: 'e'.repeat(32) }) });
    let x = await r.json(); if (typeof x === 'string') { x = JSON.parse(x); } return x;
  }, [fpNid, curRev]);
  check(ext.ok === true, "E-5a-external-update", JSON.stringify(ext).slice(0, 120));
  const tas4 = page.locator('textarea[placeholder="FP body"]');
  await tas4.first().fill("FP-EDIT-PROBE-CONFLICT-C");
  await page.getByText("Submit").first().click();
  await page.getByText("Conflict").first().waitFor({ timeout: 15000 });
  const kept = await tas4.first().inputValue();
  check(kept === "FP-EDIT-PROBE-CONFLICT-C", "E-5b-conflict-keeps-input", kept);
  await page.waitForTimeout(800);
  const bannerTxt = await page.locator("body").innerText();
  const revIdx = bannerTxt.indexOf("Server revision:");
  const bannerDump = revIdx >= 0 ? bannerTxt.slice(revIdx, revIdx + 80) : "NO-BANNER";
  console.log("E-5c banner dump:", JSON.stringify(bannerDump));
  check(bannerDump.includes("FP-EDIT-PROBE-EXTERNAL"), "E-5c-server-body-visible-for-compare", bannerDump);
  errors.length = 0;  // S-3c 中止的 Failed to fetch 是预期页面错误，此后重计
  // Rebase「点击至状态生效」（重渲染 vnode 换代可能吞点击，r9 在案）：conflict
  // 徽标消失 = Rebase 已认领；随后提交至 Saved。
  for (let i = 0; i < 3; i++) {
    const bt = await page.locator("body").innerText();
    if (!/Conflict/.test(bt)) break;
    await page.getByText("Rebase").first().click();
    await page.waitForTimeout(700);
  }
  let savedShown = false;
  for (let i = 0; i < 3 && !savedShown; i++) {
    await page.getByText("Submit").first().click();
    await page.waitForTimeout(1500);
    const st = await page.locator("body").innerText();
    savedShown = /Saved/.test(st);
  }
  const dbg = await page.locator("body").innerText();
  const stMatch = dbg.match(/idle|dirty|saving|saved|pending|error|conflict/g) || [];
  const slotDbg = await page.evaluate(async (k) => {
    const r = await fetch('/api/fp/draft/get', { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ draft_key: k }) });
    return await r.json();
  }, "fpdraft|local|notes-main|note:" + fid + "|edit");
  const g2 = await page.evaluate(async (nid) => {
    const r = await fetch('/api/fp/v1/get', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cred: 'c'.repeat(64), interface_version: 'notes.fpack/1', note_id: nid }) });
    let x = await r.json(); if (typeof x === 'string') { x = JSON.parse(x); } return x;
  }, fpNid);
  check(g2.ok === true && (g2.note || {}).body === "FP-EDIT-PROBE-CONFLICT-C",
        "E-5d-rebased-saved", JSON.stringify({ states: stMatch.slice(0, 6), slot: slotDbg, note: (g2.note || {}).body, rev: (g2.note || {}).revision }));

  // E-6 关闭/切换不扰另一实例 + 零页面错误
  const tas5 = page.locator('textarea[placeholder="FP body"]');
  const cdraft2 = await tas5.last().inputValue();
  check(cdraft2 === "KEEP-DRAFT-reload", "E-6a-create-draft-still-intact", cdraft2);
  check(errors.length === 0, "E-6b-no-page-errors", errors.slice(0, 2).join("|"));
} finally {
  await browser.close();
}
console.log(`vue-editor-probe PASS=${pass} FAIL=${fail}`);
process.exit(fail ? 1 : 0);
"""


# ── VM 轨（MCP：type_text 真实输入） ─────────────────────────────────

def run_vm(run_dir, mcp_port):
    url = f"http://127.0.0.1:{mcp_port}/mcp"
    n = [0]

    def call(tool, **args):
        n[0] += 1
        req = urllib.request.Request(url, data=json.dumps({
            "jsonrpc": "2.0", "method": "tools/call",
            "params": {"name": tool, "arguments": args}, "id": n[0]}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode())
        c = d.get("result", {}).get("content", [])
        return c[0]["text"] if c else ""

    def snapshot():
        return call("autoui_snapshot")

    def ids_for(snap, pattern):
        """按绑定面文本收集元素 id（快照序）。"""
        import re
        pat = re.compile(r"#(aura_\d+|vnode_\d+)")
        out = []
        cur = None
        for line in snap.splitlines():
            m = pat.search(line)
            if m:
                cur = m.group(1)
            if pattern in line and cur is not None:
                out.append(cur)
        return out

    def state_field(field):
        import re
        st = call("autoui_state", fields=[field])
        m = re.search(field + r'\s*[:=]\s*"?([A-Za-z_]+)"?', st)
        return m.group(1) if m else ("no-match:" + st[:80])

    def fresh_id(snap, pattern, index=0):
        ids = ids_for(snap, pattern)
        return ids[index] if len(ids) > index else None

    def press_until(pattern, index, field, want, tries=4, tag=""):
        # vnode 换代使旧 id 全失效（r9 在案；press 落 #aura_0 实证）——
        # 每轮现取快照现按 id，press 至状态生效。
        last = ""
        for i in range(tries):
            snap = snapshot()
            el = fresh_id(snap, pattern, index)
            if el is None:
                last = "no-element:" + pattern
                time.sleep(1.2)
                continue
            last = call("autoui_action", element_id=el, action="press")
            time.sleep(1.5)
            if state_field(field) == want:
                return True, last
        return False, last

    # （种子在 main 的首次重启前完成——VM 无页面刷新面，Init 需在数据在库后重跑）
    cap = http("POST", "/api/fp/v1/get", {"cred": "c" * 64, "interface_version": IF_V1,
                                          "note_id": "n-2"})
    check(cap.get("ok") is True, "vm-E-0a-fp-seed-present", cap)
    fp_nid = "n-2"
    fid = "2"
    time.sleep(2)

    snap = snapshot()
    # 种子经 HTTP 灌入时 Init 已跑（空库选中）——初始选中直接定 FP 冲突靶行
    # （VM 侧键控重挂后组件回调失效，见计划 §5 r2 实测修订 ⑦：全程免重挂）。
    import re as _re0
    _pat0 = _re0.compile(r"#(aura_\d+|vnode_\d+)")
    sel0 = None
    _cur0 = None
    for _line in snap.splitlines():
        _m0 = _pat0.search(_line)
        if _m0:
            _cur0 = _m0.group(1)
        if "onclick: .SelectNote(" in _line and _cur0 is not None:
            if "FP 冲突靶" in _line:
                sel0 = _cur0
                break
    if sel0 is None:
        _ids0 = ids_for(snap, "onclick: .SelectNote(")
        sel0 = _ids0[0] if _ids0 else None
    if sel0:
        call("autoui_action", element_id=sel0, action="press")
        time.sleep(1.5)
        snap = snapshot()
    (run_dir / "vm_editor_snapshot.txt").write_text(snap, encoding="utf-8")
    check("FeaturePack" in snap, "vm-E-1a-shell-renders")
    check("New shared note" in snap, "vm-E-1b-create-instance-renders")
    tas_ids = ids_for(snap, "oninput: .DraftEdit")
    check(len(tas_ids) == 2, "vm-E-1c-both-textareas", tas_ids)
    if len(tas_ids) != 2:
        check(False, "vm-abort-input-surface", "快照未见双 FP textarea——输入面不可用即必需用例不通过")
        return
    edit_ta, create_ta = tas_ids[0], tas_ids[1]
    submit_ids = ids_for(snap, "onclick: .SubmitText")
    check(len(submit_ids) == 2, "vm-E-1d-both-submit-bindings", submit_ids)
    if len(submit_ids) != 2:
        check(False, "vm-abort-submit-surface", "SubmitText 绑定不可定位")
        return
    edit_submit, create_submit = submit_ids[0], submit_ids[1]

    # M-1 create 真实键入（中文/emoji）→ dirty（type 至状态生效——换代重打）
    typed = False
    for _ in range(3):
        s = snapshot()
        el = fresh_id(s, "oninput: .DraftEdit", 1)
        if el:
            call("autoui_action", element_id=el, action="type_text", value="VM 中文输入 🎉")
        time.sleep(1.5)
        if state_field("fp_create_state") == "dirty":
            typed = True
            break
    check(typed, "vm-M-1a-create-typed-dirty", state_field("fp_create_state"))

    # M-2 create 提交 → saved + 服务端 +1
    ok2, resp2 = press_until("onclick: .SubmitText", 1, "fp_create_state", "saved")
    check(ok2, "vm-M-2a-create-saved", state_field("fp_create_state") + " | " + resp2[:80])
    docs = http("GET", "/api/v1/notes")
    created = [d for d in docs if isinstance(d, dict) and d.get("title") == "FP 新建"]
    check(len(created) == 1 and created[0].get("body") == "VM 中文输入 🎉",
          "vm-M-2b-create-server-body", str(created)[:160])

    # M-3 edit 真实键入（初始选中即 fp 冲突靶——无中途重挂，见实测修订 ⑦）
    check(fp_nid == "n-2", "vm-M-3a-fp-note-selected", fp_nid)
    snap2 = snapshot()
    tas2 = ids_for(snap2, "oninput: .DraftEdit")
    check(len(tas2) == 2, "vm-M-3b-both-textareas-alive", tas2)
    edit_ta2 = tas2[0] if tas2 else edit_ta
    typed2 = False
    for _ in range(3):
        s = snapshot()
        el = fresh_id(s, "oninput: .DraftEdit", 0)
        if el:
            # 先 clear（分辨变量：非空 prop 初值 vs 条件子树回调面）再 type
            call("autoui_action", element_id=el, action="clear")
            time.sleep(0.8)
            call("autoui_action", element_id=el, action="type_text", value="VM 编辑正文 ✍️")
        time.sleep(1.5)
        if state_field("fp_edit_state") == "dirty":
            typed2 = True
            break
    check(typed2, "vm-M-3c-edit-typed-dirty", state_field("fp_edit_state"))
    ok3, resp3 = press_until("onclick: .SubmitText", 0, "fp_edit_state", "saved")
    check(ok3, "vm-M-3d-edit-saved", state_field("fp_edit_state") + " | " + resp3[:80])
    g = http("POST", "/api/fp/v1/get", {"cred": "c" * 64, "interface_version": IF_V1, "note_id": fp_nid})
    check((g.get("note") or {}).get("body") == "VM 编辑正文 ✍️" and (g.get("note") or {}).get("revision") == 2,
          "vm-M-3e-edit-server-rev2", str(g)[:160])

    # M-4 冲突：外部推进 revision → UI 提交 → conflict → Rebase → 再提交 saved
    ext = http("POST", "/api/fp/v1/update",
               {"cred": "c" * 64, "interface_version": IF_V1, "attempt_id": "ext-1",
                "note_id": fp_nid, "expected_revision": 2, "text": "VM 外部推进",
                "operation_id": "e" * 32})
    check(ext.get("ok") is True, "vm-M-4a-external-update", ext)
    snap4 = snapshot()
    ta4 = ids_for(snap4, "oninput: .DraftEdit")
    call("autoui_action", element_id=ta4[0] if ta4 else edit_ta2, action="type_text", value="VM 冲突稿")
    time.sleep(1)
    ok4, resp4 = press_until("onclick: .SubmitText", 0, "fp_edit_state", "conflict")
    check(ok4, "vm-M-4b-conflict-state", state_field("fp_edit_state") + " | " + resp4[:80])
    snap6 = snapshot()
    (run_dir / "vm_conflict_snapshot.txt").write_text(snap6, encoding="utf-8")
    check("Conflict" in snap6, "vm-M-4c-conflict-badge", "conflict 徽标未渲染")
    rebase_ids = ids_for(snap6, "onclick: .Rebase")
    if not rebase_ids:
        rebase_ids = ids_for(snap6, "onclick: .RebaseTap")
    check(len(rebase_ids) >= 1, "vm-M-4d-rebase-binding", rebase_ids)
    if rebase_ids:
        call("autoui_action", element_id=rebase_ids[0], action="press")
        time.sleep(1.2)
    ok5, resp5 = press_until("onclick: .SubmitText", 0, "fp_edit_state", "saved")
    check(ok5, "vm-M-4e-rebased-saved", state_field("fp_edit_state") + " | " + resp5[:80])
    g2 = http("POST", "/api/fp/v1/get", {"cred": "c" * 64, "interface_version": IF_V1, "note_id": fp_nid})
    check((g2.get("note") or {}).get("body") == "VM 冲突稿" and (g2.get("note") or {}).get("revision") == 4,
          "vm-M-4f-rebased-server-rev4", str(g2)[:160])

    # M-5 重启恢复：edit 未提交稿 → 切换笔记（检查点）→ 杀自有进程树 →
    # 重启 → 导航回 fp 笔记 → 草稿恢复（命名空间稳定至重启）。
    typed3 = False
    for _ in range(3):
        s = snapshot()
        el = fresh_id(s, "oninput: .DraftEdit", 0)
        if el:
            call("autoui_action", element_id=el, action="type_text", value="VM 恢复稿")
        time.sleep(1.5)
        if state_field("fp_edit_state") == "dirty":
            typed3 = True
            break
    check(typed3, "vm-M-5a0-recovery-typed-dirty", state_field("fp_edit_state"))
    time.sleep(0.5)
    # 切到另一条笔记触发 SelectNote 检查点（fp_edit_state=dirty → 持久槽）；
    # 目标行避开 fp 冲突靶行（点击同笔记为无操作，检查点不落）。
    snap9 = snapshot()
    sel2 = None
    import re as _re
    pat = _re.compile(r"#(aura_\d+|vnode_\d+)")
    cur = None
    for line in snap9.splitlines():
        m = pat.search(line)
        if m:
            cur = m.group(1)
        if "onclick: .SelectNote(" in line and cur is not None:
            if "FP 冲突靶" not in line:
                sel2 = cur
                break
    if sel2:
        call("autoui_action", element_id=sel2, action="press")
        time.sleep(1.5)
    slot = http("POST", "/api/fp/draft/get", {"draft_key": draft_key("note:" + fid, "edit")})
    check(slot.get("found") is True and slot.get("text") == "VM 恢复稿" and slot.get("state") == "dirty",
          "vm-M-5a-checkpoint-persisted", str(slot)[:160])
    check(state_field("fp_edit_state") == "idle", "vm-M-5b-switched-away-clean",
          state_field("fp_edit_state"))

    # （重启由外层 main 的 vm_restart 分支承接：本函数返回后 kill/spawn，
    # 再进 run_vm_after_restart 完成恢复断言。）


def run_vm_after_restart(run_dir, mcp_port, fid):
    url = f"http://127.0.0.1:{mcp_port}/mcp"
    n = [0]

    def call(tool, **args):
        n[0] += 1
        req = urllib.request.Request(url, data=json.dumps({
            "jsonrpc": "2.0", "method": "tools/call",
            "params": {"name": tool, "arguments": args}, "id": n[0]}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode())
        c = d.get("result", {}).get("content", [])
        return c[0]["text"] if c else ""

    def snapshot():
        return call("autoui_snapshot")

    def ids_for(snap, pattern):
        import re
        pat = re.compile(r"#(aura_\d+|vnode_\d+)")
        out = []
        cur = None
        for line in snap.splitlines():
            m = pat.search(line)
            if m:
                cur = m.group(1)
            if pattern in line and cur is not None:
                out.append(cur)
        return out

    time.sleep(2)
    slot = http("POST", "/api/fp/draft/get", {"draft_key": draft_key("note:" + fid, "edit")})
    check(slot.get("found") is True and slot.get("text") == "VM 恢复稿",
          "vm-M-6a-slot-survives-restart", str(slot)[:160])
    snap = snapshot()
    (run_dir / "vm_restart_snapshot.txt").write_text(snap, encoding="utf-8")
    # 导航回 fp 笔记 → SelectNote flushed 恢复
    fp_row = None
    import re
    for line in snap.splitlines():
        if "FP 冲突靶" in line:
            m = re.search(r"#(aura_\d+|vnode_\d+)", line)
            if m:
                fp_row = m.group(1)
    if fp_row is not None:
        call("autoui_action", element_id=fp_row, action="press")
        time.sleep(1.5)
    else:
        check(False, "vm-M-6b-fp-row-located", "重启后快照未定位 FP 冲突靶行")
    st = call("autoui_state", fields=["fp_edit_state"])
    check("dirty" in st, "vm-M-6c-edit-state-restored-dirty", st[:120])
    slot2 = http("POST", "/api/fp/draft/get", {"draft_key": draft_key("note:" + fid, "edit")})
    check(slot2.get("found") is True and slot2.get("text") == "VM 恢复稿",
          "vm-M-6d-restored-slot-intact", str(slot2)[:160])
    g = http("POST", "/api/fp/v1/get", {"cred": "c" * 64, "interface_version": IF_V1,
                                        "note_id": "n-" + fid})
    check((g.get("note") or {}).get("body") == "VM 冲突稿",
          "vm-M-6e-server-body-unchanged-by-recovery", str(g)[:120])


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
            http("POST", "/api/notes", {"title": "Seed Note", "body": "seed body",
                                        "folder": "", "request_id": "seed-1"})
            run_vue(run_dir)
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
                print((run_dir / "vm_run.log").read_text(encoding="utf-8", errors="replace")[-1500:])
                return 2
            # 种子（等 back 就绪后灌入；冻结 schema fp 靶）→ 重启自有进程 →
            # Init 在数据在库后重跑（VM 无页面刷新面）。
            deadline = time.time() + 300
            while time.time() < deadline:
                h = http("GET", "/api/health")
                if isinstance(h, dict) and h.get("status") == "ok":
                    break
                time.sleep(2)
            s1 = http("POST", "/api/notes", {"title": "Seed Note", "body": "seed body",
                                             "folder": "", "request_id": "seed-1"})
            cap = http("POST", "/api/fp/v1/capture",
                       {"cred": "c" * 64, "interface_version": IF_V1, "attempt_id": "seed-fp",
                        "operation_id": "d" * 32,
                        "source_json": json.dumps(fp_src("3f2a" * 16), ensure_ascii=False),
                        "text": "原始正文"})
            check(cap.get("ok") is True, "vm-E-0a-fp-seed-captured", cap)
            kill_tree(proc)
            if log_f:
                log_f.close()
            if not wait_ports_free():
                check(False, "vm-boot-restart-ports", "自有端口未释放")
            proc, log_f, mcp_port = spawn(env_extra, run_dir / "vm_run0.log", vm=True)
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
                print("FATAL: VM MCP not ready after seed restart (see", run_dir / "vm_run0.log", ")")
                print((run_dir / "vm_run0.log").read_text(encoding="utf-8", errors="replace")[-1500:])
                return 2
            time.sleep(3)
            run_vm(run_dir, mcp_port)
            # 进程重启（只杀自有树）→ MCP 重新就绪 → 恢复断言
            fid = None
            # fid 从服务笔记列表取 fp 冲突靶行（run_vm 已持久检查点槽）
            docs = http("GET", "/api/v1/notes")
            for d in docs if isinstance(docs, list) else []:
                if isinstance(d, dict) and d.get("title") == "FP 冲突靶":
                    fid = str(d.get("note_id", ""))[2:]
            kill_tree(proc)
            if log_f:
                log_f.close()
            if not wait_ports_free():
                check(False, "vm-restart-ports-freed", "自有端口未释放")
            proc, log_f, mcp_port = spawn(env_extra, run_dir / "vm_run2.log", vm=True)
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
                print("FATAL: VM MCP not ready after restart (see", run_dir / "vm_run2.log", ")")
                print((run_dir / "vm_run2.log").read_text(encoding="utf-8", errors="replace")[-1500:])
                return 2
            if fid:
                run_vm_after_restart(run_dir, mcp_port, fid)
            else:
                check(False, "vm-restart-fid-located", "未从服务端定位 fp 冲突靶 id")
    finally:
        kill_tree(proc)
        if not wait_ports_free():
            # 不做全局 /IM 清扫（r2/S-05、OS-067 G-04/G-05）；残留属异常，
            # 显式失败提示而非静默接管他人进程。
            print("WARN: ports not free after own-tree cleanup; stray process outside this run's tree?")
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
