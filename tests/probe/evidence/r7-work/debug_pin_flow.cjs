// debug: replay filtered_recovery_pin step by step with state dumps
const {chromium}=require(process.cwd()+'/tests/node_modules/@playwright/test');
(async()=>{
const browser=await chromium.launch({headless:true}),page=await browser.newPage();
const wait=()=>page.waitForTimeout(650),title=page.locator('input[placeholder="Untitled"]');
const errors=[];
page.on('pageerror',e=>errors.push(e.message));
async function open(){await page.goto(process.env.NOTES_URL);await title.waitFor();await wait();}
async function api(method,url,data){return page.evaluate(async({method,url,data})=>{const r=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:data===undefined?undefined:JSON.stringify(data)});return r.json();},{method,url,data});}
async function state(){return page.evaluate(async()=>{const s=(await import('/src/stores/useNotesStore.ts')).useNotesStore(),out={};for(const key of ['notes','active_id','search','draft_id','draft_title','draft_revision','dirty','conflict','has_recovery','rec_title','has_recovery2','stash_blocked','has_pend','pend_title','pend_revision','has_prev','prev_title','has_prev2','prev2_title','draft_request_id'])out[key]=s[key].value;return out;});}
async function save(){await page.getByRole('button',{name:'Save',exact:true}).click();await wait();}
try{
await open();const R=await create('RecoverProbe-R'),Z=await create('OnlyVisible-Z');await open();await select('RecoverProbe-R');
async function create(t){return api('POST','/api/v1/notes',{request_id:'create-'+t,title:t,body:'base',folder:''});}
async function select(t){await page.locator('button.note-row').filter({hasText:t}).first().click();await wait();}
await api('POST','/api/v1/test/fault',{stage:'after_manifest'});await title.fill('Recovered-C1-R');await save();
console.log('after C1 save:', JSON.stringify(await state()));
await title.fill('Recovered-content-R');
console.log('after C2 edit:', JSON.stringify(await state()));
await select('OnlyVisible-Z');
console.log('after select Z:', JSON.stringify(await state()));
await api('POST','/api/v1/test/fault',{stage:'off'});
await page.locator('input[placeholder="Search notes"]').fill('OnlyVisible-Z');await wait();
console.log('after search:', JSON.stringify(await state()));
await page.getByRole('button',{name:'Recover',exact:true}).first().click();await wait();
console.log('after Recover:', JSON.stringify(await state()));
await page.getByRole('button',{name:'Pin note',exact:true}).click();await wait();
console.log('after Pin:', JSON.stringify(await state()));
console.log('errors:', errors);
const rd=await api('GET','/api/v1/notes/'+R.doc.note_id),zd=await api('GET','/api/v1/notes/'+Z.doc.note_id);
console.log('R pinned:', rd.doc.pinned, '| Z pinned:', zd.doc.pinned);
}catch(e){console.log('FATAL', e.message, errors);}
finally{await browser.close();}
})().catch(e=>{console.error('OUTER', e);process.exitCode=1});
