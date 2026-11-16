#!/usr/bin/env python3
"""storage_trace.py — NOTES-007 R-02：存储并发模型的代码级/运行时追踪断言。

用法（auto-notes 仓根）：
    python tests/probe/storage_trace.py                 # 全部断言
    python tests/probe/storage_trace.py --skip-static   # 只跑运行时
    python tests/probe/storage_trace.py --exe PATH

断言（AC-02 / R-02）：
  S-01 静态：生成后端的读路径函数（repo_get/repo_list_active/repo_search/
       read_receipt/repo_status/fp_get/fp_list_by_book/fp_receipt/fp_draft_get/
       fp_source_of_view）函数体内零 `BEGIN IMMEDIATE`、零 `ALTER TABLE`、
       零 meta 写（`INSERT OR REPLACE INTO meta`）、零 ensure_schema 调用，
       且恰好一次 `sqlite::open`（单连接）。
  S-02 静态：写路径仍以 BEGIN IMMEDIATE 为门禁（second_writer 具名面不回退）。
  R-01 运行时：全新库首请求后 `storage_schema_init` 日志恰好 1 行；随后 30 次
       读请求不再新增（schema/迁移就绪后零重跑）。
  R-02 运行时：同一数据目录重启服务 → 0 行新的 schema init（跨进程不重跑）。
  R-03 运行时：外部写锁（另一连接 BEGIN IMMEDIATE 持有 5s）期间读请求
       ≤2000ms 且返回真实数据（读路径不等待写锁 = 零写锁）。
  R-04 运行时：/api/v1/status 的 storage_error 字段在健康态为空。
"""
import argparse
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[1]
ARTIFACTS = Path(os.environ.get("PLAN_ARTIFACTS_HOME", "D:/autostack/plan-artifacts/plan-007"))
READ_FNS = ["repo_get", "repo_list_active", "repo_search", "read_receipt", "repo_status",
            "fp_get", "fp_list_by_book", "fp_receipt", "fp_draft_get", "fp_source_of_view"]
WRITE_FNS = ["repo_create", "repo_update", "repo_set_meta", "fp_capture", "fp_update"]
PASS, FAIL = [], []


def check(cond, name, detail=""):
    if cond:
        PASS.append(name)
        print("PASS", name)
    else:
        FAIL.append(name)
        print("FAIL", name, "-", str(detail)[:400])


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
    return None


def member_src():
    members = sorted(p for p in (ROOT / "rust-workspace").glob("*-back")
                     if (p / "Cargo.toml").exists()) if (ROOT / "rust-workspace").exists() else []
    return members[-1] / "src" / "repository.rs" if members else None


def fn_body(text, name):
    """抓 `[pub] fn name(` 到下一个顶层 `pub fn`/`fn` 开头。"""
    m = re.search(r"^(?:pub )?fn %s\(" % re.escape(name), text, re.M)
    if not m:
        return None
    rest = text[m.start():]
    nxt = re.search(r"^(?:pub )?fn \w+\(", rest[1:], re.M)
    return rest[1:nxt.start() + 1] if nxt else rest


def free_port(start=17971):
    for port in range(start, start + 120):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("no free port")


class Service:
    def __init__(self, exe, data_dir, port):
        self.exe, self.data_dir, self.port = exe, data_dir, port
        self.log = data_dir / f"svc-{port}.log"
        self.proc = None

    def start(self, timeout=120):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        env.update({"NOTES_DATA_DIR": str(self.data_dir), "NOTES_TEST_MODE": "1",
                    "AUTO_ALLOW_PARTIAL_DB": "1", "AUTO_HTTP_PORT": str(self.port)})
        env.pop("NOTES_FAULT", None)
        f = open(self.log, "a", encoding="utf-8")
        self.proc = subprocess.Popen([str(self.exe)], env=env, cwd=str(ROOT),
                                     stdout=f, stderr=subprocess.STDOUT,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/api/health", timeout=2) as r:
                    if r.status == 200:
                        return True
            except Exception:
                pass
            if self.proc.poll() is not None:
                return False
            time.sleep(0.1)
        return False

    def stop(self):
        if self.proc and self.proc.poll() is None:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)], capture_output=True)

    def http(self, method, path, body=None, timeout=20):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method)
        req.add_header("Content-Type", "application/json")
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read().decode()
        except Exception as e:
            return {"__err": str(e), "__ms": (time.perf_counter() - t0) * 1000}
        ms = (time.perf_counter() - t0) * 1000
        try:
            val = json.loads(raw)
            if isinstance(val, str):
                val = json.loads(val)
        except Exception:
            val = {"__badjson": raw[:200]}
        if isinstance(val, list):
            return {"__list": val, "__ms": ms}
        val["__ms"] = ms
        return val


def count_init(log_path):
    if not log_path.exists():
        return 0
    return sum(1 for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines()
               if line.startswith("storage_schema_init"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default="")
    ap.add_argument("--skip-static", action="store_true")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--json-report", default="")
    args = ap.parse_args()
    exe = resolve_exe(args.exe)
    if not exe:
        print("FATAL 预备产物缺失：先 cd rust-workspace && cargo build -p <auto-notes-*-back>")
        return 2
    print("exe:", exe)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="trace-", dir=str(ARTIFACTS)))

    # ── 静态断言 ─────────────────────────────────────────────────────
    src = member_src()
    if not args.skip_static:
        check(src is not None and src.exists(), "S-00-generated-source", src)
        text = src.read_text(encoding="utf-8")
        for name in READ_FNS:
            body = fn_body(text, name)
            if body is None:
                check(False, f"S-01-{name}-present", "function not found in generated source")
                continue
            check("BEGIN IMMEDIATE" not in body, f"S-01-{name}-no-begin-immediate")
            check("ALTER TABLE" not in body, f"S-01-{name}-no-alter")
            check("INSERT OR REPLACE INTO meta" not in body, f"S-01-{name}-no-meta-write")
            # 就绪探针走 ensure_schema_once（具名慢路径，仅未就绪时进入）；
            # 完整 DDL 体 ensure_schema(db) 绝不得出现在读路径函数里。
            check("ensure_schema(db" not in body, f"S-01-{name}-no-full-ddl")
            check("ensure_schema_once" not in body or name == "repo_status",
                  f"S-01-{name}-no-schema-entry")
            opens = body.count("sqlite::open")
            check(opens == 1, f"S-01-{name}-single-open", f"sqlite::open count={opens}")
        for name in WRITE_FNS:
            body = fn_body(text, name)
            if body is None:
                check(False, f"S-02-{name}-present", "function not found")
                continue
            check("BEGIN IMMEDIATE" in body, f"S-02-{name}-begin-immediate")
            check("second_writer" in body, f"S-02-{name}-named-second-writer")

    # ── 运行时 ───────────────────────────────────────────────────────
    data_dir = run_dir / "data"
    port = free_port()
    svc = Service(exe, data_dir, port)
    try:
        ok = svc.start()
        check(ok, "R-00-service-started", svc.log)
        if not ok:
            return 2
        r = svc.http("POST", "/api/v1/notes", {"title": "trace", "body": "b", "folder": "",
                                               "request_id": "trace-1"})
        check(r.get("ok") is True, "R-00-warmup-create", r)
        nid = (r.get("doc") or {}).get("note_id", "")
        for _ in range(30):
            svc.http("GET", "/api/v1/notes")
            svc.http("GET", f"/api/v1/notes/{nid}")
            svc.http("GET", "/api/notes/search?query=trace")
            svc.http("GET", "/api/v1/status")
        inits = count_init(svc.log)
        check(inits == 1, "R-01-schema-init-once-fresh-db", f"storage_schema_init lines={inits}")
        st = svc.http("GET", "/api/v1/status")
        check(st.get("storage_error") == "" and st.get("loaded") is True,
              "R-04-status-healthy-storage-error-empty", st)

        # 重启同一数据目录 → 不重跑 schema
        svc.stop()
        mark = len(svc.log.read_text(encoding="utf-8", errors="replace").splitlines())
        svc.port = free_port(port + 1)
        svc.log = data_dir / f"svc-{svc.port}.log"
        ok = svc.start()
        check(ok, "R-02-restart-started", svc.log)
        if ok:
            svc.http("GET", "/api/v1/notes")
            svc.http("GET", "/api/v1/status")
            check(count_init(svc.log) == 0, "R-02-schema-init-skipped-on-restart",
                  f"lines={count_init(svc.log)}")

            # 外部写锁窗口：读路径不得等待写锁
            db = sqlite3.connect(str(data_dir / "inbox.db"), timeout=10, isolation_level=None)
            db.execute("PRAGMA busy_timeout=5000")
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO notes(note_id, legacy_id) VALUES('n-trace-lock', 999999)")
            held = []
            try:
                t_end = time.time() + 4.0
                while time.time() < t_end:
                    g = svc.http("GET", f"/api/v1/notes/{nid}")
                    l = svc.http("GET", "/api/v1/notes")
                    s = svc.http("GET", "/api/v1/status")
                    held.append((g, l, s))
                    time.sleep(0.2)
            finally:
                db.execute("ROLLBACK")
                db.close()
            ok_get = all(x[0].get("ok") is True and (x[0].get("doc") or {}).get("note_id") == nid
                         for x in held)
            max_ms = max([x[0].get("__ms", 0) for x in held] + [x[1].get("__ms", 0) for x in held])
            check(ok_get, "R-03-read-correct-under-write-lock",
                  [(x[0].get("ok"), x[0].get("err_code")) for x in held])
            check(max_ms <= 2000.0, "R-03-read-not-blocked-by-write-lock",
                  f"max_read_ms={max_ms:.1f} samples={len(held)}")
            check(all(len(x[1].get("__list") or []) > 0 for x in held),
                  "R-03-list-nonempty-under-write-lock", [len(x[1].get("__list") or []) for x in held])
            print(f"NOTE read-under-write-lock: samples={len(held)} max_ms={max_ms:.1f}")
    finally:
        svc.stop()
        if not args.keep:
            import shutil
            shutil.rmtree(run_dir, ignore_errors=True)
        else:
            print("kept:", run_dir)
        report = {"pass": PASS, "fail": FAIL, "exe": str(exe)}
        out = Path(args.json_report) if args.json_report else (run_dir / "trace-report.json")
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print("report:", out)
        except Exception as e:
            print("WARN report:", e)
    print(f"PASS {len(PASS)}  FAIL {len(FAIL)}")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())