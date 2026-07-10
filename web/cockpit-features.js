(function(){
const S={pinned:[],bgTasks:[],termLines:[],alwaysPerm:{},budget:{maxTurns:0,maxEstTokens:0,turns:0,estTokens:0},checkpoints:[],voice:null,reconnects:0,todos:[],git:null,ctx:{used:0,window:500000,usage:null,source:"idle",model:null,updatedAt:0}};
function $(id){return document.getElementById(id)}
function esc(t){return String(t||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}
function chip(t){if(typeof window.chip==="function")window.chip(t);else console.log(t)}
function safeParse(raw,fallback){
 try{
  if(raw==null||raw==="")return fallback;
  const s=String(raw).replace(/^\uFEFF/,"").trim();
  if(!s)return fallback;
  return JSON.parse(s);
 }catch(e){return fallback}
}
async function jfetch(url,opts){
 const r=await fetch(url,Object.assign({cache:"no-store"},opts||{}));
 const text=await r.text();
 const body=safeParse(text,null);
 if(!r.ok){
  const msg=(body&&(body.error||body.detail||body.message))||text.slice(0,200)||("HTTP "+r.status);
  const err=new Error(String(msg).replace(/^404:\s*/i,"not found: "));
  err.status=r.status;err.body=body;err.raw=text;throw err;
 }
 if(body===null){
  const err=new Error("bad json from "+url+" · "+text.slice(0,80));
  err.status=r.status;err.raw=text;throw err;
 }
 return body;
}
function loadState(){
 try{
 const b=safeParse(localStorage.getItem("grok_remote_budget"),{});
 S.budget.maxTurns=+b.maxTurns||0;S.budget.maxEstTokens=+b.maxEstTokens||0;
 S.pinned=safeParse(localStorage.getItem("grok_remote_pins"),[]);
 S.alwaysPerm=safeParse(localStorage.getItem("grok_remote_always_perm"),{});
 if(!Array.isArray(S.pinned))S.pinned=[];
 if(!S.alwaysPerm||typeof S.alwaysPerm!=="object")S.alwaysPerm={};
 }catch(e){}
}
function saveBudget(){try{localStorage.setItem("grok_remote_budget",JSON.stringify({maxTurns:S.budget.maxTurns,maxEstTokens:S.budget.maxEstTokens}))}catch(e){}}
function savePins(){try{localStorage.setItem("grok_remote_pins",JSON.stringify(S.pinned.slice(0,12)))}catch(e){}}
function saveAlways(){try{localStorage.setItem("grok_remote_always_perm",JSON.stringify(S.alwaysPerm))}catch(e){}}
function noteUsage(text){
 S.budget.turns++;
 S.budget.estTokens+=Math.ceil(String(text||"").length/4);
 paintBudget();paintCtxMeter();
 if(S.budget.maxTurns&&S.budget.turns>=S.budget.maxTurns)chip("budget - turn limit reached ("+S.budget.turns+")");
 if(S.budget.maxEstTokens&&S.budget.estTokens>=S.budget.maxEstTokens)chip("budget - est tokens ~"+S.budget.estTokens);
}
function noteContextFromMeta(meta){
 if(!meta||typeof meta!=="object")return;
 const used=meta.totalTokens||meta.contextTokensUsed||meta.context_tokens_used||meta.tokensUsed;
 const win=meta.contextWindowTokens||meta.context_window_tokens||meta.totalContextTokens;
 if(used!=null&&+used>0){
  S.ctx.used=Math.max(S.ctx.used||0,+used);
  S.ctx.source="stream";
  S.ctx.updatedAt=Date.now();
 }
 if(win!=null&&+win>0)S.ctx.window=+win;
 if(meta.modelId)S.ctx.model=meta.modelId;
 paintCtxMeter();
}
function paintBudget(){
 const el=$("budgetBar");if(!el)return;
 const used=S.ctx.used||0;
 const win=S.ctx.window||500000;
 const parts=["turns "+S.budget.turns+(S.budget.maxTurns?"/"+S.budget.maxTurns:""),"ctx "+fmtTok(used)+"/"+fmtTok(win)];
 el.textContent="cost - "+parts.join(" - ");
 el.classList.toggle("hot",!!((S.budget.maxTurns&&S.budget.turns>=S.budget.maxTurns)||(used&&win&&used/win>=0.85)));
}
function fmtTok(n){
 n=+n||0;
 if(n>=1e6)return (n/1e6).toFixed(2)+"M";
 if(n>=1e3)return (n/1e3).toFixed(n>=10000?0:1)+"k";
 return String(Math.round(n));
}
async function refreshSessionContext(){
 const sid=window.sid;if(!sid)return;
 const cwd=window.sidCwd||(document.getElementById("cwd")&&document.getElementById("cwd").value)||"";
 try{
  const j=await jfetch("/api/session/signals?sessionId="+encodeURIComponent(sid)+"&cwd="+encodeURIComponent(cwd||"."));
  if(!j||!j.ok)return;
  if(j.contextTokensUsed!=null)S.ctx.used=+j.contextTokensUsed||0;
  if(j.contextWindowTokens!=null)S.ctx.window=+j.contextWindowTokens||500000;
  if(j.contextWindowUsage!=null)S.ctx.usage=+j.contextWindowUsage;
  if(j.primaryModelId)S.ctx.model=j.primaryModelId;
  if(j.turnCount!=null)S.budget.turns=+j.turnCount||S.budget.turns;
  S.ctx.source="signals";
  S.ctx.updatedAt=Date.now();
  paintCtxMeter();paintBudget();
 }catch(e){}
}
function parseUnifiedDiff(text){
 const lines=String(text||"").split("\n");
 const hunks=[];let cur=null;let path="";
 for(const line of lines){
 const mp=line.match(/^\+\+\+\s+(?:b\/)?(.+)/)||line.match(/^diff --git a\/.+ b\/(.+)/);
 if(mp){path=mp[1].trim();continue}
 if(line.startsWith("@@")){cur={path,header:line,lines:[]};hunks.push(cur);continue}
 if(!cur)continue;
 if(line.startsWith("+")&&!line.startsWith("+++"))cur.lines.push({t:"add",v:line.slice(1)});
 else if(line.startsWith("-")&&!line.startsWith("---"))cur.lines.push({t:"del",v:line.slice(1)});
 else if(line.startsWith("\\"))continue;
 else cur.lines.push({t:"ctx",v:line.startsWith(" ")?line.slice(1):line});
 }
 return hunks;
}
function renderDiffBlock(text,pathHint){
 const wrap=document.createElement("div");wrap.className="diff-view";
 const hunks=parseUnifiedDiff(text);
 if(!hunks.length){
 const pre=document.createElement("pre");pre.className="out";pre.textContent=text.slice(0,8000);wrap.appendChild(pre);return wrap;
 }
 hunks.forEach((h,hi)=>{
 const box=document.createElement("div");box.className="diff-hunk";
 const head=document.createElement("div");head.className="diff-head";
 const p=h.path||pathHint||"file";
 head.innerHTML="<span class='spoiler-path'>"+esc(p)+"</span> <code>"+esc(h.header||"")+"</code>";
 const body=document.createElement("pre");body.className="diff-body";
 h.lines.forEach(L=>{
 const row=document.createElement("div");row.className="diff-line diff-"+L.t;
 row.textContent=(L.t==="add"?"+":L.t==="del"?"-":" ")+L.v;body.appendChild(row);
 });
 const acts=document.createElement("div");acts.className="diff-acts";
 const acc=document.createElement("button");acc.type="button";acc.className="ok";acc.textContent="Accept hunk -> apply";
 acc.onclick=async()=>{
 try{
 await applyHunkToFile(p,h);
 acc.textContent="Applied";acc.disabled=true;chip("diff applied - "+p);
 }catch(e){alert(e)}
 };
 const rej=document.createElement("button");rej.type="button";rej.textContent="Reject";
 rej.onclick=()=>{box.classList.add("rejected");acc.disabled=true;rej.disabled=true};
 acts.appendChild(acc);acts.appendChild(rej);
 box.appendChild(head);box.appendChild(body);box.appendChild(acts);wrap.appendChild(box);
 });
 return wrap;
}
async function applyHunkToFile(path,hunk){
 const rel=path.replace(/^(\[file\]\s*|file\s*)/, "");
 let content="";
 try{
 const j=await jfetch("/api/fs/read?path="+encodeURIComponent(rel));
 if(j.binary)throw new Error("binary file");
 content=j.content||"";
 }catch(e){content=""}
 const lines=content.split("\n");
 const m=(hunk.header||"").match(/@@\s+-(\d+)(?:,\d+)?\s+\+(\d+)(?:,\d+)?\s+@@/);
 let oldStart=m?Math.max(1,+m[1]):1;
 let i=oldStart-1;
 const out=lines.slice(0,i);
 let ri=i;
 for(const L of hunk.lines){
 if(L.t==="ctx"){
 out.push(L.v);ri++;
 }else if(L.t==="del"){ri++}
 else if(L.t==="add"){out.push(L.v)}
 }
 out.push(...lines.slice(ri));
 const body=out.join("\n");
 const r=await fetch("/api/fs/write",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path:rel,content:body})});
 if(!r.ok)throw new Error(await r.text());
}
let termPaintRaf=0,termDirty=false,termLastPaint=0;
function pushTerm(line,meta){
 if(window.replaying||window.sessionSwitching)return;
 const quiet=meta&&meta.quiet;
 const text=String(line||"").replace(/\r/g,"").slice(0,800);
 if(!text.trim())return;
 const last=S.termLines[S.termLines.length-1];
 if(last&&last.line===text)return;
 S.termLines.push({t:Date.now(),line:text,meta:meta||{}});
 if(S.termLines.length>120)S.termLines=S.termLines.slice(-80);
 termDirty=true;
 scheduleTermPaint();
 if(!quiet){
 const pane=$("termPane");
 if(pane&&pane.classList.contains("on")){/* already open */}
 else{
 const btn=$("btnTerm");
 if(btn){btn.classList.add("btn-term-hot");btn.title="Terminal stream (new output)"}
 }
 }else{
 const btn=$("btnTerm");
 if(btn){btn.classList.add("btn-term-hot");btn.title="Terminal stream (new output)"}
 }
}
function scheduleTermPaint(){
 if(termPaintRaf)return;
 termPaintRaf=requestAnimationFrame(()=>{
 termPaintRaf=0;
 const now=Date.now();
 if(now-termLastPaint<120){termPaintRaf=requestAnimationFrame(()=>{termPaintRaf=0;paintTerm()});return}
 paintTerm();
 });
}
function paintTerm(){
 if(!termDirty)return;
 termDirty=false;termLastPaint=Date.now();
 const el=$("termOut");if(!el)return;
 const pane=$("termPane");
 if(!pane||!pane.classList.contains("on"))return;
 el.textContent=S.termLines.map(x=>x.line).join("\n");
 el.scrollTop=el.scrollHeight;
}
function trackBg(task){
 const id=task.id||task.taskId||Math.random().toString(36).slice(2);
 let t=S.bgTasks.find(x=>x.id===id);
 if(!t){t={id,title:task.title||"background",status:task.status||"running",at:Date.now()};S.bgTasks.unshift(t)}
 else Object.assign(t,task,{at:Date.now()});
 S.bgTasks=S.bgTasks.slice(0,30);
 paintBg();
 if(window.Notification&&Notification.permission==="granted"&&/complete|done|fail/i.test(t.status||"")){
 try{new Notification("Grok task "+t.status,{body:t.title})}catch(e){}
 }
}
function paintBg(){
 const el=$("bgList");if(!el)return;
 el.innerHTML="";
 if(!S.bgTasks.length){el.innerHTML="<div class='hint'>No background tasks</div>";return}
 S.bgTasks.forEach(t=>{
 const d=document.createElement("div");d.className="bg-item";
 d.innerHTML="<b>"+esc(t.title)+"</b> <span class='badge'>"+esc(t.status)+"</span>";
 const c=document.createElement("button");c.type="button";c.textContent="Cancel";
 c.onclick=()=>cancelBg(t.id);
 d.appendChild(c);el.appendChild(d);
 });
}
async function cancelBg(id){
 try{
 if(window.ws&&window.ws.readyState===1&&window.sid){
 const nid=typeof window.nextId==="function"?window.nextId():Date.now();
 window.ws.send(JSON.stringify({jsonrpc:"2.0",id:nid,method:"session/cancel",params:{sessionId:window.sid,taskId:id}}));
 }
 }catch(e){}
 trackBg({id,status:"cancel-requested"});
 chip("cancel requested - "+id);
}
function openAtPicker(){
 const sheet=$("atSheet");if(!sheet)return;
 sheet.classList.add("on");
 loadAtList(".");
}
async function loadAtList(rel){
 const tree=$("atTree");if(!tree)return;
 tree.innerHTML="<div class='hint'>loading...</div>";
 try{
 const j=await jfetch("/api/fs/list?path="+encodeURIComponent(rel||"."));
 tree.innerHTML="";
 if(j.parent!=null){
 const up=document.createElement("div");up.className="ide-item";up.textContent="^ ..";
 up.onclick=()=>loadAtList(j.parent);tree.appendChild(up);
 }
 (j.dirs||[]).forEach(d=>{
 const el=document.createElement("div");el.className="ide-item ide-dir";el.textContent="[dir] "+d.name;
 el.onclick=()=>loadAtList(d.rel);tree.appendChild(el);
 });
 (j.files||[]).forEach(f=>{
 const el=document.createElement("div");el.className="ide-item";el.textContent="[file] "+f.name;
 el.onclick=()=>attachAtFile(f);tree.appendChild(el);
 });
 }catch(e){tree.innerHTML="<div class='hint'>"+esc(e)+"</div>"}
}
async function attachAtFile(f){
 try{
 const j=await jfetch("/api/fs/read?path="+encodeURIComponent(f.rel));
 if(j.binary||j.text===false){chip("binary - path only");insertAtMention(f.rel);return}
 if(!window._atFiles)window._atFiles=[];
 window._atFiles.push({rel:f.rel,name:f.name,content:j.content||"",mime:j.mimeType||"text/plain"});
 paintAtChips();
 insertAtMention(f.rel);
 chip("attached @"+f.rel);
 }catch(e){alert(e)}
 const sheet=$("atSheet");if(sheet)sheet.classList.remove("on");
}
function insertAtMention(rel){
 const box=$("box");if(!box)return;
 const ins="@"+rel+" ";
 box.value=(box.value?box.value+" ":"")+ins;
 box.focus();
}
function paintAtChips(){
 const bar=$("atAttachBar");if(!bar)return;
 bar.innerHTML="";
 (window._atFiles||[]).forEach((f,i)=>{
 const s=document.createElement("span");s.className="att-chip";
 s.innerHTML="<b class='spoiler-path'>@"+esc(f.rel)+"</b><button type='button'>x</button>";
 s.querySelector("button").onclick=()=>{window._atFiles.splice(i,1);paintAtChips()};
 bar.appendChild(s);
 });
}
function consumeAtFilesIntoBlocks(blocks){
 const files=window._atFiles||[];
 if(!files.length)return blocks;
 files.forEach(f=>{
 blocks.push({type:"resource",resource:{uri:"file:///"+f.rel.replace(/\\/g,"/"),mimeType:f.mime||"text/plain",text:f.content}});
 blocks.push({type:"text",text:"Attached workspace file `"+f.rel+"`:\n```\n"+String(f.content).slice(0,120000)+"\n```"});
 });
 window._atFiles=[];paintAtChips();
 return blocks;
}
function searchChat(q){
 q=String(q||"").toLowerCase().trim();
 const feed=$("feed");if(!feed)return;
 feed.querySelectorAll(".search-hit").forEach(el=>el.classList.remove("search-hit"));
 if(!q)return;
 let first=null;
 [...feed.children].forEach(row=>{
 const t=(row.textContent||"").toLowerCase();
 if(t.includes(q)){row.classList.add("search-hit");if(!first)first=row}
 });
 if(first)first.scrollIntoView({block:"center",behavior:"smooth"});
}
function checkpointNow(){
 const feed=$("feed");if(!feed)return;
 const html=feed.innerHTML;
 const snap={id:Date.now(),sid:window.sid||null,at:new Date().toISOString(),html:html.slice(0,500000),label:"before turn - "+new Date().toLocaleTimeString()};
 S.checkpoints.unshift(snap);S.checkpoints=S.checkpoints.slice(0,8);
 try{localStorage.setItem("grok_remote_checkpoints",JSON.stringify(S.checkpoints.map(c=>({id:c.id,sid:c.sid,at:c.at,label:c.label,html:c.html.slice(0,200000)}))))}catch(e){}
 paintCheckpoints();chip("checkpoint saved");
}
function paintCheckpoints(){
 const el=$("cpList");if(!el)return;
 el.innerHTML="";
 S.checkpoints.forEach(c=>{
 const d=document.createElement("div");d.className="bg-item";
 d.innerHTML="<b>"+esc(c.label)+"</b>";
 const b=document.createElement("button");b.type="button";b.textContent="Restore view";
 b.onclick=()=>{const feed=$("feed");if(feed){feed.innerHTML=c.html;chip("restored local view (not agent memory)")}};
 d.appendChild(b);el.appendChild(d);
 });
}
function exportChat(kind){
 const feed=$("feed");if(!feed)return;
 const priv=document.body.classList.contains("privacy");
 if(!priv)document.body.classList.add("privacy");
 const title="Grok Remote export "+new Date().toISOString();
 if(kind==="html"||!kind){
 const html="<!doctype html><meta charset=utf-8><title>"+esc(title)+"</title><style>body{font:14px system-ui;background:#111;color:#eee;padding:16px} .spoiler,.spoiler-path{filter:blur(6px)}</style><h1>"+esc(title)+"</h1>"+feed.innerHTML;
 const blob=new Blob([html],{type:"text/html"});
 const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="grok-remote-chat.html";a.click();
 }
 if(kind==="png"){
 chip("PNG: use OS screenshot with Spoiler on (spoiler) - full DOM raster needs extra deps");
 }
 if(!priv)document.body.classList.remove("privacy");
 chip("export ready");
}
function startVoice(){
 const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(!SR){alert("Speech recognition not supported in this browser");return}
 if(S.voice){try{S.voice.stop()}catch(e){}S.voice=null;paintVoice(false);return}
 const r=new SR();r.lang="en-US";r.continuous=true;r.interimResults=true;
 let final="";
 r.onresult=e=>{
 let inter="";
 for(let i=e.resultIndex;i<e.results.length;i++){
 const t=e.results[i][0].transcript;
 if(e.results[i].isFinal)final+=t+" ";else inter+=t;
 }
 const box=$("box");if(box)box.value=(final+inter).trim();
 };
 r.onerror=()=>{paintVoice(false);S.voice=null};
 r.onend=()=>{paintVoice(false);S.voice=null};
 S.voice=r;r.start();paintVoice(true);
 if(window.Notification&&Notification.permission==="default")Notification.requestPermission().catch(()=>{});
}
function paintVoice(on){const b=$("btnVoice");if(b)b.classList.toggle("on",!!on)}
function setupReconnect(){
 let timer=null;
 const orig=window.connect;
 // observe ws close via interval
 setInterval(()=>{
 const ws=window.ws;
 if(!ws)return;
 if(ws.readyState===3){
 if(timer)return;
 timer=setTimeout(async()=>{
 timer=null;S.reconnects++;
 chip("reconnecting... #"+S.reconnects);
 try{
 if(typeof window.connect==="function")await window.connect();
 const want=window.sid;
 if(want&&typeof window.fetchSessions==="function"){
 await window.fetchSessions();
 const s=(window.sessions||[]).find(x=>x.sessionId===want);
 if(s&&typeof window.openSession==="function")await window.openSession(s);
 }
 chip("reconnected");
 }catch(e){chip("reconnect failed")}
 },1200);
 }
 },2000);
}
function pinSession(s){
 if(!s||!s.sessionId)return;
 if(S.pinned.some(p=>p.sessionId===s.sessionId))return;
 S.pinned.unshift({sessionId:s.sessionId,title:s.title||s.sessionId.slice(0,8),cwd:s.cwd||""});
 savePins();paintPins();
}
function paintPins(){
 const el=$("pinBar");if(!el)return;
 el.innerHTML="";
 S.pinned.forEach((p,i)=>{
 const b=document.createElement("button");b.type="button";b.className="pin-chip";
 b.textContent=p.title||p.sessionId.slice(0,8);
 b.onclick=async()=>{
 const s=(window.sessions||[]).find(x=>x.sessionId===p.sessionId)||p;
 if(typeof window.openSession==="function")await window.openSession(s);
 };
 b.oncontextmenu=e=>{e.preventDefault();S.pinned.splice(i,1);savePins();paintPins()};
 el.appendChild(b);
 });
}
function openDelve(){
 const base=location.origin.replace(/2421/,"8787");
 const urls=["http://127.0.0.1:8787/","http://127.0.0.1:8080/delve","/delve"];
 if(window.grokRemote&&window.grokRemote.openExternal)window.grokRemote.openExternal(urls[0]);
 else window.open(urls[0],"_blank");
 chip("delve - opened local hub if running");
}
function stopTurn(){
 try{
 if(!window.ws||window.ws.readyState!==1||!window.sid){chip("nothing to stop");return}
 const nid=typeof window.nextId==="function"?window.nextId():Date.now();
 window.ws.send(JSON.stringify({jsonrpc:"2.0",id:nid,method:"session/cancel",params:{sessionId:window.sid}}));
 if(typeof window.setBusy==="function")window.setBusy(false);
 chip("stop - cancel sent");
 }catch(e){chip("stop failed: "+e)}
}
async function refreshGit(){
 const el=$("gitStrip");if(!el)return;
 try{
 const j=await jfetch("/api/git/status");
 S.git=j;
 if(!j.git){el.innerHTML="<span class='git-muted'>not a git repo</span>";el.classList.remove("dirty");return}
 const bits=["<b class='git-branch'>"+esc(j.branch||"?")+"</b>"];
 if(j.sha)bits.push("<span class='git-sha'>"+esc(j.sha)+"</span>");
 bits.push("<span class='"+(j.dirty?"git-dirty":"git-clean")+"'>"+(j.dirty?j.dirty+" dirty":"clean")+"</span>");
 if(j.ahead)bits.push("<span class='git-ahead'>^"+j.ahead+"</span>");
 if(j.behind)bits.push("<span class='git-behind'>v"+j.behind+"</span>");
 el.innerHTML=bits.join(" - ");
 el.classList.toggle("dirty",!!j.dirty);
 el.title=(j.files||[]).slice(0,20).map(f=>(f.code||"")+" "+f.path).join("\n")||j.branch;
 }catch(e){el.innerHTML="<span class='git-muted'>git offline</span>";el.title=String(e&&e.message||e)}
}
async function showGitDiff(){
 try{
 const j=await jfetch("/api/git/diff");
 const feed=$("feed");if(!feed)return;
 const row=document.createElement("div");row.className="row";
 const nm=document.createElement("div");nm.className="nm";nm.textContent="Git diff - working tree";
 const bub=document.createElement("div");bub.className="bub";
 if(j.diff&&window.grokCockpit)bub.appendChild(renderDiffBlock(j.diff,"working-tree"));
 else{const pre=document.createElement("pre");pre.className="out";pre.textContent=j.diff||"(no diff)";bub.appendChild(pre)}
 row.appendChild(nm);row.appendChild(bub);feed.appendChild(row);
 try{feed.scrollTop=feed.scrollHeight}catch(e){}
 chip("git diff loaded");
 }catch(e){alert(e)}
}
function paintCtxMeter(){
 const el=$("ctxMeter");if(!el)return;
 el.style.display="";
 const used=S.ctx.used||0;
 const win=S.ctx.window||500000;
 let pct=S.ctx.usage!=null?Math.min(100,Math.round(+S.ctx.usage)):0;
 if(!pct&&used&&win)pct=Math.min(100,Math.round(100*used/win));
 if(!used&&!S.ctx.usage&&S.ctx.source==="idle"){
  el.style.setProperty("--ctx","0%");
  el.title="Context — open a session (reads session signals)";
  el.innerHTML="<i></i><span>ctx —</span>";
  el.classList.remove("hot","warn");
  return;
 }
 el.style.setProperty("--ctx",pct+"%");
 const src=S.ctx.source==="signals"?"session":(S.ctx.source==="stream"?"live":"est");
 el.title=fmtTok(used)+" / "+fmtTok(win)+" tokens ("+pct+"%) · "+src+(S.ctx.model?" · "+S.ctx.model:"");
 el.innerHTML="<i></i><span>ctx "+pct+"%</span>";
 el.classList.toggle("hot",pct>=80);el.classList.toggle("warn",pct>=55&&pct<80);
}
function syncTodosFromPlan(steps){
 if(!Array.isArray(steps)||!steps.length)return;
 S.todos=steps.map((s,i)=>({id:"p"+i+"-"+Date.now(),text:s.text||s,status:s.status||"pending"}));
 paintTodos();
}
function upsertTodo(item){
 if(!item||!item.text)return;
 const id=item.id||("t"+Date.now());
 let t=S.todos.find(x=>x.id===id||x.text===item.text);
 if(!t){t={id,text:item.text,status:item.status||"pending"};S.todos.push(t)}
 else Object.assign(t,item);
 S.todos=S.todos.slice(-40);
 paintTodos();
}
function paintTodos(){
 const el=$("todoList");if(!el)return;
 el.innerHTML="";
 if(!S.todos.length){el.innerHTML="<div class='hint'>No todos - approve a plan or add one</div>";paintTodoBadge();return}
 S.todos.forEach((t,i)=>{
 const d=document.createElement("label");d.className="todo-item"+(t.status==="done"?" done":"")+(t.status==="blocked"?" blocked":"");
 const cb=document.createElement("input");cb.type="checkbox";cb.checked=t.status==="done";
 cb.onchange=()=>{t.status=cb.checked?"done":"pending";paintTodos()};
 const sp=document.createElement("span");sp.textContent=t.text;
 d.appendChild(cb);d.appendChild(sp);el.appendChild(d);
 });
 paintTodoBadge();
 try{localStorage.setItem("grok_remote_todos",JSON.stringify(S.todos.slice(-40)))}catch(e){}
}
function paintTodoBadge(){
 const b=$("btnTodo");if(!b)return;
 const open=S.todos.filter(t=>t.status!=="done").length;
 b.textContent=open?"todo "+open:"todo";
 b.classList.toggle("on",open>0);
}
function openLocInIde(path){
 if(!path)return;
 const rel=String(path).replace(/^(\[file\]\s*|file\s*)/i,"").replace(/\\/g,"/").trim();
 if(window.grokIde&&window.grokIde.noteAgentFiles)window.grokIde.noteAgentFiles([rel],{wrote:false,autoOpen:false});
 if(window.grokIde&&window.grokIde.openFile){
  window.grokIde.openFile(rel,{forceReload:true}).catch(e=>chip(String(e)));
  if(window.grokIde.show)window.grokIde.show(true);
 }else chip("IDE not ready · "+rel);
}
async function injectProjectContext(){
 try{
 const j=await jfetch("/api/project/context");
 const box=$("box");if(!box)return;
 const files=(j.files||[]).filter(f=>/agents|claude|cursor/i.test(f.name));
 if(!files.length){chip("no AGENTS.md / CLAUDE.md found");return}
 const f=files[0];
 box.value=(box.value?box.value+"\n\n":"")+"Project instructions from `"+f.name+"`:\n```\n"+(f.preview||"").slice(0,6000)+"\n```\nFollow these unless I override.";
 chip("injected "+f.name);box.focus();
 }catch(e){alert(e)}
}
function bindSlashComplete(){
 const box=$("box");const menu=$("slashMenu");if(!box||!menu)return;
 const hide=()=>{menu.classList.remove("on");menu.innerHTML=""};
 box.addEventListener("input",()=>{
 const v=box.value;
 if(!v.startsWith("/")||v.includes(" ")||v.includes("\n")){hide();return}
 const q=v.slice(1).toLowerCase();
 const cmds=(window.commands||[]).concat([
 {name:"compact",description:"Ask agent to compact context"},
 {name:"clear",description:"Local: clear chat view (session stays)"},
 {name:"cost",description:"Show local budget / context estimate"},
 {name:"diff",description:"Load working-tree git diff into chat"},
 {name:"stop",description:"Cancel current turn"},
 {name:"agents",description:"Inject AGENTS.md / CLAUDE.md into composer"}
 ]);
 const seen=new Set();
 const hits=cmds.filter(c=>{
 const n=(c.name||"").replace(/^(\[file\]\s*|file\s*)/, "");
 if(seen.has(n))return false;seen.add(n);
 return !q||n.toLowerCase().includes(q)||String(c.description||"").toLowerCase().includes(q);
 }).slice(0,12);
 if(!hits.length){hide();return}
 menu.innerHTML="";
 hits.forEach(c=>{
 const n=(c.name||"").replace(/^(\[file\]\s*|file\s*)/, "");
 const d=document.createElement("div");d.className="slash-item";
 d.innerHTML="<b>/"+esc(n)+"</b><span>"+esc(c.description||"")+"</span>";
 d.onclick=()=>{box.value="/"+n+" ";menu.classList.remove("on");box.focus();box.dispatchEvent(new Event("input"))};
 menu.appendChild(d);
 });
 menu.classList.add("on");
 });
 box.addEventListener("keydown",e=>{
 if(e.key==="Escape"){hide();return}
 if(e.key!=="Enter"||e.shiftKey)return;
 const tv=box.value.trim();
 if(tv==="/clear"){e.preventDefault();hide();const feedEl=$("feed");if(feedEl)feedEl.innerHTML="";box.value="";chip("local view cleared");return}
 if(tv==="/cost"){e.preventDefault();hide();box.value="";paintCtxMeter();paintBudget();chip($("ctxMeter")?$("ctxMeter").title:"cost");return}
 if(tv==="/diff"){e.preventDefault();hide();box.value="";showGitDiff();return}
 if(tv==="/stop"){e.preventDefault();hide();box.value="";stopTurn();return}
 if(tv==="/agents"){e.preventDefault();hide();box.value="";injectProjectContext();return}
 if(tv.startsWith("/compact")){
 e.preventDefault();hide();
 box.value="Compact this session: summarize durable decisions, open tasks, and key file paths. Drop redundant chat. Keep actionable next steps.";
 }
 });
 document.addEventListener("click",e=>{if(!menu.contains(e.target)&&e.target!==box)hide()});
}
function enhanceBubbles(){
 const feed=$("feed");if(!feed||feed._copyObs)return;
 const addCopy=row=>{
 if(!row||row.querySelector(".row-acts"))return;
 if(!row.classList||!row.classList.contains("row"))return;
 const acts=document.createElement("div");acts.className="row-acts";
 const b=document.createElement("button");b.type="button";b.className="row-copy";b.textContent="Copy";
 b.onclick=async e=>{
 e.stopPropagation();
 const bub=row.querySelector(".bub");
 const t=bub?(bub.innerText||bub.textContent||""):row.innerText;
 try{await navigator.clipboard.writeText(t);chip("copied")}catch(err){chip("copy failed")}
 };
 acts.appendChild(b);row.appendChild(acts);
 };
 feed.querySelectorAll(".row").forEach(addCopy);
 const mo=new MutationObserver(muts=>{
 muts.forEach(m=>m.addedNodes.forEach(n=>{
 if(n.nodeType===1){
 if(n.classList&&n.classList.contains("row"))addCopy(n);
 n.querySelectorAll&&n.querySelectorAll(".row").forEach(addCopy);
 }
 }));
 });
 mo.observe(feed,{childList:true,subtree:true});
 feed._copyObs=mo;
}
function wireToolPathClicks(){
 const feed=$("feed");if(!feed||feed._locClick)return;
 feed.addEventListener("click",e=>{
 const loc=e.target.closest&&e.target.closest(".loc");
 if(!loc)return;
 const t=(loc.textContent||"").replace(/^(\[file\]\s*|file\s*)/, "").trim();
 if(t)openLocInIde(t);
 });
 feed._locClick=true;
}
function injectChrome(){
  if($("cockpitBar")||$("toolsRow"))return;
  const foot=$("foot");
  if(!foot)return;
  const host=$("composerTools")||(()=>{const d=document.createElement("div");d.id="composerTools";d.className="composer-tools";const comp=foot.querySelector(".composer");if(comp)foot.insertBefore(d,comp);else foot.appendChild(d);return d})();
  const owner=!!(window.grokPresets&&window.grokPresets.ownerUnlocked&&window.grokPresets.ownerUnlocked());
  host.innerHTML=
    '<div class="git-strip" id="gitStrip" title="Git branch status — tap to refresh">git …</div>'+
    '<div class="pin-bar" id="pinBar" title="Pinned sessions"></div>'+
    '<div class="tools-row" id="toolsRow">'+
      '<span class="tools-group-lab">Chat</span>'+
      '<button type="button" class="btn-attach" id="btnAttach" title="Attach photos or files to your next message">Attach files</button>'+
      '<button type="button" id="btnAt" title="Pick a workspace file path to include">Add path</button>'+
      '<button type="button" id="btnVoice" title="Dictate with the microphone">Voice</button>'+
      '<span class="tools-group-lab">Work</span>'+
      '<button type="button" id="btnTodo" title="Checklist for this session">Todos</button>'+
      '<button type="button" id="btnTerm" title="Show recent shell/tool output">Terminal</button>'+
      '<button type="button" id="btnGitDiff" title="Show uncommitted git changes">Git diff</button>'+
      '<button type="button" id="btnBg" title="Background tasks and save-points">Tasks</button>'+
      '<span class="tools-group-lab">Share</span>'+
      '<button type="button" id="btnCp" title="Snapshot this chat so you can restore later">Save point</button>'+
      '<button type="button" id="btnExport" title="Download chat as HTML">Export</button>'+
      '<button type="button" id="btnAgents" title="Paste project AGENTS.md / README into context">Project MD</button>'+
      '<button type="button" id="btnBudget" title="Soft limits for turns and tokens">Limits</button>'+
      (owner?'<button type="button" id="btnDelve" title="Open local Delve hub (owner)">Delve</button>':'')+
      '<span id="budgetBar" class="budget-bar" title="Turn / context estimate">cost</span>'+
    '</div>'+
    '<div id="atAttachBar" class="attach-bar"></div>';
  const floatHost=document.createElement("div");floatHost.id="cockpitFloats";
  floatHost.innerHTML=
    '<div id="todoPane" class="side-pane cockpit-float"><div class="term-head">Todos <button type="button" id="todoClose">x</button></div><div id="todoList"></div><div class="rowbtns" style="padding:8px"><button type="button" id="todoAdd">+ Todo</button><button type="button" id="todoClearDone">Clear done</button></div></div>'+
    '<div id="termPane" class="term-pane cockpit-float"><div class="term-head">Terminal <button type="button" id="termClose">x</button></div><pre id="termOut"></pre></div>'+
    '<div id="bgPane" class="side-pane cockpit-float"><div class="term-head">Background <button type="button" id="bgClose">x</button></div><div id="bgList"></div><div class="term-head">Checkpoints</div><div id="cpList"></div></div>';
  document.body.appendChild(floatHost);
  if(!$("slashMenu")){
    const sm=document.createElement("div");sm.id="slashMenu";sm.className="slash-menu";
    const comp=foot.querySelector(".composer");
    if(comp){comp.style.position="relative";comp.appendChild(sm)}
    else foot.appendChild(sm);
  }
  const orphanStop=$("btnStop");
  if(orphanStop&&orphanStop.parentNode)orphanStop.parentNode.removeChild(orphanStop);
  if(!$("ctxMeter")){
    const col=foot.querySelector(".composer-sendcol");
    if(col){
      const m=document.createElement("span");m.id="ctxMeter";m.className="ctx-meter ctx-send";m.title="Context estimate";
      m.innerHTML="<i></i><span>ctx</span>";
      col.insertBefore(m,col.firstChild);
    }
  }
  const atSheet=document.createElement("div");atSheet.className="sheet";atSheet.id="atSheet";
  atSheet.innerHTML='<div class="card"><h3>@ workspace file <button type="button" class="sheet-x" id="atClose">x</button></h3><p class="hint">Browse PC workspace and attach to the next prompt.</p><div id="atTree" class="ide-tree" style="max-height:50vh"></div></div>';
  document.body.appendChild(atSheet);
  const reflow=()=>{if(window.updateJump)window.updateJump();if(window.measureBottomStack)window.measureBottomStack()};
  const topSearch=$("chatTopSearch")||$("chatSearch");
  if(topSearch)topSearch.oninput=e=>searchChat(e.target.value);
  if($("btnAttach")&&window.wireAttachButton)try{window.wireAttachButton()}catch(e){}
  else if($("btnAttach")&&$("filePick"))$("btnAttach").onclick=()=>$("filePick").click();
  $("btnAt").onclick=()=>openAtPicker();
  $("btnVoice").onclick=()=>startVoice();
  $("btnCp").onclick=()=>checkpointNow();
  $("btnExport").onclick=()=>exportChat("html");
  $("btnTerm").onclick=()=>{
    const p=$("termPane");if(!p)return;
    p.classList.toggle("on");
    $("btnTerm").classList.remove("btn-term-hot");
    if(p.classList.contains("on")){termDirty=true;paintTerm()}
    reflow();
  };
  $("btnBg").onclick=()=>{$("bgPane").classList.toggle("on");paintBg();paintCheckpoints();reflow()};
  $("btnTodo").onclick=()=>{$("todoPane").classList.toggle("on");paintTodos();reflow()};
  $("todoClose").onclick=()=>{$("todoPane").classList.remove("on");reflow()};
  $("todoAdd").onclick=()=>{const t=prompt("Todo");if(t)upsertTodo({text:t,status:"pending"})};
  $("todoClearDone").onclick=()=>{S.todos=S.todos.filter(t=>t.status!=="done");paintTodos()};
  $("btnGitDiff").onclick=()=>showGitDiff();
  $("btnAgents").onclick=()=>injectProjectContext();
  $("gitStrip").onclick=()=>refreshGit();
  $("btnBudget").onclick=()=>{
    const t=prompt("Max turns (0=off)",String(S.budget.maxTurns||0));
    if(t===null)return;
    const k=prompt("Max est. tokens (0=off)",String(S.budget.maxEstTokens||0));
    if(k===null)return;
    S.budget.maxTurns=+t||0;S.budget.maxEstTokens=+k||0;saveBudget();paintBudget();paintCtxMeter();
  };
  if($("btnDelve"))$("btnDelve").onclick=()=>openDelve();
  $("termClose").onclick=()=>{$("termPane").classList.remove("on");reflow()};
  $("bgClose").onclick=()=>{$("bgPane").classList.remove("on");reflow()};
  $("atClose").onclick=()=>$("atSheet").classList.remove("on");
  atSheet.addEventListener("click",e=>{if(e.target===atSheet)$("atSheet").classList.remove("on")});
  const ctx=$("ctxMeter");
  if(ctx&&!ctx._wired){
    ctx.onclick=()=>{
      refreshSessionContext().finally(()=>{
        const used=S.ctx.used||0,win=S.ctx.window||500000;
        const pct=win?Math.round(100*used/win):(S.ctx.usage||0);
        alert("Context window\n\n"+fmtTok(used)+" / "+fmtTok(win)+" tokens ("+pct+"%)\nSource: "+(S.ctx.source||"?")+(S.ctx.model?"\nModel: "+S.ctx.model:"")+"\nTurns: "+(S.budget.turns||0)+"\n\nUses session signals.json (same as Grok Build), not feed-length guesses.");
      });
    };
    ctx._wired=true;
  }
  paintPins();paintBudget();paintBg();paintCheckpoints();paintTodos();paintCtxMeter();refreshGit();
  bindSlashComplete();enhanceBubbles();wireToolPathClicks();
  setInterval(()=>{refreshGit();refreshSessionContext();paintCtxMeter()},12000);
  setTimeout(()=>refreshSessionContext(),400);
  try{S.checkpoints=safeParse(localStorage.getItem("grok_remote_checkpoints"),[])}catch(e){}
  try{S.todos=safeParse(localStorage.getItem("grok_remote_todos"),[])}catch(e){S.todos=[]}
  if(!Array.isArray(S.todos))S.todos=[];
  paintTodos();
  setTimeout(reflow,30);setTimeout(reflow,300);
}

window.grokCockpit={
 S,renderDiffBlock,pushTerm,trackBg,consumeAtFilesIntoBlocks,noteUsage,noteContextFromMeta,pinSession,checkpointNow,
 isAlwaysPerm(key){return !!S.alwaysPerm[key]},
 setAlwaysPerm(key,v){if(v)S.alwaysPerm[key]=1;else delete S.alwaysPerm[key];saveAlways()},
 openAtPicker,searchChat,exportChat,startVoice,stopTurn,refreshGit,showGitDiff,paintCtxMeter,refreshSessionContext,
 syncTodosFromPlan,upsertTodo,openLocInIde,injectProjectContext
};
function boot(){
 loadState();
 injectChrome();
 setupReconnect();
 paintBudget();
 paintCtxMeter();
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);else boot();
})();
