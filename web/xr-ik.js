export function initIK(ctx){
  const {THREE,getSkeleton}=ctx;
  const V=()=>new THREE.Vector3();
  const pA=V(),pB=V(),pC=V(),pC2=V(),toT=V(),dirT=V(),ab=V(),bc=V(),ac=V(),ac2=V(),axis=V();
  const qW=new THREE.Quaternion(),qP=new THREE.Quaternion(),qR=new THREE.Quaternion(),qI=new THREE.Quaternion();
  const clamp=(v,a,b)=>v<a?a:v>b?b:v;
  const chains={};
  const state={weight:0,target:new THREE.Vector3(),chain:"right",err:-1,sign:-1};
  function setWorldQuat(bone,w){
    bone.parent?bone.parent.getWorldQuaternion(qP):qP.identity();
    bone.quaternion.copy(qP.invert().multiply(w));
  }
  function rotWorld(bone,ax,ang){
    if(!ang)return;
    qR.setFromAxisAngle(ax,ang);
    bone.getWorldQuaternion(qW);
    setWorldQuat(bone,qR.multiply(qW));
  }
  function find(rx){const sk=getSkeleton();return sk&&sk.bones.find(b=>rx.test(b.name))}
  function chain(side){
    const key=side.toLowerCase();
    if(chains[key]&&chains[key].root.parent)return chains[key];
    const S=key==="left"?"Left":"Right";
    const root=find(new RegExp(S+"Arm$")),mid=find(new RegExp(S+"ForeArm$")),end=find(new RegExp(S+"Hand$"));
    return root&&mid&&end?(chains[key]={root,mid,end}):null;
  }
  function solve(side,target,weight){
    const c=chain(side);
    if(!c||!(weight>0))return -1;
    const {root,mid,end}=c;
    root.updateMatrixWorld(true);
    root.getWorldPosition(pA);mid.getWorldPosition(pB);end.getWorldPosition(pC);
    const L1=pA.distanceTo(pB),L2=pB.distanceTo(pC);
    if(!(L1>1e-5&&L2>1e-5))return -1;
    toT.subVectors(target,pA);
    const dist=clamp(toT.length(),Math.abs(L1-L2)+1e-3,L1+L2-1e-3);
    dirT.copy(toT).normalize();
    ab.subVectors(pB,pA).normalize();
    bc.subVectors(pC,pB).normalize();
    ac.subVectors(pC,pA).normalize();
    axis.crossVectors(ab,bc);
    if(axis.lengthSq()<1e-8)axis.crossVectors(ab,dirT);
    if(axis.lengthSq()<1e-8)axis.set(0,0,1);
    axis.normalize();
    const cur1=Math.acos(clamp(ab.dot(ac),-1,1));
    const want1=Math.acos(clamp((L1*L1+dist*dist-L2*L2)/(2*L1*dist),-1,1));
    const curI=Math.acos(clamp(-ab.dot(bc),-1,1));
    const wantI=Math.acos(clamp((L1*L1+L2*L2-dist*dist)/(2*L1*L2),-1,1));
    rotWorld(root,axis,(want1-cur1)*weight*state.sign);
    root.updateMatrixWorld(true);
    rotWorld(mid,axis,(wantI-curI)*weight*state.sign);
    root.updateMatrixWorld(true);
    end.getWorldPosition(pC2);
    ac2.subVectors(pC2,pA).normalize();
    qR.setFromUnitVectors(ac2,dirT);
    if(weight<1)qR.slerp(qI.identity(),1-weight);
    root.getWorldQuaternion(qW);
    setWorldQuat(root,qR.multiply(qW));
    root.updateMatrixWorld(true);
    state.err=end.getWorldPosition(pC2).distanceTo(target);
    return state.err;
  }
  function tick(){
    if(!(state.weight>0))return;
    solve(state.chain,state.target,state.weight);
  }
  function fit(side,vec,frac){
    const c=chain(side);
    if(!c)return vec;
    c.root.updateMatrixWorld(true);
    c.root.getWorldPosition(pA);c.mid.getWorldPosition(pB);c.end.getWorldPosition(pC);
    const span=(pA.distanceTo(pB)+pB.distanceTo(pC))*(frac||0.9);
    toT.subVectors(vec,pA);
    if(toT.length()>span)vec.copy(pA).add(toT.normalize().multiplyScalar(span));
    return vec;
  }
  function reach(side,x,y,z,weight){
    state.chain=side||"right";
    fit(state.chain,state.target.set(x,y,z),0.92);
    state.weight=weight==null?1:weight;
    return solve(state.chain,state.target,state.weight);
  }
  function release(){state.weight=0;state.err=-1}
  return {solve,tick,reach,release,chain,fit,state};
}
