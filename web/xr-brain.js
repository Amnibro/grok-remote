export function initBrain(ctx){
  const {KEY,getState,setState,setLinked,say,speak,panels,composeClip,sendMotion,onReach,onSession,onFeed}=ctx;
  const B={sid:null,accum:"",spokenUpto:0,lastChunk:"",lastSpoken:""};
  const pending=new Map();
  let ws=null,wsid=0;
  const wsUrl=()=>(location.protocol==="https:"?"wss://":"ws://")+location.host+"/ws"+(KEY?"?key="+encodeURIComponent(KEY):"");
  function req(method,params){
    return new Promise(res=>{
      const id=++wsid;
      pending.set(id,res);
      ws.send(JSON.stringify({jsonrpc:"2.0",id,method,params}));
    });
  }
  function connect(){
    ws=new WebSocket(wsUrl());
    ws.onopen=async()=>{
      setLinked(true);
      await req("initialize",{protocolVersion:1,clientInfo:{name:"amni-companion",version:"0.2"},clientCapabilities:{}});
      let cwd=".";
      try{const c=await (await fetch("/config.json",{cache:"no-store"})).json();if(c&&c.cwd)cwd=c.cwd}catch(e){}
      const r=await req("session/new",{cwd,mcpServers:[]});
      B.sid=r&&r.result&&r.result.sessionId||r&&r.sessionId||null;
      B.sid?onSession&&onSession(B.sid):say("session failed: "+JSON.stringify(r).slice(0,120));
    };
    ws.onclose=()=>{setLinked(false);setTimeout(connect,2500)};
    ws.onmessage=ev=>{
      let d;
      try{d=JSON.parse(ev.data)}catch(e){return}
      if(d.id!=null&&pending.has(d.id)){pending.get(d.id)(d);pending.delete(d.id);return}
      if(d.method!=="session/update")return;
      if(d.params&&d.params.sessionId&&B.sid&&d.params.sessionId!==B.sid)return;
      const u=d.params&&d.params.update||{},k=u.sessionUpdate,c=u.content;
      let txt="";
      if(Array.isArray(c))txt=c.map(b=>b&&b.text||"").join("");
      else if(c&&c.text)txt=c.text;
      if(k==="agent_thought_chunk"){
        if(getState()!=="speak")setState("think");
        if(txt&&onFeed)onFeed("think","thinking",txt);
      }
      if(k==="tool_call"||k==="tool_call_update"){
        const title=u.title||u.kind||u.toolName||"tool";
        const st=u.status||"";
        let kind="tool";
        const tl=String(title).toLowerCase();
        if(/read|fetch|search|grep|glob|list/.test(tl))kind="read";
        else if(/write|edit|apply|patch|create|delete/.test(tl))kind="write";
        if(onFeed)onFeed(kind,title+(st?" · "+st:""),"");
      }
      if(k==="agent_message_chunk"&&txt){
        if(txt===B.lastChunk){B.lastChunk="";return}
        B.lastChunk=txt;
        B.accum+=txt;
        flushSentences(false);
      }
    };
  }
  function flushSentences(force){
    const chunk=B.accum.slice(B.spokenUpto);
    const m=force?[chunk]:chunk.match(/[^.!?\n]*[.!?\n]+/g);
    if(!m)return;
    for(const s of m){
      const tags=s.match(/\[\[(motion|emote|gaze|compose|reach):[^\]]+\]\]/gi);
      if(tags)for(const t of tags){
        const mm=t.match(/\[\[(\w+):([^\]]+)\]\]/);
        if(!mm)continue;
        panels.addConvo("move",mm[1].toLowerCase()+": "+mm[2].slice(0,60));
        const kind=mm[1].toLowerCase();
        kind==="compose"?composeClip(mm[2]):kind==="reach"?(onReach&&onReach(mm[2])):sendMotion(kind,mm[2]);
      }
      const clean=s.replace(/\[\[[^\]]*(\]\])?/g," ").replace(/\]\]/g," ").replace(/[*_#`>|-]+/g," ").replace(/\s+/g," ").trim();
      if(clean.length>1&&clean!==B.lastSpoken){B.lastSpoken=clean;speak(clean);panels.addConvo("her",clean);if(onFeed)onFeed("her","grok",clean)}
      B.spokenUpto+=s.length;
    }
  }
  const ready=()=>!!(ws&&ws.readyState===1&&B.sid);
  const begin=()=>{B.accum="";B.spokenUpto=0};
  return {connect,req,flushSentences,ready,begin,B};
}
