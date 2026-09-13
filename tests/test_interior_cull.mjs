import assert from "node:assert/strict";
/* The sampler rule from xr.html, extracted so the shell test is checkable.
   A pointcloud cannot occlude, so the mouth bag and eye sockets render straight
   through her face. Any sample inside the head whose normal points back toward
   the head centre is lining, not skin. */
export function isInterior(px,py,pz,nx,ny,nz,head,R=0.135,minDot=0.12){
 const dx=px-head[0],dy=py-head[1],dz=pz-head[2];
 const d=Math.hypot(dx,dy,dz);
 if(d>=R||d<1e-5)return false;
 return (dx*nx+dy*ny+dz*nz)/d<minDot;
}
const head=[-0.052,1.428,-0.015];
const cheek=[head[0]+0.09,head[1],head[2]];
assert.equal(isInterior(...cheek,1,0,0,head),false,"outward cheek skin is kept");
const mouthBag=[head[0]+0.05,head[1]-0.03,head[2]];
assert.equal(isInterior(...mouthBag,-1,0,0,head),true,"the mouth lining faces inward and goes");
const socket=[head[0]+0.06,head[1]+0.02,head[2]+0.03];
assert.equal(isInterior(...socket,-0.8,-0.2,-0.5,head),true,"an eye socket wall goes");
const shoulder=[head[0],head[1]-0.35,head[2]];
assert.equal(isInterior(...shoulder,0,-1,0,head),false,"nothing outside the head sphere is touched");
const grazing=[head[0]+0.09,head[1],head[2]];
assert.equal(isInterior(...grazing,0,1,0,head),true,"a wall parallel to the view is lining too");
assert.equal(isInterior(...head,1,0,0,head),false,"a sample exactly at the centre is left alone");
console.log("interior cull ok");
