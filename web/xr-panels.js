export function initPanels(ctx){
  const {KEY,getSid,getRestQ,sendMotion}=ctx;
  const hudState={base:"?",gesture:"-",gaze:"-",seq:0,cam:"off"};
  let camStream=null,camVideo=null;
  const guard=e=>!(e.target&&e.target.matches&&e.target.matches("input"));
  const host=document.getElementById("xrui")||document.body;
  const mk=(css,html,cls)=>{const d=document.createElement("div");d.className="xr-sheet"+(cls?" "+cls:"");d.style.cssText=css;if(html)d.innerHTML=html;host.appendChild(d);return d};
  const mhud=mk("top:44px;right:12px;font:11px var(--font-mono);padding:8px 10px;z-index:50;white-space:pre;display:none;color:var(--mut)");
  const visionLine=()=>{
    const v=ctx.getVision&&ctx.getVision();
    if(!v)return "-";
    if(!v.on)return "off";
    const age=v.last?Math.round((Date.now()-v.last)/1000)+"s ago":"pending";
    return v.err?("ERR "+v.err.slice(0,24)):(v.frames+" frames · "+age+" · "+(v.src||"-"));
  };
  const errLine=()=>{
    const e=ctx.getErrors&&ctx.getErrors();
    if(!e)return "-";
    if(!e.length)return "none";
    const l=e[e.length-1];
    return e.length+" · last "+l.src+": "+l.msg.slice(0,44)+(l.n>1?" (x"+l.n+")":"");
  };
  const rigLine=()=>{
    const r=ctx.getRig&&ctx.getRig();
    if(!r||!r.bones)return "loading";
    return r.bones+" bones · "+(r.file||"?")+" · rig "+r.pct+"%"+(r.missing.length?" (missing "+r.missing.slice(0,3).join(",")+")":"")+(r.driven!=null?" · clips drive "+r.driven+"/"+r.bones+" bones":"");
  };
  const ikLine=()=>{
    const k=ctx.getIK&&ctx.getIK();
    if(!k)return "-";
    if(!(k.state.weight>0))return "released";
    return k.state.chain+" → "+k.state.target.toArray().map(v=>v.toFixed(2)).join(",")+" err "+k.state.err.toFixed(3);
  };
  function hudDraw(){mhud.textContent="base    "+hudState.base+"\ngesture "+hudState.gesture+"\ngaze    "+hudState.gaze+"\nseq     "+hudState.seq+"\nsession "+((getSid()||"").slice(0,8)||"-")+"\nmotion  "+(ctx.motionLinked&&ctx.motionLinked()?"linked":"down")+"\ncam     "+(hudState.cam||"off")+"\nvision  "+visionLine()+"\nerrors  "+errLine()+"\n[h]ud [c]am [x]snap"}
  setInterval(hudDraw,1000);
  async function toggleCam(){
    if(camStream){camStream.getTracks().forEach(t=>t.stop());camStream=null;camVideo&&camVideo.remove();camVideo=null;hudState.cam="off";return}
    try{
      camStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:"environment"},audio:false});
      camVideo=document.createElement("video");
      camVideo.srcObject=camStream;camVideo.muted=true;camVideo.autoplay=true;camVideo.playsInline=true;
      camVideo.style.cssText="position:fixed;inset:0;width:100vw;height:100vh;object-fit:cover;z-index:0;filter:brightness(0.5)";
      document.body.prepend(camVideo);
      const cv=document.querySelector("canvas");
      if(cv){cv.style.position="relative";cv.style.zIndex="1"}
      hudState.cam="LIVE";
    }catch(e){hudState.cam="blocked ("+(location.hostname==="localhost"||location.hostname==="127.0.0.1"?e.name:"needs localhost/https")+")"}
  }
  const tpanel=mk("top:44px;right:12px;bottom:120px;width:270px;padding:10px;display:none","<div style='font-weight:650;font-size:11px;letter-spacing:.08em;color:var(--mut)'>CONVERSATION</div><div id='cstat' style='font:10.5px var(--font-mono);color:var(--ok);margin:4px 0'></div><div id='cstrip' style='display:flex;gap:1px;height:22px;align-items:flex-end;margin-bottom:8px;border-bottom:1px solid var(--line);padding-bottom:4px'></div><div id='clog'></div>");
  const clog=()=>document.getElementById("clog");
  const COLOR={you:"var(--you)",move:"var(--ok)",her:"var(--tx)"};
  let clipIx={};
  fetch("/static/clip_index.json",{cache:"no-store"}).then(r=>r.json()).then(j=>{clipIx=j.clips||{};drawStrip()}).catch(()=>{});
  let convoLog=[];
  try{convoLog=JSON.parse(localStorage.getItem("companionConvo")||"[]")}catch(e){}
  function renderConvo(who,text){
    const d=document.createElement("div");
    d.style.cssText="margin:6px 0;line-height:1.35;"+(who==="you"?"color:"+COLOR.you:who==="move"?"color:"+COLOR.move+";font-size:10.5px;font-style:italic":"color:"+COLOR.her);
    let extra="";
    if(who==="move"){
      const nm=String(text||"").split(":").slice(1).join(":").trim().split(/[\s|]/)[0];
      const m=clipIx[nm];
      if(m)extra="  ("+m.tier+" "+m.energy+(m.loops?"":" · hitches")+")";
    }
    d.textContent=(who==="you"?"you: ":who==="move"?"⟡ ":"")+text+extra;
    clog().appendChild(d);
    while(clog().children.length>120)clog().removeChild(clog().firstChild);
    tpanel.scrollTop=tpanel.scrollHeight;
  }
  function drawStrip(){
    const st=document.getElementById("cstrip");
    if(!st)return;
    st.innerHTML="";
    const recent=convoLog.slice(-60);
    const peak=Math.max(1,...recent.map(e=>(e.t||"").length));
    for(const e of recent){
      const b=document.createElement("div");
      const n=(e.t||"").length;
      b.style.cssText="flex:1;min-width:2px;border-radius:1px;background:"+(COLOR[e.w]||"#456")+";height:"+(4+Math.round(18*n/peak))+"px;opacity:"+(e.w==="move"?0.95:0.7);
      b.title=(e.w==="you"?"you: ":e.w==="move"?"move ":"her: ")+String(e.t||"").slice(0,120);
      st.appendChild(b);
    }
    const you=convoLog.filter(e=>e.w==="you").length;
    const her=convoLog.filter(e=>e.w==="her");
    const moves=convoLog.filter(e=>e.w==="move").map(e=>String(e.t||"").split(":")[1]||"?");
    const tally={};
    for(const m of moves)tally[m.trim()]=(tally[m.trim()]||0)+1;
    const top=Object.keys(tally).sort((a,b)=>tally[b]-tally[a])[0];
    const words=her.reduce((a,e)=>a+String(e.t||"").split(/\s+/).length,0);
    const span=convoLog.length&&convoLog[0].ts?Math.round((Date.now()-convoLog[0].ts)/60000):0;
    const el=document.getElementById("cstat");
    if(el)el.textContent="you "+you+" · her "+her.length+" ("+words+"w) · moves "+moves.length+(top?" top:"+top:"")+(span?" · "+span+"m":"");
  }
  for(const e of convoLog)renderConvo(e.w,e.t);
  drawStrip();
  function addConvo(who,text){
    renderConvo(who,text);
    convoLog.push({w:who,t:text,ts:Date.now()});
    if(convoLog.length>120)convoLog=convoLog.slice(-120);
    try{localStorage.setItem("companionConvo",JSON.stringify(convoLog))}catch(e){}
    drawStrip();
  }
  const jbox=mk("top:44px;left:12px;bottom:120px;width:210px;padding:10px;display:none","<div style='font-weight:650;font-size:11px;letter-spacing:.08em;color:var(--mut);margin-bottom:6px'>JUKEBOX</div>");
  let jboxLoaded=false;
  async function loadJukebox(){
    if(jboxLoaded)return;
    jboxLoaded=true;
    try{
      const r=await fetch("http"+(location.protocol==="https:"?"s":"")+"://"+location.hostname+":2423/motion/clips").then(r=>r.json());
      let ix={};
      try{ix=(await (await fetch("/static/clip_index.json",{cache:"no-store"})).json()).clips||{}}catch(e){}
      const TC={calm:"var(--mut)",moderate:"var(--tx)",lively:"var(--gold)",explosive:"var(--bad)"};
      const RANK={calm:0,moderate:1,lively:2,explosive:3};
      const list=[...new Set(r.clips||[])].sort((a,b)=>{
        const ra=RANK[(ix[a]||{}).tier]??9,rb=RANK[(ix[b]||{}).tier]??9;
        return ra-rb||a.localeCompare(b);
      });
      for(const c of list){
        const meta=ix[c]||{};
        const b=document.createElement("div");
        b.textContent=c+(meta.tier?"  "+meta.energy:"");
        b.title=meta.tier?meta.tier+" · "+meta.energy+" deg/s · "+meta.dur+"s":"unrated";
        b.style.cssText="padding:3px 6px;margin:1px 0;border-radius:8px;cursor:pointer;color:"+(TC[meta.tier]||"var(--mut)");
        b.onmouseenter=()=>b.style.background="var(--acc-dim)";
        b.onmouseleave=()=>b.style.background="";
        b.onclick=()=>sendMotion("motion",c);
        jbox.appendChild(b);
      }
    }catch(e){jboxLoaded=false}
  }
  const bpanel=mk("bottom:130px;left:12px;width:290px;max-height:40vh;padding:10px;display:none","<div style='font-weight:650;font-size:11px;letter-spacing:.08em;color:var(--mut)'>BRAID</div><div id='bstat' style='color:var(--ok);font-size:10.5px;margin:4px 0'></div><div id='blines'></div>");
  let braidTimer=null;
  async function braidRefresh(){
    try{
      const r=await fetch("/api/xr/braid"+(KEY?"?key="+encodeURIComponent(KEY):""),{cache:"no-store"}).then(r=>r.json());
      document.getElementById("bstat").textContent=r.live?("live · "+r.sessions+" sessions"):"Braid offline";
      const bl=document.getElementById("blines");
      bl.innerHTML="";
      for(const t of (r.transcript||[])){
        const d=document.createElement("div");
        d.style.cssText="margin:5px 0;line-height:1.3;color:"+(t.who==="Anthony"?"var(--you)":"var(--tx)");
        d.textContent=(t.who?t.who+": ":"")+t.text;
        bl.appendChild(d);
      }
      bl.scrollTop=bl.scrollHeight;
    }catch(e){}
  }
  const vpanel=mk("top:44px;left:50%;transform:translateX(-50%);width:360px;max-width:96vw;max-height:calc(100vh - 96px);overscroll-behavior:contain;font:11.5px var(--font-mono);padding:12px;z-index:51;white-space:pre;display:none");
  let vTimer=null;
  const SKIP={core:1};
  const modFiles=()=>{
    const up=(ctx.getMods&&ctx.getMods())||[];
    const out=up.filter(m=>!SKIP[m]&&m.indexOf("sid:")!==0).map(m=>"xr-"+m+".js");
    return out.length?out.sort():["xr-panels.js"];
  };
  let modSizes=null;
  async function measureMods(){
    const want=modFiles();
    if(modSizes&&modSizes.length===want.length)return modSizes;
    const out=[];
    for(const m of want){
      try{
        const t=await (await fetch("/static/"+m,{cache:"no-store"})).text();
        out.push({m,lines:t.split(chr10).length,kb:+(t.length/1024).toFixed(1)});
      }catch(e){out.push({m,lines:0,kb:0})}
    }
    modSizes=out;
    return out;
  }
  const chr10=String.fromCharCode(10);
  async function codeMapRefresh(){
    const dot=ok=>ok?"🟢":"🔴";
    await measureMods();
    let ms=null,clipN=0,braid={live:false};
    try{ms=await fetch("http"+(location.protocol==="https:"?"s":"")+"://"+location.hostname+":2423/motion/state").then(r=>r.json())}catch(e){}
    try{const c=await fetch("http"+(location.protocol==="https:"?"s":"")+"://"+location.hostname+":2423/motion/clips").then(r=>r.json());clipN=(c.clips||[]).length}catch(e){}
    try{braid=await fetch("/api/xr/braid"+(KEY?"?key="+encodeURIComponent(KEY):""),{cache:"no-store"}).then(r=>r.json())}catch(e){}
    vpanel.textContent=
"CODE MAP · companion stack\n──────────────────────────────\n"+
dot(true)+" hub server.py         :2421\n   ├─ /xr renderer (this page)\n   ├─ /api/xr/tts   edge-tts voice\n   ├─ /api/xr/see   her eyes+self-view\n   ├─ /api/xr/models GLB selector\n   └─ /api/xr/braid  Braid bridge "+dot(!!(braid&&braid.live))+"\n"+
dot(!!ms)+" motion_service.py     :2423\n   ├─ clips store     "+clipN+" moves\n   ├─ ws /pose        "+(ms?ms.clients:0)+" renderer(s)\n   └─ base: "+(ms?ms.base:"?")+"\n"+
dot(!!getSid())+" brain session (grok)  "+((getSid()||"").slice(0,8)||"down")+"\n"+
dot(!!getRestQ())+" body: "+rigLine()+"\n   feedback: perform → snapshot → refine\n"+
(modSizes?modSizes.map(x=>"   · "+x.m.padEnd(15)+String(x.lines).padStart(4)+" lines  "+x.kb+"kb").join("\n")+"\n":"")+
dot(!!(ctx.getVision&&ctx.getVision().on))+" vision: "+visionLine()+"\n   companion_view.jpg ← camera + self-view\n"+
dot(!!(ctx.getIK&&ctx.getIK()&&ctx.getIK().state.weight>0))+" arm IK: "+ikLine()+"\n"+
dot(!(ctx.getErrors&&ctx.getErrors().length))+" errors: "+errLine()+"\n──────────────────────────────\nkeys: [b]raid [j]ukebox [t]ranscript [h]ud [c]am [v]map [x]snap";
  }
  function doKey(k){
    if(k==="h")mhud.style.display=mhud.style.display==="none"?"block":"none";
    if(k==="c")toggleCam();
    if(k==="x"&&ctx.capture)ctx.capture();
    if(k==="t")tpanel.style.display=tpanel.style.display==="none"?"block":"none";
    if(k==="j"){jbox.style.display=jbox.style.display==="none"?"block":"none";loadJukebox()}
    if(k==="b"){const on=bpanel.style.display==="none";bpanel.style.display=on?"block":"none";if(on){braidRefresh();braidTimer=setInterval(braidRefresh,8000)}else if(braidTimer){clearInterval(braidTimer);braidTimer=null}}
    if(k==="v"){const on=vpanel.style.display==="none";vpanel.style.display=on?"block":"none";if(on){codeMapRefresh();vTimer=setInterval(codeMapRefresh,6000)}else if(vTimer){clearInterval(vTimer);vTimer=null}}
  }
  addEventListener("keydown",e=>{if(guard(e))doKey(e.key)});
  const KEYS=[["h","hud"],["t","talk"],["j","moves"],["b","braid"],["v","map"],["c","cam"],["x","snap"]];
  const bar=document.createElement("div");
  bar.style.cssText="display:none;gap:6px;z-index:52;flex-wrap:wrap;justify-content:center;max-width:96vw;pointer-events:auto;order:-1";
  const hud=document.getElementById("hud");
  (hud||document.body).appendChild(bar);
  if(!hud)bar.style.cssText+=";position:fixed;left:50%;transform:translateX(-50%);bottom:8px";
  for(const [k,label] of KEYS){
    const btn=document.createElement("button");
    btn.textContent=label;
    btn.setAttribute("data-key",k);
    btn.className="xr-chip";
    btn.style.cssText="touch-action:manipulation";
    btn.addEventListener("pointerdown",e=>{e.preventDefault();e.stopPropagation();doKey(k)});
    bar.appendChild(btn);
  }
  function showBar(){bar.style.display="flex"}
  showBar();
  addEventListener("touchstart",showBar,{once:true,passive:true});
  function recentConvo(maxAgeMs,n){
    const cut=Date.now()-(maxAgeMs||6*3600000);
    const rows=convoLog.filter(e=>e.w!=="move"&&e.ts&&e.ts>cut);
    if(rows.length<2)return null;
    const last=rows.slice(-(n||6));
    return {lines:last.map(e=>(e.w==="you"?"Anthony":"you")+": "+String(e.t||"").replace(/\s+/g," ").slice(0,180)),ageMin:Math.round((Date.now()-rows[rows.length-1].ts)/60000)};
  }
  function moveStats(n){
    const win=convoLog.slice(-(n||24));
    const turns=win.filter(e=>e.w==="her").length;
    const moves=win.filter(e=>e.w==="move").map(e=>String(e.t||"").split(":").slice(1).join(":").trim());
    const tally={};
    for(const m of moves)tally[m]=(tally[m]||0)+1;
    const top=Object.keys(tally).sort((a,b)=>tally[b]-tally[a])[0]||"";
    return {turns,moves:moves.length,top,topCount:tally[top]||0,last:moves[moves.length-1]||""};
  }
  return {addConvo,hudState,recentConvo,moveStats,doKey,showBar,touchBar:bar,getCam:()=>({stream:camStream,video:camVideo})};
}
