import {respond, calculateQuote} from './engine.mjs';

// 온결 원본의 상담 이벤트에서 호출할 연결 계층. 네트워크·저장소·모델 호출 없음.
// trustedQuoteProvider는 서버 코드가 설치하며 사용자 요청으로 교체하지 않는다.
export function createCounselingSession({knowledge, trustedQuoteProvider=null, clock=()=>new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Seoul'})}={}) {
 if(!knowledge||!Array.isArray(knowledge.entries))throw new Error('지식자료가 필요합니다.');
 if(trustedQuoteProvider!==null&&typeof trustedQuoteProvider!=='function')throw new Error('견적 연결 설정 오류');
 const kb=structuredClone(knowledge);
 let state={}, generation=0, queue=Promise.resolve();
 return {
  reset(){generation++;state={};},
  snapshot(){return structuredClone(state);},
  reply(question){
   const requestGeneration=generation;
   const work=async()=>{
    if(requestGeneration!==generation)throw new Error('초기화된 상담 요청');
    const today=clock();
    const response=respond(question,state,kb,today);
    // 긴급·분쟁·근거 부족일 때는 금액 계산보다 담당자 안내가 우선이다.
    if(response.quote.requested&&!response.handoff.required&&trustedQuoteProvider){
     try{
      const verified=await trustedQuoteProvider({question,state:structuredClone(response.state),today});
      if(verified){
       const calculation=calculateQuote(verified.items,{...verified.options,today});
       response.quote={...response.quote,status:calculation.complete?'verified_items_complete':'verification_required',amount:calculation.total,calculation,missing:calculation.pending.map(p=>p.reason)};
      }
     }catch{
      response.quote={...response.quote,status:'verification_required',amount:null,missing:['요금 연결 또는 검증 실패: 시설에 확인 필요']};
     }
    }
    if(requestGeneration!==generation)throw new Error('초기화된 상담 요청');
    state=structuredClone(response.state);
    return response;
   };
   const result=queue.then(work);
   queue=result.catch(()=>{});
   return result;
  }
 };
}
