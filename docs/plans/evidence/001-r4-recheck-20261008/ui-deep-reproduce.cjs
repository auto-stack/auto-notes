const fs=require('fs'),path=require('path');
const {chromium}=require(path.join(process.cwd(),'tests/node_modules/@playwright/test'));
(async()=>{
 const browser=await chromium.launch(),url=process.env.NOTES_URL,results={};
 const body=p=>p.locator('textarea[placeholder="Start writing..."]');
 const save=p=>p.getByRole('button',{name:'Save',exact:true});
 const title=p=>p.locator('input[placeholder="Untitled"]');
 const select=async(p,t)=>{await p.locator('button.note-row').filter({hasText:t}).first().click();await p.waitForTimeout(700);};
 const open=async()=>{const ctx=await browser.newContext(),p=await ctx.newPage();await p.goto(url);await p.getByRole('button',{name:'New note',exact:true}).waitFor();await p.waitForTimeout(500);return p;};
 try{
  const a=await open(),b=await open();
  await select(a,'Welcome');await select(b,'Welcome');
  await body(a).fill('server latest welcome A');await save(a).click();await save(a).waitFor({state:'hidden'});
  await body(b).fill('precious unsaved welcome B');await save(b).click();await b.waitForTimeout(500);
  await select(b,'Shopping List');
  const before={body:await body(b).inputValue(),recover:await b.getByRole('button',{name:'Recover',exact:true}).isVisible()};
  await body(b).fill('new shopping draft C');
  await b.getByRole('button',{name:'Recover',exact:true}).click();await b.waitForTimeout(350);
  results.recover_overwrites_slot={before,after:{title:await title(b).inputValue(),body:await body(b).inputValue(),recover:await b.getByRole('button',{name:'Recover',exact:true}).isVisible(),save:await save(b).isVisible()},server:(await (await b.request.get(url+'/api/v1/notes/n-1')).json()).doc};

  const c=await open(),d=await open();await select(c,'Welcome');await select(d,'Welcome');
  const old=await body(d).inputValue();await body(c).fill('newest server version D');await save(c).click();await save(c).waitFor({state:'hidden'});
  await body(d).fill('conflicting local D');await save(d).click();await d.waitForTimeout(400);
  await d.getByRole('button',{name:'Discard',exact:true}).click();await d.waitForTimeout(400);
  results.discard_stale_server={old,displayed:await body(d).inputValue(),save:await save(d).isVisible(),server:(await (await d.request.get(url+'/api/v1/notes/n-1')).json()).doc};

  const e=await open();await select(e,'Welcome');let first=true,events=[];
  e.on('request',r=>{if(r.method()==='PUT'&&/\/api\/notes\/1$/.test(r.url()))events.push(JSON.parse(r.postData()));});
  await e.route('**/api/notes/1',async route=>{if(route.request().method()==='PUT'&&first){first=false;await route.fetch();await route.abort('failed');}else await route.continue();});
  await body(e).fill('first intent committed response lost');await save(e).click();await e.waitForTimeout(600);
  await body(e).fill('second intent must be saveable');await save(e).click();await e.waitForTimeout(600);
  await save(e).click();await e.waitForTimeout(500);
  results.edited_after_response_loss={requests:events,body:await body(e).inputValue(),save:await save(e).isVisible(),conflict:await e.getByText('Save conflict or storage error').count(),server:(await (await e.request.get(url+'/api/v1/notes/n-1')).json()).doc};
  fs.writeFileSync(path.join(process.env.REVIEW_RUN,'ui-deep-results.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
