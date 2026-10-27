import fs from 'node:fs';
import readline from 'node:readline';
import {respond,validateCandidate} from './engine.mjs';
const knowledge=JSON.parse(fs.readFileSync(new URL('./knowledge.json',import.meta.url)));
// 줄마다 독립 요청. state는 같은 사용자의 요청에만 서버가 전달한다. 저장하지 않는다.
for await(const line of readline.createInterface({input:process.stdin})){
 try{
  const input=JSON.parse(line),response=respond(input.question,input.state||{},knowledge);
  const errors=input.candidate?validateCandidate(input.candidate,response):[];
  console.log(JSON.stringify({response,candidateAccepted:input.candidate?errors.length===0:null,validationErrors:errors}));
 }catch(e){console.log(JSON.stringify({error:e.message}));}
}
