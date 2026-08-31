export function initMotion(ctx){
  const {THREE,getMixer,getClips,getActIdle,setActIdle,panels}=ctx;
  const state=ctx.state||{gestureHold:0,gazeTarget:null,gazeUntil:0};
  const gestureOut=new Map(),fetchedClips=new Set(),warming=new Map();
  let mws=null,pendingPlays=[],actGesture=null,clipIx={};
  fetch("/static/clip_index.json",{cache:"no-store"}).then(r=>r.json()).then(j=>{clipIx=j.clips||{}}).catch(()=>{});
  const httpBase=()=>"http"+(location.protocol==="https:"?"s":"")+"://"+location.hostname+":2423";
  const wsBase=()=>location.protocol.replace("http","ws")+"//"+location.hostname+":2423";
  const linked=()=>!!(mws&&mws.readyState===1);
  const HOME="standing_w_briefcase_idle";
  function findClip(n){n=(n||"").toLowerCase();const cl=getClips();return cl.find(c=>c.name.toLowerCase()===n)||null}
  function stripRoot(c){
    if(!c||!c.tracks)return c;
    c.tracks=c.tracks.filter(t=>!/\.position$/i.test(t.name||""));
    for(const tr of c.tracks){
      if(!tr||!/\.quaternion$/i.test(tr.name||"")||!tr.values)continue;
      const v=tr.values;
      for(let i=0;i+3<v.length;i+=4){
        const n=Math.hypot(v[i],v[i+1],v[i+2],v[i+3])||1;
        v[i]/=n;v[i+1]/=n;v[i+2]/=n;v[i+3]/=n;
      }
    }
    return c;
  }
  function canLoop(name){
    const m=clipIx[(name||"").toLowerCase()]||clipIx[name];
    if(!m)return true;
    return m.loops!==false&&!(m.seam>40);
  }
  function stopGestures(keep){
    if(actGesture&&actGesture!==keep){
      try{actGesture.fadeOut(0.25)}catch(e){}
    }
  }
  function motionPlay(name,layer,fade){
    const mixer=getMixer();
    if(!mixer){pendingPlays.push([name,layer,fade]);return}
    if(layer==="base"&&!canLoop(name))name=HOME;
    const c=findClip(name);
    if(!c){warm(name).then(ok=>{if(ok)motionPlay(name,layer,fade)});return}
    stripRoot(c);
    const a=mixer.clipAction(c);
    fade=fade||0.4;
    if(layer==="base"){
      if(getActIdle()===a)return;
      a.enabled=true;
      a.reset().setLoop(THREE.LoopRepeat,Infinity).setEffectiveWeight(1);
      a.timeScale=0.88+Math.random()*0.28;
      if(c.duration>0.5)a.time=Math.random()*c.duration;
      a.play();
      const prev=getActIdle();
      if(prev&&prev!==a){
        prev.crossFadeTo(a,Math.max(fade,0.85),false);
        const dying=prev;
        setTimeout(()=>{if(dying!==getActIdle()){try{dying.stop();dying.enabled=false}catch(e){}}},950);
      }
      setActIdle(a);
    }else{
      stopGestures(a);
      a.enabled=true;
      a.reset().setLoop(THREE.LoopOnce,1);
      a.clampWhenFinished=true;
      const holdMs=Math.max(700,Math.min(8000,(c.duration||1.2)*1000));
      a.setEffectiveWeight(1).fadeIn(Math.min(0.35,fade)).play();
      const idle=getActIdle();
      if(idle)idle.setEffectiveWeight(0);
      actGesture=a;
      state.gestureHold=performance.now()+holdMs;
      state.lastGesture=name;
      document.title=document.title.replace(/ \| .*$/,"")+" | "+name;
      if(gestureOut.has(a))clearTimeout(gestureOut.get(a));
      gestureOut.set(a,setTimeout(()=>{
        gestureOut.delete(a);
        try{a.fadeOut(0.45)}catch(e){}
        setTimeout(()=>{try{a.stop();a.enabled=false}catch(e){}},480);
        const idl=getActIdle();
        if(idl){idl.enabled=true;idl.setEffectiveWeight(1);idl.fadeIn(0.45)}
        if(actGesture===a)actGesture=null;
      },Math.max(400,holdMs-450)));
    }
  }
  function warm(name){
    if(findClip(name))return Promise.resolve(true);
    if(warming.has(name))return warming.get(name);
    const p=(async()=>{
      fetchedClips.add(name);
      try{
        const d=await (await fetch(httpBase()+"/motion/clipdata/"+encodeURIComponent(name)+"?t="+Date.now(),{cache:"no-store"})).json();
        if(!d||!d.tracks){fetchedClips.delete(name);return false}
        const c=THREE.AnimationClip.parse(d);
        c.name=name;
        stripRoot(c);
        getClips().push(c);
        return true;
      }catch(e){fetchedClips.delete(name);return false}
      finally{warming.delete(name)}
    })();
    warming.set(name,p);
    return p;
  }
  function sendMotion(kind,val){
    fetch(httpBase()+"/motion/"+(kind==="gaze"?"gaze":"play"),{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(kind==="gaze"?{target:val.trim()}:{clip:val.trim()})}).catch(()=>{});
  }
  function connect(){
    try{mws=new WebSocket(wsBase()+"/pose")}catch(e){setTimeout(connect,5000);return}
    mws.onmessage=ev=>{
      let d;
      try{d=JSON.parse(ev.data)}catch(e){return}
      const hud=panels.hud();
      if(d.type==="play"){motionPlay(d.clip,d.layer,d.fade||0.4);if(hud){hud[d.layer==="base"?"base":"gesture"]=d.clip;hud.seq=d.seq||hud.seq}}
      if(d.type==="state"&&d.base){motionPlay(d.base,"base",0.5);if(hud)hud.base=d.base}
      if(d.type==="gaze"){state.gazeTarget=d.target;if(hud){hud.gaze=d.target;hud.seq=d.seq||hud.seq}}
    };
    mws.onclose=()=>setTimeout(connect,3000);
    mws.onerror=()=>{try{mws.close()}catch(e){}};
  }
  function flushPending(){const q=pendingPlays.splice(0);for(const p of q)motionPlay(...p)}
  warm(HOME).then(ok=>{if(ok)motionPlay(HOME,"base",0.35)});
  ["talking_on_phone","guitar_playing","agree","look_over_shoulder","waist_side_stretch","wave_hello","surprised","dismissing_gesture","point_ahead","salute","module_check","sun_salute","bow_apology","excited_bounce","machinamachina_spark","chin_think","blow_kiss","female_walk"].forEach(n=>warm(n));
  return {motionPlay,sendMotion,connect,flushPending,findClip,linked,state};
}
