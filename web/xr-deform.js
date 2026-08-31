const S={skinMs:0,clothMs:0,skinN:0,clothN:0,frames:0,peakSkin:0,peakCloth:0};
const roll=(k,v)=>{S[k]=S[k]*0.9+v*0.1};
export function deformStats(){return {skinMs:+S.skinMs.toFixed(3),clothMs:+S.clothMs.toFixed(3),skinN:S.skinN,clothN:S.clothN,frames:S.frames,peakSkinMs:+S.peakSkin.toFixed(3),peakClothMs:+S.peakCloth.toFixed(3),totalMs:+(S.skinMs+S.clothMs).toFixed(3)}}
export function resetDeformStats(){S.skinMs=0;S.clothMs=0;S.skinN=0;S.clothN=0;S.frames=0;S.peakSkin=0;S.peakCloth=0}
export function skinFrame(THREE,c){
  const {skeleton,bindPos,skinGeo,bindLocalInv,modelHolder,skelRoot,hinv,boneMats}=c;
  if(!skeleton||!bindPos||!skinGeo||!bindLocalInv||!modelHolder||!skelRoot)return null;
  const t0=performance.now();
  modelHolder.updateMatrixWorld(true);
  skelRoot.updateMatrixWorld(true);
  hinv.copy(modelHolder.matrixWorld).invert();
  const bones=skeleton.bones,M=boneMats;
  if(M.length<bones.length)while(M.length<bones.length)M.push(new THREE.Matrix4());
  for(let b=0;b<bones.length;b++)M[b].multiplyMatrices(hinv,bones[b].matrixWorld).multiply(bindLocalInv[b]);
  const P=skinGeo.attributes.position.array;
  const si=skinGeo.attributes.aSkinIndex.array;
  const sw=skinGeo.attributes.aSkinWeight.array;
  const n=Math.min(bindPos.length/3|0,P.length/3|0);
  for(let i=0;i<n;i++){
    const bx=bindPos[i*3],by=bindPos[i*3+1],bz=bindPos[i*3+2];
    let x=0,y=0,z=0;
    for(let k=0;k<4;k++){
      const w=sw[i*4+k];
      if(w<1e-4)continue;
      const mi=si[i*4+k]|0;
      if(mi<0||mi>=M.length)continue;
      const e=M[mi].elements;
      x+=(e[0]*bx+e[4]*by+e[8]*bz+e[12])*w;
      y+=(e[1]*bx+e[5]*by+e[9]*bz+e[13])*w;
      z+=(e[2]*bx+e[6]*by+e[10]*bz+e[14])*w;
    }
    P[i*3]=x;P[i*3+1]=y;P[i*3+2]=z;
  }
  skinGeo.attributes.position.needsUpdate=true;
  const ms=performance.now()-t0;
  roll("skinMs",ms);S.skinN=n;S.frames++;
  if(ms>S.peakSkin)S.peakSkin=ms;
  return {n,ms};
}
export const CLOTH={damp:0.88,kBase:0.45,kFlex:0.30,wind:0.00030,gravity:0.0005,limBase:0.004,limFlex:0.022};
export function clothStep(THREE,st,modelHolder,dt,t,tmp){
  if(!st||!modelHolder||!st.count)return null;
  const t0=performance.now();
  const {pm,pmInv,pv}=tmp;
  modelHolder.updateMatrixWorld(true);
  pm.copy(modelHolder.matrixWorld);
  pmInv.copy(pm).invert();
  const P=st.geo.attributes.position.array;
  if(!st.init){
    for(let i=0;i<st.count;i++){
      pv.set(st.base[i*3],st.base[i*3+1],st.base[i*3+2]).applyMatrix4(pm);
      st.cur[i*3]=pv.x;st.cur[i*3+1]=pv.y;st.cur[i*3+2]=pv.z;
      st.prev[i*3]=pv.x;st.prev[i*3+1]=pv.y;st.prev[i*3+2]=pv.z;
    }
    st.init=true;
  }
  const C=CLOTH;
  for(let i=0;i<st.count;i++){
    const f=st.f[i],k=C.kBase-C.kFlex*f,ix=i*3;
    pv.set(st.base[ix],st.base[ix+1],st.base[ix+2]).applyMatrix4(pm);
    const tx=pv.x,ty=pv.y,tz=pv.z;
    let x=st.cur[ix],y=st.cur[ix+1],z=st.cur[ix+2];
    let vx=(x-st.prev[ix])*C.damp,vy=(y-st.prev[ix+1])*C.damp,vz=(z-st.prev[ix+2])*C.damp;
    st.prev[ix]=x;st.prev[ix+1]=y;st.prev[ix+2]=z;
    const wind=C.wind*f*(Math.sin(t*1.3+i*0.7)+Math.sin(t*2.9+i*1.3));
    vx+=(tx-x)*k+wind;
    vy+=(ty-y)*k-C.gravity*f;
    vz+=(tz-z)*k+wind*0.6;
    x+=vx;y+=vy;z+=vz;
    const dx=x-tx,dy=y-ty,dz=z-tz;
    const d2=dx*dx+dy*dy+dz*dz,lim=C.limBase+C.limFlex*f;
    if(d2>lim*lim){const sc=lim/Math.sqrt(d2);x=tx+dx*sc;y=ty+dy*sc;z=tz+dz*sc}
    st.cur[ix]=x;st.cur[ix+1]=y;st.cur[ix+2]=z;
    pv.set(x,y,z).applyMatrix4(pmInv);
    P[ix]=pv.x;P[ix+1]=pv.y;P[ix+2]=pv.z;
  }
  st.geo.attributes.position.needsUpdate=true;
  const ms=performance.now()-t0;
  roll("clothMs",ms);S.clothN=st.count;
  if(ms>S.peakCloth)S.peakCloth=ms;
  return {n:st.count,ms};
}
export function strayRadius(st){
  if(!st||!st.count)return null;
  let worst=0;
  for(let i=0;i<st.count;i++){
    const dx=st.cur[i*3]-st.base[i*3],dy=st.cur[i*3+1]-st.base[i*3+1],dz=st.cur[i*3+2]-st.base[i*3+2];
    const d=Math.sqrt(dx*dx+dy*dy+dz*dz);
    if(d>worst)worst=d;
  }
  return {worstMm:+(worst*1000).toFixed(2),limitMm:+((CLOTH.limBase+CLOTH.limFlex)*1000).toFixed(2)};
}
export function makeLag(THREE,skeleton){
  const src=skeleton&&skeleton.boneTexture;
  if(!src||!src.image||!src.image.data)return null;
  const d=Float32Array.from(src.image.data);
  const tex=new THREE.DataTexture(d,src.image.width,src.image.height,THREE.RGBAFormat,THREE.FloatType);
  tex.needsUpdate=true;
  return {tex,data:d,src,n:d.length};
}
export function lagStep(lag,alpha){
  if(!lag)return null;
  const s=lag.src.image.data,d=lag.data,a=Math.max(0,Math.min(1,alpha));
  let drift=0;
  for(let i=0;i<d.length;i++){const t=s[i];drift+=Math.abs(t-d[i]);d[i]+=(t-d[i])*a}
  lag.tex.needsUpdate=true;
  return {drift:+drift.toFixed(5),n:d.length};
}
export const LOOSE=/head|hair|ponytail|braid|scarf|cloth|skirt|coat|cape|tail/i;
export function hairFlex(bones,p,count,si,sw,flex,opt){
  if(!bones||!bones.length||!count)return {pts:0,pct:0,max:0,bone:"",span:0};
  const o=opt||{},maxW=o.maxW==null?0.55:o.maxW,pw=o.pow==null?1.4:o.pow;
  const loose=new Set();
  bones.forEach((b,i)=>{if(LOOSE.test(b.name||""))loose.add(i)});
  if(!loose.size)return {pts:0,pct:0,max:0,bone:"",span:0};
  const y=new Map();
  bones.forEach((b,i)=>{if(loose.has(i)){const m=b.matrixWorld&&b.matrixWorld.elements;y.set(i,m?m[13]:0)}});
  let lo=1e9,hi=-1e9,pts=0,mx=0,which="";
  const dom=new Int32Array(count);
  for(let i=0;i<count;i++){
    let b=-1,bw=0;
    for(let k=0;k<4;k++){const w=sw[i*4+k];if(w>bw){bw=w;b=si[i*4+k]|0}}
    dom[i]=loose.has(b)?b:-1;
    if(dom[i]>=0){const py=p[i*3+1];if(py<lo)lo=py;if(py>hi)hi=py}
  }
  if(lo>hi)return {pts:0,pct:0,max:0,bone:"",span:0};
  for(let i=0;i<count;i++){
    if(dom[i]<0)continue;
    const jy=y.get(dom[i]),py=p[i*3+1];
    const span=Math.max(0.02,jy-lo);
    const down=Math.max(0,Math.min(1,(jy-py)/span));
    const f=Math.pow(down,pw)*maxW;
    if(f>0.01){flex[i]=Math.max(flex[i],f);pts++;if(f>mx){mx=f;which=(bones[dom[i]].name||"")}}
  }
  return {pts,pct:Math.round(100*pts/count),max:+mx.toFixed(3),bone:which,span:+(hi-lo).toFixed(3)};
}
export const LAGTUNE={base:7,slowK:0.3,minA:1.6,maxA:9,ease:6,headroom:1.15,fall:0.25,rise:0.12};
export function lagAuto(lag,dt,tune){
  if(!lag||!(dt>0))return null;
  const T=tune||LAGTUNE;
  const s=lag.src.image.data,d=lag.data;
  let raw=0,n=0;
  for(let i=0;i+15<d.length;i+=16){raw+=Math.abs(s[i+12]-d[i+12])+Math.abs(s[i+13]-d[i+13])+Math.abs(s[i+14]-d[i+14]);n++}
  const speed=raw/dt/Math.max(1,n);
  lag.speed=lag.speed==null?speed:lag.speed+(speed-lag.speed)*Math.min(1,dt*T.ease);
  lag.floor=lag.floor==null?lag.speed:lag.floor+(lag.speed-lag.floor)*Math.min(1,dt*(lag.speed<lag.floor?T.fall:T.rise));
  const excess=Math.max(0,lag.speed-lag.floor*T.headroom);
  const rate=Math.max(T.minA,Math.min(T.maxA,T.base/(1+T.slowK*excess)));
  const a=Math.min(1,dt*rate);
  const r=lagStep(lag,a);
  lag.alpha=a;lag.rate=+rate.toFixed(3);
  return {alpha:+a.toFixed(4),rate:lag.rate,speed:+lag.speed.toFixed(5),floor:+lag.floor.toFixed(5),excess:+excess.toFixed(5),drift:r.drift};
}
export const SLOWMUL=0.42;
export function lagAutoPair(fast,slow,dt,tune){
  const a=lagAuto(fast,dt,tune);
  if(!a||!slow)return a;
  slow.speed=fast.speed;slow.floor=fast.floor;
  const r=lagStep(slow,Math.min(1,dt*Math.max(0.4,a.rate*SLOWMUL)));
  slow.rate=+(a.rate*SLOWMUL).toFixed(3);slow.alpha=Math.min(1,dt*Math.max(0.4,a.rate*SLOWMUL));
  return {...a,slowRate:slow.rate,slowDrift:r.drift};
}
function skinPoint(d,si,sw,i,bx,by,bz,o){
  let x=0,y=0,z=0;
  for(let k=0;k<4;k++){
    const w=sw[i*4+k];
    if(w<1e-4)continue;
    const b=(si[i*4+k]|0)*16;
    if(b<0||b+15>=d.length)continue;
    x+=(d[b]*bx+d[b+4]*by+d[b+8]*bz+d[b+12])*w;
    y+=(d[b+1]*bx+d[b+5]*by+d[b+9]*bz+d[b+13])*w;
    z+=(d[b+2]*bx+d[b+6]*by+d[b+10]*bz+d[b+14])*w;
  }
  o[0]=x;o[1]=y;o[2]=z;
}
export function strandSpread(geo,fast,slow,step){
  if(!geo||!fast||!slow)return null;
  const A=geo.attributes,fl=A.aFlex,pos=A.position,si=A.aSkinIndex.array,sw=A.aSkinWeight.array;
  if(!fl||!pos)return null;
  const P=pos.array,F=fl.array,st=Math.max(1,step||1);
  const a=[0,0,0],b=[0,0,0];
  let worst=0,sum=0,n=0;
  for(let i=0;i<F.length;i+=st){
    if(F[i]<=0.01)continue;
    const bx=P[i*3],by=P[i*3+1],bz=P[i*3+2];
    skinPoint(fast.data,si,sw,i,bx,by,bz,a);
    skinPoint(slow.data,si,sw,i,bx,by,bz,b);
    const d=Math.hypot(a[0]-b[0],a[1]-b[1],a[2]-b[2]);
    sum+=d;n++;if(d>worst)worst=d;
  }
  return n?{worstMm:+(worst*1000).toFixed(2),meanMm:+(sum/n*1000).toFixed(2),sampled:n}:{worstMm:0,meanMm:0,sampled:0};
}
export function lagReport(lag){return lag?{speed:+(lag.speed||0).toFixed(5),floor:+(lag.floor||0).toFixed(5),rate:lag.rate||0,alpha:+(lag.alpha||0).toFixed(4)}:null}
