export function initLook(ctx){
  const {getCam,state,noteErr}=ctx;
  const L={on:false,seen:false,x:0,conf:0,frames:0,miss:0,err:""};
  let det=null,timer=null,ts=0,cv=null,cx=null;
  async function ensure(){
    if(det)return det;
    const {FilesetResolver,PoseLandmarker}=await import("/static/vendor/mp/vision_bundle.mjs");
    const fs=await FilesetResolver.forVisionTasks("/static/vendor/mp");
    det=await PoseLandmarker.createFromOptions(fs,{baseOptions:{modelAssetPath:"/static/vendor/mp/pose_landmarker_lite.task"},runningMode:"VIDEO",numPoses:1});
    return det;
  }
  async function tick(){
    const c=getCam();
    if(!c||!c.stream||!c.video||!c.video.videoWidth){L.on=false;L.seen=false;return}
    L.on=true;
    try{
      const d=await ensure();
      if(!cv){cv=document.createElement("canvas");cv.width=256;cv.height=192;cx=cv.getContext("2d",{willReadFrequently:true})}
      cx.drawImage(c.video,0,0,cv.width,cv.height);
      const r=d.detectForVideo(cv,(ts+=50));
      const lm=r&&r.landmarks&&r.landmarks[0];
      L.frames++;
      if(!lm){L.miss++;L.seen=false;return}
      const nose=lm[0],ls=lm[11],rs=lm[12];
      const mid=ls&&rs?(ls.x+rs.x)/2:nose.x;
      const cxn=(nose.x*0.6+mid*0.4);
      L.x=+(1-cxn*2).toFixed(3);
      L.conf=+((nose.visibility==null?1:nose.visibility)).toFixed(2);
      L.seen=true;
      L.miss=0;
      state.lookYaw=Math.max(-0.55,Math.min(0.55,L.x*0.7));
      state.lookUntil=Date.now()+2500;
    }catch(e){L.err=(e&&e.message)||(e&&e.type?"load event: "+e.type:String(e));noteErr&&noteErr("look",L.err)}
  }
  function start(ms){if(timer)return;timer=setInterval(tick,ms||500)}
  function stop(){if(timer){clearInterval(timer);timer=null}L.on=false;L.seen=false}
  return {start,stop,tick,L};
}
