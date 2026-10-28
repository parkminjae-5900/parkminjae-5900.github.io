/**
 * 온결 전문가 상담 연결 — 검증된 다함상조 공개 프로필 정보 사용
 * 기존 챗봇에서 onUnanswered / onComplexQuestion 호출 시 연결하기 위한 모듈.
 * 사용 예: const h = installHumanHandoff(); h.show();
 */
export const HUMAN_CONTACT = Object.freeze({
  name:"장례지도사 박민재",
  title:"다함상조 대표 장례지도사 · 현장 경력 24년",
  photo:"https://www.dahamsangjo.co.kr/staff/assets/photos/01.jpg",
  phone:"tel:16006131",
  phoneText:"1600-6131",
  kakao:"https://open.kakao.com/o/sz9RE1xi",
  profile:"https://www.dahamsangjo.co.kr/park-minjae.html"
});
const COMPLEX_TERMS=["해외 사망","국제 운구","시신 해외이송","엠바밍","분쟁","소송","상속 분쟁","부검","경찰 조사","감염병 장례","무연고","시신 인도 거부"];
export function requiresSpecialist({question="",answered=true,confidence=1,failedAttempts=0,quoteConflict=false}={}) {
  if(quoteConflict) return true;
  if(COMPLEX_TERMS.some(term=>String(question).includes(term))) return true;
  if(!answered && failedAttempts>=1) return true;
  if(confidence<0.2 && failedAttempts>=2) return true;
  return false;
}
export function installHumanHandoff(root=document.body) {
  if(!root || typeof document==="undefined") throw new Error("브라우저 환경이 필요합니다");
  const existing=document.getElementById("ongyeol-human-handoff-dialog");
  if(existing) return {show:()=>existing.showModal(),hide:()=>existing.close(),element:existing};
  const style=document.createElement("style");
  style.textContent=`
  #ongyeol-human-handoff-dialog{border:0;border-radius:20px;padding:0;max-width:min(92vw,440px);width:100%;box-shadow:0 20px 80px #0004;color:#211914;font:17px/1.6 "Malgun Gothic","Noto Sans KR",sans-serif}
  #ongyeol-human-handoff-dialog::backdrop{background:rgba(20,16,12,.65)}
  .ongyeol-handoff-inner{padding:26px 22px;text-align:center;background:#fffaf1}
  .ongyeol-handoff-photo{width:124px;height:156px;object-fit:cover;border-radius:15px;border:2px solid #e4d2aa;display:block;margin:0 auto 15px}
  .ongyeol-handoff-title{font-size:23px;font-weight:900;margin:0}
  .ongyeol-handoff-desc{margin:10px 0 18px;color:#65584a}
  .ongyeol-handoff-actions{display:grid;grid-template-columns:1fr 1fr;gap:10px}
  .ongyeol-handoff-actions a{min-height:52px;display:flex;align-items:center;justify-content:center;border-radius:12px;text-decoration:none;font-weight:900;color:#fff;background:#211914}
  .ongyeol-handoff-actions a:first-child{background:#a8750e}
  .ongyeol-handoff-close{border:1px solid #c5b493;background:white;border-radius:10px;min-height:44px;padding:8px 20px;margin-top:15px;cursor:pointer;font:inherit}
  .ongyeol-handoff-foot{font-size:13px;color:#75695e;margin-top:12px}
  @media(max-width:350px){.ongyeol-handoff-actions{grid-template-columns:1fr}}
  `;
  root.append(style);
  const dlg=document.createElement("dialog");dlg.id="ongyeol-human-handoff-dialog";dlg.setAttribute("aria-labelledby","ongyeol-handoff-heading");
  const inner=document.createElement("div");inner.className="ongyeol-handoff-inner";
  const img=document.createElement("img");img.className="ongyeol-handoff-photo";img.src=HUMAN_CONTACT.photo;img.alt="장례지도사 박민재 공식 프로필 사진";img.loading="lazy";inner.append(img);
  const title=document.createElement("h2");title.className="ongyeol-handoff-title";title.id="ongyeol-handoff-heading";title.textContent="장례지도사 박민재";inner.append(title);
  const role=document.createElement("p");role.className="ongyeol-handoff-desc";role.textContent="보다 정확한 상담이 필요한 내용입니다. 장례지도사 박민재에게 문의 부탁드립니다.";inner.append(role);
  const actions=document.createElement("div");actions.className="ongyeol-handoff-actions";
  const phone=document.createElement("a");phone.href=HUMAN_CONTACT.phone;phone.textContent="전화 상담 "+HUMAN_CONTACT.phoneText;actions.append(phone);
  const kakao=document.createElement("a");kakao.href=HUMAN_CONTACT.kakao;kakao.target="_blank";kakao.rel="noopener noreferrer";kakao.textContent="카카오톡 상담";actions.append(kakao);
  inner.append(actions);
  const close=document.createElement("button");close.type="button";close.className="ongyeol-handoff-close";close.textContent="닫기";close.addEventListener("click",()=>dlg.close());inner.append(close);
  const foot=document.createElement("p");foot.className="ongyeol-handoff-foot";foot.textContent="상담 전 개인정보·민감한 서류를 공개 채팅에 올리지 마세요.";inner.append(foot);
  dlg.append(inner);root.append(dlg);
  return {show:()=>{if(!dlg.open)dlg.showModal();},hide:()=>dlg.close(),element:dlg};
}
