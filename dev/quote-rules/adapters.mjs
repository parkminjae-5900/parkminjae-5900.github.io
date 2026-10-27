import {calculate, REQUIRED, PRODUCTS, number} from './engine.mjs';
const units={maleSuit:50000,femaleSuit:20000,helper:120000,limo:450000,bus:450000};
const legacySource='funeral-cost-calculator.html@20ebd59366e1e1e8689091c408a1076de4bc04c2';
const count=value=>value===''||value===null||value===undefined ? 0 : number(value,'수량');
/** Snapshot of existing state + input values. Package mode must be explicitly selected. */
export function fromLegacy({state={},values={},mode='itemized',productId,contracts={},external=[],facilityId,roomId}) {
  const services=[];
  const push=(id,quantity,unit,unitPrice,label,specification)=>{
    if(!quantity)return;
    const confirmed=contracts[id] || {};
    services.push({id,quantity,unit,unitPrice,label,specification,
      tariff:mode==='itemized' ? {status:'confirmed',reference:legacySource,serviceId:id,unit,unitPrice} : undefined,
      ...confirmed});
  };
  for(const [id,r] of Object.entries(REQUIRED)) push(id,1,r.unit,r.amount,r.label,PRODUCTS.nobinso.coverage[id].specification);
  for(const [id,field,defaultDays] of [['director','directorDays',3],['assistant','assistantDays',1]]) {
    services.find(x=>x.id===id).days=values[field]===undefined ? defaultDays : number(values[field],'근무일수');
  }
  for(const [id,unit] of [['shroud','벌'],['coffin','개'],['urn','개']]) if(state[id]) {
    push(id,1,unit,state[id+'Price'],state[id],state[id]);
    // Existing zero placeholders mean unknown, not free.
    if(!Number(state[id+'Price']) && mode==='itemized') services.at(-1).tariff=undefined;
  }
  for(const id of ['maleSuit','femaleSuit','helper']) push(id,count(values[id]),id==='helper'?'인회':'벌',units[id],id);
  for(const id of ['limo','bus']) if(values[id]===true) push(id,1,'회',units[id],id);
  for(const [id,field] of [['crossBar','crossBarCost'],['vehicleExtra','vehicleExtra']]) if(count(values[field])) push(id,1,'회',count(values[field]),id);
  // Untyped manual external totals are not official facility quotations.
  const pendingRaw=[['facilityOther','hallCost'],['facilityOther','hallEtc'],['food','foodCost'],['cremation','cremationCost'],['burial','burialCost']];
  const externalLines=[...external];
  const facilityFields=['hallCost','hallEtc'].filter(field=>count(values[field]));
  if(facilityFields.length && !externalLines.some(x=>x.id==='facilityOther')) externalLines.push({id:'facilityOther',label:facilityFields.map(field=>field+' '+values[field]+'원').join(' / '),unit:'once',quantity:1});
  for(const [id,field] of pendingRaw) if(count(values[field]) && !externalLines.some(x=>x.id===id)) externalLines.push({id,label:field,unit:'once',quantity:1,unitPrice:count(values[field])});
  return calculate({mode,productId,services,external:externalLines,facilityId,roomId});
}
/** Numeric select values from PR24 are converted to stable product IDs. */
export function fromPrototype({product,services=[],external=[],facilityId,roomId,values={}}) {
  const productId=Object.keys(PRODUCTS).find(id=>PRODUCTS[id].price===number(product,'상품가',true));
  if(!productId)throw Error('알 수 없는 상품');
  const lines=[...services], ext=[...external];
  if(count(values.otherCost)) lines.push({id:'other',quantity:1,unit:'회',unitPrice:count(values.otherCost),label:values.otherNote || '기타'});
  if(count(values.mealCount) || count(values.mealPrice)) if(!ext.some(x=>x.id==='food')) ext.push({id:'food',unit:'meal',quantity:count(values.mealCount),unitPrice:count(values.mealPrice)});
  for(const [id,field] of [['cremation','cremation'],['burial','burial']]) if(count(values[field]) && !ext.some(x=>x.id===id)) ext.push({id,unit:'once',quantity:1,unitPrice:count(values[field])});
  return calculate({mode:'package',productId,services:lines,external:ext,facilityId,roomId});
}
