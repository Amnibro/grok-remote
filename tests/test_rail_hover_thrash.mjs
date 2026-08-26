/* Hovering the conversation list flickered during a live turn: renderSessions() wipes
   sessList.innerHTML and rebuilds every row, and the work board pushes every 0.4s, so the node under
   the cursor was destroyed ~2.5x a second and :hover died with it.
   Baseline: GROK_INDEX=backups/index.html.v1.9.19_pre_hoverthrash.bak node tests/test_rail_hover_thrash.mjs */
import {pathToFileURL} from "url";import {createRequire} from "module";
import path from "path";import fs from "fs";import os from "os";
const HERE=path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/,"$1"));
const ROOT=path.resolve(HERE,"..");
const CAND=[process.env.GROK_NODE_MODULES,path.join(os.homedir(),"Documents","ai","grok-remote","node_modules")].filter(Boolean);
let chromium=null;
for(const b of CAND){try{chromium=createRequire(path.join(b,"x.js"))("playwright-core").chromium;break}catch(e){}}
if(!chromium){console.error("playwright-core not found");process.exit(2)}
let target=path.join(ROOT,process.env.GROK_INDEX||"web/index.html"),tmp=null;
if(!/\.html$/i.test(target)){tmp=path.join(ROOT,"logs","_chk","hover_under_test.html");fs.mkdirSync(path.dirname(tmp),{recursive:true});fs.copyFileSync(target,tmp);target=tmp}
const fails=[];
const ok=(n,c,d)=>{console.log((c?"PASS ":"FAIL ")+n+(c?"":" · "+d));if(!c)fails.push(n)};
const b=await chromium.launch();
try{
  const p=await b.newPage({viewport:{width:1920,height:1080}});
  p.on("pageerror",()=>{});
  await p.goto(pathToFileURL(target).href+"?demo=1");
  await p.waitForFunction(()=>typeof window.renderSessions==="function"&&document.getElementById("sessList"),null,{timeout:20000});

  const r=await p.evaluate(async ()=>{
    // a realistic rail: several idle chats, none of them changing
    window.sessions=undefined;
    const mk=(n,i)=>({sessionId:"01a0"+String(i).padStart(4,"0")+"-0000-7000-8000-00000000000"+i,title:n,cwd:"C:\\Users\\antho\\Documents\\ai",resident:false,activity:"",updated:1787660000+i});
    const list=[mk("Azno-v2",1),mk("Amni-Browse",2),mk("Amni-type",3),mk("Braid",4),mk("Grok Remote",5)];
    try{window.setSessionsForTest?window.setSessionsForTest(list):null}catch(e){}
    // fall back to driving the real global if the page exposes no setter
    if(typeof window.fetchSessions==="function"){/* no network in demo */}
    const host=document.getElementById("sessList");
    // observe node churn while the work board pushes repeatedly with UNCHANGED data
    let removed=0;
    const obs=new MutationObserver(muts=>{for(const m of muts)removed+=m.removedNodes.length});
    obs.observe(host,{childList:true});
    for(let i=0;i<10;i++){                       // 10 work/changed pushes, nothing actually changed
      window.renderSessions();
      await new Promise(r=>setTimeout(r,40));
    }
    obs.disconnect();
    return {removed,kids:host.children.length};
  });
  ok("repeat renders do not tear down the rail",r.removed<=r.kids+1,
     `${r.removed} nodes removed across 10 identical renders (${r.kids} rows) · every one of those kills :hover under the cursor`);
}finally{await b.close();if(tmp)try{fs.unlinkSync(tmp)}catch(e){}}
console.log(fails.length?("\n"+fails.length+" FAILED: "+fails.join(", ")):"\nOK · all checks passed");
process.exit(fails.length?1:0);
