import asyncio,json,os,re,shutil,uuid
from pathlib import Path
from .base import Brain,summarize,kind_of
SAFE=["Read","Glob","Grep","WebSearch","WebFetch"]
RISKY=["Bash","Edit","Write","NotebookEdit","MultiEdit"]
class Claude(Brain):
 kind="claude";label="Claude Code";caps={"image":True,"load":True,"system":True}
 def __init__(self,cfg):
  super().__init__(cfg);self.ps={};self.cwds={};self.known=set()
 @staticmethod
 def exe(cfg):
  return cfg.get("claude_cmd") or shutil.which("claude") or next((p for p in (str(Path.home()/".local"/"bin"/"claude"),str(Path.home()/".claude"/"local"/"claude")) if os.path.isfile(p)),"")
 @classmethod
 def probe(cls,cfg):
  x=cls.exe(cfg)
  return {"ok":bool(x),"label":cls.label,"cmd":x,"why":"" if x else "claude CLI not found on PATH"}
 @staticmethod
 def transcript(sid,cwd):
  root=Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home()/".claude")/"projects"
  return (root/re.sub(r"[^A-Za-z0-9]","-",str(cwd))/("%s.jsonl"%sid)).is_file()
 def args(self,sid):
  c=self.cfg;tools=[str(t) for t in (c.get("claude_tools") or SAFE)];allow=[str(t) for t in (c.get("claude_allowed") or [t for t in tools if t in SAFE])]
  a=[self.exe(c),"-p","--input-format","stream-json","--output-format","stream-json","--verbose","--include-partial-messages","--permission-prompt-tool","stdio","--tools",",".join(tools)]
  a+=["--allowedTools",",".join(allow)] if allow else []
  a+=["--disallowedTools",",".join(t for t in RISKY if t not in tools)] if any(t not in tools for t in RISKY) else []
  a+=["--permission-mode",str(c["permission_mode"])] if c.get("permission_mode") else []
  a+=["--model",str(c["claude_model"])] if c.get("claude_model") else []
  a+=["--append-system-prompt",self.system] if self.system else []
  return a+(["--resume",sid] if sid in self.known else ["--session-id",sid])+[str(x) for x in c.get("claude_args") or []]
 async def _spawn(self,sid):
  log=open(os.path.join(self.cfg["log_dir"],"companion-claude.log"),"ab") if self.cfg.get("log_dir") else asyncio.subprocess.DEVNULL
  env={k:v for k,v in os.environ.items() if not (k.startswith("CLAUDE_CODE_") or k in ("CLAUDECODE","CLAUDE_PID","CLAUDE_EFFORT"))}
  p=await asyncio.create_subprocess_exec(*self.args(sid),stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=log,cwd=self.cwds.get(sid) or None,limit=64*1024*1024,start_new_session=True,env=env)
  st={"proc":p,"turn":False,"cancel":False,"streamed":False,"texted":False}
  st["reader"]=asyncio.ensure_future(self._read(sid,st));self.ps[sid]=st
  return st
 async def new_session(self,cwd):
  sid=str(uuid.uuid4());self.cwds[sid]=cwd;return sid
 async def load_session(self,sid,cwd):
  ok=sid in self.known or self.transcript(sid,cwd)
  ok and (self.known.add(sid),self.cwds.__setitem__(sid,cwd))
  return bool(ok)
 async def _write(self,st,obj):
  st["proc"].stdin.write((json.dumps(obj)+"\n").encode());await st["proc"].stdin.drain()
 async def _run(self,sid,blocks):
  st=self.ps.get(sid)
  st=st if st and st["proc"].returncode is None else await self._spawn(sid)
  st.update(turn=True,cancel=False,streamed=False,texted=False)
  content=[{"type":"text","text":b["text"]} if b["type"]=="text" else {"type":"image","source":{"type":"base64","media_type":b.get("mime") or "image/jpeg","data":b["data"]}} for b in blocks]
  await self._write(st,{"type":"user","message":{"role":"user","content":content},"parent_tool_use_id":None,"session_id":sid})
 async def _read(self,sid,st):
  p=st["proc"]
  while True:
   line=await p.stdout.readline()
   if not line:break
   try:m=json.loads(line)
   except ValueError:continue
   isinstance(m,dict) and await self._on(sid,st,m)
  rc=await p.wait()
  st["turn"] and (self.emit(sid,{"type":"error","message":"claude exited (%s) - see companion-claude.log"%rc}),self.emit(sid,{"type":"done","stop_reason":"error"}))
  st["turn"]=False
  self.ps.get(sid) is st and self.ps.pop(sid,None)
 def _text(self,sid,st,t):
  t and (st["texted"]=="gap" and self.emit(sid,{"type":"text","delta":"\n"}),st.__setitem__("texted",True),self.emit(sid,{"type":"text","delta":t}))
 async def _on(self,sid,st,m):
  t=m.get("type")
  m.get("session_id") and self.known.add(sid)
  if t=="stream_event":
   e=m.get("event") or {};et=e.get("type");d=e.get("delta") or {};b=e.get("content_block") or {}
   et=="message_start" and st["texted"] and st.__setitem__("texted","gap")
   et=="content_block_delta" and d.get("type")=="text_delta" and (st.__setitem__("streamed",True),self._text(sid,st,d.get("text")))
   et=="content_block_delta" and d.get("type")=="thinking_delta" and d.get("thinking") and self.emit(sid,{"type":"thought","delta":d["thinking"]})
   et=="content_block_start" and b.get("type")=="tool_use" and self.emit(sid,{"type":"tool","id":str(b.get("id") or ""),"title":str(b.get("name") or "tool"),"kind":kind_of(b.get("name")),"status":"pending","input":""})
   return
  if t=="assistant":
   for b in (m.get("message") or {}).get("content") or []:
    b.get("type")=="tool_use" and self.emit(sid,{"type":"tool","id":str(b.get("id") or ""),"title":str(b.get("name") or "tool"),"kind":kind_of(b.get("name")),"status":"in_progress","input":summarize(b.get("input"))})
    b.get("type")=="text" and not st["streamed"] and self._text(sid,st,b.get("text"))
   st["streamed"]=False
   return
  if t=="user":
   for b in ((m.get("message") or {}).get("content") or []) if isinstance((m.get("message") or {}).get("content"),list) else []:
    b.get("type")=="tool_result" and self.emit(sid,{"type":"tool","id":str(b.get("tool_use_id") or ""),"title":"","kind":"","status":"failed" if b.get("is_error") else "completed","input":""})
   return
  if t=="result":
   err=m.get("is_error") or m.get("subtype")!="success"
   err and not st["cancel"] and self.emit(sid,{"type":"error","message":str(m.get("result") or m.get("subtype") or "claude error")[:300]})
   st["turn"] and self.emit(sid,{"type":"done","stop_reason":"cancelled" if st["cancel"] else "error" if err else "end_turn"})
   st["turn"]=False
   return
  if t=="control_request":
   r=m.get("request") or {};rid=m.get("request_id")
   if r.get("subtype")=="can_use_tool":return asyncio.ensure_future(self._perm(sid,st,rid,r))
   await self._write(st,{"type":"control_response","response":{"subtype":"error","request_id":rid,"error":"unsupported: %s"%r.get("subtype")}})
 async def _perm(self,sid,st,rid,r):
  name=str(r.get("tool_name") or "tool");inp=r.get("input") or {}
  opts=[{"id":"allow","name":"Allow once","kind":"allow_once"},{"id":"deny","name":"Deny","kind":"reject_once"}]
  ch=await self.ask_permission(sid,{"title":name,"kind":kind_of(name),"input":summarize(inp,160)},opts,"deny")
  resp={"behavior":"allow","updatedInput":inp} if ch=="allow" else {"behavior":"deny","message":"The user declined this from the companion."}
  try:await self._write(st,{"type":"control_response","response":{"subtype":"success","request_id":rid,"response":resp}})
  except Exception:pass
 async def cancel(self,sid):
  st=self.ps.get(sid)
  if not st or not st["turn"]:return
  st["cancel"]=True
  try:await self._write(st,{"type":"control_request","request_id":uuid.uuid4().hex,"request":{"subtype":"interrupt"}})
  except Exception:pass
  asyncio.get_event_loop().call_later(float(self.cfg.get("cancel_grace") or 6),self._reap,sid,st)
 def _reap(self,sid,st):
  if not st["turn"]:return
  st["turn"]=False;self.emit(sid,{"type":"done","stop_reason":"cancelled"})
  try:st["proc"].kill()
  except Exception:pass
 async def close(self):
  for st in list(self.ps.values()):
   st["reader"].cancel()
   try:st["proc"].kill();await asyncio.wait_for(st["proc"].wait(),3)
   except Exception:pass
  self.ps.clear();self.fail("brain closed")
