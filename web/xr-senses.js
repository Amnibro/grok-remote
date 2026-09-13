export const DEFAULTS={names:["rikku","hey you","companion"],minGapMs:45000,maxPerHour:12,arriveQuietMs:90000,leaveQuietMs:120000,motionThresh:9,envPollMs:10000,silenceMs:20*60000,greetGapMs:10*60000};
export const REFLEX={arrive:[["gaze","user"],["motion","wave_hello"]],leave:[["gaze","away"]],addressed:[["gaze","user"]],work_done:[["gaze","user"],["motion","agree"]],work_error:[["gaze","user"],["motion","look_over_shoulder"]],ask_open:[["gaze","user"]],focus_change:[["gaze","away"]],overheard_name:[["gaze","user"]]};
export const DELIBERATE=new Set(["arrive","work_done","work_error","ask_open","long_silence","overheard_name","return"]);
export function addressed(text,names){
 const t=String(text||"").toLowerCase().replace(/[^a-z0-9' ]+/g," ").replace(/\s+/g," ").trim();
 if(!t)return {hit:false,text:""};
 for(const n of names||[]){
  const k=String(n).toLowerCase().trim();if(!k)continue;
  const i=t.indexOf(k);
  if(i<0)continue;
  const rest=t.slice(i+k.length).trim().replace(/^[, ]+/,"");
  return {hit:true,name:k,text:rest||t};
 }
 return {hit:false,text:t};
}
export function mentions(text,names){return addressed(text,names).hit}
export function makeBudget(o={}){
 const cfg=Object.assign({},DEFAULTS,o);const fired=[];
 return {
  ok(now){const hr=now-3600000;while(fired.length&&fired[0]<hr)fired.shift();return (!fired.length||now-fired[fired.length-1]>=cfg.minGapMs)&&fired.length<cfg.maxPerHour},
  spend(now){fired.push(now)},
  count(){return fired.length}
 };
}
export function motionScore(prev,cur,w,h){
 if(!prev)return 0;
 let acc=0,n=0;
 for(let i=0;i<w*h*4;i+=16){acc+=Math.abs(cur[i]-prev[i])+Math.abs(cur[i+1]-prev[i+1])+Math.abs(cur[i+2]-prev[i+2]);n++}
 return n?acc/n:0;
}
export function situation(p,env,mem){
 const fg=env&&env.foreground&&env.foreground.title?` He is looking at "${env.foreground.title.slice(0,70)}".`:"";
 const w=env&&env.work||{};
 const busy=w.running?` ${w.running} agent job${w.running>1?"s":""} running (${(w.running_titles||[]).join("; ").slice(0,120)}).`:"";
 const heard=mem&&mem.overheard&&mem.overheard.length?` Overheard lately: ${mem.overheard.slice(-3).map(x=>'"'+x.slice(0,60)+'"').join(", ")}.`:"";
 const base={
  arrive:"Anthony just came into view after being away.",
  return:"Anthony just came back after being away a while.",
  leave:"Anthony just left the room.",
  work_done:`A job you were running just finished: ${((p.titles&&p.titles.length?p.titles:w.just_finished)||[]).join("; ").slice(0,120)||"(untitled)"}.`,
  work_error:`A tool just failed: ${p.tool||(w.latest_tool?w.latest_tool.title:"(unknown)")}.`,
  ask_open:`One of your jobs is waiting on him: ${(w.open_asks||[]).map(a=>a.text).join(" | ").slice(0,160)}.`,
  long_silence:"It has been quiet for twenty minutes while he sat there working.",
  overheard_name:`He said your name to someone else, or muttered it: "${String(p.text||"").slice(0,120)}".`
 }[p.type]||`Something happened: ${p.type}.`;
 return `[Situation, ${env&&env.clock?env.clock+", ":""}not a message from him: ${base}${fg}${busy}${heard} React as the person in the room would, in one or two short spoken sentences, or reply exactly [[quiet]] if a real person would stay silent here. Do not describe this note.]`;
}
export function initSenses(ctx){
 const {ask,react,panels,sendMotion,speaking,thinking,KEY,names,log,onState}=ctx;
 const cfg=Object.assign({},DEFAULTS,{names:names&&names.length?names:DEFAULTS.names});
 const S={on:false,ears:false,eyes:false,present:null,lastMotion:0,lastSeen:0,lastGreet:0,lastInteract:Date.now(),percepts:[],overheard:[],env:null,envSig:"",cam:null,rec:null,recWant:false,recRestart:0,budget:makeBudget(cfg),stats:{reflex:0,deliberate:0,quiet:0,frames:0}};
 const key=KEY?"?key="+encodeURIComponent(KEY):"";
 const say=log||(()=>{});
 const emit=v=>{try{onState&&onState(S)}catch(e){}};
 const push=(type,extra)=>{const p=Object.assign({type,at:Date.now()},extra||{});S.percepts.push(p);if(S.percepts.length>200)S.percepts.shift();handle(p);emit();return p};
 function reflex(p){
  const rs=REFLEX[p.type];if(!rs)return;
  const now=Date.now();
  for(const [k,v] of rs){
   if(k==="motion"&&(now-S.lastGreet<cfg.greetGapMs&&p.type==="arrive"))continue;
   try{sendMotion(k,v)}catch(e){}
  }
  if(p.type==="arrive")S.lastGreet=now;
  S.stats.reflex++;
 }
 async function deliberate(p){
  if(!DELIBERATE.has(p.type))return;
  const now=Date.now();
  if(speaking&&speaking())return;
  if(thinking&&thinking())return;
  if(p.type!=="arrive"&&p.type!=="return"&&S.present===false)return;
  if(!S.budget.ok(now)){say("senses: budget held "+p.type);return}
  S.budget.spend(now);S.stats.deliberate++;
  const text=situation(p,S.env,{overheard:S.overheard});
  try{
   const out=await react(text,p);
   if(out&&out.quiet)S.stats.quiet++;
  }catch(e){say("senses: react failed "+(e&&e.message||e))}
 }
 function handle(p){
  if(p.type==="addressed"){S.lastInteract=Date.now();reflex(p);ask(p.text);return}
  reflex(p);deliberate(p);
 }
 async function startEyes(){
  if(S.eyes)return true;
  try{
   let c=panels&&panels.getCam&&panels.getCam();
   let video=c&&c.video&&c.video.videoWidth?c.video:null;
   if(!video){
    const st=await navigator.mediaDevices.getUserMedia({video:{width:320,height:180},audio:false});
    video=document.createElement("video");video.muted=true;video.playsInline=true;video.srcObject=st;await video.play();
    S.cam={stream:st,video};
   }
   const cv=document.createElement("canvas"),w=64,h=36;cv.width=w;cv.height=h;const g=cv.getContext("2d",{willReadFrequently:true});
   let prev=null;
   S.eyes=true;
   const tick=()=>{
    if(!S.eyes)return;
    try{
     g.drawImage(video,0,0,w,h);const cur=g.getImageData(0,0,w,h).data;
     const sc=motionScore(prev,cur,w,h);prev=new Uint8ClampedArray(cur);S.stats.frames++;
     const now=Date.now();
     if(sc>cfg.motionThresh){
      const quiet=now-S.lastMotion;
      S.lastMotion=now;
      if(S.present!==true){
       const away=now-(S.lastSeen||0);
       S.present=true;
       push(S.lastSeen&&away>cfg.greetGapMs?"return":"arrive",{score:Math.round(sc),quietMs:quiet});
      }
      S.lastSeen=now;
     }else if(S.present===true&&now-S.lastMotion>cfg.leaveQuietMs){S.present=false;push("leave",{quietMs:now-S.lastMotion})}
    }catch(e){}
    setTimeout(tick,500);
   };
   tick();emit();return true;
  }catch(e){say("senses: camera "+(e&&e.message||e));return false}
 }
 function stopEyes(){S.eyes=false;if(S.cam){try{S.cam.stream.getTracks().forEach(t=>t.stop())}catch(e){}S.cam=null}emit()}
 function startEars(){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR||!window.isSecureContext){say("senses: hands-free ears need https or localhost");return false}
  S.recWant=true;
  const spin=()=>{
   if(!S.recWant)return;
   const r=new SR();r.lang="en-US";r.interimResults=false;r.continuous=true;
   let buf="";
   r.onresult=e=>{
    for(let i=e.resultIndex;i<e.results.length;i++){const res=e.results[i];if(!res.isFinal)continue;const t=String(res[0].transcript||"").trim();if(!t)continue;hear(t)}
   };
   r.onerror=e=>{const why=e&&e.error||"";if(why==="not-allowed"||why==="service-not-allowed"){S.recWant=false;say("senses: mic refused")}};
   r.onend=()=>{S.ears=false;emit();if(S.recWant){const wait=Date.now()-S.recRestart<2000?1500:250;S.recRestart=Date.now();setTimeout(spin,wait)}};
   try{r.start();S.rec=r;S.ears=true;emit()}catch(e){S.ears=false;setTimeout(spin,2000)}
  };
  spin();return true;
 }
 function stopEars(){S.recWant=false;try{S.rec&&S.rec.stop()}catch(e){}S.ears=false;emit()}
 function hear(t){
  if(speaking&&speaking())return;
  const a=addressed(t,cfg.names);
  S.lastInteract=Date.now();
  if(a.hit&&a.text&&a.text.split(" ").length>=2)push("addressed",{text:a.text,raw:t});
  else if(a.hit)push("overheard_name",{text:t});
  else{S.overheard.push(t);if(S.overheard.length>12)S.overheard.shift();push("overheard",{text:t})}
 }
 let envTimer=null;
 async function pollEnv(){
  try{
   const r=await fetch("/api/companion/env"+key,{cache:"no-store"});
   if(!r.ok)throw new Error("env "+r.status);
   const env=await r.json();const prev=S.env;S.env=env;
   const fg=(env.foreground&&env.foreground.title||"");
   const sig=fg.slice(0,60);
   if(prev&&S.envSig&&sig!==S.envSig&&fg)push("focus_change",{title:fg});
   S.envSig=sig;
   const w=env.work||{},pw=prev&&prev.work||{};
   if(prev&&pw.running>0&&w.running===0&&(w.just_finished||[]).length)push("work_done",{titles:w.just_finished});
   if(w.latest_tool&&/fail|error/i.test(w.latest_tool.status||"")&&(!pw.latest_tool||pw.latest_tool.title!==w.latest_tool.title))push("work_error",{tool:w.latest_tool.title});
   if((w.open_asks||[]).length&&!(pw.open_asks||[]).length)push("ask_open",{asks:w.open_asks});
   if(S.present===true&&Date.now()-S.lastInteract>cfg.silenceMs){S.lastInteract=Date.now();push("long_silence")}
  }catch(e){}
  emit();
 }
 async function start(o={}){
  S.on=true;
  if(o.eyes!==false)await startEyes();
  if(o.ears!==false)startEars();
  if(!envTimer){pollEnv();envTimer=setInterval(pollEnv,cfg.envPollMs)}
  emit();return S;
 }
 function stop(){S.on=false;stopEyes();stopEars();if(envTimer){clearInterval(envTimer);envTimer=null}emit()}
 return {start,stop,startEyes,stopEyes,startEars,stopEars,inject:(type,extra)=>push(type,extra),hear,state:()=>S,cfg,pollEnv};
}
