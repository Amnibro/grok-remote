export function initVoice(ctx){
  const {getState,setState,say,ensureAudio,getAudio,KEY}=ctx;
  const V=ctx.V||{speaking:false,alevel:0,gestureSeed:0,spoken:0};
  const ttsQ=[];
  let cur=null,epoch=0,noServer=0;
  function speak(text){
    const t=String(text||"").trim();
    if(!t)return;
    ttsQ.push(t);
    pump();
  }
  const play=fn=>new Promise(res=>{cur=res;fn(res)});
  async function pump(){
    if(V.speaking||!ttsQ.length)return;
    V.speaking=true;
    setState("speak");
    V.gestureSeed=Math.random()*6.283;
    const text=ttsQ.shift(),my=epoch;
    say(text);
    try{
      ensureAudio();
      const a=getAudio();
      if(!a||!a.ctx)throw new Error("no audio ctx");
      if(Date.now()-noServer<60000)throw new Error("no server voice");
      const r=await fetch("/api/xr/tts"+(KEY?"?key="+encodeURIComponent(KEY):""),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text})});
      if(r.status===503)noServer=Date.now();
      if(!r.ok)throw new Error("tts "+r.status);
      V.backend=r.headers.get("X-TTS-Backend")||"";
      const buf=await a.ctx.decodeAudioData(await r.arrayBuffer());
      my===epoch&&await play(res=>{const src=a.ctx.createBufferSource();src.buffer=buf;src.connect(a.analyser);src.onended=res;src.start();cur=()=>{try{src.stop()}catch(e){}res()}});
    }catch(e){
      V.backend="browser";
      my===epoch&&await play(res=>{
        try{
          const u=new SpeechSynthesisUtterance(text);
          u.onend=res;u.onerror=res;
          u.onboundary=()=>{V.alevel=0.7};
          speechSynthesis.speak(u);
          setTimeout(res,Math.min(12000,900+text.length*70));
        }catch(x){res()}
      });
    }
    cur=null;
    V.speaking=false;
    V.spoken++;
    if(ttsQ.length)pump();
    else if(getState()==="speak")setState("idle");
  }
  function hush(){ttsQ.length=0;epoch++;const c=cur;cur=null;try{c&&c()}catch(e){}try{speechSynthesis.cancel()}catch(e){}}
  const idle=()=>!ttsQ.length&&!V.speaking;
  const queued=()=>ttsQ.length;
  return {speak,hush,idle,queued,V};
}
