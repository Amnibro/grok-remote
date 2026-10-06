import assert from "node:assert/strict";
const store=new Map([["grok_xr_companion_sid","old-sid"]]);
globalThis.localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};
globalThis.location={protocol:"http:",host:"hub.test"};
const sent=[];let sockets=[];let mode="ok";
class FakeWS{
  constructor(url){this.url=url;this.readyState=0;sockets.push(this);setTimeout(()=>{if(mode==="refuse"){this.readyState=3;this.onclose&&this.onclose();return}this.readyState=1;this.onopen&&this.onopen()},1)}
  emit(o){setTimeout(()=>this.readyState===1&&this.onmessage&&this.onmessage({data:JSON.stringify(o)}),1)}
  send(s){
    const m=JSON.parse(s);sent.push(m);
    if(m.op==="hello")return this.emit({type:"session",sid:"s-"+(m.brain||"grok"),brain:m.brain||"grok",caps:{image:m.brain==="claude"},user:"Sam",body:"female",label:m.brain||"grok"});
    if(m.op==="say"&&mode==="ok"){for(const d of ["Ha","Ha"," hi. [[motion:wave_hello]] Bye"])this.emit({type:"text",delta:d,turn:m.turn});this.emit({type:"tool",id:"t1",title:"Read",status:"completed",turn:m.turn});this.emit({type:"done",stop_reason:"end_turn",turn:m.turn})}
    if(m.op==="say"&&mode==="perm")this.emit({type:"permission",id:"p1",tool:{title:"Bash"},options:[{id:"allow"},{id:"deny"}],turn:m.turn});
  }
  close(){this.readyState=3;this.onclose&&this.onclose()}
}
globalThis.WebSocket=FakeWS;
const {initBrain,cleanSpeech}=await import("../web/xr-brain.js");
const spoken=[],moves=[],events=[],permits=[];let hushed=0,linked=false;
const b=initBrain({KEY:"k1",getState:()=>"idle",setState(){},setLinked:v=>{linked=v},say(){},speak:t=>spoken.push(t),hush:()=>hushed++,
  panels:{addConvo(){}},composeClip(){},sendMotion:(k,v)=>moves.push(k+":"+v),onReach(){},onSession(){},onEvent:u=>events.push(u),onPermit:(ev,ans)=>{permits.push(ev);ans("deny")},helloMs:200,minBackoff:20,maxBackoff:40});
const tick=ms=>new Promise(r=>setTimeout(r,ms||20));
b.connect();await tick(30);
assert.match(sockets[0].url,/\/api\/companion\/brain\?key=k1$/);
const h=sent.find(m=>m.op==="hello");
assert.equal(h.sid,"old-sid","old grok sid is offered once for migration");
assert.equal(store.has("grok_xr_companion_sid"),false,"old key is cleared after the session arrives");
assert.ok(b.ready()&&linked);assert.equal(b.B.user,"Sam");
let r=await b.ask("hello");
assert.equal(r.stop,"end_turn");
assert.equal(b.B.accum,"HaHa hi. [[motion:wave_hello]] Bye","repeated deltas are kept, not deduped");
assert.deepEqual(spoken,["HaHa hi.","Bye"]);
assert.deepEqual(moves,["motion:wave_hello"]);
assert.ok(events.some(u=>u.sessionUpdate==="tool_call_update"&&u.toolCallId==="t1"&&u.status==="completed"),"tool events reach the HUD");
const say=sent.filter(m=>m.op==="say").pop();assert.equal(say.text,"hello");assert.deepEqual(say.percept,[]);
mode="hang";
const p=b.ask("are you there");await tick(10);
sockets[sockets.length-1].close();
r=await Promise.race([p,tick(500).then(()=>"HUNG")]);
assert.notEqual(r,"HUNG","a dropped socket mid-turn resolves the turn");
assert.equal(r.error,"link dropped");
assert.equal(b.busy(),false);
mode="ok";await tick(80);
assert.ok(b.ready(),"reconnects with backoff");
assert.ok(sockets.length>=2);
mode="hang";
const p2=b.ask("long one");await tick(10);
assert.equal(b.cancel(),true);
r=await p2;assert.equal(r.stop,"cancelled");
assert.ok(sent.some(m=>m.op==="cancel"),"cancel goes to the server");
assert.ok(hushed>=1,"cancel flushes speech");
mode="perm";
const p3=b.ask("run ls");await tick(20);
assert.equal(permits.length,1);
assert.deepEqual(sent.filter(m=>m.op==="permit").pop(),{op:"permit",id:"p1",option:"deny"});
b.cancel();await p3;
b.setBrain("claude");await tick(20);
assert.equal(store.get("grok_companion_brain"),"claude","brain choice persists");
assert.equal(sent.filter(m=>m.op==="hello").pop().brain,"claude");
assert.equal(b.B.brain,"claude");assert.ok(b.B.caps.image);
mode="hang";
const b2=initBrain({KEY:"",getState:()=>"idle",setState(){},setLinked(){},say(){},speak(){},panels:{addConvo(){}},composeClip(){},sendMotion(){},turnMs:60});
b2.connect();await tick(30);
r=await b2.ask("x");assert.equal(r.error,"turn timed out","a silent brain cannot wedge the page");
assert.equal(cleanSpeech("**Hi** [[gaze:user]] there"),"Hi there");
for(const s of sockets)s.onclose=null;
console.log("xr-brain ok");
process.exit(0);
