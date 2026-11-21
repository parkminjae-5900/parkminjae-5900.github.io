import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createCounselingSession} from '../../counseling/session.mjs';
const knowledge=JSON.parse(fs.readFileSync(new URL('../../counseling/knowledge.json',import.meta.url)));
const today='2026-10-28', config={knowledge,clock:()=>today};let checks=0;
async function test(fn){await fn();checks++;}
await test(async()=>{const s=createCounselingSession(config);const [a,b]=await Promise.all([s.reply('인천 무빈소'),s.reply('그럼 비용은?')]);assert.equal(b.state.region,'인천');assert.ok(b.answers.some(x=>x.id==='q1'));assert.equal(b.quote.amount,null);});
await test(async()=>{const a=createCounselingSession(config),b=createCounselingSession(config);await a.reply('서울 가족장');assert.equal((await b.reply('그럼 비용은?')).state.region,null);});
await test(async()=>{const s=createCounselingSession(config);await s.reply('서울 가족장');const state=s.snapshot();state.region='부산';assert.equal(s.snapshot().region,'서울');s.reset();assert.equal((await s.reply('입관')).state.region,null);});
await test(async()=>{const s=createCounselingSession(config);await assert.rejects(s.reply(''));assert.ok((await s.reply('입관')).answers.length);});
await test(async()=>{let calls=0;const s=createCounselingSession({...config,trustedQuoteProvider:async()=>{calls++;return null;}});await s.reply('그럼 의식이 없어요 비용은');assert.equal(calls,0);});
await test(async()=>{const s=createCounselingSession({...config,trustedQuoteProvider:async()=>{throw Error('개인정보가 포함될 수 있는 내부 오류');}});const r=await s.reply('무빈소 비용');assert.equal(r.quote.amount,null);assert.ok(!JSON.stringify(r).includes('개인정보가 포함될'));});
const item={id:'room',facilityId:'fixture',status:'verified',sourceGrade:'official',sourceUrl:'https://example.org/fixture',checkedAt:today,reviewBy:'2026-11-01',effectiveFrom:today,effectiveUntil:'2026-11-01',unit:'hour',unitPrice:1000,quantity:24,billingRuleConfirmed:true};
const options={facilityId:'fixture',serviceDate:today,requiredIds:['room','cremation']};
await test(async()=>{const s=createCounselingSession({...config,trustedQuoteProvider:async()=>({items:[item],options})});const r=await s.reply('시설비 계산');assert.equal(r.quote.amount,null);assert.equal(r.quote.calculation.subtotal,24000);});
await test(async()=>{const s=createCounselingSession({...config,trustedQuoteProvider:async()=>({items:[item],options:{...options,requiredIds:['room']}})});const r=await s.reply('시설비 계산');assert.equal(r.quote.amount,24000);assert.equal(r.quote.status,'verified_items_complete');});
await test(async()=>{let release,started;const ready=new Promise(r=>started=r);const s=createCounselingSession({...config,trustedQuoteProvider:()=>new Promise(r=>{release=r;started();})});const pending=s.reply('인천 시설비');await ready;s.reset();release(null);await assert.rejects(pending,/초기화/);assert.deepEqual(s.snapshot(),{});});
await test(async()=>{const k=structuredClone(knowledge),s=createCounselingSession({...config,knowledge:k});k.entries=[];assert.ok((await s.reply('입관')).answers.length);});
console.log(JSON.stringify({sessionChecksPassed:checks}));
