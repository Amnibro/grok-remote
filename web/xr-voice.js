export function initVoice(ctx){
  const {getState,setState,say,ensureAudio,getAudio,KEY}=ctx;
  const V=ctx.V||{speaking:false,alevel:0,gestureSeed:0,spoken:0};
  const ttsQ=[];
  function speak(text){
    const t=String(text||"").trim();
    if(!t)return;
    ttsQ.push(t);
    pump();
  }
  async function pump(){
    if(V.speaking||!ttsQ.length)return;
    V.speaking=true;
    setState("speak");
    V.gestureSeed=Math.random()*6.283;
    const text=ttsQ.shift();
    say(text);
    try{
      ensureAudio();
      const a=getAudio();
      if(!a||!a.ctx)throw new Error("no audio ctx");
      const r=await fetch("/api/xr/tts"+(KEY?"?key="+encodeURIComponent(KEY):""),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text})});
      if(!r.ok)throw new Error("tts "+r.status);
      const buf=await a.ctx.decodeAudioData(await r.arrayBuffer());
      await new Promise(res=>{
        const src=a.ctx.createBufferSource();
        src.buffer=buf;
        src.connect(a.analyser);
        src.onended=res;
        src.start();
      });
    }catch(e){
      await new Promise(res=>{
        try{
          const u=new SpeechSynthesisUtterance(text);
          u.onend=res;u.onerror=res;
          u.onboundary=()=>{V.alevel=0.7};
          speechSynthesis.speak(u);
          setTimeout(res,Math.min(12000,900+text.length*70));
        }catch(x){res()}
      });
    }
    V.speaking=false;
    V.spoken++;
    if(ttsQ.length)pump();
    else if(getState()==="speak")setState("idle");
  }
  const idle=()=>!ttsQ.length&&!V.speaking;
  const queued=()=>ttsQ.length;
  return {speak,idle,queued,V};
}
