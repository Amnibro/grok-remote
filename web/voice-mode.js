(function(){
const LS_VOICE="grok_remote_voice";
const VOICES=["eve","ara","leo","rex","sal","luna","orion","helix"];
const ACKS=["Got it. Working on that.","On it.","Task received. Working.","Heard you. Starting now.","Roger. On it."];
let cfg={mode:"off",voiceId:"eve",autoSend:true,speakAck:true,speakResult:true,lang:"en-US",wake:"hey grok"};
let rec=null,listening=false,busy=false,audioEl=null,audioCtx=null,ttsOk=null,queue=[],speaking=false,xrSess=null,pauseTimer=null,finalBuf="",interim="",lastTurnSpeak=0,micFatal=false;
function $(id){return document.getElementById(id)}
function chip(t){try{if(typeof window.chip==="function")window.chip(t)}catch(e){}}
function loadCfg(){
 try{
  const j=JSON.parse(String(localStorage.getItem(LS_VOICE)||"{}").replace(/^\uFEFF/,"").trim()||"{}");
  if(j&&typeof j==="object")cfg=Object.assign(cfg,j);
 }catch(e){}
 if(!VOICES.includes(cfg.voiceId))cfg.voiceId="eve";
 if(!["off","dictate","go","xr"].includes(cfg.mode))cfg.mode="off";
}
function saveCfg(){try{localStorage.setItem(LS_VOICE,JSON.stringify(cfg))}catch(e){}}
function ensureAudioCtx(){
 if(!audioCtx){const AC=window.AudioContext||window.webkitAudioContext;if(AC)audioCtx=new AC()}
 if(audioCtx&&audioCtx.state==="suspended")audioCtx.resume().catch(()=>{});
 return audioCtx;
}
function paintHud(){
 const hud=$("voiceHud");if(!hud)return;
 const on=cfg.mode!=="off";
 hud.classList.toggle("on",on);
 hud.classList.toggle("go",cfg.mode==="go");
 hud.classList.toggle("xr",cfg.mode==="xr");
 document.body.classList.toggle("voice-go",cfg.mode==="go");
 document.body.classList.toggle("voice-xr",cfg.mode==="xr");
 document.body.classList.toggle("voice-on",on);
 const st=$("voiceHudStatus"),sub=$("voiceHudSub"),mic=$("voiceHudMic");
 if(st)st.textContent=cfg.mode==="xr"?"XR · hands-free":cfg.mode==="go"?"Go · conversational":cfg.mode==="dictate"?"Dictate":"Voice off";
 if(sub)sub.textContent=speaking?"Speaking…":listening?(interim||"Listening…"):(busy?"Working…":(ttsOk===false?"Browser voice fallback":ttsOk?"Grok voice ready":"Voice standby"));
 if(mic)mic.classList.toggle("on",listening);
 paintBtns();
}
let xrCaps={ar:false,vr:false,xr:false,uaWearable:false,smallScreen:false,preferred:"hud",ready:false};
function paintBtns(){
 ["btnVoiceGo","btnVoiceXr","btnVoice","btnComposerVoice","btnComposerXr"].forEach(id=>{
  const b=$(id);if(!b)return;
  if(id==="btnVoiceGo"||id==="btnComposerVoice")b.classList.toggle("on",cfg.mode==="go"||cfg.mode==="dictate"||listening);
  else if(id==="btnVoiceXr"||id==="btnComposerXr")b.classList.toggle("on",cfg.mode==="xr");
  else if(id==="btnVoice")b.classList.toggle("on",cfg.mode==="dictate"||listening);
 });
 const xrBtn=$("btnComposerXr");
 if(xrBtn){
  const want=typeof window.grokCompanionOn==="function"&&window.grokCompanionOn();
  xrBtn.classList.toggle("show",!!want);
  xrBtn.textContent="XR";
  xrBtn.title=want?"Open hologram companion":"Companion is off — enable in Settings";
 }
 const menuXr=$("btnXrMenu");
 if(menuXr){
  const lab=xrCaps.ar?"AR ready":xrCaps.vr?"VR ready":xrCaps.uaWearable?"Wearable HUD":"HUD mode";
  menuXr.innerHTML='XR / AR <span class="mm-k">'+lab+"</span>";
 }
 const mic=$("btnComposerVoice");
 if(mic)mic.textContent=cfg.mode==="go"?"Go":(listening?"…":"Mic");
 const sel=$("voiceVoiceSel");if(sel&&sel.value!==cfg.voiceId)sel.value=cfg.voiceId;
}
async function detectXrCaps(){
 const caps={ar:false,vr:false,xr:false,uaWearable:false,smallScreen:false,preferred:"hud",ready:true};
 try{
  if(navigator.xr&&navigator.xr.isSessionSupported){
   caps.ar=!!(await navigator.xr.isSessionSupported("immersive-ar").catch(()=>false));
   caps.vr=!!(await navigator.xr.isSessionSupported("immersive-vr").catch(()=>false));
   caps.xr=caps.ar||caps.vr;
  }
 }catch(e){}
 const ua=String(navigator.userAgent||"");
 caps.uaWearable=/Glass|Quest|Vision|HoloLens|Pico|Magic\s*Leap|WebXR|Wear\s*OS|Tizen|Galaxy\s*Watch|SM-R|Watch\s*OS/i.test(ua);
 try{caps.smallScreen=Math.min(screen.width||999,screen.height||999)<=320||window.matchMedia("(max-width:320px) and (max-height:360px)").matches}catch(e){}
 caps.preferred=caps.ar?"immersive-ar":(caps.vr?"immersive-vr":"hud");
 xrCaps=caps;
 window.grokXrCaps=caps;
 paintBtns();
 return caps;
}
async function refreshTtsStatus(){
 try{
  const r=await fetch("/api/voice/status",{cache:"no-store"});
  const j=await r.json();
  ttsOk=!!(j&&j.tts);
  if(j&&j.hint&&!ttsOk)chip(j.hint);
 }catch(e){ttsOk=false}
 paintHud();
}
function summarizeForVoice(raw){
 let t=String(raw||"").replace(/```[\s\S]*?```/g," ").replace(/`[^`]*`/g," ").replace(/!\[[^\]]*\]\([^)]*\)/g," ").replace(/\[[^\]]*\]\([^)]*\)/g,"$1").replace(/[#>*_~|]/g," ").replace(/\s+/g," ").trim();
 if(!t)return"Done.";
 if(t.length<=280)return t;
 const parts=t.split(/(?<=[.!?])\s+/).filter(Boolean);
 if(parts.length<=2)return t.slice(0,260).trim()+"…";
 const head=parts.slice(0,2).join(" ");
 const tail=parts[parts.length-1];
 let out=head+(tail&&tail!==parts[1]?" … "+tail:"");
 return out.length>360?out.slice(0,340).trim()+"…":out;
}
function stripSpeakable(t){return String(t||"").replace(/\[(?:pause|long-pause|laugh|sigh|whisper)\]/gi," ").replace(/<\/?[^>]+>/g," ").replace(/\s+/g," ").trim()}
function browserSpeak(text){
 return new Promise(resolve=>{
  if(!window.speechSynthesis){resolve(false);return}
  try{window.speechSynthesis.cancel()}catch(e){}
  const u=new SpeechSynthesisUtterance(stripSpeakable(text));
  u.lang=(cfg.lang||"en-US").slice(0,5);
  u.rate=1.05;
  u.onend=()=>resolve(true);
  u.onerror=()=>resolve(false);
  window.speechSynthesis.speak(u);
 });
}
async function grokSpeak(text){
 const r=await fetch("/api/tts",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text:String(text).slice(0,4000),voice_id:cfg.voiceId||"eve",language:(cfg.lang||"en").split("-")[0]||"en"})});
 if(!r.ok){
  let err="";try{const j=await r.json();err=j.error||""}catch(e){}
  throw new Error(err||("TTS "+r.status));
 }
 const blob=await r.blob();
 const url=URL.createObjectURL(blob);
 return new Promise((resolve,reject)=>{
  if(audioEl){try{audioEl.pause()}catch(e){}try{if(audioEl._settle)audioEl._settle()}catch(e){}}
  audioEl=new Audio(url);
  let done=false;
  const settle=(fn,v)=>{if(done)return;done=true;URL.revokeObjectURL(url);audioEl&&(audioEl._settle=null);fn(v)};
  audioEl._settle=()=>settle(resolve,false);
  audioEl.onended=()=>settle(resolve,true);
  audioEl.onerror=()=>settle(reject,new Error("audio play failed"));
  ensureAudioCtx();
  audioEl.play().catch(e=>settle(reject,e));
 });
}
async function speak(text,kind){
 const t=String(text||"").trim();
 if(!t)return;
 queue.push({t,kind:kind||"line"});
 if(speaking)return;
 speaking=true;paintHud();
 while(queue.length){
  const item=queue.shift();
  try{
   if(ttsOk!==false){
    try{await grokSpeak(item.t);ttsOk=true}
    catch(e){ttsOk=false;await browserSpeak(item.t)}
   }else await browserSpeak(item.t);
  }catch(e){chip("voice: "+e)}
 }
 speaking=false;paintHud();
 if(cfg.mode==="go"||cfg.mode==="xr")setTimeout(()=>{if(!busy&&!listening)startListen(true)},350);
}
function stopSpeak(){
 queue=[];
 try{if(audioEl)audioEl.pause()}catch(e){}
 try{if(audioEl&&audioEl._settle)audioEl._settle()}catch(e){}
 try{if(window.speechSynthesis)window.speechSynthesis.cancel()}catch(e){}
 speaking=false;paintHud();
}
function lastAgentText(){
 try{
  const rows=document.querySelectorAll("#feed .row");
  for(let i=rows.length-1;i>=0;i--){
   const nm=rows[i].querySelector(".nm");
   if(nm&&/grok/i.test(nm.textContent||"")){
    const bub=rows[i].querySelector(".bub");
    return (bub&&bub.dataset&&bub.dataset.raw)||(bub&&bub.textContent)||"";
   }
  }
 }catch(e){}
 return"";
}
function setBusyFlag(b){busy=!!b;paintHud()}
function onTaskSent(userText,meta){
 if(cfg.mode==="off")return;
 const m=meta&&typeof meta==="object"?meta:{};
 const delivery=m.delivery||m.mode||"";
 if(delivery==="queue"||delivery==="fyi")setBusyFlag(!!m.agentBusy);else setBusyFlag(true);
 stopListen(false);
 const short=String(userText||"").trim().slice(0,80);
 if(cfg.speakAck){
  const ack=delivery==="queue"?"Queued. I'll take that at the next pause.":delivery==="fyi"?"Got the FYI. Continuing the current task.":delivery==="interject"?"Interjecting. Cancelling current steps.":ACKS[Math.floor(Math.random()*ACKS.length)];
  speak(ack,"ack");
 }
 const hud=$("voiceHudLine");if(hud)hud.textContent=short?((delivery?delivery.toUpperCase()+" · ":"")+"You: "+short):"Task sent";
}
function onTurnDone(){
 if(cfg.mode==="off")return;
 setBusyFlag(false);
 const now=Date.now();
 if(now-lastTurnSpeak<2500)return;
 lastTurnSpeak=now;
 if(!cfg.speakResult){if(cfg.mode==="go"||cfg.mode==="xr")startListen(true);return}
 const raw=lastAgentText();
 const summary=summarizeForVoice(raw);
 const hud=$("voiceHudLine");if(hud)hud.textContent=summary;
 speak(summary,"result");
}
function SR(){return window.SpeechRecognition||window.webkitSpeechRecognition}
function stopListen(paint){
 if(pauseTimer){clearTimeout(pauseTimer);pauseTimer=null}
 if(rec){try{rec.onend=null;rec.stop()}catch(e){}rec=null}
 listening=false;finalBuf="";interim="";
 if(paint!==false)paintHud();
}
function sendVoiceText(text){
 const t=String(text||"").trim();
 if(!t)return;
 const box=$("box");
 if(box){box.value=t;box.dispatchEvent(new Event("input",{bubbles:true}))}
 if(typeof window.sendPrompt==="function")window.sendPrompt().catch(e=>chip(String(e)));
 else{
  const send=$("send");if(send)send.click();
 }
}
function maybeWake(text){
 const w=String(cfg.wake||"").toLowerCase().trim();
 if(!w)return text;
 const low=text.toLowerCase();
 const i=low.indexOf(w);
 return i>=0?text.slice(i+w.length).replace(/^[\s,.:;!-]+/,"").trim():(cfg.mode==="go"||cfg.mode==="xr"?text:"");
}
function startListen(continuous){
 const C=SR();
 if(!C){chip("Speech recognition not supported here");return}
 micFatal=false;
 stopListen(false);
 ensureAudioCtx();
 const r=new C();
 r.lang=cfg.lang||"en-US";
 r.continuous=!!continuous;
 r.interimResults=true;
 finalBuf="";interim="";
 r.onresult=e=>{
  let f="",inter="";
  for(let i=e.resultIndex;i<e.results.length;i++){
   const t=e.results[i][0].transcript;
   e.results[i].isFinal?f+=t+" ":inter+=t;
  }
  if(f)finalBuf=(finalBuf+" "+f).trim();
  interim=inter;
  const live=(finalBuf+(interim?" "+interim:"")).trim();
  const box=$("box");if(box&&cfg.mode==="dictate")box.value=live;
  const line=$("voiceHudLine");if(line)line.textContent=live||"…";
  paintHud();
  if(cfg.mode==="go"||cfg.mode==="xr"){
   if(pauseTimer)clearTimeout(pauseTimer);
   if(finalBuf&&cfg.autoSend){
    pauseTimer=setTimeout(()=>{
     const payload=maybeWake(finalBuf);
     finalBuf="";interim="";
     if(payload)sendVoiceText(payload);
    },1100);
   }
  }
 };
 r.onerror=e=>{
  if(e&&e.error==="no-speech"&&(cfg.mode==="go"||cfg.mode==="xr"))return;
  listening=false;paintHud();
  if(e&&["not-allowed","audio-capture","service-not-allowed"].includes(e.error)){
   micFatal=true;chip("mic: "+e.error+" — voice mode stopped");setMode("off");return;
  }
  if(e&&e.error&&e.error!=="aborted")chip("mic: "+e.error);
 };
 r.onend=()=>{
  listening=false;rec=null;paintHud();
  if(micFatal)return;
  if((cfg.mode==="go"||cfg.mode==="xr")&&!busy&&!speaking)setTimeout(()=>startListen(true),400);
 };
 rec=r;r.start();listening=true;paintHud();
 if(window.Notification&&Notification.permission==="default")Notification.requestPermission().catch(()=>{});
}
async function enterXr(){
 if(!xrCaps.ready)await detectXrCaps();
 const prefer=xrCaps.preferred||"hud";
 try{
  if(navigator.xr&&prefer!=="hud"){
   xrSess=await navigator.xr.requestSession(prefer,{optionalFeatures:["local-floor","bounded-floor","hand-tracking","dom-overlay"]});
   xrSess.addEventListener("end",()=>{xrSess=null;if(cfg.mode==="xr"){cfg.mode="go";saveCfg();paintHud();paintBtns()}});
   chip(prefer==="immersive-ar"?"AR session up — glance HUD + voice":"VR session up — voice primary");
   return prefer;
  }
 }catch(e){chip("XR session unavailable · HUD mode")}
 chip(xrCaps.ar||xrCaps.vr?"XR HUD (session blocked) · voice primary":"XR HUD on · smartwear-friendly voice");
 return"hud";
}
async function enterBestXr(){
 await detectXrCaps();
 return setMode("xr");
}
async function setMode(mode){
 const next=mode||"off";
 if(next==="xr"&&typeof window.grokCompanionOn==="function"&&!window.grokCompanionOn()){chip("Companion is off — ⚙ Settings → Companion");return}
 if(next===cfg.mode&&next!=="off"){cfg.mode="off";saveCfg();stopListen();stopSpeak();if(xrSess)try{xrSess.end()}catch(e){}paintHud();paintBtns();return}
 cfg.mode=next;saveCfg();
 ensureAudioCtx();
 await refreshTtsStatus();
 if(cfg.mode==="off"){stopListen();stopSpeak();if(xrSess)try{xrSess.end()}catch(e){}paintHud();paintBtns();return}
 if(cfg.mode==="xr")await enterXr();
 if(cfg.mode==="dictate")startListen(true);
 else if(cfg.mode==="go"||cfg.mode==="xr"){
  startListen(true);
  const intro=cfg.mode==="xr"?(xrCaps.ar?"AR mode on. Speak your task.":xrCaps.vr?"VR mode on. Speak your task.":"XR HUD on. Speak your task."):"Go mode on. Speak your task when ready.";
  speak(intro,"intro");
 }
 paintHud();paintBtns();
}
function toggleDictate(){setMode(cfg.mode==="dictate"?"off":"dictate")}
function injectHud(){
 if($("voiceHud"))return;
 const d=document.createElement("div");
 d.id="voiceHud";
 d.innerHTML='<div class="vh-card"><div class="vh-top"><span class="vh-mic" id="voiceHudMic" aria-hidden="true"></span><div class="vh-meta"><b id="voiceHudStatus">Voice off</b><span id="voiceHudSub">standby</span></div><button type="button" class="vh-x" id="voiceHudClose" title="Exit voice">×</button></div><div class="vh-line" id="voiceHudLine">Tap Go for hands-free · XR for smartwear</div><div class="vh-acts"><button type="button" id="vhGo">Go</button><button type="button" id="vhXr">XR / AR</button><button type="button" id="vhMic">Mic</button><button type="button" id="vhStopSpeak">Quiet</button><label class="vh-voice">Voice <select id="voiceVoiceSel">'+VOICES.map(v=>'<option value="'+v+'">'+v+'</option>').join("")+"</select></label></div></div>";
 document.body.appendChild(d);
 $("voiceHudClose").onclick=()=>setMode("off");
 $("vhGo").onclick=()=>setMode("go");
 $("vhXr").onclick=()=>setMode("xr");
 $("vhMic").onclick=()=>listening?stopListen():startListen(cfg.mode!=="dictate");
 $("vhStopSpeak").onclick=()=>stopSpeak();
 const sel=$("voiceVoiceSel");
 if(sel){sel.value=cfg.voiceId;sel.onchange=()=>{cfg.voiceId=sel.value;saveCfg()}}
}
async function boot(){
 loadCfg();
 injectHud();
 paintHud();
 await detectXrCaps();
 refreshTtsStatus();
 const q=new URLSearchParams(location.search);
 if(q.get("xr")==="1"||q.get("ar")==="1"){setTimeout(()=>setMode("xr"),400);return}
 if(q.get("go")==="1"||q.get("voice")==="1"){setTimeout(()=>setMode("go"),400);return}
 if(xrCaps.uaWearable||xrCaps.smallScreen){
  if(cfg.mode==="off")setTimeout(()=>setMode(xrCaps.xr?"xr":"go"),500);
  else setTimeout(()=>setMode(cfg.mode),500);
  return;
 }
 if(cfg.mode==="go"||cfg.mode==="xr"||cfg.mode==="dictate")setTimeout(()=>setMode(cfg.mode),500);
 else paintBtns();
}
window.grokVoice={
 setMode,toggleDictate,startListen,stopListen,speak,stopSpeak,onTaskSent,onTurnDone,setBusyFlag,summarizeForVoice,refreshTtsStatus,detectXrCaps,enterBestXr,enterXr,
 get mode(){return cfg.mode},
 get cfg(){return cfg},
 get xrCaps(){return xrCaps},
 paintHud,paintBtns
};
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);else boot();
})();
