import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import worker from '../reception-worker/worker.mjs';
const originalFetch=globalThis.fetch;
const base={name:'테스트',phone:'01000000000',contactTime:'any',consent:true,consentVersion:'2026-10-07',requestId:'11111111-1111-4111-8111-111111111111',turnstileToken:'test-token'};
function environment(){const db=new DatabaseSync(':memory:');db.exec(readFileSync(new URL('../reception-worker/migrations/0001_intake.sql',import.meta.url),'utf8'));return {db,env:{DB:{prepare(sql){return {bind(...args){const statement=db.prepare(sql);return {run:async()=>statement.run(...args),first:async()=>statement.get(...args),all:async()=>({results:statement.all(...args)})};}}}},TURNSTILE_SECRET:'test-only',ADMIN_TOKEN:'a'.repeat(40)}};}
function request(body=base,origin='https://www.dahamsangjo.co.kr'){return new Request('https://intake.example/requests',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:JSON.stringify(body)});}
test('stored once; duplicate with different content conflicts; private read and expiry',async()=>{
 const {db,env}=environment();
 globalThis.fetch=async()=>Response.json({success:true,hostname:'www.dahamsangjo.co.kr',action:'consultation'});
 try {
  let res=await worker.fetch(request(),env);assert.equal(res.status,200);assert.deepEqual(await res.json(),{ok:true,requestId:base.requestId});
  assert.equal((await worker.fetch(request(),env)).status,200);assert.equal(db.prepare('SELECT count(*) AS n FROM requests').get().n,1);
  assert.equal((await worker.fetch(request({...base,phone:'01011111111'}),env)).status,409);
  assert.equal((await worker.fetch(new Request('https://intake.example/admin/requests'),env)).status,401);
  let authorized=new Request('https://intake.example/admin/requests',{headers:{Authorization:'Bearer '+env.ADMIN_TOKEN}});
  let listing=await (await worker.fetch(authorized,env)).json();assert.equal(listing.requests[0].phone,base.phone);
  db.prepare('UPDATE requests SET expires_at = 1').run();
  listing=await (await worker.fetch(authorized,env)).json();assert.equal(listing.requests.length,0);
  await worker.scheduled({},env);assert.equal(db.prepare('SELECT count(*) AS n FROM requests').get().n,0);
 } finally {globalThis.fetch=originalFetch;db.close();}
});
test('invalid consent, data, origins and oversized submissions never store',async()=>{
 const {db,env}=environment();
 for(const mutation of [{consent:false},{phone:'not a phone'},{contactTime:'unknown'},{name:'x'.repeat(31)},{requestId:'x'},{consentVersion:'old'}]) assert.equal((await worker.fetch(request({...base,...mutation}),env)).status,400);
 assert.equal((await worker.fetch(request(base,'https://evil.example'),env)).status,403);
 assert.equal((await worker.fetch(request({...base,name:'x'.repeat(5000)}),env)).status,413);
 assert.equal(db.prepare('SELECT count(*) AS n FROM requests').get().n,0);db.close();
});
test('verification and storage failures never report successful intake',async()=>{
 const {db,env}=environment();
 try {
  for(const verification of [{success:false},{success:true,hostname:'evil.example',action:'consultation'},{success:true,hostname:'www.dahamsangjo.co.kr',action:'wrong'}]){
   globalThis.fetch=async()=>Response.json(verification);assert.equal((await worker.fetch(request(),env)).status,403);
  }
  globalThis.fetch=async()=>{throw Error('network');};assert.equal((await worker.fetch(request(),env)).status,503);
  globalThis.fetch=async()=>Response.json({success:true,hostname:'www.dahamsangjo.co.kr',action:'consultation'});
  assert.equal((await worker.fetch(request(),{...env,DB:{prepare(){throw Error('unavailable');}}})).status,503);
  assert.equal((await worker.fetch(request(),{...env,ADMIN_TOKEN:''})).status,503);
  assert.equal(db.prepare('SELECT count(*) AS n FROM requests').get().n,0);
 } finally {globalThis.fetch=originalFetch;db.close();}
});

test('health checks configuration and operator pagination has no gaps',async()=>{
 const {db,env}=environment();
 try {
  assert.equal((await worker.fetch(new Request('https://intake.example/health'),env)).status,200);
  assert.equal((await worker.fetch(new Request('https://intake.example/health'),{...env,TURNSTILE_SECRET:''})).status,503);
  const insert=db.prepare('INSERT INTO requests (id,name,phone,contact_time,consent_version,payload_hash,created_at,expires_at) VALUES (?,?,?,?,?,?,?,?)');
  const now=Date.now();
  for(let i=0;i<205;i++){
   const id=`00000000-0000-4000-8000-${String(i).padStart(12,'0')}`;
   insert.run(id,'','01000000000','any','2026-10-07','hash',now,now+86400000);
  }
  const headers={Authorization:'Bearer '+env.ADMIN_TOKEN};
  const first=await (await worker.fetch(new Request('https://intake.example/admin/requests',{headers}),env)).json();
  assert.equal(first.requests.length,200);assert.ok(first.nextCursor);
  const second=await (await worker.fetch(new Request('https://intake.example/admin/requests?before='+encodeURIComponent(first.nextCursor),{headers}),env)).json();
  assert.equal(second.requests.length,5);assert.equal(second.nextCursor,null);
  const ids=new Set([...first.requests,...second.requests].map(x=>x.id));assert.equal(ids.size,205);
 } finally {db.close();}
});

import vm from 'node:vm';
const clientSource=readFileSync(new URL('../consult-request.js',import.meta.url),'utf8');
function clientHarness(response){
 const elements=new Map(),events=[];let handler, sent;
 for(const id of ['callback-request','request-fields','availability','request-result','request-submit'])elements.set(id,{textContent:'',disabled:id==='request-fields',focus(){},reportValidity(){return true;},reset(){},addEventListener(type,fn){handler=fn;}});
 const form=elements.get('callback-request');
 const values=new Map([['phone','010-0000-0000'],['name','테스트'],['contactTime','any'],['consent','on']]);
 const window={DAHAM_INTAKE:{endpoint:'https://intake.example/requests',turnstileSiteKey:'public-test'},DAHAM_ANALYTICS:{ga4MeasurementId:'G-TEST'},gtag(...args){events.push(args);},turnstile:{render(_target,options){options.callback('token');return 1;},reset(){}}};
 vm.runInNewContext(clientSource,{window,document:{getElementById:id=>elements.get(id),head:{appendChild(){}},createElement(){return {};}},URL,crypto,AbortSignal,FormData:class {get(key){return values.get(key);}},fetch:async(_url,options)=>{sent=JSON.parse(options.body);return response(sent);}});
 window.dahamIntakeReady();
 return {form,elements,events,window,submit:()=>handler({preventDefault(){}}),get sent(){return sent;}};
}
test('client reports conversion only after matching saved receipt and excludes personal data',async()=>{
 const h=clientHarness(sent=>Response.json({ok:true,requestId:sent.requestId}));await h.submit();await h.submit();
 assert.equal(h.events.length,1);assert.equal(h.events[0][1],'consult_submit');assert.equal(h.form.hidden,true);
 assert.equal(JSON.stringify(h.events).includes('01000000000'),false);assert.equal(JSON.stringify(h.events).includes('테스트'),false);assert.equal(JSON.stringify(h.events).includes(h.sent.requestId),false);
});
test('client retains request ID on ambiguous failure and records no false conversion',async()=>{
 const h=clientHarness(()=>{throw Error('timeout');});await h.submit();const id=h.sent.requestId;
 assert.equal(h.events.length,0);assert.equal(h.form.hidden,undefined);assert.equal(h.elements.get('request-fields').disabled,false);
 h.window.dahamIntakeReady();await h.submit();assert.equal(h.sent.requestId,id);
 const bad=clientHarness(()=>Response.json({ok:true,requestId:'wrong'}));await bad.submit();assert.equal(bad.events.length,0);assert.equal(bad.form.hidden,undefined);
});

test('shared analytics strips query, referrer path and arbitrary event values',()=>{
 const source=readFileSync(new URL('../analytics-tracking.js',import.meta.url),'utf8');
 const values=new Map(),listeners=new Map(),dataLayer=[];
 const storage={getItem:key=>values.get(key)||null,setItem:(key,value)=>values.set(key,value)};
 class Form {}
 const location={origin:'https://www.dahamsangjo.co.kr',href:'https://www.dahamsangjo.co.kr/consult.html?utm_source=naver&utm_term=01012345678&n_query=user%40example.com',pathname:'/consult.html',search:'?utm_source=naver&utm_term=01012345678&n_query=user%40example.com'};
 const document={title:'상담',referrer:'https://search.example/private/path?phone=01012345678',head:{appendChild(){}},createElement(){return{};},addEventListener(type,fn){listeners.set(type,fn);}};
 const window={DAHAM_ANALYTICS:{enabled:true,ga4MeasurementId:'G-TEST'},dataLayer};
 vm.runInNewContext(source,{window,document,location,localStorage:storage,URL,URLSearchParams,Date,Math,Set,HTMLFormElement:Form});
 const entries=dataLayer.map(args=>Array.from(args));
 const config=entries.find(x=>x[0]==='config');
 assert.equal(config[2].page_location,'https://www.dahamsangjo.co.kr/consult.html');
 assert.equal(config[2].page_referrer,'https://search.example');
 assert.equal(config[2].send_page_view,false);
 const page=entries.find(x=>x[0]==='event'&&x[1]==='page_view');
 assert.equal(page[2].page_location,'https://www.dahamsangjo.co.kr/consult.html');
 assert.equal(page[2].page_referrer,'https://search.example');
 assert.equal(JSON.stringify(entries).includes('01012345678'),false);
 assert.equal(JSON.stringify(entries).includes('user@example.com'),false);
 window.dahamTrack('custom_event',{secret:'01012345678',area:'서울'});
 const custom=dataLayer.map(args=>Array.from(args)).at(-1);assert.equal(custom[2].secret,undefined);assert.equal(custom[2].area,'서울');
});

test('retention is 30 days and retry never extends it; concurrent requests insert once',async()=>{
 const {db,env}=environment();
 globalThis.fetch=async()=>Response.json({success:true,hostname:'www.dahamsangjo.co.kr',action:'consultation'});
 try {
  const responses=await Promise.all(Array.from({length:8},()=>worker.fetch(request(),env)));
  assert.ok(responses.every(r=>r.status===200));
  const row=db.prepare('SELECT * FROM requests').get();
  assert.equal(row.expires_at-row.created_at,30*86400000);
  await worker.fetch(request(),env);
  assert.equal(db.prepare('SELECT expires_at FROM requests').get().expires_at,row.expires_at);
  assert.equal(db.prepare('SELECT COUNT(*) n FROM requests').get().n,1);
 } finally {globalThis.fetch=originalFetch;db.close();}
});
test('CORS, malformed JSON, wrong media type and admin cursors fail safely',async()=>{
 const {db,env}=environment();
 try {
  const preflight=await worker.fetch(new Request('https://intake.example/requests',{method:'OPTIONS',headers:{Origin:'https://www.dahamsangjo.co.kr'}}),env);
  assert.equal(preflight.status,204);assert.equal(preflight.headers.get('Access-Control-Allow-Origin'),'https://www.dahamsangjo.co.kr');
  for(const [body,type,status] of [['{','application/json',400],['{}','text/plain',415]]){
   assert.equal((await worker.fetch(new Request('https://intake.example/requests',{method:'POST',headers:{Origin:'https://www.dahamsangjo.co.kr','Content-Type':type},body}),env)).status,status);
  }
  const headers={Authorization:'Bearer '+env.ADMIN_TOKEN};
  for(const before of ['bad','null','[1]','[1,"invalid"]'])assert.equal((await worker.fetch(new Request('https://intake.example/admin/requests?before='+encodeURIComponent(before),{headers}),env)).status,400);
  const privateResponse=await worker.fetch(new Request('https://intake.example/admin/requests',{headers}),env);
  assert.equal(privateResponse.headers.get('Cache-Control'),'no-store');assert.equal(privateResponse.headers.get('Access-Control-Allow-Origin'),null);
 } finally {db.close();}
});
test('cleanup deletes only expired records and repeat cleanup is harmless',async()=>{
 const {db,env}=environment();
 globalThis.fetch=async()=>Response.json({success:true,hostname:'www.dahamsangjo.co.kr',action:'consultation'});
 try {
  await worker.fetch(request(),env);
  await worker.fetch(request({...base,requestId:'22222222-2222-4222-8222-222222222222'}),env);
  db.prepare('UPDATE requests SET expires_at=1 WHERE id=?').run(base.requestId);
  await worker.scheduled({},env);await worker.scheduled({},env);
  assert.equal(db.prepare('SELECT COUNT(*) n FROM requests').get().n,1);
  assert.notEqual(db.prepare('SELECT id FROM requests').get().id,base.requestId);
 } finally {globalThis.fetch=originalFetch;db.close();}
});
test('cleanup failure stays failed and never exposes the database error',async()=>{
 const originalError=console.error,logs=[];console.error=value=>logs.push(value);
 try {
  await assert.rejects(worker.scheduled({},{DB:{prepare(){throw Error('private contact 01000000000');}}}),/^Error: expired_requests_cleanup_failed$/);
  assert.deepEqual(logs,['{"event":"expired_requests_cleanup_failed"}']);
 } finally {console.error=originalError;}
});
test('client fails closed for missing or insecure setup',()=>{
 for(const cfg of [{},{endpoint:'http://unsafe.example/requests',turnstileSiteKey:'key'},{endpoint:'https://safe.example/requests',turnstileSiteKey:''}]){
  const elements=new Map(['callback-request','request-fields','availability','request-result','request-submit'].map(id=>[id,{disabled:true,textContent:''}]));
  vm.runInNewContext(clientSource,{window:{DAHAM_INTAKE:cfg},document:{getElementById:id=>elements.get(id)},URL});
  assert.equal(elements.get('request-fields').disabled,true);
  assert.match(elements.get('availability').textContent,/1600-6131/);
 }
});
test('analytics failure does not turn a saved request into a failed request',async()=>{
 const h=clientHarness(sent=>Response.json({ok:true,requestId:sent.requestId}));
 h.window.gtag=()=>{throw Error('analytics blocked');};
 await h.submit();assert.equal(h.form.hidden,true);assert.match(h.elements.get('request-result').textContent,/접수되었습니다/);
});
