/* Grok Remote session kernel.
   The hub is a bridge to one Grok Build ACP process. This module is the
   client contract that process never had: one room per session, exact
   sessionId only, tools/thoughts/jobs off the reply column, attach as
   a state instead of a pile of booleans. */
(function(root){
"use strict";
const TERM=/completed|failed|error|cancelled|canceled|timed.?out/i;
const LIVE=/pending|in_progress|inprogress|running/i;
function str(v){return String(v==null?"":v)}
function jobLive(j){
  if(!j)return false;
  if(/stalled|idle|cancelled|canceled/i.test(str(j.phase)))return false;
  if(j.running)return true;
  if((j.asks||[]).some(a=>a&&!a.acked))return true;
  return (j.tools||[]).some(t=>t&&!TERM.test(str(t.status)));
}
/* Same contract as Aug 1 braid: prefix-tolerant ids (8+ chars, hyphen boundary).
   Exact-only matching dropped live turns when ACP/hub sent a short or longer id. */
function idsMatch(a,b){
  const x=str(a),y=str(b);
  if(!x||!y)return false;
  if(x===y)return true;
  const short=x.length<=y.length?x:y,long=x.length<=y.length?y:x;
  if(short.length>=8&&long.startsWith(short)&&(long.length===short.length||long[short.length]==="-"))return true;
  return false;
}
function makeRoom(sid){
  return {
    sid:str(sid),
    attach:"none",
    gen:0,
    phase:"idle",
    tools:Object.create(null),
    pendingTools:new Set(),
    dismissed:new Set(),
    curUser:null,
    curAgent:null,
    curThought:null,
    curThoughtRow:null,
    userWireBuf:""
  };
}
function createChatRuntime(opts){
  opts=opts||{};
  const rooms=new Map();
  const state={
    openSid:"",
    gen:0,
    jobs:[],
    railClosed:false,
    homeTitle:"",
    prepend:null
  };
  function room(sid){
    const id=str(sid||state.openSid);
    if(!id)return makeRoom("");
    let r=rooms.get(id);
    if(r)return r;
    if(state.openSid&&idsMatch(id,state.openSid)){
      r=rooms.get(state.openSid);
      if(r)return r;
    }
    r=makeRoom(id);rooms.set(id,r);
    return r;
  }
  function belongs(sessionId){
    return idsMatch(state.openSid,sessionId);
  }
  function accept(sessionId,flags){
    flags=flags||{};
    const history=!!flags.history;
    if(!str(state.openSid))return false;
    if(!sessionId)return !!history;
    return belongs(sessionId);
  }
  function open(sid,gen){
    const id=str(sid);
    state.openSid=id;
    state.gen=gen||state.gen+1;
    state.railClosed=false;
    const r=room(id);
    r.sid=id;
    r.gen=state.gen;
    r.attach="loading";
    r.curUser=null;r.curAgent=null;r.curThought=null;r.curThoughtRow=null;
    r.userWireBuf="";
    r.pendingTools=new Set();
    return r;
  }
  function warming(sid){
    const r=room(sid||state.openSid);
    if(r.attach==="loading")r.attach="warming";
    return r;
  }
  function ready(sid){
    const r=room(sid||state.openSid);
    r.attach="ready";
    return r;
  }
  function fail(sid){
    const r=room(sid||state.openSid);
    r.attach="error";
    return r;
  }
  function cursors(sid){
    const r=room(sid||state.openSid);
    return {
      curUser:r.curUser,
      curAgent:r.curAgent,
      curThought:r.curThought,
      curThoughtRow:r.curThoughtRow,
      userWireBuf:r.userWireBuf,
      pendingTools:r.pendingTools,
      toolMap:r.tools
    };
  }
  function saveCursors(bag,sid){
    const r=room(sid||state.openSid);
    if(!bag)return r;
    if("curUser" in bag)r.curUser=bag.curUser;
    if("curAgent" in bag)r.curAgent=bag.curAgent;
    if("curThought" in bag)r.curThought=bag.curThought;
    if("curThoughtRow" in bag)r.curThoughtRow=bag.curThoughtRow;
    if("userWireBuf" in bag)r.userWireBuf=bag.userWireBuf;
    return r;
  }
  function extraJobs(openSid){
    const want=str(openSid||state.openSid);
    return (state.jobs||[]).filter(j=>jobLive(j)&&!idsMatch(j.sid,want));
  }
  function noteTool(sid,id,status){
    const r=room(sid);
    const tid=str(id);
    if(!tid)return r.pendingTools;
    const st=str(status).toLowerCase();
    if(!st||LIVE.test(st))r.pendingTools.add(tid);
    if(TERM.test(st))r.pendingTools.delete(tid);
    return r.pendingTools;
  }
  function doc(){return typeof document!=="undefined"?document:null}
  function listEl(){const d=doc();return d&&d.getElementById("agentRailList")}
  function railEl(){const d=doc();return d&&d.getElementById("agentRail")}
  function wide(){
    try{return typeof window!=="undefined"&&window.matchMedia("(min-width:900px)").matches}catch(e){return false}
  }
  function uxHide(){
    const u=(typeof window!=="undefined"&&window.ux)||opts.ux||{};
    return u;
  }
  function viewVisible(el){
    if(!el||el.classList.contains("dismissed"))return false;
    const u=uxHide();
    if(el.classList.contains("thought-row")&&u.hideThink)return false;
    if(el.classList.contains("agent-job"))return true;
    if(el.classList.contains("tool")){
      if(u.hideTools)return false;
      const k=el.getAttribute("data-tool-kind")||"";
      if(u.hideEdit&&(k==="edit"||k==="write"||k==="multi_edit"))return false;
      if(u.hideRead&&(k==="read"||k==="search"||k==="grep"||k==="glob"))return false;
    }
    return true;
  }
  function decorate(el){
    if(!el||!doc()||el.querySelector(".agent-x"))return el;
    const x=doc().createElement("button");
    x.type="button";x.className="agent-x";x.title="Remove";x.setAttribute("aria-label","Remove");x.textContent="×";
    x.onclick=e=>{e.preventDefault();e.stopPropagation();dismiss(el)};
    const head=el.querySelector(".tool-head, .nm, .agent-job-head");
    (head||el).appendChild(x);
    return el;
  }
  function isHome(el){return !!(el&&(el.classList.contains("agent-home")||el.getAttribute("data-home")==="1"))}
  function homeCard(){
    const list=listEl();
    return list?list.querySelector(".agent-home"):null;
  }
  function ensureHome(){
    const list=listEl();
    const d=doc();
    if(!list||!d)return null;
    let home=homeCard();
    if(home)return home;
    home=d.createElement("div");
    home.className="agent-job agent-home";
    home.setAttribute("data-home","1");
    home.innerHTML='<div class="agent-job-head"><span class="chev">▾</span><span class="tt">This chat</span><span class="st"></span></div><div class="agent-job-body"><div class="agent-home-act"></div></div>';
    home.querySelector(".agent-job-head").onclick=e=>{
      if(e.target.closest(".agent-x"))return;
      home.classList.toggle("collapsed");
    };
    decorate(home);
    list.appendChild(home);
    return home;
  }
  function homeAct(){
    const home=ensureHome();
    return home?home.querySelector(".agent-home-act"):null;
  }
  function setHomeTitle(t){
    state.homeTitle=str(t||"").trim();
    const tt=homeCard()&&homeCard().querySelector(".tt");
    if(tt)tt.textContent=state.homeTitle||"This chat";
  }
  function syncHome(){
    const home=homeCard();
    if(!home)return;
    const act=home.querySelector(".agent-home-act");
    const bits=act?[...act.children].filter(viewVisible):[];
    home.hidden=!bits.length;
    if(!bits.length)return;
    const tt=home.querySelector(".tt");
    if(tt)tt.textContent=state.homeTitle||"This chat";
    const st=home.querySelector(".st");
    if(st){
      const live=bits.some(el=>{
        if(!el.classList.contains("tool"))return false;
        const s=el.querySelector(".st");
        return s&&/run|pend|progress|start/i.test(s.textContent||"");
      });
      const last=bits[bits.length-1];
      const thinkLast=!!(last&&last.classList.contains("thought-row")&&!last.classList.contains("settled"));
      st.textContent=live?"working":(thinkLast?"thinking":"");
    }
  }
  function visible(){
    const list=listEl();
    if(!list)return[];
    return [...list.children].filter(el=>el.classList.contains("agent-job")&&viewVisible(el)&&!el.hidden);
  }
  function sync(maybeOpen){
    const rail=railEl();
    const d=doc();
    if(!rail||!d)return;
    syncHome();
    const nEl=d.getElementById("agentRailN");
    const tab=d.getElementById("btnAgentRailTab");
    const n=visible().length;
    if(nEl){nEl.hidden=!n;nEl.textContent=n>99?"99+":String(n)}
    if(!n){
      rail.hidden=true;
      rail.dataset.open="0";
      if(tab)tab.setAttribute("aria-expanded","false");
      return;
    }
    rail.hidden=false;
    if(maybeOpen&&!state.railClosed&&wide())rail.dataset.open="1";
    if(tab)tab.setAttribute("aria-expanded",rail.dataset.open==="1"?"true":"false");
  }
  function setOpen(on){
    const rail=railEl();
    if(!rail||rail.hidden)return;
    rail.dataset.open=on?"1":"0";
    state.railClosed=!on;
    const tab=doc()&&doc().getElementById("btnAgentRailTab");
    if(tab)tab.setAttribute("aria-expanded",on?"true":"false");
  }
  function place(el,opts){
    opts=opts||{};
    if(!el)return el;
    decorate(el);
    el.classList.remove("dismissed");
    if(state.prepend){state.prepend.push(el);return el}
    const list=listEl();
    if(!list){
      const feed=doc()&&doc().getElementById("feed");
      if(feed)feed.appendChild(el);
      return el;
    }
    const nest=el.classList.contains("tool")||el.classList.contains("thought-row");
    if(nest){
      const act=homeAct();
      if(act){
        if(opts.front)act.insertBefore(el,act.firstChild);
        else if(el.parentNode!==act)act.appendChild(el);
        sync(true);
        return el;
      }
    }
    if(el.parentNode!==list)list.appendChild(el);
    sync(true);
    return el;
  }
  function placeBatch(els,opts){
    (els||[]).forEach(el=>place(el,opts));
  }
  function dismiss(el){
    if(!el)return;
    el.classList.add("dismissed");
    const r=room();
    if(r.curThoughtRow===el){r.curThought=null;r.curThoughtRow=null}
    sync();
  }
  function clear(){
    const list=listEl();
    if(list)list.innerHTML="";
    state.railClosed=false;
    const rail=railEl();
    if(rail){rail.hidden=true;rail.dataset.open="0"}
    const nEl=doc()&&doc().getElementById("agentRailN");
    if(nEl){nEl.hidden=true;nEl.textContent="0"}
    const r=room();
    r.tools=Object.create(null);
    r.curThought=null;r.curThoughtRow=null;
    r.curUser=null;r.curAgent=null;
    r.userWireBuf="";
    r.pendingTools=new Set();
  }
  function gather(){
    const feed=doc()&&doc().getElementById("feed");
    if(!feed)return;
    [...feed.children].filter(el=>el.classList&&(el.classList.contains("tool")||el.classList.contains("thought-row"))).forEach(place);
  }
  function paintJobs(hooks){
    hooks=hooks||{};
    const list=listEl();
    if(!list)return extraJobs();
    /* Other chats are sessions, not extra agents in this room. Keep this
       rail to the open chat's agent (thoughts/tools nested in the home card). */
    [...list.querySelectorAll(".agent-job")].forEach(card=>{
      if(isHome(card))return;
      card.remove();
    });
    sync();
    return extraJobs();
  }
  function setJobs(jobs,hooks){
    state.jobs=Array.isArray(jobs)?jobs:[];
    return paintJobs(hooks);
  }
  function bind(hooks){
    const d=doc();
    if(!d)return;
    const tab=d.getElementById("btnAgentRailTab");
    const hide=d.getElementById("btnAgentRailHide");
    const wipe=d.getElementById("btnAgentRailClear");
    const pan=d.getElementById("agentRailPan");
    if(tab&&!tab._wired){tab.onclick=e=>{e.stopPropagation();setOpen(true)};tab._wired=true}
    if(hide&&!hide._wired){hide.onclick=e=>{e.stopPropagation();setOpen(false)};hide._wired=true}
    if(wipe&&!wipe._wired){
      wipe.onclick=e=>{
        e.stopPropagation();
        const list=listEl();
        if(list)[...list.children].forEach(el=>el.classList.add("dismissed"));
        sync();
      };
      wipe._wired=true;
    }
    if(pan&&!pan._wired){pan.addEventListener("click",e=>e.stopPropagation());pan._wired=true}
    if(hooks)state.hooks=hooks;
  }
  return {
    rooms,state,room,belongs,accept,idsMatch,open,warming,ready,fail,
    cursors,saveCursors,extraJobs,jobLive,noteTool,
    place,placeBatch,dismiss,clear,gather,sync,setOpen,setJobs,paintJobs,bind,visible,setHomeTitle,
    beginPrepend(){state.prepend=[]},
    takePrepend(){const n=state.prepend||[];state.prepend=null;return n}
  };
}
const grokChat=createChatRuntime();
if(typeof window!=="undefined")window.grokChat=grokChat;
if(typeof module!=="undefined"&&module.exports){
  module.exports={createChatRuntime,grokChat,idsMatch};
}
})(typeof window!=="undefined"?window:typeof globalThis!=="undefined"?globalThis:this);
