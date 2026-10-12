const {chromium}=require(process.cwd()+'/tests/node_modules/@playwright/test');
const fs=require('fs'),path=require('path');
(async()=>{
const browser=await chromium.launch({headless:true}),page=await browser.newPage();
const results={},errors=[];
const persist=()=>fs.writeFileSync(path.join(process.env.R5_RUN,'independent-ui.json'),JSON.stringify(results,null,2));
page.on('pageerror',e=>errors.push(e.message));
const wait=()=>page.waitForTimeout(650),title=page.locator('input[placeholder="Untitled"]');
async function open(){await page.goto(process.env.NOTES_URL);await title.waitFor();await wait();}
async function api(method,url,data){return page.evaluate(async({method,url,data})=>{const r=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:data===undefined?undefined:JSON.stringify(data)});return r.json();},{method,url,data});}
async function create(t){return api('POST','/api/v1/notes',{request_id:'create-'+t,title:t,body:'base',folder:''});}
async function select(t){await page.locator('button.note-row').filter({hasText:t}).first().click();await wait();}
async function state(){return page.evaluate(async()=>{const s=(await import('/src/stores/useNotesStore.ts')).useNotesStore(),out={};for(const key of ['notes','active_id','search','draft_id','draft_title','draft_revision','dirty','conflict','has_recovery','rec_title','has_recovery2','rec2_title','stash_blocked','has_pend','pend_title','has_prev','prev_title'])out[key]=s[key].value;return out;});}
async function save(){await page.getByRole('button',{name:'Save',exact:true}).click();await wait();}
try{
await open(); const B=await create('SearchProbe-B'),A=await create('SearchProbe-A');await open();
await page.locator('input[placeholder="Search notes"]').fill('SearchProbe');await wait();await select('SearchProbe-A');await title.fill('NoMatch-A');
const before=await state();await select('SearchProbe-B');const after=await state();
results.filtered_navigation={before,after,errors:[...errors],serverA:await api('GET','/api/v1/notes/'+A.doc.note_id),expected_draft_id:B.doc.legacy_id,pass:after.draft_id===B.doc.legacy_id&&after.draft_title==='SearchProbe-B'};
persist();
await open();const C=await create('ChainProbe-C');await open();await select('ChainProbe-C');let writes=0;
await page.route('**/api/notes/*/result',async route=>{if(route.request().method()!=='PUT')return route.continue();writes++;if(writes===1){const r=await route.fetch();results.chain_first=await r.json();return route.abort();}if(writes===2)return route.abort();return route.continue();});
await title.fill('Chain-C1');await save();const s1=await state();await title.fill('Chain-C2');await save();const s2=await state();await title.fill('Chain-C3');await save();const s3=await state();if(s3.dirty)await save();const s4=await state();
const srv=await api('GET','/api/v1/notes/'+C.doc.note_id);results.repeated_unknown={s1,s2,s3,s4,server:srv,pass:!s4.dirty&&srv.doc.title==='Chain-C3'};await page.unroute('**/api/notes/*/result');
persist();
await open();const R=await create('RecoverProbe-R'),Z=await create('OnlyVisible-Z');await open();await select('RecoverProbe-R');
await api('POST','/api/v1/test/fault',{stage:'after_manifest'});await title.fill('Recovered-C1-R');await save();await title.fill('Recovered-content-R');await select('OnlyVisible-Z');await api('POST','/api/v1/test/fault',{stage:'off'});
results.before_recovery_search=await state();persist();
await page.locator('input[placeholder="Search notes"]').fill('OnlyVisible-Z');await wait();results.after_recovery_search=await state();persist();await page.getByRole('button',{name:'Recover',exact:true}).first().click();await wait();const restored=await state();await page.getByRole('button',{name:'Pin note',exact:true}).click();await wait();
const rd=await api('GET','/api/v1/notes/'+R.doc.note_id),zd=await api('GET','/api/v1/notes/'+Z.doc.note_id);results.filtered_recovery_pin={restored,after:await state(),R:rd,Z:zd,pass:rd.doc.pinned===true&&zd.doc.pinned===false};
persist();
await open();const F=await create('FullProbe-F'),G=await create('FullProbe-G'),H=await create('FullProbe-H');await open();
async function external(d,t){const current=(await api('GET','/api/v1/notes/'+d.doc.note_id)).doc;const r=await api('PUT','/api/v1/notes/'+d.doc.note_id,{request_id:'external-'+t,expected_revision:current.revision,title:t,body:'external'});if(!r.ok)throw Error('external writer failed');}
await select('FullProbe-F');await title.fill('Draft-F');await external(F,'Server-F');await save();await select('FullProbe-G');await title.fill('Draft-G');await external(G,'Server-G');await save();await select('FullProbe-H');await title.fill('Draft-H');await external(H,'Server-H');const fullBefore=await state();await page.locator('input[placeholder="Search notes"]').fill('NeverMatch');await wait();const fullAfter=await state();results.full_slots_search={before:fullBefore,after:fullAfter,pass:fullAfter.search===fullBefore.search&&fullAfter.draft_title==='Draft-H'&&fullAfter.dirty};persist();
results.oracle_failures=Object.entries(results).filter(([k,v])=>v.pass===false).map(([k])=>k);results.errors=errors;
fs.writeFileSync(path.join(process.env.R5_RUN,'independent-ui.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));process.exitCode=results.oracle_failures.length?1:0;
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
