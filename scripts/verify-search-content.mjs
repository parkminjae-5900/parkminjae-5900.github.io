import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {targets,renderData,plain} from './sync-search-data.mjs';

const root=process.cwd(),origin='https://www.dahamsangjo.co.kr/';
const files=fs.readdirSync(root).filter(f=>f.endsWith('.html')&&!f.startsWith('google'));
const sitemap=fs.readFileSync('sitemap.xml','utf8');
const locations=[...sitemap.matchAll(/<loc>(.*?)<\/loc>/g)].map(m=>m[1]);
const retiredAliases=new Map([['area-incheon-junggu-funeral.html','area-incheon-jemulpo-funeral.html']]);
const facilityEvidence=JSON.parse(fs.readFileSync('data/funeral-hall-evidence.json','utf8'));
const facilityAliases=new Map();
for(const alias of facilityEvidence.aliases||[]){
  assert.match(alias.page,/^[a-z0-9-]+\.html$/,'Unsafe facility alias');
  assert.ok(!facilityAliases.has(alias.page),'Duplicate facility alias');
  const identity=facilityEvidence.entries.find(e=>e.facility_id===alias.facility_id);
  assert.ok(identity?.pages.some(p=>p.page===alias.canonical_page&&p.canonical===origin+p.page),'Alias target must be reviewed canonical of same facility');
  facilityAliases.set(alias.page,alias);
}
assert.equal(new Set(locations).size,locations.length,'Duplicate sitemap URLs');
const titles=new Set(),descriptions=new Set();let faqCount=0;
for(const file of files){
  const html=fs.readFileSync(file,'utf8');
  // Private/utility landing pages intentionally excluded from search do not
  // require a public canonical or sitemap entry. Retired aliases are checked below.
  if (/<meta\b[^>]*name="robots"[^>]*content="[^"]*\bnoindex\b/i.test(html) && !retiredAliases.has(file)) continue;
  const url=origin+(file==='index.html'?'':file);
  const title=html.match(/<title>(.*?)<\/title>/s)?.[1];
  const description=html.match(/<meta name="description" content="([^"]+)"/)?.[1];
  assert.ok(title&&!titles.has(title),file+': missing or duplicate title');titles.add(title);
  assert.ok(description&&!descriptions.has(description),file+': missing or duplicate description');descriptions.add(description);
  assert.equal([...html.matchAll(/<h1\b/gi)].length,1,file+': H1 count');
  const canonicals=[...html.matchAll(/<link rel="canonical" href="([^"]+)"/g)];
  assert.equal(canonicals.length,1,file+': canonical count');
  const retiredTarget=retiredAliases.get(file);
  if(facilityAliases.has(file)){
    const alias=facilityAliases.get(file),target=alias.canonical_page;
    assert.equal(canonicals[0][1],origin+target,file+': reviewed facility alias canonical');
    assert.ok(html.includes('name="daham-facility-id" content="'+alias.facility_id+'"'),file+': alias identity');
    assert.ok(!locations.includes(url),file+': duplicate alias must not be in sitemap');
    assert.ok(locations.includes(origin+target),file+': primary canonical must be in sitemap');
    assert.ok(fs.existsSync(path.join(root,target)),file+': primary target missing');
  }else if(retiredTarget){
    assert.equal(canonicals[0][1],origin+retiredTarget,file+': retired canonical URL');
    const robots=html.match(/<meta name="robots" content="([^"]+)"/)?.[1]||'';
    const robotTokens=robots.split(',').map(x=>x.trim());
    assert.ok(robotTokens.includes('noindex'),file+': retired page must be noindex');
    assert.ok(!robotTokens.includes('index'),file+': retired page must not contain index');
    assert.ok(robotTokens.includes('follow'),file+': retired page must remain follow');
    assert.ok(!locations.includes(url),file+': retired page must stay out of sitemap');
  }else{
    assert.equal(canonicals[0][1],url,file+': canonical URL');
    assert.ok(locations.includes(url),file+': sitemap URL missing');
  }
  assert.ok(!/\\n<script/.test(html),file+': literal newline in head');
  const body=plain(html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'').replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi,''));
  function walk(o){
    if(Array.isArray(o))return o.forEach(walk);
    if(!o||typeof o!=='object')return;
    if(o['@type']==='Question'){
      faqCount++;assert.ok(body.includes(plain(o.name)),file+': question not visible');
      assert.ok(body.includes(plain(o.acceptedAnswer.text)),file+': answer not visible');
    }
    Object.values(o).forEach(walk);
  }
  for(const m of html.matchAll(/<script[^>]*type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/g)) walk(JSON.parse(m[1]));
  const markup=html.replace(/(<script\b[^>]*>)[\s\S]*?<\/script>/gi,'$1</script>');
  for(const m of markup.matchAll(/\b(?:href|src)="([^"<>]+)"/g)){
    const ref=m[1];if(/^(?:[a-z]+:|\/\/|#|\{)/i.test(ref))continue;
    const pathname=decodeURIComponent(ref.split(/[?#]/)[0]);if(!pathname)continue;
    assert.ok(fs.existsSync(path.join(root,pathname.replace(/^\//,''))),file+': missing local path '+ref);
  }
  if(targets.includes(file)) assert.ok(html.includes(renderData(file,html)),file+': run node scripts/sync-search-data.mjs --write');
}
for(const [alias,target] of retiredAliases){
  assert.ok(fs.existsSync(path.join(root,alias)),alias+': retired alias missing');
  assert.ok(fs.existsSync(path.join(root,target)),target+': retired target missing');
  assert.ok(locations.includes(origin+target),target+': retired target missing from sitemap');
}
for(const location of locations){
  assert.ok(location.startsWith(origin),'Sitemap points off site');
  const rel=location.slice(origin.length),local=path.join(root,rel||'index.html');
  assert.ok(fs.existsSync(local),'Sitemap file missing: '+rel);
}
const home=fs.readFileSync('index.html','utf8');
assert.ok(!home.includes('★★★★★'),'Home review evidence required before publishing star ratings');
assert.ok(!home.includes('전국 협약 장례식장'),'Public directory must not imply all facilities are partners');
const personalization=fs.readFileSync('region-personalization.js','utf8');
assert.ok(!/document\.title\s*=|updateMeta\('meta/.test(personalization),'Regional personalization changes canonical metadata');
console.log(JSON.stringify({publicPages:files.length,sitemapURLs:locations.length,synchronizedFAQAnswers:faqCount,managedPages:targets.length,result:'PASS'}));
