const ORIGINS = new Set(['https://www.dahamsangjo.co.kr', 'https://dahamsangjo.co.kr']);
const HOSTS = new Set(['www.dahamsangjo.co.kr', 'dahamsangjo.co.kr']);
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const reply = (status, body, origin) => new Response(JSON.stringify(body), {status, headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff',...(origin ? {'Access-Control-Allow-Origin':origin,'Vary':'Origin'} : {})}});
export function validate(body) {
  if (!body || typeof body !== 'object' || Array.isArray(body)) return null;
  const {name='', phone, contactTime='any', consent, consentVersion, requestId, turnstileToken} = body;
  if (typeof name !== 'string' || name.trim().length > 30 || /[\x00-\x1f]/.test(name) || typeof phone !== 'string' || !/^0\d{8,10}$/.test(phone)) return null;
  if (!['any','daytime','evening'].includes(contactTime) || consent !== true || consentVersion !== '2026-10-07' || !UUID.test(requestId || '') || typeof turnstileToken !== 'string' || !turnstileToken || turnstileToken.length > 2048) return null;
  return {name:name.trim(),phone,contactTime,consentVersion,requestId,turnstileToken};
}
async function digest(value) {return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value))),x=>x.toString(16).padStart(2,'0')).join('');}
async function equalSecret(a,b) {const x=await digest(a),y=await digest(b);let different=0;for(let i=0;i<x.length;i++)different|=x.charCodeAt(i)^y.charCodeAt(i);return different===0;}
export default {
  async fetch(request, env) {
    const url = new URL(request.url), origin = request.headers.get('Origin');
    if (url.pathname === '/health' && request.method === 'GET') {
      if (!env.DB || !env.TURNSTILE_SECRET || !env.ADMIN_TOKEN || env.ADMIN_TOKEN.length < 32) return reply(503,{ok:false});
      try {await env.DB.prepare('SELECT 1 FROM requests LIMIT 1').bind().first();return reply(200,{ok:true,scope:'storage-and-configuration'});} catch (_) {return reply(503,{ok:false});}
    }
    // Operator access is never embedded in the static site; read after explicit authentication.
    if (url.pathname === '/admin/requests' && request.method === 'GET') {
      if (!env.ADMIN_TOKEN || env.ADMIN_TOKEN.length < 32 || !await equalSecret(request.headers.get('Authorization') || '', 'Bearer '+env.ADMIN_TOKEN)) return reply(401,{ok:false});
      try {
        const before = url.searchParams.get('before');
        let cursor = null;
        if (before) {try {cursor=JSON.parse(before);} catch (_) {return reply(400,{ok:false});}
          if (!Array.isArray(cursor) || cursor.length !== 2 || !Number.isSafeInteger(cursor[0]) || !UUID.test(cursor[1])) return reply(400,{ok:false});}
        const sql='SELECT id, name, phone, contact_time, created_at FROM requests WHERE expires_at > ?'+(cursor ? ' AND (created_at < ? OR (created_at = ? AND id < ?))' : '')+' ORDER BY created_at DESC, id DESC LIMIT 201';
        const args=cursor ? [Date.now(),cursor[0],cursor[0],cursor[1]] : [Date.now()];
        const rows=await env.DB.prepare(sql).bind(...args).all();
        const records=rows.results.slice(0,200), last=records.at(-1);
        return reply(200,{ok:true,requests:records,nextCursor:rows.results.length>200 ? JSON.stringify([last.created_at,last.id]) : null});
      } catch (_) {return reply(503,{ok:false});}
    }
    if (url.pathname !== '/requests') return reply(404,{ok:false});
    if (!ORIGINS.has(origin)) return reply(403,{ok:false});
    if (request.method === 'OPTIONS') return new Response(null,{status:204,headers:{'Access-Control-Allow-Origin':origin,'Access-Control-Allow-Methods':'POST','Access-Control-Allow-Headers':'Content-Type','Access-Control-Max-Age':'600','Vary':'Origin'}});
    if (request.method !== 'POST') return reply(405,{ok:false},origin);
    // Intake remains unavailable until storage, abuse protection AND operator access exist.
    if (!env.DB || !env.TURNSTILE_SECRET || !env.ADMIN_TOKEN || env.ADMIN_TOKEN.length < 32) return reply(503,{ok:false},origin);
    if (!request.headers.get('Content-Type')?.startsWith('application/json')) return reply(415,{ok:false},origin);
    let raw = '', size = 0;
    try {
      const reader = request.body?.getReader();
      if (!reader) return reply(400,{ok:false},origin);
      const decoder = new TextDecoder();
      while (true) {const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>4096){await reader.cancel();return reply(413,{ok:false},origin);}raw+=decoder.decode(value,{stream:true});}
      raw += decoder.decode();
    } catch (_) {return reply(400,{ok:false},origin);}
    let item;try{item=validate(JSON.parse(raw));}catch(_){}
    if (!item) return reply(400,{ok:false},origin);
    try {
      const verification=await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({secret:env.TURNSTILE_SECRET,response:item.turnstileToken}),signal:AbortSignal.timeout(8000)});
      const check=await verification.json();
      if (!verification.ok || !check.success || check.action !== 'consultation' || !HOSTS.has(check.hostname)) return reply(403,{ok:false},origin);
      const now=Date.now();
      const hash=await digest(JSON.stringify([item.name,item.phone,item.contactTime,item.consentVersion]));
      // A UUID handles retries without exposing someone else's request or contact values.
      await env.DB.prepare('INSERT OR IGNORE INTO requests (id,name,phone,contact_time,consent_version,payload_hash,created_at,expires_at) VALUES (?,?,?,?,?,?,?,?)').bind(item.requestId,item.name,item.phone,item.contactTime,item.consentVersion,hash,now,now+30*86400000).run();
      const stored=await env.DB.prepare('SELECT payload_hash, expires_at FROM requests WHERE id = ?').bind(item.requestId).first();
      if (!stored || stored.payload_hash !== hash || stored.expires_at<=now) return reply(409,{ok:false},origin);
      return reply(200,{ok:true,requestId:item.requestId},origin);
    } catch (_) {return reply(503,{ok:false},origin);}
  },
  async scheduled(_controller,env) {
    const result=await env.DB.prepare('DELETE FROM requests WHERE expires_at <= ?').bind(Date.now()).run();
    const deleted=Number(result?.meta?.changes ?? result?.changes ?? 0);
    console.log(JSON.stringify({event:'expired_requests_cleanup',deleted:Number.isFinite(deleted)?deleted:0}));
  }
};
