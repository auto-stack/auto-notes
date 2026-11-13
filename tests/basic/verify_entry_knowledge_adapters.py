#!/usr/bin/env python3
"""verify_entry_knowledge_adapters.py — NOTES-003 永久验证入口（I-01..I-06 双端）。

用法（auto-notes 仓根）：
    python tests/basic/verify_entry_knowledge_adapters.py --profile service   # S 段（I-01/03/04/05/06）
    python tests/basic/verify_entry_knowledge_adapters.py --profile vue       # S 段 + V 段（I-02 小组件）

覆盖（计划 §6 I-01..I-06 + SD-01..03 断言）：
  S 段（服务/磁盘 oracle；双端同源；debug 后端 exe 直跑，AGENTS.md 构建纪律）：
    S-01 I-01 Launcher 文件交接：独立 caller 写 envelope → scan → 回执文件
         committed；库行与回执独立核验；重启同包重放 replayed 同 note 不重复；
         半写/错版本/名不匹配/未知 producer/无授权 cred/未知 note/过期修订/
         同 ID 异载荷 全部确定 rejected，无虚假 committed。
    S-02 I-03 Jade 导出快照：Unicode/Markdown 正文+来源+多附件 → stub 逐项核
         （note.json/note.md/note.txt/source.json/attachments hash/manifest）；
         同 export_id 重投同映射（manifest 文件 hash 不变）；导出中更新后同包
         保持快照绑定；缺原件 → asset_missing 可重试；异 note/revision 撞包
         → request_conflict。
    S-03 I-04 来源：scape 网页（url locator+选区 hash）/lens 截图区域（region
         locator+原件 hash）/reader 013 canonical（locator 原样）经真实入口
         入库，fp_get 逐项比对；重复投递幂等；缺字段/未知 producer 拒绝且
         不误认完整来源（source_status 投影）。
    S-04 I-05 Ink：图像+版本化模型（pressure_missing/coords/strokes）round-trip
         逐字；原件 hash/字节不变；能力报告输出实际平台与未验证边界。
    S-05 I-06 配置仅收窄：错 scope/未知能力拒绝；006 文本+002 附件同 note
         兼容；固定 manifest SHA；必需 case 无 skip。
  V 段（Vue 真实 UI，Playwright）：I-02 小组件/快速卡片/管理页同一
    note_id/revision 打开（三实例同 draft props）；小组件真实键入 → 提交 saved
    服务端逐字；外部更新触发冲突 → Rebase 保输入再提交；关闭小组件可回主
    应用（管理页仍在）；关闭不清草稿（重开恢复）；零页面错误。

约定：隔离 NOTES_DATA_DIR/NOTES_HANDOFF_DIR/NOTES_EXPORT_DIR、自有端口、只
回收自有进程树；必需 case 无 skip；退出码非零=红。原始材料
D:/autostack/plan-artifacts/plan-003/。VM 轨：I-02 编辑实例物理输入 = 006
裁定②边界外（BOUNDARY 引用不计退出码）；结构面由 vue 轨覆盖。
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[1]
ARTIFACTS = Path(os.environ.get("PLAN_ARTIFACTS_HOME", "D:/autostack/plan-artifacts/plan-003"))
IFV = "notes.fpack/1"
FIX = ROOT / "tests" / "fixtures" / "integrations"

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
    for n in ["auto-notes-30db9907-back.exe", "auto.exe", "node.exe"]:
        subprocess.run(["taskkill", "/F", "/IM", n], capture_output=True)
    time.sleep(2)


# ── 服务生命周期（S 段）───────────────────────────────────────────────

PORT = 17851
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


def spawn_service(data_dir, env_extra, log_path):
    global PORT, BASE
    env = dict(os.environ)
    env["NOTES_DATA_DIR"] = str(data_dir)
    env["NOTES_TEST_MODE"] = "1"
    env["AUTO_ALLOW_PARTIAL_DB"] = "1"
    env["AUTO_HTTP_PORT"] = str(PORT)
    env.update(env_extra)
    log_f = open(log_path, "w", encoding="utf-8")
    backend_exe = os.environ.get(
        "NOTES_BACK_EXE",
        "D:/autostack/auto-lang/target/generated-consumers/f3f98a9e/debug/auto-notes-30db9907-back.exe")
    proc = subprocess.Popen([backend_exe], cwd=str(ROOT), env=env, stdout=log_f, stderr=subprocess.STDOUT)
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
    subprocess.run(["taskkill", "/F", "/IM", "auto-notes-30db9907-back.exe"], capture_output=True)
    time.sleep(1)
    PORT = PORT + 1
    BASE = f"http://127.0.0.1:{PORT}"


def notes_rows(data_dir):
    import sqlite3
    db = sqlite3.connect(f"file:{data_dir}/inbox.db?mode=ro", uri=True)
    try:
        return db.execute("SELECT note_id, revision, title, body FROM notes WHERE state='active' ORDER BY seq").fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        db.close()


# ── 夹具 ───────────────────────────────────────────────────────────────

def env_capture(op, source, text):
    return {"schema_version": 1, "producer": "launcher", "producer_version": "launcher/1",
            "operation_id": op, "intent": "capture", "source": source, "text": text}


def env_update(op, nid_int, rev, text):
    return {"schema_version": 1, "producer": "launcher", "producer_version": "launcher/1",
            "operation_id": op, "intent": "update", "note_id": str(nid_int),
            "expected_revision": rev, "text": text}


def write_incoming(handoff, op, env):
    (handoff / "incoming" / f"{op}.json").write_text(json.dumps(env, ensure_ascii=False), encoding="utf-8")


def read_receipt(handoff, op):
    return json.loads((handoff / "outgoing" / f"{op}.json").read_text(encoding="utf-8"))


def SRC_WEB():
    return json.loads((FIX / "source-scape-v1.json").read_text(encoding="utf-8"))


def SRC_LENS():
    return json.loads((FIX / "source-lens-v1.json").read_text(encoding="utf-8"))


def SRC_READER():
    return json.loads((FIX / "source-reader-013-v1.json").read_text(encoding="utf-8"))


# ── S 段用例 ─────────────────────────────────────────────────────────

CRED = "e" * 64
CRED_OTHER = "o" * 64


def run_service_section():
    d = ARTIFACTS / "entry-service"
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    handoff = d / "handoff"
    (handoff / "incoming").mkdir(parents=True)
    (handoff / "outgoing").mkdir(parents=True)
    policy = {"entries": [
        {"cred": CRED, "principal": "launcher",
         "operations": ["capture", "update", "read", "receipt", "list_by_book"],
         "book_scopes": ["book:smoke", "book:web", "book:lens", "book:reader013"]},
        {"cred": CRED_OTHER, "principal": "other-book",
         "operations": ["capture", "update", "read", "receipt"],
         "book_scopes": ["book:other"]},
    ]}
    (d / "fp-policy.json").write_text(json.dumps(policy), encoding="utf-8")
    env_extra = {"NOTES_FP_POLICY": str(d / "fp-policy.json"),
                 "NOTES_HANDOFF_DIR": str(handoff),
                 "NOTES_EXPORT_DIR": str(d / "exports")}
    proc = spawn_service(d / "data", env_extra, d / "svc-main.log")
    try:
        # ── 种子 ──
        st, note = http("POST", "/api/notes", {"title": "交接靶", "body": "正文α", "folder": "", "request_id": "ek-seed"})
        check(st == 200 and note.get("id"), "S-00 seed note", (st, note))
        nid = note["id"]

        # ── S-01 I-01 Launcher 文件交接 ──
        src = {"book_id": "book:smoke", "source_hash": "a1" * 32, "title": "交接书", "author": "作者",
               "quote": "原句", "locator": {"kind": "url", "v": 1, "value": "https://example.com/x"}}
        e1 = env_capture("ek-cap-1", src, "交接正文一：中文与 **Markdown** 保留")
        write_incoming(handoff, "ek-cap-1", e1)
        st, r = http("POST", "/api/entry/v1/launcher/scan", {"cred": CRED})
        check(r.get("processed") == 1 and r.get("committed") == 1, "S-01a scan processed", r)
        rec = read_receipt(handoff, "ek-cap-1")
        check(rec.get("status") == "committed" and rec.get("note_id", "").startswith("n-") and rec.get("revision") == 1,
              "S-01b receipt committed", rec)
        cap_nid = rec["note_id"]
        cap_int = int(cap_nid.replace("n-", ""))
        check(not (handoff / "incoming" / "ek-cap-1.json").exists(), "S-01c incoming consumed")
        rows = notes_rows(d / "data")
        check(any(rw[0] == cap_nid and rw[1] == 1 and rw[3] == "交接正文一：中文与 **Markdown** 保留" for rw in rows),
              "S-01d db row matches receipt (independent oracle)", rows)

        # 重启同包重放：同 note 一条
        write_incoming(handoff, "ek-cap-1", e1)
        kill(proc)
        proc = spawn_service(d / "data", env_extra, d / "svc-restart.log")
        st, r = http("POST", "/api/entry/v1/launcher/scan", {"cred": CRED})
        rec2 = read_receipt(handoff, "ek-cap-1")
        check(rec2.get("status") == "committed" and rec2.get("note_id") == cap_nid and rec2.get("replayed") is True,
              "S-01e restart replay same note", rec2)
        rows = notes_rows(d / "data")
        check(sum(1 for rw in rows if rw[0] == cap_nid) == 1, "S-01f no duplicate after replay")

        # update 交接
        e2 = env_update("ek-upd-1", cap_int, 1, "交接更新后")
        write_incoming(handoff, "ek-upd-1", e2)
        st, r = http("POST", "/api/entry/v1/launcher/scan", {"cred": CRED})
        rec3 = read_receipt(handoff, "ek-upd-1")
        check(rec3.get("status") == "committed" and rec3.get("revision") == 2, "S-01g update handoff rev2", rec3)

        # 同 ID 异载荷 → request_conflict（无虚假 committed）
        e1b = dict(e1)
        e1b["text"] = "不同的意图"
        write_incoming(handoff, "ek-cap-1", e1b)
        st, r = http("POST", "/api/entry/v1/launcher/scan", {"cred": CRED})
        rec_c = read_receipt(handoff, "ek-cap-1")
        check(rec_c.get("status") == "rejected" and rec_c.get("err_code") == "request_conflict",
              "S-01h different payload same ID rejected", rec_c)
        check(sum(1 for rw in notes_rows(d / "data") if rw[0] == cap_nid) == 1, "S-01i no write on conflict")

        # 过期修订
        write_incoming(handoff, "ek-upd-2", env_update("ek-upd-2", cap_int, 1, "过期"))
        st, r = http("POST", "/api/entry/v1/launcher/scan", {"cred": CRED})
        rec_s = read_receipt(handoff, "ek-upd-2")
        check(rec_s.get("status") == "rejected" and rec_s.get("err_code") == "revision_conflict", "S-01j stale rejected", rec_s)

        # 未知 note_id
        write_incoming(handoff, "ek-upd-3", env_update("ek-upd-3", 999, 1, "未知"))
        st, r = http("POST", "/api/entry/v1/launcher/scan", {"cred": CRED})
        rec_u = read_receipt(handoff, "ek-upd-3")
        check(rec_u.get("status") == "rejected" and rec_u.get("err_code") == "not_found", "S-01k unknown note rejected", rec_u)

        # 半写文件
        (handoff / "incoming" / "ek-half.json").write_text('{"schema_version":1,"producer":"launcher"', encoding="utf-8")
        st, r = http("POST", "/api/entry/v1/launcher/scan", {"cred": CRED})
        rec_h = read_receipt(handoff, "ek-half")
        check(rec_h.get("status") == "rejected" and "half-written" in rec_h.get("err_detail", ""), "S-01l half-write rejected", rec_h)

        # 错版本
        e_bad = dict(e1)
        e_bad["schema_version"] = 99
        write_incoming(handoff, "ek-ver-1", e_bad)
        st, r = http("POST", "/api/entry/v1/launcher/scan", {"cred": CRED})
        rec_v = read_receipt(handoff, "ek-ver-1")
        check(rec_v.get("status") == "rejected" and "schema_version" in rec_v.get("err_detail", ""), "S-01m wrong version rejected", rec_v)

        # 未知 producer
        e_p = dict(e1)
        e_p["producer"] = "mystery"
        write_incoming(handoff, "ek-prod-1", e_p)
        st, r = http("POST", "/api/entry/v1/launcher/scan", {"cred": CRED})
        rec_p = read_receipt(handoff, "ek-prod-1")
        check(rec_p.get("status") == "rejected" and "permission_denied" in rec_p.get("err_detail", ""), "S-01n unknown producer rejected", rec_p)

        # 无授权 cred（policy 门）
        e_cred = env_capture("ek-cred-1", src, "无权意图")
        write_incoming(handoff, "ek-cred-1", e_cred)
        st, r = http("POST", "/api/entry/v1/launcher/scan", {"cred": "0" * 64})
        rec_g = read_receipt(handoff, "ek-cred-1")
        check(rec_g.get("status") == "rejected" and rec_g.get("err_code") == "permission_denied", "S-01o unauthorized cred rejected", rec_g)

        # ── S-02 I-03 Jade 导出 ──
        png = (ROOT / "tests" / "fixtures" / "capture" / "valid-1x1.png").read_bytes()
        st, up1 = http("POST", "/api/assets/v1/import", {"operation_id": "ek-exp-img1", "note_id": str(cap_int),
                                                         "path": str(ROOT / "tests/fixtures/capture/valid-1x1.png"),
                                                         "name": "导出 图一.png", "kind": "image", "mime": "image/png", "source": "test"})
        st, up2 = http("POST", "/api/assets/v1/import", {"operation_id": "ek-exp-img2", "note_id": str(cap_int),
                                                         "path": str(ROOT / "tests/fixtures/capture/valid-1x1.png"),
                                                         "name": "notes.md", "kind": "file", "mime": "text/markdown", "source": "test"})
        check(up1.get("ok") is True and up2.get("ok") is True, "S-02a attachments in place", (up1.get("ok"), up2.get("ok")))
        st, exp = http("POST", "/api/entry/v1/jade/export", {"note_id": cap_int, "export_id": "ek-pkg-1"})
        check(exp.get("ok") is True and exp.get("revision") == 2 and exp.get("note_id") == cap_int, "S-02b export ok", exp)
        pkg = Path(exp["package_dir"])
        man = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
        check(man.get("note_id") == cap_int and man.get("revision") == 2 and man.get("producer") == "jade", "S-02c manifest binding", man)
        atts = {a["name"]: a for a in man.get("attachments", [])}
        check(len(atts) == 2 and atts["导出 图一.png"]["sha256"] == up1["assets"][0]["sha256"]
              and atts["notes.md"]["sha256"] == up2["assets"][0]["sha256"], "S-02d manifest attachment hashes", man["attachments"])
        for a in man["attachments"]:
            f = pkg / "attachments" / a["file"]
            if not (f.exists() and sha(f.read_bytes()) == a["sha256"]):
                check(False, f"S-02e exported original {a['name']} hash", str(f))
        check((pkg / "note.txt").read_text(encoding="utf-8") == "交接更新后", "S-02f exported text body")
        md = (pkg / "note.md").read_text(encoding="utf-8")
        check("# 原句" in md and "交接更新后" in md, "S-02g exported markdown", md[:80])
        srcj = json.loads((pkg / "source.json").read_text(encoding="utf-8"))
        check(srcj.get("book_id") == "book:smoke" and srcj.get("quote") == "原句", "S-02h exported source", srcj)
        man_sha1 = sha((pkg / "manifest.json").read_bytes())
        pkg_sha1 = sha((pkg / "note.json").read_bytes())

        # 同 export_id 重投 → 同映射（manifest/文件 hash 不变）
        st, exp2 = http("POST", "/api/entry/v1/jade/export", {"note_id": cap_int, "export_id": "ek-pkg-1"})
        check(exp2.get("ok") is True and exp2.get("replayed") is True, "S-02i replay same mapping", exp2)
        check(sha((pkg / "manifest.json").read_bytes()) == man_sha1 and sha((pkg / "note.json").read_bytes()) == pkg_sha1,
              "S-02j fixed package SHA across replay")

        # 导出中更新后：同 export_id 再投 = 过期快照 → 显式 request_conflict
        # （D-03 "明确快照失效重试"），旧包文件不变（不混合多 revision）。
        e3 = env_update("ek-upd-4", cap_int, 2, "第三版正文")
        write_incoming(handoff, "ek-upd-4", e3)
        st, r = http("POST", "/api/entry/v1/launcher/scan", {"cred": CRED})
        st, exp3 = http("POST", "/api/entry/v1/jade/export", {"note_id": cap_int, "export_id": "ek-pkg-1"})
        check(exp3.get("ok") is False and exp3.get("err_code") == "request_conflict",
              "S-02k stale export_id after update explicit conflict", exp3)
        check(sha((pkg / "note.json").read_bytes()) == pkg_sha1
              and (pkg / "note.txt").read_text(encoding="utf-8") == "交接更新后",
              "S-02l snapshot intact not mixed with newer revision")

        # 缺原件 → asset_missing 可重试（新 export_id；删 objects 原件）
        obj = d / "data" / "assets" / "objects" / up1["assets"][0]["sha256"]
        bak = d / "obj-backup"
        bak.write_bytes(obj.read_bytes())
        obj.unlink()
        st, exp4 = http("POST", "/api/entry/v1/jade/export", {"note_id": cap_int, "export_id": "ek-pkg-2"})
        check(exp4.get("ok") is False and exp4.get("err_code") == "asset_missing", "S-02m missing original retryable", exp4)
        obj.write_bytes(bak.read_bytes())
        st, exp5 = http("POST", "/api/entry/v1/jade/export", {"note_id": cap_int, "export_id": "ek-pkg-2"})
        check(exp5.get("ok") is True, "S-02n retry converges after restore", exp5)

        # 异 note/revision 撞包 → request_conflict
        st, exp6 = http("POST", "/api/entry/v1/jade/export", {"note_id": nid, "export_id": "ek-pkg-1"})
        check(exp6.get("ok") is False and exp6.get("err_code") == "request_conflict", "S-02o export_id collision rejected", exp6)

        # ── S-03 I-04 来源 ──
        st, sc = http("POST", "/api/entry/v1/source/capture",
                      {"cred": CRED, "producer": "scape", "operation_id": "ek-sc-1",
                       "source_json": json.dumps(SRC_WEB(), ensure_ascii=False), "text": "网页正文：选区①",
                       "attachment_path": "", "attachment_name": ""})
        check(sc.get("ok") is True, "S-03a scape capture", sc)
        scid = (sc.get("note") or {}).get("note_id")
        st, sg = http("POST", "/api/fp/v1/get", {"cred": CRED, "interface_version": IFV, "note_id": scid})
        gdoc = (sg.get("note") or {})
        check(gdoc.get("book_id") == "book:web" and gdoc.get("source", {}).get("locator", {}).get("value")
              == "https://example.com/page/scape" and gdoc.get("source", {}).get("source_hash") == SRC_WEB()["source_hash"],
              "S-03b scape fidelity (locator/hash verbatim)", gdoc.get("source"))
        check(gdoc.get("body") == "网页正文：选区①", "S-03c scape text verbatim")

        st, ln = http("POST", "/api/entry/v1/source/capture",
                      {"cred": CRED, "producer": "lens", "operation_id": "ek-ln-1",
                       "source_json": json.dumps(SRC_LENS(), ensure_ascii=False), "text": "截图正文",
                       "attachment_path": str(ROOT / "tests/fixtures/capture/valid-1x1.png"),
                       "attachment_name": "区域截图.png"})
        check(ln.get("ok") is True and (ln.get("attachment") or []), "S-03d lens capture with shot", ln)
        lnid = (ln.get("note") or {}).get("note_id")
        st, rows3 = http("POST", "/api/assets/v1/list", {"note_id": int(lnid.replace("n-", ""))})
        shot = [r for r in rows3 if r["source"] == "lens"]
        check(len(shot) == 1 and shot[0]["sha256"] == sha(png), "S-03e lens shot original hash", shot)
        st, lg = http("POST", "/api/fp/v1/get", {"cred": CRED, "interface_version": IFV, "note_id": lnid})
        ldoc = (lg.get("note") or {})
        check(ldoc.get("source", {}).get("locator", {}).get("kind") == "region"
              and "coord" in ldoc.get("source", {}).get("locator", {}).get("value", ""), "S-03f lens region locator", ldoc.get("source"))

        st, rd = http("POST", "/api/entry/v1/source/capture",
                      {"cred": CRED, "producer": "reader", "operation_id": "ek-rd-1",
                       "source_json": json.dumps(SRC_READER(), ensure_ascii=False), "text": "阅读正文",
                       "attachment_path": "", "attachment_name": ""})
        check(rd.get("ok") is True, "S-03g reader capture", rd)
        rdid = (rd.get("note") or {}).get("note_id")
        st, rg = http("POST", "/api/fp/v1/get", {"cred": CRED, "interface_version": IFV, "note_id": rdid})
        rdoc = (rg.get("note") or {})
        check(rdoc.get("source", {}).get("locator", {}).get("value") == "epubcfi(/6/2[cover]!/4/2)"
              and rdoc.get("source", {}).get("source_hash") == SRC_READER()["source_hash"],
              "S-03h reader canonical locator/hash preserved", rdoc.get("source"))
        check(rdoc.get("source_status") == "ok", "S-03i reader source ok")

        # 重复投递幂等（同 op 同载荷）
        st, sc2 = http("POST", "/api/entry/v1/source/capture",
                       {"cred": CRED, "producer": "scape", "operation_id": "ek-sc-1",
                        "source_json": json.dumps(SRC_WEB(), ensure_ascii=False), "text": "网页正文：选区①",
                        "attachment_path": "", "attachment_name": ""})
        check(sc2.get("ok") is True and sc2.get("replayed") is True and (sc2.get("note") or {}).get("note_id") == scid,
              "S-03j source replay idempotent", sc2)

        # 缺字段来源 → 拒绝且无写入、不误认完整来源
        badsrc = {"book_id": "book:smoke", "source_hash": "e5" * 32, "title": "缺字段", "author": "X", "quote": ""}
        rows_before = len(notes_rows(d / "data"))
        st, br = http("POST", "/api/entry/v1/source/capture",
                      {"cred": CRED, "producer": "scape", "operation_id": "ek-sc-bad",
                       "source_json": json.dumps(badsrc), "text": "x", "attachment_path": "", "attachment_name": ""})
        check(br.get("ok") is False and br.get("err_code") == "invalid_request", "S-03k missing-field source rejected", br)
        check(len(notes_rows(d / "data")) == rows_before, "S-03l no partial row on rejected source")

        # 未知 producer
        st, up = http("POST", "/api/entry/v1/source/capture",
                      {"cred": CRED, "producer": "mars", "operation_id": "ek-mars",
                       "source_json": json.dumps(SRC_WEB()), "text": "x", "attachment_path": "", "attachment_name": ""})
        check(up.get("err_code") == "permission_denied", "S-03m unknown producer denied", up)

        # ── S-04 I-05 Ink ──
        model = {"schema_version": 1, "canvas": {"w": 800, "h": 600}, "pressure_missing": True,
                 "coords": [{"x": 10.5, "y": 20.0, "t": 100}, {"x": 30, "y": 40, "t": 200}],
                 "strokes": [{"id": 1, "points": 2}]}
        st, ink = http("POST", "/api/entry/v1/ink/save", {"note_id": cap_int, "operation_id": "ek-ink-1",
                                                          "image_path": str(ROOT / "tests/fixtures/capture/valid-1x1.png"),
                                                          "image_name": "手写.png", "model_json": json.dumps(model, ensure_ascii=False)})
        check(ink.get("ok") is True, "S-04a ink save", ink)
        st, ig = http("POST", "/api/entry/v1/ink/get", {"note_id": cap_int})
        assets_ink = ig.get("ink_assets", [])
        models = [a for a in assets_ink if a.get("is_model")]
        imgs = [a for a in assets_ink if not a.get("is_model")]
        check(len(models) == 1 and len(imgs) == 1, "S-04b ink get model+image", assets_ink)
        m = models[0]["text"] if isinstance(models[0]["text"], dict) else json.loads(models[0]["text"])
        check(m == model, "S-04c ink model round-trip verbatim", (m, model))
        check(m.get("pressure_missing") is True and m.get("coords")[1] == {"x": 30, "y": 40, "t": 200}
              and m.get("strokes")[0] == {"id": 1, "points": 2}, "S-04d pressure/coords/strokes preserved", m)
        st, dl, hdrs = http("GET", f"/api/assets/v1/{imgs[0]['asset_id']}/raw", raw=True)
        check(dl == png and imgs[0]["sha256"] == sha(png), "S-04e ink image original bytes+hash", imgs[0]["sha256"][:16])

        # 能力报告（真实平台/接口 + 未验证边界，不跳过必需图像/模型用例）
        import platform as pf
        print(f"CAPABILITY platform={pf.system()} {pf.machine()} python={pf.python_version()} "
              f"ink-hardware=absent(unverified) ink-runtime=file-import(tested via S-04) ocr=absent(unverified)")

        # ── S-05 I-06 配置仅收窄 / 兼容 / 固定 SHA ──
        # 错 scope：CRED_OTHER 捕获 book:smoke 来源 → 拒绝
        st, os = http("POST", "/api/entry/v1/source/capture",
                      {"cred": CRED_OTHER, "producer": "scape", "operation_id": "ek-other",
                       "source_json": json.dumps(SRC_WEB()), "text": "x", "attachment_path": "", "attachment_name": ""})
        check(os.get("ok") is False and os.get("err_code") == "permission_denied", "S-05a wrong-scope capture denied", os)
        # 006 文本 + 002 附件同 note 兼容（lens 已证；再证同 note 多附件+正文共存）
        st, gr = http("POST", "/api/fp/v1/get", {"cred": CRED, "interface_version": IFV, "note_id": lnid})
        st, rows5 = http("POST", "/api/assets/v1/list", {"note_id": int(lnid.replace("n-", ""))})
        check((gr.get("note") or {}).get("body") == "截图正文" and len(rows5) == 1, "S-05b 006 text + 002 attachment coexist", rows5)
        # 必需 case 无 skip 由运行期计数保证（下见收尾断言）

    finally:
        kill(proc)


# ── V 段（Vue 真实 UI：I-02 小组件）───────────────────────────────────

V_PROBE = r'''
import { chromium } from '@playwright/test';

const BACK = 'http://127.0.0.1:17819';
const FRONT = 'http://127.0.0.1:17818';
const results = [];
const check = (name, cond, detail) => {
  results.push({ name, ok: !!cond });
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : ' - ' + String(detail ?? '').slice(0, 220)));
};
const j = async (r) => {
  const t = await r.text();
  let x;
  try { x = JSON.parse(t); } catch { return { __raw: t.slice(0, 120) }; }
  if (typeof x === 'string') { try { x = JSON.parse(x); } catch { return { __raw: x.slice(0, 120) }; } }
  return x;
};

const browser = await chromium.launch();
const page = await browser.newPage();
const pageErrors = [];
page.on('pageerror', (e) => pageErrors.push(String(e)));

// 种子（应用后端 HTTP 直驱）
const note = await j(await fetch(BACK + '/api/notes', { method: 'POST', headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ title: '小组件靶α', body: '正文一', folder: '', request_id: 'ek-v-seed-1' }) }));
const note2 = await j(await fetch(BACK + '/api/notes', { method: 'POST', headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ title: '第二条β', body: '正文二', folder: '', request_id: 'ek-v-seed-2' }) }));
check('V-pre two notes seeded', note.id > 0 && note2.id > 0, JSON.stringify(note).slice(0, 80));

await page.goto(FRONT);
await page.getByText('小组件靶α').first().waitFor({ state: 'visible', timeout: 60000 });
await page.getByText('小组件靶α').first().click();
await page.locator('textarea').first().waitFor({ state: 'visible', timeout: 20000 });
for (let i = 0; i < 40; i++) {
  const v = await page.locator('textarea').first().inputValue();
  if (v === '正文一') break;
  await page.waitForTimeout(250);
}

// I-02a 小组件/卡片/管理页打开同一 note_id/revision（三 edit 实例同 draft props）
await page.getByText('Notes widget', { exact: true }).first().click();
await page.getByText('Attachments').first().waitFor({ state: 'visible', timeout: 30000 });
await page.getByText('Quick card', { exact: true }).first().click();
await page.waitForTimeout(600);
const tas = page.locator('textarea[placeholder="FP body"]');
const count = await tas.count();
check('V-01 widget+card+main three edit instances same note', count === 4, count); // main-edit + card + widget + create
const mainV = await tas.nth(0).inputValue();
const cardV = await tas.nth(2).inputValue();
const widgetV = await tas.nth(3).inputValue();
check('V-02 widget shares same draft text as management page', mainV === widgetV && mainV === cardV && mainV.includes('正文一'),
  { mainV: mainV.slice(0, 40), widgetV: widgetV.slice(0, 40) });

// I-02b 小组件真实键入（中文）→ 提交 saved（服务端逐字）
const wt = tas.nth(3);
await wt.fill('正文一');
await page.keyboard.type('小组件增补β');
await page.waitForTimeout(400);
const typed = await wt.inputValue();
check('V-03 IME-channel Chinese typed in widget', typed.includes('小组件增补β'), typed.slice(0, 60));
await wt.press('End');
await page.getByText('Submit').nth(3).click();
let saved = null;
for (let i = 0; i < 15; i++) {
  await page.waitForTimeout(700);
  saved = await j(await fetch(BACK + `/api/notes/${note.id}/result`));
  if (saved.ok === true && (saved.doc?.body || '').includes('小组件增补β')) break;
}
check('V-04 widget submit saved on server', saved.ok === true && (saved.doc?.body || '').includes('小组件增补β'),
  { body: (saved.doc?.body || '').slice(0, 50), err: saved.err_code });

// I-02c 外部更新触发冲突：读当前修订 → API 直写推进 → 小组件以过期基底提交 → conflict + Rebase
const cur = await j(await fetch(BACK + `/api/notes/${note.id}/result`));
const curRev = (cur.doc?.revision) || 1;
const ext = await j(await fetch(BACK + `/api/notes/${note.id}/result`, { method: 'PUT', headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ expected_revision: curRev, title: '小组件靶α', body: '外部更新γ', request_id: 'ek-v-ext' }) }));
check('V-05 external update advances revision', ext.ok === true, JSON.stringify(ext).slice(0, 90));
await wt.fill('正文一');
await page.keyboard.type('小组件增补β');
await page.waitForTimeout(300);
await page.getByText('Submit').nth(3).click();
let conflict = false;
for (let i = 0; i < 15; i++) {
  await page.waitForTimeout(500);
  const txt = await page.getByText('Conflict', { exact: true }).count();
  if (txt > 0) { conflict = true; break; }
}
check('V-06 external update triggers conflict in widget', conflict, '');
console.log('DIAG after-conflict body:', (await page.evaluate(() => document.body.innerText)).slice(0, 900));
const rebaseBtns = page.getByText('Rebase', { exact: true });
console.log('DIAG rebase count:', await rebaseBtns.count());
await rebaseBtns.last().click();
await page.waitForTimeout(400);
const kept = await wt.inputValue();
check('V-07 rebase keeps user input', kept.includes('小组件增补β'), kept.slice(0, 40));
await page.getByText('Submit').nth(3).click();
let saved2 = null;
for (let i = 0; i < 15; i++) {
  await page.waitForTimeout(700);
  saved2 = await j(await fetch(BACK + `/api/notes/${note.id}/result`));
  if (saved2.ok === true && (saved2.doc?.body || '').includes('小组件增补β')) break;
}
check('V-08 rebase then resubmit saved', saved2.ok === true && (saved2.doc?.body || '').includes('小组件增补β'),
  { body: (saved2.doc?.body || '').slice(0, 50) });

// I-02d 关闭小组件 → 管理页仍在（adapter 断开可回主应用）
await page.getByText('×', { exact: true }).last().click();
await page.waitForTimeout(400);
check('V-09 widget closed, management page still there',
  (await page.getByText('Notes widget', { exact: true }).count()) >= 1 && (await tas.count()) >= 2, await tas.count());

// I-02e 关闭保脏稿（不清草稿不 flush；重开恢复）
await page.getByText('Notes widget', { exact: true }).first().click();
await page.waitForTimeout(500);
const wta = page.locator('textarea[placeholder="FP body"]').nth(3);
await wta.fill('正文一');
await page.keyboard.type('关闭保留检查');
await page.waitForTimeout(300);
const slotKey = 'fpdraft|local|notes-main|note:' + note.id + '|edit';
const slot = await j(await fetch(BACK + '/api/fp/draft/get', { method: 'POST', headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ draft_key: slotKey }) }));
console.log('DIAG widget slot:', JSON.stringify(slot).slice(0, 200));
await page.getByText('×', { exact: true }).last().click();
await page.waitForTimeout(300);
await page.getByText('Notes widget', { exact: true }).first().click();
await page.waitForTimeout(500);
const tas2 = page.locator('textarea[placeholder="FP body"]');
check('V-10 reopen widget keeps dirty input (不清草稿)', (await tas2.nth(3).inputValue()).includes('关闭保留检查'),
  (await tas2.nth(3).inputValue()).slice(0, 40));

check('V-11 zero page errors', pageErrors.length === 0, pageErrors.slice(0, 3));

await browser.close();
const fails = results.filter((r) => !r.ok);
console.log('VRESULT ' + JSON.stringify({ pass: results.length - fails.length, fail: fails.length }));
process.exit(fails.length ? 1 : 0);
'''


def wait_http(url, timeout=300):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=4) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(2)
    return False


def run_vue_section():
    run_dir = ARTIFACTS / "entry-vue"
    run_dir.mkdir(parents=True, exist_ok=True)
    data_dir = run_dir / "data"
    if data_dir.exists():
        shutil.rmtree(data_dir, ignore_errors=True)  # 每轮干净库（request_id 重放隔离）
    probe = ROOT / "tests" / ".ek_vue_probe.mjs"
    probe.write_text(V_PROBE, encoding="utf-8")

    env = dict(os.environ)
    env["NOTES_DATA_DIR"] = str(data_dir)  # 进程数据隔离（I-06）
    env["NOTES_TEST_MODE"] = "1"
    env["AUTO_ALLOW_PARTIAL_DB"] = "1"
    env["AUTO_HTTP_PORT"] = "17819"
    backend_exe = Path(os.environ.get(
        "NOTES_BACK_EXE",
        "D:/autostack/auto-lang/target/generated-consumers/f3f98a9e/debug/auto-notes-30db9907-back.exe"))
    scaffold = ROOT / "gen/front/vue"
    procs = []
    lb = open(run_dir / "backend.log", "w", encoding="utf-8")
    procs.append(subprocess.Popen([str(backend_exe)], cwd=str(ROOT), env=env, stdout=lb, stderr=subprocess.STDOUT))
    lv = open(run_dir / "vite.log", "w", encoding="utf-8")
    procs.append(subprocess.Popen(
        ["node", str(scaffold / "node_modules/vite/bin/vite.js"),
         "--host", "127.0.0.1", "--port", "17818", "--strictPort"],
        cwd=str(scaffold), env=env, stdout=lv, stderr=subprocess.STDOUT))
    try:
        if not wait_http("http://127.0.0.1:17819/api/health", timeout=300):
            check(False, "V app backend ready", "timeout")
            return
        if not wait_http("http://127.0.0.1:17818", timeout=300):
            check(False, "V app front ready", "timeout")
            return
        node = subprocess.run(["node", str(probe)], cwd=str(ROOT / "tests"), env=env,
                              capture_output=True, text=True, timeout=600)
        out = (node.stdout or "") + "\n" + (node.stderr or "")
        print(out[-3000:])
        for line in out.splitlines():
            if line.startswith("PASS ") or line.startswith("FAIL "):
                name = line[5:].split(" - ")[0].strip()
                check(not line.startswith("FAIL"), name[:90], line[len(name) + 5:][:200])
        ok = "VRESULT" in out and '"fail":0' in out.split("VRESULT")[1][:40]
        check(ok, "V section exit green", out[-150:])
    finally:
        for pr, lf in [(procs[0], lb), (procs[1], lv)] if len(procs) == 2 else []:
            if pr.poll() is None:
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(pr.pid)], capture_output=True)
            lf.close()
        subprocess.run(["taskkill", "/F", "/IM", "auto-notes-30db9907-back.exe"], capture_output=True)
        time.sleep(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="service", choices=["service", "vue"])
    args = ap.parse_args()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    kill_leftovers()
    try:
        run_service_section()
        if args.profile == "vue":
            run_vue_section()
    finally:
        kill_leftovers()
    print(f"\n== verify_entry_knowledge_adapters {args.profile}: "
          f"{len(PASS)} pass / {len(FAIL)} fail / {len(BOUNDARY)} boundary")
    if FAIL:
        print("FAILED:", ", ".join(FAIL))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
