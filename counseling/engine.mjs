// 외부 모델·검색 결과는 신뢰하지 않는다. 계산 입력은 별도 검증된 어댑터만 공급한다.
const dateValue = value => {
 if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value))return NaN;
 const ms=Date.parse(value+'T00:00:00Z');
 return Number.isFinite(ms)&&new Date(ms).toISOString().slice(0,10)===value?ms:NaN;
};
const fresh = (checked, until, today) => {
 try {const [a,b,c]=[checked,until,today].map(dateValue);return [a,b,c].every(Number.isFinite)&&a<=c&&c<=b;}catch{return false;}
};
const https = url => {try{return new URL(url).protocol==='https:';}catch{return false;}};
const unique = a => [...new Set(a)];
export function respond(question, previous={}, knowledge, today=new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Seoul'})) {
 if(typeof question!=='string'||!question.trim()||question.length>4000) throw new Error('질문은 1~4000자로 입력하세요.');
 const q=question.normalize('NFKC').trim();
 previous=previous&&typeof previous==='object'&&!Array.isArray(previous)?previous:{};
 // 주소는 상담 희망 지역일 뿐, 고인의 주민등록·관내 자격으로 전환하지 않는다.
 const regions=unique(q.match(/서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주|춘천|성남|수원|부천|안산|송파|영등포|강남/g)||[]);
 const state={region:regions.length?regions.join(' '):typeof previous.region==='string'&&previous.region.length<=100?previous.region:null,topics:Array.isArray(previous.topics)?previous.topics.filter(id=>knowledge.entries.some(e=>e.id===id)):[]};
 const injection=/지침.*무시|규칙.*무시|출처.*(?:빼|없이)|지어내|아무.*금액|시스템.*프롬프트/.test(q);
 const emergency=/숨.*안|호흡.*없|의식.*없|심정지/.test(q);
 const dispute=/분쟁|동의 없이|몰래|무연고|외국|해외|변사|사고사/.test(q);
 const cost=/비용|요금|시설비|화장료|사용료|안치료|입관료|관리비|얼마|가격|견적|총액|금액|계산|원\b/.test(q);
 let entries=injection||emergency?[]:knowledge.entries.filter(e=>e.terms.some(t=>q.includes(t)));
 const followup=/^(그럼|그러면|거기|그곳|그건|그것|아까|네|예|얼마|비용)/.test(q);
 if(!injection&&!emergency&&followup&&!/무빈소|가족장|일반장/.test(q))entries.push(...knowledge.entries.filter(e=>state.topics.includes(e.id)));
 entries=unique(entries);
 const hasSpecific=entries.some(e=>!/^q\d+$/.test(e.id)&&e.id!=='family');
 entries.sort((a,b)=>(hasSpecific?Number(/^q\d+$/.test(a.id))-Number(/^q\d+$/.test(b.id)):0));
 entries=entries.slice(0,6);
 const stale=entries.filter(e=>!fresh(e.checkedAt,e.reviewBy,today));
 entries=entries.filter(e=>e.status==='verified'&&fresh(e.checkedAt,e.reviewBy,today)&&Array.isArray(e.sourceIds)&&e.sourceIds.length>0&&e.sourceIds.every(id=>knowledge.sources[id]&&https(knowledge.sources[id].url)&&fresh(knowledge.sources[id].checkedAt,e.reviewBy,today)));
 state.topics=entries.map(e=>e.id);
 const handoff=emergency||dispute||injection||!entries.length||entries.some(e=>e.id==='human');
 const missing=unique(entries.flatMap(e=>e.needs));
 if(cost)missing.push('현행 시설 요금표·단위·유효기간·포함 항목 확인');
 if(!state.region)missing.push('상담 희망 지역');
 let notice=emergency?'사망 여부를 스스로 판단하지 말고 즉시 119에 연락하여 지시를 따르세요.':injection?'근거 없는 금액이나 출처를 만들어 답할 수 없습니다.':!entries.length?'검증된 답변을 찾지 못했습니다. 질문을 구체화하거나 상담원에게 확인해 주세요.':'일반 안내이며 개별 시설 자격·예약·총액 확정은 별도 확인이 필요합니다.';
 if(stale.length)notice+=' 검토기한이 지난 자료는 답변에서 제외했습니다.';
 return {mode:'verified-retrieval',generative:false,state,notice,answers:entries.map(e=>({id:e.id,text:e.answer,checkedAt:e.checkedAt,exceptions:e.exceptions,needs:e.needs,sources:e.sourceIds.map(id=>({id,...knowledge.sources[id]}))})),needs:unique(missing),handoff:{required:handoff,reason:emergency?'응급상황':dispute?'예외·분쟁·해외 전문 확인':injection?'근거 우회 요청':!entries.length?'근거 부족':handoff?'사용자 요청':null,contact:emergency?'119':handoff?'1600-6131':null,connected:false},quote:{requested:cost,status:cost?'verification_required':'not_requested',amount:null,region:state.region,eligibility:'unknown',missing:cost?['시설 고유 식별자','이용일','공식 요금 및 과금 단위','감면·관내 자격','포함·별도 항목']:[]}};
}

// 금액은 원 단위 정수. quantity는 확정된 청구 단위 수이며 시간→일 자동환산 금지.
// requiredIds는 UI/서버가 선택한 필수 비용 항목 집합. 모델이 정하지 않는다.
export function calculateQuote(items, {facilityId,serviceDate,eligibility,requiredIds,today}={}) {
 if(!Array.isArray(items)||!Array.isArray(requiredIds)||!requiredIds.length||requiredIds.some(id=>typeof id!=='string'||!id.trim())||new Set(requiredIds).size!==requiredIds.length||typeof facilityId!=='string'||!facilityId.trim()||!Number.isFinite(dateValue(serviceDate))||!Number.isFinite(dateValue(today)))throw new Error('견적 조건 누락');
 const seen=new Set(), accepted=[], pending=[];let subtotal=0;
 for(const item of items){
  if(!item||typeof item.id!=='string'||!item.id.trim()||seen.has(item.id))throw new Error('중복 또는 잘못된 항목');seen.add(item.id);
  const unknown=reason=>pending.push({id:item.id,reason});
  if(item.status==='not_applicable'&&item.confirmed===true){accepted.push({id:item.id,amount:0,reason:'미이용 확인'});continue;}
  if(item.includedIn){unknown('포함 항목은 계약 확인 후 중복 제거 필요');continue;}
  if(item.status!=='verified'||item.sourceGrade!=='official'||!https(item.sourceUrl)||item.facilityId!==facilityId){unknown('공식 출처 또는 시설 식별 불일치');continue;}
  if(!fresh(item.checkedAt,item.reviewBy,today)||!fresh(item.effectiveFrom,item.effectiveUntil,serviceDate)){unknown('확인일·요금 적용기간 미확인 또는 만료');continue;}
  if(item.eligibilityRequired&&(typeof item.category!=='string'||!item.category.trim()||!eligibility||eligibility.verified!==true||eligibility.facilityId!==facilityId||eligibility.category!==item.category||!https(eligibility.sourceUrl)||!fresh(eligibility.checkedAt,eligibility.validUntil,today)||!fresh(eligibility.checkedAt,eligibility.validUntil,serviceDate))){unknown('자격 미확인');continue;}
  if(!['hour','day','person','each','fixed'].includes(item.unit)||item.billingRuleConfirmed!==true){unknown('과금 규칙 미확인');continue;}
  if(!Number.isSafeInteger(item.unitPrice)||item.unitPrice<0||!Number.isSafeInteger(item.quantity)||item.quantity<0||item.quantity===0&&item.zeroConfirmed!==true)throw new Error('금액·수량은 확인된 0 이상의 안전한 정수여야 합니다.');
  const amount=item.unitPrice*item.quantity;if(!Number.isSafeInteger(amount)||!Number.isSafeInteger(subtotal+amount))throw new Error('계산 범위 초과');
  subtotal+=amount;accepted.push({id:item.id,amount,sourceUrl:item.sourceUrl,checkedAt:item.checkedAt});
 }
 for(const id of requiredIds)if(!seen.has(id))pending.push({id,reason:'필수 항목 미확인'});
 return {subtotal,total:pending.length?null:subtotal,complete:!pending.length,accepted,pending,currency:'KRW'};
}

// 생성 모델을 붙일 경우 자유문장을 그대로 노출하지 않는다. 승인된 카드 선택만 허용한다.
export function validateCandidate(candidate, response) {
 // 추가 필드까지 대조해 미승인 문장·상태가 표시되지 않게 한다.
 try {
  if(!candidate||typeof candidate!=='object'||!Array.isArray(candidate.answers))return ['답변 구조 오류'];
  const normalize=value=>Array.isArray(value)?value.map(normalize):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(key=>[key,normalize(value[key])])):value;
  return JSON.stringify(normalize(candidate))===JSON.stringify(normalize(response))?[]:['미승인 답변·출처·상태·전환·계산 변경'];
 }catch{return ['답변 구조 오류'];}
}
