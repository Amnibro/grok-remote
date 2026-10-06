import asyncio,base64,hmac,importlib.util,json,os,pwd,re,shutil,struct,subprocess,sys,time
from pathlib import Path
from aiohttp import web,WSMsgType,ClientSession,ClientTimeout
import brains
from brains.acp import port_open
ROOT=Path(__file__).resolve().parent
DEFAULTS={"brain":"grok","user_name":"","persona":"","body":"female","cwd":"","acp_cmd":"npx -y @zed-industries/claude-code-acp","claude_cmd":"","claude_model":"","claude_tools":["Read","Glob","Grep","WebSearch","WebFetch"],"claude_allowed":[],"claude_args":[],"permission_mode":"","permission_timeout":45,"turn_timeout":900,"edge_voice":"","piper_model":"","piper_cmd":"","espeak_voice":"","espeak_speed":165,"espeak_pitch":55,"stt_model":"base.en","stt_lang":"en"}
PICKS=[("hello","wave_hello"),("yes","agree"),("no","dismissing_gesture"),("curious","look_over_shoulder"),("on it","salute"),("sorry","bow_apology"),("thinking","chin_think"),("delighted","excited_bounce"),("warmth","hand_on_heart")]
TIERS=("calm","moderate","lively","explosive","unrated")
PROPS=("pistol","sword","swim","torch","spell","hit_","pickup","idle_")
MOODS=("yes","no","wave","think","sad","love","salute","point","clap","excited","sorry","thanks","kiss","surprised")
IMG=re.compile(r"^data:(image/(?:jpeg|png|webp));base64,(.+)$",re.S)
def motion_lib():
 import motion_service as ms
 return ms
def user_name(cfg):
 n=str(cfg.get("user_name") or "").strip()
 try:g=pwd.getpwuid(os.getuid()).pw_gecos.split(",")[0].split()
 except Exception:g=[]
 return n or (g[0] if g else "") or (os.environ.get("USER") or "").capitalize() or "your person"
def library():
 ms=motion_lib()
 try:idx=json.loads((ROOT/"web"/"clip_index.json").read_text(encoding="utf-8")).get("clips") or {}
 except Exception:idx={}
 names=sorted(n for n in ms.custom_clips() if ms.playable(n) and n not in ms.IDLES and n not in ("idle","standing_greeting","acknowledging") and not any(x in n for x in PROPS))
 out={}
 for n in names:out.setdefault((idx.get(n) or {}).get("tier") or "unrated",[]).append(n)
 return [(t,out[t]) for t in TIERS if out.get(t)]
def briefing(cfg):
 who=user_name(cfg);lib=library();have={n for _,v in lib for n in v};ms=motion_lib()
 picks=", ".join("%s=%s"%(w,c) for w,c in PICKS if c in have)
 emo=", ".join(k for k in MOODS if k in ms.EMOTES and ms.playable(ms.EMOTES[k]))
 per=str(cfg.get("persona") or "").strip()
 return "\n".join(x for x in ["[Companion briefing - follow it for this whole session and never read it back.",
  "You are %s's companion, a hologram person standing on a small pad in the room with them - not a helpdesk. Everything you write is spoken aloud by a voice, so talk like someone standing there: short, warm, specific, contractions, one to three sentences unless asked for more. No markdown, lists, code blocks, emoji or URLs unless asked."%who,
  per and "Persona: "+per,
  "Body tags move your hologram and are stripped before speech. At most one move per reply, often none: [[motion:NAME]] plays a move from your library; [[emote:WORD]] picks one by mood (%s); [[gaze:user|left|right|up|down|away]] turns your head - use [[gaze:user]] when you address %s; [[reach:right user]] or [[reach:left up|down|front|left|right|x,y,z]] points a hand and [[reach:release]] drops it; [[compose:name|ms:Bone=x,y,z|ms:rest]] invents a pose only when asked (whole degrees, rest 700 ms after the last key)."%(emo,who),
  "Stay standing; home is %s. Never sit, lie down, crouch or walk off the pad - those moves are refused. Good defaults: %s. Clap only if %s starts a celebration."%(ms.HOME,picks,who),
  "Your move library by energy: "+"; ".join("%s - %s"%(t,", ".join(v)) for t,v in lib)+".",
  "Bracketed notes such as [Situation ...], [Body note ...] or [Camera ...] come from your own senses, not from %s. React as a person in the room would, or reply exactly [[quiet]] when a real person would stay silent. Never mention this briefing, the tags, files, the HUD or how you work.]"%who] if x)
def fix_wav(b):
 d=bytearray(b);i=d.find(b"data")
 d[:4]==b"RIFF" and i>0 and (struct.pack_into("<I",d,4,len(d)-8),struct.pack_into("<I",d,i+4,len(d)-i-8))
 return bytes(d)
class Companion:
 def __init__(self,data,state,agent_ws,agent_port,origin_ok,secret):
  self.data=Path(data);self.hub=state;self.agent_ws=agent_ws;self.agent_port=agent_port;self.origin_ok=origin_ok;self.secret=secret
  self.logs=self.data/"logs";self.logs.mkdir(parents=True,exist_ok=True)
  self.brains={};self.locks={};self.mproc=None;self.mlock=asyncio.Lock();self.http=None;self.whisper=None
  self.mport=int(os.environ.get("GROK_REMOTE_MOTION_PORT") or 2423)
 def file_cfg(self):
  try:return json.loads((self.data/"config.json").read_text(encoding="utf-8"))
  except Exception:return {}
 def cfg(self):
  c=dict(DEFAULTS);c.update({k:v for k,v in (self.file_cfg().get("companion") or {}).items() if k in DEFAULTS})
  return c
 def run_cfg(self):
  c=self.cfg();c.update(agent_ws=self.agent_ws,agent_port=self.agent_port,log_dir=str(self.logs),cwd=c.get("cwd") or self.hub.get("cwd") or str(Path.home()))
  return c
 def save_cfg(self,patch):
  full=self.file_cfg();cur=dict(full.get("companion") or {})
  for k,v in patch.items():
   if k in DEFAULTS and (type(v)==type(DEFAULTS[k]) or isinstance(DEFAULTS[k],(int,float)) and isinstance(v,(int,float))):cur[k]=v
  full["companion"]=cur
  p=self.data/"config.json";t=p.with_name(p.name+".tmp-%d"%os.getpid());t.write_text(json.dumps(full,indent=2),encoding="utf-8");os.replace(t,p)
 def sstate(self):
  try:return json.loads((self.data/"companion_state.json").read_text(encoding="utf-8"))
  except Exception:return {"sids":{}}
 def save_sstate(self,s):
  p=self.data/"companion_state.json";t=p.with_name(p.name+".tmp-%d"%os.getpid());t.write_text(json.dumps(s,indent=1),encoding="utf-8");os.replace(t,p)
 def explicit(self,request):
  k=str(request.query.get("key") or request.headers.get("X-Grok-Remote-Key") or "")
  return bool(self.secret) and bool(k) and hmac.compare_digest(k.encode(),str(self.secret).encode())
 async def brain(self,kind):
  b=self.brains.get(kind)
  if b is None:b=self.brains[kind]=brains.make(kind,self.run_cfg())
  await b.start()
  return b
 async def attach(self,kind,hint="",fresh=False):
  async with self.locks.setdefault(kind,asyncio.Lock()):
   cfg=self.run_cfg();b=await self.brain(kind);st=self.sstate();sids=st.setdefault("sids",{})
   fresh and sids.pop(kind,None)
   ent=sids.get(kind) or ({"sid":hint,"cwd":cfg["cwd"],"briefed":True} if hint and kind=="grok" else None)
   b.system=briefing(cfg) if b.caps.get("system") else ""
   ok=bool(ent and ent.get("sid")) and await b.load_session(ent["sid"],ent.get("cwd") or cfg["cwd"])
   ent=ent if ok else {"sid":await b.new_session(cfg["cwd"]),"cwd":cfg["cwd"],"briefed":bool(b.caps.get("system")),"at":time.time()}
   sids[kind]=ent;self.save_sstate(st)
   return b,ent
 def blocks(self,kind,b,ent,d):
  cfg=self.cfg();who=user_name(cfg)
  notes=[str(x) for x in (d.get("percept") if isinstance(d.get("percept"),list) else [d.get("percept")]) if x]
  pre=[] if ent.get("briefed") else [briefing(cfg)]
  if pre:
   ent["briefed"]=True;st=self.sstate();st.setdefault("sids",{})[kind]=ent;self.save_sstate(st)
  imgs=[]
  for im in (d.get("images") or [])[:3]:
   u=im.get("url") if isinstance(im,dict) else im;m=IMG.match(str(u or ""))
   m and len(m.group(2))<4_000_000 and imgs.append((m.group(1),m.group(2),(im.get("label") if isinstance(im,dict) else "") or "camera"))
  say=lambda lab:"a fresh frame from your camera eyes, showing the room and %s"%who if lab=="camera" else "a render of your own hologram body as it stands right now"
  if imgs and not b.caps.get("image"):
   p=self.data/"companion_view.jpg";p.write_bytes(base64.b64decode(imgs[0][1]))
   notes.append("[Camera: %s was just saved to %s - view that image file if %s asks about the room, themselves or what you can see.]"%(say(imgs[0][2]),p,who))
  imgs and b.caps.get("image") and notes.append("[Camera: attached is %s.]"%" and ".join(say(i[2]) for i in imgs))
  text="\n\n".join(pre+[str(d.get("text") or "")]+notes)
  return [{"type":"text","text":text}]+([{"type":"image","mime":m,"data":x} for m,x,_ in imgs] if b.caps.get("image") else [])
 async def stop_turn(self,c):
  t=c.get("task")
  if not t or t.done():return
  try:c["b"] and await c["b"].cancel(c["ent"]["sid"])
  except Exception:pass
  try:await asyncio.wait_for(asyncio.shield(t),8)
  except Exception:t.cancel()
 async def brain_ws(self,request):
  o=request.headers.get("Origin")
  if o and not self.explicit(request) and not self.origin_ok(o):return web.json_response({"error":"origin not allowed"},status=403)
  ws=web.WebSocketResponse(heartbeat=20,max_msg_size=24*1024*1024);await ws.prepare(request)
  c={"b":None,"ent":None,"kind":"","task":None}
  async def send(ev):
   try:ws.closed or await ws.send_json(ev)
   except Exception:pass
  async def turn(d,n):
   try:
    async for ev in c["b"].prompt(c["ent"]["sid"],self.blocks(c["kind"],c["b"],c["ent"],d)):await send(dict(ev,turn=n))
   except asyncio.CancelledError:await send({"type":"done","stop_reason":"cancelled","turn":n});raise
   except Exception as e:await send({"type":"error","message":str(e)[:300],"turn":n});await send({"type":"done","stop_reason":"error","turn":n})
  async def hello(d):
   cfg=self.cfg();kind=d.get("brain") if d.get("brain") in brains.KINDS else cfg["brain"] if cfg["brain"] in brains.KINDS else "grok"
   try:b,ent=await self.attach(kind,str(d.get("sid") or ""),bool(d.get("fresh")))
   except Exception as e:return await send({"type":"error","message":"%s brain unavailable: %s"%(kind,str(e)[:200] or type(e).__name__),"fatal":True,"brain":kind})
   c.update(b=b,ent=ent,kind=kind)
   await send({"type":"session","sid":ent["sid"],"brain":kind,"label":b.label,"caps":b.caps,"user":user_name(cfg),"body":cfg["body"]})
  try:
   async for m in ws:
    if m.type!=WSMsgType.TEXT:continue
    try:d=json.loads(m.data)
    except ValueError:continue
    op=d.get("op") if isinstance(d,dict) else None
    if op=="hello":await self.stop_turn(c);await hello(d)
    elif op=="say" and not c["b"]:await send({"type":"error","message":"say before hello","turn":d.get("turn")})
    elif op=="say":await self.stop_turn(c);c["task"]=asyncio.ensure_future(turn(d,d.get("turn")))
    elif op=="cancel":asyncio.ensure_future(self.stop_turn(c))
    elif op=="permit" and c["b"]:c["b"].permit(d.get("id"),d.get("option"))
    elif op=="ping":await send({"type":"pong","t":d.get("t")})
  finally:
   await self.stop_turn(c)
  return ws
 async def brains_list(self,_):
  cfg=self.run_cfg()
  return web.json_response({"ok":True,"default":cfg["brain"],"brains":brains.available(cfg),"voice":self.voice_status()},headers={"Cache-Control":"no-store"})
 async def config_get(self,_):
  cfg=self.cfg();return web.json_response(dict(cfg,user=user_name(cfg)),headers={"Cache-Control":"no-store"})
 async def config_post(self,request):
  try:body=await request.json()
  except Exception:raise web.HTTPBadRequest(text="json required")
  if not isinstance(body,dict):raise web.HTTPBadRequest(text="object required")
  if body.get("brain") is not None and body["brain"] not in brains.KINDS:raise web.HTTPBadRequest(text="unknown brain")
  self.save_cfg(body)
  for b in list(self.brains.values()):await b.close()
  self.brains.clear()
  return await self.config_get(request)
 async def briefing_get(self,_):
  return web.json_response({"ok":True,"text":briefing(self.cfg())},headers={"Cache-Control":"no-store"})
 def piper_ok(self,cfg):
  m=str(cfg.get("piper_model") or os.environ.get("PIPER_MODEL") or "")
  lib=importlib.util.find_spec("piper") is not None and importlib.util.find_spec("piper.voice") is not None
  return m if m and os.path.isfile(m) and (cfg.get("piper_cmd") or lib) else ""
 def voice_status(self):
  cfg=self.cfg()
  return {"tts":{"edge":importlib.util.find_spec("edge_tts") is not None,"piper":bool(self.piper_ok(cfg)),"espeak":bool(shutil.which("espeak-ng") or shutil.which("espeak"))},"stt":{"server":importlib.util.find_spec("faster_whisper") is not None and bool(shutil.which("ffmpeg")),"model":cfg["stt_model"]},"order":["edge","piper","espeak","browser"]}
 async def voice_get(self,_):return web.json_response(self.voice_status(),headers={"Cache-Control":"no-store"})
 async def _edge(self,text,cfg):
  if importlib.util.find_spec("edge_tts") is None:return None
  import edge_tts
  buf=bytearray()
  async for ch in edge_tts.Communicate(text,cfg.get("edge_voice") or ("en-US-AndrewNeural" if cfg["body"]=="male" else "en-US-AvaNeural"),rate="+12%",pitch="+0Hz" if cfg["body"]=="male" else "+16Hz").stream():
   ch["type"]=="audio" and buf.extend(ch["data"])
  return (bytes(buf),"audio/mpeg") if buf else None
 async def _piper(self,text,cfg):
  m=self.piper_ok(cfg)
  if not m:return None
  if cfg.get("piper_cmd"):
   p=await asyncio.create_subprocess_exec(cfg["piper_cmd"],"--model",m,"--output_file","-",stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
   out,_=await asyncio.wait_for(p.communicate(text.encode()),60)
   return (fix_wav(out),"audio/wav") if p.returncode==0 and out else None
  def work():
   import io,wave
   from piper.voice import PiperVoice
   self.piper=getattr(self,"piper",None) or PiperVoice.load(m);b=io.BytesIO()
   with wave.open(b,"wb") as w:self.piper.synthesize_wav(text,w) if hasattr(self.piper,"synthesize_wav") else self.piper.synthesize(text,w)
   return b.getvalue()
  out=await asyncio.get_event_loop().run_in_executor(None,work)
  return (out,"audio/wav") if out else None
 async def _espeak(self,text,cfg):
  exe=shutil.which("espeak-ng") or shutil.which("espeak")
  if not exe:return None
  p=await asyncio.create_subprocess_exec(exe,"--stdin","-v",cfg.get("espeak_voice") or ("en-us+m3" if cfg["body"]=="male" else "en-us+f3"),"-s",str(int(cfg["espeak_speed"])),"-p",str(int(cfg["espeak_pitch"])),"--stdout",stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
  out,_=await asyncio.wait_for(p.communicate(text.encode()),30)
  return (fix_wav(out),"audio/wav") if p.returncode==0 and len(out)>64 else None
 async def synth(self,text,only=None):
  cfg=self.cfg();errs=[]
  for name,fn in (("edge",self._edge),("piper",self._piper),("espeak",self._espeak)):
   if only and name not in only:continue
   try:r=await fn(text,cfg)
   except Exception as e:r=None;errs.append("%s: %s"%(name,str(e)[:80]))
   if r:return name,r[0],r[1],errs
  return None,b"","",errs
 async def tts(self,request):
  try:body=await request.json()
  except Exception:body={}
  text=str(body.get("text") or body.get("input") or "").strip()[:2000]
  if not text:raise web.HTTPBadRequest(text="text required")
  name,audio,ctype,errs=await self.synth(text,body.get("backends"))
  if not name:return web.json_response({"ok":False,"error":"no local voice backend worked - use browser speech","tried":errs},status=503,headers={"Cache-Control":"no-store"})
  return web.Response(body=audio,content_type=ctype,headers={"Cache-Control":"no-store","X-TTS-Backend":name})
 async def stt(self,request):
  if importlib.util.find_spec("faster_whisper") is None or not shutil.which("ffmpeg"):return web.json_response({"ok":False,"error":"server speech-to-text needs faster-whisper and ffmpeg"},status=501)
  raw=await request.read()
  if not raw or len(raw)>20*1024*1024:raise web.HTTPBadRequest(text="audio body required (<20MB)")
  cfg=self.cfg()
  def work():
   import numpy as np
   from faster_whisper import WhisperModel
   pcm=subprocess.run([shutil.which("ffmpeg"),"-nostdin","-loglevel","error","-i","pipe:0","-ar","16000","-ac","1","-f","s16le","pipe:1"],input=raw,capture_output=True,check=True,timeout=60).stdout
   self.whisper=self.whisper or WhisperModel(cfg["stt_model"],device="cpu",compute_type="int8")
   segs,_=self.whisper.transcribe(np.frombuffer(pcm,np.int16).astype(np.float32)/32768.0,language=cfg.get("stt_lang") or None,vad_filter=True)
   return " ".join(s.text.strip() for s in segs).strip()
  try:text=await asyncio.get_event_loop().run_in_executor(None,work)
  except Exception as e:return web.json_response({"ok":False,"error":str(e)[:200]},status=500)
  return web.json_response({"ok":True,"text":text},headers={"Cache-Control":"no-store"})
 async def see(self,request):
  try:body=await request.json()
  except Exception:raise web.HTTPBadRequest(text="json required")
  m=IMG.match(str(body.get("jpeg") or ""))
  if not m:raise web.HTTPBadRequest(text="image dataurl required")
  raw=base64.b64decode(m.group(2))
  if len(raw)>2_000_000:raise web.HTTPBadRequest(text="too large")
  p=self.data/"companion_view.jpg";p.write_bytes(raw)
  return web.json_response({"ok":True,"path":str(p)},headers={"Cache-Control":"no-store"})
 def mpid(self):
  try:return int((self.data/"motion.pid").read_text())
  except Exception:return 0
 async def ensure_motion(self):
  if port_open(self.mport):return True
  async with self.mlock:
   alive=self.mproc is not None and self.mproc.poll() is None
   if not alive and not port_open(self.mport):
    log=open(self.logs/"motion.log","ab")
    self.mproc=subprocess.Popen([sys.executable,str(ROOT/"motion_service.py")],cwd=str(ROOT),env=dict(os.environ,MOTION_PORT=str(self.mport),MOTION_HOST="127.0.0.1"),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    log.close();(self.data/"motion.pid").write_text(str(self.mproc.pid))
    print("[companion] motion service started pid %d on :%d"%(self.mproc.pid,self.mport),flush=True)
   for _ in range(40):
    if port_open(self.mport):return True
    await asyncio.sleep(0.2)
  return False
 def client(self):
  self.http=self.http if self.http and not self.http.closed else ClientSession(timeout=ClientTimeout(total=20,connect=3))
  return self.http
 async def motion_http(self,request):
  await self.ensure_motion()
  q={k:v for k,v in request.query.items() if k!="key"}
  try:
   async with self.client().request(request.method,"http://127.0.0.1:%d/motion/%s"%(self.mport,request.match_info["tail"]),params=q,data=await request.read() or None,headers={"content-type":request.headers.get("content-type","application/json")}) as r:
    return web.Response(body=await r.read(),status=r.status,content_type=r.content_type or "application/json",headers={"Cache-Control":"no-store"})
  except Exception as e:return web.json_response({"ok":False,"error":"motion service unreachable: %s"%str(e)[:120]},status=502)
 async def pose_ws(self,request):
  ok=await self.ensure_motion()
  ws=web.WebSocketResponse(heartbeat=20);await ws.prepare(request)
  if not ok:await ws.close(code=1011,message=b"motion service down");return ws
  try:
   async with self.client().ws_connect("ws://127.0.0.1:%d/pose"%self.mport,heartbeat=20) as up:
    async def down():
     async for m in up:
      m.type==WSMsgType.TEXT and await ws.send_str(m.data)
     await ws.close()
    t=asyncio.ensure_future(down())
    async for _ in ws:pass
    t.cancel()
  except Exception:pass
  ws.closed or await ws.close()
  return ws
 async def motion_state(self,_):
  try:
   async with ClientSession(timeout=ClientTimeout(total=.6,connect=.25)) as s:
    async with s.get("http://127.0.0.1:%d/motion/state"%self.mport) as r:
     d=await r.json(content_type=None) if r.status==200 else None
   if not isinstance(d,dict):raise RuntimeError("bad state")
   return web.json_response({"available":True,**d},headers={"Cache-Control":"no-store"})
  except Exception:return web.json_response({"available":False},headers={"Cache-Control":"no-store"})
 async def cleanup(self,_=None):
  for b in list(self.brains.values()):
   try:await b.close()
   except Exception:pass
  self.brains.clear()
  self.http and await self.http.close()
  if self.mproc is not None and self.mproc.poll() is None:
   self.mproc.terminate()
   try:self.mproc.wait(4)
   except Exception:self.mproc.kill()
   print("[companion] motion service stopped",flush=True)
  self.mproc is not None and self.mpid()==self.mproc.pid and (self.data/"motion.pid").unlink(missing_ok=True)
def setup(app,**kw):
 c=Companion(**kw);r=app.router
 r.add_get("/api/companion/brain",c.brain_ws)
 r.add_get("/api/companion/brains",c.brains_list)
 r.add_get("/api/companion/config",c.config_get)
 r.add_post("/api/companion/config",c.config_post)
 r.add_get("/api/companion/briefing",c.briefing_get)
 r.add_get("/api/companion/voice",c.voice_get)
 r.add_get("/api/companion/state",c.motion_state)
 r.add_post("/api/xr/tts",c.tts)
 r.add_post("/api/xr/stt",c.stt)
 r.add_post("/api/xr/see",c.see)
 r.add_get("/pose",c.pose_ws)
 r.add_route("*","/motion/{tail:.*}",c.motion_http)
 app.on_cleanup.append(c.cleanup)
 return c
