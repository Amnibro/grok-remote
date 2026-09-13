export function toolSummary(u){
 const raw=u&&(u.rawInput||u.input)||{};
 const r=typeof raw==="string"?(()=>{try{return JSON.parse(raw)}catch(e){return {text:raw}}})():raw;
 const pick=["command","cmd","target_file","file_path","path","pattern","query","url","glob","name","text"].map(k=>r&&r[k]).find(v=>typeof v==="string"&&v.trim());
 const s=String(pick||"").replace(/\\\\/g,"\\").replace(/\s+/g," ").trim();
 return s.length>96?s.slice(0,93)+"…":s;
}
export function toolLabel(u){
 const t=String(u&&(u.title||u.kind||u.toolName||u.tool)||"tool").replace(/[`*]/g,"").replace(/_/g," ").replace(/\s+/g," ").trim();
 const w=t.split(" "),w1=(w[1]||"").replace(/:$/,"");
 return (w1&&/^[a-z_]+$/i.test(w1)?w[0]+" "+w1:w[0]).slice(0,40);
}
export function toolKind(u){
 const t=String(u&&(u.title||u.kind||u.toolName||u.tool)||"").toLowerCase();
 if(/read|fetch|search|grep|glob|list|view/.test(t))return "read";
 if(/write|edit|apply|patch|create|delete|save/.test(t))return "write";
 return "tool";
}
export function makeCoalescer(){
 const turns=[];let cur=null;
 const text=c=>Array.isArray(c)?c.map(b=>b&&b.text||"").join(""):(c&&c.text)||"";
 function push(kind,body,meta){
  if(cur&&cur.kind===kind&&kind!=="you"&&kind!=="noticed"&&kind!=="sys"){cur.body+=body;cur.n++;return cur}
  cur={kind,body,n:1,meta:meta||{},id:turns.length};turns.push(cur);return cur;
 }
 function tool(u){
  const id=String(u.toolCallId||u.id||"");
  const prev=id&&turns.find(t=>t.kind==="tool"&&t.meta.id===id);
  if(prev){if(u.status)prev.meta.status=u.status;if(u.title&&!prev.meta.title)prev.meta.title=toolLabel(u);prev.updated=true;cur=null;return prev}
  cur=null;
  const t={kind:"tool",body:toolSummary(u),n:1,meta:{id,status:u.status||"",title:toolLabel(u),sub:toolKind(u)},id:turns.length};
  turns.push(t);return t;
 }
 function event(u){
  if(!u)return null;
  const k=u.sessionUpdate||u.type||"";
  if(k==="user_message_chunk"||k==="user_message"){const t=(text(u.content)||u.text||"").trim();if(!t)return null;if(/^\[Situation/i.test(t)){cur=null;return push("noticed",t.replace(/^\[Situation,?\s*(?:\d\d:\d\d,\s*)?not a message from him:\s*/i,"").split(/ React as/)[0].slice(0,140))}if(/^\[(AGENT SETUP|INTERJECT|You are in the room|You and Anthony were already talking)/i.test(t)){cur=null;const r=push("sys",t);cur=r;return r}const last=turns[turns.length-1];if(last&&cur===last&&last.kind==="sys"&&last.body.indexOf("]")<0){last.body+=t;last.n++;return last}const dup=turns.slice(-3).find(x=>x.kind==="you"&&(x.body===t||x.body.indexOf(t)>=0||t.indexOf(x.body)>=0));if(dup){if(t.length>dup.body.length)dup.body=t;return dup}if(last&&cur===last&&last.kind==="you"){last.body+=" "+t;last.n++;return last}cur=null;const r=push("you",t);cur=r;return r}
  if(k==="agent_message_chunk"||k==="agent_message"){const t=text(u.content);return t?push("her",t):null}
  if(k==="agent_thought_chunk"){const t=(u.content&&u.content.text)||u.text||"";return t?push("think",t):null}
  if(k==="tool_call"||k==="tool_call_update")return tool(u);
  return null;
 }
 return {event,turns,reset(){turns.length=0;cur=null}};
}
export function initHud(ctx){
 const KEY=ctx.KEY||"";
 const sessEl=document.getElementById("sessRail"),chatEl=document.getElementById("feedChat"),workEl=document.getElementById("feedWork");
 let selected="",liveSid="",pinned=false,co=makeCoalescer(),els=new Map(),rows=[];
 const clean=s=>String(s||"").replace(/\[\[[^\]]*\]\]/g," ").replace(/[*_`#>|]+/g,"").replace(/\s+/g," ").trim();
 function paint(t){
  const work=t.kind==="think"||t.kind==="tool";
  const host=work?workEl:chatEl;if(!host)return;
  let d=els.get(t.id);
  if(!d){d=document.createElement("div");d.className="xr-ev xr-ev-"+(t.kind==="tool"?t.meta.sub:t.kind);const k=document.createElement("div");k.className="k";const b=document.createElement("div");b.className="b";d.appendChild(k);d.appendChild(b);host.appendChild(d);els.set(t.id,d);while(host.children.length>140)host.removeChild(host.firstChild)}
  const k=d.firstChild,b=d.lastChild;
  if(t.kind==="tool"){k.textContent=t.meta.title;const st=String(t.meta.status||"").toLowerCase();d.dataset.status=st;k.innerHTML="";const lab=document.createElement("span");lab.textContent=t.meta.title;k.appendChild(lab);if(st){const c=document.createElement("span");c.className="xr-chip xr-chip-"+(/complete|done|success/.test(st)?"ok":/fail|error/.test(st)?"bad":"run");c.textContent=/complete|done|success/.test(st)?"done":/fail|error/.test(st)?"failed":"running";k.appendChild(c)}b.textContent=t.body||"";b.style.display=t.body?"":"none"}
  else if(t.kind==="think"){k.textContent="thinking";const s=clean(t.body);b.textContent=s.length>220?"…"+s.slice(-220):s}
  else if(t.kind==="sys"){k.textContent="setup";b.textContent=t.body.slice(0,120)+(t.body.length>120?"…":"")}
  else if(t.kind==="noticed"){k.textContent="she noticed";b.textContent=t.body}
  else{k.textContent=t.kind==="you"?"you":"her";const s=clean(t.body).slice(0,1200);b.textContent=s;d.style.display=s?"":"none"}
  host.scrollTop=host.scrollHeight;
 }
 function feed(u){const t=co.event(u);if(t)paint(t)}
 function clear(){co.reset();els=new Map();if(chatEl)chatEl.innerHTML="";if(workEl)workEl.innerHTML=""}
 function header(){
  if(!chatEl)return;
  let h=chatEl.parentElement.querySelector(".xr-viewing");
  if(!pinned||!selected||selected===liveSid){if(h)h.remove();return}
  if(!h){h=document.createElement("button");h.type="button";h.className="xr-viewing";h.onclick=()=>{pinned=false;showLive()};chatEl.parentElement.insertBefore(h,chatEl.parentElement.firstChild)}
  const row=rows.find(s=>String(s.sessionId)===selected);
  h.textContent="viewing: "+((row&&row.title)||selected.slice(0,8))+"  ·  back to her";
 }
 async function loadHistory(sid){
  clear();selected=sid;header();
  try{
   const cwd=(ctx.getCwd&&ctx.getCwd())||"";
   const j=await (await fetch("/api/session/history?sessionId="+encodeURIComponent(sid)+"&cwd="+encodeURIComponent(cwd)+"&limit=120",{cache:"no-store"})).json();
   for(const ev of (Array.isArray(j.events)?j.events:[]))feed((ev.params&&ev.params.update)||ev.update||ev);
  }catch(e){}
  mark();
 }
 function showLive(){if(!liveSid)return;if(selected===liveSid&&!pinned)return;loadHistory(liveSid);header()}
 function mark(){if(sessEl)[...sessEl.querySelectorAll("[data-sid]")].forEach(n=>n.classList.toggle("on",n.getAttribute("data-sid")===selected))}
 function live(kind,title,body){
  if(pinned&&selected&&selected!==liveSid)return;
  const map={you:{sessionUpdate:"user_message_chunk",content:{text:body}},her:{sessionUpdate:"agent_message_chunk",content:{text:body}},think:{sessionUpdate:"agent_thought_chunk",content:{text:body}}};
  const u=map[kind]||{sessionUpdate:"tool_call_update",title:title,status:(String(title).split(" · ")[1]||""),toolCallId:title};
  if(kind==="tool"||kind==="read"||kind==="write"){const parts=String(title).split(" · ");u.title=parts[0];u.status=parts[1]||"";u.toolCallId=parts[0]}
  feed(u);
 }
 function setLiveSid(id){liveSid=id||"";if(liveSid&&!pinned){selected=liveSid;clear();header()}refreshList()}
 const clusterKey=t=>String(t||"").toLowerCase().replace(/[^a-z0-9\s]/g," ").split(/\s+/).filter(Boolean).sort().join(" ");
 async function refreshList(){
  if(!sessEl)return;
  try{
   const j=await (await fetch("/api/sessions?limit=80",{cache:"no-store"})).json();
   let list=(j.sessions||[]).filter(s=>s&&s.sessionId);
   const ids=list.map(s=>String(s.sessionId));
   let kinds={};
   try{const t=await (await fetch("/api/session/titles",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({ids:ids.slice(0,80)})})).json();kinds=t.titles||{}}catch(e){}
   const seen={},out=[];
   for(const s of list){
    const id=String(s.sessionId),k=kinds[id]||{};
    if(k.kind==="auto"&&id!==liveSid)continue;
    const ck=clusterKey(s.title||k.title);
    if(ck&&ck.split(" ").length>=3){seen[ck]=(seen[ck]||0)+1;if(seen[ck]>1)continue}
    out.push(Object.assign({},s,{title:s.title||k.title||""}));
   }
   rows=out.slice(0,14);
   sessEl.innerHTML="";
   const h=document.createElement("div");h.className="xr-rail-h";h.textContent="Chats";sessEl.appendChild(h);
   if(liveSid&&!rows.some(s=>String(s.sessionId)===liveSid))rows.unshift({sessionId:liveSid,title:"her live session"});
   for(const s of rows){
    const id=String(s.sessionId);
    const b=document.createElement("button");b.type="button";b.className="xr-sess"+(id===selected?" on":"")+(id===liveSid?" live":"");
    b.setAttribute("data-sid",id);b.textContent=(id===liveSid?"● ":"")+(s.title||"Chat · "+id.slice(0,8));b.title=s.title||id;
    b.onclick=()=>{if(id===liveSid){pinned=false;showLive()}else{pinned=true;loadHistory(id)}};
    sessEl.appendChild(b);
   }
   header();
  }catch(e){}
 }
 let started=false;
 function start(){
  if(started)return;started=true;
  fetch("/config.json",{cache:"no-store"}).then(r=>r.json()).then(c=>{window.__cwd=c.cwd||"";refreshList()}).catch(()=>refreshList());
  setInterval(refreshList,20000);
 }
 return {start,live,setLiveSid,paintEvent:feed,add:live,refreshList,showLive,turns:()=>co.turns};
}
