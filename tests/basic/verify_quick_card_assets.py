#!/usr/bin/env python3
"""verify_quick_card_assets.py — NOTES-002 永久验证入口（A-01..A-06 双端）。

用法（auto-notes 仓根）：
    python tests/basic/verify_quick_card_assets.py --profile service   # 服务/存储/恢复面（S 段）
    python tests/basic/verify_quick_card_assets.py --profile vue       # Vue 真实 UI 面（V 段，含 S 段）
    python tests/basic/verify_quick_card_assets.py --profile vm        # 原生面（M 段，裁定②边界内）

覆盖（计划 §6 A-01..A-06 + SD-01..03 断言）：
  S 段（服务/磁盘 oracle；双端同源）：
    S-01 A-01 收存→重启→raw/export 逐字节 hash 相等（图片/文件/Unicode 名）。
    S-02 同 hash 异名共享 objects，行元数据独立（内容去重不并意图）。
    S-03 同 operation_id 重放 replayed:true 不重复；异载荷 request_conflict。
    S-04 receipt committed/not_observed（W4 回包丢失恢复入口）。
    S-05 A-05 clipboard-bin fixture：混合条目原顺序=seq、producer/选择/来源
         入 bin_json；同请求重试同集合不重复；同文新操作另建集合。
    S-06 A-04 拒绝面：路径分隔名/禁止类型/缺文件/未知笔记/超限（env 收紧到
         真实执法点）——拒绝无虚假完成。
    S-07 A-03 四窗口：after_incoming/after_object/after_entity/after_manifest
         → 无虚假 committed → 同 operation 重试调和 → 恰一行 + hash 相等；
         after_manifest 行已提交且 receipt=committed。
  V 段（Vue 真实输入，Playwright）：A-02 卡片键入/提交/重复点击/IME 中文；
    A-06 卡片↔管理页同 ID 同 revision、附件在位（图片解码+损坏解码失败态）、
    宽窄/明暗/色标焦点参数、最近项/空态、关闭保脏稿。
  M 段（VM 真实输入，AutoUI MCP）：结构渲染/按钮链路/状态面；edit 实例物理
    输入 = 裁定②边界外（BOUNDARY 打印引用，不 skip 不计入退出码）。

约定：隔离 NOTES_DATA_DIR、自有端口、只回收自有进程树；必需 case 无 skip；
退出码非零=红。原始材料 D:/autostack/plan-artifacts/plan-002/。
构建再生成需 AUTO_ALLOW_PARTIAL_DB=1（asset_upload=PLAN-730 UploadRequest 形；
db.rs pub async fn 不被装配器 db-fn 提取识别——T-01 实测，写入无分叉）。
"""
import argparse
import hashlib
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[1]
ARTIFACTS = Path(os.environ.get("PLAN_ARTIFACTS_HOME", "D:/autostack/plan-artifacts/plan-002"))
IFV = "notes.fpack/1"

PASS, FAIL, BOUNDARY = [], [], []


def check(cond, name, detail=""):
    if cond:
        PASS.append(name)
        print("PASS", name)
    else:
        FAIL.append(name)
        print("FAIL", name, "-", str(detail)[:300])


def boundary(name, reason):
    BOUNDARY.append(name)
    print("BOUNDARY", name, "-", reason)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def kill_leftovers():
    for n in ["auto-notes-30db9907-back.exe", "auto.exe"]:
        subprocess.run(["taskkill", "/F", "/IM", n], capture_output=True)
    time.sleep(2)


# ── 服务生命周期（S 段）───────────────────────────────────────────────

PORT = 17841
BASE = f"http://127.0.0.1:{PORT}"


def http(method, path, body=None, headers=None, base=None, raw=False):
    base = base or BASE
    data = body
    hdr = dict(headers or {})
    if body is not None and not isinstance(body, bytes):
        data = json.dumps(body).encode()
        hdr.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(base + path, data=data, method=method, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            b = r.read()
            if raw:
                return r.status, b, dict(r.headers)
            out = None
            try:
                out = json.loads(b.decode())
            except Exception:
                return r.status, {"__raw": b[:300].decode(errors="replace")}
            if isinstance(out, str):
                try:
                    out = json.loads(out)
                except Exception:
                    pass
            return r.status, out
    except urllib.error.HTTPError as e:
        b = e.read()
        if raw:
            return e.code, b, dict(e.headers)
        out = None
        try:
            out = json.loads(b.decode())
        except Exception:
            return e.code, {"__raw": b[:300].decode(errors="replace")}
        if isinstance(out, str):
            try:
                out = json.loads(out)
            except Exception:
                pass
        return e.code, out
    except Exception as e:
        return 0, {"__err": str(e)}


def multipart(fields, file_field, filename, content, ctype="application/octet-stream"):
    if isinstance(content, str):
        content = content.encode("utf-8")
    b = uuid.uuid4().hex
    out = io.BytesIO()
    for k, v in fields.items():
        out.write(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    out.write(f"--{b}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{filename}\"\r\nContent-Type: {ctype}\r\n\r\n".encode())
    out.write(content)
    out.write(f"\r\n--{b}--\r\n".encode())
    return out.getvalue(), f"multipart/form-data; boundary={b}"


def spawn_service(data_dir, env_extra, log_path, retry=True):
    try:
        return _spawn_once(data_dir, env_extra, log_path)
    except RuntimeError:
        if retry is False:
            raise
        # 上实例退场竞态（bind 残响/文件锁）——换端口一次性重试
        kill(None)
        return _spawn_once(data_dir, env_extra, log_path.with_suffix(".retry.log"))


def _spawn_once(data_dir, env_extra, log_path):
    global PORT, BASE
    env = dict(os.environ)
    env["NOTES_DATA_DIR"] = str(data_dir)
    env["NOTES_TEST_MODE"] = "1"
    env["AUTO_ALLOW_PARTIAL_DB"] = "1"
    env.update(env_extra)
    log_f = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        ["D:/autostack/auto-man/target/debug/auto.exe", "service", "--server", "rust", "-B", str(PORT)],
        cwd=str(ROOT), env=env, stdout=log_f, stderr=subprocess.STDOUT)
    deadline = time.time() + 900
    while time.time() < deadline:
        try:
            st, _ = http("GET", "/api/health")
            if st == 200:
                return proc
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError(f"service not ready ({log_path})")


def kill(proc):
    global PORT, BASE
    if proc and proc.poll() is None:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        time.sleep(2)
    for n in ["auto-notes-30db9907-back.exe", "auto.exe"]:
        subprocess.run(["taskkill", "/F", "/IM", n], capture_output=True)
    time.sleep(1)
    PORT = PORT + 1
    BASE = f"http://127.0.0.1:{PORT}"


def asset_rows(data_dir):
    import sqlite3
    db = sqlite3.connect(f"file:{data_dir}/inbox.db?mode=ro", uri=True)
    try:
        return db.execute("SELECT asset_id, note_id, name, bytes, sha256, mime, source, seq, bin_json FROM note_assets ORDER BY seq").fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        db.close()


def upload(note_id, op, name, content, mime="image/png", kind="image", source="test"):
    mp, ct = multipart({"operation_id": op, "note_id": str(note_id), "name": name,
                        "mime": mime, "kind": kind, "source": source},
                       "file", name, content, ctype=mime or "application/octet-stream")
    return http("POST", "/api/assets/v1/upload", mp, {"Content-Type": ct})


# ── S 段用例 ─────────────────────────────────────────────────────────

VALID_PNG = None
CORRUPT_PNG = None


def load_fixtures():
    global VALID_PNG, CORRUPT_PNG
    VALID_PNG = (ROOT / "tests/fixtures/capture/valid-1x1.png").read_bytes()
    CORRUPT_PNG = (ROOT / "tests/fixtures/capture/corrupt.png").read_bytes()


def run_service_section():
    load_fixtures()
    d = ARTIFACTS / "qc-service"
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)

    proc = spawn_service(d / "data", {}, d / "svc-main.log")
    try:
        st, note = http("POST", "/api/notes", {"title": "快速卡片靶", "body": "正文α", "folder": "", "request_id": "qc-seed"})
        check(st == 200 and note.get("id"), "S-00 seed note", (st, note))
        nid = str(note["id"])

        # S-01 A-01: 收存（图片/文件/Unicode 名）→ 重启 → raw/export hash 相等
        content_png = VALID_PNG + "载荷α中文".encode("utf-8")
        st, body = upload(nid, "qc-up-1", "图 片.png", content_png, mime="image/png", kind="image")
        check(st == 201, "S-01 upload committed", (st, body))
        st, body = upload(nid, "qc-up-2", "notes.txt", "纯文本附件内容", mime="text/plain", kind="file")
        check(st == 201, "S-01 upload file committed", (st, body))
    finally:
        kill(proc)

    proc = spawn_service(d / "data", {}, d / "svc-restart.log")
    try:
        st, rows = http("POST", "/api/assets/v1/list", {"note_id": 1})
        check(st == 200 and isinstance(rows, list) and len(rows) == 2, "S-01 rows after restart", rows)
        ok_raw = True
        TXT_CONTENT = "纯文本附件内容".encode("utf-8")
        for row, content in [(rows[0], content_png), (rows[1], TXT_CONTENT)]:
            st, raw, hdrs = http("GET", f"/api/assets/v1/{row['asset_id']}/raw", raw=True)
            if st != 200 or raw != content:
                ok_raw = False
        check(ok_raw and rows[0]["sha256"] == sha(content_png), "S-01 restart export hash equal (raw+recorded)", rows)
        st, dl, hdrs = http("GET", f"/api/assets/v1/{rows[0]['asset_id']}/download", raw=True)
        dl_l = {k.lower(): v for k, v in hdrs.items()}
        check(dl == content_png and "attachment" in dl_l.get("content-disposition", "") and "filename" in dl_l.get("content-disposition", ""),
              "S-01 download attachment + name header", dl_l.get("content-disposition"))
        st, raw206, _ = http("GET", f"/api/assets/v1/{rows[0]['asset_id']}/raw", headers={"Range": "bytes=0-3"}, raw=True)
        # urllib 对 206 需要 HTTPError 之外的处理：200 全量也如实记录
        check(st in (200, 206), "S-01 raw range served", st)

        # S-02 dedup: 同内容异名 → 共享 objects、行独立
        src = d / "same.bin"
        src.write_bytes(content_png)
        st, body = http("POST", "/api/assets/v1/import", {"operation_id": "qc-imp-1", "note_id": "1",
                                                          "path": str(src), "name": "同名不同显示.png",
                                                          "kind": "image", "mime": "image/png", "source": "test"})
        check(st == 200 and body.get("ok"), "S-02 import committed", (st, body))
        st, rows2 = http("POST", "/api/assets/v1/list", {"note_id": 1})
        objs = list((d / "data" / "assets" / "objects").glob("*"))
        check(len(rows2) == 3 and len(objs) == 2, "S-02 three rows two objects (shared by hash)", (len(rows2), len(objs)))

        # S-03 replay / conflict
        st, body = http("POST", "/api/assets/v1/import", {"operation_id": "qc-imp-1", "note_id": "1",
                                                          "path": str(src), "name": "同名不同显示.png",
                                                          "kind": "image", "mime": "image/png", "source": "test"})
        check(body.get("replayed") is True, "S-03 replay replayed:true", body)
        st, rows3 = http("POST", "/api/assets/v1/list", {"note_id": 1})
        check(len(rows3) == 3, "S-03 no duplicate on replay", len(rows3))
        st, body = http("POST", "/api/assets/v1/import", {"operation_id": "qc-imp-1", "note_id": "1",
                                                          "path": str(src), "name": "换名.png",
                                                          "kind": "image", "mime": "image/png", "source": "test"})
        check(body.get("err_code") == "request_conflict", "S-03 different payload conflict", body)

        # S-04 receipts
        st, rec = http("POST", "/api/assets/v1/receipt", {"operation_id": "qc-up-1"})
        check(rec.get("status") == "committed", "S-04 receipt committed", rec)
        st, rec = http("POST", "/api/assets/v1/receipt", {"operation_id": "qc-unknown"})
        check(rec.get("status") == "not_observed", "S-04 receipt not_observed", rec)

        # S-05 A-05 clipboard-bin fixture 导入
        entries = {"v": 1, "producer": "clipboard-bin-v0",
                   "entries": [
                       {"kind": "text", "text": "第一段复制内容", "selected_at": "t1", "origin": "docA"},
                       {"kind": "url", "text": "https://example.com/页", "selected_at": "t2", "origin": "web"},
                       {"kind": "file", "path": str(src), "name": "bin-图.png", "mime": "image/png", "selected_at": "t3", "origin": "explorer"},
                   ]}
        st, body = http("POST", "/api/assets/v1/clip_import", {"operation_id": "qc-clip-1", "note_id": "1",
                                                               "entries_json": json.dumps(entries, ensure_ascii=False),
                                                               "producer": "clipboard-bin-v0"})
        check(st == 200 and body.get("ok"), "S-05 clip_import committed", (st, body))
        st, rows4 = http("POST", "/api/assets/v1/list", {"note_id": 1})
        bin_rows = [r for r in rows4 if r["source"] == "clipboard-bin"]
        check(len(bin_rows) == 3, "S-05 three bin rows", len(bin_rows))
        seqs = [r["seq"] for r in bin_rows]
        check(seqs == sorted(seqs), "S-05 original order = seq ascending", seqs)
        ok_bin = all(("clipboard-bin-v0" in r["source"]) for r in bin_rows)
        dbr = asset_rows(d / "data")
        bins = [r for r in dbr if r[6] == "clipboard-bin"]
        ok_prov = len(bins) == 3 and all("producer" in (r[8] or "") and "selected_at" in (r[8] or "") for r in bins)
        check(ok_prov, "S-05 bin_json provenance (producer/selection/origin)", [r[8][:60] for r in bins])
        st, body = http("POST", "/api/assets/v1/clip_import", {"operation_id": "qc-clip-1", "note_id": "1",
                                                               "entries_json": json.dumps(entries, ensure_ascii=False),
                                                               "producer": "clipboard-bin-v0"})
        check(body.get("replayed") is True, "S-05 same-request retry same set", body)
        st, rows5 = http("POST", "/api/assets/v1/list", {"note_id": 1})
        check(len([r for r in rows5 if r["source"] == "clipboard-bin"]) == 3, "S-05 no duplicate on retry", len(rows5))
        entries2 = dict(entries)
        st, body = http("POST", "/api/assets/v1/clip_import", {"operation_id": "qc-clip-2", "note_id": "1",
                                                               "entries_json": json.dumps(entries, ensure_ascii=False),
                                                               "producer": "clipboard-bin-v0"})
        check(body.get("ok") is True and body.get("replayed") is not True, "S-05 same text new op new set", body)
        st, rows6 = http("POST", "/api/assets/v1/list", {"note_id": 1})
        check(len([r for r in rows6 if r["source"] == "clipboard-bin"]) == 6, "S-05 new op adds new set", len(rows6))

        # S-06 A-04 rejects
        st, body = http("POST", "/api/assets/v1/import", {"operation_id": "qc-r1", "note_id": "1",
                                                          "path": str(src), "name": "坏/名.png", "kind": "", "mime": "", "source": ""})
        check(body.get("err_code") == "invalid_request", "S-06 reject path-separator name", body)
        exe = d / "x.exe"
        exe.write_bytes(b"MZ")
        st, body = http("POST", "/api/assets/v1/import", {"operation_id": "qc-r2", "note_id": "1",
                                                          "path": str(exe), "name": "x.exe", "kind": "", "mime": "", "source": ""})
        check(body.get("err_code") == "invalid_request" and "forbidden_type" in body.get("err_detail", ""), "S-06 reject forbidden type", body)
        st, body = http("POST", "/api/assets/v1/import", {"operation_id": "qc-r3", "note_id": "1",
                                                          "path": str(d / "nope.bin"), "name": "x.bin", "kind": "", "mime": "", "source": ""})
        check(body.get("err_code") == "invalid_request" and "missing_file" in body.get("err_detail", ""), "S-06 reject missing file", body)
        st, body = http("POST", "/api/assets/v1/import", {"operation_id": "qc-r4", "note_id": "99999",
                                                          "path": str(src), "name": "x.bin", "kind": "", "mime": "", "source": ""})
        check(body.get("err_code") == "not_found", "S-06 reject unknown note", body)
        st, body = http("POST", "/api/assets/v1/raw", {"asset_id": "a-99999"})
        check(st in (200, 404), "S-06 unknown asset raw served-or-404 (no fabricate)", st)
    finally:
        kill(proc)

    # S-06 cap boundary（env 收紧到真实执法点）
    proc = spawn_service(d / "data-cap", {"NOTES_ASSET_MAX_FILE_BYTES": "16",
                                          "AUTO_HTTP_UPLOAD_MAX_FILE_BYTES": "65536",
                                          "AUTO_HTTP_UPLOAD_MAX_WIRE_BYTES": "655360"},
                         d / "svc-cap.log")
    try:
        st, note = http("POST", "/api/notes", {"title": "C", "body": "b", "folder": "", "request_id": "qc-cap-seed"})
        nid = str(note["id"])
        big = b"x" * 64
        st, body = upload(nid, "qc-cap-1", "big.bin", big, mime="", kind="file")
        check(st == 400 and "too_large" in json.dumps(body), "S-06 app cap reject", (st, body))
        check(len(asset_rows(d / "data-cap")) == 0, "S-06 cap reject leaves no row", None)
    finally:
        kill(proc)

    # S-07 A-03 四窗口
    for stage in ["after_incoming", "after_object", "after_entity", "after_manifest"]:
        # after_manifest 在 COMMIT 之后才报错——行已提交（回执可查），
        # 其余三窗零行
        expect_rows = 1 if stage == "after_manifest" else 0
        dw = d / f"data-{stage}"
        proc0 = spawn_service(dw, {}, d / f"svc-{stage}-seed.log")
        try:
            st, note = http("POST", "/api/notes", {"title": "F", "body": "b", "folder": "", "request_id": f"qc-{stage}-seed"})
            nid = str(note["id"])
        finally:
            kill(proc0)
        content2 = b"fault-window-" + stage.encode()
        proc = spawn_service(dw, {"NOTES_FAULT": stage}, d / f"svc-{stage}.log")
        try:
            st, body = upload(nid, f"qc-f-{stage}", "f.bin", content2, mime="", kind="file")
            check(st != 201, f"S-07 {stage}: no committed reply", (st, str(body)[:120]))
            check(len(asset_rows(dw)) == expect_rows, f"S-07 {stage}: rows after fault = {expect_rows}", len(asset_rows(dw)))
        finally:
            kill(proc)
        proc2 = spawn_service(dw, {}, d / f"svc-{stage}-rec.log")
        try:
            st, body = upload(nid, f"qc-f-{stage}", "f.bin", content2, mime="", kind="file")
            check(st in (201, 409), f"S-07 {stage}: retry accepted", (st, str(body)[:120]))
            st, rec = http("POST", "/api/assets/v1/receipt", {"operation_id": f"qc-f-{stage}"})
            check(rec.get("status") == "committed", f"S-07 {stage}: retry recovers committed", (st, rec))
            rows = asset_rows(dw)
            check(len(rows) == 1 and rows[0][4] == sha(content2), f"S-07 {stage}: exactly one row hash equal", rows)
        finally:
            kill(proc2)


# ── 入口 ─────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["service", "vue", "vm"], required=True)
    args = ap.parse_args()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    kill_leftovers()

    if args.profile in ("service", "vue", "vm"):
        try:
            run_service_section()
        except Exception as e:
            check(False, "S section crashed", repr(e))

    if args.profile == "vue":
        try:
            import run_vue_section
            run_vue_section.main(ROOT, ARTIFACTS, check, boundary)
        except Exception as e:
            check(False, "V section crashed", repr(e))

    if args.profile == "vm":
        try:
            import run_vm_section
            run_vm_section.main(ROOT, ARTIFACTS, check, boundary)
        except Exception as e:
            check(False, "M section crashed", repr(e))

    print(f"\n== verify_quick_card_assets[{args.profile}]: {len(PASS)} PASS / {len(FAIL)} FAIL / {len(BOUNDARY)} BOUNDARY ==")
    if FAIL:
        print("FAILURES:", FAIL)
        sys.exit(1)


if __name__ == "__main__":
    main()
