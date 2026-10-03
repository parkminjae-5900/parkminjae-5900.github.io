const fs=require('node:fs'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const base=process.env.QA_BASE_URL||'http://127.0.0.1:8765';
(async()=>{
 const browser=await chromium.launch({headless:true});
 fs.mkdirSync('qa-output',{recursive:true});
 for(const width of [390,1440]){
  const page=await browser.newPage({viewport:{width,height:900}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  // Explicit test fixture exercises mislabeled room rows; never shipped as facility prices.
  const data=JSON.parse(fs.readFileSync('data/funeral-hall-price-baseline.json','utf8'));
  data.halls['신화장례식장']=[
   {category:'기타',label:'분향실',detail:'1일',amount:999000},
   {category:'염습실/입관실',label:'빈소+접객실',detail:'1일',amount:888000},
   {category:'안치실',label:'안치료',detail:'1일',amount:10000},
   {category:'입관실',label:'입관실 사용료',detail:'1회',amount:30000}
  ];
  await page.route('**/data/funeral-hall-price-baseline.json',r=>r.fulfill({json:data}));
  await page.route('**/data/funeral-hall-prices.json',r=>r.fulfill({json:{items:[]}}));
  await page.goto(base+'/funeral-cost-calculator.html');
  await page.waitForFunction(()=>document.querySelector('#nationwide-status').textContent.includes('가격은'));
  await page.evaluate(()=>setStep(3));
  await page.getByRole('button',{name:'서울',exact:true}).click();
  await page.selectOption('#subregionSelect','강남구');
  await page.evaluate(()=>chooseHall('삼성서울병원장례식장'));
  await page.locator('#facility-row-0').check();
  assert.ok(await page.evaluate(()=>calcData().external)>0);
  await page.locator('#hallEtc').fill('55555');
  await page.evaluate(()=>setStep(1));
  await page.locator('[data-field=funeralType][data-value=무빈소]').click();
  assert.equal(await page.evaluate(()=>calcData().external),0,'previous room and miscellaneous amounts reset');
  await page.evaluate(()=>setStep(3));
  assert.equal(await page.locator('#hallList input').count(),0,'unconfirmed Gangnam facilities excluded');
  assert.equal(await page.inputValue('#hallSelect'),'');
  assert.equal(await page.locator('.regionDetailField').isVisible(),false,'manual unconfirmed facility cannot bypass list');
  await page.selectOption('#subregionSelect','영등포구');
  assert.deepEqual(await page.locator('#hallList b').allTextContents(),['신화장례식장']);
  await page.evaluate(()=>chooseHall('삼성서울병원장례식장'));
  assert.equal(await page.inputValue('#hallSelect'),'','direct selection cannot bypass allowlist');
  await page.evaluate(()=>chooseHall('신화장례식장'));
  const labels=await page.locator('.facility-price strong').allTextContents();
  assert.equal(labels.length,2);assert.ok(labels.every(x=>!/빈소|분향|접객/.test(x)));
  await page.locator('#facility-row-0').check();
  await page.locator('#facility-row-1').check();
  assert.equal(await page.evaluate(()=>calcData().external),50000,'only morgue and preparation included');
  assert.ok(!/999,000|888,000/.test(await page.evaluate(()=>summaryText())));
  await page.locator('#hallSearch').fill('없는시설');
  assert.equal(await page.inputValue('#hallSelect'),'신화장례식장','search preserves only eligible selection');
  await page.locator('#hallSearch').fill('');
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:'qa-output/mubinso-'+width+'.png',fullPage:true});
  await page.getByRole('button',{name:'경기',exact:true}).click();
  await page.selectOption('#subregionSelect','부천시');
  assert.deepEqual(await page.locator('#hallList b').allTextContents(),['부천시민장례식장']);
  await page.getByRole('button',{name:'제주',exact:true}).click();
  const sub=await page.locator('#subregionSelect option').nth(1).getAttribute('value');
  await page.selectOption('#subregionSelect',sub);
  assert.equal(await page.locator('#hallList input').count(),0);
  assert.ok((await page.locator('#hallList').textContent()).includes('상담'));
  await page.evaluate(()=>setStep(1));
  await page.locator('[data-field=funeralType][data-value="3일장"]').click();
  await page.evaluate(()=>setStep(3));
  assert.equal(await page.locator('.regionDetailField').isVisible(),true);
  await page.getByRole('button',{name:'서울',exact:true}).click();
  await page.selectOption('#subregionSelect','강남구');
  assert.ok(await page.locator('#hallList input').count()>0,'ordinary funeral list restored');
  assert.deepEqual(errors,[]);
  await page.close();
 }
 for(const mode of ['failure','wrong-address','malformed']){
  const page=await browser.newPage();
  await page.route('**/data/mubinso-facilities.json',r=> mode==='failure'?r.abort():r.fulfill({json:mode==='malformed'?{}:{items:[{facilityName:'신화장례식장',address:'다른 주소',status:'confirmed'}]}}));
  await page.goto(base+'/funeral-cost-calculator.html');
  await page.waitForFunction(()=>!document.querySelector('#nationwide-status').textContent.includes('불러오는'));
  await page.evaluate(()=>setStep(1));
  await page.locator('[data-field=funeralType][data-value=무빈소]').click();
  await page.evaluate(()=>setStep(3));
  await page.getByRole('button',{name:'서울',exact:true}).click();
  await page.selectOption('#subregionSelect','영등포구');
  assert.equal(await page.locator('#hallList input').count(),0,mode+' never expands unverified list');
  await page.close();
 }
 await browser.close();console.log('Mubinso QA passed: confirmed lists, room exclusion, stale-price reset, ordinary restoration, source failure and address mismatch.');
})().catch(e=>{console.error(e);process.exit(1)});
