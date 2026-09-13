const PORT=process.env.CDP_PORT||9333;
const list=await (await fetch("http://127.0.0.1:"+PORT+"/json")).json();
const want=process.env.CDP_PAGE||"/xr";
const page=list.find(t=>t.type==="page"&&t.url.includes(want));
if(!page){console.log("NO PAGE matching "+want+" on :"+PORT);process.exit(1)}
const ws=new WebSocket(page.webSocketDebuggerUrl);
const expr=process.argv[2]||'JSON.stringify({t:document.title,mods:__xr.mods(),ready:!!(__xr.brain()&&__xr.brain().ready()),clips:__xr.clips().length,state:__xr.state()})';
ws.onopen=()=>ws.send(JSON.stringify({id:1,method:"Runtime.evaluate",params:{expression:expr,awaitPromise:true,returnByValue:true}}));
ws.onmessage=e=>{
  const d=JSON.parse(e.data);
  if(d.id!==1)return;
  const r=d.result&&d.result.result;
  console.log(r&&r.subtype==="error"?"ERROR "+r.description:String(r&&r.value));
  ws.close();
  process.exit(r&&r.subtype==="error"?1:0);
};
setTimeout(()=>{console.log("TIMEOUT");process.exit(1)},15000);
