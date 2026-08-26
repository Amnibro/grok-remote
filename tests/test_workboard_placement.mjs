/* The work ("thinking") box is 201px tall and used to sit in the rail directly above #sessList.
   The moment a turn started it un-hid, shoved the whole conversation list down, and the row under
   the cursor slid out from under it -- hover died and did not come back. Nothing above the session
   list may change height.
   Baseline: GROK_INDEX=backups/index.html.v1.9.19_pre_workboard_move.bak node tests/test_workboard_placement.mjs */
import {pathToFileURL} from "url";import {createRequire} from "module";
import path from "path";import fs from "fs";import os from "os";
const HERE=path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/,"$1"));
const ROOT=path.resolve(HERE,"..");
const CAND=[process.env.GROK_NODE_MODULES,path.join(os.homedir(),"Documents","ai","grok-remote","node_modules")].filter(Boolean);
let chromium=null;
for(const b of CAND){try{chromium=createRequire(path.join(b,"x.js"))("playwright-core").chromium;break}catch(e){}}
if(!chromium){console.error("playwright-core not found");process.exit(2)}
let target=path.join(ROOT,process.env.GROK_INDEX||"web/index.html"),tmp=null;
if(!/\.html$/i.test(target)){tmp=path.join(ROOT,"logs","_chk","wb_under_test.html");fs.mkdirSync(path.dirname(tmp),{recursive:true});fs.copyFileSync(target,tmp);target=tmp}
const fails=[];
const ok=(n,c,d)=>{console.log((c?"PASS ":"FAIL ")+n+(c?"":" · "+d));if(!c)fails.push(n)};
const b=await chromium.launch();
try{
  const p=await b.newPage({viewport:{width:1920,height:1080}});
  p.on("pageerror",()=>{});
  await p.goto(pathToFileURL(target).href+"?demo=1");
  await p.waitForFunction(()=>document.getElementById("workBoard")&&document.getElementById("sessList"),null,{timeout:20000});
  const r=await p.evaluate(async ()=>{
    try{window.showPage("chat")}catch(e){}
    const host=document.getElementById("sessList"),wb=document.getElementById("workBoard");
    // give the rail rows so it has real geometry
    host.innerHTML="";
    for(let i=0;i<8;i++){const d=document.createElement("div");d.className="item";d.dataset.sid="s"+i;
      d.innerHTML='<div class="body"><div class="t">Chat '+i+'</div><div class="m">C:\ai · 2m</div></div>';host.appendChild(d)}
    await new Promise(r=>requestAnimationFrame(r));
    const before={top:Math.round(host.getBoundingClientRect().top),row:Math.round(host.children[2].getBoundingClientRect().top)};
    // a turn starts: the work board un-hides with real content
    wb.hidden=false;
    wb.innerHTML='<div class="wj"><div class="wj-body"><b>tools · Amni-Browse</b><div class="d">'+("grep servo_real.rs ".repeat(14))+'</div></div><button type="button">Kill</button></div>';
    await new Promise(r=>requestAnimationFrame(r));
    await new Promise(r=>setTimeout(r,60));
    const after={top:Math.round(host.getBoundingClientRect().top),row:Math.round(host.children[2].getBoundingClientRect().top)};
    return {before,after,wbHeight:Math.round(wb.getBoundingClientRect().height)};
  });
  ok("the work box appearing does not move the conversation list",r.before.top===r.after.top,
     `#sessList top ${r.before.top} -> ${r.after.top} when a ${r.wbHeight}px work box appeared`);
  ok("the work box appearing does not move a row out from under the cursor",r.before.row===r.after.row,
     `row 3 top ${r.before.row} -> ${r.after.row} · that is the hover dying mid-turn`);
}finally{await b.close();if(tmp)try{fs.unlinkSync(tmp)}catch(e){}}
console.log(fails.length?("\n"+fails.length+" FAILED: "+fails.join(", ")):"\nOK · all checks passed");
process.exit(fails.length?1:0);
