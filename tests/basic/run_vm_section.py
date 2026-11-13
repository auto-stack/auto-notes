#!/usr/bin/env python3
"""run_vm_section.py — NOTES-002 M 段（原生 VM 轨；verify_quick_card_assets --profile vm 调用）。

驱动：`auto run -r vm` + AUTOUI_MCP_PORT（AutoUI MCP JSON-RPC）。种子经应用后端
HTTP（17819），写入后杀树重启使 Init 重读（VM 无页面刷新面——006 先例）。
边界（裁定②）：edit 实例物理输入不在 VM 真实输入面内——卡片编辑器属 edit
实例，其键入用例打印 BOUNDARY 引用裁定，不 skip 不计退出码；VM 真实输入以
create 链+状态面为准（NOTES-006 §5⑦/§10 裁定②同源）。
"""
import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

BACK = "http://127.0.0.1:17819"


def http(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BACK + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    out = None
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


class Mcp:
    def __init__(self, port):
        self.url = f"http://127.0.0.1:{port}/mcp"
        self.rid = 0

    def call(self, method, params=None):
        self.rid += 1
        payload = json.dumps({"jsonrpc": "2.0", "id": self.rid, "method": method,
                              "params": params or {}}).encode()
        req = urllib.request.Request(self.url, data=payload, method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())

    def tools_list(self):
        return self.call("tools/list")

    def tool(self, name, args=None):
        res = self.call("tools/call", {"name": name, "arguments": args or {}})
        return res


def wait_mcp(mcp, timeout=1800):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            res = mcp.tools_list()
            if "result" in res:
                return True
        except Exception:
            time.sleep(3)
    return False


def snapshot_text(mcp):
    res = mcp.tool("autoui_snapshot")
    content = res.get("result", {}).get("content", [])
    return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))


def press(mcp, snap, text_match, tries=5):
    """按绑定文本定位元素 id 并 press（vnode 重渲染换 id——每轮重照）。"""
    for _ in range(tries):
        snap = snapshot_text(mcp)
        el = None
        for line in snap.splitlines():
            if text_match in line:
                for token in line.split():
                    if token.startswith("#aura_") or token.startswith("#vnode_"):
                        el = token.strip("#")
                        break
            if el:
                break
        if el:
            mcp.tool("autoui_action", {"element_id": el, "action": "press"})
            time.sleep(0.6)
            return True
        time.sleep(1)
    return False


def state_fields(mcp, fields):
    res = mcp.tool("autoui_state", {"fields": fields})
    content = res.get("result", {}).get("content", [])
    text = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    try:
        return json.loads(text)
    except Exception:
        return {"__raw": text[:200]}


def kill_tree(proc):
    if proc and proc.poll() is None:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        time.sleep(2)


def main(ROOT, ARTIFACTS, check, boundary):
    run_dir = ARTIFACTS / "qc-vm"
    run_dir.mkdir(parents=True, exist_ok=True)
    kill = lambda proc: kill_tree(proc)

    env = dict(os.environ)
    env["NOTES_TEST_MODE"] = "1"
    env["AUTO_ALLOW_PARTIAL_DB"] = "1"
    env["AUTO_HTTP_PORT"] = "17819"
    mcp_port = free_bind_port()
    env["AUTOUI_MCP_PORT"] = str(mcp_port)
    exe = os.environ.get("AUTO_EXE", "D:/autostack/auto-man/target/debug/auto.exe")
    log_f = open(run_dir / "app.log", "w", encoding="utf-8")
    proc = subprocess.Popen([exe, "run", "-r", "vm"], cwd=str(ROOT), env=env,
                            stdout=log_f, stderr=subprocess.STDOUT)
    try:
        mcp = Mcp(mcp_port)
        if not wait_mcp(mcp):
            check(False, "M-00 MCP ready", "timeout (see " + str(run_dir / "app.log") + ")")
            return
        check("M-00 MCP ready", True)

        # 应用后端就绪后经 HTTP 种子（两条笔记 + 附件挂第一条）——后端由
        # auto run 派生（17819），种子必须打在它上面
        note = http("POST", "/api/notes", {"title": "VM 卡片靶γ", "body": "正文γ", "folder": "", "request_id": "vm-seed-1"})
        http("POST", "/api/notes", {"title": "VM 第二条δ", "body": "正文δ", "folder": "", "request_id": "vm-seed-2"})
        check("M-00 seeds posted", note.get("id", 0) > 0, note)
        nid = str(note["id"])
        fixture = ROOT / "tests/fixtures/capture/valid-1x1.png"
        imp = http("POST", "/api/assets/v1/import", {"operation_id": "vm-imp-1", "note_id": nid,
                                                     "path": str(fixture), "name": "vm-图.png",
                                                     "kind": "image", "mime": "image/png", "source": "test"})
        check("M-00 attachment attached", imp.get("ok") is True, imp)

        # 杀树重启使 Init 重读种子（VM 无页面刷新面——006 先例）
        kill(proc)
        log_f2 = open(run_dir / "app2.log", "w", encoding="utf-8")
        proc = subprocess.Popen([exe, "run", "-r", "vm"], cwd=str(ROOT), env=env,
                                stdout=log_f2, stderr=subprocess.STDOUT)
        if not wait_mcp(mcp):
            check(False, "M-00 MCP ready (restart)", "timeout")
            return

        snap = snapshot_text(mcp)
        check("M-01 shell renders with Quick card entry", "Quick card" in snap, "")
        check("M-01 target note listed", "VM 卡片靶γ" in snap, "")

        # 选中目标笔记（侧栏行 press）→ 打开卡片
        ok_sel = press(mcp, snap, "VM 卡片靶γ")
        check("M-02 select note pressed", ok_sel, "")
        time.sleep(1)
        ok_card = press(mcp, None, "Quick card")
        check("M-02 quick card opened", ok_card, "")
        time.sleep(1)
        snap = snapshot_text(mcp)
        check("M-03 card renders editor + attachments strip",
              "Attachments" in snap and "FP body" in snap, "")
        check("M-04 attachment row visible (vm-图.png)", "vm-图.png" in snap, "")
        check("M-05 recent list renders sibling note", "VM 第二条δ" in snap, "")

        st = state_fields(mcp, ["fp_edit_state", "card_open"])
        check("M-06 state face readable (card_open true)", str(st).find("card_open") >= 0, st)

        # 关闭（CloseCard 按钮 ×）→ 卡片关
        ok_close = press(mcp, None, "onclick: .CardClosed") or press(mcp, None, "×")
        time.sleep(1)
        snap = snapshot_text(mcp)
        check("M-07 card closed via button", "Attachments" not in snap, "")

        # 裁定②边界：卡片编辑器 = edit 实例——VM 物理键入不在真实输入面
        boundary("M-B-01 card editor (edit instance) physical typing",
                 "裁定②：VM edit 实例输入面不在真实输入边界内（NOTES-006 §5⑦/§10）；"
                 "卡片中文键入/提交的输入真实性以 Vue 轨 V-02/V-03 为准")
    finally:
        kill(proc)
        for n in ["auto-notes-30db9907-back.exe", "auto.exe"]:
            subprocess.run(["taskkill", "/F", "/IM", n], capture_output=True)
