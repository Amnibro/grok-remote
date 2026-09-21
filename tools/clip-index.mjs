import {readdirSync,readFileSync,writeFileSync} from "node:fs";
import {join} from "node:path";
const CLIPS=process.argv[2]||"clips";
const OUT=process.argv[3]||"web/clip_index.json";
const ang=(a,b)=>{
  let d=a[0]*b[0]+a[1]*b[1]+a[2]*b[2]+a[3]*b[3];
  d=Math.abs(d)>1?Math.sign(d):d;
  return Math.acos(Math.abs(d))*2*180/Math.PI;
};
const MAJOR=/(Arm|ForeArm|Shoulder|Spine\d?|Spine|Neck|Head|UpLeg|Leg|Foot|Hips|Hand)$/;
const tier=e=>e<12?"calm":e<35?"moderate":e<80?"lively":"explosive";
const out={};
for(const f of readdirSync(CLIPS).filter(n=>n.endsWith(".json")&&!n.startsWith("_"))){
  let c;
  try{c=JSON.parse(readFileSync(join(CLIPS,f),"utf8"))}catch(e){continue}
  const dur=+(c.duration||0);
  const tracks=(c.tracks||[]).filter(t=>t.type==="quaternion"&&t.times.length>1&&MAJOR.test(t.name.replace(/\.quaternion$/,"").replace(/^mixamorig:?/,"")));
  if(!tracks.length||!(dur>0))continue;
  let peak=0,peakBone="",movers=0,travel=0;
  for(const t of tracks){
    const v=t.values,n=t.times.length,base=[v[0],v[1],v[2],v[3]];
    let m=0,sum=0;
    for(let k=1;k<n;k++){
      const q=[v[k*4],v[k*4+1],v[k*4+2],v[k*4+3]];
      const pv=[v[(k-1)*4],v[(k-1)*4+1],v[(k-1)*4+2],v[(k-1)*4+3]];
      m=Math.max(m,ang(base,q));
      sum+=ang(pv,q);
    }
    travel+=sum;
    if(m>10)movers++;
    if(m>peak){peak=m;peakBone=t.name.replace(/\.quaternion$/,"").replace(/^mixamorig:?/,"")}
  }
  let seam=0;
  for(const t of tracks){
    const v=t.values,n=t.times.length;
    if(n<2)continue;
    seam=Math.max(seam,ang([v[0],v[1],v[2],v[3]],[v[(n-1)*4],v[(n-1)*4+1],v[(n-1)*4+2],v[(n-1)*4+3]]));
  }
  const energy=travel/tracks.length/dur;
  out[f.replace(/\.json$/,"")]={name:c.name||"",deg:+peak.toFixed(1),bone:peakBone,movers,dur:+dur.toFixed(2),energy:+energy.toFixed(1),seam:+seam.toFixed(1),loops:seam<8,tier:tier(energy)};
}
const names=Object.keys(out).sort();
writeFileSync(OUT,JSON.stringify({built:names.length,clips:out},null,0));
const byTier={};
for(const n of names)byTier[out[n].tier]=(byTier[out[n].tier]||0)+1;
console.log("indexed",names.length,"clips ->",OUT);
console.log("tiers",JSON.stringify(byTier));
console.log("sample",names.slice(0,5).map(n=>n+" "+out[n].energy+"deg/s "+out[n].tier).join(" | "));
