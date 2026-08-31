export function initPose(ctx){
  const {THREE,getSkeleton}=ctx;
  const IDLE={Hips:(s,c)=>[0.01,s*0.07,0],Spine2:(s,c)=>[0.04+c*0.025,s*0.05,0],Neck:(s,c)=>[0.03,s*0.08,0],Head:(s,c)=>[0.05+c*0.04,s*0.14,c*0.03],LeftArm:(s,c)=>[0.28+s*0.32,0.04,0.38],RightArm:(s,c)=>[0.28-s*0.32,-0.04,-0.38],LeftForeArm:(s,c)=>[0.42+s*0.12,0,0],RightForeArm:(s,c)=>[0.42-s*0.12,0,0],LeftUpLeg:(s,c)=>[0.06+s*0.05,0,0.03],RightUpLeg:(s,c)=>[0.06-s*0.05,0,-0.03],LeftLeg:(s,c)=>[0.1+Math.max(0,-s)*0.08,0,0],RightLeg:(s,c)=>[0.1+Math.max(0,s)*0.08,0,0]};
  const TALK={Head:(s,c)=>[0.08+s*0.1,c*0.12,s*0.05],Neck:(s,c)=>[0.05,s*0.06,0],Spine2:(s,c)=>[0.06+s*0.04,s*0.06,0],RightArm:(s,c)=>[0.45+s*0.4,-0.08,-0.7-s*0.15],RightForeArm:(s,c)=>[0.7+s*0.25,0,0],LeftArm:(s,c)=>[0.22,0.05,0.32],LeftForeArm:(s,c)=>[0.35,0,0]};
  const idlePose=(n,t,d)=>{const u=(t/d)*Math.PI*2,f=IDLE[n];return f?f(Math.sin(u),Math.cos(u)):[0,0,0]};
  const talkPose=(n,t,d)=>{const u=(t/d)*Math.PI*2,f=TALK[n];return f?f(Math.sin(u),Math.cos(u*2)):idlePose(n,t,d)};
  function makeBodyClip(name,dur,pose,segs){
    const sk=getSkeleton();
    if(!sk||!sk.bones.length)return null;
    const n=segs||12,times=[];
    for(let i=0;i<=n;i++)times.push(dur*i/n);
    const q=new THREE.Quaternion(),e=new THREE.Euler();
    const tracks=sk.bones.map(b=>{
      const arr=[];
      times.forEach(t=>{const p=pose(b.name,t,dur);q.setFromEuler(e.set(p[0],p[1],p[2],"XYZ"));arr.push(q.x,q.y,q.z,q.w)});
      return new THREE.QuaternionKeyframeTrack(b.name+".quaternion",times,arr);
    });
    return new THREE.AnimationClip(name,dur,tracks);
  }
  function seamOf(clip){
    let worst=0,name="";
    for(const tr of clip.tracks){
      const v=tr.values,n=v.length;
      if(n<8)continue;
      const d=Math.abs(v[0]*v[n-4]+v[1]*v[n-3]+v[2]*v[n-2]+v[3]*v[n-1]);
      const a=2*Math.acos(Math.min(1,d))*180/Math.PI;
      if(a>worst){worst=a;name=tr.name}
    }
    return {deg:+worst.toFixed(4),track:name,tracks:clip.tracks.length};
  }
  return {makeBodyClip,idlePose,talkPose,seamOf,IDLE,TALK};
}
