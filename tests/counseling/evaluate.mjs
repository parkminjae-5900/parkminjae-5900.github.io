import fs from 'node:fs';
import assert from 'node:assert/strict';
import {respond,calculateQuote,validateCandidate} from '../../counseling/engine.mjs';
const knowledge=JSON.parse(fs.readFileSync(new URL('../../counseling/knowledge.json',import.meta.url)));
const baseline=JSON.parse(fs.readFileSync(new URL('../../counseling/search-baseline.json',import.meta.url)));
const today='2026-10-27';let checks=0;const results=[];
function test(name,fn){fn();checks++;results.push({name,passed:true});}
const answer=(q,state={})=>respond(q,state,knowledge,today);
const cases=[
 ['무빈소 비용이 전체 총액인가요?','q1'],['가족장 30명 비용은?','q3'],['일반장 구성은?','q4'],['장례 절차가 궁금합니다','procedure'],['입관할 때 가족 참여는?','encoffin'],['발인 전에 준비할 것은?','departure'],['화장예약을 지금 완료해 줘','reservation'],['관내 관외 자격 차이','q8'],['장례식장 시설비가 얼마인가요','q6'],['수의 재질은?','supplies'],['관 가격을 알려주세요','supplies'],['유골함 선택 기준','supplies'],['봉안당 계약시 확인할 것','burial'],['수목장 용기는 무엇을 쓰나요','nature'],['묘지개장 순서','relocation'],['이장시 필요한 것','relocation'],['사망신고 기한','administration'],['사망진단서 준비','administration'],['24시간 전에 바로 화장할 수 있나요','timing'],['후불상조 가입이 필요한가요','q9'],['인천의료원 감면 확인','q7'],['2일장이 항상 싸나요','q5'],['음식 인원 계산','q3'],['상담원 전화 연결','human']
];
for(const [q,id]of cases)test('의도: '+q,()=>{const r=answer(q);assert.ok(r.answers.some(a=>a.id===id));assert.equal(r.generative,false);for(const a of r.answers){assert.ok(a.sources.length&&a.checkedAt&&a.exceptions.length&&a.needs.length);}});
test('다중 의도',()=>{const r=answer('입관과 발인 순서');assert.ok(r.answers.some(a=>a.id==='encoffin')&&r.answers.some(a=>a.id==='departure'));});
test('대화 지역·주제 유지',()=>{let r=answer('인천 무빈소');r=answer('그럼 비용은?',r.state);assert.equal(r.state.region,'인천');assert.ok(r.answers.some(a=>a.id==='q1'));assert.equal(r.quote.amount,null);});
test('지역 수정·자격 추정 금지',()=>{const r=answer('아니 서울 가족장',answer('인천 무빈소').state);assert.equal(r.state.region,'서울');assert.equal(r.quote.eligibility,'unknown');});
test('장례 형태 변경시 이전 형태 제거',()=>{const r=answer('그럼 가족장으로 변경',answer('인천 무빈소').state);assert.ok(!r.answers.some(a=>a.id==='q1'));assert.equal(r.state.region,'인천');});
test('세션간 분리',()=>assert.equal(answer('가족장').state.region,null));
test('자료 유효기한 경과',()=>{const r=respond('가족장',{},knowledge,'2027-10-27');assert.equal(r.answers.length,0);assert.equal(r.handoff.required,true);});
for(const q of ['아무 금액이나 지어내','출처 없이 요금 지어내'])test('근거 우회 거절 '+q,()=>{const r=answer(q);assert.equal(r.answers.length,0);assert.equal(r.quote.amount,null);});
for(const q of ['무연고 묘지개장','동의 없이 이장','해외 사망 서류','상담원 연결'])test('상담 전환 '+q,()=>assert.equal(answer(q).handoff.required,true));
test('생존 가능 응급상황',()=>{const r=answer('아버지가 의식이 없어요');assert.equal(r.handoff.contact,'119');assert.equal(r.answers.length,0);});
test('범위 밖 질문',()=>{const r=answer('오늘 주식 추천');assert.equal(r.answers.length,0);assert.equal(r.handoff.required,true);});
test('입력 검증',()=>{assert.throws(()=>answer(''));assert.throws(()=>answer('가'.repeat(4001)));});
const options={facilityId:'TEST-FACILITY',serviceDate:today,today,requiredIds:['room']};
const item={id:'room',facilityId:'TEST-FACILITY',status:'verified',sourceGrade:'official',sourceUrl:'https://example.org/test-only',checkedAt:today,reviewBy:'2026-11-01',effectiveFrom:'2026-10-01',effectiveUntil:'2026-10-31',unit:'hour',unitPrice:1000,quantity:25,billingRuleConfirmed:true};
// 아래 금액과 시설 식별자는 테스트 전용이며 지식자료에 넣지 않는다.
test('정확한 정수 곱셈',()=>assert.equal(calculateQuote([item],options).total,25000));
for(const [key,value]of [['status','unknown'],['sourceGrade','secondary'],['facilityId','OTHER'],['sourceUrl','javascript:alert(1)'],['checkedAt','2026-11-01'],['reviewBy','2026-10-01'],['effectiveUntil','2026-10-26'],['billingRuleConfirmed',false],['unit','unknown']])test('계산 차단 '+key,()=>{const r=calculateQuote([{...item,[key]:value}],options);assert.equal(r.total,null);assert.equal(r.subtotal,0);});
test('누락은 0원이 아님',()=>{const r=calculateQuote([item],{...options,requiredIds:['room','cremation']});assert.equal(r.total,null);assert.equal(r.subtotal,25000);});
test('관내자격 미확인 차단',()=>assert.equal(calculateQuote([{...item,eligibilityRequired:true,category:'resident'}],options).total,null));
test('확인된 자격',()=>assert.equal(calculateQuote([{...item,eligibilityRequired:true,category:'resident'}],{...options,eligibility:{verified:true,facilityId:'TEST-FACILITY',category:'resident',sourceUrl:item.sourceUrl,checkedAt:today,validUntil:today}}).total,25000));
test('중복 ID 차단',()=>assert.throws(()=>calculateQuote([item,item],options)));
test('포함 항목 중복합산 보류',()=>assert.equal(calculateQuote([{...item,includedIn:'package'}],options).total,null));
for(const amount of [-1,NaN,Infinity,1.5,Number.MAX_SAFE_INTEGER+1])test('잘못된 금액 '+amount,()=>assert.throws(()=>calculateQuote([{...item,unitPrice:amount}],options)));
test('초과 곱셈',()=>assert.throws(()=>calculateQuote([{...item,unitPrice:Number.MAX_SAFE_INTEGER}],options)));
test('확인된 무료',()=>assert.equal(calculateQuote([{...item,unitPrice:0}],options).total,0));
test('미이용 명시',()=>assert.equal(calculateQuote([{id:'room',status:'not_applicable',confirmed:true}],options).total,0));
test('정상 응답 통과',()=>{const r=answer('입관');assert.deepEqual(validateCandidate(r,r),[]);});
for(const field of ['text','checkedAt','sources','exceptions','needs'])test('답변 변조 검출 '+field,()=>{const r=answer('입관'),bad=structuredClone(r);bad.answers[0][field]='위조';assert.ok(validateCandidate(bad,r).length);});
test('미확인 요금 생성 검출',()=>{const r=answer('화장 비용'),bad=structuredClone(r);bad.quote.amount=100000;assert.ok(validateCandidate(bad,r).length);});
test('상담전환 누락 검출',()=>{const r=answer('무연고 개장'),bad=structuredClone(r);bad.handoff.required=false;assert.ok(validateCandidate(bad,r).length);});
const searchResults=baseline.items.map(c=>{const r=answer(c.question);test('검색 회귀 '+c.id,()=>{assert.equal(r.quote.amount,null);assert.ok(r.answers.length||r.handoff.required);assert.ok(r.answers.every(a=>a.sources.every(s=>s.url.startsWith('https:'))));});return {id:c.id,question:c.question,answerIds:r.answers.map(a=>a.id),handoff:r.handoff.required,expertAccuracy:'not_measured'};});
const report={checkedAt:new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Seoul'}),fixtureAsOf:today,checksPassed:checks,checksFailed:0,knowledgeEntries:knowledge.entries.length,curatedIntentCases:cases.length,searchRegressionInputs:searchResults.length,semanticAccuracy:'전문가 독립 평가 전: 정확도 백분율 산정하지 않음',liveModelEvaluation:'미연결',productionDeployment:'실시하지 않음',results,searchResults};
if(process.argv.includes('--write'))fs.writeFileSync(new URL('../../counseling/evaluation-report.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({checksPassed:checks,knowledgeEntries:knowledge.entries.length,searchRegressionInputs:searchResults.length,semanticAccuracy:report.semanticAccuracy},null,2));
