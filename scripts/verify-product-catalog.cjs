const fs=require('fs'),path=require('path'),http=require('http'),assert=require('assert');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..'),out=path.resolve(process.env.PRODUCT_QA_OUTPUT||path.join(__dirname,'../../qa'));fs.mkdirSync(out,{recursive:true});
const server=http.createServer((req,res)=>{let file=path.join(root,decodeURIComponent(req.url.split('?')[0]));try{const ext=path.extname(file);res.setHeader('Content-Type',({'.html':'text/html','.jpg':'image/jpeg','.png':'image/png','.js':'text/javascript','.css':'text/css','.json':'application/json'})[ext]||'application/octet-stream');res.end(fs.readFileSync(file));}catch{res.statusCode=404;res.end();}});
(async()=>{await new Promise(r=>server.listen(8765,'127.0.0.1',r));const browser=await chromium.launch({headless:true,channel:'msedge'});
 const results=[];
 for(const width of [360,390,430,768,1280]){
  const page=await browser.newPage({viewport:{width,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8765/funeral-cost-calculator.html');
  await page.waitForFunction(()=>document.querySelectorAll('.urnProductCard').length===90);
  for(const step of [6,7,8]){
   await page.evaluate(n=>setStep(n),step);await page.locator('.step.active img.catalogPhoto').evaluateAll(imgs=>Promise.all(imgs.map(i=>{i.loading='eager';return i.decode().catch(()=>{throw Error(i.src)})})));
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}/${step}`);
   const cards=page.locator('.step.active [data-popup-product]');const count=await cards.count();assert.equal(count,step===6?15:step===7?10:90);
   for(let i=0;i<count;i++){
    const card=cards.nth(i);const key=await card.getAttribute('data-popup-product');const src=await card.locator('img.catalogPhoto').getAttribute('src');const before=await page.evaluate(k=>({total:calcData().total,old:state[productDetails[k].group+'Price']||0,amount:productDetails[k].amount}),key);await card.click();
    assert.equal(await page.locator('#productDetailImage').getAttribute('src'),src,`mapping ${key}`);
    await page.locator('#productDetailImage').evaluate(i=>i.decode());
    assert.equal(await page.locator('#productDetailTitle').textContent(),await page.evaluate(k=>productDetails[k].title,key));
    await page.locator('#productDetailSelect').click();
    assert(await card.evaluate(c=>c.classList.contains('selected')));
    assert(await page.evaluate(k=>{const d=productDetails[k];return state[d.group]===d.value&&state[d.group+'Price']===d.amount},key));
    assert.equal(await page.evaluate(()=>calcData().total),before.total-before.old+before.amount,`calculation ${key}`);
   }
   await cards.first().scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,`${width}-step${step}.png`)});
   await cards.first().click();await page.locator('#productDetailImage').evaluate(i=>i.decode());await page.screenshot({path:path.join(out,`${width}-modal${step}.png`)});
   assert(await page.locator('#productDetailImage').evaluate(i=>{const r=i.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight}), 'popup image fits viewport');
   await page.keyboard.press('Shift+Tab');assert.equal(await page.evaluate(()=>document.activeElement.id),'productDetailSelect');
   await page.keyboard.press('Tab');assert(await page.locator('.productDetailClose').evaluate(b=>b===document.activeElement));
   await page.getByRole('button',{name:'다음 상품 →',exact:true}).click();await page.locator('#productDetailImage').evaluate(i=>i.decode());
   await page.getByRole('button',{name:'← 이전 상품',exact:true}).click();await page.keyboard.press('Escape');assert.equal(await page.locator('#productDetailModal').getAttribute('aria-hidden'),'true');
   results.push({width,step,count});
  }
  for(const button of await page.locator('.urnCat').all()){
   const category=await button.textContent();await button.click();
   assert.equal(await page.locator('.urnProductCard:visible').count(),await page.evaluate(cat=>urnProducts20260930.filter(x=>urnCategoryMatch(x.category,cat)).length,category));
  }
  assert.equal(await page.evaluate(()=>[...document.querySelectorAll('img')].filter(i=>!i.src.includes('daham_logo')&&!i.closest('.photoBrand')).length),0,'Every photo has a watermark');
  assert.equal(errors.length,0,errors.join('\n'));await page.close();
 }
 fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(results,null,2));await browser.close();server.close();console.log('PASS',results);
})().catch(e=>{console.error(e);server.close();process.exit(1)});
