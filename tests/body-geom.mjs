import {meterize,reposeStatic,TARGET_H} from "../web/xr-body.js";
const N=600,p=new Float32Array(N*3),region=new Uint8Array(N),flex=new Float32Array(N);
for(let i=0;i<N;i++){p[i*3]=(i%20)/19*4-2;p[i*3+1]=Math.floor(i/20)*0.1+3;p[i*3+2]=(i%7)/6*2+5}
let far=0;for(let i=1;i<N;i++)if(p[i*3+2]>p[far*3+2])far=i;
const S={};
const m=meterize(p,N,S);
let mnY=1e9,mxY=-1e9,mnX=1e9,mxX=-1e9,mnZ=1e9,mxZ=-1e9;
for(let i=0;i<N;i++){const x=p[i*3],y=p[i*3+1],z=p[i*3+2];if(y<mnY)mnY=y;if(y>mxY)mxY=y;if(x<mnX)mnX=x;if(x>mxX)mxX=x;if(z<mnZ)mnZ=z;if(z>mxZ)mxZ=z}
for(let i=0;i<N;i++)region[i]=p[i*3+1]>1.5&&Math.abs(p[i*3])>0.4?0:1;
const before=Float32Array.from(p);
const r=reposeStatic(p,N,region,S,flex);
let maxD=0;for(let i=0;i<N;i++){const d=Math.hypot(p[i*3]-before[i*3],p[i*3+1]-before[i*3+1]);if(d>maxD)maxD=d}
const legs=[...region].filter(v=>v===1).length;
const flexSet=[...flex].filter(v=>Math.abs(v-0.2)<1e-6).length;
const S2={},empty=meterize(new Float32Array(0),0,S2);
const noS=reposeStatic(p,N,region,null,flex);
console.log(JSON.stringify({h:Math.round((mxY-mnY)*1000),feet:Math.round(mnY*1000),cx:Math.round((mnX+mxX)*500),zFlipped:(p[far*3+2]<=mnZ+1e-6)?1:0,scale:Math.round(m.scale*1000),moved:r.moved,legs,flexSet,maxMoveMm:Math.round(maxD*1000),emptySafe:empty===null?1:0,nullSSafe:noS===null?1:0,target:Math.round(TARGET_H*1000)}));
