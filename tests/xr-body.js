export const TARGET_H=1.7;
export function meterize(p,count,S){
  if(!count)return null;
  let minX=1e9,minY=1e9,minZ=1e9,maxX=-1e9,maxY=-1e9,maxZ=-1e9;
  for(let i=0;i<count;i++){
    const x=p[i*3],y=p[i*3+1],z=p[i*3+2];
    if(x<minX)minX=x;if(y<minY)minY=y;if(z<minZ)minZ=z;
    if(x>maxX)maxX=x;if(y>maxY)maxY=y;if(z>maxZ)maxZ=z;
  }
  const s=TARGET_H/Math.max(1e-6,maxY-minY);
  const cx=(minX+maxX)*0.5,cz=(minZ+maxZ)*0.5;
  for(let i=0;i<count;i++){
    p[i*3]=(p[i*3]-cx)*s;
    p[i*3+1]=(p[i*3+1]-minY)*s;
    p[i*3+2]=-(p[i*3+2]-cz)*s;
  }
  S.H=TARGET_H;S.minY=0;S.cx=0;S.bodyZ=0;
  return {scale:s,srcH:maxY-minY};
}
export function reposeStatic(p,count,region,S,flex){
  if(!S||!count)return null;
  const H=S.H,minY=S.minY,cx=S.cx;
  const shX=H*0.20,shY=minY+H*0.82,blendW=H*0.06,armA=0.42;
  let moved=0;
  for(let i=0;i<count;i++){
    let x=p[i*3],y=p[i*3+1];
    if(region[i]===1){
      if(flex)flex[i]=0.2;
      continue;
    }
    const dx=x-cx,isHand=region[i]===2;
    if(!(isHand||(Math.abs(dx)>shX&&y>minY+H*0.55)))continue;
    const side=dx>0?1:-1;
    const b=isHand?1:Math.min(1,(Math.abs(dx)-shX)/blendW);
    const a=-side*armA*b;
    const px=cx+side*shX,ox=x-px,oy=y-shY;
    const ca=Math.cos(a),sa=Math.sin(a);
    p[i*3]=px+ox*ca-oy*sa;
    p[i*3+1]=shY+ox*sa+oy*ca;
    moved++;
  }
  return {moved};
}
