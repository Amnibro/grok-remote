export const BRAIN_KEY="grok_companion_brain",OLD_SID="grok_xr_companion_sid";
export const ls={get:k=>{try{return localStorage.getItem(k)}catch(e){return null}},set:(k,v)=>{try{v==null?localStorage.removeItem(k):localStorage.setItem(k,String(v))}catch(e){}}};
export const TAG=/\[\[(motion|emote|gaze|compose|reach):[^\]]+\]\]/gi;
export const cleanSpeech=s=>String(s||"").replace(/\[\[[^\]]*(\]\])?/g," ").replace(/\]\]/g," ").replace(/[*_#`>|-]+/g," ").replace(/\s+/g," ").trim();
export function initBrain(ctx){
  const {KEY,getState,setState,setLinked,say,speak,hush,panels,composeClip,sendMotion,onReach,onSession,onEvent,onPermit,onError}=ctx;
  const B={sid:null,brain:ls.get(BRAIN_KEY)||"",caps:{},user:"",body:"",label:"",accum:"",spokenUpto:0,turn:0,cur:null,err:"",linked:false};
  const TURN_MS=ctx.turnMs||240000,HELLO_MS=ctx.helloMs||30000,MIN_BACKOFF=ctx.minBackoff||1000,MAX_BACKOFF=ctx.maxBackoff||15000;
  B.backoff=MIN_BACKOFF;
  let ws=null,helloT=0,retryT=0;
  const wsUrl=()=>(location.protocol==="https:"?"wss://":"ws://")+location.host+"/api/companion/brain"+(KEY?"?key="+encodeURIComponent(KEY):"");
  const send=o=>{try{if(ws&&ws.readyState===1){ws.send(JSON.stringify(o));return true}}catch(e){}return false};
  const quiet=()=>/\[\[\s*quiet\s*\]\]/i.test(B.accum)||!B.accum.replace(/\[\[[^\]]*\]\]/g,"").trim();
  const hello=o=>send(Object.assign({op:"hello",brain:B.brain||undefined,sid:ls.get(OLD_SID)||undefined},o||{}));
  function finish(r,flush){const c=B.cur;if(!c)return;B.cur=null;clearTimeout(c.timer);flush!==false&&flushSentences(true);c.res(Object.assign({text:B.accum,quiet:quiet()},r))}
  function retry(){clearTimeout(retryT);retryT=setTimeout(connect,B.backoff);B.backoff=Math.min(MAX_BACKOFF,B.backoff*2)}
  function connect(){
    clearTimeout(retryT);
    try{ws=new WebSocket(wsUrl())}catch(e){return retry()}
    const me=ws;
    me.onopen=()=>{hello();clearTimeout(helloT);helloT=setTimeout(()=>{if(ws===me&&!B.linked)try{me.close()}catch(e){}},HELLO_MS)};
    me.onclose=()=>{if(ws!==me)return;clearTimeout(helloT);B.linked=false;setLinked(false);finish({error:"link dropped"});retry()};
    me.onerror=()=>{try{me.close()}catch(e){}};
    me.onmessage=ev=>{let d;try{d=JSON.parse(ev.data)}catch(e){return}ws===me&&d&&handle(d)};
  }
  function handle(d){
    const t=d.type,ev=u=>{try{onEvent&&onEvent(u)}catch(e){}};
    if(t==="session"){clearTimeout(helloT);Object.assign(B,{sid:d.sid||null,brain:d.brain||B.brain,caps:d.caps||{},user:d.user||"",body:d.body||"",label:d.label||d.brain||"",backoff:MIN_BACKOFF,linked:!!d.sid});ls.set(OLD_SID,null);setLinked(B.linked);onSession&&onSession(B.sid,d);return}
    if(t==="error"&&d.fatal){clearTimeout(helloT);B.linked=false;setLinked(false);say(d.message);onError&&onError(d);return}
    if(t==="pong"||d.turn!=null&&(!B.cur||d.turn!==B.cur.n))return;
    if(t==="text"&&d.delta){B.accum+=d.delta;flushSentences(false);ev({sessionUpdate:"agent_message_chunk",content:{text:d.delta}})}
    else if(t==="thought"){getState()!=="speak"&&setState("think");ev({sessionUpdate:"agent_thought_chunk",content:{text:d.delta||""}})}
    else if(t==="tool")ev({sessionUpdate:"tool_call_update",toolCallId:d.id,title:d.title||undefined,kind:d.kind,status:d.status,rawInput:d.input?{text:d.input}:undefined});
    else if(t==="permission")onPermit?onPermit(d,opt=>send({op:"permit",id:d.id,option:opt})):send({op:"permit",id:d.id,option:null});
    else if(t==="error"){B.err=d.message||"error";onError&&onError(d)}
    else if(t==="done")finish({stop:d.stop_reason,error:B.err||undefined});
  }
  function flushSentences(force){
    const chunk=B.accum.slice(B.spokenUpto);
    const m=force?[chunk]:chunk.match(/[^.!?\n]*[.!?\n]+/g);
    if(!m)return;
    for(const s of m){
      for(const t of s.match(TAG)||[]){
        const mm=t.match(/\[\[(\w+):([^\]]+)\]\]/);
        if(!mm)continue;
        const kind=mm[1].toLowerCase();
        panels.addConvo("move",kind+": "+mm[2].slice(0,60));
        kind==="compose"?composeClip(mm[2]):kind==="reach"?(onReach&&onReach(mm[2])):sendMotion(kind,mm[2]);
      }
      const clean=cleanSpeech(s);
      if(clean.length>1&&!/^quiet$/i.test(clean)){speak(clean);panels.addConvo("her",clean)}
      B.spokenUpto+=s.length;
    }
  }
  const ready=()=>!!(ws&&ws.readyState===1&&B.sid&&B.linked);
  const busy=()=>!!B.cur;
  const begin=()=>{B.accum="";B.spokenUpto=0;B.err=""};
  function ask(text,o){
    o=o||{};
    if(!ready())return Promise.resolve({error:"not linked",quiet:true});
    B.cur&&cancel(true);
    begin();
    const n=++B.turn;
    return new Promise(res=>{
      B.cur={n,res,timer:setTimeout(()=>{send({op:"cancel"});finish({error:"turn timed out"})},o.timeoutMs||TURN_MS)};
      send({op:"say",turn:n,text:String(text||""),percept:o.percept||[],images:o.images||[]})||finish({error:"link dropped"});
    });
  }
  function cancel(keepSpeech){const was=!!B.cur;send({op:"cancel"});finish({stop:"cancelled"},false);keepSpeech||hush&&hush();return was}
  function setBrain(kind){B.brain=kind||"";ls.set(BRAIN_KEY,kind||null);B.cur&&cancel();B.linked=false;B.sid=null;setLinked(false);hello({brain:kind||undefined})||connect()}
  function reset(){B.cur&&cancel();B.linked=false;setLinked(false);hello({fresh:true})}
  return {connect,ask,cancel,setBrain,reset,ready,busy,flushSentences,begin,B};
}
