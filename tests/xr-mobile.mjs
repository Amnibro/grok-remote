const PORT=process.env.CDP_PORT||9333;
const list=await (await fetch("http://127.0.0.1:"+PORT+"/json")).json();
const want=process.env.CDP_PAGE||"auto=1";
const page=list.find(t=>t.type==="page"&&t.url.includes(want));
if(!page){console.log("NO PAGE matching "+want);process.exit(1)}
const ws=new WebSocket(page.webSocketDebuggerUrl);
const W=+(process.argv[2]||390),H=+(process.argv[3]||844);
const expr=process.argv[4]||"1";
let id=0;const pend=new Map();
const send=(method,params)=>new Promise(r=>{const i=++id;pend.set(i,r);ws.send(JSON.stringify({id:i,method,params}))});
ws.onmessage=e=>{const d=JSON.parse(e.data);if(d.id&&pend.has(d.id)){pend.get(d.id)(d);pend.delete(d.id)}};
ws.onopen=async()=>{
  await send("Emulation.setDeviceMetricsOverride",{width:W,height:H,deviceScaleFactor:2,mobile:true});
  await new Promise(r=>setTimeout(r,1200));
  const res=await send("Runtime.evaluate",{expression:expr,awaitPromise:true,returnByValue:true});
  const r=res.result&&res.result.result;
  console.log(r&&r.subtype==="error"?"ERROR "+r.description:String(r&&r.value));
  process.exit(0);
};
setTimeout(()=>{console.log("TIMEOUT");process.exit(1)},20000);
