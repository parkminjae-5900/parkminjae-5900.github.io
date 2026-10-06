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
  gtag("config",id,{send_page_view:true,allow_google_signals:false,allow_ad_personalization_signals:false});

  function attribution(){
    try{
      const q=new URLSearchParams(location.search);
      const keys=["utm_source","utm_medium","utm_campaign","utm_term","utm_content","gclid","n_media","n_query","n_rank","n_ad_group"];
      const firstKey="daham_first_touch";
      let first={};
      try{first=JSON.parse(localStorage.getItem(firstKey)||"{}")||{};}catch(e){}
      if(!first.landing_page){
        first={landing_page:location.pathname+location.search,referrer:document.referrer||"",first_seen_at:new Date().toISOString()};
        keys.forEach(function(k){const v=q.get(k);if(v)first[k]=v;});
        try{localStorage.setItem(firstKey,JSON.stringify(first));}catch(e){}
      }
      let leadId="";
      try{leadId=localStorage.getItem("daham_lead_id")||"";}catch(e){}
      if(!leadId){
        leadId="L-"+Date.now().toString(36)+"-"+Math.random().toString(36).slice(2,10);
        try{localStorage.setItem("daham_lead_id",leadId);}catch(e){}
      }
      const out={lead_id:leadId,landing_page:first.landing_page||"",first_referrer:first.referrer||""};
      keys.forEach(function(k){const v=q.get(k)||first[k];if(v)out[k]=v;});
      return out;
    }catch(e){return {};}
  }

  function send(name,params){
    try{gtag("event",name,Object.assign({page_path:location.pathname,page_title:document.title},attribution(),params||{}));}catch(e){}
  }

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

  if(location.pathname.startsWith("/jangjunmo/")) send("jangjunmo_view");
  if(/mubinso|nobinso|무빈소/i.test(location.pathname+" "+document.title)) send("mubinso_page_view");
  if(/family|가족장/i.test(location.pathname+" "+document.title)) send("family_funeral_page_view");
  if(/funeral|장례식장/i.test(location.pathname+" "+document.title)) send("funeral_home_page_view");
})();
