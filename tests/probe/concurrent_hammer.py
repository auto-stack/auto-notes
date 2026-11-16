#!/usr/bin/env python3
"""concurrent_hammer.py — NOTES-007 并发负载/停摆取证入口（T-01 建，T-03 定版 R-01）。

用法（auto-notes 仓根）：
    python tests/probe/concurrent_hammer.py --mode ui --rounds 20
    python tests/probe/concurrent_hammer.py --mode lockwindow --hold 6
    python tests/probe/concurrent_hammer.py --mode smoke

模式：
  ui          UI 形状并发锤：≥3 并发写者（create/update/capture/draft put）+ ≥3 并发
              读者（list/get/search/status/receipt/fp get/draft get）+ 同修订争用对，
              逐轮断言读延迟/幻影 not_found/幂等回执/数据零丢失。
  lockwindow  确定性放大器取证：外部进程以 FileShare=None 独占 inbox.db（模拟 AV/EDR
              排他扫描窗口），窗口内发读/写，断言"要么正确数据、要么具名失败"，绝不允许
              静默返回幽灵空库（a2r sqlite.open 失败回退内存库的语义放大器）。
  smoke       1 轮 ui（≤10s 快验）。

自管生命周期：隔离 NOTES_DATA_DIR + 临时端口 + 自建 NOTES_FP_POLICY；只回收自有 PID 树。
预备产物：脚本绝不触发编译。后端 exe 解析顺序 = --exe → NOTES_BACK_EXE → 由本仓
rust-workspace/.cargo/config.toml 的 target-dir 与 *-back 成员推导；缺失即具名失败
（先 `cd rust-workspace && cargo build -p <member>`）。

原始证据写 D:/autostack/plan-artifacts/plan-007/（--json-report / --keep 保留运行目录）。
"""
import argparse
import glob as globmod
import json
import os
import random
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[1]
ARTIFACTS = Path(os.environ.get("PLAN_ARTIFACTS_HOME", "D:/autostack/plan-artifacts/plan-007"))
IF_V1 = "notes.fpack/1"
READ_KINDS = {"list", "get", "search", "status", "receipt", "fp_get", "draft_get"}
ALLOWED_ERR = {"second_writer", "revision_conflict", "request_conflict", "storage_unavailable",
               "not_observed", "fault_injected"}

PASS, FAIL, NOTES = [], [], []


def check(cond, name, detail=""):
    if cond:
        PASS.append(name)
        print("PASS", name)
    else:
        FAIL.append(name)
        print("FAIL", name, "-", str(detail)[:400])


def note(msg):
    NOTES.append(msg)
    print("NOTE", msg)


# ── 预备产物解析（禁止在测试体内编译）──────────────────────────────────
def resolve_exe(explicit):
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None
    env = os.environ.get("NOTES_BACK_EXE")
    if env:
        p = Path(env)
        return p if p.exists() else None
    cfg = ROOT / "rust-workspace" / ".cargo" / "config.toml"
    target = None
    if cfg.exists():
        for line in cfg.read_text(encoding="utf-8").splitlines():
            if "target-dir" in line and "=" in line:
                target = line.split("=", 1)[1].strip().strip('"').replace("/", os.sep)
    members = sorted(p for p in (ROOT / "rust-workspace").glob("*-back")
                     if (p / "Cargo.toml").exists()) if (ROOT / "rust-workspace").exists() else []
    if target and members:
        cand = Path(target) / "debug" / (members[-1].name + ".exe")
        if cand.exists():
            return cand
    if target:
        cands = globmod.glob(str(Path(target) / "debug" / "auto-notes-*-back.exe"))
        cands = [Path(c) for c in cands if Path(c).exists()]
        if cands:
            return max(cands, key=lambda p: p.stat().st_mtime)
    return None


def free_port(start=17951):
    for port in range(start, start + 200):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("no free port")


# ── 服务生命周期 ──────────────────────────────────────────────────────
class Service:
    def __init__(self, exe, run_dir, policy):
        self.exe = exe
        self.port = free_port()
        self.data_dir = run_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.policy_path = run_dir / "fp-policy.json"
        self.policy_path.write_text(json.dumps(policy), encoding="utf-8")
        self.log_path = run_dir / "service.log"
        self.proc = None
        self.log_f = None

    @property
    def base(self):
        return f"http://127.0.0.1:{self.port}"

    def start(self, timeout=120):
        env = dict(os.environ)
        env.update({
            "NOTES_DATA_DIR": str(self.data_dir),
            "NOTES_TEST_MODE": "1",
            "AUTO_ALLOW_PARTIAL_DB": "1",
            "AUTO_HTTP_PORT": str(self.port),
            "NOTES_FP_POLICY": str(self.policy_path),
        })
        env.pop("NOTES_FAULT", None)
        env.pop("NOTES_LEGACY_FILE", None)
        self.log_f = open(self.log_path, "w", encoding="utf-8")
        self.proc = subprocess.Popen([str(self.exe)], env=env, cwd=str(ROOT),
                                     stdout=self.log_f, stderr=subprocess.STDOUT,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                return False, f"service exited rc={self.proc.returncode} (see {self.log_path})"
            try:
                with urllib.request.urlopen(self.base + "/api/health", timeout=2) as r:
                    if r.status == 200:
                        return True, ""
            except Exception:
                pass
            time.sleep(0.1)
        return False, f"service not ready in {timeout}s (see {self.log_path})"

    def stop(self):
        if self.proc and self.proc.poll() is None:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)],
                           capture_output=True)
        if self.log_f:
            try:
                self.log_f.close()
            except Exception:
                pass

    def http(self, method, path, body=None, timeout=30):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read().decode()
                status = r.status
        except urllib.error.HTTPError as e:
            try:
                raw = e.read().decode()
            except Exception:
                raw = ""
            status = e.code
        except Exception as e:  # transport failure: never silently a value
            return {"__transport_error": str(e), "__ms": (time.perf_counter() - t0) * 1000, "__status": 0}
        ms = (time.perf_counter() - t0) * 1000
        try:
            val = json.loads(raw) if raw else None
        except Exception:
            val = {"__badjson": raw[:300]}
        # str 端点的信封是 JSON 字符串（双层编码），按服务面既有约定再解一层
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except Exception:
                val = {"__badjson": val[:300]}
        # typed 数组端点（[]NoteDocument）原样为 list：包一层以携带计时/状态
        if isinstance(val, list):
            val = {"__list": val, "__ms": ms, "__status": status}
        elif isinstance(val, dict):
            val["__ms"] = ms
            val["__status"] = status
        else:
            val = {"__scalar": val, "__ms": ms, "__status": status}
        return val


# ── 负载元件 ──────────────────────────────────────────────────────────
def make_policy():
    return {"entries": [
        {"cred": "c" * 64, "principal": "hammer",
         "operations": ["capture", "read", "update", "receipt", "list_by_book"],
         "book_scopes": ["book:hammer"]},
    ]}


CRED = "c" * 64
SRC = {"book_id": "book:hammer", "source_hash": "7a" * 32, "title": "并发锤书名",
       "author": "作者", "quote": "原句：并发读写的放大器取证 🎯", "chapter": 3,
       "locator": {"kind": "cfi", "v": 1, "value": "epubcfi(i/4!)"}}
SRC_JSON = json.dumps(SRC, ensure_ascii=False)


def op_id(rnd, seq, tag=0):
    """32 hex chars（contract 形状）；(rnd,seq,tag) 决定唯一性。"""
    return ("%08x" % ((rnd * 1000003 + seq * 7919 + tag * 104729) & 0xFFFFFFFF)) * 4


class Stats:
    def __init__(self):
        self.lock = threading.Lock()
        self.samples = []   # (kind, ms, ok, err_code)
        self.unexpected = []

    def add(self, kind, res):
        ms = res.get("__ms", 0.0)
        ok = bool(res.get("ok")) if "ok" in res else None
        code = res.get("err_code", "")
        with self.lock:
            self.samples.append((kind, ms, ok, code))
            if "__transport_error" in res or "__badjson" in res:
                self.unexpected.append((kind, res.get("__transport_error") or res.get("__badjson")))

    def pct(self, kind, p):
        vals = sorted(ms for k, ms, _, _ in self.samples if k == kind)
        if not vals:
            return 0.0
        idx = min(len(vals) - 1, int(round((p / 100.0) * (len(vals) - 1))))
        return vals[idx]

    def max_ms(self, kinds):
        return max((ms for k, ms, _, _ in self.samples if k in kinds), default=0.0)


def read_once(svc, stats, known):
    """一个读者轮次：按 UI 消费面轮流发读请求。"""
    nid, rid, opid = known["nid"], known["rid"], known["opid"]
    fp_nid = known.get("fp_nid") or nid
    plan = [
        ("list", "GET", "/api/v1/notes", None),
        ("get", "GET", f"/api/v1/notes/{nid}", None),
        ("status", "GET", "/api/v1/status", None),
        ("search", "GET", "/api/notes/search?query=" + urllib.parse.quote("并发"), None),
        ("receipt", "POST", "/api/fp/v1/receipt",
         {"cred": CRED, "interface_version": IF_V1, "operation_id": opid}),
        ("draft_get", "POST", "/api/fp/draft/get", {"draft_key": "hammer|host|n-1|i"}),
        ("fp_get", "POST", "/api/fp/v1/get",
         {"cred": CRED, "interface_version": IF_V1, "note_id": fp_nid}),
    ]
    for kind, method, path, body in plan:
        res = svc.http(method, path, body, timeout=20)
        stats.add(kind, res)
        if kind == "get":
            # 幻影 not_found / 空文档 = 读快照冻结特征，绝不接受
            if not (res.get("ok") is True and (res.get("doc") or {}).get("note_id") == nid):
                check(False, "R-01-get-phantom", {"want": nid, "got": res})
        if kind == "list":
            items = res.get("__list")
            if not (isinstance(items, list) and len(items) > 0):
                check(False, "R-01-list-phantom", res)
        if kind == "fp_get":
            if not (res.get("ok") is True and (res.get("note") or {}).get("note_id") == fp_nid):
                check(False, "R-01-fp-get-phantom", res)
        if kind == "receipt":
            if res.get("status") != "committed":
                check(False, "R-01-receipt-stable", res)


def writer_once(svc, stats, rnd, seq, own):
    """一个写者轮次：create → update（自持修订）→ draft put → capture/relay。"""
    rid = f"hammer-c-{rnd}-{seq}-{own['id']}"
    res = svc.http("POST", "/api/v1/notes",
                   {"title": f"T{rnd}-{seq}", "body": "并发写者正文 α", "folder": "",
                    "request_id": rid}, timeout=20)
    stats.add("create", res)
    if res.get("ok") is True:
        nid = (res.get("doc") or {}).get("note_id", "")
        rev = (res.get("doc") or {}).get("revision", 1)
        with stats.lock:
            own["created"].append((rid, nid))
        urid = f"hammer-u-{rnd}-{seq}-{own['id']}"
        ures = svc.http("PUT", f"/api/v1/notes/{nid}",
                        {"expected_revision": rev, "title": f"T{rnd}-{seq}!",
                         "body": "并发更新正文 β", "request_id": urid}, timeout=20)
        stats.add("update", ures)
        code = ures.get("err_code", "")
        if ures.get("ok") is not True and code not in ("revision_conflict", "second_writer"):
            check(False, "R-01-update-named", ures)
        if code == "not_found":
            check(False, "R-01-update-phantom-not-found", ures)
    key = f"hammer|host|k{rnd}-{seq}-{own['id']}|i"
    dres = svc.http("POST", "/api/fp/draft/put",
                    {"draft_key": key, "text": "草稿正文 γ", "state": "dirty",
                     "op": "capture", "base_rev": 0, "input_ver": 1}, timeout=20)
    stats.add("draft_put", dres)
    # capture：每个写者独立 op（同 op 同载荷重放证明幂等回执不变）
    op = op_id(rnd, seq, own["id"])
    cap_body = {"cred": CRED, "interface_version": IF_V1, "attempt_id": f"a-{rnd}-{seq}",
                "operation_id": op, "source_json": SRC_JSON,
                "text": f"捕获正文 r{rnd} s{seq} ✅"}
    cres = svc.http("POST", "/api/fp/v1/capture", cap_body, timeout=20)
    stats.add("capture", cres)
    if cres.get("ok") is True:
        cnid = (cres.get("note") or {}).get("note_id", "")
        with stats.lock:
            own["captures"].append((op, cnid))
        rep = svc.http("POST", "/api/fp/v1/capture", cap_body, timeout=20)
        stats.add("capture_replay", rep)
        if rep.get("ok") is not True or rep.get("replayed") is not True \
                or (rep.get("note") or {}).get("note_id") != cnid:
            check(False, "R-01-capture-replay", {"first": cres, "replay": rep})


def run_ui(svc, rounds, max_seconds, stats, known):
    deadline = time.time() + max_seconds
    done_rounds = 0
    for rnd in range(rounds):
        if time.time() > deadline:
            note(f"ui: 预算 {max_seconds}s 用尽，完成 {done_rounds}/{rounds} 轮")
            break
        owns = [{"id": i, "created": [], "captures": []} for i in range(3)]
        threads = []
        for i, own in enumerate(owns):
            t = threading.Thread(target=lambda o=own: [writer_once(svc, stats, rnd, s, o) for s in range(3)])
            threads.append(t)
        for i in range(3):
            t = threading.Thread(target=lambda: [read_once(svc, stats, known) for _ in range(3)])
            threads.append(t)
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=180)
        done_rounds += 1
        # 同修订争用对：两写者对同一 note 同 expected_revision，恰一成功
        if known.get("nid") and known.get("rev"):
            results = []
            rlock = threading.Lock()

            def contend(tag):
                res = svc.http("PUT", f"/api/v1/notes/{known['nid']}",
                               {"expected_revision": known["rev"],
                                "title": f"contend-{tag}", "body": f"contend body {tag}",
                                "request_id": f"hammer-x-{rnd}-{tag}"}, timeout=20)
                with rlock:
                    results.append(res)
                stats.add("update_contend", res)

            ts = [threading.Thread(target=contend, args=(t,)) for t in ("a", "b")]
            for t in ts:
                t.start()
            for t in ts:
                t.join(timeout=60)
            winners = [r for r in results if r.get("ok") is True]
            losers = [r for r in results if r.get("ok") is not True]
            check(len(winners) == 1 and len(losers) == 1, f"R-01-contend-r{rnd}",
                  [(r.get("ok"), r.get("err_code")) for r in results])
            if winners:
                known["rev"] = (winners[0].get("doc") or {}).get("revision", known["rev"])
            elif losers:
                check(all(r.get("err_code") == "second_writer" for r in losers),
                      f"R-01-contend-named-r{rnd}", [r.get("err_code") for r in losers])
        # 每轮必查：读延迟上限 + 数据零丢失 + 幻影 not_found
        for own in owns:
            for rid, nid in own["created"]:
                g = svc.http("GET", f"/api/v1/notes/{nid}", timeout=20)
                if not (g.get("ok") is True and (g.get("doc") or {}).get("note_id") == nid):
                    check(False, f"R-01-durable-r{rnd}", {"nid": nid, "got": g})
    return done_rounds


def run_lockwindow(svc, hold):
    """确定性放大器：外部独占 inbox.db 句柄窗口内的读/写行为。"""
    db = Path(svc.data_dir) / "inbox.db"
    known_ids = []
    for i in range(3):
        r = svc.http("POST", "/api/v1/notes",
                     {"title": f"lock-{i}", "body": "窗口前落盘", "folder": "",
                      "request_id": f"lock-pre-{i}"}, timeout=20)
        if r.get("ok") is True:
            known_ids.append((r.get("doc") or {}).get("note_id", ""))
    check(len(known_ids) == 3, "LW-pre-create", known_ids)
    base = [svc.http("GET", "/api/v1/notes", timeout=10) for _ in range(3)]
    check(all(isinstance(b.get("__list"), list) and len(b["__list"]) >= 3 for b in base),
          "LW-baseline-list", [len(b.get("__list") or []) for b in base])
    base_ms = max(b.get("__ms", 0) for b in base if isinstance(b, dict))
    note(f"lockwindow: baseline list max {base_ms:.1f}ms, hold={hold}s, db={db}")

    if os.name != "nt":
        note("lockwindow 需要 Windows FileShare 语义，跳过")
        return
    holder = subprocess.Popen([
        "pwsh", "-NoProfile", "-Command",
        "$fs=[System.IO.File]::Open('" + str(db).replace("'", "''") + "','Open','ReadWrite','None'); "
        "Write-Output 'HELD'; Start-Sleep -Seconds " + str(hold) + "; $fs.Close(); Write-Output 'RELEASED'",
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    line = holder.stdout.readline().strip()
    check(line == "HELD", "LW-holder-held", line)
    window = []
    t_end = time.time() + hold
    try:
        while time.time() < t_end and len(window) < 6:
            # 四路并发取样：写（幽灵写面）+ 单读（幻影 not_found 面）+ 列表/状态（幽灵空库面）
            slot = {}

            def fire(tag, fn):
                slot[tag] = fn()

            ts = [
                threading.Thread(target=fire, args=("create", lambda: svc.http(
                    "POST", "/api/v1/notes",
                    {"title": "窗口内创建", "body": "窗口内正文", "folder": "",
                     "request_id": f"lock-in-{len(window)}"}, timeout=15))),
                threading.Thread(target=fire, args=("get", lambda: svc.http(
                    "GET", f"/api/v1/notes/{known_ids[0]}", timeout=15))),
                threading.Thread(target=fire, args=("list", lambda: svc.http(
                    "GET", "/api/v1/notes", timeout=15))),
                threading.Thread(target=fire, args=("status", lambda: svc.http(
                    "GET", "/api/v1/status", timeout=15))),
            ]
            for t in ts:
                t.start()
            for t in ts:
                t.join(timeout=40)
            window.append({"get": slot.get("get", {}), "list": slot.get("list", {}),
                           "status": slot.get("status", {}), "create": slot.get("create", {})})
            time.sleep(0.2)
    finally:
        holder.stdout.read()
        holder.wait(timeout=60)

    # 窗口内行为必须"要么正确、要么具名失败"：绝不允许幽灵空库
    for i, w in enumerate(window):
        g, lst, st, c = w["get"], w["list"], w["status"], w["create"]
        g_ok = g.get("ok") is True and (g.get("doc") or {}).get("note_id") == known_ids[0]
        g_named = g.get("ok") is False and g.get("err_code") in ("storage_unavailable", "second_writer")
        check(g_ok or g_named, f"LW-get-r{i}", g)
        st_named = (st.get("storage_error") or "") in ("storage_unavailable", "second_writer")
        st_honest = st.get("loaded") is False or (st.get("entries", 0) >= 3 and (st.get("storage_error") or "") == "")
        check(st_named or st_honest, f"LW-status-r{i}", st)
        if isinstance(lst.get("__list"), list) and len(lst["__list"]) == 0:
            # 空列表只有在状态面同时具名报错时才可接受
            check(st_named, f"LW-list-phantom-r{i}", {"list": lst.get("__list"), "status_err": st.get("storage_error")})
        c_ok = c.get("ok") is True
        c_named = c.get("err_code") in ("storage_unavailable", "second_writer")
        check(c_ok or c_named, f"LW-create-r{i}", c)

    # 释放后：数据必须完整、窗口内 ok=true 的写必须真的落盘
    after = svc.http("GET", "/api/v1/notes", timeout=20).get("__list")
    check(isinstance(after, list) and len(after) >= 3, "LW-after-intact", after)
    ids_after = {d.get("note_id") for d in after} if isinstance(after, list) else set()
    for i, w in enumerate(window):
        if w["create"].get("ok") is True:
            nid = (w["create"].get("doc") or {}).get("note_id", "")
            check(nid in ids_after, f"LW-write-persisted-r{i}", {"nid": nid, "have": sorted(ids_after)})
    note("lockwindow: 窗口内 %d 组取样完成" % len(window))
    raw = []
    for i, w in enumerate(window):
        g, lst, st, c = w["get"], w["list"], w["status"], w["create"]
        raw.append({
            "i": i,
            "get_ms": round(g.get("__ms", 0), 1), "get_ok": g.get("ok"),
            "get_code": g.get("err_code"), "get_note": (g.get("doc") or {}).get("note_id", ""),
            "list_len": len(lst.get("__list") or []), "list_ms": round(lst.get("__ms", 0), 1),
            "status_loaded": st.get("loaded"), "status_entries": st.get("entries"),
            "status_err": st.get("storage_error"), "status_ms": round(st.get("__ms", 0), 1),
            "create_ok": c.get("ok"), "create_code": c.get("err_code"),
            "create_nid": (c.get("doc") or {}).get("note_id", ""),
            "create_ms": round(c.get("__ms", 0), 1),
        })
    return {"hold_s": hold, "window": raw}


def summarise(stats, rounds_done, elapsed, total_notes):
    kinds = ["list", "get", "status", "search", "receipt", "draft_get", "fp_get",
             "create", "update", "draft_put", "capture", "capture_replay", "update_contend"]
    table = {}
    for k in kinds:
        vals = [ms for kk, ms, _, _ in stats.samples if kk == k]
        if not vals:
            continue
        table[k] = {"n": len(vals), "p50": round(stats.pct(k, 50), 1),
                    "p95": round(stats.pct(k, 95), 1), "p99": round(stats.pct(k, 99), 1),
                    "max": round(max(vals), 1)}
    reads = stats.max_ms(READ_KINDS)
    check(reads <= 2000.0, "R-01-read-p99-budget", f"max_read={reads:.1f}ms budget=2000ms")
    check(not stats.unexpected, "R-01-no-transport-errors", stats.unexpected[:3])
    bad = [(k, code) for k, _, ok, code in stats.samples
           if code and code not in ALLOWED_ERR]
    check(not bad, "R-01-errors-named", bad[:5])
    return {"rounds_done": rounds_done, "elapsed_s": round(elapsed, 1),
            "notes_total": total_notes, "latency_ms": table,
            "read_max_ms": round(reads, 1), "samples": len(stats.samples)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["ui", "lockwindow", "smoke"], default="ui")
    ap.add_argument("--rounds", type=int, default=20)
    ap.add_argument("--max-seconds", type=float, default=300.0)
    ap.add_argument("--hold", type=float, default=6.0)
    ap.add_argument("--exe", default="")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--json-report", default="")
    args = ap.parse_args()
    if args.mode == "smoke":
        args.rounds = 1

    exe = resolve_exe(args.exe)
    if not exe:
        print("FATAL 预备产物缺失: 未找到已构建的生成后端 exe。先执行：")
        print("  cd rust-workspace && cargo build -p <auto-notes-*-back>")
        return 2
    note(f"exe={exe} ({exe.stat().st_mtime_ns // 10**9})")

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix=f"{args.mode}-", dir=str(ARTIFACTS)))
    svc = Service(exe, run_dir, make_policy())
    if args.port:
        svc.port = args.port
    started = time.time()
    stats = Stats()
    rounds_done = 0
    summary = {}
    try:
        ok, why = svc.start()
        if not ok:
            print("FATAL", why)
            return 2
        # 预热：建一条已知 note + 一次 capture（读面锚点）
        r = svc.http("POST", "/api/v1/notes",
                     {"title": "预热", "body": "预热正文", "folder": "", "request_id": "warm-1"},
                     timeout=20)
        nid = (r.get("doc") or {}).get("note_id", "")
        rev = (r.get("doc") or {}).get("revision", 1)
        op = op_id(0, 0)
        cap = svc.http("POST", "/api/fp/v1/capture",
                       {"cred": CRED, "interface_version": IF_V1, "attempt_id": "warm-a",
                        "operation_id": op, "source_json": SRC_JSON, "text": "预热捕获"}, timeout=20)
        fp_nid = (cap.get("note") or {}).get("note_id", "") or nid
        known = {"nid": nid, "rid": "warm-1", "opid": op, "rev": rev, "fp_nid": fp_nid}
        check(bool(nid) and bool(fp_nid), "T-00-warmup", {"create": r, "capture": cap})

        if args.mode == "lockwindow":
            summary = run_lockwindow(svc, args.hold)
            note("lockwindow summary " + json.dumps(summary, ensure_ascii=False))
        else:
            rounds_done = run_ui(svc, args.rounds, args.max_seconds, stats, known)
            check(rounds_done >= args.rounds, "R-01-rounds", f"{rounds_done}/{args.rounds}")
            # 终局：数据零丢失
            fresp = svc.http("GET", "/api/v1/notes", timeout=30)
            final = fresp.get("__list")
            summary = summarise(stats, rounds_done, time.time() - started,
                                len(final) if isinstance(final, list) else -1)
            note("summary " + json.dumps(summary, ensure_ascii=False))
            ids = [d.get("note_id") for d in final] if isinstance(final, list) else []
            check(len(ids) == len(set(ids)), "R-01-unique-ids", len(ids))
    finally:
        svc.stop()
        report = dict(summary)
        report.update({"mode": args.mode, "pass": PASS, "fail": FAIL, "notes": NOTES,
                       "run_dir": str(run_dir), "exe": str(exe)})
        out = Path(args.json_report) if args.json_report else (run_dir / "hammer-report.json")
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print("WARN report write failed:", e)
        print(f"report: {out}")
        if not args.keep:
            shutil.rmtree(run_dir, ignore_errors=True)
            print("run_dir removed (--keep to retain)")

    print(f"PASS {len(PASS)}  FAIL {len(FAIL)}")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())