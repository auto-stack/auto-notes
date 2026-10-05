const fs = require('fs');
const path = require('path');
const { chromium } = require(path.join(process.cwd(), 'tests/node_modules/@playwright/test'));

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const a = await context.newPage();
  const b = await context.newPage();
  const url = process.env.NOTES_URL;
  const events = [];
  b.on('request', r => {
    if (r.method() === 'PUT' && /\/api\/notes\/\d+$/.test(r.url())) events.push(JSON.parse(r.postData()));
  });
  const body = p => p.locator('textarea[placeholder="Start writing..."]');
  const save = p => p.getByRole('button', { name: 'Save', exact: true });
  try {
    for (const p of [a,b]) {
      await p.goto(url);
      await p.locator('button.note-row').filter({hasText:'Welcome'}).first().click();
      await body(p).waitFor();
    }
    await body(a).fill('client-A saved');
    await body(b).fill('client-B conflict draft must survive');
    await save(a).click();
    await save(a).waitFor({state:'hidden'});
    await save(b).click();
    await b.waitForTimeout(300);
    const conflictBefore = {body:await body(b).inputValue(), saveVisible:await save(b).isVisible(), requests:events.slice()};
    await b.getByRole('button',{name:'Tag',exact:true}).click();
    await b.locator('input[placeholder="tag name"]').fill('review-tag');
    await b.locator('input[placeholder="tag name"]').press('Enter');
    await b.waitForTimeout(400);
    const conflictAfterTag = {body:await body(b).inputValue(), saveVisible:await save(b).isVisible()};
    await b.screenshot({path:path.join(process.env.REVIEW_RUN,'ui-after-tag.png')});

    await b.locator('button.note-row').filter({hasText:'Shopping List'}).first().click();
    await body(b).fill('folder flush must remain visible');
    await b.getByRole('button',{name:'personal',exact:true}).click();
    await b.waitForTimeout(400);
    await b.locator('button.note-row').filter({hasText:'Shopping List'}).first().click();
    const folderFlush = {body:await body(b).inputValue(), saveVisible:await save(b).isVisible()};

    // Commit a save but drop its HTTP response; an exact client retry must reuse the same id.
    await b.getByRole('button',{name:'All',exact:true}).click();
    await b.locator('button.note-row').filter({hasText:'Welcome'}).first().click();
    await body(b).fill('save committed before response loss');
    let intercepted;
    await b.route('**/api/notes/1',async route => {
      if (route.request().method() !== 'PUT') return route.continue();
      intercepted=JSON.parse(route.request().postData());
      await route.fetch();
      await route.abort('failed');
    },{times:1});
    await save(b).click();
    await b.waitForTimeout(300);
    await save(b).click();
    await b.waitForTimeout(300);
    const serverAfterLoss = await (await b.request.get(url + '/api/v1/notes/n-1')).json();
    const responseLoss = {intercepted,body:await body(b).inputValue(),saveVisible:await save(b).isVisible(),lastTwoRequests:events.slice(-2),serverAfterLoss};
    fs.writeFileSync(path.join(process.env.REVIEW_RUN,'ui-results.json'),JSON.stringify({conflictBefore,conflictAfterTag,folderFlush,responseLoss},null,2));
    console.log(JSON.stringify({conflictBefore,conflictAfterTag,folderFlush,responseLoss}));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode=1; });
