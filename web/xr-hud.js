export function initHud(ctx){
  const KEY=ctx.KEY||"";
  const qk=KEY?"?key="+encodeURIComponent(KEY):"";
  const sessEl=document.getElementById("sessRail");
  const chatEl=document.getElementById("feedChat");
  const workEl=document.getElementById("feedWork");
  const esc=s=>String(s||"").replace(/[<>&]/g,c=>({"<":"&lt;",">":"&gt;","&":"&amp;"}[c]));
  let selected="",liveSid="";
  function trim(el,n){while(el&&el.children.length>(n||180))el.removeChild(el.firstChild)}
  function stick(el){if(el)el.scrollTop=el.scrollHeight}
  function add(kind,title,body){
    const work=kind==="think"||kind==="read"||kind==="write"||kind==="tool";
    const el=work?workEl:chatEl;
    if(!el)return;
    const d=document.createElement("div");
    d.className="xr-ev xr-ev-"+kind;
    const k=document.createElement("div");k.className="k";k.textContent=title||kind;
    d.appendChild(k);
    if(body){const b=document.createElement("div");b.className="b";b.textContent=String(body).slice(0,800);d.appendChild(b)}
    el.appendChild(d);trim(el,220);stick(el);
  }
  function toolKind(u){
    const t=String(u.title||u.kind||u.toolName||u.tool||"").toLowerCase();
    if(/read|fetch|search|grep|glob|list/.test(t))return "read";
    if(/write|edit|apply|patch|create|delete/.test(t))return "write";
    return "tool";
  }
  function paintEvent(u){
    if(!u)return;
    const k=u.sessionUpdate||u.type||"";
    if(k==="user_message_chunk"||k==="user_message"){
      let t="";const c=u.content;
      if(Array.isArray(c))t=c.map(b=>b&&b.text||"").join("");
      else if(c&&c.text)t=c.text;else t=u.text||"";
      if(t.trim())add("you","you",t.replace(/\s+/g," ").slice(0,400));
      return;
    }
    if(k==="agent_message_chunk"||k==="agent_message"){
      let t="";const c=u.content;
      if(Array.isArray(c))t=c.map(b=>b&&b.text||"").join("");
      else if(c&&c.text)t=c.text;
      if(t.trim())add("her","grok",t.replace(/\s+/g," ").slice(0,500));
      return;
    }
    if(k==="agent_thought_chunk"){
      let t=(u.content&&u.content.text)||u.text||"";
      if(t.trim())add("think","thinking",t.replace(/\s+/g," ").slice(0,400));
      return;
    }
    if(k==="tool_call"||k==="tool_call_update"){
      const title=u.title||u.kind||u.toolName||"tool";
      const st=u.status||"";
      add(toolKind(u),title+(st?" · "+st:""),(u.rawInput&&JSON.stringify(u.rawInput).slice(0,240))||u.content&&u.content.text||"");
    }
  }
  async function loadHistory(sid){
    if(!chatEl||!workEl)return;
    chatEl.innerHTML="";workEl.innerHTML="";
    selected=sid;
    try{
      const cwd=(ctx.getCwd&&ctx.getCwd())||"";
      const r=await fetch("/api/session/history?sessionId="+encodeURIComponent(sid)+"&cwd="+encodeURIComponent(cwd)+"&limit=80",{cache:"no-store"});
      const j=await r.json();
      const events=Array.isArray(j.events)?j.events:[];
      for(const ev of events){
        const u=(ev.params&&ev.params.update)||ev.update||ev;
        paintEvent(u);
      }
    }catch(e){add("tool","history",String(e&&e.message||e))}
    [...sessEl.querySelectorAll("[data-sid]")].forEach(n=>n.classList.toggle("on",n.getAttribute("data-sid")===sid));
  }
  async function refreshList(){
    if(!sessEl)return;
    try{
      const r=await fetch("/api/sessions?limit=80",{cache:"no-store"});
      const j=await r.json();
      const rows=j.sessions||[];
      sessEl.innerHTML="";
      const h=document.createElement("div");h.className="xr-rail-h";h.textContent="Chats";sessEl.appendChild(h);
      for(const s of rows.slice(0,60)){
        const id=String(s.sessionId||s.id||"");
        if(!id)continue;
        const b=document.createElement("button");
        b.type="button";b.className="xr-sess"+(id===selected?" on":"");
        b.setAttribute("data-sid",id);
        b.textContent=(s.title||"Chat · "+id.slice(0,8)).slice(0,48);
        b.title=id;
        b.onclick=()=>loadHistory(id);
        sessEl.appendChild(b);
      }
    }catch(e){}
  }
  function live(kind,title,body){
    if(selected&&liveSid&&selected!==liveSid)return;
    add(kind,title,body);
  }
  function setLiveSid(id){
    liveSid=id||"";
    if(liveSid&&!selected)loadHistory(liveSid);
    refreshList();
  }
  let started=false;
  function start(){
    if(started)return;started=true;
    fetch("/config.json",{cache:"no-store"}).then(r=>r.json()).then(c=>{window.__cwd=c.cwd||"";refreshList();if(liveSid)loadHistory(liveSid)}).catch(()=>{refreshList();if(liveSid)loadHistory(liveSid)});
    setInterval(refreshList,12000);
  }
  return {start,live,setLiveSid,paintEvent,add,refreshList};
}
