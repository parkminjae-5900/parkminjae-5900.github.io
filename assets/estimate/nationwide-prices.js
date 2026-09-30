/* Facility-linked estimates. Public sources are reference prices, never guarantees. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const safe = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const norm = s => String(s||"").replace(/[^가-힣a-zA-Z0-9]/g,"").toLowerCase();
  const money = v => Math.round(v).toLocaleString("ko-KR")+"원";
  const number = v => Number.isFinite(Number(v)) ? Math.max(0,Number(v)) : 0;
  let facilityRecords=[], catalog=null, latest=null, crem=null, rows=[], selectedName=null, selectedCrem=null;
  let loading=true, failed=false, manualHall=false, manualCrem=false;
  const selectedRows=()=>rows.filter((r,i)=>$("facility-row-"+i)?.checked);
  function group(r){const t=r.category||"";if(/빈소|접객|분향/.test(t))return "room";if(/안치/.test(t))return "morgue";if(/입관|염습/.test(t))return "preparation";return t;}
  function qtyFor(r) {
    const t=(r.unit||"")+" "+(r.detail||"");
    if(/1일|일당|24시간/.test(t))return {qty:number($("facility-days").value),unit:"일"};
    if(/1시간|시간당/.test(t))return {qty:number($("facility-hours").value),unit:"시간"};
    if(/1회|회당/.test(t))return {qty:1,unit:"회"};
    return {qty:1,unit:"단위 확인 필요"};
  }
  function hallLines() {
    if(manualHall) return [["장례식장 직접 입력 · "+(selectedName||txt("region2")||"미정"),number($("hallCost").value)]];
    return selectedRows().map(r => {
      const i=rows.indexOf(r), q=number($("facility-qty-"+i).value);
      return [r.label+" · "+money(r.amount)+" × "+q+" "+$("facility-unit-"+i).value,Math.round(r.amount*q)];
    });
  }
  function sourceText() {
    const h=(manualHall?[]:selectedRows()).map(r=>r.sourceName+" / 자료 기준 "+r.sourceDate+" / 조회 "+(r.verifiedAt||"미확인"));
    if(manualHall)h.push("장례식장 직접 입력: "+$("hall-manual-source").value);
    if(state.burialType!=="매장"&&selectedCrem&&!manualCrem)h.push(selectedCrem.name+" / "+crem.sourceName+" / 자료 기준 "+crem.sourceDate+" / "+$("crem-rate").selectedOptions[0]?.textContent);
    if(state.burialType!=="매장"&&manualCrem)h.push("화장료 직접 입력: "+$("crem-manual-source").value);
    return [...new Set(h)].join("\n");
  }
  function warnings() {
    const w=[];
    if(!state.funeralType)w.push("장례형태 미선택");
    if(!state.burialType||state.burialType==="미정")w.push("화장·매장 방식 미확정");
    if(!manualHall&&selectedRows().filter(r=>group(r)==="room").length>1)w.push("복수 빈소 선택: 이용 기간 중복 여부 확인");
    if(loading)w.push("전국 요금자료를 불러오는 중입니다.");
    if(failed)w.push("일부 요금자료 연결 실패. 직접 입력 또는 시설 확인이 필요합니다.");
    if(!selectedName&&!txt("region2"))w.push("장례식장 미정");
    if(!manualHall&&!selectedRows().length)w.push("시설 요금 미선택: 빈소·안치·입관 등 필요한 항목 확인");
    if(!manualHall&&selectedRows().some(r=>r.sourceGrade==="A"))w.push("공식 홈페이지 게시 요금: 시행일·과금 단위·추가 비용 확인 필요");
    if(!manualHall&&selectedRows().some(r=>r.sourceGrade!=="A"))w.push("2023년 공시 또는 2차 자료: 현재 시설 요금 재확인 필요");
    if(!manualHall&&selectedRows().some(r=>qtyFor(r).unit==="단위 확인 필요"))w.push("원문에 없는 과금 단위: 시설 확인 후 수량·단위 입력");
    if(manualHall&&!number($("hallCost").value))w.push("장례식장 직접 입력 금액 미확인: 빈 값·0원은 무료 확정 아님");
    if(manualHall&&!$("hall-manual-source").value.trim())w.push("장례식장 직접 입력 요금의 확인 근거 미입력");
    if(state.burialType!=="매장") {
      if(!manualCrem&&!$("crem-rate").value)w.push("화장시설·적용요금 미선택");
      if(!manualCrem&&$("crem-rate").value)w.push("화장료는 2023년 참고값: 현재 요금과 거주기간·감면 자격 확인 필요");
      if(!$("crem-residence").value.trim())w.push("고인의 거주지·거주기간 미입력");
      if(!$("crem-qualified").checked)w.push("고인의 거주지·거주기간·감면 증빙 확인 필요");
      if(manualCrem&&!number($("cremationCost").value))w.push("직접 입력 화장료 미확인: 빈 값·0원은 무료 확정 아님");
      if(manualCrem&&!$("crem-manual-source").value.trim())w.push("화장료 직접 입력 근거 미입력");
    }
    if(state.funeralType!=="무빈소"&&!$("food-not-used").checked&&!number($("foodCost").value))w.push("음식·접객비 미입력");
    if(!$("burial-not-used").checked&&!number($("burialCost").value))w.push("장지·봉안·자연장 비용 미입력");
    for(const k of ["shroud","coffin","urn"].filter(k=>k!=="urn"||state.burialType!=="매장"))if(!state[k]||state[k+"Price"]===0)w.push(({shroud:"수의",coffin:"관",urn:"유골함"})[k]+" 선택가 미확인: 0원 확정 아님");
    if(!$("extra-reviewed").checked)w.push("제단·영정·이송·거리·추가 주문 검토 필요");
    return [...new Set(w)];
  }
  function updateHall(force=false) {
    const n=txt("hallSelect");
    if(n===selectedName&&!force)return;
    const keepManual=manualHall&&n===selectedName;
    if(n!==selectedName)$("hall-manual-source").value="";
    selectedName=n;if(!keepManual){manualHall=false;$("hall-manual").checked=false;$("hallCost").value="";}
    const matches=facilityRecords.filter(f=>norm(f.fcltNm)===norm(n));
    const street=a=>norm(String(a||"").split("(")[0]);
    const actual=(latest?.items||[]).filter(i=>norm(i.facilityName)===norm(n)&&matches.length===1&&street(i.address)===street(matches[0].addr));
    const sharedUrl=actual.length===1&&(latest?.items||[]).filter(i=>i.sourceUrl===actual[0].sourceUrl&&norm(i.facilityName)!==norm(n)).length>0;
    const oldNames=Object.keys(catalog?.halls||{}).filter(k=>norm(k)===norm(n));
    rows=[];
    // Duplicate names remain unresolved rather than silently combining different facilities.
    if(actual.length===1&&!sharedUrl)rows=actual[0].prices.filter(r=>(r.category!=="염습/입관"||/입관실/.test(r.label))&&(r.label.match(/\d{1,3}(?:,\d{3})+\s*원/g)||[]).length<2).map(r=>({...r,sourceGrade:actual[0].sourceGrade,sourceName:actual[0].sourceName,sourceDate:"시행일 확인 필요",verifiedAt:actual[0].verifiedAt,sourceUrl:actual[0].sourceUrl}));
    if(oldNames.length===1&&matches.length===1){
      const categories=new Set(rows.map(group));
      for(const r of catalog.halls[oldNames[0]])if(!categories.has(group(r)))rows.push({...r,sourceGrade:"C",sourceName:catalog.sourceName,sourceDate:catalog.sourceDate,sourceUrl:catalog.sourceUrl});
    }
    $("facility-prices").innerHTML=rows.length?rows.map((r,i)=>{
      const q=qtyFor(r);
      return '<div class="facility-price"><label><input type="checkbox" id="facility-row-'+i+'"> <strong>'+safe(r.category+' · '+r.label)+'</strong><br>'+safe(r.detail||r.unit||"과금 단위 확인 필요")+' · '+money(r.amount)+'</label><p>'+safe(r.sourceName)+' · '+safe(r.sourceDate)+' · 조회 '+safe(r.verifiedAt||"현재 미확인")+' <a href="'+safe(/^https?:\/\//.test(r.sourceUrl||"")?r.sourceUrl:"#")+'" target="_blank" rel="noopener">원문</a></p><div class="formGrid"><div class="field"><label for="facility-qty-'+i+'">사용 수량</label><input id="facility-qty-'+i+'" type="number" min="0" step="0.5" value="'+q.qty+'"></div><div class="field"><label for="facility-unit-'+i+'">과금 단위</label><input id="facility-unit-'+i+'" value="'+q.unit+'"></div></div></div>';
    }).join(""):'<p>해당 시설의 정확한 가격 연결이 없습니다. 시설에 확인한 금액을 직접 입력해주세요.</p>';
    $("facility-prices").querySelectorAll("input").forEach(e=>e.addEventListener("input",()=>{if(!manualHall)$("hallCost").value=hallLines().reduce((s,r)=>s+r[1],0);recalc();}));
    $("hallCost").readOnly=!manualHall;
    recalc();
  }
  function updateCrem() {
    selectedCrem=crem?.facilities.find(f=>f.name===$("crem-facility").value)||null;
    $("cremationCost").value="";$("crem-manual-source").value="";manualCrem=false;$("crem-manual").checked=false;$("crem-qualified").checked=false;
    $("crem-rate").innerHTML='<option value="">고인의 조건에 맞는 요금 선택</option>'+(selectedCrem?.prices||[]).map((r,i)=>'<option value="'+i+'">'+safe(r.category+" · "+r.label+" · "+r.detail)+" · "+money(r.amount)+'</option>').join("");
    $("crem-address").textContent=selectedCrem?[selectedCrem.address,selectedCrem.phone,"시설정보·요금 자료 기준: "+crem.sourceDate].filter(Boolean).join(" · "):"";
    $("cremationCost").readOnly=true;recalc();
  }
  const originalCalc=calcData, originalRecalc=recalc, originalSummary=summaryText;
  calcData=function() {
    const d=originalCalc();
    if(state.burialType==="매장"){d.serviceItems=d.serviceItems.filter(r=>!r[0].startsWith("유골함"));d.service=d.serviceItems.reduce((s,r)=>s+r[1],0);}
    d.externalItems=d.externalItems.filter(r=>r[0]!=="장례식장·안치·시설비"&&r[0]!=="화장시설 이용료");
    d.externalItems.push(...hallLines().filter(r=>r[1]>0));
    if(number($("hallEtc").value)>0)d.externalItems.push(["기타 시설비",number($("hallEtc").value)]);
    if(state.burialType!=="매장"&&number($("cremationCost").value)>0)d.externalItems.push(["화장료 · "+(selectedCrem?.name||"직접 입력"),number($("cremationCost").value)]);
    d.external=d.externalItems.reduce((s,r)=>s+r[1],0);d.total=d.service+d.external;return d;
  };
  recalc=function() {
    originalRecalc();
    const w=warnings();
    $("estimate-readiness").textContent=w.length?"입력된 항목 소계 · 미확인 비용 "+w.length+"건":"입력 항목 기준 예상금액 · 최종 시설 확인 필요";
    $("estimate-pending").innerHTML='<strong>추가 확인사항</strong><ul>'+w.map(v=>'<li>'+safe(v)+'</li>').join("")+'</ul>';
    $("estimate-source").textContent=sourceText();
    $("estimate-context").textContent="작성일: "+new Date().toLocaleDateString("ko-KR")+" · 장례형태: "+(state.funeralType||"미정")+" · 지역: "+txt("region1")+" · 장례식장: "+(selectedName||txt("region2")||"미정")+" · 장법: "+(state.burialType||"미정")+(state.burialType!=="매장"?" · 화장시설: "+(selectedCrem?.name||"미정")+" · 거주지·기간: "+$("crem-residence").value:"");
  };
  summaryText=function() {
    const d=calcData();
    return originalSummary()+"\n\n[항목별 산출내역]\n"+[...d.serviceItems,...d.externalItems].map(r=>r[0]+": "+money(r[1])).join("\n")+"\n\n[미확인 비용·조건]\n"+warnings().join("\n")+"\n\n[요금 근거]\n"+sourceText()+"\n작성일: "+new Date().toLocaleDateString("ko-KR");
  };
  $("hall-manual").addEventListener("change",e=>{manualHall=e.target.checked;$("hallCost").readOnly=!manualHall;$("hallCost").value=manualHall?"":hallLines().reduce((s,r)=>s+r[1],0);recalc();});
  $("crem-manual").addEventListener("change",e=>{manualCrem=e.target.checked;$("cremationCost").readOnly=!manualCrem;$("cremationCost").value="";$("crem-rate").value="";recalc();});
  $("crem-facility").addEventListener("change",updateCrem);
  $("crem-rate").addEventListener("change",e=>{manualCrem=false;$("crem-manual").checked=false;$("cremationCost").readOnly=true;$("cremationCost").value=e.target.value!==""?selectedCrem.prices[Number(e.target.value)].amount:"";$("crem-qualified").checked=false;recalc();});
  ["facility-hours","facility-days"].forEach(id=>$(id).addEventListener("input",()=>{rows.forEach((r,i)=>{$("facility-qty-"+i).value=qtyFor(r).qty;});if(!manualHall)$("hallCost").value=hallLines().reduce((s,r)=>s+r[1],0);recalc();}));
  ["hall-manual-source","crem-manual-source","crem-qualified","food-not-used","burial-not-used","extra-reviewed","crem-residence"].forEach(id=>$(id).addEventListener("input",recalc));
  const originalRender=renderHallCards;
  renderHallCards=function(){originalRender();const el=$("hallSelect");if(selectedHall){if(![...el.options].some(o=>o.value===selectedHall)){const o=document.createElement("option");o.value=selectedHall;o.textContent=selectedHall;el.append(o);}el.value=selectedHall;}updateHall();};
  $("subregionSelect").addEventListener("change",()=>{rows=[];selectedName=null;updateHall();});
  $("crem-search").addEventListener("input",()=> {
    const q=$("crem-search").value.trim(),keep=$("crem-facility").value;
    const all=(crem?.facilities||[]).filter(f=>!q||[f.name,f.province,f.district,f.address].join(" ").includes(q)||f.name===keep);
    $("crem-facility").innerHTML='<option value="">화장시설 선택</option>'+all.map(f=>'<option>'+safe(f.name)+'</option>').join("");$("crem-facility").value=keep;
  });
  Promise.allSettled(["data/funeral-halls.json","data/funeral-hall-price-baseline.json","data/funeral-hall-prices.json","data/cremation-prices.json"].map(async u=>{const r=await fetch(u,{cache:"no-store",signal:AbortSignal.timeout(12000)});if(!r.ok)throw Error(u);return r.json();})).then(results=>{
    failed=results.some(r=>r.status==="rejected");
    const data=results.map(r=>r.status==="fulfilled"?r.value:null);
    [ ,catalog,latest,crem]=data;
    if(data[0]?.items){
      Object.keys(hallData).forEach(k=>delete hallData[k]);
      const aliases={"서울특별시":"서울","부산광역시":"부산","대구광역시":"대구","인천광역시":"인천","광주광역시":"광주","대전광역시":"대전","울산광역시":"울산","세종특별자치시":"세종","경기도":"경기","강원특별자치도":"강원","충청북도":"충북","충청남도":"충남","전북특별자치도":"전북","전라남도":"전남","경상북도":"경북","경상남도":"경남","제주특별자치도":"제주"};
      facilityRecords=data[0].items;
      const duplicateNames=new Set(facilityRecords.filter((f,i,a)=>a.findIndex(v=>norm(v.fcltNm)===norm(f.fcltNm))!==i).map(f=>norm(f.fcltNm)));
      data[0].items.forEach(f=>{const p=aliases[f.ctpv]||f.ctpv;hallData[p]??={};hallData[p][f.sigungu]??=[];if(!hallData[p][f.sigungu].includes(f.fcltNm))hallData[p][f.sigungu].push(f.fcltNm);hallMeta[f.fcltNm]=duplicateNames.has(norm(f.fcltNm))?{type:"동명 시설 · 상세 확인",operation:f.gubun||"확인 필요",rooms:"확인 필요",address:"동명 시설이 있어 주소·가격 직접 확인 필요"}:{type:f.operType||"운영형태 확인",operation:f.gubun||"확인 필요",rooms:f.mtaCnt?Number(f.mtaCnt)+"개 (시설목록 기준)":"확인 필요",address:f.addr};});
      renderHalls();
    }
    $("crem-facility").innerHTML='<option value="">화장시설 선택</option>'+(crem?.facilities||[]).map(f=>'<option>'+safe(f.name)+'</option>').join("");
    $("nationwide-status").textContent=failed?"일부 자료 연결 실패 · 시설 확인 후 직접 입력 가능":"전국 시설목록 연결 · 가격은 원문 기준일 확인";
    loading=false;updateHall(true);recalc();
  });
  recalc();
})();
