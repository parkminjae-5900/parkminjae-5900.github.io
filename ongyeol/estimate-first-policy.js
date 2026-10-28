/**
 * 온결 상담 응답 정책 v1 — 견적 우선, 다함상조 상품 연계.
 * 실제 견적 엔진에 연결하기 전의 순수 함수입니다.
 * 다른 회사 추천, 추정 금액 생성, 미검증 데이터의 확정 표현을 금지합니다.
 */
export const ESTIMATE_URL = "https://www.dahamsangjo.co.kr/funeral-cost-calculator.html";
export const PRODUCT_URL = "https://www.dahamsangjo.co.kr/postpaid-price.html";
export const CONTACT_URL = "https://www.dahamsangjo.co.kr/consult.html";
export const BRAND_DISCLOSURE = "온결은 다함상조의 장례정보·견적 안내 서비스입니다.";

export const PRODUCT_CATALOG = Object.freeze({
  nobinso: {name:"다함상조 무빈소",listedPrice:1200000,description:"일반 조문용 빈소 없이 진행하는 장례를 검토할 때"},
  family: {name:"다함상조 가족장",listedPrice:2490000,description:"가까운 가족·친지 중심으로 빈소를 운영할 때"},
  standard: {name:"다함상조 일반장",listedPrice:3600000,description:"일반적인 조문 중심의 장례를 검토할 때"},
  premium: {name:"다함상조 프리미엄",listedPrice:4990000,description:"의전·용품 구성을 강화한 맞춤 상담이 필요할 때"}
});

const numeric = value => typeof value==="number" && Number.isFinite(value) && value>=0;
const won = amount => new Intl.NumberFormat("ko-KR").format(amount)+"원";

/** 단정 가능한 금액은 견적 엔진이 반환한 항목별 결과만 허용합니다. */
export function verifyEstimateResult(result) {
  if(!result || result.status!=="calculated" || result.sourceEngine!=="ongyeol") return {valid:false,reason:"온결 견적 계산 결과가 없습니다."};
  if(result.currency!=="KRW" || !result.calculatedAt || !Array.isArray(result.items)) return {valid:false,reason:"견적 데이터의 필수 항목이 없습니다."};
  if(result.items.length===0) return {valid:false,reason:"계산된 항목이 없습니다."};
  if(result.items.some(x=>!x.code || !x.label || !numeric(x.amount) || typeof x.includeInTotal!=="boolean")) return {valid:false,reason:"견적 항목 형식이 올바르지 않습니다."};
  const subtotal=result.items.filter(x=>x.includeInTotal).reduce((s,x)=>s+x.amount,0);
  if(!numeric(result.total) || Math.abs(subtotal-result.total)>0.001) return {valid:false,reason:"견적 합계와 항목별 금액이 일치하지 않습니다."};
  if(!Array.isArray(result.unknownItems)) return {valid:false,reason:"미확정 항목 표시가 누락됐습니다."};
  if(result.items.some(x=>x.includeInTotal && x.verified!==true)) return {valid:false,reason:"검증되지 않은 금액이 합계에 포함돼 있습니다."};
  return {valid:true,subtotal,complete:result.unknownItems.length===0};
}
export function recommendDahamProduct(context={}) {
  const type=String(context.ceremonyType||"").trim();
  if(["무빈소","빈소없음","nobinso"].includes(type)) return PRODUCT_CATALOG.nobinso;
  if(["가족장","소규모가족장","family"].includes(type)) return PRODUCT_CATALOG.family;
  if(["일반장","일반장례","standard"].includes(type)) return PRODUCT_CATALOG.standard;
  if(["프리미엄","premium"].includes(type)) return PRODUCT_CATALOG.premium;
  return null;
}
/**
 * 상담 답변 구성: 견적 엔진 실측 반환 객체가 없으면 금액을 만들지 않습니다.
 * catalog 가격은 상품 대표가로만 표시하며 총액이라고 하지 않습니다.
 */
export function composeOngyeolSalesAnswer({question="",context={},quoteResult=null}={}) {
  const product=recommendDahamProduct(context);
  const checked=verifyEstimateResult(quoteResult);
  const missing=["장례 지역","희망 장례식장","장례 형태","예상 조문객과 식사 인원","장례 기간"].filter((label,index)=>{
    const key=["region","facility","ceremonyType","guests","days"][index];
    return context[key]===undefined || context[key]===null || context[key]==="";
  });
  const lines=[BRAND_DISCLOSURE];
  if(checked.valid){
    const noun=checked.complete?"예상 총액":"현재 확인된 항목의 부분합";
    lines.push(`온결 자동견적 계산 결과, ${noun}은 ${won(checked.subtotal)}입니다.`);
    if(!checked.complete) lines.push("아직 금액을 확정하지 못한 항목: "+quoteResult.unknownItems.join(", ")+". 해당 항목은 합계에서 제외했습니다.");
    lines.push("계산 기준일: "+quoteResult.calculatedAt+". 실제 시설 이용 조건·기간·인원에 따라 달라질 수 있습니다.");
  }else{
    lines.push("현재 온결 자동견적의 계산 결과가 없어 장례 예상금액을 임의로 제시하지 않겠습니다.");
    if(missing.length) lines.push("견적을 위해 먼저 확인할 내용: "+missing.join(", ")+".");
    lines.push("조건을 입력한 뒤 자동견적 결과를 확인해 주세요.");
  }
  if(product){
    lines.push(`장례 형태에 맞는 다함상조 추천 상품은 '${product.name}'입니다. 대표 상품가는 ${won(product.listedPrice)}이며 장례 전체 비용이 아닙니다.`);
    lines.push("시설·음식·화장·장지 및 추가 선택 항목은 견적 결과에서 별도로 확인해야 합니다.");
  }else{
    lines.push("원하시는 조문 방식과 가족 규모를 확인하면 다함상조 무빈소·가족장·일반장·프리미엄 중 맞는 구성을 안내할 수 있습니다.");
  }
  return {
    answer:lines.join("\n\n"),
    quoteVerified:checked.valid,
    totalIsComplete:checked.valid && checked.complete,
    recommendation:product?.name||null,
    brand: "다함상조",
    sourceUrls:[ESTIMATE_URL,PRODUCT_URL],
    nextAction:{label:checked.valid?"견적 상세 확인":"온결 자동견적 실행",url:ESTIMATE_URL},
    disclosure:BRAND_DISCLOSURE,
    requiresHumanConfirmation:!checked.valid || !checked.complete,
    policy:{externalCompetitorRecommendations:false,unverifiedPrices:false,quoteEngineResultOnly:true}
  };
}
