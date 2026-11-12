const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('funeral-hall-cost.html','utf8').match(/<script>\s*([\s\S]*?)<\/script>/)[1];
const fields=new Map();
const document={querySelector(s){if(!fields.has(s))fields.set(s,{value:'',innerHTML:'',addEventListener(){}});return fields.get(s);}};
const ctx=vm.createContext({document,console,fetch:()=>new Promise(()=>{}),Date,Number,String,Array,Object,Set,Promise});
vm.runInContext(source,ctx);
ctx.testHalls=JSON.parse(fs.readFileSync('data/funeral-halls.json','utf8')).items;
ctx.testPrices=JSON.parse(fs.readFileSync('data/funeral-hall-prices.json','utf8')).items;
vm.runInContext("halls=testHalls;testPrices.forEach(x=>priceMap['name:'+norm(x.facilityName)]=x)",ctx);
for(let i=0;i<2;i++){
 fields.get('#q').value='창원시립상복공원';vm.runInContext('render()',ctx);
 const html=fields.get('#results').innerHTML;
 assert.equal((html.match(/class="priceitem"/g)||[]).length,8);
 assert.match(html,/빈소·접객실 · 관내<\/b>1,800원 \/ 1㎡당\(1일\)/);
 assert.match(html,/안치실 · 관외<\/b>70,000원 \/ 1구당\(1일\)/);
 assert.match(html,/빈소 총액이 아닙니다/);assert.match(html,/sub02_01_02.html/);
 assert.doesNotMatch(html,/wwwcwsisulorkr|2023-06-01 기준/);
 fields.get('#q').value='강릉';vm.runInContext('render()',ctx);
 assert.doesNotMatch(fields.get('#results').innerHTML,/1㎡당|sub02_01_02.html/);
}
const estimator=fs.readFileSync('assets/estimate/nationwide-prices.js','utf8');
const qtySource=estimator.match(/function qtyFor\(r\) \{[\s\S]*?(?=\n  function hallLines)/)[0];
const q=vm.createContext({number:Number,$:()=>({value:'3'})});vm.runInContext(qtySource,q);
assert.equal(vm.runInContext("qtyFor({unit:'1㎡당(1일)',requiresManualQuantity:true}).qty",q),0);
assert.equal(vm.runInContext("qtyFor({unit:'1㎡당(1일)'}).qty",q),0);
assert.equal(vm.runInContext("qtyFor({unit:'1일'}).qty",q),3);
assert.equal(vm.runInContext("qtyFor({unit:'1회'}).qty",q),1);
assert.match(estimator,/면적당 요금: 빈소 전체 금액이 아닙니다/);
console.log('Sangbok display and area-rate quantity guards passed.');
