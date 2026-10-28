/**
 * 온결 지식검색 모듈 v1
 * 기존 온결 챗봇에 연결하기 위한 API 비의존 구성요소입니다.
 * 이 모듈은 모델을 학습시키거나 실시간 시설요금을 검증하지 않습니다.
 */
export const ANSWER_BANK_URL = "/data/ongyeol-answer-bank-v1.json";
const stopwords = new Set(["에서","어떻게","무엇을","하나요","알려주세요","비용","장례","장례식장","확인","준비","경우","어떤","차이","때","및"]);
export function tokens(text) {
  return (String(text).toLowerCase().match(/[가-힣a-z0-9]+/g)||[])
    .filter(t=>t.length>=2&&!stopwords.has(t));
}
export function findAnswers(bank, question, limit=3) {
  const q=tokens(question);
  if(!q.length||!Array.isArray(bank?.entries)) return [];
  return bank.entries.map(entry=>{
    const et=new Set(tokens(entry.question));
    const overlap=q.filter(t=>et.has(t)).length;
    const union=new Set([...q,...et]).size;
    const similarity=union?overlap/union:0;
    return {entry,score:similarity};
  }).filter(hit=>hit.score>0).sort((a,b)=>b.score-a.score).slice(0,Math.max(1,limit));
}
export function composeGroundedAnswer(bank, question) {
  const matches=findAnswers(bank,question,3);
  if(!matches.length||matches[0].score<0.18) return {
    answered:false,
    answer:"현재 검증된 자료에서 정확히 일치하는 내용을 찾지 못했습니다. 지역·장례식장·기간·장례 형태를 구체적으로 알려주시면 확인 항목부터 안내하겠습니다.",
    sources:[],needs_live_confirmation:true
  };
  const top=matches[0].entry;
  return {
    answered:true,
    answer:top.model_answer,
    sources:top.source_urls,
    needs_live_confirmation:(top.live_confirmation_required||[]).length>0,
    confirm_items:top.live_confirmation_required,
    reviewed:top.review_status==="검증 완료",
    note:"자료의 일반 안내와 실제 시설 가능 여부·현재 요금은 구분해 확인해야 합니다.",
    matched_question:top.question,
    match_score:matches[0].score
  };
}
export async function loadAnswerBank(fetchImpl=fetch,url=ANSWER_BANK_URL){
  const response=await fetchImpl(url,{cache:"no-store"});
  if(!response.ok) throw new Error("답변 자료를 불러오지 못했습니다: "+response.status);
  const bank=await response.json();
  if(!Array.isArray(bank.entries)||bank.entries.length!==100) throw new Error("답변 자료 형식이 올바르지 않습니다");
  return bank;
}
