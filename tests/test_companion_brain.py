import asyncio,json,os,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import brains,companion
from brains.claude import Claude
from aiohttp import web
from aiohttp.test_utils import TestServer,TestClient
FAKE=[sys.executable,str(ROOT/"tests"/"fake_acp_agent.py")]
async def drain(gen):return [e async for e in gen]
class Briefing(unittest.TestCase):
 def test_names_are_real_and_user_is_configurable(self):
  b=companion.briefing({"user_name":"Sam"})
  self.assertIn("Sam",b);self.assertNotIn("Anthony",b);self.assertIn("[[reach:",b);self.assertIn("[[compose:",b);self.assertIn("[[quiet]]",b)
  have={p.stem for p in (ROOT/"clips").glob("*.json")}
  for t,names in companion.library():
   for n in names:self.assertIn(n,have)
  for _,c in companion.PICKS:self.assertIn(c,have)
 def test_fix_wav_sizes(self):
  raw=b"RIFF\xff\xff\xff\x7fWAVEfmt "+b"\0"*20+b"data\xff\xff\xff\x7f"+b"\1"*10
  w=companion.fix_wav(raw)
  self.assertEqual(int.from_bytes(w[4:8],"little"),len(w)-8);i=w.find(b"data");self.assertEqual(int.from_bytes(w[i+4:i+8],"little"),10)
class AcpStdio(unittest.TestCase):
 def test_turn_permission_cancel_and_load(self):
  async def go():
   b=brains.make("acp-stdio",{"acp_cmd":FAKE,"permission_timeout":0.3})
   await b.start();self.assertTrue(b.caps["image"]);self.assertTrue(b.caps["load"])
   sid=await b.new_session("/tmp");self.assertEqual(sid,"fs-1")
   ev=await drain(b.prompt(sid,[{"type":"text","text":"hi"},{"type":"image","mime":"image/jpeg","data":"AAAA"}]))
   kinds=[e["type"] for e in ev]
   self.assertEqual(kinds[-1],"done");self.assertIn("thought",kinds)
   self.assertEqual("".join(e["delta"] for e in ev if e["type"]=="text"),"Hello there. images=1")
   tools=[e for e in ev if e["type"]=="tool"];self.assertEqual(tools[0]["input"],"/x");self.assertEqual(tools[1]["status"],"completed")
   gen=b.prompt(sid,[{"type":"text","text":"perm please"}]);got=[]
   async for e in gen:
    got.append(e)
    e["type"]=="permission" and b.permit(e["id"],"ok")
   self.assertIn("chose ok","".join(e.get("delta","") for e in got))
   got=await drain(b.prompt(sid,[{"type":"text","text":"perm again"}]))
   self.assertIn("chose no","".join(e.get("delta","") for e in got),"unanswered permission is denied on timeout")
   async def later():await asyncio.sleep(0.2);await b.cancel(sid)
   t=asyncio.ensure_future(later());got=await asyncio.wait_for(drain(b.prompt(sid,[{"type":"text","text":"hang"}])),5);await t
   self.assertEqual(got[-1],{"type":"done","stop_reason":"cancelled"})
   self.assertTrue(await b.load_session(sid,"/tmp"))
   got=await drain(b.prompt(sid,[{"type":"text","text":"after load"}]))
   self.assertNotIn("REPLAY","".join(e.get("delta","") for e in got),"session/load replay is never spoken")
   await b.close()
   got=await drain(b.prompt(sid,[{"type":"text","text":"restarts"}]))
   self.assertEqual(got[-1]["type"],"done")
   await b.close()
  asyncio.run(go())
 def test_dead_agent_ends_the_turn(self):
  async def go():
   b=brains.make("acp-stdio",{"acp_cmd":[sys.executable,"-c","import sys,json\nfor l in sys.stdin:\n m=json.loads(l)\n if m.get('method')=='initialize':print(json.dumps({'jsonrpc':'2.0','id':m['id'],'result':{}}),flush=True)\n elif m.get('method')=='session/new':print(json.dumps({'jsonrpc':'2.0','id':m['id'],'result':{'sessionId':'d'}}),flush=True)\n else:sys.exit(3)"]})
   sid=await b.new_session("/tmp")
   got=await asyncio.wait_for(drain(b.prompt(sid,[{"type":"text","text":"x"}])),5)
   self.assertEqual([e["type"] for e in got][-2:],["error","done"])
   await b.close()
  asyncio.run(go())
class ClaudeStream(unittest.TestCase):
 def test_safe_args(self):
  c=Claude({"claude_cmd":"/bin/claude"});c.system="BRIEF"
  a=c.args("s1")
  self.assertIn("--session-id",a);self.assertEqual(a[a.index("--tools")+1],"Read,Glob,Grep,WebSearch,WebFetch")
  self.assertIn("Bash",a[a.index("--disallowedTools")+1]);self.assertEqual(a[a.index("--append-system-prompt")+1],"BRIEF")
  c.known.add("s1");self.assertIn("--resume",c.args("s1"))
  c2=Claude({"claude_cmd":"/bin/claude","claude_tools":["Read","Bash"]})
  a2=c2.args("s2");self.assertEqual(a2[a2.index("--allowedTools")+1],"Read");self.assertNotIn("Bash",a2[a2.index("--disallowedTools")+1])
 def test_stream_mapping(self):
  async def go():
   c=Claude({});sid="s";q=c.qs[sid]=asyncio.Queue();st={"turn":True,"cancel":False,"streamed":False,"texted":False}
   msgs=[{"type":"system","subtype":"init","session_id":sid},
    {"type":"stream_event","event":{"type":"message_start"}},
    {"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":"ok"}}},
    {"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"Let me look"}}},
    {"type":"stream_event","event":{"type":"content_block_start","content_block":{"type":"tool_use","id":"tu1","name":"Read"}}},
    {"type":"assistant","message":{"content":[{"type":"text","text":"Let me look"},{"type":"tool_use","id":"tu1","name":"Read","input":{"file_path":"/a"}}]}},
    {"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"tu1","is_error":False}]}},
    {"type":"stream_event","event":{"type":"message_start"}},
    {"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"Found it"}}},
    {"type":"assistant","message":{"content":[{"type":"text","text":"Found it"}]}},
    {"type":"result","subtype":"success","is_error":False,"result":"x"}]
   for m in msgs:await c._on(sid,st,m)
   ev=[q.get_nowait() for _ in range(q.qsize())]
   self.assertEqual("".join(e["delta"] for e in ev if e["type"]=="text"),"Let me look\nFound it")
   self.assertEqual([e["status"] for e in ev if e["type"]=="tool"],["pending","in_progress","completed"])
   self.assertEqual(ev[-1],{"type":"done","stop_reason":"end_turn"});self.assertIn(sid,c.known)
  asyncio.run(go())
class Endpoint(unittest.TestCase):
 def test_ws_protocol_with_stdio_brain(self):
  async def go():
   d=Path(tempfile.mkdtemp());(d/"config.json").write_text(json.dumps({"autostart":True,"companion":{"brain":"acp-stdio","acp_cmd":FAKE,"user_name":"Sam"}}))
   app=web.Application();comp=companion.setup(app,data=d,state={"cwd":str(d)},agent_ws="ws://127.0.0.1:1/ws",agent_port=1,origin_ok=lambda o:o=="http://ok",secret="s3")
   async with TestClient(TestServer(app)) as cl:
    r=await cl.get("/api/companion/brains");j=await r.json();self.assertEqual({b["kind"] for b in j["brains"]},{"grok","claude","acp-stdio"});self.assertIn("tts",j["voice"])
    r=await cl.get("/api/companion/brain",headers={"Origin":"http://evil"});self.assertEqual(r.status,403)
    ws=await cl.ws_connect("/api/companion/brain",headers={"Origin":"http://ok"})
    await ws.send_json({"op":"hello"});s=await ws.receive_json()
    self.assertEqual((s["type"],s["sid"],s["brain"],s["user"]),("session","fs-1","acp-stdio","Sam"))
    await ws.send_json({"op":"say","turn":1,"text":"hi","images":["data:image/jpeg;base64,/9j/AAAA"],"percept":["[Body note: fine]"]})
    ev=[]
    while not ev or ev[-1]["type"]!="done":ev.append(await ws.receive_json())
    self.assertTrue(all(e["turn"]==1 for e in ev));self.assertIn("images=1","".join(e.get("delta","") for e in ev))
    st=json.loads((d/"companion_state.json").read_text())["sids"]["acp-stdio"];self.assertTrue(st["briefed"])
    await ws.send_json({"op":"say","turn":2,"text":"hang"});await asyncio.sleep(0.3);await ws.send_json({"op":"cancel"})
    ev=[]
    while not ev or ev[-1]["type"]!="done":ev.append(await ws.receive_json())
    self.assertEqual(ev[-1]["stop_reason"],"cancelled")
    await ws.close()
    r=await cl.post("/api/companion/config",json={"user_name":"Kim","bogus":1});j=await r.json();self.assertEqual(j["user"],"Kim");self.assertNotIn("bogus",j)
    self.assertEqual(json.loads((d/"config.json").read_text())["autostart"],True,"other config keys survive")
    r=await cl.post("/api/xr/tts",json={"text":"hello there","backends":["espeak"]})
    self.assertIn(r.status,(200,503));r.status==200 and self.assertEqual((await r.read())[:4],b"RIFF")
  asyncio.run(go())
if __name__=="__main__":unittest.main()
