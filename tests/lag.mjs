import {makeLag,lagStep,lagAuto,lagAutoPair,lagReport,strandSpread,LAGTUNE,SLOWMUL,hairFlex,LOOSE} from "../web/xr-deform.js";
const B=18,W=4*B,H=1;
const src={image:{data:new Float32Array(B*16),width:W,height:H}};
for(let b=0;b<B;b++){const o=b*16;src.image.data[o]=1;src.image.data[o+5]=1;src.image.data[o+10]=1;src.image.data[o+15]=1}
const T={DataTexture:function(d,w,h){this.image={data:d,width:w,height:h};this.needsUpdate=false},RGBAFormat:1,FloatType:2};
const sk={boneTexture:src};
const fast=makeLag(T,sk),slow=makeLag(T,sk);
const nullLag=makeLag(T,{boneTexture:null});
const move=(t)=>{for(let b=0;b<B;b++){src.image.data[b*16+13]=t}};
const dt=1/60;
const calm=[];
for(let f=0;f<2400;f++){move(0.5+0.004*Math.sin(f*0.05));calm.push(lagAutoPair(fast,slow,dt))}
const c=calm[calm.length-1];
const fastM=[];
for(let f=0;f<60;f++){move(0.5+0.20*Math.sin(f*0.5));fastM.push(lagAutoPair(fast,slow,dt))}
const g=fastM.reduce((a,b)=>b.rate<a.rate?b:a);
let burstGeo=null;
const settle=[];
for(let f=0;f<600;f++){move(0.5+0.004*Math.sin(f*0.05));settle.push(lagAutoPair(fast,slow,dt))}
const s2=settle[settle.length-1];
const bad=[lagAuto(null,dt),lagAuto(fast,0),lagAutoPair(null,slow,dt)].filter(v=>v===null).length;
const N=400;
const P=new Float32Array(N*3),si=new Float32Array(N*4),sw=new Float32Array(N*4),flex=new Float32Array(N);
for(let i=0;i<N;i++){P[i*3]=(i%13)/12-0.5;P[i*3+1]=1.2+(i%23)/22*0.5;P[i*3+2]=(i%7)/6-0.5;si[i*4]=i%B;sw[i*4]=1}
const bones=[];for(let b=0;b<B;b++)bones.push({name:b===3?"mixamorigHead":b===5?"scarf_end":"mixamorigSpine"+b,matrixWorld:{elements:(()=>{const e=new Array(16).fill(0);e[0]=e[5]=e[10]=e[15]=1;e[13]=1.6;return e})()}});
const hf=hairFlex(bones,P,N,si,sw,flex);
const geo={attributes:{position:{array:P},aFlex:{array:flex},aSkinIndex:{array:si},aSkinWeight:{array:sw}}};
const spCalm=strandSpread(geo,fast,slow,1);
for(let f=0;f<40;f++){move(0.5+0.20*Math.sin(f*0.5));lagAutoPair(fast,slow,dt)}
const sp=strandSpread(geo,fast,slow,1);
const spNull=[strandSpread(null,fast,slow,1),strandSpread(geo,null,slow,1)].filter(v=>v===null).length;
const noFlex={attributes:{position:{array:P},aFlex:{array:new Float32Array(N)},aSkinIndex:{array:si},aSkinWeight:{array:sw}}};
const spZero=strandSpread(noFlex,fast,slow,1);
console.log(JSON.stringify({
  calmRate:Math.round(c.rate*100),fastRate:Math.round(g.rate*100),
  slowIsSlower:c.slowRate<c.rate?1:0,slowMul:Math.round(SLOWMUL*100),
  settleRate:Math.round(s2.rate*100),burstExcess:Math.round(g.excess*100),
  guards:bad,nullTex:nullLag===null?1:0,
  hairPts:hf.pts,hairBone:hf.bone,hairMax:Math.round(hf.max*100),
  looseMatch:[LOOSE.test("mixamorigHead"),LOOSE.test("scarf_end"),LOOSE.test("mixamorigSpine2")].map(Number).join(""),
  strandN:sp.sampled,strandWorst:Math.round(sp.worstMm),strandMean:Math.round(sp.meanMm),strandCalm:Math.round(spCalm.worstMm),
  spGuards:spNull,spZeroSampled:spZero.sampled
}));
