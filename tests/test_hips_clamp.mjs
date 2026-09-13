import assert from "node:assert/strict";
/* The renderer clamp in xr.html, extracted so the axis rule is testable.
   Her armature parent is rotated 90 deg about X, so the hips bone's LOCAL
   up axis is z, not y. The baked Mixamo clips carry a Hips.position track
   whose values sit near the origin instead of the bind offset, so writing
   them straight in dropped her a full metre through the disc. */
export function clampHips(pos,bind,up,limit=0.5){
 const out={x:pos.x,y:pos.y,z:pos.z},k=["x","y","z"];
 for(let i=0;i<3;i++)if(i!==up)out[k[i]]=bind[k[i]];
 const a=k[up];
 if(Math.abs(out[a]-bind[a])>limit)out[a]=bind[a];
 return out;
}
export function upAxis(bind){const a=[Math.abs(bind.x),Math.abs(bind.y),Math.abs(bind.z)];return a.indexOf(Math.max(...a))}
const bind={x:-0.019,y:-0.015,z:-1.012};
assert.equal(upAxis(bind),2,"z is up in this rig's bone-local frame");
assert.equal(upAxis({x:0,y:1.012,z:0}),1,"a y-up rig still resolves to y");
const clipPose={x:0.008,y:-0.006,z:0.022};
const fixed=clampHips(clipPose,bind,2);
assert.deepEqual(fixed,{x:-0.019,y:-0.015,z:-1.012},"a clip whose hips track lost the bind offset snaps back");
const oldWay={x:0,y:clipPose.y,z:0};
assert.notEqual(oldWay.z,bind.z,"zeroing x and z is what sank her");
const crouch=clampHips({x:9,y:9,z:bind.z+0.6},bind,2,1.5);
assert.equal(crouch.z,bind.z+0.6,"a crouch (hips 60 cm lower) survives");
assert.equal(crouch.x,bind.x,"sideways drift is always pinned");
const teleport=clampHips({x:0,y:0,z:16},bind,2,1.5);
assert.equal(teleport.z,bind.z,"a centimetre-scale lab value is rejected");
console.log("hips clamp ok");
