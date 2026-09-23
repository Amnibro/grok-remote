import assert from "node:assert/strict";
const store=new Map();
globalThis.localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};
globalThis.location={protocol:"http:",host:"hub.test"};
globalThis.fetch=async()=>({json:async()=>({cwd:"/home/u/proj"})});
const sent=[];let sockets=[];let loadFails=false;let newN=0;
class FakeWS{
  constructor(url){this.url=url;this.readyState=0;sockets.push(this);setTimeout(()=>{this.readyState=1;this.onopen&&this.onopen()},1)}
  send(s){
    const m=JSON.parse(s);sent.push(m);
    const reply=r=>setTimeout(()=>this.onmessage&&this.onmessage({data:JSON.stringify(Object.assign({jsonrpc:"2.0",id:m.id},r))}),1);
    if(m.method==="initialize")return reply({result:{}});
    if(m.method==="session/load"){
      this.onmessage&&this.onmessage({data:JSON.stringify({jsonrpc:"2.0",method:"session/update",params:{sessionId:m.params.sessionId,update:{sessionUpdate:"agent_message_chunk",content:{type:"text",text:"Replayed old line."}}}})});
      return reply(loadFails?{error:{code:-32000,message:"unknown session"}}:{result:{}});
    }
    if(m.method==="session/new"){newN++;return reply({result:{sessionId:"xr-sid-"+newN}})}
    reply({result:{}});
  }
  close(){this.readyState=3;this.onclose&&this.onclose()}
}
globalThis.WebSocket=FakeWS;
const {initBrain}=await import("../web/xr-brain.js");
const spoken=[];const sessionsSeen=[];
const mk=()=>initBrain({KEY:"",getState:()=>"idle",setState(){},setLinked(){},say(){},speak:t=>spoken.push(t),
  panels:{addConvo(){}},composeClip(){},sendMotion(){},onReach(){},onSession:id=>sessionsSeen.push(id),onFeed(){},onEvent(){}});
const tick=ms=>new Promise(r=>setTimeout(r,ms||20));
const b1=mk();b1.connect();await tick(40);
assert.equal(newN,1,"first connect creates one session");
assert.ok(sent.find(m=>m.method==="session/new").params._grReq,"session/new carries a _grReq");
assert.equal(store.get("grok_xr_companion_sid"),"xr-sid-1","sid persisted");
sockets[sockets.length-1].close();
await tick(2700);
assert.equal(newN,1,"reconnect reuses the session (no second session/new)");
assert.ok(sent.some(m=>m.method==="session/load"&&m.params.sessionId==="xr-sid-1"),"reconnect re-attaches with session/load");
assert.equal(spoken.length,0,"a session/load replay is never spoken");
const b2=mk();b2.connect();await tick(40);
assert.equal(newN,1,"reload reuses the stored session");
assert.equal(b2.B.sid,"xr-sid-1");
loadFails=true;
const b3=mk();b3.connect();await tick(40);
assert.equal(newN,2,"a dead stored session is replaced once");
assert.equal(store.get("grok_xr_companion_sid"),"xr-sid-2");
for(const s of sockets){s.onclose=null}
console.log("ok");
process.exit(0);
