// Development only: no production page imports this module.
const source = 'https://www.dahamsangjo.co.kr/nobinso-cost.html';
const freeze = value => {
  Object.values(value).forEach(v => { if (v && typeof v === 'object') freeze(v); });
  return Object.freeze(value);
};
export const PRODUCTS = freeze({
  nobinso: {name:'무빈소', price:1200000, source, checkedAt:'2026-10-27', coverage:{
    director:{quantity:1, unit:'행사', days:3, specification:'1명·3일', source},
    assistant:{quantity:1, unit:'행사', days:1, specification:'염습상례사 1명·1일, 입관 업무', source},
    supplies:{quantity:1, unit:'세트', specification:'입관용품 일체', source},
    coffin:{quantity:1, unit:'개', specification:'오동나무 규격관', source},
    shroud:{quantity:1, unit:'벌', specification:'화장수의', source}
  }, notes:['모바일 부고장 제공', '화장예약 지원', '관내 앰뷸런스 운구지원: 거리·횟수 미공개']},
  family249:{name:'가족장',price:2490000,source:'https://www.dahamsangjo.co.kr/family.html',coverage:{}},
  general360:{name:'일반장',price:3600000,source:'https://www.dahamsangjo.co.kr/',coverage:{}},
  premium499:{name:'프리미엄',price:4990000,source:'https://www.dahamsangjo.co.kr/postpaid-price.html',coverage:{}}
});
export const REQUIRED = freeze({
  director:{label:'전담 장례지도사',amount:400000,unit:'행사'},
  supplies:{label:'입관용품 일체',amount:230000,unit:'세트'},
  assistant:{label:'보조 장례지도사(입관식)',amount:150000,unit:'행사'}
});
const SERVICE_IDS = new Set([...Object.keys(REQUIRED),'shroud','coffin','urn','maleSuit','femaleSuit','helper','limo','bus','vehicleExtra','crossBar','other']);
const EXTERNAL_IDS = new Set(['room','morgue','preparation','food','cremation','burial','facilityOther']);
const text = x => typeof x === 'string' && x.trim().length > 0;
export function number(value, name='금액', integer=false) {
  if (!['number','string'].includes(typeof value) || (typeof value === 'string' && !value.trim())) throw Error(name+' 미입력');
  const n=Number(value);
  if (!Number.isFinite(n) || n < 0 || (integer && !Number.isSafeInteger(n))) throw Error(name+' 오류');
  return n;
}
const money = n => number(n,'원 단위 금액',true);
const amount = (price,quantity) => money(Math.round(money(price)*number(quantity,'수량')));
const evidence = e => e && e.status === 'confirmed' && text(e.reference);
const contract = (e,id) => evidence(e) && e.productId === id;

/** Pure calculation. A subtotal is never a final invoice, even when all selected rows are resolved. */
export function calculate(input) {
  if (!['itemized','package'].includes(input.mode)) throw Error('견적 모드를 명시하세요');
  if (input.mode === 'itemized' && input.productId) throw Error('개별 모드에 상품가를 더할 수 없습니다');
  const product=input.mode === 'package' ? PRODUCTS[input.productId] : null;
  if (input.mode === 'package' && !product) throw Error('상품을 선택하세요');
  const rows=[], pending=[], warnings=[];
  const add=(id,label,value,status,reason,reference=null)=>rows.push({id,label,amount:value,status,reason,reference});
  const hold=(id,label,reason)=>{add(id,label,null,'pending',reason);pending.push({id,reason});};
  if (product) {
    add('package',product.name,product.price,'priced','기본 상품가',product.source);
    if (input.productId !== 'nobinso') hold('composition','상품 구성','정확한 인원·용품·차량 제공 범위 미확인');
  } else for (const [id,r] of Object.entries(REQUIRED)) add(id,r.label,r.amount,'priced','개별 견적 필수항목');

  const seen=new Set(), active=new Set();
  for (const line of input.services || []) {
    if (!SERVICE_IDS.has(line.id)) throw Error('알 수 없는 서비스 항목: '+line.id);
    if (seen.has(line.id)) throw Error('동일 서비스 중복 입력: '+line.id);
    seen.add(line.id);
    const label=line.label || line.id, q=number(line.quantity,'수량');
    if(line.unitPrice!==undefined) money(line.unitPrice);
    if(line.delta!==undefined) money(line.delta);
    if (q===0) continue;
    active.add(line.id);
    if (!product) {
      if (REQUIRED[line.id]) {
        if(q!==1 || line.unit!==REQUIRED[line.id].unit || line.kind==='upgrade') throw Error('필수 기본항목 변경은 별도 계약 필요');
        continue; // already charged once
      }
      if (!evidence(line.tariff) || line.tariff.serviceId!==line.id || line.tariff.unit!==line.unit || line.tariff.unitPrice!==line.unitPrice) {hold(line.id,label,'개별 선택 단가 확인 필요');continue;}
      add(line.id,label,amount(line.unitPrice,q),'priced','개별 선택',line.tariff.reference);
      continue;
    }
    if (line.id==='other') {hold(line.id,label,'자유입력 기타비용은 중복 검증 불가: 항목 분류 필요');continue;}
    const terms=contract(line.coverage,input.productId) ? line.coverage : product.coverage[line.id];
    if (line.kind==='upgrade') {
      if (!contract(line.deltaEvidence,input.productId) || line.deltaEvidence.serviceId!==line.id || line.deltaEvidence.amount!==line.delta) {hold(line.id,label,'상품에 대응하는 교체 차액 근거 필요');continue;}
      add(line.id,label,money(line.delta),'priced','승인된 교체 차액만 반영',line.deltaEvidence.reference);
      continue;
    }
    if (!terms || terms.unit!==line.unit || (terms.specification && terms.specification!==line.specification)) {
      hold(line.id,label,'상품 포함 범위·수량·규격 확인 필요');continue;
    }
    const included=number(terms.quantity,'포함 수량');
    if (line.days !== undefined && (!terms.days || number(line.days,'근무일수') > terms.days)) {
      hold(line.id,label,'상품 제공 일수 초과: 연장 조건과 추가요금 확인 필요');continue;
    }
    const extra=Math.max(0,q-included);
    if (!extra) {add(line.id,label,0,'included','상품 포함: 개별 단가 재합산 안 함',terms.source || terms.reference);continue;}
    if (!evidence(line.tariff) || line.tariff.productId!==input.productId || line.tariff.unit!==line.unit || line.tariff.serviceId!==line.id || line.tariff.unitPrice!==line.unitPrice) {hold(line.id,label,'포함 수량 초과분 단가·단위 확인 필요');continue;}
    add(line.id,label,amount(line.unitPrice,extra),'priced',`전체 ${q} - 포함 ${included} = 추가 ${extra} ${line.unit}`,line.tariff.reference);
  }
  // Required package services are never automatically added as 780,000 KRW.
  if (product) for (const id of Object.keys(REQUIRED)) if(!active.has(id)) {
    const c=product.coverage[id];
    if(c) add(id,REQUIRED[id].label,0,'included','기본 제공 범위 내 포함',c.source);
    else hold(id,REQUIRED[id].label,'포함 여부 미확인: 추가 청구 보류');
  }
  const externalSeen=new Set();
  for (const line of input.external || []) {
    if (!EXTERNAL_IDS.has(line.id) || externalSeen.has(line.id)) throw Error('외부항목 식별 오류 또는 중복: '+line.id);
    externalSeen.add(line.id);
    const label=line.label || line.id;
    if(line.unitPrice!==undefined) money(line.unitPrice);
    if (line.id==='room' && input.productId==='nobinso') {
      add(line.id,label,0,'not-used','무빈소: 빈소만 미사용');
      if (Number(line.hours)>0) warnings.push('무빈소 전환으로 이전 빈소 이용시간을 제외했습니다');
      continue;
    }
    if (line.notUsed===true) {add(line.id,label,0,'not-used','명시적 미사용');continue;}
    if (!evidence(line.proof) || line.proof.category!==line.id || line.proof.unit!==line.unit || line.proof.unitPrice!==line.unitPrice) {hold(line.id,label,'요금 근거 미확인');continue;}
    if (['room','morgue','preparation','facilityOther'].includes(line.id)) {
      if(!text(input.facilityId) || line.facilityId!==input.facilityId || line.proof.facilityId!==input.facilityId || line.proof.applicabilityConfirmed!==true) {
        hold(line.id,label,'선택 시설·현행 적용조건 확인 필요');continue;
      }
      if(line.id==='room' && (!text(input.roomId) || line.roomId!==input.roomId || line.proof.roomId!==input.roomId)) {
        hold(line.id,label,'실제 선택 호실 확인 필요: 최저가 자동대입 금지');continue;
      }
    }
    let units;
    if (line.unit==='hour' || line.unit==='day') {
      const hours=number(line.hours,'이용시간');
      if(line.unit==='hour' && line.billing==='hourly') units=hours;
      else if(line.unit==='day' && line.billing==='ceil24') units=Math.ceil(hours/24);
      else if(line.unit==='day' && line.billing==='prorata24') units=hours/24;
      else {hold(line.id,label,'시간 산정·올림 규칙 확인 필요');continue;}
      if (line.proof.billing!==line.billing) {hold(line.id,label,'출처의 시간 계산 규칙 불일치');continue;}
    } else if (line.unit==='once' || line.unit==='meal') units=number(line.quantity,'수량');
    else {hold(line.id,label,'요금 단위 미확인');continue;}
    add(line.id,label,amount(line.unitPrice,units),'priced',`${units} × ${line.unitPrice}`,line.proof.reference);
  }
  for (const id of ['room','morgue','preparation','food','cremation','burial']) if(!externalSeen.has(id)) {
    if(id==='room' && input.productId==='nobinso') add(id,'빈소',0,'not-used','무빈소');
    else hold(id,id,'필요 여부·금액 확인 필요');
  }
  const subtotal=money(rows.reduce((sum,r)=>sum+(r.amount ?? 0),0));
  return {mode:input.mode,productId:input.productId || null,subtotal,finalTotal:null,rows,pending,warnings,
    label:'확인된 항목 소계 · 미확인 비용 별도',readyForCustomer:false};
}
