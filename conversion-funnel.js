(function(){
"use strict";
if(window.__DAHAM_SEO_FUNNEL__)return;window.__DAHAM_SEO_FUNNEL__=true;
var PHONE="16006131";
var PACKAGES=[
 {key:"nobinso",label:"무빈소 120",type:"무빈소",price:1200000,note:"빈소 없이 화장 중심으로 간소하게"},
 {key:"flower199",label:"꽃나라 199",type:"가족장",price:1990000,note:"가족·가까운 친지 중심"},
 {key:"star299",label:"별나라 299",type:"일반장",price:2990000,note:"일반 3일장 중심 구성"}
];
function clean(v){return String(v||"").replace(/\s+/g," ").trim()}
function text(sel){var e=document.querySelector(sel);return e?clean(e.textContent):""}
function area(){
 var s=[document.title,text("h1"),text(".top"),location.pathname].join(" ");
 var a=["강남","강서","서초","서대문","성북","송파","수원","성남","고양","부천","안산","의정부","춘천","인천 중구","인천 서구","인천","서울","경기","강원"];
 for(var i=0;i<a.length;i++)if(s.indexOf(a[i])>-1)return a[i];return "";
}
function hall(){var h=text("h1"),m=h.match(/([^·|]{2,35}(?:병원|의료원|장례식장))/);return m?clean(m[1]):""}
function pageType(){var p=location.pathname;if(/area-/.test(p))return"region";if(/-funeral\.html$/.test(p))return"funeral_hall";if(/cost|price|nobinso|family/.test(p))return"cost_intent";return"home"}
function push(ev,x){window.dataLayer=window.dataLayer||[];var d={event:ev,page_path:location.pathname,page_type:pageType(),area:area(),funeral_hall:hall()};Object.assign(d,x||{});window.dataLayer.push(d)}
function selected(){var r=document.querySelector('input[name="dahamSeoPackage"]:checked'),g=document.getElementById("dahamSeoGuests");return{key:r?r.value:"flower199",guests:g?Math.max(0,Number(g.value||0)):50}}
function pkg(k){return PACKAGES.find(function(x){return x.key===k})||PACKAGES[1]}
function params(o){var p=new URLSearchParams();Object.keys(o).forEach(function(k){if(o[k]!==""&&o[k]!=null)p.set(k,o[k])});return p.toString()}
function goCalc(){var s=selected(),p=pkg(s.key);push("seo_funnel_calculator_click",{package_key:p.key,guest_count:s.guests});location.href="funeral-cost-calculator.html?"+params({source:"seo-funnel",area:area(),hall:hall(),funeralType:p.type,package:p.key,guests:p.type==="무빈소"?0:s.guests,from:location.pathname})}
function call(){var s=selected();push("seo_funnel_call_click",{package_key:s.key,guest_count:s.guests});location.href="tel:"+PHONE}
async function copy(){
 var s=selected(),p=pkg(s.key),lines=["[다함상조 홈페이지 상담]","지역: "+(area()||"미정"),"장례식장: "+(hall()||"미정"),"선택상품: "+p.label,"예상 조문객: "+(p.type==="무빈소"?"해당없음":s.guests+"명"),"요청: 장례식장·접객·화장·장지 포함 실제 예상비용 확인"];
 try{await navigator.clipboard.writeText(lines.join("\n"));alert("상담 내용이 복사되었습니다. 전화상담 시 그대로 전달해 주세요.")}catch(e){prompt("아래 내용을 복사해 주세요.",lines.join("\n"))}
 push("seo_funnel_copy_click",{package_key:p.key,guest_count:s.guests})
}
function style(){
 var e=document.createElement("style");e.id="dahamSeoFunnelStyle";e.textContent=
 ".dahamSeoFunnel{max-width:1080px;margin:28px auto;padding:0 20px;font-family:'Noto Sans KR','Malgun Gothic',Arial,sans-serif}.dahamSeoFunnelCard{background:#fff;border:1px solid #e4d8c6;border-radius:22px;padding:26px;box-shadow:0 12px 30px rgba(54,38,20,.08)}.dahamSeoFunnel h2{margin:0 0 8px;font-size:30px;line-height:1.35}.dahamSeoLead{margin:0 0 18px;color:#635950}.dahamSeoPkgGrid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.dahamSeoPkg{border:1px solid #dfd1bd;border-radius:14px;padding:15px;cursor:pointer}.dahamSeoPkg:has(input:checked){border:2px solid #a87512;background:#fff8e8;padding:14px}.dahamSeoPkg small{display:block;margin-top:5px;color:#6d635b}.dahamSeoRow{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px}.dahamSeoField{background:#fbf7ef;border-radius:13px;padding:14px}.dahamSeoField label{display:block;font-weight:900;margin-bottom:7px}.dahamSeoField input{width:100%;min-height:46px;border:1px solid #d8c9b5;border-radius:10px;padding:10px;font-size:17px}.dahamSeoActions{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:9px;margin-top:16px}.dahamSeoActions button{min-height:54px;border:0;border-radius:12px;font-size:17px;font-weight:900;cursor:pointer}.dahamSeoCalc{background:#b88712;color:#fff}.dahamSeoCall{background:#211914;color:#fff}.dahamSeoCopy{background:#f4ead6;color:#3c2c19;border:1px solid #ddc89f!important}.dahamSeoFine{font-size:13px;color:#796f66}@media(max-width:700px){.dahamSeoFunnel{padding:0 15px}.dahamSeoFunnelCard{padding:20px 16px}.dahamSeoFunnel h2{font-size:25px}.dahamSeoPkgGrid,.dahamSeoRow{grid-template-columns:1fr}.dahamSeoActions{grid-template-columns:1fr 1fr}.dahamSeoCalc{grid-column:1/-1}.dahamSeoActions button{min-height:58px}}";
 document.head.appendChild(e)
}
function mount(){
 if(document.getElementById("dahamSeoFunnel"))return;style();
 var r=document.createElement("section");r.id="dahamSeoFunnel";r.className="dahamSeoFunnel";r.innerHTML='<div class="dahamSeoFunnelCard"><b style="color:#8b6212">검색에서 실제 장례접수까지</b><h2>상품가격만 보지 말고 실제 장례비까지 확인하세요</h2><p class="dahamSeoLead">지역·장례식장·조문객 규모를 이어서 계산해 실제 예상비용을 확인할 수 있습니다.</p><p><strong>현재 기준</strong> · '+(area()||"지역 미지정")+(hall()?" · "+hall():"")+'</p><div class="dahamSeoPkgGrid">'+PACKAGES.map(function(p,i){return'<label class="dahamSeoPkg"><input type="radio" name="dahamSeoPackage" value="'+p.key+'" '+(i===1?"checked":"")+'><b>'+p.label+'</b><small>'+p.note+'</small></label>'}).join("")+'</div><div class="dahamSeoRow"><div class="dahamSeoField"><label for="dahamSeoGuests">예상 조문객</label><input id="dahamSeoGuests" type="number" min="0" max="1000" step="10" value="50"></div><div class="dahamSeoField"><label>계산 기준</label><div>외부비용은 확인된 데이터만 사용하고 최종 견적에서 계산합니다.</div></div></div><div class="dahamSeoActions"><button class="dahamSeoCalc" type="button">실제 장례비 계산하기</button><button class="dahamSeoCall" type="button">☎ 24시간 전화</button><button class="dahamSeoCopy" type="button">상담내용 복사</button></div><p class="dahamSeoFine">※ 장례식장·음식·화장장·장지 비용은 시설과 이용 조건에 따라 달라집니다.</p></div>';
 var a=document.querySelector("main")||document.querySelector(".section")||document.querySelector("footer");if(a&&a.parentNode)a.parentNode.insertBefore(r,a);else document.body.appendChild(r);
 r.querySelector(".dahamSeoCalc").onclick=goCalc;r.querySelector(".dahamSeoCall").onclick=call;r.querySelector(".dahamSeoCopy").onclick=copy;
 r.querySelectorAll('input[name="dahamSeoPackage"]').forEach(function(el){el.onchange=function(){var s=selected(),p=pkg(s.key),g=document.getElementById("dahamSeoGuests");g.disabled=p.type==="무빈소";if(p.type==="무빈소")g.value=0;else if(Number(g.value)===0)g.value=50;push("seo_funnel_package_select",{package_key:p.key})}});
 push("seo_funnel_view")
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",mount);else mount();
})();