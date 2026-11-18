// Actual browser regression for conditionally published ordinance references.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const reports=[];
 try {
  for(const width of [390,1280]){
   const page=await browser.newPage({viewport:{width,height:900}});
   const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.route('**/*',route=>{
    const url=route.request().url();
    if(url.startsWith('http://127.0.0.1:8765/'))return route.continue();
    // Test the checked-out asset when markup uses the production absolute URL.
    if(url==='https://www.dahamsangjo.co.kr/assets/regional-funeral-base.png')return route.fulfill({status:200,contentType:'image/png',body:fs.readFileSync('assets/regional-funeral-base.png')});
    return route.abort();
   });
   await page.goto('http://127.0.0.1:8765/funeral-hall-cost.html');
   await page.waitForFunction(()=>document.querySelector('#results .result'));
   for(const name of ['진부','평창장례식장','진부']){
    await page.locator('#q').fill(name);await page.locator('#searchBtn').click();
    const cards=page.locator('#results .result');await cards.first().waitFor();
    if(name==='진부'){
     assert.equal(await cards.count(),1);
     const body=await cards.innerText();
     for(const text of ['공시 참고요금','분향실 40,000원(관외 53,000원)/1일','접객실 120,000원(관외 160,000원)/1일','안치실 40,000원(관외 53,000원)/1일','염습료 100,000원(관외 130,000원)/1회·1구','부분일 계산','자동견적에 합산하지 않습니다'])assert.ok(body.includes(text),text);
     assert.equal(await cards.locator('.priceitem').count(),0);
     assert.ok((await cards.locator('a.official').getAttribute('href')).includes('ordinSeq=2033869'));
    }else assert.equal(await cards.locator('.priceitem').count(),8);
   }
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'horizontal overflow');
   for(const img of await page.locator('img').all())await img.scrollIntoViewIfNeeded();
   await page.waitForFunction(()=>[...document.images].every(i=>i.complete));
   assert.equal(await page.locator('img').evaluateAll(images=>images.filter(i=>!i.complete||i.naturalWidth===0).length),0,'broken images');
   assert.deepEqual(errors,[]);
   fs.mkdirSync('qa-output',{recursive:true});
   await page.screenshot({path:`qa-output/jinbu-reference-${width}.png`,fullPage:true});
   console.log('JINBU_VISUAL:'+width+':'+fs.readFileSync(`qa-output/jinbu-reference-${width}.png`).toString('base64'));
   await page.locator('#q').fill('경상국립대학교병원장례식장');await page.locator('#searchBtn').click();
   const gnuh=page.locator('#results .result');assert.equal(await gnuh.count(),1);
   const gnuhText=await gnuh.innerText();
   for(const text of ['80,000원/1일','7,000원/1시간','12시간 이상','상한·조정','직원·직원 가족','자동견적과 과거 공시가격 대체 합산은 보류'])assert.ok(gnuhText.includes(text),text);
   assert.equal(await gnuh.locator('.priceitem').count(),0);
   assert.ok((await gnuh.locator('a.official').getAttribute('href')).includes('rbsIdx=42'));
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await gnuh.screenshot({path:`qa-output/gnuh-reference-${width}.jpg`,type:'jpeg',quality:80});
   console.log('GNUH_VISUAL:'+width+':'+fs.readFileSync(`qa-output/gnuh-reference-${width}.jpg`).toString('base64'));
   reports.push({width,result:'PASS',repeatedSearch:true,referenceOnly:true});await page.close();
  }
  fs.writeFileSync('qa-output/jinbu-reference-report.json',JSON.stringify(reports,null,2));
  console.log(JSON.stringify(reports));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
