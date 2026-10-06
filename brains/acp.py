import asyncio,json,os,shlex,shutil,socket
from urllib.parse import urlparse
from .base import Brain,summarize
CLIENT={"name":"grok-remote-companion","version":"0.3"}
def port_open(port,host="127.0.0.1"):
 try:
  with socket.create_connection((host,int(port)),timeout=0.3):return True
 except Exception:return False
class Acp(Brain):
 kind="acp-stdio";label="ACP agent (stdio)"
 def __init__(self,cfg):
  super().__init__(cfg);self._id=0;self._pend={};self.replay=set();self.proc=None;self.ws=None;self.sess=None;self.reader=None;self.ok=False
 @staticmethod
 def command(cfg):
  c=cfg.get("acp_cmd") or "npx -y @zed-industries/claude-code-acp"
  return shlex.split(c) if isinstance(c,str) else [str(x) for x in c]
 @classmethod
 def probe(cls,cfg):
  cmd=cls.command(cfg);exe=shutil.which(cmd[0]) if cmd else None
  return {"ok":bool(exe),"label":cls.label,"cmd":" ".join(cmd),"why":"" if exe else "%s not on PATH"%(cmd[0] if cmd else "no acp_cmd")}
 async def _open(self):
  log=open(os.path.join(self.cfg["log_dir"],"companion-acp.log"),"ab") if self.cfg.get("log_dir") else asyncio.subprocess.DEVNULL
  self.proc=await asyncio.create_subprocess_exec(*self.command(self.cfg),stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=log,cwd=self.cfg.get("cwd") or None,limit=64*1024*1024,start_new_session=True)
  self.reader=asyncio.ensure_future(self._read())
 async def _read(self):
  p=self.proc
  while p.stdout:
   line=await p.stdout.readline()
   if not line:break
   await self._line(line)
  self._dead("agent exited")
 async def _line(self,raw):
  try:m=json.loads(raw)
  except ValueError:return
  isinstance(m,dict) and await self._on(m)
 async def _send(self,obj):
  self.proc.stdin.write((json.dumps(obj)+"\n").encode());await self.proc.stdin.drain()
 def _dead(self,why):
  self.ok=False
  for f in list(self._pend.values()):f.done() or f.set_exception(RuntimeError(why))
  self._pend.clear();self.fail(why)
 async def _on(self,m):
  meth=m.get("method");p=m.get("params") or {}
  if meth is None and "id" in m:
   f=self._pend.pop(m["id"],None)
   f is None or f.done() or (f.set_exception(RuntimeError(json.dumps(m["error"])[:300])) if "error" in m else f.set_result(m.get("result") or {}))
   return
  if meth=="session/update":return self._update(p.get("sessionId"),p.get("update") or {})
  if meth=="session/request_permission":return asyncio.ensure_future(self._perm(m.get("id"),p))
  "id" in m and await self._send({"jsonrpc":"2.0","id":m["id"],"error":{"code":-32601,"message":"unsupported: %s"%meth}})
 def _update(self,sid,u):
  if sid in self.replay:return
  k=u.get("sessionUpdate");c=u.get("content")
  t="".join(b.get("text") or "" for b in c if isinstance(b,dict)) if isinstance(c,list) else (c.get("text") or "") if isinstance(c,dict) else ""
  ev={"agent_message_chunk":"text","agent_thought_chunk":"thought"}.get(k)
  ev and t and self.emit(sid,{"type":ev,"delta":t})
  k in ("tool_call","tool_call_update") and self.emit(sid,{"type":"tool","id":str(u.get("toolCallId") or ""),"title":str(u.get("title") or ""),"kind":str(u.get("kind") or ""),"status":str(u.get("status") or ""),"input":summarize(u.get("rawInput"))})
 async def _perm(self,rid,p):
  tc=p.get("toolCall") or {};opts=[{"id":str(o.get("optionId")),"name":str(o.get("name") or o.get("optionId")),"kind":str(o.get("kind") or "")} for o in p.get("options") or []]
  deny=next((o["id"] for o in opts if o["kind"].startswith("reject")),None)
  ch=await self.ask_permission(p.get("sessionId"),{"title":str(tc.get("title") or "tool"),"kind":str(tc.get("kind") or ""),"input":summarize(tc.get("rawInput"))},opts,deny)
  await self._send({"jsonrpc":"2.0","id":rid,"result":{"outcome":{"outcome":"selected","optionId":ch} if ch else {"outcome":"cancelled"}}})
 async def req(self,method,params,timeout=60):
  self._id+=1;i=self._id;f=asyncio.get_event_loop().create_future();self._pend[i]=f
  try:
   await self._send({"jsonrpc":"2.0","id":i,"method":method,"params":params})
   return await asyncio.wait_for(f,timeout)
  finally:self._pend.pop(i,None)
 async def start(self):
  async with self._lock:
   if self.ok:return
   await self._shut()
   await self._open()
   r=await self.req("initialize",{"protocolVersion":1,"clientInfo":CLIENT,"clientCapabilities":{"fs":{"readTextFile":False,"writeTextFile":False},"terminal":False}},30)
   ac=r.get("agentCapabilities") or {};pc=ac.get("promptCapabilities") or {}
   self.caps.update(image=bool(pc.get("image")),load=bool(ac.get("loadSession") or self.caps.get("load")))
   self.ok=True
 async def new_session(self,cwd):
  await self.start()
  sid=(await self.req("session/new",{"cwd":cwd,"mcpServers":[]},90)).get("sessionId")
  if not sid:raise RuntimeError("agent returned no sessionId")
  return str(sid)
 async def load_session(self,sid,cwd):
  await self.start()
  if not self.caps.get("load"):return False
  self.replay.add(sid)
  try:await self.req("session/load",{"sessionId":sid,"cwd":cwd,"mcpServers":[]},60);return True
  except Exception:return False
  finally:asyncio.get_event_loop().call_later(0.5,self.replay.discard,sid)
 async def _run(self,sid,blocks):
  await self.start()
  pr=[{"type":"text","text":b["text"]} if b["type"]=="text" else {"type":"image","mimeType":b.get("mime") or "image/jpeg","data":b["data"]} for b in blocks]
  try:r=await self.req("session/prompt",{"sessionId":sid,"prompt":pr},float(self.cfg.get("turn_timeout") or 900))
  except asyncio.TimeoutError:await self.cancel(sid);raise RuntimeError("turn timed out")
  self.emit(sid,{"type":"done","stop_reason":str(r.get("stopReason") or "end_turn")})
 async def cancel(self,sid):
  self.ok and await self._send({"jsonrpc":"2.0","method":"session/cancel","params":{"sessionId":sid}})
 async def _shut(self):
  self.ok=False
  self.reader and self.reader.cancel()
  if self.proc and self.proc.returncode is None:
   try:self.proc.terminate();await asyncio.wait_for(self.proc.wait(),3)
   except Exception:
    try:self.proc.kill()
    except Exception:pass
  self.ws is None or await self.ws.close()
  self.sess is None or await self.sess.close()
  self.proc=self.ws=self.sess=self.reader=None
 async def close(self):
  await self._shut();self.fail("brain closed")
class GrokAcp(Acp):
 kind="grok";label="Grok (grok agent)";caps={"image":False,"load":True,"system":False}
 @classmethod
 def probe(cls,cfg):
  u=urlparse(cfg.get("agent_ws") or "ws://127.0.0.1:2419/ws");ok=port_open(u.port or 2419,u.hostname or "127.0.0.1")
  return {"ok":ok,"label":cls.label,"why":"" if ok else "grok agent not listening on %s:%s"%(u.hostname,u.port)}
 async def _open(self):
  from aiohttp import ClientSession
  self.sess=ClientSession();self.ws=await self.sess.ws_connect(self.cfg["agent_ws"],heartbeat=30,max_msg_size=64*1024*1024)
  self.reader=asyncio.ensure_future(self._read())
 async def _read(self):
  ws=self.ws
  async for m in ws:
   isinstance(m.data,str) and await self._line(m.data)
  self._dead("grok agent socket closed")
 async def _send(self,obj):await self.ws.send_str(json.dumps(obj))
