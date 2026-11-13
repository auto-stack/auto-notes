
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
