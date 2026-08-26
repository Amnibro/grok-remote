/* Scrolled up in a long chat, the 500-900ms poll's trimFeedDom() deleted the rows loadOlderHistory
   had just prepended, scrollTop fell back under 120, and the scroll handler loaded older again --
   forever, walking to the start of the transcript and repainting the rail every pass (the flicker).
   Baseline: GROK_INDEX=backups/index.html.v1.9.18_pre_trimloop.bak node tests/test_trim_scroll_loop.mjs */
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
if(!/\.html$/i.test(target)){tmp=path.join(ROOT,"logs","_chk","trim_under_test.html");fs.mkdirSync(path.dirname(tmp),{recursive:true});fs.copyFileSync(target,tmp);target=tmp}
const fails=[];
const ok=(n,c,d)=>{console.log((c?"PASS ":"FAIL ")+n+(c?"":" · "+d));if(!c)fails.push(n)};
const b=await chromium.launch();
try{
  const p=await b.newPage({viewport:{width:1440,height:900}});
  p.on("pageerror",()=>{});
  await p.goto(pathToFileURL(target).href+"?demo=1");
  await p.waitForFunction(()=>typeof window.trimFeedDom==="function"&&document.getElementById("feed"),null,{timeout:20000});

  const r=await p.evaluate(async ()=>{
    try{window.showPage("chat")}catch(e){}          // the feed is display:none on the setup page
    const feed=document.getElementById("feed");
    feed.innerHTML="";
    for(let i=0;i<120;i++){                       // long transcript, well over FEED_DOM_CAP=72
      const d=document.createElement("div");d.className="row user";
      d.innerHTML='<div class="bub">row '+i+' — '+"x".repeat(200)+'</div>';
      feed.appendChild(d);
    }
    feed.style.overflowY="auto";feed.style.height="600px";
    feed.scrollTop=0;                              // the user has scrolled up, for real
    window.ignoreScrollUntil=0;
    const before=feed.children.length;
    let loads=0;
    if(typeof window.loadOlderHistory==="function"){
      const real=window.loadOlderHistory;
      window.loadOlderHistory=function(){loads++;return Promise.resolve()};
    }
    const seen=[],drift=[];
    feed.scrollTop=Math.floor(feed.scrollHeight/2);   // parked mid-transcript, reading
    const st0=feed.scrollTop;
    for(let i=0;i<12;i++){                             // 12 poll ticks, no user input at all
      feed.scrollTop=st0;                              // the reader holds their place
      const rows=feed.children.length;
      seen.push(window.atBottom());
      window.trimFeedDom();
      if(feed.children.length!==rows)drift.push(rows+"->"+feed.children.length);
      feed.dispatchEvent(new Event("scroll"));
      await new Promise(r=>setTimeout(r,60));
    }
    return {before,after:feed.children.length,loads,st0,scrollTop:feed.scrollTop,atBottomSeen:seen,drift};
  });
  ok("scrolled-up feed is not trimmed by the poll",r.after===r.before,
     `feed went ${r.before} -> ${r.after} rows while scrolled up (atBottom seen: ${JSON.stringify(r.atBottomSeen)}) · the poll ate the prepended history`);
  ok("the poll never trims while you are reading",r.drift.length===0,
     `rows changed under the reader: ${JSON.stringify(r.drift)} · that is what collapses scrollTop and restarts the loop`);
  ok("no runaway loadOlderHistory",r.loads===0,
     `loadOlderHistory fired ${r.loads}x with no user scrolling · this is the walk back to the start of history`);

  const pinned=await p.evaluate(async ()=>{
    try{window.showPage("chat")}catch(e){}
    const feed=document.getElementById("feed");
    feed.innerHTML="";
    for(let i=0;i<120;i++){const d=document.createElement("div");d.className="row user";d.innerHTML='<div class="bub">r'+i+' '+"y".repeat(200)+'</div>';feed.appendChild(d)}
    feed.style.overflowY="auto";feed.style.height="600px";
    feed.scrollTop=feed.scrollHeight;              // pinned to the bottom, for real
    window.ignoreScrollUntil=0;
    const before=feed.children.length;
    window.trimFeedDom();
    return {before,after:feed.children.length};
  });
  ok("pinned to the bottom the cap still applies",pinned.after<pinned.before,
     `feed stayed at ${pinned.after} rows · the DOM cap stopped working`);
}finally{await b.close();if(tmp)try{fs.unlinkSync(tmp)}catch(e){}}
console.log(fails.length?("\n"+fails.length+" FAILED: "+fails.join(", ")):"\nOK · all checks passed");
process.exit(fails.length?1:0);
