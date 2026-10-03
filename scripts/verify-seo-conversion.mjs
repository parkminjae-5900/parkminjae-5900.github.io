import fs from "node:fs";
import path from "node:path";

const root=process.cwd();
const htmls=fs.readdirSync(root).filter(f=>f.endsWith(".html"));
const funnelTargets=htmls.filter(f=>
  ["index.html","cost.html","family.html","nobinso.html","postpaid-price.html","funeral-hospital-guide.html","area-funeral-seo-hub.html"].includes(f) ||
  /^area-.*-funeral\.html$/.test(f) ||
  /-funeral\.html$/.test(f)
);
const errors=[];
for(const file of funnelTargets){
  const c=fs.readFileSync(path.join(root,file),"utf8");
  if(!c.includes("conversion-funnel.js")) errors.push(file+": conversion-funnel.js 누락");
  if(!/<link\s+rel=["']canonical["'][^>]*>/i.test(c)) errors.push(file+": canonical 누락");
}
for(const file of ["index.html","cost.html","family.html","postpaid-price.html"]){
  const c=fs.readFileSync(path.join(root,file),"utf8");
  for(const old of ["249만원","360만원","499만원","가족장 249","일반장 360","프리미엄 499"]){
    if(c.includes(old)) errors.push(file+": 과거 상품가격 표현 남음 - "+old);
  }
}
const funnel=fs.readFileSync(path.join(root,"conversion-funnel.js"),"utf8");
for(const required of ["무빈소 120","꽃나라 199","별나라 299","seo_funnel_view","seo_funnel_calculator_click"]){
  if(!funnel.includes(required)) errors.push("conversion-funnel.js 필수요소 누락: "+required);
}
const calc=fs.readFileSync(path.join(root,"funeral-cost-calculator.html"),"utf8");
for(const required of ["applySeoPrefill","seo_funnel_estimator_prefill","source_page"]){
  if(!calc.includes(required)) errors.push("funeral-cost-calculator.html prefill 누락: "+required);
}
const logo=path.join(root,"assets","daham_logo.jpg");
if(!fs.existsSync(logo)||fs.statSync(logo).size<1000) errors.push("공식 로고 파일 누락 또는 비정상");
if(errors.length){
  console.error("\n"+errors.join("\n"));
  process.exit(1);
}
console.log("SEO conversion verification OK");
console.log("Funnel pages:",funnelTargets.length);
