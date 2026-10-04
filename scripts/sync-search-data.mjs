import fs from 'node:fs';
import {pathToFileURL} from 'node:url';

export const targets = ['index.html','postpaid.html','postpaid-price.html','cost.html','family.html','nobinso.html','nobinso-cost.html','nobinso-vs-family.html'];
const origin = 'https://www.dahamsangjo.co.kr/';
export const plain = value => value.replace(/<[^>]*>/g,'').replace(/&nbsp;/g,' ').replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/\s+/g,' ').trim();
export function searchData(file, html) {
  const url = origin+(file==='index.html'?'':file);
  const title = plain(html.match(/<title>([\s\S]*?)<\/title>/i)[1]);
  const description = html.match(/<meta name="description" content="([^"]*)"/i)[1];
  const page = {'@type':'WebPage','@id':url+'#webpage',url,name:title,description:plain(description),inLanguage:'ko-KR',isPartOf:{'@id':origin+'#website'},publisher:{'@id':origin+'#organization'}};
  const graph=[page];
  if (file!=='index.html') {
    const breadcrumb={'@type':'BreadcrumbList','@id':url+'#breadcrumb',itemListElement:[{'@type':'ListItem',position:1,name:'다함상조 홈',item:origin},{'@type':'ListItem',position:2,name:title.split('|')[0].trim(),item:url}]};
    page.breadcrumb={'@id':breadcrumb['@id']}; graph.push(breadcrumb);
  }
  const questions=[...html.matchAll(/<details\b[^>]*>\s*<summary[^>]*>([\s\S]*?)<\/summary>\s*<p[^>]*>([\s\S]*?)<\/p>\s*<\/details>/gi)].map(m=>({'@type':'Question',name:plain(m[1]),acceptedAnswer:{'@type':'Answer',text:plain(m[2])}}));
  if(questions.length) graph.push({'@type':'FAQPage','@id':url+'#faq-data',url,isPartOf:{'@id':page['@id']},mainEntity:questions});
  return {'@context':'https://schema.org','@graph':graph};
}
export function renderData(file,html) {
  return '<script id="daham-search-data" type="application/ld+json">\n'+JSON.stringify(searchData(file,html),null,2).replaceAll('<','\\u003c')+'\n</script>';
}
const managed=/<script id="daham-search-data" type="application\/ld\+json">[\s\S]*?<\/script>/;
if (process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  const write=process.argv.includes('--write');const errors=[];
  for(const file of targets) {
    const html=fs.readFileSync(file,'utf8'),expected=renderData(file,html),current=html.match(managed)?.[0];
    if(current===expected) continue;
    if(write) fs.writeFileSync(file,current?html.replace(managed,()=>expected):html.replace('</head>',expected+'\n</head>'));
    else errors.push(file+': visible content and search data are out of sync');
  }
  if(errors.length){console.error(errors.join('\n'));process.exitCode=1;}
  else console.log(write?'Search data generated from visible content.':'Search data matches visible content.');
}
