import fs from 'node:fs';
import {calculateQuote} from './engine.mjs';

// 저장소 수집 자료를 검증 완료 요금으로 자동 승격하지 않는다.
// 시행·종료일, 과금 규칙, 시설 식별은 실제 자료에 있는 값만 전달한다.
export function auditRecord(record, price, today) {
 const item={id:'audited-item',facilityId:record.facilityId,status:'verified',sourceGrade:record.sourceGrade==='A'?'official':record.sourceGrade,sourceUrl:record.sourceUrl,checkedAt:record.verifiedAt?.slice(0,10),reviewBy:record.reviewBy,effectiveFrom:record.effectiveFrom,effectiveUntil:record.effectiveUntil,unitPrice:price.amount,quantity:1,unit:({'1시간':'hour','1일':'day','24시간':'day','1회':'each'})[price.unit],billingRuleConfirmed:record.billingRuleConfirmed};
 const absent=['facilityId','reviewBy','effectiveFrom','effectiveUntil'].filter(key=>!record[key]);
 if(record.billingRuleConfirmed!==true)absent.push('billingRuleConfirmed');
 if(absent.length)return {eligible:false,reasons:absent};
 try{const quote=calculateQuote([item],{facilityId:record.facilityId,today,serviceDate:today,requiredIds:['audited-item']});return {eligible:quote.complete,reasons:quote.pending.map(p=>p.reason)};}catch{return {eligible:false,reasons:['검증 입력 오류']};}
}
export function auditDataset(halls,cremation,today) {
 const outcomes=[];
 for(const facility of halls.items||[])for(const price of facility.prices||[]){outcomes.push({facility:facility.facilityName,...auditRecord(facility,price,today)});}
 // 2023년 참고자료를 현행 자격·요금으로 승격하지 않는다.
 const historical=(cremation.facilities||[]).reduce((n,f)=>n+(f.prices||[]).length,0);
 return {checkedAt:today,scope:'저장소 가격자료의 상담 자동계산 연결 적격성; 공식 요금의 실제 진위 검수 아님',hallFacilities:(halls.items||[]).length,hallPriceItems:outcomes.length,eligibleHallItems:outcomes.filter(r=>r.eligible).length,blockedHallItems:outcomes.filter(r=>!r.eligible).length,missingFields:[...new Set(outcomes.flatMap(r=>r.reasons))],cremationSourceDate:cremation.sourceDate,cremationFacilities:(cremation.facilities||[]).length,historicalCremationItemsBlocked:historical,readyForProduction:false};
}
if(process.argv.includes('--write')){
 const halls=JSON.parse(fs.readFileSync(new URL('../data/funeral-hall-prices.json',import.meta.url)));
 const cremation=JSON.parse(fs.readFileSync(new URL('../data/cremation-prices.json',import.meta.url)));
 const today=new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Seoul'});
 const report=auditDataset(halls,cremation,today);
 fs.writeFileSync(new URL('./price-readiness-report.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify(report,null,2));
}
