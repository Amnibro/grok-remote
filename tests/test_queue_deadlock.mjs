/* Queued user messages piled up until restart / hard refresh / cancel, then flushed FIFO.
   Two causes, both tested here against the REAL page:
     1. Circular gate. `_x.ai/queue/changed` with no entries and nothing running is the agent
        saying it is idle, but the client refused to clear `busy` while msgQueue was non-empty,
        and drainMsgQueue refused to run while busy. Neither side could move.
     2. The drain was edge-triggered with no re-arm, so any blocked attempt dropped the wakeup.
   Run against the pre-fix backup to prove it fails there:
     GROK_INDEX=backups/index.html.v1.9.16_pre_queue_deadlock.bak node tests/test_queue_deadlock.mjs
*/
import {pathToFileURL} from "url";
import {createRequire} from "module";
import path from "path";
import fs from "fs";
import os from "os";
/* playwright-core lives in ai/grok-remote/node_modules. NODE_PATH does not apply to ESM imports,
   so resolve it by hand instead of requiring a node_modules symlink in the plugin dir. */
const CANDIDATES=[process.env.GROK_NODE_MODULES,path.join(os.homedir(),"Documents","ai","grok-remote","node_modules"),path.join(process.cwd(),"node_modules")].filter(Boolean);
let chromium=null;
for(const base of CANDIDATES){
  try{chromium=createRequire(path.join(base,"x.js"))("playwright-core").chromium;break}catch(e){}
}
if(!chromium){console.error("playwright-core not found · set GROK_NODE_MODULES · looked in:\n  "+CANDIDATES.join("\n  "));process.exit(2)}
const ROOT=path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/,"$1")),"..");
const REL=process.env.GROK_INDEX||"web/index.html";
const SID="11111111-2222-3333-4444-555555555555";
let target=path.join(ROOT,REL);
let tmp=null;
if(!/\.html$/i.test(target)){
  tmp=path.join(ROOT,"logs","_chk","under_test.html");
  fs.mkdirSync(path.dirname(tmp),{recursive:true});
  fs.copyFileSync(target,tmp);
  target=tmp;
}
const fails=[];
const ok=(name,cond,detail)=>{console.log((cond?"PASS ":"FAIL ")+name+(cond?"":" · "+detail));if(!cond)fails.push(name)};
const browser=await chromium.launch({executablePath:process.env.PW_CHROME||undefined});
try{
  const page=await browser.newPage();
  page.on("pageerror",()=>{});
  await page.goto(pathToFileURL(target).href+"?demo=1");
  await page.waitForFunction(()=>typeof window.handleMsg==="function"&&typeof window.setBusy==="function"&&typeof window.setSelectedSession==="function"&&Array.isArray(window.msgQueue),null,{timeout:20000});

  const deadlock=await page.evaluate(sid=>{
    window.setSelectedSession(sid,{bindSid:true});
    window.msgQueue.length=0;
    window.msgQueue.push({id:"mq-test",mode:"queue",tRaw:"queued while busy",files:[],at:Date.now(),sessionId:sid,echoed:true});
    window.setBusy(true,sid);
    const busyBefore=!!window.busy;
    window.handleMsg({method:"_x.ai/queue/changed",params:{sessionId:sid,entries:[],runningPromptId:null}});
    return {busyBefore,busyAfter:!!window.busy,queued:window.msgQueue.length};
  },SID);
  ok("busy is set before the agent reports idle",deadlock.busyBefore===true,JSON.stringify(deadlock));
  ok("agent-idle clears busy even with messages queued",deadlock.busyAfter===false,
     "busy stayed true with "+deadlock.queued+" queued · the queue can never drain, which is the pile-up");

  /* With a non-empty queue and NO further events, the drain must keep re-checking on its own.
     Blocked on purpose (busy) so every attempt bounces off a gate and has to re-arm. */
  const ticks=await page.evaluate(async sid=>{
    window.msgQueue.length=0;
    window.msgQueue.push({id:"mq-test2",mode:"queue",tRaw:"still queued",files:[],at:Date.now(),sessionId:sid,echoed:true});
    window.setBusy(true,sid);
    let n=0;
    const real=window.drainMsgQueue;
    window.drainMsgQueue=function(){n++;return real.apply(this,arguments)};
    await new Promise(r=>setTimeout(r,4200));
    window.drainMsgQueue=real;
    return n;
  },SID);
  ok("a blocked drain keeps re-arming instead of dropping the wakeup",ticks>=2,
     "drainMsgQueue ran "+ticks+"x in 4.2s with a non-empty queue and no events · nothing re-arms it, so the queue sits until something unrelated fires");

  const drained=await page.evaluate(async sid=>{
    window.msgQueue.length=0;
    window.msgQueue.push({id:"mq-test3",mode:"queue",tRaw:"drain me",files:[],at:Date.now(),sessionId:sid,echoed:true});
    window.setBusy(true,sid);
    window.handleMsg({method:"_x.ai/queue/changed",params:{sessionId:sid,entries:[],runningPromptId:null}});
    await new Promise(r=>setTimeout(r,2600));
    return {busy:!!window.busy};
  },SID);
  ok("busy stays clear after the idle notice",drained.busy===false,JSON.stringify(drained));
}finally{
  await browser.close();
  if(tmp)try{fs.unlinkSync(tmp)}catch(e){}
}
console.log(fails.length?("\n"+fails.length+" FAILED: "+fails.join(", ")):"\nOK · all checks passed");
process.exit(fails.length?1:0);
