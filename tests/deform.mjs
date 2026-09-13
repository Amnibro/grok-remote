import {skinFrame,clothStep,deformStats,resetDeformStats,strayRadius,CLOTH} from "../web/xr-deform.js";
globalThis.performance=globalThis.performance||{now:()=>Number(process.hrtime.bigint()/1000n)/1000};
const M4=function(){this.elements=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];this.copy=function(m){this.elements=m.elements.slice();return this};this.invert=function(){this.elements[12]*=-1;this.elements[13]*=-1;this.elements[14]*=-1;return this};this.multiplyMatrices=function(a,b){this.elements=a.elements.slice();for(let i=12;i<15;i++)this.elements[i]+=b.elements[i];return this};this.multiply=function(b){for(let i=12;i<15;i++)this.elements[i]+=b.elements[i];return this}};
const V3=function(){this.x=0;this.y=0;this.z=0;this.set=function(x,y,z){this.x=x;this.y=y;this.z=z;return this};this.applyMatrix4=function(m){this.x+=m.elements[12];this.y+=m.elements[13];this.z+=m.elements[14];return this}};
const T={Matrix4:M4,Vector3:V3};
const N=20000;
const attr=a=>({array:a,needsUpdate:false});
const bindPos=new Float32Array(N*3);
for(let i=0;i<N;i++){bindPos[i*3]=(i%31)/30-0.5;bindPos[i*3+1]=(i%97)/96*1.8;bindPos[i*3+2]=(i%13)/12-0.5}
const si=new Float32Array(N*4),sw=new Float32Array(N*4);
for(let i=0;i<N;i++){si[i*4]=i%12;sw[i*4]=0.6;si[i*4+1]=(i+1)%12;sw[i*4+1]=0.4}
const skinGeo={attributes:{position:attr(new Float32Array(N*3)),aSkinIndex:attr(si),aSkinWeight:attr(sw)}};
const mk=()=>{const m=new M4();m.elements=m.elements.slice();return m};
const holder={matrixWorld:mk(),updateMatrixWorld(){}};
const skelRoot={updateMatrixWorld(){}};
const bones=[];for(let b=0;b<12;b++)bones.push({matrixWorld:(()=>{const m=mk();m.elements[13]=0.01*b;return m})()});
const c={skeleton:{bones},bindPos,skinGeo,bindLocalInv:bones.map(()=>mk()),modelHolder:holder,skelRoot,hinv:mk(),boneMats:[]};
resetDeformStats();
let r=null;for(let f=0;f<30;f++)r=skinFrame(T,c);
let moved=0;for(let i=0;i<N;i++)if(skinGeo.attributes.position.array[i*3+1]!==0)moved++;
const nulls=[skinFrame(T,{...c,skeleton:null}),skinFrame(T,{...c,bindPos:null}),skinFrame(T,{...c,modelHolder:null})].filter(v=>v===null).length;
const badIdx=new Float32Array(N*4);for(let i=0;i<N*4;i++)badIdx[i]=999;
const safeGeo={attributes:{position:attr(new Float32Array(N*3)),aSkinIndex:attr(badIdx),aSkinWeight:attr(sw)}};
const oob=skinFrame(T,{...c,skinGeo:safeGeo})?1:0;
const K=4000;
const st={count:K,init:false,base:new Float32Array(K*3),cur:new Float32Array(K*3),prev:new Float32Array(K*3),f:new Float32Array(K),geo:{attributes:{position:attr(new Float32Array(K*3))}}};
for(let i=0;i<K;i++){st.base[i*3]=(i%29)/28-0.5;st.base[i*3+1]=1.2+(i%17)/16*0.5;st.base[i*3+2]=(i%7)/6-0.5;st.f[i]=(i%11)/10}
let cr=null;for(let f=0;f<120;f++)cr=clothStep(T,st,holder,1/60,f/60,{pm:mk(),pmInv:mk(),pv:new V3()});
const stray=strayRadius(st);
const clothNull=[clothStep(T,null,holder,0.016,0,{pm:mk(),pmInv:mk(),pv:new V3()}),clothStep(T,{...st,count:0},holder,0.016,0,{pm:mk(),pmInv:mk(),pv:new V3()})].filter(v=>v===null).length;
const S=deformStats();
console.log(JSON.stringify({skinN:r.n,movedPct:Math.round(moved/N*100),skinMs:Math.round(S.skinMs*100),clothN:cr.n,clothMs:Math.round(S.clothMs*100),frames:S.frames,guardsHit:nulls,oobSafe:oob,clothGuards:clothNull,strayMm:Math.round(stray.worstMm),limitMm:Math.round(stray.limitMm),within:stray.worstMm<=stray.limitMm+0.01?1:0}));
