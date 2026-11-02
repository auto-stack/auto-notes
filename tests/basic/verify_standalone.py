#!/usr/bin/env python3
"""NOTES-004 独立运行门（T-01..T-04 落地）。

编排：有界正式准备（submodule pin → 引擎 dist → 前端依赖 → 生成+后端构建 →
隔离启动）+ N-01..05 用例 + 001 回归复用入口。任何阶段失败必须非零退出并
保留阶段日志；只回收本次 spawn 的进程树，不触碰共享 target 与他者实例。

用法（仓根）：
    python tests/basic/verify_standalone.py --profile vue --case n01
    python tests/basic/verify_standalone.py --profile vue --case suite   # Vue 全套 31 项
    python tests/basic/verify_standalone.py --profile vm  --case n01     # 原生门（G4 解除后）

原始日志：D:/autostack/plan-artifacts/plan-004/verify-standalone-<id>/（不入口）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = Path(os.environ.get("PLAN_ARTIFACTS_HOME", "D:/autostack/plan-artifacts/plan-004"))
BACKEND_EXE = Path(os.environ.get(
    "NOTES_BACK_EXE",
    "D:/autostack/auto-lang/target/generated-consumers/f3f98a9e/debug/auto-notes-30db9907-back.exe"))
AUTO_CLI = os.environ.get("AUTO_CLI", "D:/autostack/auto-man/target/debug/auto.exe")
ENGINE_PKG = ROOT / "vendor/auto-down/autodown/packages/engine"
ENGINE_WORKSPACE = ROOT / "vendor/auto-down/autodown"
VUE_SCAFFOLD = ROOT / "gen/front/vue"
VENDOR_PIN = "c39ac7f9dacdc769fc4a5ad3b98ec896240b28e8"

# 阶段预算（秒）——决策稿 §5；失败即中止并保留日志。
BUDGETS = {"engine_install": 600, "engine_build": 600, "scaffold_install": 600,
           "gen_build": 900, "backend_build": 1200, "ready": 150, "suite": 900}


def log(msg: str) -> None:
    print(msg, flush=True)


def run(cmd: list[str], cwd: Path, budget_key: str, log_file: Path, env_extra: dict | None = None) -> int:
    """有界执行：超预算 kill 自己的子进程并返回 124；输出进日志文件。"""
    env = dict(os.environ, PYTHONUTF8="1", TAURI_ENV="1")
    if env_extra:
        env.update(env_extra)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "wb") as out:
        # 注意：auto CLI 工具链（tool host/pnpm/cargo 子进程）在 CREATE_NO_WINDOW
        # 下会静默失败（T-01 实证：同命令带旗标 exit 1、不带 exit 0）——这里只用
        # 进程组隔离，不隐藏窗口。
        p = subprocess.Popen(cmd, cwd=str(cwd), env=env, stdout=out, stderr=subprocess.STDOUT,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        deadline = time.time() + BUDGETS[budget_key]
        while p.poll() is None:
            if time.time() > deadline:
                p.kill()
                p.wait(timeout=10)
                log(f"  TIMEOUT {budget_key} after {BUDGETS[budget_key]}s: {' '.join(map(str, cmd))}")
                return 124
            time.sleep(1)
        return p.returncode


def fail(run_id: str, stage: str, detail: str) -> int:
    log(f"FAIL [{run_id}] {stage}: {detail}")
    return 1


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- 准备阶段

def prep(run_id: str, run_dir: Path, record: dict) -> int:
    """正式准备：每个阶段有就绪判定/预算/非零失败。幂等可重入（共享机器缓存
    允许温加速；运行自有状态（数据目录/端口）永远新建，见决策稿 §2/§5）。"""
    stages = record.setdefault("prep", {})
    # S1 submodule pin：无漂移（+/-/U 前缀即漂移）
    r = subprocess.run(["git", "submodule", "status", "vendor/auto-down"], cwd=ROOT,
                       capture_output=True, text=True, timeout=30)
    line = r.stdout.strip()
    stages["submodule_pin"] = {"output": line, "exit": r.returncode}
    if r.returncode != 0 or not line:
        return fail(run_id, "prep/submodule", f"vendor pin 漂移或缺失: {line!r}")
    if line[0] in "+-U":
        return fail(run_id, "prep/submodule", f"vendor pin 漂移: {line}")
    if not line.split()[0].startswith(VENDOR_PIN[:7]):
        return fail(run_id, "prep/submodule", f"pin {line} != {VENDOR_PIN[:7]}")
    log("  S1 submodule pin ok")

    # S2 引擎 workspace install（node_modules 缺失时；pnpm 温缓存快）
    if not (ENGINE_WORKSPACE / "node_modules").is_dir():
        rc = run(["pnpm", "install"], ENGINE_WORKSPACE, "engine_install",
                 run_dir / "prep-engine-install.log")
        if rc != 0:
            return fail(run_id, "prep/engine_install", f"pnpm install exit {rc}")
    stages["engine_install"] = "ok" if (ENGINE_WORKSPACE / "node_modules").is_dir() else "missing"
    log("  S2 engine workspace install ok")

    # S3 引擎 dist（存在且含 index.js 即认为可用；缺失则构建并核对 dist-stamp）
    dist_ok = (ENGINE_PKG / "dist/index.js").is_file() and (ENGINE_PKG / "dist/style.css").is_file()
    if not dist_ok:
        rc = run(["npm", "run", "build"], ENGINE_PKG, "engine_build",
                 run_dir / "prep-engine-build.log")
        if rc != 0:
            return fail(run_id, "prep/engine_build", f"engine build exit {rc}")
        dist_ok = (ENGINE_PKG / "dist/index.js").is_file()
    if not dist_ok:
        return fail(run_id, "prep/engine_build", "engine dist 仍缺失")
    stamp = ""
    stamp_file = ENGINE_PKG / "dist/dist-stamp.txt"
    if stamp_file.is_file():
        stamp = stamp_file.read_text(encoding="utf8", errors="replace").strip()[:80]
    stages["engine_build"] = {"dist": True, "stamp": stamp}
    record["engine_dist_stamp"] = stamp
    log("  S3 engine dist ok")

    # S4 前端 scaffold 依赖（package.json 已由工具生成；node_modules 缺失时安装）
    if not (VUE_SCAFFOLD / "node_modules").is_dir():
        rc = run(["pnpm", "install", "--no-frozen-lockfile"], VUE_SCAFFOLD, "scaffold_install",
                 run_dir / "prep-scaffold-install.log")
        if rc != 0:
            return fail(run_id, "prep/scaffold_install", f"pnpm install exit {rc}")
    if not (VUE_SCAFFOLD / "node_modules/vite/bin/vite.js").is_file():
        return fail(run_id, "prep/scaffold_install", "vite 仍缺失")
    stages["scaffold_install"] = "ok"
    log("  S4 scaffold deps ok")

    # S5 生成 + 后端构建：生成链（auto build -r vue）保证生成物与当前源一致；
    # 工具宿主在高并发构建机器上有间歇性静默失败（决策稿 G4 同源），故有界重试；
    # 后端 exe 缺失时 cargo build。exe 身份（sha256）入记录。
    rc = 1
    for attempt in range(1, 4):
        rc = run([AUTO_CLI, "build", "-r", "vue"], ROOT, "gen_build",
                 run_dir / f"prep-gen-build-{attempt}.log")
        if rc == 0:
            break
        log(f"  S5 gen build attempt {attempt} exit {rc} — retrying (transient tool-host/contention)")
        time.sleep(10)
    if rc != 0:
        return fail(run_id, "prep/gen_build", f"auto build -r vue exit {rc} after 3 attempts")
    stages["gen_build"] = "ok"
    if not BACKEND_EXE.is_file():
        ws = ROOT / "rust-workspace"
        crate = BACKEND_EXE.name.replace(".exe", "")
        rc = run(["cargo", "build", "-p", crate], ws, "backend_build",
                 run_dir / "prep-cargo-build.log")
        if rc != 0:
            return fail(run_id, "prep/backend_build", f"cargo build exit {rc}")
    if not BACKEND_EXE.is_file():
        return fail(run_id, "prep/backend_build", f"exe 缺失 {BACKEND_EXE}")
    record["backend_exe_sha256"] = sha256(BACKEND_EXE)
    stages["backend_build"] = "ok"
    ver = subprocess.run([AUTO_CLI, "--version"], capture_output=True, text=True, timeout=30)
    record["cli_version"] = (ver.stdout or ver.stderr).strip().splitlines()[-1]
    log(f"  S5 gen+backend ok (exe {record['backend_exe_sha256'][:16]})")
    return 0


# ---------------------------------------------------------------- 隔离启动

class Live:
    """本次拥有的隔离实例：自有端口/数据目录/进程树；close 只回收自己。"""

    def __init__(self, run_dir: Path, data_dir: Path, test_mode: str = "1", seed: str = "1"):
        self.back, self.front = free_port(), free_port()
        self.data = data_dir
        self.env = dict(os.environ,
                        NOTES_DATA_DIR=str(data_dir), NOTES_SEED=seed, NOTES_TEST_MODE=test_mode,
                        AUTO_HTTP_PORT=str(self.back), AUTO_FRONT_PORT=str(self.front),
                        NOTES_URL=f"http://127.0.0.1:{self.front}",
                        TAURI_ENV="1", PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        for k in ("NOTES_FAULT", "NOTES_FORCE_LOCK", "NOTES_LEGACY_FILE", "AUTO_HTTP_PROXY",
                  "AUTO_REUSE_BACKEND"):
            self.env.pop(k, None)
        self.procs: list[subprocess.Popen] = []
        self.logs: list = []
        self.run_dir = run_dir

    def start(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        lb = open(self.run_dir / "backend.log", "wb"); self.logs.append(lb)
        self.procs.append(subprocess.Popen([str(BACKEND_EXE)], cwd=str(ROOT), env=self.env,
                                           stdout=lb, stderr=lb,
                                           creationflags=subprocess.CREATE_NO_WINDOW))
        lv = open(self.run_dir / "vite.log", "wb"); self.logs.append(lv)
        self.procs.append(subprocess.Popen(
            ["node", str(VUE_SCAFFOLD / "node_modules/vite/bin/vite.js"),
             "--host", "127.0.0.1", "--port", str(self.front), "--strictPort"],
            cwd=str(VUE_SCAFFOLD), env=self.env, stdout=lv, stderr=lv,
            creationflags=subprocess.CREATE_NO_WINDOW))

    def wait_ready(self, timeout: float = BUDGETS["ready"]) -> tuple[bool, str]:
        t0 = time.time()
        while time.time() - t0 < timeout:
            back_up = front_up = False
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{self.back}/api/v1/status", timeout=1).close()
                back_up = True
            except Exception:
                pass
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{self.front}", timeout=1).close()
                front_up = True
            except Exception:
                pass
            if back_up and front_up:
                return True, f"ready in {round(time.time() - t0, 1)}s"
            for p in self.procs:
                if p.poll() is not None:
                    return False, f"process exited early code={p.returncode}"
            time.sleep(0.5)
        return False, "readiness timeout"

    def close(self) -> None:
        for p in reversed(self.procs):
            if p.poll() is None:
                p.kill()
            try:
                p.wait(timeout=5)
            except Exception:
                pass
        for f in self.logs:
            try:
                f.close()
            except Exception:
                pass


# ---------------------------------------------------------------- 用例

def case_n01_vue(run_id: str, run_dir: Path, record: dict) -> int:
    """N-01 Vue：空缓存正式首启 + 失败控制（坏 exe 路径 / 端口占用），不触碰旁观实例。"""
    # (a) 空缓存首启：全新数据目录 + 自有端口
    data = run_dir / "data-n01"
    live = Live(run_dir, data)
    try:
        live.start()
        ok, why = live.wait_ready()
        record["n01_cold_launch"] = {"ready": ok, "why": why, "data": str(data)}
        if not ok:
            return fail(run_id, "n01/cold", why)
        with urllib.request.urlopen(f"http://127.0.0.1:{live.back}/api/v1/status", timeout=3) as r:
            status = json.loads(r.read().decode("utf-8", "replace"))
        if isinstance(status, str):  # 端点返回 JSON 字符串字面量（内嵌 JSON）
            status = json.loads(status)
        if not status.get("loaded"):
            return fail(run_id, "n01/cold", f"status 未载入: {status}")
        got = str(status.get("data_dir", "")).replace("\\", "/").rstrip("/").lower()
        want = str(data).replace("\\", "/").rstrip("/").lower()
        if got != want:
            return fail(run_id, "n01/cold", f"data_dir 隔离不符: got {got} want {want}")
        record["n01_status"] = status
        log(f"  N-01(a) cold launch ok, seeded={status.get('seeded', '')}, db 落位隔离目录")
    finally:
        live.close()

    # (b) 坏 exe 路径 → 非零、命名失败（替换 BACKEND_EXE 后走同一启动链）
    global BACKEND_EXE
    real_exe = BACKEND_EXE
    live = None
    try:
        BACKEND_EXE = Path("D:/autostack/plan-artifacts/plan-004/not-exist/auto-notes-back.exe")
        live = Live(run_dir, run_dir / "data-badexe")
        try:
            live.start()
            ok, why = live.wait_ready(timeout=20)
            record["n01_bad_tool"] = {"ready": ok, "why": why}
            if ok:
                return fail(run_id, "n01/bad_tool", "坏 exe 竟然就绪——门未检测到失败")
            why_str = why
        except FileNotFoundError as e:
            # Windows 在 spawn 即抛文件不存在——这正是要求命名的失败
            why_str = f"spawn failed as expected: {e}"
            record["n01_bad_tool"] = {"ready": False, "why": why_str}
        log(f"  N-01(b) bad tool detected nonzero: {why_str}")
    finally:
        BACKEND_EXE = real_exe
        if live is not None:
            live.close()

    # (c) 端口占用：占口后启动应失败；旁观 socket 全程不被杀
    blocker = socket.socket()
    blocker.bind(("127.0.0.1", 0))
    blocker_port = blocker.getsockname()[1]
    blocker.listen(1)
    try:
        live = Live(run_dir, run_dir / "data-occupied")
        live.env["AUTO_HTTP_PORT"] = str(blocker_port)  # 强制与占口冲突
        live.start()
        ok, why = live.wait_ready(timeout=30)
        record["n01_port_occupied"] = {"ready": ok, "why": why}
        if ok:
            return fail(run_id, "n01/port", "端口被占却就绪——隔离失败")
        log(f"  N-01(c) occupied port detected nonzero: {why}")
    finally:
        try:
            live.close()
        except Exception:
            pass
        blocker.close()  # 旁观 socket 由本用例自己关闭；进程树清理从未触碰它
    record["n01_verdict"] = "PASS"
    log("  N-01(vue) PASS")
    return 0


def case_suite_vue(run_id: str, run_dir: Path, record: dict) -> int:
    """Vue 全套 31 项（smoke + negatives-r4/r5/r8/r9 + accent-dark）。"""
    data = run_dir / "data-suite"
    live = Live(run_dir, data)
    try:
        live.start()
        ok, why = live.wait_ready()
        if not ok:
            return fail(run_id, "suite/ready", why)
        with open(run_dir / "playwright.log", "wb") as out:
            r = subprocess.run(
                ["node", str(ROOT / "tests/node_modules/@playwright/test/cli.js"), "test",
                 "--reporter=list"],
                cwd=str(ROOT / "tests"), env=live.env, stdout=out, stderr=subprocess.STDOUT,
                timeout=BUDGETS["suite"])
        record["suite_exit"] = r.returncode
        tail = (run_dir / "playwright.log").read_text(encoding="utf8", errors="replace")[-500:]
        log(tail)
        if r.returncode != 0:
            return fail(run_id, "suite", f"playwright exit {r.returncode}")
        record["suite_verdict"] = "PASS"
        log("  suite(vue) PASS")
        return 0
    finally:
        live.close()


def _run_spec(run_dir: Path, live: Live, spec: str, env_extra: dict, timeout: float) -> int:
    env = dict(live.env)
    env.update(env_extra)
    with open(run_dir / f"spec-{spec}-{env_extra.get('STAGE', 'x')}.log", "wb") as out:
        r = subprocess.run(
            ["node", str(ROOT / "tests/node_modules/@playwright/test/cli.js"), "test", spec,
             "--reporter=list"],
            cwd=str(ROOT / "tests"), env=env, stdout=out, stderr=subprocess.STDOUT, timeout=timeout)
    return r.returncode


def _sqlite_note(db: Path, title: str) -> dict | None:
    """只读查询 inbox.db 的 notes 行（UI/API 之外的磁盘 oracle）。"""
    import sqlite3
    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    try:
        row = con.execute(
            "SELECT note_id, title, body, revision FROM notes WHERE title = ?", (title,)
        ).fetchone()
        return {"note_id": row[0], "title": row[1], "body": row[2], "revision": row[3]} if row else None
    finally:
        con.close()


def case_n04_vue(run_id: str, run_dir: Path, record: dict) -> int:
    """N-04 Vue：确认落库 → 强杀后端 → 同数据目录重启 → 正文保真 + 下一次保存推进 revision。
    Windows 的进程终止即硬杀（无优雅控制台关闭通道）——本用例验证的是更强的不变量：
    已确认内容跨硬杀存活 + 重启后下一次真实编辑成功；优雅窗口关闭语义属原生 profile。"""
    title = f"N04-恢复探针-{run_id}"
    data = run_dir / "data-n04"
    live = Live(run_dir, data)
    try:
        live.start()
        ok, why = live.wait_ready()
        if not ok:
            return fail(run_id, "n04/ready", why)

        # 阶段1：before（新建+中文/引号/换行正文+保存）
        if _run_spec(run_dir, live, "standalone-recovery.spec.ts",
                     {"STAGE": "before", "N04_TITLE": title}, 180) != 0:
            return fail(run_id, "n04/before", "before spec 失败（见 spec 日志）")
        note = _sqlite_note(data / "inbox.db", title)
        if not note or note["body"] == "" or note["revision"] < 1:
            return fail(run_id, "n04/before", f"SQLite 落库不符: {note}")
        rev_before = note["revision"]
        record["n04_before"] = {**note, "body_len": len(note["body"])}
        log(f"  N-04 before ok: rev={rev_before} body={len(note['body'])}B（SQLite 磁盘核实）")

        # 阶段2：强杀后端（taskkill /F 进程树），确认死亡
        backend = live.procs[0]
        subprocess.run(["taskkill", "/PID", str(backend.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        backend.wait(timeout=10)
        log("  N-04 backend force-killed")

        # 阶段3：同数据目录重启后端
        lb = open(run_dir / "backend-restart.log", "wb"); live.logs.append(lb)
        live.procs[0] = subprocess.Popen([str(BACKEND_EXE)], cwd=str(ROOT), env=live.env,
                                         stdout=lb, stderr=lb,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
        t0 = time.time()
        while time.time() - t0 < 60:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{live.back}/api/v1/status", timeout=1).close()
                break
            except Exception:
                time.sleep(0.5)
        else:
            return fail(run_id, "n04/restart", "后端重启未就绪")
        log("  N-04 backend restarted on same data dir")

        # 阶段4：after（UI 重开 → 保真 → 下一次保存）
        if _run_spec(run_dir, live, "standalone-recovery.spec.ts",
                     {"STAGE": "after", "N04_TITLE": title, "N04_REV_BEFORE": str(rev_before)},
                     240) != 0:
            return fail(run_id, "n04/after", "after spec 失败（见 spec 日志）")
        note2 = _sqlite_note(data / "inbox.db", title)
        if not note2 or note2["revision"] <= rev_before:
            return fail(run_id, "n04/after", f"revision 未推进: {note2}")
        record["n04_after"] = {**note2, "body_len": len(note2["body"]), "rev_before": rev_before}
        record["n04_verdict"] = "PASS"
        log(f"  N-04(vue) PASS: rev {rev_before} → {note2['revision']}，硬杀重启后下一次真实编辑成功")
        return 0
    finally:
        live.close()


def case_backend_gates(run_dir: Path, record: dict, live_env_base: tuple[int, Path]) -> int:
    """battery S0–S22 + scratch 52：直启 TEST_MODE 后端（无种子），Git bash 跑电池。
    （battery 经 bash+curl+python，MSYS 环境变量/换行纪律见决策稿 §5/G4 附录）"""
    back_port, data = live_env_base
    import shutil as _sh
    _sh.rmtree(ROOT / ".auto/t004-battery", ignore_errors=True)
    env = dict(os.environ, NOTES_DATA_DIR=str(data), NOTES_TEST_MODE="1",
               AUTO_HTTP_PORT=str(back_port), PYTHONUTF8="1", NOTES_BACK_EXE=str(BACKEND_EXE))
    for k in ("NOTES_SEED", "NOTES_FAULT", "NOTES_FORCE_LOCK", "NOTES_LEGACY_FILE"):
        env.pop(k, None)
    log_f = open(run_dir / "backend-gates.log", "wb")
    p = subprocess.Popen([str(BACKEND_EXE)], cwd=str(ROOT), env=env, stdout=log_f, stderr=log_f,
                         creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{back_port}/api/v1/status", timeout=1).close()
                break
            except Exception:
                time.sleep(0.5)
        else:
            return fail("gates", "battery", "后端未就绪")
        base = f"http://127.0.0.1:{back_port}"
        # WSL bash 会丢弃 Windows env（T-03 实证）——必须用 Git bash 跑电池
        bash = "C:/Program Files/Git/bin/bash.exe"
        r1 = subprocess.run([bash, "tests/probe/run_v1_battery.sh", ".auto/t004-battery"],
                            cwd=str(ROOT), env=dict(env, BASE=base),
                            capture_output=True, text=True, timeout=BUDGETS["suite"])
        summ = ROOT / ".auto/t004-battery/summary.txt"
        record["battery_exit"] = r1.returncode
        if r1.returncode != 0:
            return fail("gates", "battery", (summ.read_text(encoding='utf8', errors='replace')[-300:]
                                             if summ.is_file() else "无 summary"))
        r2 = subprocess.run(["python", "tests/probe/evidence/r5-work/verify_backend_scratch.py"],
                            cwd=str(ROOT), env=env, capture_output=True, text=True,
                            timeout=BUDGETS["suite"])
        record["scratch_exit"] = r2.returncode
        if r2.returncode != 0:
            return fail("gates", "scratch", (r2.stdout or "")[-300:])
        record["backend_gates"] = "PASS (battery S0-S22 fails=0; scratch 52 fails=0)"
        log("  backend gates PASS (battery S0-S22 + scratch 52)")
        return 0
    finally:
        if p.poll() is None:
            p.kill()
        log_f.close()


def case_all_vue(run_id: str, run_dir: Path, record: dict) -> int:
    """聚合门（Vue profile）：n01 + n04 + suite + battery/scratch。首败即停，非零退出。"""
    for name, fn in (("n01", case_n01_vue), ("n04", case_n04_vue), ("suite", case_suite_vue)):
        if fn(run_id, run_dir, record) != 0:
            return fail(run_id, f"all/{name}", "用例失败（见上文）")
    data = run_dir / "data-gates"
    if case_backend_gates(run_dir, record, (free_port(), data)) != 0:
        return fail(run_id, "all/gates", "battery/scratch 失败")
    record["all_verdict"] = "PASS"
    log("ALL(vue) PASS: n01 + n04 + suite31 + battery S0-S22 + scratch 52")
    return 0


CASES = {
    "n01": case_n01_vue,
    "n04": case_n04_vue,
    "suite": case_suite_vue,
    "all": case_all_vue,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["vue", "vm"], default="vue")
    ap.add_argument("--case", choices=list(CASES), default="n01")
    ap.add_argument("--skip-prep", action="store_true", help="跳过准备阶段（调试用）")
    args = ap.parse_args()

    run_id = f"{int(time.time())}-{os.getpid()}"
    run_dir = ARTIFACTS / f"verify-standalone-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    record: dict = {"run_id": run_id, "profile": args.profile, "case": args.case,
                    "root": str(ROOT), "cli": AUTO_CLI}

    if args.profile == "vm":
        # G4（§10 已裁决：等 plan-910 收口后重探）：原生门当前不可用，显式非零，不做静默跳过。
        return fail(run_id, "profile/vm",
                    "原生门被框架缺口 G4 阻塞（见 docs/plans/004 §10；plan-910 收口后重探）")

    if not args.skip_prep:
        rc = prep(run_id, run_dir, record)
        if rc != 0:
            (run_dir / "record.json").write_text(
                json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
            return rc
    rc = CASES[args.case](run_id, run_dir, record)
    (run_dir / "record.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"EVIDENCE {run_dir}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
