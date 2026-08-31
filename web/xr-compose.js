const ALLOWED=new Set("spine spine1 spine2 neck head leftshoulder leftarm leftforearm lefthand rightshoulder rightarm rightforearm righthand leftupleg leftleg leftfoot rightupleg rightleg rightfoot".split(" "));
export function initCompose(ctx){
  const {THREE,getSkeleton,getRestQ,getClips,setClips,motionPlay,KEY,onStats,solidShot}=ctx;
  function measure(clip,skeleton,restQ){
    const hands=skeleton.bones.filter(b=>/hand$/i.test(b.name));
    const saved=skeleton.bones.map(b=>b.quaternion.clone());
    const q=new THREE.Quaternion(),p=new THREE.Vector3();
    let peakDeg=0,peakBone="",travel=0;
    const n=clip.tracks.length?clip.tracks[0].times.length:0;
    const apply=k=>{
      for(const tr of clip.tracks){
        const b=skeleton.bones.find(x=>x.name===tr.name.replace(/\.quaternion$/,""));
        if(b)b.quaternion.fromArray(tr.values,k*4);
      }
      skeleton.bones[0].updateMatrixWorld(true);
    };
    if(n)apply(0);
    const home=hands.map(b=>b.getWorldPosition(new THREE.Vector3()));
    for(let k=0;k<n;k++){
      for(const tr of clip.tracks){
        const bn=tr.name.replace(/\.quaternion$/,"");
        const b=skeleton.bones.find(x=>x.name===bn);
        if(!b)continue;
        q.fromArray(tr.values,k*4);
        b.quaternion.copy(q);
        const r=restQ.get(b.name);
        if(r){
          const d=Math.acos(Math.min(1,Math.abs(q.dot(r))))*2*180/Math.PI;
          if(d>peakDeg){peakDeg=d;peakBone=bn.replace(/^mixamorig:?/,"")}
        }
      }
      skeleton.bones[0].updateMatrixWorld(true);
      hands.forEach((b,i)=>{travel=Math.max(travel,b.getWorldPosition(p).distanceTo(home[i]))});
    }
    skeleton.bones.forEach((b,i)=>b.quaternion.copy(saved[i]));
    skeleton.bones[0].updateMatrixWorld(true);
    return {peakDeg:+peakDeg.toFixed(1),peakBone,travelCm:+(travel*100).toFixed(1),keys:n,dur:+clip.duration.toFixed(2)};
  }
  return function composeClip(spec){
    try{
      const skeleton=getSkeleton(),restQ=getRestQ();
      if(!restQ||!skeleton)return;
      const parts=spec.split("|");
      const name=parts[0].trim().toLowerCase().replace(/[^a-z0-9_]/g,"");
      if(!name)return;
      const times=[0],poses=[{}],touched=new Set(),skipped=new Set();
      for(let i=1;i<parts.length;i++){
        const ci=parts[i].indexOf(":");
        if(ci<0)continue;
        const t=Math.max(1,parseInt(parts[i].slice(0,ci),10)||0)/1000;
        const body=parts[i].slice(ci+1).trim();
        const pose={};
        if(!/^rest$/i.test(body))
          for(const seg of body.split(/\s+/)){
            const mm=seg.match(/^(\w+)=(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)$/);
            if(!mm)continue;
            const bn=mm[1].toLowerCase();
            if(!ALLOWED.has(bn)){skipped.add(mm[1]);continue}
            pose[bn]=[Math.round(+mm[2]),Math.round(+mm[3]),Math.round(+mm[4])];
            touched.add(bn);
          }
        times.push(t);poses.push(pose);
      }
      if(times.length<2||!touched.size)return;
      const tracks=[],e=new THREE.Euler(),q=new THREE.Quaternion();
      for(const short of touched){
        const bone=skeleton.bones.find(b=>b.name.toLowerCase().replace("mixamorig","").replace(":","")===short)||skeleton.bones.find(b=>b.name.toLowerCase().includes(short));
        if(!bone)continue;
        const rq=restQ.get(bone.name);
        if(!rq)continue;
        const vals=[];
        let cur=[0,0,0];
        for(let k=0;k<times.length;k++){
          const p=poses[k];
          if(k>0&&Object.keys(p).length===0)cur=[0,0,0];
          else if(p[short])cur=p[short];
          e.set(cur[0]*Math.PI/180,cur[1]*Math.PI/180,cur[2]*Math.PI/180);
          q.setFromEuler(e).premultiply(rq);
          vals.push(q.x,q.y,q.z,q.w);
        }
        tracks.push(new THREE.QuaternionKeyframeTrack(bone.name+".quaternion",times,vals));
      }
      if(!tracks.length)return;
      const clip=new THREE.AnimationClip(name,-1,tracks);
      try{onStats&&onStats(name,Object.assign(measure(clip,skeleton,restQ),{skipped:[...skipped]}))}catch(e3){}
      setClips(getClips().filter(c=>c.name!==name).concat([clip]));
      motionPlay(name,"gesture",0.45);
      fetch("http"+(location.protocol==="https:"?"s":"")+"://"+location.hostname+":2423/motion/clip",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({name,data:THREE.AnimationClip.toJSON(clip)})}).catch(()=>{});
      setTimeout(()=>{
        try{
          const shot=solidShot&&solidShot();
          const cv=shot?null:document.querySelector("canvas");
          if(shot)fetch("/api/xr/see"+(KEY?"?key="+encodeURIComponent(KEY):""),{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({jpeg:shot})}).catch(()=>{});
          else if(cv)fetch("/api/xr/see"+(KEY?"?key="+encodeURIComponent(KEY):""),{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({jpeg:cv.toDataURL("image/jpeg",0.7)})}).catch(()=>{});
        }catch(e2){}
      },Math.min(2000,clip.duration*500+300));
    }catch(err){}
  };
}
