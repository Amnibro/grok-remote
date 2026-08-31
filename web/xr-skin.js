export const JOINTS={hips:[0,0.92,0],chest:[0,1.22,0.02],neck:[0,1.46,0.03],head:[0,1.62,0.04],uArmL:[-0.18,1.36,0.02],lArmL:[-0.22,1.08,0.06],uArmR:[0.18,1.36,0.02],lArmR:[0.22,1.08,0.06],uLegL:[-0.09,0.88,0.01],lLegL:[-0.10,0.46,0.02],uLegR:[0.09,0.88,0.01],lLegR:[0.10,0.46,0.02]};
export const CAPSULES=[
  ["Hips",0,0.80,0,0,1.06,0.01,0.15],
  ["Spine2",0,1.06,0.01,0,1.44,0.02,0.16],
  ["Neck",0,1.44,0.02,0,1.60,0.03,0.08],
  ["Head",0,1.60,0.03,0,1.80,0.04,0.13],
  ["LeftArm",-0.13,1.40,0.02,-0.22,1.10,0.05,0.06],
  ["LeftForeArm",-0.22,1.10,0.05,-0.25,0.84,0.10,0.055],
  ["RightArm",0.13,1.40,0.02,0.22,1.10,0.05,0.06],
  ["RightForeArm",0.22,1.10,0.05,0.25,0.84,0.10,0.055],
  ["LeftUpLeg",-0.09,0.90,0.01,-0.10,0.48,0.02,0.10],
  ["LeftLeg",-0.10,0.48,0.02,-0.10,0.04,0.03,0.08],
  ["RightUpLeg",0.09,0.90,0.01,0.10,0.48,0.02,0.10],
  ["RightLeg",0.10,0.48,0.02,0.10,0.04,0.03,0.08]
];
export const INFLUENCES=4;
export function buildSkeleton(THREE){
  const J=JOINTS,V=(a)=>new THREE.Vector3(a[0],a[1],a[2]);
  const bones=[],root=new THREE.Bone();
  root.name="Hips";root.position.copy(V(J.hips));bones.push(root);
  const add=(name,parent,wp)=>{
    const b=new THREE.Bone();b.name=name;parent.add(b);parent.updateWorldMatrix(true,false);
    b.position.copy(V(wp)).applyMatrix4(new THREE.Matrix4().copy(parent.matrixWorld).invert());
    bones.push(b);return b;
  };
  const spine=add("Spine2",root,J.chest),neckB=add("Neck",spine,J.neck);
  add("Head",neckB,J.head);
  const ual=add("LeftArm",spine,J.uArmL);add("LeftForeArm",ual,J.lArmL);
  const uar=add("RightArm",spine,J.uArmR);add("RightForeArm",uar,J.lArmR);
  const ull=add("LeftUpLeg",root,J.uLegL);add("LeftLeg",ull,J.lLegL);
  const ulr=add("RightUpLeg",root,J.uLegR);add("RightLeg",ulr,J.lLegR);
  const skelRoot=new THREE.Group();skelRoot.add(root);
  return {bones,root,skelRoot,skeleton:new THREE.Skeleton(bones)};
}
export function skinWeights(p,count,bones){
  const id={};bones.forEach((b,i)=>id[b.name]=i);
  const segs=CAPSULES.map(c=>[id[c[0]],c[1],c[2],c[3],c[4],c[5],c[6],c[7]]).filter(s=>s[0]!=null);
  const si=new Float32Array(count*INFLUENCES),sw=new Float32Array(count*INFLUENCES);
  if(!segs.length||!count)return {si,sw,segs:segs.length};
  const cand=segs.map(()=>[0,0]);
  for(let i=0;i<count;i++){
    const x=p[i*3],y=p[i*3+1],z=p[i*3+2];
    for(let g=0;g<segs.length;g++){
      const s=segs[g],ax=s[1],ay=s[2],az=s[3],r=s[7];
      const abx=s[4]-ax,aby=s[5]-ay,abz=s[6]-az;
      const ab2=abx*abx+aby*aby+abz*abz;
      let tt=((x-ax)*abx+(y-ay)*aby+(z-az)*abz)/(ab2||1);
      tt=tt<0?0:(tt>1?1:tt);
      const dx=x-(ax+abx*tt),dy=y-(ay+aby*tt),dz=z-(az+abz*tt);
      const d=Math.sqrt(dx*dx+dy*dy+dz*dz);
      cand[g][0]=s[0];cand[g][1]=Math.pow(r/(d+r*0.35),3);
    }
    cand.sort((a,b)=>b[1]-a[1]);
    let sum=0;
    const n=Math.min(INFLUENCES,cand.length);
    for(let k=0;k<n;k++)sum+=cand[k][1];
    if(sum<1e-9)sum=1;
    for(let k=0;k<n;k++){si[i*INFLUENCES+k]=cand[k][0];sw[i*INFLUENCES+k]=cand[k][1]/sum}
  }
  return {si,sw,segs:segs.length};
}
export function dominantBone(p,i,bones,si,sw){
  let best=0,bw=-1;
  for(let k=0;k<INFLUENCES;k++)if(sw[i*INFLUENCES+k]>bw){bw=sw[i*INFLUENCES+k];best=si[i*INFLUENCES+k]}
  return {name:bones[best]?bones[best].name:"",w:bw};
}
