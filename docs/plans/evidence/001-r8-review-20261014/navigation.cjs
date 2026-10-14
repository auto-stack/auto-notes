const {chromium}=require(process.cwd()+'/tests/node_modules/@playwright/test');
const fs=require('fs'),path=require('path');
(async()=>{
const browser=await chromium.launch({headless:true}),page=await browser.newPage(),results={errors:[]};
page.on('pageerror',e=>results.errors.push(e.message));
const wait=()=>page.waitForTimeout(650),title=page.locator('input[placeholder="Untitled"]');
async function api(method,url,data){return page.evaluate(async({method,url,data})=>{const r=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:data===undefined?undefined:JSON.stringify(data)});return r.json();},{method,url,data});}
async function open(){await page.goto(process.env.NOTES_URL);await title.waitFor();await wait();}
async function state(){return page.evaluate(async()=>{const s=(await import('/src/stores/useNotesStore.ts')).useNotesStore(),o={};for(const k of ['notes','active_id','draft_id','draft_title','draft_revision','dirty','conflict','draft_request_id'])o[k]=s[k].value;return o;});}
try{
await open();const B=await api('POST','/api/v1/notes',{request_id:'nav-B',title:'NavProbe-B',body:'base',folder:''});await api('POST','/api/v1/notes',{request_id:'nav-A',title:'NavProbe-A',body:'base',folder:''});await open();
await page.locator('input[placeholder="Search notes"]').fill('NavProbe');await wait();
await page.locator('button.note-row').filter({hasText:'NavProbe-A'}).click();await wait();await title.fill('Removed-A');
await page.locator('button.note-row').filter({hasText:'NavProbe-B'}).click();await wait();results.after_navigation=await state();
await title.fill('NavProbe-B-one');await page.getByRole('button',{name:'Save',exact:true}).click();await wait();results.after_first_save=await state();results.server_first=await api('GET','/api/v1/notes/'+B.doc.note_id);
await title.fill('NavProbe-B-two');await page.getByRole('button',{name:'Save',exact:true}).click();await wait();results.after_second_save=await state();results.server_second=await api('GET','/api/v1/notes/'+B.doc.note_id);
results.pass=results.errors.length===0 && !results.after_second_save.dirty && results.server_second.doc.title==='NavProbe-B-two';
fs.writeFileSync(path.join(process.env.R5_RUN,'navigation-result.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));process.exitCode=results.pass?0:1;
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=2;});
