// r6 green-run copy of the r5-recheck independent UI driver.
// Only delta: Recover/Save clicks are state-guarded — with the flush adjudication
// fix the C2 navigation flush can land directly (no stash, no banner), so the
// stash-path clicks only run when a slot exists. Actions/assertions otherwise
// identical to the committed independent-ui.cjs.
const {chromium}=require(process.cwd()+'/tests/node_modules/@playwright/test');
const fs=require('fs');
const path=require('path');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage();
 const results={}; const requests=[];
 page.on('response',async res=>{if(res.request().method()==='PUT' && /\/result$/.test(res.url())) {try{requests.push({payload:res.request().postDataJSON(),result:await res.json()});}catch{}}});
 const wait=()=>page.waitForTimeout(750);
 const title=page.locator('input[placeholder="Untitled"]');
 async function open(){await page.goto(process.env.NOTES_URL); await page.getByRole('button',{name:'New note'}).waitFor(); await wait();}
 async function api(method,url,data){return page.evaluate(async({method,url,data})=>{const r=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:data===undefined?undefined:JSON.stringify(data)});return r.json();},{method,url,data});}
 async function create(t){return api('POST','/api/v1/notes',{request_id:'probe-create-'+t,title:t,body:'base',folder:''});}
 async function select(t){await page.locator('button.note-row').filter({hasText:t}).first().click();await wait();}
 async function state(){return page.evaluate(async()=>{const s=(await import('/src/stores/useNotesStore.ts')).useNotesStore();const out={};for(const key of ['draft_id','draft_title','draft_body','draft_revision','draft_request_id','dirty','conflict','has_recovery','rec_title','rec_request_id','has_recovery2','rec2_title','rec2_request_id','has_pend','pend_title','has_prev','prev_title'])out[key]=s[key].value;return out;});}
 async function bump(id,t){const d=(await api('GET','/api/v1/notes/'+id)).doc;const r=await api('PUT','/api/v1/notes/'+id,{request_id:'ext-'+Date.now(),expected_revision:d.revision,title:t,body:'external'});if(!r.ok)throw Error(JSON.stringify(r));}
 async function save(){await page.getByRole('button',{name:'Save',exact:true}).click();await wait();}
 try{
  await open();
  const A=await create('Probe-A'),B=await create('Probe-B'),C=await create('Probe-C');await open();
  await select('Probe-A');await title.fill('precious-A');await bump(A.doc.note_id,'server-A');await save();await select('Probe-B');
  await title.fill('precious-B');await bump(B.doc.note_id,'server-B');await save();await select('Probe-C');
  await title.fill('precious-C');await wait();
  const before=await state();
  await page.getByRole('button',{name:'Recover',exact:true}).first().click();await wait();
  const after=await state();
  await page.getByRole('button',{name:'Recover',exact:true}).first().click();await wait();
  const second=await state();
  results.full_slots_recover={before,after,second,visible_title:await title.inputValue(),b_preserved:[after.draft_title,after.rec_title,after.rec2_title].includes('precious-B')};
  await open();const D=await create('Probe-D'),E=await create('Probe-E');await open();await select('Probe-D');
  let dropped=false;
  await page.route('**/api/notes/*/result',async route=>{if(route.request().method()==='PUT'&&!dropped){dropped=true;const res=await route.fetch();results.c1_commit=await res.json();await route.abort();}else await route.continue();});
  await title.fill('C1-unconfirmed');await save();await title.fill('C2-new-draft');await wait();
  const edited=await state();await select('Probe-E');const stashed=await state();
  const restoredPre=await state();
  if(restoredPre.has_recovery||restoredPre.has_recovery2){await page.getByRole('button',{name:'Recover',exact:true}).first().click();await wait();}
  const restored=await state();
  if(restored.dirty){await save();}
  const retry1=await state();
  if(retry1.dirty){await save();}
  const retry2=await state();
  results.recovered_changed_intent={edited,stashed,restored,retry1,retry2,server:await api('GET','/api/v1/notes/'+D.doc.note_id)};
  results.requests=requests;
  results.oracle_failures=[];
  if(!results.full_slots_recover.b_preserved)results.oracle_failures.push('IND-VUE-1 existing B draft preserved');
  if(results.recovered_changed_intent.retry2.dirty || results.recovered_changed_intent.server.doc.title!=='C2-new-draft')results.oracle_failures.push('IND-VUE-2 recovered new intent can save');
  if(results.oracle_failures.length)process.exitCode=1;
  fs.writeFileSync(path.join(process.env.R5_RUN,'independent-ui.json'),JSON.stringify(results,null,2));
  console.log(JSON.stringify(results,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
