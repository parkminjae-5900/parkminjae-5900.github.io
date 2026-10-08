(function(){
  const cfg=window.DAHAM_ANALYTICS||{};
  const id=(cfg.ga4MeasurementId||"").trim();
  if(!cfg.enabled||!/^G-[A-Z0-9]+$/i.test(id)) return;
  if(window.__DAHAM_GA4_INITIALIZED__) return;
  window.__DAHAM_GA4_INITIALIZED__=true;
  window.dataLayer=window.dataLayer||[];
  window.gtag=window.gtag||function(){window.dataLayer.push(arguments);};
  const gtag=window.gtag;
  const s=document.createElement("script");
  s.async=true;
  s.src="https://www.googletagmanager.com/gtag/js?id="+encodeURIComponent(id);
  document.head.appendChild(s);
  gtag("js",new Date());
  const initialAttribution=attribution();
  gtag("config",id,Object.assign({send_page_view:true,allow_google_signals:false,allow_ad_personalization_signals:false},initialAttribution));

  let memoryLeadId="";
  function attribution(){
    try{
      const q=new URLSearchParams(location.search);
      const keys=["utm_source","utm_medium","utm_campaign","utm_term","utm_content","gclid","n_media","n_query","n_rank","n_ad_group"];
      function safeValue(key,value){
        let v=String(value||"").trim().slice(0,150);
        if(!v) return "";
        if(/[\r\n<>]/.test(v)||/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i.test(v)||/\d{6}-[1-8]\d{6}/.test(v)||/(?:01[016789])[- ]?\d{3,4}[- ]?\d{4}/.test(v)) return "";
        if(key==="gclid") return /^[A-Za-z0-9._~-]+$/.test(v)?v:"";
        return v.replace(/[^0-9A-Za-z가-힣._~ -]/g,"");
      }
      function safeReferrer(value){
        try{const u=new URL(value);return (u.origin+u.pathname).slice(0,300);}catch(e){return "";}
      }
      function safePath(value){
        try{return new URL(value,location.origin).pathname.slice(0,300);}catch(e){return location.pathname;}
      }
      const firstKey="daham_first_touch";
      let first={};
      try{first=JSON.parse(localStorage.getItem(firstKey)||"{}")||{};}catch(e){}
      if(!first.landing_page){
        first={landing_page:location.pathname,referrer:safeReferrer(document.referrer),first_seen_at:new Date().toISOString()};
        keys.forEach(function(k){const v=safeValue(k,q.get(k));if(v)first[k]=v;});
      }
      first.landing_page=safePath(first.landing_page);
      first.referrer=safeReferrer(first.referrer);
      keys.forEach(function(k){const v=safeValue(k,first[k]);if(v)first[k]=v;else delete first[k];});
      try{localStorage.setItem(firstKey,JSON.stringify(first));}catch(e){}
      let leadId=memoryLeadId;
      try{leadId=localStorage.getItem("daham_lead_id")||memoryLeadId;}catch(e){}
      if(!leadId){
        leadId="L-"+Date.now().toString(36)+"-"+Math.random().toString(36).slice(2,10);
        try{localStorage.setItem("daham_lead_id",leadId);}catch(e){}
      }
      memoryLeadId=leadId;
      function safeQaMarker(value){
        const v=String(value||"").trim();
        if(v==="off") return v;
        return /^[A-Za-z0-9._-]{1,64}$/.test(v)?v:"";
      }
      let qaMarker=safeQaMarker(q.get("daham_qa"));
      try{
        if(qaMarker==="off"){
          sessionStorage.removeItem("daham_qa_marker");
          qaMarker="";
        }else{
          const storedQa=safeQaMarker(sessionStorage.getItem("daham_qa_marker"));
          if(qaMarker) sessionStorage.setItem("daham_qa_marker",qaMarker);
          else qaMarker=storedQa;
        }
      }catch(e){if(qaMarker==="off")qaMarker="";}
      const out={lead_id:leadId,landing_page:first.landing_page||"",first_referrer:first.referrer||""};
      keys.forEach(function(k){const v=safeValue(k,q.get(k)||first[k]);if(v)out[k]=v;});
      if(qaMarker) out.qa_marker=qaMarker;
      return out;
    }catch(e){return {};}
  }

  function send(name,params){
    try{gtag("event",name,Object.assign({page_path:location.pathname,page_title:document.title},params||{},attribution()));}catch(e){}
  }
  window.dahamTrack=function(name,params){send(name,params);};

  document.addEventListener("click",function(e){
    const a=e.target.closest("a,button");
    if(!a) return;
    const href=(a.getAttribute("href")||"").trim();
    const text=(a.innerText||a.getAttribute("aria-label")||"").trim().slice(0,120);
    if(/^tel:/i.test(href)) send("phone_click",{link_url:href,link_text:text});
    if(/kakao|pf.kakao|open.kakao|talk/i.test(href+" "+text)) send("kakao_click",{link_url:href,link_text:text});
    if(/견적|estimate|quote|calculator/i.test(href+" "+text)) send("estimate_click",{link_url:href,link_text:text});
    if(/상담|consult/i.test(href+" "+text)) send("consult_click",{link_url:href,link_text:text});
    if(/A4|견적서|pdf/i.test(href+" "+text)) send("quote_document_open",{link_url:href,link_text:text});
  },true);

  document.addEventListener("submit",function(e){
    const f=e.target;
    if(!(f instanceof HTMLFormElement)) return;
    const sig=((f.id||"")+" "+(f.className||"")+" "+(f.getAttribute("action")||"")).toLowerCase();
    if(/consult|상담/.test(sig)) send("consult_submit");
    if(/quote|estimate|견적/.test(sig)) send("estimate_submit");
  },true);

  const path=location.pathname.toLowerCase();
  if(path.startsWith("/jangjunmo/")) send("jangjunmo_view");

  const isMubinsoPage=/mubinso|nobinso/.test(path);
  const isFamilyPage=/family/.test(path);
  const isRegionPage=/^\/area-[^/]+-funeral\.html$/.test(path);
  const isSpecificFuneralHome=
    (!isRegionPage && /-funeral\.html$/.test(path) && !/-funeral-halls\.html$/.test(path)) ||
    /^\/jangjunmo\/funeral-home\/[^/]+\/?$/.test(path);

  if(isMubinsoPage) send("mubinso_page_view");
  if(isFamilyPage) send("family_funeral_page_view");
  if(isRegionPage) send("region_page_view");
  if(isSpecificFuneralHome) send("funeral_home_page_view");
})();
