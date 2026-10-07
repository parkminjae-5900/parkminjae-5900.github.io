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
  function safeOrigin(value){
    try{return new URL(value).origin.slice(0,150);}catch(e){return "";}
  }
  function safePath(value){
    try{return new URL(value,location.origin).pathname.slice(0,300);}catch(e){return location.pathname;}
  }
  function safeValue(key,value){
    const v=String(value||"").trim().slice(0,150);
    if(!v||/[\r\n<>]/.test(v)||/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i.test(v)||/\d{6}-[1-8]\d{6}/.test(v)||/(?:01[016789])[- ]?\d{3,4}[- ]?\d{4}/.test(v)) return "";
    if(key==="gclid") return /^[A-Za-z0-9._~-]+$/.test(v)?v:"";
    return v.replace(/[^0-9A-Za-z가-힣._~ -]/g,"");
  }
  gtag("js",new Date());
  gtag("config",id,{send_page_view:false,allow_google_signals:false,allow_ad_personalization_signals:false});
  gtag("event","page_view",{page_location:location.origin+safePath(location.href),page_path:safePath(location.href),page_title:document.title.slice(0,150),page_referrer:safeOrigin(document.referrer),send_to:id});

  function attribution(){
    try{
      const q=new URLSearchParams(location.search);
      const keys=["utm_source","utm_medium","utm_campaign","utm_content","gclid","n_media","n_rank","n_ad_group"];
      const firstKey="daham_first_touch";
      let first={};
      try{first=JSON.parse(localStorage.getItem(firstKey)||"{}")||{};}catch(e){}
      if(!first.landing_page){
        first={landing_page:safePath(location.href),referrer_origin:safeOrigin(document.referrer),first_seen_at:new Date().toISOString()};
        keys.forEach(function(k){const v=safeValue(k,q.get(k));if(v)first[k]=v;});
        try{localStorage.setItem(firstKey,JSON.stringify(first));}catch(e){}
      }
      let leadId="";
      try{leadId=localStorage.getItem("daham_lead_id")||"";}catch(e){}
      if(!leadId){
        leadId="L-"+Date.now().toString(36)+"-"+Math.random().toString(36).slice(2,10);
        try{localStorage.setItem("daham_lead_id",leadId);}catch(e){}
      }
      const out={lead_id:leadId,landing_page:safePath(first.landing_page||location.pathname),first_referrer_origin:safeOrigin(first.referrer_origin||first.referrer)};
      keys.forEach(function(k){const v=safeValue(k,q.get(k)||first[k]);if(v)out[k]=v;});
      return out;
    }catch(e){return {};}
  }

  const allowedParams=new Set(["lead_id","landing_page","landing_path","first_referrer_origin","referrer_origin","utm_source","utm_medium","utm_campaign","utm_content","gclid","n_media","n_rank","n_ad_group","link_kind","link_host","link_path","page_type","area","funeral_hall","package_key","guest_count","form_id","method"]);
  function cleanParams(params){
    const out={};
    Object.keys(params||{}).forEach(function(key){
      if(!allowedParams.has(key)) return;
      const value=params[key];
      if(typeof value==="number"&&Number.isFinite(value)) out[key]=value;
      else {
        const clean=(key==="landing_page"||key==="landing_path"||key==="link_path")?safePath(value):(key==="first_referrer_origin"||key==="referrer_origin")?safeOrigin(value):safeValue(key,value);
        if(clean)out[key]=clean;
      }
    });
    return out;
  }
  function send(name,params){
    try{gtag("event",name,Object.assign({page_path:safePath(location.href)},cleanParams(attribution()),cleanParams(params)));}catch(e){}
  }
  window.dahamTrack=function(name,params){send(name,params);};

  document.addEventListener("click",function(e){
    const a=e.target.closest("a,button");
    if(!a) return;
    const href=(a.getAttribute("href")||"").trim();
    const text=(a.innerText||a.getAttribute("aria-label")||"").trim().slice(0,120);
    let target={link_kind:"button"};
    if(/^tel:/i.test(href)) target={link_kind:"telephone"};
    else if(href){try{const u=new URL(href,location.href);target={link_kind:u.origin===location.origin?"internal":"external",link_host:u.origin===location.origin?"":u.hostname,link_path:u.origin===location.origin?safePath(u.href):""};}catch(_) {}}
    if(/^tel:/i.test(href)) send("phone_click",target);
    if(/kakao|pf.kakao|open.kakao|talk/i.test(href+" "+text)) send("kakao_click",target);
    if(/견적|estimate|quote|calculator/i.test(href+" "+text)) send("estimate_click",target);
    if(/상담|consult/i.test(href+" "+text)) send("consult_click",target);
    if(/A4|견적서|pdf/i.test(href+" "+text)) send("quote_document_open",target);
  },true);

  document.addEventListener("submit",function(e){
    const f=e.target;
    if(!(f instanceof HTMLFormElement)) return;
    const sig=((f.id||"")+" "+(f.className||"")+" "+(f.getAttribute("action")||"")).toLowerCase();
    if(/consult|상담/.test(sig) && !f.hasAttribute("data-confirmed-conversion")) send("consult_submit_attempt");
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
