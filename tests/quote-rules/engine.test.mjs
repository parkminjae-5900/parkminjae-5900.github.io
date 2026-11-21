import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {calculate,PRODUCTS,REQUIRED} from '../../dev/quote-rules/engine.mjs';
import {fromLegacy,fromPrototype} from '../../dev/quote-rules/adapters.mjs';
const pkg=(productId='nobinso',rest={})=>calculate({mode:'package',productId,...rest});
const proof={status:'confirmed',reference:'자동검사용 가상 요금표 — 실시설 아님',facilityId:'TEST',roomId:'A',applicabilityConfirmed:true,billing:'hourly',category:'room',unit:'hour',unitPrice:10000};
const room=(rest={})=>({id:'room',facilityId:'TEST',roomId:'A',unit:'hour',unitPrice:10000,hours:24,billing:'hourly',proof,...rest});
const terms=(productId='family249',quantity=16,unit='인시간')=>({status:'confirmed',reference:'자동검사용 가상 추가약정 — 실제 상품 구성 아님',productId,quantity,unit});
const tariff=(productId='family249',serviceId='helper',unit='인시간',unitPrice=15000)=>({...terms(productId),serviceId,unit,unitPrice});
const deltaEvidence={...terms('nobinso'),serviceId:'shroud',amount:80000};
const helper=(rest={})=>({id:'helper',quantity:24,unit:'인시간',unitPrice:15000,coverage:terms(),tariff:tariff(),...rest});
const context={facilityId:'TEST',roomId:'A'};
for(const [id,p] of Object.entries(PRODUCTS)) {
  test(`${p.name}: 상품가에 78만원 재합산 금지`,()=>{
    const result=fromLegacy({mode:'package',productId:id});
    assert.equal(result.subtotal,p.price);
    assert.equal(result.rows.filter(r=>r.id==='package').length,1);
    assert.equal(result.finalTotal,null);
    if(id!=='nobinso')assert.ok(result.pending.some(x=>x.id==='director'));
  });
  test(`${p.name}: 두 입력 어댑터 동일 모드 소계 일치`,()=>{
    assert.equal(fromLegacy({mode:'package',productId:id}).subtotal,fromPrototype({product:p.price}).subtotal);
  });
}
test('기존 개별 필수 항목은 한 번만 78만원',()=>{
  assert.equal(fromLegacy({}).subtotal,780000);
  assert.equal(calculate({mode:'itemized',services:[{id:'director',quantity:1,unit:'행사'}]}).subtotal,780000);
});
test('모드 혼합과 미지정 상품 거부',()=>{
  assert.throws(()=>calculate({mode:'itemized',productId:'nobinso'}));
  assert.throws(()=>calculate({mode:'package'}));
  assert.throws(()=>calculate({}));
  assert.throws(()=>fromPrototype({product:0}));
});
test('중복 서비스/시설 행 거부',()=>{
  assert.throws(()=>pkg('family249',{services:[helper(),helper()]}));
  assert.throws(()=>pkg('family249',{external:[room(),room()]}));
});
test('무빈소에서 이전 48시간 빈소료 제외, 안치·입관 미확인 유지',()=>{
  const r=pkg('nobinso',{...context,external:[room({hours:48})]});
  assert.equal(r.subtotal,1200000);
  assert.equal(r.rows.find(x=>x.id==='room').status,'not-used');
  assert.ok(r.pending.some(x=>x.id==='morgue'));
  assert.ok(r.pending.some(x=>x.id==='preparation'));
  assert.ok(r.warnings.length);
});
test('시설비 미확인은 0원 확정이 아닌 null',()=>{
  const r=pkg('family249',{external:[room({proof:null})]});
  assert.equal(r.subtotal,2490000);
  assert.equal(r.rows.find(x=>x.id==='room').amount,null);
  assert.equal(r.finalTotal,null);
});
test('다른 시설·호실·최저가 자동대입 차단',()=>{
  for(const ctx of [{},{facilityId:'OTHER',roomId:'A'},{facilityId:'TEST',roomId:'B'}]) {
    assert.equal(pkg('family249',{...ctx,external:[room()]}).subtotal,2490000);
  }
});
test('과거 공식 요금도 현행 적용조건 미확인이면 제외',()=>{
  assert.equal(pkg('family249',{...context,external:[room({proof:{...proof,applicabilityConfirmed:false}})]}).subtotal,2490000);
});
for(const hours of [0,24,48,72]) test(`시간당 빈소료 ${hours}시간`,()=>{
  assert.equal(pkg('family249',{...context,external:[room({hours})]}).subtotal,2490000+hours*10000);
});
test('일 요금: 과금규칙 미확인 비례계산 금지',()=>{
  assert.equal(pkg('family249',{...context,external:[room({unit:'day',unitPrice:240000,hours:30,billing:undefined})]}).subtotal,2490000);
});
test('확인된 일 올림/비례 규칙 각각 적용',()=>{
  for(const [billing,expected] of [['ceil24',480000],['prorata24',300000]]) {
    assert.equal(pkg('family249',{...context,external:[room({unit:'day',unitPrice:240000,hours:30,billing,proof:{...proof,billing,unit:'day',unitPrice:240000}})]}).subtotal,2490000+expected);
  }
});
test('출처와 계산 규칙 불일치 차단',()=>{
  assert.equal(pkg('family249',{...context,external:[room({billing:'prorata24',unit:'day'})]}).subtotal,2490000);
});
test('추가 도우미는 확인된 포함 인시간을 뺀 초과분만',()=>{
  const r=pkg('family249',{services:[helper()]});
  assert.equal(r.subtotal,2610000); // 249만원 + (24-16)*15000
  assert.match(r.rows.find(x=>x.id==='helper').reason,/추가 8/);
});
test('도우미 이용시간 증가와 감소 재계산',()=>{
  assert.equal(pkg('family249',{services:[helper({quantity:32})]}).subtotal,2730000);
  assert.equal(pkg('family249',{services:[helper({quantity:8})]}).subtotal,2490000);
});
test('추가 도우미 포함량 또는 단가 미확인 시 합산 보류',()=>{
  for(const changes of [{coverage:null},{tariff:null},{unit:'명'}]) assert.equal(pkg('family249',{services:[helper(changes)]}).subtotal,2490000);
});
test('상품 전환 뒤 예전 상품 추가약정 재사용 금지',()=>{
  assert.equal(pkg('general360',{services:[helper()]}).subtotal,3600000);
});
test('추가 차량 횟수 및 거리: 확인된 단위와 포함량만 계산',()=>{
  const r=pkg('family249',{services:[{id:'vehicleExtra',quantity:130,unit:'km',unitPrice:2000,coverage:terms('family249',100,'km'),tariff:tariff('family249','vehicleExtra','km',2000)}]});
  assert.equal(r.subtotal,2550000);
  assert.equal(pkg('family249',{services:[{id:'limo',quantity:1,unit:'회',unitPrice:450000}]}).subtotal,2490000);
});
test('무빈소 기본 관·수의는 재합산 안 함',()=>{
  const services=['coffin','shroud'].map(id=>({id,...PRODUCTS.nobinso.coverage[id],unitPrice:170000}));
  assert.equal(pkg('nobinso',{services}).subtotal,1200000);
});
test('다른 수의 규격 전체 판매가 자동 합산 금지',()=>{
  const r=fromLegacy({mode:'package',productId:'nobinso',state:{shroud:'육수청홍수의',shroudPrice:170000}});
  assert.equal(r.subtotal,1200000);assert.ok(r.pending.some(x=>x.id==='shroud'));
});
test('용품 변경은 근거 있는 차액만, 상품 변경하면 차액 무효',()=>{
  const line={id:'shroud',quantity:1,kind:'upgrade',delta:80000,deltaEvidence};
  assert.equal(pkg('nobinso',{services:[line]}).subtotal,1280000);
  assert.equal(pkg('general360',{services:[line]}).subtotal,3600000);
  assert.equal(pkg('nobinso',{services:[{...line,deltaEvidence:null}]}).subtotal,1200000);
});
test('임의 공제·음수 차액·무한대·문자 수량 거부',()=>{
  for(const value of [-1,Infinity,NaN,'오류']) assert.throws(()=>pkg('family249',{services:[helper({quantity:value})]}));
  assert.throws(()=>pkg('nobinso',{services:[{id:'urn',quantity:1,kind:'upgrade',delta:-1,deltaEvidence:{...deltaEvidence,serviceId:'urn',amount:-1}}]}));
  assert.throws(()=>pkg('family249',{services:[helper({unitPrice:Infinity})]}));
});
test('무료 확인과 미확인 금액 구별',()=>{
  const external={id:'cremation',quantity:1,unit:'once',unitPrice:0,proof:{status:'confirmed',reference:'검사용 감면확인',category:'cremation',unit:'once',unitPrice:0}};
  assert.equal(pkg('nobinso',{external:[external]}).rows.find(x=>x.id==='cremation').status,'priced');
  assert.equal(pkg('nobinso',{external:[{...external,proof:null}]}).rows.find(x=>x.id==='cremation').amount,null);
});
test('수기 외부 요금과 기타비용은 검증 없이 더하지 않음',()=>{
  assert.equal(fromPrototype({product:1200000,values:{otherCost:780000,otherNote:'지도사·입관용품',cremation:100000,mealCount:80,mealPrice:10000}}).subtotal,1200000);
  assert.equal(fromLegacy({values:{hallCost:500000,hallEtc:100000}}).subtotal,780000);
});
test('기존 개별 선택 단가 보존, 용품 0원 placeholder는 보류',()=>{
  const result=fromLegacy({state:{shroud:'육수청홍수의',shroudPrice:170000,coffin:'오동나무 0.6관',coffinPrice:170000},values:{helper:1,limo:true}});
  assert.equal(result.subtotal,1690000);
  assert.ok(fromLegacy({state:{coffin:'상담 관',coffinPrice:0}}).pending.some(x=>x.id==='coffin'));
});
test('입력·공식 구성 불변 및 반복계산 안정성',()=>{
  const input={mode:'package',productId:'family249',...context,external:[room()]};
  const before=JSON.stringify(input); assert.deepEqual(calculate(input),calculate(input));assert.equal(JSON.stringify(input),before);
  assert.throws(()=>{PRODUCTS.nobinso.price=0;});
});
const fixture=JSON.parse(fs.readFileSync(new URL('./baseline.json',import.meta.url),'utf8'));
function oldLegacy(values={},state={}) {
  const sandbox={state, val:id=>Number(values[id]||0),document:{getElementById:id=>({checked:values[id]===true})}};
  vm.createContext(sandbox);vm.runInContext(fixture.legacyConstants+'\n'+fixture.legacyFunction+'\nresult=calcData();',sandbox);return sandbox.result;
}
function oldPrototype(base,values={}) {
  const elements={}; const sandbox={chosen:null,won:n=>String(n),safe:String,$safeNumber:id=>Number(values[id]||0),$:id=>elements[id] ||= {value:values[id]||''}};
  vm.createContext(sandbox);vm.runInContext(fixture.prototypeFunction+`\nrenderDetailed(${base},null,null);`,sandbox);return Number(elements.detailedTotal.textContent);
}
for(const [id,p] of Object.entries(PRODUCTS)) test(`${p.name}: 실제 원본 함수 동일 무입력 조건 재현`,()=>{
  assert.equal(oldLegacy().total,780000);
  assert.equal(oldPrototype(p.price),p.price);
  assert.equal(fromPrototype({product:p.price}).subtotal,p.price);
});
test('실제 원본 함수: 선택 품목 합계 재현',()=>{
  const state={shroud:'육수청홍수의',shroudPrice:170000,coffin:'오동나무 0.6관',coffinPrice:170000};
  const values={helper:1,limo:true};
  assert.equal(oldLegacy(values,state).total,fromLegacy({state,values}).subtotal);
});
test('원본 PR24: 기타에 78만원 재입력 시 위험 재현, 신규 엔진 보류',()=>{
  assert.equal(oldPrototype(1200000,{otherCost:780000}),1980000);
  const r=fromPrototype({product:1200000,values:{otherCost:780000}});
  assert.equal(r.subtotal,1200000); assert.ok(r.pending.some(x=>x.id==='other'));
});
test('지도사 4일과 입관보조 2일은 자동 무료연장 금지',()=>{
  const r=fromLegacy({mode:'package',productId:'nobinso',values:{directorDays:4,assistantDays:2}});
  assert.ok(r.pending.some(x=>x.id==='director'));assert.ok(r.pending.some(x=>x.id==='assistant'));
  assert.equal(r.subtotal,1200000);
});
test('추가단가의 단위 불일치 차단',()=>{
  assert.equal(pkg('family249',{services:[helper({tariff:terms('family249',16,'명')})]}).subtotal,2490000);
});
test('시설비·도우미 추가를 포함한 두 어댑터 동일조건',()=>{
  const coverage=terms('family249',2,'인회'), tariff={...terms('family249',2,'인회'),serviceId:'helper',unitPrice:120000};
  const l=fromLegacy({mode:'package',productId:'family249',values:{helper:3},contracts:{helper:{coverage,tariff}},...context,external:[room()]});
  const p=fromPrototype({product:2490000,services:[{id:'helper',quantity:3,unit:'인회',unitPrice:120000,coverage,tariff}],...context,external:[room()]});
  assert.equal(l.subtotal,2850000);assert.equal(l.subtotal,p.subtotal);
});
test('공백·배열·객체·불리언 숫자 입력 차단',()=>{
  for(const quantity of [' ',[],[2],{},true]) assert.throws(()=>pkg('family249',{services:[helper({quantity})]}));
});
test('0수량 입력도 필수 포함/미확인 행 유지',()=>{
  const services=[{id:'director',quantity:0}];
  assert.equal(pkg('nobinso',{services}).rows.find(x=>x.id==='director').status,'included');
  assert.ok(pkg('family249',{services}).pending.some(x=>x.id==='director'));
});
test('시설비와 기타 시설비 둘 다 확인 대기에 보존',()=>{
  const r=fromLegacy({values:{hallCost:500000,hallEtc:100000}});
  const row=r.rows.find(x=>x.id==='facilityOther');
  assert.match(row.label,/hallCost 500000/);assert.match(row.label,/hallEtc 100000/);
  assert.equal(row.amount,null);
});
test('요금 근거의 항목·단가와 입력 불일치 차단',()=>{
  for(const changes of [{serviceId:'bus'},{unitPrice:1000}]) {
    assert.equal(pkg('family249',{services:[helper({tariff:{...tariff(),...changes}})]}).subtotal,2490000);
  }
  assert.equal(pkg('family249',{...context,external:[room({unitPrice:20000})]}).subtotal,2490000);
  assert.equal(pkg('nobinso',{services:[{id:'shroud',quantity:1,kind:'upgrade',delta:90000,deltaEvidence}]}).subtotal,1200000);
});
