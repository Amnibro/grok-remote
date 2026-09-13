import {buildSkeleton,skinWeights,dominantBone,CAPSULES,INFLUENCES} from "../web/xr-skin.js";
const T={Vector3:function(x,y,z){this.x=x;this.y=y;this.z=z;this.copy=function(v){this.x=v.x;this.y=v.y;this.z=v.z;return this};this.applyMatrix4=function(){return this}},Bone:function(){this.children=[];this.position=new T.Vector3(0,0,0);this.add=function(c){this.children.push(c)};this.updateWorldMatrix=function(){};this.matrixWorld={}},Group:function(){this.add=function(){}},Matrix4:function(){this.copy=function(){return this};this.invert=function(){return this}},Skeleton:function(b){this.bones=b}};
const r=buildSkeleton(T);
const PROBE=[[0,1.62,0.04,"Head"],[0,1.22,0.02,"Spine2"],[-0.22,1.08,0.06,"LeftForeArm"],[0.22,1.08,0.06,"RightForeArm"],[-0.10,0.46,0.02,"LeftLeg"],[0.10,0.46,0.02,"RightLeg"],[0,0.92,0,"Hips"],[0,1.46,0.03,"Neck"],[-0.18,1.36,0.02,"LeftArm"],[0.18,1.36,0.02,"RightArm"],[-0.09,0.88,0.01,"LeftUpLeg"],[0.09,0.88,0.01,"RightUpLeg"]];
const N=PROBE.length,p=new Float32Array(N*3);
PROBE.forEach((q,i)=>{p[i*3]=q[0];p[i*3+1]=q[1];p[i*3+2]=q[2]});
const w=skinWeights(p,N,r.bones);
let hit=0,minSum=9,maxSum=0,miss=[];
for(let i=0;i<N;i++){
  const d=dominantBone(p,i,r.bones,w.si,w.sw);
  let s=0;for(let k=0;k<INFLUENCES;k++)s+=w.sw[i*INFLUENCES+k];
  minSum=Math.min(minSum,s);maxSum=Math.max(maxSum,s);
  d.name===PROBE[i][3]?hit++:miss.push(PROBE[i][3]+">"+d.name);
}
const M=1000,big=new Float32Array(M*3);
for(let i=0;i<M;i++){big[i*3]=(i%17)/16*0.6-0.3;big[i*3+1]=(i%53)/52*1.8;big[i*3+2]=(i%11)/10*0.3-0.15}
const t0=process.hrtime.bigint();
const bw=skinWeights(big,M,r.bones);
const ms=Number(process.hrtime.bigint()-t0)/1e6;
let mixed=0;
for(let i=0;i<M;i++){let d=0;for(let k=0;k<INFLUENCES;k++)if(bw.sw[i*INFLUENCES+k]>0.001)d++;if(d>1)mixed++}
const hard=new Float32Array(M*INFLUENCES);
for(let i=0;i<M;i++)hard[i*INFLUENCES]=1;
let hardMixed=0;
for(let i=0;i<M;i++){let d=0;for(let k=0;k<INFLUENCES;k++)if(hard[i*INFLUENCES+k]>0.001)d++;if(d>1)hardMixed++}
const empty=skinWeights(new Float32Array(0),0,r.bones);
const nobones=skinWeights(p,N,[]);
let nzNoBones=0;for(const v of nobones.sw)if(v!==0)nzNoBones++;
console.log(JSON.stringify({bones:r.bones.length,capsules:CAPSULES.length,segs:w.segs,hit,of:N,miss,sumLo:Math.round(minSum*1e6),sumHi:Math.round(maxSum*1e6),blendPct:Math.round(mixed/M*100),rigidCtrlPct:Math.round(hardMixed/M*100),bindMs:Math.round(ms),emptyLen:empty.sw.length,noBoneNonZero:nzNoBones}));
