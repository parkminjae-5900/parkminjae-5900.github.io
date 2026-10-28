import {requiresSpecialist,installHumanHandoff} from "./human-handoff.js";
import {answerWithOngyeol} from "./answer-retriever.js";

/**
 * 실제 온결 채팅 UI에서 호출할 연결 어댑터.
 * 사용자의 질문 이벤트에서 호출하면 필요한 경우 전문가 팝업을 자동 표시합니다.
 */
export function respondWithHandoff({bank,question,context={},quoteResult=null,failedAttempts=0,confidence=1,quoteConflict=false}={}) {
  const result=answerWithOngyeol({bank,question,context,quoteResult});
  const shouldShow=requiresSpecialist({
    question,
    answered:result.knowledgeReviewed || result.quoteVerified,
    failedAttempts,confidence,quoteConflict
  });
  if(shouldShow && typeof document!=="undefined") installHumanHandoff().show();
  return {...result,handoffRequired:shouldShow,handoffMessage:shouldShow?"장례지도사 박민재에게 문의 부탁드립니다.":null};
}
