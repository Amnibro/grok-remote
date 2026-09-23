import path from "node:path";
import fs from "node:fs";
import {fileURLToPath} from "node:url";
import {launchFirefox,startStatic} from "./bidi_harness.mjs";
const HERE=path.dirname(fileURLToPath(import.meta.url));
const ROOT=path.resolve(HERE,"..");
const WEB=path.join(ROOT,"web");
const INDEX=process.env.GROK_INDEX?path.resolve(ROOT,process.env.GROK_INDEX):path.join(WEB,"index.html");
const PRELOAD=fs.readFileSync(path.join(HERE,"fake_hub_preload.js"),"utf8");
const only=process.argv[2]||"";
const {srv,port}=await startStatic(WEB,INDEX);
const B=await launchFirefox();
await B.setPreload(PRELOAD);
const ORIGIN="http://127.0.0.1:"+port;
const results=[];
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function check(name,cond,detail){results.push({name,ok:!!cond,detail});console.log((cond?"PASS ":"FAIL ")+name+(cond?"":" · "+(typeof detail==="string"?detail:JSON.stringify(detail))))}
async function boot(seed,qs,opts){
  opts=opts||{};
  if(!opts.keepStorage){
    await B.nav(ORIGIN+"/static/__none__").catch(()=>{});
    await B.nav(ORIGIN+"/?auto=0&blank=1");
    await B.ev(`(()=>{localStorage.clear();sessionStorage.clear();return 1})()`);
  }
  await B.ev(`(()=>{localStorage.setItem("__fakehub_seed",${JSON.stringify(JSON.stringify(seed||{}))});${opts.storage?Object.entries(opts.storage).map(([k,v])=>`localStorage.setItem(${JSON.stringify(k)},${JSON.stringify(v)});`).join(""):""}return 1})()`);
  B.clearEvents();
  await B.nav(ORIGIN+"/"+(qs||"?r="+Math.random()));
  if(opts.noWait)return;
  await waitFor(`!!(typeof sid!=="undefined"&&sid&&!sessionSwitching&&!attachReplay&&ws&&ws.readyState===1)`,8000,"chat opened");
}
async function waitFor(expr,ms,what){
  const t0=Date.now();
  while(Date.now()-t0<(ms||5000)){
    try{if(await B.ev(`(()=>{try{return !!(${expr})}catch(e){return false}})()`))return true}catch(e){}
    await sleep(80);
  }
  throw new Error("timeout waiting for "+(what||expr));
}
const J=expr=>B.json(expr);
async function run(name,fn){
  if(only&&!name.includes(only))return;
  try{await Promise.race([fn(),sleep(60000).then(()=>{throw new Error("case timed out")})])}catch(e){check(name+" (threw)",false,String(e&&e.message||e).slice(0,400))}
}
await run("boot: page loads with no JS errors and opens a chat",async()=>{
  await boot({});
  await sleep(600);
  const errs=B.errors().filter(e=>!/favicon|__none__|Failed to load resource|NS_BINDING_ABORTED/i.test(e));
  check("boot: no console/JS errors",errs.length===0,errs.slice(0,5));
  const st=await J(`({sid,page,title:document.getElementById("chatTitle").textContent,cwd:sidCwd})`);
  check("boot: auto-opened the newest chat in the default folder",st.sid==="11111111-aaaa-7aaa-8aaa-000000000001",st);
});
await run("no resend: repeated agent error shows Retry, never re-sends",async()=>{
  await boot({promptMode:"error"});
  await B.ev(`(async()=>{box.value="summarize the repo";await sendPrompt();return 1})()`);
  await sleep(2500);
  const a=await J(`({n:__H.prompts().length,retry:!!feed.querySelector(".act-chip.bad button.pri"),you:feed.querySelectorAll(".row.me").length,q:msgQueue.length,busy})`);
  check("error: exactly one session/prompt sent",a.n===1,a);
  check("error: Retry offered, nothing queued, one You bubble",a.retry&&a.q===0&&a.you===1,a);
  await B.ev(`(()=>{feed.querySelector(".act-chip.bad button.pri").click();return 1})()`);
  await sleep(1500);
  const b=await J(`({n:__H.prompts().length,ids:__H.prompts().map(m=>m.params._grPromptId),retry:feed.querySelectorAll(".act-chip.bad").length,you:feed.querySelectorAll(".row.me").length})`);
  check("error: manual Retry sends once more, with a NEW _grPromptId (hub answered)",b.n===2&&b.ids[0]&&b.ids[1]&&b.ids[0]!==b.ids[1],b);
  check("error: retry does not paint a second You bubble",b.you===1,b);
  await sleep(2500);
  const c=await J(`__H.prompts().length`);
  check("error: still no automatic resend after the second error",c===2,c);
});
await run("no resend: 120s silence only shows status",async()=>{
  await boot({promptMode:"hold"});
  await B.ev(`(async()=>{window.__promptStallMs=1200;box.value="run the deploy";await sendPrompt();return 1})()`);
  await sleep(4000);
  const a=await J(`({n:__H.prompts().length,pend:[...pending.values()].filter(p=>p.kind==="prompt").length,detail:phaseDetail,q:msgQueue.length,retry:!!feed.querySelector(".act-chip")})`);
  check("silence: one send, prompt still pending, nothing requeued",a.n===1&&a.pend===1&&a.q===0&&!a.retry,a);
  check("silence: status says 'no updates for …'",/no updates for/.test(a.detail||""),a);
  await B.ev(`(()=>{window.__promptStallMs=0;return 1})()`);
});
await run("no resend: short link drop mid-send",async()=>{
  await boot({promptMode:"hold"});
  await B.ev(`(async()=>{box.value="deploy please";await sendPrompt();return 1})()`);
  await sleep(200);
  const n0=await J(`__H.sockets.length`);
  await B.ev(`(()=>{__H.cur().serverClose(1006,"");return 1})()`);
  await waitFor(`__H.sockets.length>${n0}&&ws&&ws.readyState===1&&!connecting`,9000,"reconnect");
  await sleep(2500);
  const a=await J(`({n:__H.prompts().length,retry:[...feed.querySelectorAll(".act-chip")].map(x=>x.textContent)})`);
  check("drop: no automatic resend after reconnect",a.n===1,a);
  check("drop: a manual Retry is offered for the unacknowledged send",a.retry.some(t=>/link dropped/.test(t)),a);
  await B.ev(`(()=>{[...feed.querySelectorAll(".act-chip")].find(x=>/link dropped/.test(x.textContent)).querySelector("button.pri").click();return 1})()`);
  await sleep(600);
  const b=await J(`({ids:__H.prompts().map(m=>m.params._grPromptId),chips:[...feed.querySelectorAll(".chip")].map(x=>x.textContent).slice(-3)})`);
  check("drop: Retry reuses the SAME _grPromptId so the hub can dedupe",b.ids.length===2&&b.ids[0]===b.ids[1],b);
  check("drop: hub 'duplicate' reply is reported, not run",b.chips.some(t=>/already sent/.test(t)),b);
});
await run("completion from another cid is ignored",async()=>{
  await boot({promptMode:"hold"});
  await B.ev(`(async()=>{box.value="long job";await sendPrompt();return 1})()`);
  await sleep(150);
  const id=await J(`__H.prompts()[0].id`);
  await B.ev(`(()=>{__H.push({jsonrpc:"2.0",method:"_x.ai/remote/rpc_done",params:{id:${id},cid:"c-someone-else",sessionId:sid,ok:true,detached:true}});return 1})()`);
  await sleep(300);
  const a=await J(`({busy,pend:pending.has(${id}),wait:handleMsg._waitPrompt})`);
  check("cid: another client's completion leaves our turn running",a.busy===true&&a.pend===true,a);
  await B.ev(`(()=>{__H.push({jsonrpc:"2.0",method:"_x.ai/remote/rpc_done",params:{id:${id}+1000,cid:clientId(),sessionId:sid,ok:true,detached:true}});return 1})()`);
  await sleep(200);
  const b=await J(`({pend:pending.has(${id})})`);
  check("cid: our cid but an id we never sent is ignored",b.pend===true,b);
  await B.ev(`(()=>{__H.push({jsonrpc:"2.0",method:"_x.ai/remote/rpc_done",params:{id:${id},cid:clientId(),sessionId:sid,ok:true,detached:true}});return 1})()`);
  await sleep(300);
  const c=await J(`({pend:pending.has(${id}),busy})`);
  check("cid: our own completion (cid + id) ends the turn",c.pend===false&&c.busy===false,c);
});
await run("strict sid matching",async()=>{
  await boot({});
  const r=await J(`(async()=>{
    const full=sid,short=sid.slice(0,8),longer=sid+"-x";
    const mk=(s,t)=>({jsonrpc:"2.0",method:"session/update",params:{sessionId:s,update:{sessionUpdate:"agent_message_chunk",content:{type:"text",text:t}}}});
    __H.push(mk(short,"PREFIX-LEAK"));__H.push(mk(longer,"LONGER-LEAK"));
    __H.push({jsonrpc:"2.0",method:"session/update",params:{update:{sessionUpdate:"agent_message_chunk",content:{type:"text",text:"SESSIONLESS-LEAK"}}}});
    __H.push(mk(full,"EXACT-OK"));
    await new Promise(r=>setTimeout(r,200));
    const txt=feed.innerText;
    return {prefix:txt.includes("PREFIX-LEAK"),longer:txt.includes("LONGER-LEAK"),none:txt.includes("SESSIONLESS-LEAK"),exact:txt.includes("EXACT-OK"),rt:window.grokChat.idsMatch(full,short),arch:isArchived(short)};
  })()`);
  check("sid: prefix / longer / sessionless updates are not painted",!r.prefix&&!r.longer&&!r.none,r);
  check("sid: the exact id is painted",r.exact,r);
  check("sid: chat-runtime idsMatch is strict",r.rt===false,r);
});
await run("new chat: double click -> one session/new with one _grReq",async()=>{
  await boot({newDelay:400});
  await B.ev(`(()=>{const b=document.getElementById("newSess");b.click();b.click();setTimeout(()=>b.click(),50);return 1})()`);
  await waitFor(`String(sid||"").indexOf("99999999-new")===0&&!sessionSwitching`,6000,"new chat");
  await sleep(400);
  const a=await J(`({n:__H.news().length,req:__H.news().map(m=>m.params._grReq),made:__H.newCount})`);
  check("new: exactly one session/new for a double click",a.n===1&&a.made===1,a);
  check("new: it carries a _grReq",!!a.req[0],a);
});
await run("new chat: WS failure falls back to HTTP with the SAME _grReq",async()=>{
  await boot({wsNewFails:true});
  await B.ev(`(()=>{document.getElementById("newSess").click();return 1})()`);
  await waitFor(`String(sid||"").indexOf("99999999-new")===0&&!sessionSwitching`,6000,"new chat");
  const a=await J(`({ws:__H.news().map(m=>m.params._grReq),http:__H.fetchLog.filter(f=>f.path==="/api/session/new").map(f=>f.body._grReq),made:__H.newCount})`);
  check("new: HTTP fallback reuses the WS _grReq (hub dedupes)",a.ws.length===1&&a.http.length===1&&a.ws[0]===a.http[0]&&a.made===1,a);
});
await run("new chat: visible in any scope/search, uses config cwd",async()=>{
  await boot({rows:[
    {sessionId:"11111111-aaaa-7aaa-8aaa-000000000001",title:"First chat",archived:false,titleIsManual:false,cwd:"/home/u/proj",updatedAt:Date.now()-1000},
    {sessionId:"33333333-cccc-7ccc-8ccc-000000000003",title:"Other folder chat",archived:false,titleIsManual:false,cwd:"/srv/other",updatedAt:Date.now()-500}
  ]});
  await B.ev(`(async()=>{const s=sessions.find(x=>x.sessionId.startsWith("33333333"));await openSession(s);return 1})()`);
  await waitFor(`sid&&sid.startsWith("33333333")&&!attachReplay`,5000,"open other");
  await B.ev(`(async()=>{openTaskSheet();document.getElementById("taskCwd").value="/elsewhere/task";document.getElementById("taskMsg").value="";document.getElementById("taskGo").click();return 1})()`);
  await waitFor(`String(sid||"").indexOf("99999999-new1")===0&&!sessionSwitching`,6000,"task chat");
  await B.ev(`(()=>{sessScope="archived";saveSessScope();const f=document.getElementById("sessFilter");f.value="zzz-no-match";renderSessions();return 1})()`);
  await B.ev(`(()=>{document.getElementById("newSess").click();return 1})()`);
  await waitFor(`String(sid||"").indexOf("99999999-new2")===0&&!sessionSwitching`,6000,"plain new chat");
  await sleep(300);
  const a=await J(`({cwds:__H.news().map(m=>m.params.cwd),scope:sessScope,q:document.getElementById("sessFilter").value,row:!!sessList.querySelector('.item[data-sid="'+sid+'"]'),title:sessList.querySelector('.item[data-sid="'+sid+'"] .t')&&sessList.querySelector('.item[data-sid="'+sid+'"] .t').textContent,bar:document.getElementById("chatTitle").textContent,fsroot:__H.fetchLog.filter(f=>f.path==="/api/fs/root").length,def:defaultCwd,cwdField:document.getElementById("cwd").value})`);
  check("new: task used its own folder, plain New used the hub's config cwd",a.cwds[0]==="/elsewhere/task"&&a.cwds[1]==="/home/u/proj",a);
  check("new: opening a chat never POSTs /api/fs/root; defaultCwd unchanged",a.fsroot===0&&a.def==="/home/u/proj"&&a.cwdField==="/home/u/proj",a);
  check("new: scope reset to Active, search cleared, row visible",a.scope==="active"&&a.q===""&&a.row,a);
  check("new: one placeholder title in rail and title bar",a.title===a.bar&&/^Chat · 99999999$/.test(a.bar),a);
});
await run("rename: hub title wins, no localStorage override remains",async()=>{
  const X="11111111-aaaa-7aaa-8aaa-000000000001";
  await boot({
    rows:[{sessionId:X,title:"Server Title",agentTitle:"Agent Title",titleIsManual:true,archived:false,cwd:"/home/u/proj",updatedAt:Date.now()-1000}],
    live:[{sessionId:X,title:"Agent Live Title",cwd:"/home/u/proj",resident:true}]
  },null,{storage:{grok_remote_titles:JSON.stringify({[X]:"Old local override"})}});
  await sleep(600);
  const a=await J(`({row:sessList.querySelector('.item[data-sid="${X}"] .t').textContent,bar:document.getElementById("chatTitle").textContent,ls:localStorage.getItem("grok_remote_titles")})`);
  check("rename: hub meta title beats the agent live list and the old local override",a.row==="Server Title"&&a.bar==="Server Title",a);
  check("rename: legacy grok_remote_titles is gone after migration",a.ls===null,a);
  await B.ev(`(async()=>{await renameSession("${X}",{title:"Renamed On Phone"});return 1})()`);
  await sleep(500);
  const b=await J(`({post:__H.fetchLog.filter(f=>f.path==="/api/session/rename").map(f=>f.body),row:sessList.querySelector('.item[data-sid="${X}"] .t').textContent,ls:Object.keys(localStorage).filter(k=>/title/i.test(k))})`);
  check("rename: POSTs {sessionId,title} to the hub and shows it",b.post.length>=1&&b.post[b.post.length-1].sessionId===X&&b.post[b.post.length-1].title==="Renamed On Phone"&&b.row==="Renamed On Phone",b);
  check("rename: nothing title-ish in localStorage",b.ls.length===0,b);
  await B.ev(`(()=>{__H.push({jsonrpc:"2.0",method:"session/update",params:{sessionId:"${X}",update:{sessionUpdate:"session_info_update",title:"Agent Generated"}}});return 1})()`);
  await sleep(1200);
  const c=await J(`sessList.querySelector('.item[data-sid="${X}"] .t').textContent`);
  check("rename: a later agent title does not override a manual one",c==="Renamed On Phone",c);
  await B.ev(`(()=>{__H.row("${X}").title="Renamed On PC";__H.push({jsonrpc:"2.0",method:"_x.ai/sessions/changed",params:{sessionId:"${X}",reason:"rename"}});return 1})()`);
  await sleep(900);
  const d=await J(`({row:sessList.querySelector('.item[data-sid="${X}"] .t').textContent,bar:document.getElementById("chatTitle").textContent})`);
  check("rename: _x.ai/sessions/changed repaints rail + title from the hub",d.row==="Renamed On PC"&&d.bar==="Renamed On PC",d);
  const Y=await J(`(async()=>{await newSession();return sid})()`);
  await B.ev(`(()=>{__H.push({jsonrpc:"2.0",method:"session/update",params:{sessionId:sid,update:{sessionUpdate:"session_info_update",title:"Agent Named It"}}});return 1})()`);
  await sleep(300);
  const e=await J(`({bar:document.getElementById("chatTitle").textContent})`);
  check("rename: session_info_update names an untitled chat at once",e.bar==="Agent Named It",e);
});
await run("archive: single-session POSTs, survives refresh with stale local data",async()=>{
  const X="11111111-aaaa-7aaa-8aaa-000000000001",Y="22222222-bbbb-7bbb-8bbb-000000000002";
  await boot({},null,{storage:{grok_remote_archived:JSON.stringify([Y])}});
  await sleep(800);
  const m=await J(`({posts:__H.fetchLog.filter(f=>f.path==="/api/session/archived"&&f.method==="POST").map(f=>f.body),ls:localStorage.getItem("grok_remote_archived"),flag:localStorage.getItem("grok_remote_archived_migrated"),yArch:__H.row("${Y}").archived})`);
  check("archive: legacy list migrated once as {ids} then removed",m.posts.length===1&&Array.isArray(m.posts[0].ids)&&m.ls===null&&m.flag==="1"&&m.yArch===true,m);
  await B.ev(`(()=>{__H.fetchLog.length=0;sessScope="all";renderSessions();const b=sessList.querySelector('.item[data-sid="${Y}"] button[data-act="arch"]');b.click();return 1})()`);
  await sleep(500);
  const a=await J(`({posts:__H.fetchLog.filter(f=>f.path==="/api/session/archived"&&f.method==="POST").map(f=>f.body),y:__H.row("${Y}").archived,label:sessList.querySelector('.item[data-sid="${Y}"] button[data-act="arch"]').textContent})`);
  check("archive: unarchive sends ONE {sessionId,archived:false} POST",a.posts.length===1&&a.posts[0].sessionId===Y&&a.posts[0].archived===false&&!a.posts[0].ids&&a.y===false,a);
  check("archive: row button label follows state",a.label==="Archive",a);
  await boot({rows:[
    {sessionId:X,title:"First chat",archived:false,titleIsManual:false,cwd:"/home/u/proj",updatedAt:Date.now()-60000},
    {sessionId:Y,title:"Second chat",archived:false,titleIsManual:false,cwd:"/home/u/proj",updatedAt:Date.now()-3600000}
  ]},null,{storage:{grok_remote_archived:JSON.stringify([Y]),grok_remote_archived_migrated:"1"}});
  await sleep(800);
  const b=await J(`({arch:isArchived("${Y}"),posts:__H.fetchLog.filter(f=>f.path==="/api/session/archived"&&f.method==="POST").length,ls:localStorage.getItem("grok_remote_archived"),active:classifySessions("active","","").primary.map(s=>s.sessionId)})`);
  check("archive: refresh with a stale local list keeps the hub's state",b.arch===false&&b.posts===0&&b.ls===null&&b.active.includes(Y),b);
  await B.ev(`(()=>{__H.archiveFail=true;toggleArchive("${X}");return 1})()`);
  await sleep(500);
  const c=await J(`({arch:isArchived("${X}"),chip:!![...feed.querySelectorAll(".act-chip")].find(x=>/archive failed/.test(x.textContent))})`);
  check("archive: a failed POST reverts and offers Retry",c.arch===false&&c.chip,c);
});
await run("queue: removal persists across refresh",async()=>{
  await boot({});
  await B.ev(`(()=>{busy=true;lastLiveAt=Date.now();enqueueMsg({mode:"queue",tRaw:"first queued",files:[],at:Date.now(),sessionId:sid});enqueueMsg({mode:"queue",tRaw:"second queued",files:[],at:Date.now(),sessionId:sid});paintMsgQueue();queueEl.querySelector("button[data-qi]").click();return 1})()`);
  const a=await J(`({mem:msgQueue.map(q=>q.tRaw),ls:JSON.parse(localStorage.getItem("grok_remote_msgq")||"[]").map(q=>q.tRaw)})`);
  check("queue: × removes from memory and storage",a.mem.length===1&&a.ls.length===1&&a.ls[0]==="second queued",a);
  await boot({},null,{keepStorage:true});
  await sleep(1500);
  const b=await J(`({q:msgQueue.map(q=>q.tRaw),sent:__H.prompts().map(m=>m.params.prompt.map(x=>x.text).join(" "))})`);
  const all=b.q.concat(b.sent).join(" | ");
  check("queue: removed item does not come back after refresh (kept one drains once)",!/first queued/.test(all)&&(all.match(/second queued/g)||[]).length===1,b);
  const c=await J(`(()=>{busy=true;msgQueue.splice(0);msgQueue.push({id:"x",mode:"queue",tRaw:"for another chat",files:[],sessionId:"22222222-bbbb-7bbb-8bbb-000000000002"});msgQueue.push({id:"y",mode:"queue",tRaw:"for this chat",files:[],sessionId:sid});paintMsgQueue();return {head:queueHeadIndex(),html:queueEl.innerText}})()`);
  check("queue: another chat's item neither shows here nor blocks the head",c.head===1&&/1 queued in other chat/i.test(c.html)&&!/for another chat/.test(c.html)&&/for this chat/.test(c.html),c);
});
await run("reconnect: phone stays in the chat",async()=>{
  await boot({},"?layout=mobile&r="+Math.random());
  const s0=await J(`({page,sid})`);
  const n0=await J(`__H.sockets.length`);
  await B.ev(`(()=>{__H.cur().serverClose(1006,"");return 1})()`);
  await waitFor(`__H.sockets.length>${n0}&&ws&&ws.readyState===1&&!connecting`,9000,"reconnect");
  await sleep(1200);
  const a=await J(`({page,sid,body:document.body.classList.contains("page-chat")})`);
  check("reconnect: mobile layout",!(await J(`document.body.classList.contains("desktop")`)),"");
  check("reconnect: still on the chat page with the same chat",s0.page==="chat"&&a.page==="chat"&&a.sid===s0.sid&&a.body,{s0,a});
});
await run("reconnect: offline chat switch is kept",async()=>{
  await boot({});
  const B2="22222222-bbbb-7bbb-8bbb-000000000002";
  await B.ev(`(()=>{__H.closeSocketsQuietly=true;__H.cur().serverClose(1006,"");return 1})()`);
  await B.ev(`(async()=>{const s=sessions.find(x=>x.sessionId==="${B2}");openSession(s);return 1})()`);
  await waitFor(`ws&&ws.readyState===1&&!connecting&&sid==="${B2}"&&!sessionSwitching`,9000,"reconnect after switch");
  await sleep(1500);
  const a=await J(`({sid,loads:__H.sent.filter(m=>m.method==="session/load").map(m=>m.params.sessionId).slice(-2)})`);
  check("reconnect: resumes the chat selected while offline",a.sid===B2&&a.loads[a.loads.length-1]===B2,a);
});
await run("visibility/online with a dead socket forces reconnect",async()=>{
  await boot({});
  const n0=await J(`__H.sockets.length`);
  await B.ev(`(()=>{__H.deadPing=true;window.dispatchEvent(new Event("online"));return 1})()`);
  await waitFor(`__H.sockets.length>${n0}`,7000,"forced reconnect");
  const a=await J(`({n:__H.sockets.length,old:__H.sockets[${n0}-1].readyState})`);
  check("online: an OPEN socket that does not answer is replaced",a.n>n0&&a.old===3,a);
  await B.ev(`(()=>{__H.deadPing=false;return 1})()`);
  await waitFor(`ws&&ws.readyState===1&&!connecting`,6000,"relinked");
  const n1=await J(`__H.sockets.length`);
  await B.ev(`(()=>{document.dispatchEvent(new Event("visibilitychange"));return 1})()`);
  await sleep(4000);
  const n2=await J(`__H.sockets.length`);
  check("visibility: a live socket (answers the probe) is kept",n2===n1,{n1,n2});
});
await run("auth: 4401 shows re-pair UI and stops retrying",async()=>{
  await boot({});
  const n0=await J(`__H.sockets.length`);
  await B.ev(`(()=>{__H.cur().serverClose(4401,"auth");return 1})()`);
  await sleep(3500);
  const a=await J(`({n:__H.sockets.length,msg:document.getElementById("linkBannerMsg").textContent,on:document.getElementById("linkBanner").classList.contains("on"),btn:document.getElementById("btnBannerSetup").textContent})`);
  check("auth: no reconnect loop after 4401",a.n===n0,a);
  check("auth: banner says re-pair",a.on&&/not paired/i.test(a.msg)&&a.btn==="Re-pair",a);
  await B.ev(`(()=>{window.dispatchEvent(new Event("online"));document.dispatchEvent(new Event("visibilitychange"));return 1})()`);
  await sleep(1500);
  const b=await J(`__H.sockets.length`);
  check("auth: online/visibility do not restart the loop",b===n0,b);
});
await run("boot: ?auto=0 and demo do not connect on pageshow",async()=>{
  await boot({},"?auto=0&r="+Math.random(),{noWait:true});
  await sleep(1500);
  const a=await J(`__H.sockets.length`);
  check("auto=0: no socket opened",a===0,a);
  await boot({},"?demo=1&r="+Math.random(),{noWait:true});
  await sleep(2500);
  const b=await J(`({ws:__H.sockets.length,calls:__H.fetchLog.map(f=>f.path).filter(p=>p.startsWith("/api")||p.startsWith("/config")||p.startsWith("/health"))})`);
  check("demo: no socket and no /api /config /health calls (C7)",b.ws===0&&b.calls.length===0,b);
});
await run("echo: repeated message is not swallowed; own echo is",async()=>{
  await boot({promptMode:"ok"});
  const r=await J(`(async()=>{
    box.value="ok";await sendPrompt();
    await new Promise(r=>setTimeout(r,300));
    const ev=(t,i)=>({params:{sessionId:sid,update:{sessionUpdate:"user_message_chunk",content:{type:"text",text:t}},_meta:{eventId:"e-"+i}}});
    await paintDiskEvents([ev("ok",1)],sid,{replay:false});
    await paintDiskEvents([ev("that looks ok",2)],sid,{replay:false});
    await paintDiskEvents([ev("that looks ok",2)],sid,{replay:false});
    return [...feed.querySelectorAll(".row.me .bub")].map(b=>b.dataset.raw);
  })()`);
  check("echo: own prompt echo consumed, real message kept, event id dedupes",JSON.stringify(r)===JSON.stringify(["ok","that looks ok"]),r);
});
await run("catch-up: new chat first reply, old completion does not idle",async()=>{
  await boot({promptMode:"hold"});
  await B.ev(`(async()=>{await newSession();return 1})()`);
  await waitFor(`String(sid||"").indexOf("99999999-new")===0&&!sessionSwitching`,5000,"new chat");
  await B.ev(`(async()=>{box.value="hello new chat";await sendPrompt();return 1})()`);
  await sleep(200);
  const r=await J(`(async()=>{
    const s=sid,t0=promptStartAt[s];
    __H.liveEvents={[s]:[
      {_off:0,params:{sessionId:s,update:{sessionUpdate:"turn_completed"},_meta:{timestampMs:t0-60000}}},
      {_off:1,params:{sessionId:s,update:{sessionUpdate:"user_message_chunk",content:{type:"text",text:"hello new chat"}},_meta:{eventId:"u1",timestampMs:t0+10}}},
      {_off:2,params:{sessionId:s,update:{sessionUpdate:"agent_message_chunk",content:{type:"text",text:"FIRST REPLY"}},_meta:{eventId:"a1",timestampMs:t0+20}}}
    ]};
    pending.forEach(p=>{if(p.kind==="prompt")p.detached=true});
    await diskLiveCatchup();
    return {reply:feed.innerText.includes("FIRST REPLY"),you:feed.querySelectorAll(".row.me").length,busy};
  })()`);
  check("catch-up: first reply of a new chat is painted (offset 0 is real)",r.reply,r);
  check("catch-up: own prompt echo not doubled",r.you===1,r);
  check("catch-up: an older turn's completion does not idle the new turn",r.busy===true,r);
});
await run("double Enter after a send does not cancel the new turn",async()=>{
  await boot({promptMode:"hold"});
  await B.ev(`(async()=>{
    busy=false;
    msgQueue.push({id:"q1",mode:"queue",tRaw:"older queued",files:[],sessionId:sid,echoed:false});
    box.value="brand new";
    box.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",bubbles:true}));
    await new Promise(r=>setTimeout(r,120));
    box.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",bubbles:true}));
    await new Promise(r=>setTimeout(r,700));
    return 1})()`);
  const a=await J(`({cancels:__H.sent.filter(m=>m.method==="session/cancel").length,prompts:__H.prompts().map(m=>m.params.prompt[0].text)})`);
  check("dbl-enter: no session/cancel, only the new prompt went out",a.cancels===0&&a.prompts.length===1,a);
});
await run("heartbeat busy list heals a stuck spinner",async()=>{
  await boot({});
  const a=await J(`(async()=>{setBusy(true,sid);setPhase("tools","stuck");promptStartAt[sid]=0;__H.push({jsonrpc:"2.0",method:"_x.ai/remote/hub",params:{up:true,busy:[]}});await new Promise(r=>setTimeout(r,100));const b1=busy;__H.push({jsonrpc:"2.0",method:"_x.ai/remote/hub",params:{up:true,busy:[sid]}});await new Promise(r=>setTimeout(r,100));return {afterIdle:b1,afterBusy:busy}})()`);
  check("heartbeat: busy:[] idles a stale spinner, busy:[sid] lights it",a.afterIdle===false&&a.afterBusy===true,a);
});
await run("filters: other folders reachable, All shows them, empty state honest",async()=>{
  await boot({rows:[
    {sessionId:"11111111-aaaa-7aaa-8aaa-000000000001",title:"Home chat",archived:false,titleIsManual:false,cwd:"/home/u/proj",updatedAt:Date.now()-1000},
    {sessionId:"44444444-dddd-7ddd-8ddd-000000000004",title:"Azno live trading health check",archived:false,titleIsManual:false,cwd:"/home/u/proj",updatedAt:Date.now()-2000},
    {sessionId:"55555555-eeee-7eee-8eee-000000000005",title:"Sub folder work",archived:false,titleIsManual:false,cwd:"/home/u/proj/sub",updatedAt:Date.now()-3000},
    {sessionId:"66666666-ffff-7fff-8fff-000000000006",title:"Cron tick",archived:false,titleIsManual:false,cwd:"/home/u/proj",kind:"auto",updatedAt:Date.now()-4000}
  ]});
  const a=await J(`(()=>{
    sessScope="active";document.getElementById("sessFilter").value="";renderSessions();
    const act=[...sessList.querySelectorAll(".item")].map(x=>x.dataset.sid.slice(0,8));
    const fold=(sessList.querySelector(".sess-others-more")||{}).textContent||"";
    sessScope="all";renderSessions();
    const all=[...sessList.querySelectorAll(".item")].map(x=>x.dataset.sid.slice(0,8));
    sessScope="active";document.getElementById("sessFilter").value="sub folder";renderSessions();
    const q=[...sessList.querySelectorAll(".item")].map(x=>x.dataset.sid.slice(0,8));
    document.getElementById("sessFilter").value="";renderSessions();
    return {act,fold,all,q,chips:[...document.querySelectorAll("#sessScopeChips button")].map(b=>b.textContent)};
  })()`);
  check("filters: real chat with a 'noise-like' title is shown (no title regex hiding)",a.act.includes("44444444"),a);
  check("filters: other folder is folded (not lost) in Active and listed in All",!a.act.includes("55555555")&&/1 in other folders/.test(a.fold)&&a.all.includes("55555555"),a);
  check("filters: search finds other folders; hub-marked auto stays hidden",a.q.includes("55555555")&&!a.all.includes("66666666"),a);
  check("filters: Active count counts reachable rows",a.chips[0]==="Active 3",a);
});
await run("cid: hello carries a page nonce; cid-conflict close regenerates the cid",async()=>{
  await boot({});
  const a=await J(`(()=>{const h=__H.sent.filter(m=>m.method==="_x.ai/remote/hello").pop();return {cid:h.params.cid,nonce:h.params.nonce,loadedAt:h.params.loadedAt,n:__H.sockets.length}})()`);
  check("cid: hello has cid + nonce + loadedAt",!!a.cid&&!!a.nonce&&a.loadedAt>0,a);
  await B.ev(`(()=>{__H.cur().serverClose(4409,"cid-conflict");return 1})()`);
  await waitFor(`__H.sockets.length>${a.n}&&ws&&ws.readyState===1&&!connecting`,6000,"reconnect after conflict");
  const b=await J(`(()=>{const h=__H.sent.filter(m=>m.method==="_x.ai/remote/hello").pop();return {cid:h.params.cid,ss:sessionStorage.getItem("grok_remote_cid")}})()`);
  check("cid: a conflict close makes this tab take a new cid",b.cid&&b.cid!==a.cid&&b.ss===b.cid,{a,b});
});
await run("per-tab last chat + ?session in the URL",async()=>{
  await boot({});
  const B2="22222222-bbbb-7bbb-8bbb-000000000002";
  await B.ev(`(async()=>{await openSession(sessions.find(x=>x.sessionId==="${B2}"));return 1})()`);
  await waitFor(`sid==="${B2}"&&!attachReplay`,5000,"open B2");
  const a=await J(`({url:location.search,tab:JSON.parse(sessionStorage.getItem("grok_remote_last")).sid})`);
  check("tab: URL carries ?session=<sid> and sessionStorage holds this tab's chat",a.url.includes("session="+B2)&&a.tab===B2,a);
  await B.ev(`(()=>{localStorage.setItem("grok_remote_last",JSON.stringify({sid:"11111111-aaaa-7aaa-8aaa-000000000001",cwd:"/home/u/proj",at:Date.now()}));return 1})()`);
  await boot({},"?r="+Math.random(),{keepStorage:true});
  const b=await J(`sid`);
  check("tab: a reload reopens THIS tab's chat, not the one another tab touched",b===B2,b);
});
await run("drafts persist per chat across a killed page",async()=>{
  await boot({});
  await B.ev(`(()=>{box.value="half-typed thought";box.dispatchEvent(new Event("input"));window.dispatchEvent(new Event("pagehide"));return 1})()`);
  const s1=await J(`sid`);
  await boot({},"?r="+Math.random(),{keepStorage:true});
  const a=await J(`({sid,box:box.value})`);
  check("drafts: the composer text comes back after a reload",a.sid===s1&&a.box==="half-typed thought",a);
  await B.ev(`(async()=>{await newSession();return 1})()`);
  await waitFor(`String(sid||"").indexOf("99999999-new")===0&&!sessionSwitching`,5000,"new chat");
  const b=await J(`({box:box.value,perm:getPermLevel(sid)})`);
  check("new chat: starts with an empty composer and the DEFAULT permission",b.box===""&&b.perm==="always",b);
});
await run("new chat does not inherit another chat's permission level",async()=>{
  await boot({});
  await B.ev(`(()=>{setPermLevel("plan",sid);return 1})()`);
  await B.ev(`(async()=>{await newSession();return 1})()`);
  await waitFor(`String(sid||"").indexOf("99999999-new")===0&&!sessionSwitching`,5000,"new chat");
  const a=await J(`({perm:getPermLevel(sid),first:getPermLevel("11111111-aaaa-7aaa-8aaa-000000000001")})`);
  check("perm: the plan gate stays on its chat, the new chat gets the default",a.perm==="always"&&a.first==="plan",a);
});
await run("chat switch keeps link-scoped requests (initialize) alive",async()=>{
  await boot({});
  const a=await J(`(async()=>{
    __H.onSend=(m)=>m.method==="initialize"?false:undefined;
    let settled="pending";
    req("initialize",initParams(),5000).then(()=>settled="ok",e=>settled="rejected:"+e.message);
    const l=req("session/load",{sessionId:"x-other",cwd:"/",mcpServers:[]},5000).then(()=>"ok",e=>"rejected:"+e.message);
    abortSessionSwitch();
    const lr=await l;
    await new Promise(r=>setTimeout(r,50));
    __H.onSend=null;
    return {init:settled,load:lr};
  })()`);
  check("switch: initialize survives, session/load is rejected",a.init==="pending"&&/session switched/.test(a.load),a);
});
await run("late work/attachment answers never touch the new chat",async()=>{
  await boot({});
  const a=await J(`(async()=>{
    const first=sid;
    let release=null;
    __H.fetchHook=(m,p)=>p==="/api/work"&&!release?new Promise(r=>{release=()=>r(new Response(JSON.stringify({ok:true,jobs:[{sid:first,running:0,phase:"idle",tools:[]}]}),{status:200}))}):null;
    const second=sessions.find(x=>x.sessionId!==first).sessionId;
    __H.jobs=[{sid:second,running:1,phase:"tools",tools:[{id:"t1",status:"in_progress",title:"build"}]}];
    const hw=hydrateWork(first);
    await openSession(sessions.find(x=>x.sessionId===second));
    await new Promise(r=>setTimeout(r,400));
    const before=busy;
    __H.fetchHook=null;
    release();await hw;
    await new Promise(r=>setTimeout(r,100));
    return {before,busy,sid};
  })()`);
  check("K9: a late hydrateWork for the previous chat leaves the current turn alone",a.before===true&&a.busy===true,a);
});
await run("C2 pending row + sessions/changed(new) shows a chat made elsewhere",async()=>{
  await boot({});
  await B.ev(`(()=>{const r=__H.newSession({cwd:"/home/u/proj"});__H.push({jsonrpc:"2.0",method:"_x.ai/sessions/changed",params:{sessionId:r.sessionId,reason:"new"}});window.__made=r.sessionId;return 1})()`);
  await sleep(900);
  const a=await J(`({row:!!sessList.querySelector('.item[data-sid="'+window.__made+'"]'),t:(sessList.querySelector('.item[data-sid="'+window.__made+'"] .t')||{}).textContent})`);
  check("new elsewhere: row appears with the shared placeholder title",a.row&&/^Chat · 99999999$/.test(a.t),a);
});
await run("rail: identical re-renders never tear rows down (hover invariant)",async()=>{
  await boot({rows:[
    {sessionId:"11111111-aaaa-7aaa-8aaa-000000000001",title:"Home chat",archived:false,titleIsManual:false,cwd:"/home/u/proj",updatedAt:Date.now()-1000},
    {sessionId:"22222222-bbbb-7bbb-8bbb-000000000002",title:"Second",archived:false,titleIsManual:false,cwd:"/home/u/proj",updatedAt:Date.now()-2000},
    {sessionId:"55555555-eeee-7eee-8eee-000000000005",title:"Sub folder work",archived:false,titleIsManual:false,cwd:"/home/u/proj/sub",updatedAt:Date.now()-3000}
  ]});
  const r=await J(`(async()=>{
    sessOthersOpen=true;renderSessions();
    const host=document.getElementById("sessList");
    let removed=0;
    const obs=new MutationObserver(ms=>{for(const m of ms)removed+=m.removedNodes.length});
    obs.observe(host,{childList:true,subtree:true});
    for(let i=0;i<10;i++){renderSessions();paintSessScopeChips();handleMsg({jsonrpc:"2.0",method:"_x.ai/work/changed",params:{jobs:[]}});await new Promise(r=>setTimeout(r,30))}
    obs.disconnect();sessOthersOpen=false;
    return {removed,rows:host.querySelectorAll(".item").length};
  })()`);
  check("rail: 10 identical renders + work pushes remove no rows",r.removed===0&&r.rows===3,r);
});
await run("HTTP fallback: _grPromptId + cid, running then rpc_done finishes it",async()=>{
  await boot({});
  const r=await J(`(async()=>{
    __H.httpPromptMode="running";
    const live=ws;ws=null;
    box.value="sent over http";await sendPrompt();
    const f=__H.fetchLog.filter(x=>x.path==="/api/session/prompt").pop();
    const b1=busy;
    ws=live;
    __H.push({jsonrpc:"2.0",method:"_x.ai/remote/rpc_done",params:{id:f.body.requestId,ok:true,detached:true,sessionId:sid,cid:"c-other",method:"session/prompt",promptId:f.body._grPromptId}});
    await new Promise(r=>setTimeout(r,100));
    const b2=busy;
    __H.push({jsonrpc:"2.0",method:"_x.ai/remote/rpc_done",params:{id:f.body.requestId,ok:true,detached:true,sessionId:sid,cid:clientId(),method:"session/prompt",promptId:f.body._grPromptId}});
    await new Promise(r=>setTimeout(r,200));
    return {body:f.body,b1,b2,b3:busy};
  })()`);
  check("http: body carries _grPromptId, cid, requestId (never id)",!!r.body._grPromptId&&!!r.body.cid&&!!r.body.requestId&&!("id" in r.body),r.body);
  check("http: running turn stays busy until OUR rpc_done",r.b1===true&&r.b2===true&&r.b3===false,r);
});
await run("attached prompt: reply + broadcast rpc_done do not double-finish or error",async()=>{
  await boot({promptMode:"ok"});
  await B.ev(`(async()=>{box.value="quick one";await sendPrompt();return 1})()`);
  await sleep(700);
  const a=await J(`({busy,phase:agentPhase,retry:feed.querySelectorAll(".act-chip").length,n:__H.prompts().length})`);
  check("attached: turn ends idle, no error chip, one send",a.busy===false&&a.phase==="idle"&&a.retry===0&&a.n===1,a);
});
await B.close();
srv.close();
const bad=results.filter(r=>!r.ok);
console.log("\n"+(results.length-bad.length)+"/"+results.length+" passed"+(bad.length?" · FAILED: "+bad.map(r=>r.name).join(" | "):""));
process.exit(bad.length?1:0);
