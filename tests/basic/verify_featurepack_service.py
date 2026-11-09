#!/usr/bin/env python3
"""verify_featurepack_service.py — NOTES-006 T-02 服务面永久验证入口（V-01/AC-01 服务级）。

用法（auto-notes 仓根）：
    python tests/basic/verify_featurepack_service.py            # 自管服务生命周期（默认）
    python tests/basic/verify_featurepack_service.py --url URL  # 外部已启服务（跳过生命周期）

覆盖（NOTES-006 §6 V-01 + AC-01 服务级拒绝面；契约 featurepack-v0 §2/§5）：
  F-01 旧库升级：隔离目录 + legacy 样例迁移，既有无来源便签照常读写（行数/标题核对）。
  F-02 fp capture 合法：来源快照（中文/emoji 原文）+ 正文 → note_id/revision=1；fp_get 往返
       book_id/source 逐字相等（Unicode 不 trim 不规范化）。
  F-03 capture 重放：同 (principal, operation_id) 同载荷 → 原收据/文档 replayed=true，行数不变。
  F-04 capture 异载荷：同键不同 text → request_conflict（契约 operation_conflict），行数不变。
  F-05 fp update：expected_revision 条件更新 → rev2；title（来源原句）不可变。
  F-06 update 重放：同 operation_id 重试 → rev2 replayed=true（跨重试幂等，不重复推进）。
  F-07 过期修订：expected_revision=1（现 rev2）→ revision_conflict + current_revision，正文不变。
  F-08 并发更新：双线程同 expected_revision → 恰一成功，终局 revision 唯一。
  F-09 按书分页：book 列表含捕获行；limit=1 + next_cursor 翻页；未授权书列表为空（拒绝面同源）。
  F-10 拒绝面（全部业务前、无写入）：无凭据 / 错作用域 / 越操作 / 版本不合 / 无来源便签宿主不可见。
  F-11 回执查询：committed 返回原收据；未知 operation → not_observed。

约定（计划 §6）：隔离目录、断言失败返回非零；原始日志 D:/autostack/plan-artifacts/plan-006/。
前置：auto CLI（PATH 或 AUTO_EXE）；端口 17819 空闲（--auto 时）。
"""
import argparse
import json
import os
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
LEGACY_FIXTURE = ROOT / "tests" / "fixtures" / "inbox" / "legacy-v0" / "notes-valid.json"
ARTIFACTS = Path(os.environ.get("PLAN_ARTIFACTS_HOME", "D:/autostack/plan-artifacts/plan-006"))
IF_V1 = "notes.fpack/1"
IF_V2 = "notes.fpack/2"

PASS, FAIL = [], []


def check(cond, name, detail=""):
    if cond:
        PASS.append(name)
        print("PASS", name)
    else:
        FAIL.append(name)
        print("FAIL", name, "-", str(detail)[:300])


def http(method, path, body=None, base="http://127.0.0.1:17819"):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            out = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            out = json.loads(e.read().decode())
        except Exception:
            out = {"__status": e.code}
    except Exception:
        out = {"__status": 0}
    if isinstance(out, str):
        try:
            out = json.loads(out)
        except Exception:
            pass
    return out


def free_port(start=17819):
    return start  # pac.at back_port；--auto 前置要求空闲


def spawn_service(data_dir, policy_path, legacy_file, log_path):
    env = dict(os.environ)
    env["NOTES_DATA_DIR"] = str(data_dir)
    env["NOTES_TEST_MODE"] = "1"
    env["NOTES_FP_POLICY"] = str(policy_path)
    env["NOTES_LEGACY_FILE"] = str(legacy_file)
    exe = os.environ.get("AUTO_EXE", "auto")
    log_f = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen([exe, "service", "--server", "rust", "-B", "17819"],
                            cwd=str(ROOT), env=env, stdout=log_f,
                            stderr=subprocess.STDOUT,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return proc, log_f


def wait_ready(timeout=900):
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = http("GET", "/api/v1/status")
        if "__status" not in st:
            return True
        time.sleep(2)
    return False


def kill_tree(proc):
    if proc and proc.poll() is None:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        time.sleep(1)


def notes_count():
    arr = http("GET", "/api/v1/notes")
    if isinstance(arr, list):
        return len(arr)
    return -1


def qs(params):
    """Query string with proper URL encoding（服务端按名绑定 query 参数）。"""
    return "?" + urllib.parse.urlencode(params) if params else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="", help="外部已启服务基址（跳过自管生命周期）")
    ap.add_argument("--keep", action="store_true", help="保留隔离目录与日志")
    args = ap.parse_args()

    external = bool(args.url)
    base = args.url or "http://127.0.0.1:17819"
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="fpv01-", dir=str(ARTIFACTS)))
    proc = None
    log_f = None

    try:
        # ── 隔离目录 + policy ──────────────────────────────────────
        data_dir = run_dir / "data"
        legacy = run_dir / "notes.json"
        shutil.copyfile(LEGACY_FIXTURE, legacy)
        policy = {
            "entries": [
                {"cred": "c" * 64, "principal": "fp-reader",
                 "operations": ["capture", "read", "update", "receipt", "list_by_book"],
                 "book_scopes": ["book:abc123"]},
                {"cred": "r" * 64, "principal": "fp-readonly",
                 "operations": ["read"], "book_scopes": ["book:abc123"]},
                {"cred": "o" * 64, "principal": "fp-otherbook",
                 "operations": ["capture", "read", "update", "receipt", "list_by_book"],
                 "book_scopes": ["book:other"]},
            ]
        }
        policy_path = run_dir / "fp-policy.json"
        policy_path.write_text(json.dumps(policy), encoding="utf-8")
        CRED = "c" * 64
        CRED_RO = "r" * 64
        CRED_OTHER = "o" * 64

        if not external:
            proc, log_f = spawn_service(data_dir, policy_path, legacy,
                                        run_dir / "service.log")
            if not wait_ready():
                print("FATAL: service not ready (see", run_dir / "service.log", ")")
                kill_tree(proc)
                return 2

        # ── F-01 旧库升级 ─────────────────────────────────────────
        rep = http("POST", "/api/v1/migrate")
        check(rep.get("migrated", 0) >= 3, "F-01a-legacy-migrated", rep)
        n0 = notes_count()
        check(n0 == 3, "F-01b-legacy-readable", f"count={n0}")
        legacy_note = http("GET", "/api/v1/notes")
        zh_ok = any("中文笔记" in (d.get("title") or "") for d in legacy_note) if isinstance(legacy_note, list) else False
        check(zh_ok, "F-01c-legacy-unicode-roundtrip")

        # ── F-02 capture 合法 + 来源往返 ──────────────────────────
        src = {"book_id": "book:abc123", "book_version": "v3", "author": "测试作者✅",
               "quote": "重复的原句：中文与 emoji 🎉", "chapter": 7,
               "locator": {"kind": "cfi", "v": 1, "value": "epubcfi(i/2!)"}}
        op1 = "0123456789abcdef0123456789abcdef"
        r1 = http("POST", "/api/fp/v1/capture",
                  {"cred": CRED, "interface_version": IF_V1, "attempt_id": "a-1",
                   "operation_id": op1, "source_json": json.dumps(src, ensure_ascii=False),
                   "text": "捕获正文第一版：中文正文 ✅\n第二行"})
        check(r1.get("ok") is True, "F-02a-capture-ok", r1)
        nid = (r1.get("note") or {}).get("note_id", "")
        check(bool(nid) and nid.startswith("n-"), "F-02b-note-id", r1)
        check((r1.get("note") or {}).get("revision") == 1, "F-02c-revision-1", r1)
        check((r1.get("receipt") or {}).get("status") == "committed", "F-02d-receipt", r1)
        g = http("POST", "/api/fp/v1/get", {"cred": CRED, "interface_version": IF_V1, "note_id": nid})
        gdoc = g.get("note") or {}
        check(g.get("ok") is True and gdoc.get("book_id") == "book:abc123", "F-02e-get-book", g)
        gsrc = gdoc.get("source") or {}
        check(gsrc == src, "F-02f-source-verbatim", (gsrc, src))
        check(gdoc.get("title") == src["quote"], "F-02g-title-is-quote", gdoc.get("title"))

        # ── F-03 capture 重放 ─────────────────────────────────────
        r2 = http("POST", "/api/fp/v1/capture",
                  {"cred": CRED, "interface_version": IF_V1, "attempt_id": "a-2",
                   "operation_id": op1, "source_json": json.dumps(src, ensure_ascii=False),
                   "text": "捕获正文第一版：中文正文 ✅\n第二行"})
        check(r2.get("ok") is True and r2.get("replayed") is True, "F-03a-replay-ok", r2)
        check((r2.get("note") or {}).get("note_id") == nid, "F-03b-same-note", r2)
        check(notes_count() == n0 + 1, "F-03c-no-dup-row")

        # ── F-04 capture 异载荷 ───────────────────────────────────
        r3 = http("POST", "/api/fp/v1/capture",
                  {"cred": CRED, "interface_version": IF_V1, "attempt_id": "a-3",
                   "operation_id": op1, "source_json": json.dumps(src, ensure_ascii=False),
                   "text": "不同的意图"})
        check(r3.get("ok") is False and r3.get("err_code") == "request_conflict",
              "F-04a-conflict", r3)
        check(notes_count() == n0 + 1, "F-04b-no-write")

        # ── F-05 fp update ────────────────────────────────────────
        opu = "11111111111111111111111111111111"
        u1 = http("POST", "/api/fp/v1/update",
                  {"cred": CRED, "interface_version": IF_V1, "attempt_id": "a-4",
                   "note_id": nid, "expected_revision": 1, "text": "更新后的正文 ✍️", "operation_id": opu})
        check(u1.get("ok") is True and (u1.get("note") or {}).get("revision") == 2,
              "F-05a-update-rev2", u1)
        check((u1.get("note") or {}).get("title") == src["quote"], "F-05b-title-immutable", u1)
        check((u1.get("note") or {}).get("body") == "更新后的正文 ✍️", "F-05c-body-updated", u1)

        # ── F-06 update 重放（跨重试幂等） ────────────────────────
        u2 = http("POST", "/api/fp/v1/update",
                  {"cred": CRED, "interface_version": IF_V1, "attempt_id": "a-5",
                   "note_id": nid, "expected_revision": 1, "text": "更新后的正文 ✍️", "operation_id": opu})
        check(u2.get("ok") is True and u2.get("replayed") is True, "F-06a-replay", u2)
        check((u2.get("note") or {}).get("revision") == 2, "F-06b-still-rev2", u2)

        # ── F-07 过期修订 ─────────────────────────────────────────
        u3 = http("POST", "/api/fp/v1/update",
                  {"cred": CRED, "interface_version": IF_V1, "attempt_id": "a-6",
                   "note_id": nid, "expected_revision": 1, "text": "过期意图", "operation_id": "2" * 32})
        check(u3.get("ok") is False and u3.get("err_code") == "revision_conflict",
              "F-07a-stale-rejected", u3)
        check(u3.get("current_revision") == 2, "F-07b-current-rev", u3)

        # ── F-08 并发更新（同 revision 恰一成功） ─────────────────
        results = []

        def worker(tag, text):
            rr = http("POST", "/api/fp/v1/update",
                      {"cred": CRED, "interface_version": IF_V1, "attempt_id": f"c-{tag}",
                       "note_id": nid, "expected_revision": 2, "text": text, "operation_id": tag * 32})
            results.append((tag, rr))

        t1 = threading.Thread(target=worker, args=("3", "并发 A"))
        t2 = threading.Thread(target=worker, args=("4", "并发 B"))
        t1.start(); t2.start(); t1.join(); t2.join()
        oks = [rr for _, rr in results if rr.get("ok") is True]
        check(len(oks) == 1, "F-08a-exactly-one-wins",
              [(t, rr.get("err_code")) for t, rr in results])
        losers = [rr for _, rr in results if rr.get("ok") is not True]
        check(all(rr.get("err_code") == "revision_conflict" for rr in losers),
              "F-08b-losers-conflict", losers)
        g2 = http("POST", "/api/fp/v1/get", {"cred": CRED, "interface_version": IF_V1, "note_id": nid})
        check((g2.get("note") or {}).get("revision") == 3, "F-08c-final-rev3", g2)

        # ── F-09 按书分页（先捕第二条保证翻页面） ─────────────────
        r4 = http("POST", "/api/fp/v1/capture",
                  {"cred": CRED, "interface_version": IF_V1, "attempt_id": "a-7",
                   "operation_id": "5" * 32,
                   "source_json": json.dumps({"book_id": "book:abc123", "quote": "第二条原句", "chapter": 9},
                                             ensure_ascii=False),
                   "text": "第二条正文"})
        check(r4.get("ok") is True, "F-09-pre-second-capture", r4)

        # ── F-09 按书分页 ─────────────────────────────────────────
        l1 = http("POST", "/api/fp/v1/list", {"cred": CRED, "interface_version": IF_V1, "book_id": "book:abc123", "cursor": 0, "limit": 1})
        items = l1.get("items") or []
        check(l1.get("ok") is True and len(items) == 1, "F-09a-page1", l1)
        check(isinstance(l1.get("next_cursor"), int), "F-09b-next-cursor", l1.get("next_cursor"))
        l2 = http("POST", "/api/fp/v1/list", {"cred": CRED, "interface_version": IF_V1, "book_id": "book:abc123", "cursor": l1.get("next_cursor") or 0, "limit": 10})
        check(len(l2.get("items") or []) >= 1, "F-09c-page2", l2)
        l3 = http("POST", "/api/fp/v1/list", {"cred": CRED_OTHER, "interface_version": IF_V1, "book_id": "book:other", "cursor": 0, "limit": 10})
        check(l3.get("ok") is True and len(l3.get("items") or []) == 0, "F-09d-other-book-empty", l3)

        # ── F-10 拒绝面（业务前、无写入） ─────────────────────────
        count_before = notes_count()
        d1 = http("POST", "/api/fp/v1/capture",
                  {"cred": "", "interface_version": IF_V1, "attempt_id": "d1",
                   "operation_id": "a" * 32, "source_json": json.dumps(src), "text": "x"})
        check(d1.get("err_code") == "permission_denied", "F-10a-no-cred", d1)
        d2 = http("POST", "/api/fp/v1/capture",
                  {"cred": CRED_OTHER, "interface_version": IF_V1, "attempt_id": "d2",
                   "operation_id": "b" * 32, "source_json": json.dumps(src), "text": "x"})
        check(d2.get("err_code") == "permission_denied", "F-10b-wrong-scope", d2)
        legacy_doc = (legacy_note or [{}])[0]
        d3 = http("POST", "/api/fp/v1/update",
                  {"cred": CRED_RO, "interface_version": IF_V1, "attempt_id": "d3",
                   "note_id": nid, "expected_revision": 3, "text": "越权", "operation_id": "c" * 32})
        check(d3.get("err_code") == "permission_denied", "F-10c-op-not-granted", d3)
        d4 = http("POST", "/api/fp/v1/get", {"cred": CRED, "interface_version": IF_V2, "note_id": nid})
        check(d4.get("err_code") == "unsupported_version", "F-10d-version-reject", d4)
        legacy_nid = legacy_doc.get("note_id", "")
        d5 = http("POST", "/api/fp/v1/get", {"cred": CRED, "interface_version": IF_V1, "note_id": legacy_nid})
        check(d5.get("err_code") == "permission_denied", "F-10e-plain-note-hidden", d5)
        check(notes_count() == count_before, "F-10f-no-write-on-rejects")
        h = http("GET", "/api/health")
        check(h.get("interface") == IF_V1 and h.get("status") == "ok", "F-10g-health", h)

        # ── F-11 回执查询 ─────────────────────────────────────────
        q1 = http("POST", "/api/fp/v1/receipt", {"cred": CRED, "interface_version": IF_V1, "operation_id": op1})
        check(q1.get("status") == "committed" and (q1.get("receipt") or {}).get("note_id") == nid,
              "F-11a-receipt-committed", q1)
        q2 = http("POST", "/api/fp/v1/receipt", {"cred": CRED, "interface_version": IF_V1, "operation_id": "f" * 32})
        check(q2.get("status") == "not_observed", "F-11b-not-observed", q2)

    finally:
        if not external:
            kill_tree(proc)
            if log_f:
                log_f.close()
        if not args.keep:
            shutil.rmtree(run_dir, ignore_errors=True)

    print(f"\nfeaturepack-service PASS={len(PASS)} FAIL={len(FAIL)}")
    for f in FAIL:
        print("  FAIL:", f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
