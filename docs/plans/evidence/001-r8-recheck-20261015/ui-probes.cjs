const {chromium}=require(process.cwd()+'/tests/node_modules/@playwright/test');
const fs=require('fs'),path=require('path'),cp=require('child_process');
(async()=>{
const browser=await chromium.launch({headless:true});const results={};
async function sql(text){cp.execFileSync(process.env.REVIEW_PYTHON,['-c','import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.executescript(sys.argv[2]);c.commit();c.close()',path.join(process.env.R5_RUN,'data','inbox.db'),text]);}
async function session(name){
 const page=await browser.newPage(),events=[],errors=[];page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(['PUT','PATCH','DELETE'].includes(r.method()))events.push({method:r.method(),url:r.url(),data:r.postData()});});
 const title=page.locator('input[placeholder="Untitled"]'),wait=()=>page.waitForTimeout(650);
 async function api(method,url,data){return page.evaluate(async({method,url,data})=>{const r=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:data===undefined?undefined:JSON.stringify(data)});return r.json();},{method,url,data});}
 async function open(){await page.goto(process.env.NOTES_URL);await title.waitFor();await wait();}
 async function state(){return page.evaluate(async()=>{const s=(await import('/src/stores/useNotesStore.ts')).useNotesStore(),o={};for(const k of ['draft_id','draft_title','draft_body','draft_revision','dirty','conflict','action_error','has_pend','has_prev','draft_request_id','all_tags'])o[k]=s[k].value;return o;});}
 await open();const made=await api('POST','/api/v1/notes',{request_id:'r9-'+name,title:'Retry-'+name,body:'base',folder:''});await open();await page.locator('button.note-row').filter({hasText:'Retry-'+name}).click();await wait();
 return {page,events,errors,title,wait,api,state,made,close:()=>page.close()};
}
try{
let s=await session('pin');
await sql("CREATE TRIGGER review_pin BEFORE UPDATE OF pinned ON notes BEGIN SELECT RAISE(ABORT,'r9 transient pin'); END;");
await s.page.getByRole('button',{name:'Pin note',exact:true}).click();await s.wait();
results.pin={first:await s.state(),first_requests:[...s.events],banner:await s.page.getByText('Action failed: change not saved').count()};
await sql('DROP TRIGGER review_pin;');const count=s.events.length;
await s.page.getByRole('button',{name:'Pin note',exact:true}).click();await s.wait();
results.pin.retry=await s.state();results.pin.retry_requests=s.events.slice(count);results.pin.server=await s.api('GET','/api/v1/notes/'+s.made.doc.note_id);results.pin.errors=s.errors;
results.pin.pass=results.pin.banner===1 && results.pin.first.action_error==='pin' && results.pin.errors.length===0 && results.pin.server.doc.pinned===true&&results.pin.retry.action_error==='';await s.close();
s=await session('dirty-tag');
await sql("CREATE TRIGGER review_tag BEFORE UPDATE OF tags_json ON notes BEGIN SELECT RAISE(ABORT,'r9 transient tags'); END;");
await s.title.fill('Retry-dirty-tag-one');await s.page.getByRole('button',{name:'Tag',exact:true}).click();await s.page.locator('input[placeholder="tag name"]').fill('new-tag');await s.page.keyboard.press('Enter');await s.wait();
results.dirty_tag={after_failure:await s.state(),server_after_failure:await s.api('GET','/api/v1/notes/'+s.made.doc.note_id),requests:[...s.events]};
await sql('DROP TRIGGER review_tag;');await s.title.fill('Retry-dirty-tag-two');await s.page.getByRole('button',{name:'Save',exact:true}).click();await s.wait();
results.dirty_tag.after_save=await s.state();results.dirty_tag.server_after_save=await s.api('GET','/api/v1/notes/'+s.made.doc.note_id);results.dirty_tag.errors=s.errors;
results.dirty_tag.pass=!results.dirty_tag.after_save.dirty&&results.dirty_tag.server_after_save.doc.title==='Retry-dirty-tag-two';await s.close();
s=await session('normal-control');await s.title.fill('Retry-control-one');await s.page.getByRole('button',{name:'Tag',exact:true}).click();await s.page.locator('input[placeholder="tag name"]').fill('good-tag');await s.page.keyboard.press('Enter');await s.wait();
const controlFirst=await s.state();await s.title.fill('Retry-control-two');await s.page.getByRole('button',{name:'Save',exact:true}).click();await s.wait();const controlLast=await s.state(),controlServer=await s.api('GET','/api/v1/notes/'+s.made.doc.note_id);
results.normal_control={after_tag:controlFirst,after_save:controlLast,server:controlServer,errors:s.errors,pass:!controlLast.dirty&&controlServer.doc.title==='Retry-control-two'&&controlServer.doc.revision===3&&controlServer.doc.tags.includes('good-tag')&&s.errors.length===0};await s.close();
s=await session('mask-control');await sql("CREATE TRIGGER review_mask BEFORE UPDATE OF state ON notes BEGIN SELECT RAISE(ABORT,'r9 delete before pin'); END;");
await s.page.getByRole('button',{name:'Delete',exact:true}).click();await s.wait();await s.page.getByRole('button',{name:'Delete',exact:true}).click();await s.wait();
const maskBefore=await s.state();await sql("DROP TRIGGER review_mask; CREATE TRIGGER review_mask BEFORE UPDATE OF pinned ON notes BEGIN SELECT RAISE(ABORT,'r9 pin must execute'); END;");const maskCount=s.events.length;
await s.page.getByRole('button',{name:'Pin note',exact:true}).click();await s.wait();
results.masked_pin={after_delete:maskBefore,after_pin:await s.state(),requests:s.events.slice(maskCount),banner:await s.page.getByText('Action failed: change not saved').count()};
results.masked_pin.pass=results.masked_pin.requests.some(r=>r.method==='PATCH');await sql('DROP TRIGGER review_mask;');await s.close();
results.failures=Object.entries(results).filter(([k,v])=>v.pass===false).map(([k])=>k);
fs.writeFileSync(path.join(process.env.R5_RUN,'new-ui-results.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));process.exitCode=results.failures.length?1:0;
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=2;});
