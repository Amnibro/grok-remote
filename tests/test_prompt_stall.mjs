/* A brain-dead agent (process alive, WS answering pings, workers dead) accepted session/prompt and
   returned nothing. The prompt is sent raw and registered straight into `pending`, bypassing req()'s
   timeout, so the spinner ran forever. Watchdog fires on total SILENCE so long turns survive.
   Prove it fails on the baseline:
     GROK_INDEX=backups/index.html.v1.9.17_pre_promptwatch.bak node tests/test_prompt_stall.mjs   */
import {pathToFileURL} from "url";
import {createRequire} from "module";
import path from "path";import fs from "fs";import os from "os";
const HERE=path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/,"$1"));
const ROOT=path.resolve(HERE,"..");
const CAND=[process.env.GROK_NODE_MODULES,path.join(os.homedir(),"Documents","ai","grok-remote","node_modules")].filter(Boolean);
let chromium=null;
for(const b of CAND){try{chromium=createRequire(path.join(b,"x.js"))("playwright-core").chromium;break}catch(e){}}
if(!chromium){console.error("playwright-core not found");process.exit(2)}
let target=path.join(ROOT,process.env.GROK_INDEX||"web/index.html"),tmp=null;
if(!/\.html$/i.test(target)){tmp=path.join(ROOT,"logs","_chk","stall_under_test.html");fs.mkdirSync(path.dirname(tmp),{recursive:true});fs.copyFileSync(target,tmp);target=tmp}
const fails=[];
const ok=(n,c,d)=>{console.log((c?"PASS ":"FAIL ")+n+(c?"":" · "+d));if(!c)fails.push(n)};
const b=await chromium.launch();
try{
  const p=await b.newPage();
  p.on("pageerror",()=>{});
  await p.goto(pathToFileURL(target).href+"?demo=1");
  await p.waitForFunction(()=>typeof window.dispatchPromptPayload==="function"&&typeof window.setBusy==="function",null,{timeout:20000});

  const has=await p.evaluate(()=>typeof window.startPromptWatch==="function"&&!!window.pending);
  ok("a prompt watchdog exists",has,
     "session/prompt is registered in `pending` with no timeout · nothing can ever clear the spinner");
  if(has){
    /* Silent agent: watchdog must reject the pending prompt and clear busy. */
    const silent=await p.evaluate(async ()=>{
      window.__promptStallMs=1200;
      const id=98765;let rejected=null;
      window.pending.set(id,{kind:"prompt",sessionId:"x",turnToken:0,resolve:()=>{},reject:e=>{rejected=String(e.message||e);window.setBusy(false)},onDrop:()=>{}});
      window.setBusy(true,"x");
      window.startPromptWatch(id);
      await new Promise(r=>setTimeout(r,3000));
      return {rejected,busy:!!window.busy,stillPending:window.pending.has(id)};
    });
    ok("a silent agent stops the spinner",silent.rejected!==null&&silent.busy===false&&!silent.stillPending,JSON.stringify(silent));
    ok("the failure says something useful",/no reply from the agent/i.test(silent.rejected||""),String(silent.rejected));

    /* A long turn that is still streaming keeps lastLiveAt fresh and must NOT be killed. */
    const streaming=await p.evaluate(async ()=>{
      window.__promptStallMs=1200;
      const id=98766;let rejected=null;
      window.pending.set(id,{kind:"prompt",sessionId:"x",turnToken:0,resolve:()=>{},reject:e=>{rejected=String(e.message||e)},onDrop:()=>{}});
      window.setBusy(true,"x");
      window.startPromptWatch(id);
      const beat=setInterval(()=>{try{window.touchLive()}catch(e){}},300);
      await new Promise(r=>setTimeout(r,4000));
      clearInterval(beat);window.stopPromptWatch();
      const still=window.pending.has(id);window.pending.delete(id);
      return {rejected,still};
    });
    ok("a streaming long turn is never killed",streaming.rejected===null&&streaming.still===true,JSON.stringify(streaming));
  }
}finally{await b.close();if(tmp)try{fs.unlinkSync(tmp)}catch(e){}}
console.log(fails.length?("\n"+fails.length+" FAILED: "+fails.join(", ")):"\nOK · all checks passed");
process.exit(fails.length?1:0);
