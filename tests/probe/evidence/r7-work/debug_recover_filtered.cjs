const {chromium}=require(process.cwd()+'/tests/node_modules/@playwright/test');
(async()=>{
const browser=await chromium.launch({headless:true}),page=await browser.newPage();
const wait=()=>page.waitForTimeout(700),title=page.locator('input[placeholder="Untitled"]');
async function open(){await page.goto(process.env.NOTES_URL);await title.waitFor();await wait();}
async function api(m,u,d){return page.evaluate(async({m,u,d})=>{const r=await fetch(u,{method:m,headers:{'Content-Type':'application/json'},body:d===undefined?undefined:JSON.stringify(d)});return r.json();},{m,u,d});}
async function state(){return page.evaluate(async()=>{const s=(await import('/src/stores/useNotesStore.ts')).useNotesStore();const o={};for(const k of ['notes','active_id','search','draft_id','draft_title','dirty','conflict','has_recovery','rec_title','has_recovery2','stash_blocked'])o[k]=s[k].value;return o;});}
try{
await open();const R=await api('POST','/api/v1/notes',{request_id:'dbg-R',title:'Dbg-R',body:'b',folder:''});
// 制造入槽：外部推进 + 本地草稿 + 冲突导航
await select('Dbg-R');await title.fill('Dbg-R-draft');
await api('PUT','/api/v1/notes/'+R.doc.note_id,{request_id:'dbg-ext',expected_revision:1,title:'Dbg-R-ext',body:'e'});
await page.getByRole('button',{name:'Save',exact:true}).click();await wait();
await page.locator('button.note-row').filter({hasText:'Welcome'}).first().click();await wait();
console.log('stashed:', JSON.stringify(await state()));
await page.locator('input[placeholder="Search notes"]').fill('Welcome');await wait();
console.log('filtered:', JSON.stringify(await state()));
await page.getByRole('button',{name:'Recover',exact:true}).first().click();await wait();
console.log('after Recover:', JSON.stringify(await state()));
}catch(e){console.log('FATAL',e.message);}
finally{await browser.close();}
async function select(t){await page.locator('button.note-row').filter({hasText:t}).first().click();await wait();}
})().catch(e=>{console.error(e);process.exitCode=1});
