export function initMotion(ctx){
  const {THREE,getMixer,getClips,getActIdle,setActIdle,panels}=ctx;
  const state=ctx.state||{gestureHold:0,gazeTarget:null,gazeUntil:0};
  const gestureOut=new Map(),fetchedClips=new Set(),warming=new Map();
  const HOME="standing_w_briefcase_idle";
  let mws=null,pendingPlays=[],actGesture=null,pendingBase=null,clipIx={},mixerHooked=false,pbTimer=null,curBase=HOME,baseHold=0;
  const HEAD=new Set(["module_check","machinamachina_spark"]),GUITAR=new Set(["module_check","machinamachina_spark","bow_apology","chin_think","hand_on_heart","blow_kiss"]),SOFT=new Set(["module_check","machinamachina_spark","chin_think","waist_side_stretch","sun_salute","interact","bow_apology"]),LEFT=new Set(["waist_side_stretch","sun_salute","chin_think","interact"]),RIGHT=new Set(["look_over_shoulder","dismissing_gesture","point_ahead","salute","wave_hello","hand_on_heart","bow_apology","blow_kiss"]);
  function clientPropOk(clip){
    if(curBase==="guitar_playing")return GUITAR.has(clip);
    if(curBase==="talking_on_phone")return SOFT.has(clip);
    if(curBase===HOME)return !LEFT.has(clip)&&clip!=="agree"&&clip!=="surprised"&&clip!=="standing_clap";
    return true;
  }
  function holdGaze(clip){return HEAD.has(clip)||clip==="look_over_shoulder"||clip==="hand_on_heart"||clip==="chin_think"||clip==="blow_kiss"}
  function keepIdle(clip){return holdGaze(clip)||(curBase===HOME&&RIGHT.has(clip))||(curBase==="talking_on_phone"&&SOFT.has(clip))||(curBase==="guitar_playing"&&GUITAR.has(clip))}
  function travelSkip(n){return /(sit|lay|crouch|plank|walk|run|jog|sprint|dance|twerk|shuffle|kneel|pray|squat|angry|jump|jab_cross|beckon|punch)/i.test(n||"")}
  fetch("/static/clip_index.json",{cache:"no-store"}).then(r=>r.json()).then(j=>{clipIx=j.clips||{}}).catch(()=>{});
  function warmPool(){
    fetch(httpBase()+"/motion/alive",{cache:"no-store"}).then(r=>r.json()).then(j=>{
      const g=j.guitar_life||[];
      if(g.length){GUITAR.clear();g.forEach(n=>GUITAR.add(n))}
      const s=j.life_soft||[];
      if(s.length){SOFT.clear();s.forEach(n=>SOFT.add(n))}
      const r=j.arm_right||[];
      if(r.length){RIGHT.clear();r.forEach(n=>RIGHT.add(n))}
      const l=j.arm_left||[];
      if(l.length){LEFT.clear();l.forEach(n=>LEFT.add(n))}
      const h=j.hold_gaze||[];
      if(h.length){HEAD.clear();h.forEach(n=>HEAD.add(n))}
      const names=[HOME,...(j.idles||[]),...(j.life||[]),...(j.life_soft||[]),...(j.life_head||[]),...g,...r];
      [...new Set(names)].forEach(n=>{if(n)warm(n)});
    }).catch(()=>{});
  }
  const httpBase=()=>"http"+(location.protocol==="https:"?"s":"")+"://"+location.hostname+":2423";
  const wsBase=()=>location.protocol.replace("http","ws")+"//"+location.hostname+":2423";
  const linked=()=>!!(mws&&mws.readyState===1);
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
  function hookMixer(){
    const mixer=getMixer();
    if(!mixer||mixerHooked===mixer)return;
    mixerHooked=mixer;
    mixer.addEventListener("finished",ev=>{if(ev.action===actGesture)endGesture(ev.action)});
  }
  function flushBase(){
    pbTimer=null;
    const pb=pendingBase;pendingBase=null;
    if(pb)motionPlay(pb[0],"base",pb[1]);
  }
  function queueBase(name,fade){
    pendingBase=[name,fade];
    const wait=Math.max(40,baseHold-performance.now()+40);
    if(pbTimer)clearTimeout(pbTimer);
    pbTimer=setTimeout(flushBase,wait);
  }
  function endGesture(a){
    if(actGesture!==a)return;
    if(gestureOut.has(a)){clearTimeout(gestureOut.get(a));gestureOut.delete(a)}
    const last=state.lastGesture||"";
    if(!keepIdle(last)||holdGaze(last))state.gestureHold=performance.now()+480;
    if(!keepIdle(last))baseHold=performance.now()+480;
    try{a.fadeOut(0.45)}catch(e){}
    setTimeout(()=>{try{a.stop();a.enabled=false}catch(e){}},480);
    if(actGesture===a)actGesture=null;
    if(pendingBase)queueBase(pendingBase[0],pendingBase[1]);
    const idl=getActIdle();
    if(idl){
      idl.paused=false;if(idl.timeScale===0)idl.timeScale=0.94+Math.random()*0.14;idl.enabled=true;idl.setEffectiveWeight(1);
      if(!keepIdle(state.lastGesture||""))idl.fadeIn(0.45)
    }
  }
  function stopGestures(keep){
    for(const [act,tid] of [...gestureOut]){
      if(act===keep)continue;
      clearTimeout(tid);gestureOut.delete(act);
      try{act.fadeOut(0.25)}catch(e){}
    }
    if(actGesture&&actGesture!==keep){
      try{actGesture.fadeOut(0.25)}catch(e){}
    }
  }
  function motionPlay(name,layer,fade){
    const mixer=getMixer();
    if(!mixer){pendingPlays.push([name,layer,fade]);return}
    hookMixer();
    if(layer==="base"&&(travelSkip(name)||!canLoop(name)))name=HOME;
    if(layer!=="base"&&(travelSkip(name)||!clientPropOk(name)))return;
    if(layer==="base"&&performance.now()<baseHold){queueBase(name,fade);return}
    const c=findClip(name);
    if(!c){warm(name).then(ok=>{if(ok)motionPlay(name,layer,fade)});return}
    stripRoot(c);
    const a=mixer.clipAction(c);
    fade=fade||0.4;
    if(layer==="base"){
      curBase=name;
      if(pbTimer){clearTimeout(pbTimer);pbTimer=null}
      pendingBase=null;
      if(getActIdle()===a){
        a.paused=false;a.enabled=true;a.setEffectiveWeight(1);
        a.timeScale=0.94+Math.random()*0.14;
        if(c.duration>1)a.time=(a.time+Math.random()*Math.min(2,c.duration*0.15))%Math.max(0.01,c.duration);
        return;
      }
      if(actGesture){
        const g=actGesture;actGesture=null;
        if(gestureOut.has(g)){clearTimeout(gestureOut.get(g));gestureOut.delete(g)}
        try{g.fadeOut(0.25)}catch(e){}
        setTimeout(()=>{try{g.stop();g.enabled=false}catch(e){}},280);
      }
      a.paused=false;
      a.enabled=true;
      a.reset().setLoop(THREE.LoopRepeat,Infinity).setEffectiveWeight(1);
      a.timeScale=0.94+Math.random()*0.14;
      if(c.duration>4)a.time=Math.random()*Math.min(2.5,c.duration*0.12);
      else if(c.duration>0.5)a.time=Math.random()*c.duration*0.2;
      a.play();
      const prev=getActIdle();
      if(prev&&prev!==a){
        prev.paused=false;
        if(prev.timeScale===0)prev.timeScale=0.94;
        const fadeS=Math.max(fade,0.5);
        prev.crossFadeTo(a,fadeS,false);
        const dying=prev;
        setTimeout(()=>{if(dying!==getActIdle()){try{dying.stop();dying.enabled=false}catch(e){}}},fadeS*1000+120);
      }
      setActIdle(a);
    }else{
      stopGestures(a);
      a.enabled=true;
      a.reset().setLoop(THREE.LoopOnce,1);
      a.clampWhenFinished=true;
      let ts=0.92+Math.random()*0.16;
      if(keepIdle(name)&&(c.duration||1.2)>2.8)ts=Math.max(ts,(c.duration||1.2)/2.6);
      a.timeScale=ts;
      if(c.duration>0.4)a.time=Math.random()*Math.min(0.15,c.duration*0.1);
      const holdMs=Math.max(700,Math.min(keepIdle(name)?2800:8000,((c.duration||1.2)-a.time)/ts*1000));
      if(keepIdle(name))a.setEffectiveWeight(1).play();
      else a.setEffectiveWeight(1).fadeIn(Math.min(0.35,fade)).play();
      const idle=getActIdle();
      if(idle){
        if(keepIdle(name)){idle.paused=false;if(idle.timeScale===0)idle.timeScale=0.94+Math.random()*0.14;idle.enabled=true;idle.setEffectiveWeight(1)}
        else{idle.timeScale=0;idle.fadeOut(0.28)}
      }
      actGesture=a;
      if(holdGaze(name)||!keepIdle(name))state.gestureHold=performance.now()+holdMs;
      if(!keepIdle(name))baseHold=performance.now()+holdMs;
      state.lastGesture=name;
      document.title=document.title.replace(/ \| .*$/,"")+" | "+name;
      if(gestureOut.has(a))clearTimeout(gestureOut.get(a));
      gestureOut.set(a,setTimeout(()=>endGesture(a),Math.max(400,holdMs-450)));
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
      if(d.type==="play"){if(d.layer==="base")curBase=d.clip;motionPlay(d.clip,d.layer,d.fade||0.4);if(hud){hud[d.layer==="base"?"base":"gesture"]=d.clip;hud.seq=d.seq||hud.seq}}
      if(d.type==="state"&&d.base){
        curBase=d.base;
        const idl=getActIdle();
        const nm=(idl&&idl.getClip&&idl.getClip().name||"").toLowerCase();
        if(!idl||nm!==String(d.base).toLowerCase())motionPlay(d.base,"base",0.5);
        if(hud)hud.base=d.base
      }
      if(d.type==="gaze"){state.gazeTarget=d.target;state.gazeUntil=performance.now()+5500;if(hud){hud.gaze=d.target;hud.seq=d.seq||hud.seq}}
    };
    mws.onclose=()=>setTimeout(connect,3000);
    mws.onerror=()=>{try{mws.close()}catch(e){}};
  }
  function flushPending(){const q=pendingPlays.splice(0);for(const p of q)motionPlay(...p)}
  warm(HOME).then(ok=>{if(ok&&!getActIdle())motionPlay(HOME,"base",0.35)});
  ["talking_on_phone","guitar_playing","agree","look_over_shoulder","waist_side_stretch","hand_on_heart","surprised","dismissing_gesture","point_ahead","salute","module_check","sun_salute","bow_apology","excited_bounce","machinamachina_spark","chin_think","blow_kiss","standing_clap","wave_hello","interact"].forEach(n=>warm(n));
  warmPool();
  return {motionPlay,sendMotion,connect,flushPending,findClip,linked,state};
}
