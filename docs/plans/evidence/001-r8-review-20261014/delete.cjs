const {chromium}=require(process.cwd()+'/tests/node_modules/@playwright/test');
const fs=require('fs'),path=require('path');
(async()=>{
const browser=await chromium.launch({headless:true}),page=await browser.newPage();
const results={};
async function state(){return page.evaluate(async()=>{const s=(await import('/src/stores/useNotesStore.ts')).useNotesStore(),o={};for(const k of ['draft_id','draft_title','draft_body','dirty','has_recovery','rec_title','has_recovery2','rec2_title','conflict','confirm_delete'])o[k]=s[k].value;return o;});}
try{
await page.goto(process.env.NOTES_URL);
const title=page.locator('input[placeholder="Untitled"]');await title.waitFor();await page.waitForTimeout(800);
const before=await state();
await title.fill('UNSAVED-delete-failure-001');
await page.locator('textarea[placeholder="Start writing..."]').fill('用户尚未保存的中文\n第二行');
await page.waitForTimeout(200);results.before=await state();
let deletion=null;
await page.route('**/api/notes/*',async route=>{
 if(route.request().method()!=='DELETE')return route.continue();
 const response=await route.fetch();deletion=await response.json();
 return route.fulfill({response});
});
// The wrapper's isolated DB is locked via an explicit SQLite trigger so the
// real backend returns false. A separate process creates the trigger first.
const cp=require('child_process');
cp.execFileSync(process.env.REVIEW_PYTHON,['-c',"import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute(\"CREATE TRIGGER reject_delete BEFORE UPDATE OF state ON notes BEGIN SELECT RAISE(ABORT,'review deletion failure'); END\"); c.commit(); c.close()",path.join(process.env.R5_RUN,'data','inbox.db')]);
await page.getByRole('button',{name:'Delete',exact:true}).click();await page.waitForTimeout(150);
const labels=await page.locator('button').allTextContents();results.buttons=labels;
await page.getByRole('button',{name:'Delete',exact:true}).click();await page.waitForTimeout(800);
results.delete_result=deletion;results.after=await state();
results.server=await page.evaluate(async id=>{const r=await fetch('/api/notes/'+id);return r.json();},before.draft_id);
results.pass=deletion===false && results.after.dirty && results.after.draft_title==='UNSAVED-delete-failure-001';
fs.writeFileSync(path.join(process.env.R5_RUN,'delete-result.json'),JSON.stringify(results,null,2));
console.log(JSON.stringify(results,null,2));process.exitCode=results.pass?0:1;
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=2;});
