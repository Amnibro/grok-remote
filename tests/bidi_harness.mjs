import {spawn} from "node:child_process";
import http from "node:http";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
const MIME={".html":"text/html; charset=utf-8",".js":"text/javascript",".mjs":"text/javascript",".css":"text/css",".json":"application/json",".png":"image/png",".jpg":"image/jpeg",".svg":"image/svg+xml",".woff2":"font/woff2",".woff":"font/woff",".ttf":"font/ttf",".webmanifest":"application/manifest+json"};
export function startStatic(webRoot,indexFile){
  const srv=http.createServer((req,res)=>{
    const u=new URL(req.url,"http://x");
    let p=u.pathname;
    let file=null;
    if(p==="/"||p==="/index.html")file=indexFile||path.join(webRoot,"index.html");
    else if(p.startsWith("/static/"))file=path.join(webRoot,decodeURIComponent(p.slice(8)));
    if(!file||!file.startsWith(webRoot)&&file!==indexFile||!fs.existsSync(file)||fs.statSync(file).isDirectory()){res.writeHead(404);res.end("nf");return}
    res.writeHead(200,{"Content-Type":MIME[path.extname(file)]||"application/octet-stream","Cache-Control":"no-store"});
    fs.createReadStream(file).pipe(res);
  });
  return new Promise(r=>srv.listen(0,"127.0.0.1",()=>r({srv,port:srv.address().port})));
}
export async function launchFirefox(){
  const port=Number(process.env.BIDI_PORT)||(20000+Math.floor(Math.random()*20000));
  const base=process.env.GROK_TEST_TMP||os.tmpdir();
  fs.mkdirSync(base,{recursive:true});
  const prof=fs.mkdtempSync(path.join(base,"grk-ff-"));
  fs.writeFileSync(path.join(prof,"user.js"),[
    'user_pref("browser.shell.checkDefaultBrowser", false);',
    'user_pref("datareporting.policy.dataSubmissionEnabled", false);',
    'user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);',
    'user_pref("browser.startup.homepage_override.mstone", "ignore");',
    'user_pref("dom.serviceWorkers.enabled", false);',
    'user_pref("browser.cache.disk.enable", false);',
    'user_pref("browser.cache.memory.capacity", 16384);',
    'user_pref("dom.ipc.processCount", 1);',
    'user_pref("fission.autostart", false);',
    'user_pref("browser.sessionstore.resume_from_crash", false);'
  ].join("\n"));
  const bin=process.env.FIREFOX||"firefox";
  const ff=spawn(bin,["--headless","--no-remote","--profile",prof,"--remote-debugging-port",String(port)],{stdio:["ignore","pipe","pipe"]});
  let cleaned=false;
  const cleanup=()=>{
    if(cleaned)return;cleaned=true;
    try{ff.kill("SIGKILL")}catch(e){}
    try{fs.rmSync(prof,{recursive:true,force:true})}catch(e){}
  };
  process.on("exit",cleanup);
  for(const sig of ["SIGINT","SIGTERM","SIGHUP"])process.on(sig,()=>{cleanup();process.exit(130)});
  process.on("uncaughtException",e=>{console.error(e);cleanup();process.exit(1)});
  await new Promise((res,rej)=>{
    let buf="";
    const t=setTimeout(()=>rej(new Error("firefox did not start: "+buf.slice(-400))),30000);
    const on=d=>{buf+=d;if(/WebDriver BiDi listening/.test(buf)){clearTimeout(t);res()}};
    ff.stdout.on("data",on);ff.stderr.on("data",on);
    ff.on("exit",c=>{clearTimeout(t);rej(new Error("firefox exited "+c+": "+buf.slice(-400)))});
  });
  const ws=new WebSocket("ws://127.0.0.1:"+port+"/session");
  let id=0;const waits=new Map();const events=[];
  ws.onmessage=e=>{
    const m=JSON.parse(e.data);
    if(m.id!=null&&waits.has(m.id)){waits.get(m.id)(m);waits.delete(m.id);return}
    if(m.type==="event")events.push(m);
  };
  await new Promise((r,j)=>{ws.onopen=r;ws.onerror=()=>j(new Error("bidi ws error"))});
  const send=(method,params)=>new Promise(r=>{const i=++id;waits.set(i,r);ws.send(JSON.stringify({id:i,method,params}))});
  const s=await send("session.new",{capabilities:{}});
  if(s.type==="error")throw new Error("session.new: "+JSON.stringify(s));
  await send("session.subscribe",{events:["log.entryAdded"]});
  const tree=await send("browsingContext.getTree",{});
  const ctx=tree.result.contexts[0].context;
  let preloadId=null;
  const api={
    events,
    async setPreload(fnSource){
      if(preloadId)await send("script.removePreloadScript",{script:preloadId});
      const r=await send("script.addPreloadScript",{functionDeclaration:fnSource});
      if(r.type==="error")throw new Error("preload: "+JSON.stringify(r).slice(0,400));
      preloadId=r.result.script;
    },
    async nav(url){const r=await send("browsingContext.navigate",{context:ctx,url,wait:"complete"});if(r.type==="error")throw new Error("nav: "+JSON.stringify(r).slice(0,300));return r},
    async ev(expr){
      const r=await send("script.evaluate",{expression:expr,target:{context:ctx},awaitPromise:true,resultOwnership:"none"});
      if(r.type==="error")throw new Error("evaluate: "+JSON.stringify(r).slice(0,600));
      if(r.result&&r.result.type==="exception")throw new Error("page exception: "+JSON.stringify(r.result.exceptionDetails).slice(0,900));
      const v=r.result.result;
      if(v.type==="string")return v.value;
      if(v.type==="number"||v.type==="boolean")return v.value;
      if(v.type==="undefined"||v.type==="null")return null;
      return JSON.stringify(v);
    },
    async json(expr){const s=await api.ev("(async()=>JSON.stringify(await ("+expr+")))()");return s==null?null:JSON.parse(s)},
    errors(){return events.filter(e=>e.method==="log.entryAdded"&&e.params&&(e.params.level==="error")).map(e=>((e.params.type||"")+": "+(e.params.text||"")+(e.params.stackTrace&&e.params.stackTrace.callFrames&&e.params.stackTrace.callFrames[0]?" @"+e.params.stackTrace.callFrames[0].url.split("/").pop()+":"+e.params.stackTrace.callFrames[0].lineNumber:"")))},
    clearEvents(){events.length=0},
    async close(){
      try{await Promise.race([send("session.end",{}),new Promise(r=>setTimeout(r,1500))])}catch(e){}
      try{ws.close()}catch(e){}
      try{ff.kill("SIGTERM")}catch(e){}
      await new Promise(r=>{if(ff.exitCode!=null)return r();const t=setTimeout(r,3000);ff.once("exit",()=>{clearTimeout(t);r()})});
      cleanup();
    }
  };
  return api;
}
