#!/usr/bin/env python3
"""run_vue_section.py — NOTES-002 V 段（Vue 真实输入；verify_quick_card_assets --profile vue 调用）。

驱动：auto run（17818/17819）+ Playwright（tests/node_modules）。种子与附件经
应用后端 HTTP 直驱（auto run 后端落自有数据目录——006 D-8 在案，隔离靠进程/端口）。
"""
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

FRONT = "http://127.0.0.1:17818"
BACK = "http://127.0.0.1:17819"

PROBE_MJS = r'''
import { chromium } from '@playwright/test';

const BACK = 'http://127.0.0.1:17819';
const FRONT = 'http://127.0.0.1:17818';
const results = [];
const check = (name, cond, detail) => {
  results.push({ name, ok: !!cond });
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : ' - ' + String(detail ?? '').slice(0, 200)));
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

// 种子（应用后端 HTTP 直驱；隔离=auto run 自有数据目录）
const note = await j(await fetch(BACK + '/api/notes', { method: 'POST', headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ title: '卡片靶α', body: '正文一', folder: '', request_id: 'v-seed-1' }) }));
const note2 = await j(await fetch(BACK + '/api/notes', { method: 'POST', headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ title: '第二条β', body: '正文二', folder: '', request_id: 'v-seed-2' }) }));
check('V-pre two notes seeded', note.id > 0 && note2.id > 0, JSON.stringify(note).slice(0, 80));
console.log('DIAG note full:', JSON.stringify(note).slice(0, 260));
console.log('DIAG all notes:', JSON.stringify(await j(await fetch(BACK + '/api/notes'))).slice(0, 400));

const FIX = process.env.QC_FIXTURE_DIR;
const RUN = Math.random().toString(36).slice(2, 8);
async function importPath(op, nid, path, name) {
  const r = await fetch(BACK + '/api/assets/v1/import', { method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ operation_id: op + '-' + RUN, note_id: String(nid), path, name, mime: 'image/png', kind: 'image', source: 'test' }) });
  return j(r);
}
const r1 = await importPath('v-imp-valid', note.id, FIX + '/valid-1x1.png', '有效图.png');
check('V-pre valid attached', r1.ok === true, JSON.stringify(r1).slice(0, 120));
const r2 = await importPath('v-imp-corrupt', note.id, FIX + '/corrupt.png', '损坏图.png');
check('V-pre corrupt attached', r2.ok === true, JSON.stringify(r2).slice(0, 120));
const r4 = await importPath('v-imp-n2', note2.id, FIX + '/valid-1x1.png', '第二条图.png');
check('V-pre note2 attached', r4.ok === true, JSON.stringify(r4).slice(0, 120));

// 打开应用 → 选第一条 → 打开快速卡片
await page.goto(FRONT);
await page.getByText('卡片靶α').first().waitFor({ state: 'visible', timeout: 60000 });
// 选中目标笔记（应用初始选中 = 最新一条；卡片须编辑既定靶）
await page.getByText('卡片靶α').first().click();
// 确定性等待：主编辑器已装载目标正文（异步 SelectNote/LoadDraft 完成）
await page.locator('textarea').first().waitFor({ state: 'visible', timeout: 20000 });
for (let i = 0; i < 40; i++) {
  const v = await page.locator('textarea').first().inputValue();
  if (v === '正文一') break;
  await page.waitForTimeout(250);
}
await page.getByText('Quick card').first().click();
await page.getByText('Attachments').first().waitFor({ state: 'visible', timeout: 30000 });
check('V-01 card opens with editor + attachments', true);
const tas = page.locator('textarea[placeholder="FP body"]');
check('V-01 three editor instances (main-edit/main-create/card)', (await tas.count()) === 3, await tas.count());

// A-02 中文键入（卡片透传链）→ 提交 saved
const cardTa = tas.nth(2);
await cardTa.fill('正文一');
await cardTa.press('End');
await page.keyboard.type('卡片增补α');
await page.waitForTimeout(400);
const typed = await cardTa.inputValue();
check('V-02 IME-channel Chinese typed in card', typed.includes('卡片增补α'), typed.slice(0, 60));
const cardBox = page.locator('div').filter({ hasText: 'Quick card' }).filter({ has: page.locator('textarea[placeholder="FP body"]') }).last();
await cardBox.getByText('Submit').click();
// 轮询服务端正文直至包含提交标记（UI 保存链路异步完成）
let saved = null;
for (let i = 0; i < 15; i++) {
  await page.waitForTimeout(700);
  saved = await j(await fetch(BACK + `/api/notes/${note.id}/result`));
  if (saved.ok === true && (saved.note?.body || '').includes('卡片增补α')) break;
}
check('V-02 submit via card saved', saved.ok === true && (saved.doc?.body || '').includes('卡片增补α'), JSON.stringify({ body: (saved.doc?.body || '').slice(0, 60), err: saved.err_code }));
console.log('DIAG saved full:', JSON.stringify(saved).slice(0, 300));
// 诊断：fp 草稿槽与卡片状态面
const slotKey = 'fpdraft|local|notes-main|note:' + note.id + '|edit';
const slot = await j(await fetch(BACK + '/api/fp/draft/get', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ draft_key: slotKey }) }));
console.log('DIAG card slot:', JSON.stringify(slot).slice(0, 200));
console.log('DIAG card badge text:', (await cardBox.innerText()).slice(0, 160).split(String.fromCharCode(10)).join('|'));

// A-02 重复点击：同文同修订重放，revision 不重复推进
const rev1 = saved.doc.revision;
await cardTa.fill('正文一');
await page.keyboard.type('卡片增补α');
await cardBox.getByText('Submit').click();
await cardBox.getByText('Submit').click().catch(() => {});
// 轮询至落定后断言：重复点击必须恰推进 1 个修订（saving 在途忽略 + 意图重放）
let saved2 = null;
for (let i = 0; i < 15; i++) {
  await page.waitForTimeout(700);
  saved2 = await j(await fetch(BACK + `/api/notes/${note.id}/result`));
  if (saved2.ok === true && (saved2.doc?.body || '').includes('卡片增补α')) break;
}
const rev2 = saved2.doc?.revision;
check('V-03 dup-click keeps single revision advance', saved2.ok === true && rev2 === rev1 + 1 && (saved2.doc?.body || '').includes('卡片增补α'),
  { rev1, rev2, err: saved2.err_code, body: (saved2.doc?.body || '').slice(0, 40) });

// A-06 附件在位：图片真实解码 + 损坏解码失败态（原件管理不受扰）
const imgs = page.locator('img[alt*="图"]');
let n = 0;
try {
  await imgs.first().waitFor({ state: 'visible', timeout: 8000 });
  n = await imgs.count();
} catch { n = await imgs.count(); }
check('V-04 image previews rendered', n >= 1, n);
let okDecode = false, badDecode = false;
for (let i = 0; i < n; i++) {
  const el = imgs.nth(i);
  const alt = (await el.getAttribute('alt')) || '';
  await el.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(500);
  const w = await el.evaluate((img) => img.naturalWidth);
  if (alt.includes('有效图') && w > 0) okDecode = true;
  if (alt.includes('损坏图') && w === 0) badDecode = true;
}
check('V-04 valid image decodes (naturalWidth>0)', okDecode, n);
check('V-05 corrupt image decode-failure state (naturalWidth=0), original managed', badDecode, n);

// A-06 宽窄参数
const cardRoot = page.locator('div').filter({ hasText: 'Quick card' }).filter({ has: page.locator('textarea[placeholder="FP body"]') }).last();
const cls0 = await cardRoot.getAttribute('class');
console.log('DIAG width before:', JSON.stringify(cls0));
await page.getByText('Wide', { exact: true }).last().click();
await page.waitForTimeout(500);
const cls1 = await cardRoot.getAttribute('class');
console.log('DIAG width after:', JSON.stringify(cls1));
check('V-06 width toggle changes card width class', cls0 !== cls1, { cls0: cls0?.slice(0, 50), cls1: cls1?.slice(0, 50) });
await page.getByText('Narrow', { exact: true }).last().click();
await page.waitForTimeout(200);

// A-06 明暗参数（根 dark class 翻转即主题达卡片区域）
const darkOf = async () => await page.evaluate(() => {
  const root = document.querySelector('[data-auto-theme-root="1"]');
  const a = (root?.className || '').includes('dark');
  const b = document.documentElement.className.includes('dark');
  return (a || b) ? 'dark' : 'light';
});
const html0 = await darkOf();
const themeBtn = page.getByRole('button').first();
const btnCount = await themeBtn.count();
await themeBtn.first().click().catch((e) => console.log('DIAG dark click err:', String(e).slice(0, 80)));
await page.waitForTimeout(600);
const html1 = await darkOf();
console.log('DIAG dark:', btnCount, html0, '->', html1);
check('V-06 dark/light toggle reaches document', html0 !== html1, `theme buttons=${btnCount} ${html0} -> ${html1}`);

// A-06 最近项
check('V-06 recent list renders second note', (await page.getByText('第二条β').count()) >= 1, '');

// 关闭保脏稿：键入 → 关闭 → 重开 → 输入保留
await cardTa.fill('');
await page.keyboard.type('关闭保留检查');
await page.getByText('×', { exact: true }).last().click();
await page.waitForTimeout(400);
check('V-07 card closed', (await page.getByText('Attachments').count()) === 0, '');
await page.getByText('Quick card').first().click();
await page.waitForTimeout(500);
const tas2 = page.locator('textarea[placeholder="FP body"]');
check('V-07 reopen keeps dirty input (不清草稿)', (await tas2.nth(2).inputValue()).includes('关闭保留检查'), (await tas2.nth(2).inputValue()).slice(0, 40));

// 卡片↔管理页同 ID：主编辑实例与卡片实例同文（同 draft prop 往返）
check('V-08 management page shares the same draft text',
  (await tas2.nth(0).inputValue()) === (await tas2.nth(2).inputValue()), '');

// 显式纯文本粘贴（Ctrl+V 系统剪贴板）
await tas2.nth(2).fill('');
await page.context().grantPermissions(['clipboard-read', 'clipboard-write']);
await page.evaluate(() => navigator.clipboard.writeText('剪贴板显式粘贴γ'));
await tas2.nth(2).click();
await page.keyboard.press('Control+v');
await page.waitForTimeout(300);
check('V-09 explicit plain-text paste into card', (await tas2.nth(2).inputValue()).includes('剪贴板显式粘贴γ'), (await tas2.nth(2).inputValue()).slice(0, 40));

check('V-10 zero page errors', pageErrors.length === 0, pageErrors.slice(0, 3));

await browser.close();
const fails = results.filter((r) => !r.ok);
console.log('VRESULT ' + JSON.stringify({ pass: results.length - fails.length, fail: fails.length }));
process.exit(fails.length ? 1 : 0);
'''


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


def main(ROOT, ARTIFACTS, check, boundary):
    run_dir = ARTIFACTS / "qc-vue"
    run_dir.mkdir(parents=True, exist_ok=True)
    probe = ROOT / "tests" / ".qc_vue_probe.mjs"
    probe.write_text(PROBE_MJS, encoding="utf-8")

    env = dict(os.environ)
    env["NOTES_TEST_MODE"] = "1"
    env["AUTO_ALLOW_PARTIAL_DB"] = "1"
    env["QC_FIXTURE_DIR"] = str(ROOT / "tests" / "fixtures" / "capture")
    env["AUTO_HTTP_PORT"] = "17819"
    # P-V 形态（verify_standalone 同款；AGENTS.md 构建纪律）：debug 后端 exe 直跑
    # + vite dev——不走 auto run 的 release 硬编码路径
    backend_exe = Path(os.environ.get(
        "NOTES_BACK_EXE",
        "D:/autostack/auto-lang/target/generated-consumers/f3f98a9e/debug/auto-notes-30db9907-back.exe"))
    scaffold = ROOT / "gen/front/vue"
    procs = []
    lb = open(run_dir / "backend.log", "w", encoding="utf-8")
    procs.append(subprocess.Popen([str(backend_exe)], cwd=str(ROOT), env=env,
                                  stdout=lb, stderr=subprocess.STDOUT))
    lv = open(run_dir / "vite.log", "w", encoding="utf-8")
    procs.append(subprocess.Popen(
        ["node", str(scaffold / "node_modules/vite/bin/vite.js"),
         "--host", "127.0.0.1", "--port", "17818", "--strictPort"],
        cwd=str(scaffold), env=env, stdout=lv, stderr=subprocess.STDOUT))
    try:
        if not wait_http(BACK + "/api/health", timeout=300):
            check(False, "V app backend ready", "timeout (see " + str(run_dir / "backend.log") + ")")
            return
        if not wait_http(FRONT, timeout=300):
            check(False, "V app front ready", "timeout (see " + str(run_dir / "vite.log") + ")")
            return
        node = subprocess.run(["node", str(probe)], cwd=str(ROOT / "tests"), env=env,
                              capture_output=True, text=True, timeout=600)
        out = (node.stdout or "") + "\n" + (node.stderr or "")
        print(out[-2500:])
        for line in out.splitlines():
            if line.startswith("PASS ") or line.startswith("FAIL "):
                name = line[5:].split(" - ")[0].strip()
                check(not line.startswith("FAIL"), name[:90], line[len(name) + 5:][:160])
        ok = "VRESULT" in out and '"fail":0' in out.split("VRESULT")[1][:40]
        check(ok, "V section exit green", out[-150:])
    finally:
        for pr in reversed(procs):
            if pr and pr.poll() is None:
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(pr.pid)], capture_output=True)
        for n in ["auto-notes-30db9907-back.exe", "node.exe"]:
            subprocess.run(["taskkill", "/F", "/IM", n], capture_output=True)
