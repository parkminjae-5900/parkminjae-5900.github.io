(function(){
  const cfg=window.DAHAM_ANALYTICS||{};
  const id=(cfg.ga4MeasurementId||"").trim();
  if(!cfg.enabled||!/^G-[A-Z0-9]+$/i.test(id)) return;
  window.dataLayer=window.dataLayer||[];
  function gtag(){dataLayer.push(arguments);}
  window.gtag=window.gtag||gtag;
  const s=document.createElement("script");
  s.async=true;
  s.src="https://www.googletagmanager.com/gtag/js?id="+encodeURIComponent(id);
  document.head.appendChild(s);
  gtag("js",new Date());
  gtag("config",id,{send_page_view:true});

  function send(name,params){
    try{gtag("event",name,Object.assign({page_path:location.pathname,page_title:document.title},params||{}));}catch(e){}
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
