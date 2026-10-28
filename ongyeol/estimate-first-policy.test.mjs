// node --test ongyeol/estimate-first-policy.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import {verifyEstimateResult,recommendDahamProduct,composeOngyeolSalesAnswer} from "./estimate-first-policy.js";

const good={status:"calculated",sourceEngine:"ongyeol",currency:"KRW",calculatedAt:"2026-10-28",items:[
  {code:"service",label:"다함상조 상품비",amount:1200000,includeInTotal:true,verified:true},
  {code:"facility",label:"확인된 시설 이용료",amount:80000,includeInTotal:true,verified:true}
],total:1280000,unknownItems:["화장료","장지비"]};

test("실제 견적 결과가 없으면 총액을 만들지 않는다",()=>{
 const r=composeOngyeolSalesAnswer({context:{ceremonyType:"무빈소"}});
 assert.equal(r.quoteVerified,false);
 assert.match(r.answer,/임의로 제시하지 않겠습니다/);
 assert.equal(r.recommendation,"다함상조 무빈소");
 assert.doesNotMatch(r.answer,/경쟁사 추천/);
});
test("검증된 부분합만 표시하고 미확정 항목은 제외한다",()=>{
 const r=composeOngyeolSalesAnswer({context:{ceremonyType:"무빈소"},quoteResult:good});
 assert.equal(r.quoteVerified,true);
 assert.equal(r.totalIsComplete,false);
 assert.match(r.answer,/1,280,000원/);
 assert.match(r.answer,/화장료, 장지비/);
 assert.match(r.answer,/부분합/);
});
test("합계 불일치·미검증 금액을 거부한다",()=>{
 assert.equal(verifyEstimateResult({...good,total:1}).valid,false);
 assert.equal(verifyEstimateResult({...good,items:[{...good.items[0],verified:false},good.items[1]]}).valid,false);
});
test("모르는 장례 형태에서 임의로 상품을 지정하지 않는다",()=>{
 assert.equal(recommendDahamProduct({ceremonyType:"확인 전"}),null);
});
test("외부 경쟁업체 추천 대신 브랜드 관계를 공개한다",()=>{
 const r=composeOngyeolSalesAnswer({context:{ceremonyType:"가족장"}});
 assert.match(r.answer,/온결은 다함상조의/);
 assert.equal(r.policy.externalCompetitorRecommendations,false);
});
