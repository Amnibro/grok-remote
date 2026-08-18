"""Grok Remote: UI + multi-client WS hub (fan-out) + workspace FS API."""
import os,sys,json,socket,argparse,asyncio,mimetypes,subprocess,shutil,re,time,uuid
from pathlib import Path
from urllib.parse import quote,unquote
ROOT=Path(__file__).resolve().parent
try:
 import room as room_store
except Exception:
 room_store=None
WEB=ROOT/"web"
GROK_SESSIONS=Path.home()/".grok"/"sessions"
LOOP_STORE=Path.home()/".grok"/"plugin-data"/"grok-remote"/"loops.json"
HISTORY_KEEP={"user_message_chunk","agent_message_chunk","agent_thought_chunk","tool_call","tool_call_update","plan","session_recap","turn_completed","task_completed","available_commands_update"}
SKIP_DIR={".git","node_modules","__pycache__",".venv","venv","dist","build",".next",".cache","desktop/node_modules"}
MAX_READ=2_000_000
MAX_WRITE=4_000_000
TEXT_EXT={".py",".js",".ts",".tsx",".jsx",".json",".md",".txt",".css",".html",".htm",".xml",".yml",".yaml",".toml",".ini",".cfg",".env",".sh",".ps1",".bat",".cmd",".rs",".go",".java",".c",".h",".cpp",".hpp",".cs",".rb",".php",".sql",".r",".swift",".kt",".vue",".svelte",".scss",".less",".svg",".gitignore",".dockerfile",".cmake",".gradle",".log",".diff",".patch",".csv"}
def lan_ip():
 try:
  with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
   s.connect(("8.8.8.8",80));return s.getsockname()[0]
 except Exception:return "127.0.0.1"
def find_grok():
 for p in (Path.home()/".grok"/"bin"/"grok.exe",Path.home()/".grok"/"bin"/"grok",shutil.which("grok") or ""):
  if p and Path(p).is_file():return str(Path(p))
 return None
def listen_pids_port(port:int,exclude_self=True):
 pids=[];me=os.getpid()
 try:
  out=subprocess.run(["netstat","-ano"],capture_output=True,text=True,timeout=8,encoding="utf-8",errors="replace")
  for line in (out.stdout or "").splitlines():
   if "LISTENING" not in line:continue
   parts=line.split()
   if len(parts)<5:continue
   addr=parts[1]
   try:
    if int(addr.rsplit(":",1)[1])!=port:continue
   except Exception:continue
   try:pid=int(parts[-1])
   except Exception:continue
   if pid<=0:continue
   if exclude_self and pid==me:continue
   pids.append(pid)
 except Exception:pass
 return sorted(set(pids))
def kill_pids_list(pids):
 killed=[]
 for pid in pids:
  try:
   r=subprocess.run(["taskkill","/F","/PID",str(pid)],capture_output=True,text=True,timeout=8,encoding="utf-8",errors="replace")
   killed.append({"pid":pid,"ok":r.returncode==0,"out":((r.stdout or "")+(r.stderr or ""))[:120]})
  except Exception as e:
   killed.append({"pid":pid,"ok":False,"out":str(e)[:120]})
 return killed
def claim_port(port:int,label="port"):
 pids=listen_pids_port(port,exclude_self=True)
 if not pids:return []
 print("[claim] free %s :%d pids=%s"%(label,port,pids),flush=True)
 return kill_pids_list(pids)
def use_leader_mode():
 v=str(os.environ.get("GROK_REMOTE_LEADER") or "").strip().lower()
 return v in ("1","true","yes","on")
def write_run_agent_cmd(secret:str,agent_port:int,cwd:str,use_leader=None):
 log_dir=ROOT/"logs";log_dir.mkdir(parents=True,exist_ok=True)
 grok=find_grok()
 if not grok:return None
 agent_log=log_dir/"agent.log"
 cmd_path=log_dir/"run-agent.cmd"
 cwd_s=str(cwd).replace('"','')
 if use_leader is None:use_leader=use_leader_mode()
 flag="--leader" if use_leader else "--no-leader"
 body="@echo off\r\ncd /d \"%s\"\r\nset GROK_AGENT_SECRET=%s\r\n\"%s\" agent --always-approve %s serve --bind 127.0.0.1:%d --secret %s >> \"%s\" 2>&1\r\n"%(cwd_s,secret,grok,flag,agent_port,secret,agent_log)
 cmd_path.write_text(body,encoding="utf-8",errors="replace")
 return cmd_path
def start_agent_process(secret:str,agent_port:int,cwd:str,force=False):
 if not force and listen_pids_port(agent_port,exclude_self=False):
  print("[boot] agent already on :%d — leave it"%agent_port,flush=True)
  return "existing"
 if force:claim_port(agent_port,"agent")
 grok=find_grok()
 if not grok:raise RuntimeError("grok.exe not found under ~/.grok/bin")
 write_run_agent_cmd(secret,agent_port,cwd,use_leader=False)
 log_dir=ROOT/"logs";log_dir.mkdir(parents=True,exist_ok=True)
 log_path=log_dir/"agent.spawn.log"
 try:logf=open(log_path,"a",encoding="utf-8",errors="replace")
 except Exception:logf=subprocess.DEVNULL
 creation=0x08000000 if sys.platform=="win32" else 0
 env=dict(os.environ);env["GROK_AGENT_SECRET"]=str(secret)
 subprocess.Popen([grok,"agent","--always-approve","--no-leader","serve","--bind","127.0.0.1:%d"%int(agent_port),"--secret",str(secret)],
  cwd=str(cwd),stdout=logf,stderr=logf,stdin=subprocess.DEVNULL,
  creationflags=creation if sys.platform=="win32" else 0,env=env,close_fds=False)
 print("[boot] spawned grok agent serve :%d"%int(agent_port),flush=True)
 return grok
def wait_port(port:int,timeout=20.0):
 import time
 t0=time.time()
 while time.time()-t0<timeout:
  if listen_pids_port(port,exclude_self=False):return True
  time.sleep(0.35)
 return False
def xai_api_key():
 for k in ("XAI_API_KEY","GROK_API_KEY","xai_api_key"):
  v=(os.environ.get(k) or "").strip()
  if v:return v
 try:
  p=Path.home()/".grok"/"credentials.json"
  if p.is_file():
   d=json.loads(p.read_text(encoding="utf-8",errors="replace"))
   if isinstance(d,dict):
    for k in ("XAI_API_KEY","apiKey","api_key","xaiApiKey","token"):
     v=str(d.get(k) or "").strip()
     if v:return v
 except Exception:pass
 return ""
def archive_store_path():
 base=os.environ.get("GROK_PLUGIN_DATA") or str(Path.home()/".grok"/"plugin-data"/"grok-remote")
 p=Path(base);p.mkdir(parents=True,exist_ok=True)
 return p/"archived_sessions.json"
def load_archived_ids():
 path=archive_store_path()
 if not path.is_file():return []
 try:
  data=json.loads(path.read_text(encoding="utf-8",errors="replace"))
  if isinstance(data,dict):ids=data.get("ids") or data.get("archived") or []
  elif isinstance(data,list):ids=data
  else:ids=[]
  out=[];seen=set()
  for x in ids:
   s=str(x or "").strip()
   if not s or s in seen:continue
   seen.add(s);out.append(s)
  return out
 except Exception:return []
def save_archived_ids(ids):
 path=archive_store_path()
 clean=[];seen=set()
 for x in ids or []:
  s=str(x or "").strip()
  if not s or s in seen:continue
  seen.add(s);clean.append(s)
 path.write_text(json.dumps({"ids":clean,"updatedAt":__import__("time").time()},indent=2),encoding="utf-8")
 return clean
def encode_session_cwd(cwd:str):
 s=str(Path(cwd).expanduser()) if cwd else ""
 s=s.replace("/","\\") if os.name=="nt" else s
 return quote(s,safe="")
def _session_dir_ok(d:Path):
 return d.is_dir() and ((d/"updates.jsonl").is_file() or (d/"summary.json").is_file())
_SID_INDEX=None
_SID_INDEX_AT=0.0
_SID_DIR_CACHE={}
def _rebuild_sid_index():
 global _SID_INDEX,_SID_INDEX_AT
 idx={}
 root=GROK_SESSIONS
 if root.is_dir():
  try:
   for p in root.iterdir():
    if not p.is_dir():continue
    try:
     for c in p.iterdir():
      if not c.is_dir():continue
      name=c.name
      if ".." in name or "/" in name or "\\" in name:continue
      if (c/"updates.jsonl").is_file() or (c/"summary.json").is_file():
       idx.setdefault(name,[]).append(c)
    except Exception:pass
  except Exception:pass
 _SID_INDEX=idx
 _SID_INDEX_AT=time.time()
 return idx
def _sid_index(force=False):
 global _SID_INDEX,_SID_INDEX_AT
 if force or _SID_INDEX is None or (time.time()-_SID_INDEX_AT)>60:return _rebuild_sid_index()
 return _SID_INDEX
def _cache_session_dir(sid,cwd,d):
 if not d:return d
 _SID_DIR_CACHE[(sid,str(cwd or ""))]= (str(d),time.time()+90)
 return d
def find_session_dir(session_id:str,cwd:str|None=None):
 sid=str(session_id or "").strip()
 if not sid or ".." in sid or "/" in sid or "\\" in sid:return None
 root=GROK_SESSIONS
 if not root.is_dir():return None
 ck=(sid,str(cwd or ""))
 hit=_SID_DIR_CACHE.get(ck)
 if hit:
  p,exp=hit
  if time.time()<exp:
   d=Path(p)
   if _session_dir_ok(d):return d
  else:_SID_DIR_CACHE.pop(ck,None)
 if cwd:
  c=""
  try:c=str(Path(cwd).expanduser().resolve()) if cwd not in (".","") else ""
  except Exception:c=str(cwd or "")
  variants=[]
  if c:
   for v in (c,c.replace("/","\\"),c.replace("\\","/"),str(Path(c))):
    if v and v not in variants:variants.append(v)
    if os.name=="nt":
     v2=v.replace("\\","\\\\")
     if v2 not in variants:variants.append(v2)
  for variant in variants:
   enc=encode_session_cwd(variant)
   d=root/enc/sid
   if _session_dir_ok(d):return _cache_session_dir(sid,cwd,d)
   enc2=quote(variant.replace("/","\\").replace("\\","\\\\") if os.name=="nt" else variant,safe="")
   d2=root/enc2/sid
   if _session_dir_ok(d2):return _cache_session_dir(sid,cwd,d2)
 hits=list(_sid_index().get(sid) or [])
 if not hits and (time.time()-_SID_INDEX_AT)>5.0:
  hits=list(_sid_index(force=True).get(sid) or [])
 hits=[d for d in hits if _session_dir_ok(d)]
 if len(hits)==1:return _cache_session_dir(sid,cwd,hits[0])
 if len(hits)>1:
  if cwd:
   try:
    cnorm=str(Path(cwd).expanduser().resolve()).replace("/","\\").lower() if os.name=="nt" else str(Path(cwd).expanduser().resolve())
   except Exception:
    cnorm=str(cwd or "").replace("/","\\").lower() if os.name=="nt" else str(cwd or "")
   cwd_hits=[]
   for d in hits:
    try:
     parent=unquote(d.parent.name).replace("/","\\")
     pl=parent.lower() if os.name=="nt" else parent
     if cnorm and (pl==cnorm or pl.endswith(cnorm) or cnorm.endswith(pl)):cwd_hits.append(d)
    except Exception:pass
   if len(cwd_hits)==1:return _cache_session_dir(sid,cwd,cwd_hits[0])
   if cwd_hits:hits=cwd_hits
  hits.sort(key=lambda d:(d/"updates.jsonl").stat().st_mtime if (d/"updates.jsonl").is_file() else 0,reverse=True)
  return _cache_session_dir(sid,cwd,hits[0])
 return None
def read_session_title(sdir:Path):
 if not sdir:return ""
 try:
  summ=json.loads((sdir/"summary.json").read_text(encoding="utf-8",errors="replace"))
  return str(summ.get("remote_title") or summ.get("generated_title") or summ.get("session_summary") or "").strip()
 except Exception:return ""
def read_session_info(sdir:Path):
 out={"title":"","cwd":""}
 if not sdir:return out
 try:
  summ=json.loads((sdir/"summary.json").read_text(encoding="utf-8",errors="replace"))
  out["title"]=str(summ.get("remote_title") or summ.get("generated_title") or summ.get("session_summary") or "").strip()
  info=summ.get("info") if isinstance(summ.get("info"),dict) else {}
  out["cwd"]=str(info.get("cwd") or summ.get("cwd") or "").strip()
 except Exception:pass
 return out
def _parse_update_line(line,live=False):
 line=(line or "").strip()
 if not line:return None
 try:obj=json.loads(line)
 except Exception:return None
 params=obj.get("params") if isinstance(obj,dict) else None
 if not isinstance(params,dict):return None
 update=params.get("update") if isinstance(params.get("update"),dict) else None
 if not update:return None
 kind=update.get("sessionUpdate") or ""
 if kind not in HISTORY_KEEP:return None
 content=update.get("content") if isinstance(update.get("content"),dict) else {}
 text=(content.get("text") if content else None) or ""
 if kind in ("user_message_chunk","agent_message_chunk","agent_thought_chunk") and not str(text).strip():
  return None
 if kind=="tool_call_update" and not live:
  st=str(update.get("status") or "")
  if st and st.lower() not in ("completed","failed","cancelled","error","done","success") and not update.get("content") and not update.get("rawOutput"):
   return None
 meta=params.get("_meta") if isinstance(params.get("_meta"),dict) else {}
 umeta=update.get("_meta") if isinstance(update.get("_meta"),dict) else {}
 merged=dict(meta or {})
 if umeta:
  for k,v in umeta.items():
   if k not in merged:merged[k]=v
 return {
  "method":obj.get("method") or "session/update",
  "params":{"sessionId":params.get("sessionId"),"update":update,"_meta":merged},
  "_kind":kind,
  "_eid":str(merged.get("eventId") or umeta.get("eventId") or ""),
 }
def _strip_ev(ev):
 return {k:v for k,v in ev.items() if not k.startswith("_")}
_CHAT_TEXT_CAP=120_000
_CHAT_MARK_A=b"user_message_chunk"
_CHAT_MARK_B=b"agent_message_chunk"
def _trim_chat_text(ev,cap=_CHAT_TEXT_CAP):
 try:
  u=((ev.get("params") or {}).get("update") or {})
  c=u.get("content") if isinstance(u.get("content"),dict) else None
  if not c:return ev
  t=c.get("text")
  if isinstance(t,str) and len(t)>cap:
   c=dict(c);c["text"]=t[:cap]+"\n…[truncated for load speed]";u=dict(u);u["content"]=c
   p=dict(ev.get("params") or {});p["update"]=u;ev=dict(ev);ev["params"]=p
 except Exception:pass
 return ev
def _coalesce_chat(events):
 out=[]
 for ev in events:
  kind=ev.get("_kind") or ""
  if kind not in ("user_message_chunk","agent_message_chunk") or not out:
   out.append(ev);continue
  prev=out[-1]
  if prev.get("_kind")!=kind:
   out.append(ev);continue
  pu=(prev.get("params") or {}).get("update") or {}
  cu=(ev.get("params") or {}).get("update") or {}
  pt=((pu.get("content") or {}).get("text") if isinstance(pu.get("content"),dict) else "") or ""
  ct=((cu.get("content") or {}).get("text") if isinstance(cu.get("content"),dict) else "") or ""
  if not isinstance(pu.get("content"),dict):pu["content"]={"type":"text","text":""}
  pu["content"]["text"]=pt+ct
  if "params" not in prev:prev["params"]={}
  prev["params"]["update"]=pu
 return out
def read_session_updates(session_dir:Path,limit=1600,max_bytes=8_000_000,since_bytes=0,live=False,before_bytes=None,chat_only=False):
 path=session_dir/"updates.jsonl"
 if not path.is_file():return [],{"path":str(path),"missing":True,"size":0,"has_more":False}
 size=path.stat().st_size
 since=int(since_bytes or 0)
 if since<0:since=0
 if since>size:since=0
 if live and since>=size:
  return [],{"path":str(path),"size":size,"returned":0,"scanned":0,"since":since,"live":True,"has_more":False,"end":size}
 end_pos=size
 window_start=0
 scored=[]
 msg_kinds={"user_message_chunk","agent_message_chunk"}
 chat_kinds=msg_kinds|{"agent_thought_chunk","plan","session_recap","turn_completed","task_completed"}
 try:
  with path.open("rb") as f:
   if live:
    if since>0:f.seek(since)
    else:
     f.seek(max(0,size-min(max_bytes,512_000)));f.readline()
    window_start=f.tell()
    raw=f.read()
    cut=raw.rfind(b"\n")+1
    if cut>0 and cut<len(raw):raw=raw[:cut]
    end_pos=window_start+len(raw)
    for line in raw.splitlines():
     if _CHAT_MARK_A not in line and _CHAT_MARK_B not in line and b"agent_thought_chunk" not in line and b"tool_call" not in line and b"turn_completed" not in line and b"task_completed" not in line and b"plan" not in line and b"session_recap" not in line:continue
     try:s=line.decode("utf-8","replace")
     except Exception:s=""
     ev=_parse_update_line(s,live=True)
     if ev:scored.append(ev)
    if len(scored)>limit:scored=scored[-limit:]
    return [_trim_chat_text(_strip_ev(ev)) for ev in scored],{"path":str(path),"size":size,"end":end_pos,"returned":len(scored),"scanned":len(scored),"since":since,"live":True,"has_more":False,"window_start":window_start}
   end_cap=size if before_bytes is None else min(max(0,int(before_bytes)),size)
   if end_cap<=0:return [],{"path":str(path),"size":size,"has_more":False,"window_start":0,"window_end":0,"returned":0,"live":False}
   if chat_only:
    want=max(1,int(limit))
    max_scan=min(64_000_000,max(16_000_000,int(max_bytes or 0)*16,want*800_000))
    scan=min(max_scan,max(1_200_000,want*80_000))
    collected=[]
    first_off=end_cap
    scanned_lines=0
    start=end_cap
    coalesced=[]
    acc=[]
    read_to=end_cap
    end_pos=end_cap
    window_start=end_cap
    while True:
     start=max(0,end_cap-scan)
     f.seek(start)
     if start>0:f.readline()
     window_start=f.tell()
     if window_start<read_to:
      blob=f.read(read_to-window_start)
      if read_to==end_cap:end_pos=window_start+len(blob)
      lines=blob.splitlines(keepends=True)
      scanned_lines+=len(lines)
      off=window_start+len(blob)
      for raw_line in reversed(lines):
       off-=len(raw_line)
       if _CHAT_MARK_A not in raw_line and _CHAT_MARK_B not in raw_line:continue
       s=raw_line.decode("utf-8","replace").rstrip("\r\n")
       if not s.strip():continue
       ev=_parse_update_line(s,live=False)
       if not ev or ev.get("_kind") not in msg_kinds:continue
       ev["_off"]=off
       acc.append(ev)
       if len(acc)>=want*4:break
      read_to=window_start
     groups=0;lastk=None
     for ev in reversed(acc):
      k=ev.get("_kind") or ""
      if k not in msg_kinds or lastk is None or lastk!=k:groups+=1
      lastk=k
     if groups>=want or start<=0 or scan>=max_scan or len(acc)>=want*4:break
     scan=min(max_scan,max(scan*2,scan+4_000_000))
    coalesced=_coalesce_chat(list(reversed(acc)))
    first_off=coalesced[0].get("_off",window_start) if coalesced else window_start
    collected=coalesced
    if len(collected)>want:collected=collected[-want:]
    first_off=collected[0].get("_off",first_off) if collected else first_off
    has_more=bool(first_off>0 and (start>0 or len(collected)>=want))
    return [_trim_chat_text(_strip_ev(ev)) for ev in collected],{"path":str(path),"size":size,"returned":len(collected),"scanned":scanned_lines,"live":False,"has_more":has_more,"window_start":int(first_off),"window_end":end_pos,"end":end_pos,"older_before":int(first_off),"chat_only":True}
   start=max(0,end_cap-max_bytes)
   f.seek(start)
   if start>0:f.readline()
   window_start=f.tell()
   blob=f.read(max(0,end_cap-window_start))
   end_pos=window_start+len(blob)
  lines=blob.splitlines(keepends=True)
  off=window_start
  for line in lines:
   line_start=off
   off+=len(line)
   if b"sessionUpdate" not in line and b"session_update" not in line:continue
   s=line.decode("utf-8","replace").rstrip("\r\n")
   if not s.strip():continue
   ev=_parse_update_line(s,live=False)
   if ev:
    ev["_off"]=line_start
    scored.append(ev)
 except Exception as e:
  return [],{"path":str(path),"error":str(e),"size":size,"has_more":False}
 if not scored:
  return [],{"path":str(path),"size":size,"returned":0,"scanned":0,"live":False,"has_more":window_start>0,"window_start":window_start,"window_end":end_pos,"end":end_pos}
 trimmed=len(scored)>limit
 if trimmed:
  chat_idx=[];tool_idx=[]
  for i,ev in enumerate(scored):
   (chat_idx if ev.get("_kind") in chat_kinds else tool_idx).append(i)
  chat_budget=max(limit*3//4,max(1,limit-20))
  keep=set(chat_idx[-chat_budget:])
  room=limit-len(keep)
  if room>0:keep.update(tool_idx[-room:])
  kept=[scored[i] for i in range(len(scored)) if i in keep]
 else:
  kept=scored
 first_off=kept[0].get("_off",window_start) if kept else window_start
 events=[_trim_chat_text(_strip_ev(ev)) for ev in kept]
 has_more=bool(window_start>0 or trimmed)
 return events,{"path":str(path),"size":size,"returned":len(events),"scanned":len(scored),"live":False,"has_more":has_more,"window_start":int(first_off),"window_end":end_pos,"end":end_pos,"older_before":int(first_off),"chat_only":bool(chat_only)}
def is_text_path(p:Path):
 if p.suffix.lower() in TEXT_EXT:return True
 if p.name.lower() in ("dockerfile","makefile","license","readme"):return True
 return p.suffix==""

def parse_frontmatter(text):
 meta={}; body=text
 if text.startswith("---"):
  parts=text.split("---",2)
  if len(parts)>=3:
   raw=parts[1]; body=parts[2].lstrip("\n")
   key=None; acc=[]
   def flush():
    nonlocal key,acc
    if key is not None:
     meta[key]=" ".join(acc).strip().strip('"').strip("'")
     key=None;acc=[]
   for line in raw.splitlines():
    if not line.strip():
     continue
    if (line.startswith(" ") or line.startswith("\t")) and key is not None:
     acc.append(line.strip());continue
    flush()
    if ":" in line:
     k,v=line.split(":",1);k=k.strip();v=v.strip()
     if v in ("|",">",">-","|-") or v=="":
      key=k;acc=[]
     else:
      meta[k]=v.strip('"').strip("'")
   flush()
 return meta,body
def skill_roots(cwd):
 home=Path.home()/".grok"
 roots=[]
 for r in [home/"skills",home/"bundled"/"skills",home/"plugins",home/"installed-plugins",home/"marketplace-cache"]:
  if r.is_dir():roots.append(r)
 if cwd:
  c=Path(cwd)
  for r in [c/".grok"/"skills",c/".agents"/"skills",c/"skills"]:
   if r.is_dir():roots.append(r)
 return roots
def scan_skills(cwd):
 seen=set();out=[]
 for root in skill_roots(cwd):
  try:files=list(root.rglob("SKILL.md"))
  except Exception:continue
  for f in files:
   try:
    if any(part in f.parts for part in ("node_modules",".git")):continue
    raw=f.read_text(encoding="utf-8",errors="replace")
    meta,body=parse_frontmatter(raw)
    name=(meta.get("name") or f.parent.name).strip()
    if not name or name.lower() in seen:continue
    seen.add(name.lower())
    desc=meta.get("description") or ""
    if len(desc)>240:desc=desc[:237]+"..."
    sp=str(f).replace("\\","/")
    src="user"
    if "/bundled/" in sp:src="bundled"
    elif "/marketplace-cache/" in sp:src="marketplace"
    elif "/plugins/" in sp or "/installed-plugins/" in sp:src="plugin"
    inv=str(meta.get("user-invocable","true")).lower() not in ("false","0","no")
    out.append({"name":name,"description":desc,"when":meta.get("when-to-use") or "","hint":meta.get("argument-hint") or "","source":src,"path":str(f),"kind":"skill","userInvocable":inv,"invoke":"/"+name})
   except Exception:continue
 home=Path.home()/".grok"
 cmd_roots=[]
 for r in [home/"plugins",home/"installed-plugins",home/"marketplace-cache"]:
  if r.is_dir():cmd_roots.append(r)
 if cwd:
  c=Path(cwd)
  for r in [c/".grok"/"commands",c/"commands"]:
   if r.is_dir():cmd_roots.append(r)
 for root in cmd_roots:
  try:files=list(root.rglob("*.md"))
  except Exception:continue
  for f in files:
   try:
    if "commands" not in f.parts:continue
    if f.name.lower() in ("readme.md","changelog.md","license.md"):continue
    if any(part in f.parts for part in ("node_modules",".git")):continue
    raw=f.read_text(encoding="utf-8",errors="replace")
    meta,body=parse_frontmatter(raw)
    name=(meta.get("name") or f.stem).strip().lstrip("/")
    if not name or name.lower() in seen:continue
    seen.add(name.lower())
    desc=meta.get("description") or ""
    if len(desc)>240:desc=desc[:237]+"..."
    out.append({"name":name,"description":desc,"when":"","hint":meta.get("argument-hint") or "","source":"command","path":str(f),"kind":"command","userInvocable":True,"invoke":"/"+name})
   except Exception:continue
 order={"bundled":0,"user":1,"plugin":2,"command":3,"marketplace":4,"agent":5}
 out.sort(key=lambda x:(order.get(x["source"],9),x["name"].lower()))
 return out

UI_KEY_COOKIE="grok_remote_key"
def make_auth_middleware(token:str):
 from aiohttp import web
 def _loopback(request):
  try:
   peer=request.remote or ""
  except Exception:peer=""
  if peer in ("127.0.0.1","::1","::ffff:127.0.0.1"):return True
  if str(peer).startswith("127."):return True
  # X-Forwarded-For is not trusted for bypass — only the TCP peer.
  return False
 @web.middleware
 async def auth_mw(request,handler):
  if not token:return await handler(request)
  if request.query.get("demo")=="1":return await handler(request)
  if request.path in ("/health","/health/deep"):return await handler(request)
  supplied=request.query.get("key") or request.cookies.get(UI_KEY_COOKIE) or request.headers.get("X-Grok-Remote-Key") or ""
  loop=_loopback(request)
  if not loop and supplied!=token:
   if request.path=="/ws":raise web.HTTPUnauthorized(text="unauthorized")
   acc=(request.headers.get("Accept") or "").lower()
   if "text/html" in acc and request.method=="GET":
    local="http://127.0.0.1:%s/?key=%s&auto=1"%(request.url.port or 2421,token)
    phone=("http://%s:%s/?key=%s&auto=1"%(lan_ip(),request.url.port or 2421,token))
    html=("<!doctype html><meta charset=utf-8><meta name=viewport content=\"width=device-width,initial-scale=1\">"
     "<title>Grok Remote — pair</title>"
     "<body style=\"font-family:system-ui;max-width:36rem;margin:2rem auto;padding:0 1rem;line-height:1.5;background:#0b0d10;color:#e8eaed\">"
     "<h1 style=\"font-size:1.25rem\">Pairing key required</h1>"
     "<p>Open the <b>paired link</b> (has <code>?key=…</code>). Same Wi‑Fi as the PC.</p>"
     "<p><a style=\"color:#7dd3fc\" href=\""+phone+"\">Open phone link</a></p>"
     "<p style=\"word-break:break-all;font-size:12px;opacity:.85\">"+phone+"</p>"
     "<p><a style=\"color:#a7f3d0\" href=\""+local+"\">Open on this PC (localhost)</a></p>"
     "</body>")
    return web.Response(text=html,status=401,content_type="text/html")
   return web.json_response({"error":"unauthorized · open the paired link from connect.url, or add ?key=<secret>"},status=401)
  resp=await handler(request)
  if request.path!="/ws" and (request.query.get("key")==token or (loop and token)):
   try:resp.set_cookie(UI_KEY_COOKIE,token,max_age=30*86400,httponly=True,samesite="Lax",path="/")
   except Exception:pass
  return resp
 return auth_mw
def under_root(path:Path,root:Path):
 try:
  path=path.resolve();root=root.resolve()
  return str(path).startswith(str(root)+os.sep) or path==root
 except Exception:return False
class HubTerminal:
 def __init__(self,tid,proc,limit=1_048_576):
  self.id=tid
  self.proc=proc
  self.limit=max(1024,int(limit or 1_048_576))
  self.buf=bytearray()
  self.truncated=False
  self.exit_code=None
  self.signal=None
  self._done=asyncio.Event()
  self._lock=asyncio.Lock()
  self._tasks=[]
 def start_readers(self):
  if self.proc.stdout:self._tasks.append(asyncio.create_task(self._pump(self.proc.stdout)))
  if self.proc.stderr:self._tasks.append(asyncio.create_task(self._pump(self.proc.stderr)))
  self._tasks.append(asyncio.create_task(self._wait_proc()))
 async def _pump(self,stream):
  try:
   while True:
    chunk=await stream.read(4096)
    if not chunk:break
    async with self._lock:
     self.buf.extend(chunk)
     if len(self.buf)>self.limit:
      overflow=len(self.buf)-self.limit
      del self.buf[:overflow]
      self.truncated=True
  except Exception:pass
 async def _wait_proc(self):
  try:
   code=await self.proc.wait()
   self.exit_code=code
  except Exception:
   self.exit_code=-1
  finally:
   self._done.set()
 async def output(self):
  async with self._lock:
   text=self.buf.decode("utf-8","replace")
   trunc=self.truncated
  st=None
  if self._done.is_set():
   st={"exitCode":self.exit_code,"signal":self.signal}
  return {"output":text,"truncated":trunc,"exitStatus":st}
 async def wait_exit(self):
  await self._done.wait()
  return {"exitCode":self.exit_code,"signal":self.signal}
 async def kill(self):
  if self.proc.returncode is None:
   try:self.proc.kill()
   except Exception:pass
   try:await asyncio.wait_for(self.proc.wait(),timeout=3)
   except Exception:pass
  self._done.set()
  return {}
 async def release(self):
  await self.kill()
  for t in self._tasks:
   t.cancel()
  return {}
class AgentHub:
 def __init__(self,agent_ws:str):
  self.agent_ws=agent_ws
  self.clients=set()
  self.pending={}
  self._nid=0
  self._agent=None
  self._session=None
  self._reader=None
  self._lock=asyncio.Lock()
  self._alive=False
  self._init_result=None
  self._init_error=None
  self._init_done=False
  self._last_err=""
  self._rpc_futs={}
  self._agent_req_ids=set()
  self._terms={}
  self._hub_rev_ids=set()
  self._term_n=0
  self._watch_task=None
 def _maybe_spawn_agent(self):
  port=getattr(self,"agent_port",2419)
  try:
   if listen_pids_port(int(port),exclude_self=False):return
  except Exception:pass
  fn=getattr(self,"spawn_agent",None)
  if not fn:return
  now=time.time()
  if now-getattr(self,"_last_agent_spawn",0)<30:return
  self._last_agent_spawn=now
  try:
   print("[hub] agent port dead — respawning grok agent serve",flush=True)
   fn()
  except Exception as e:print("[hub] agent respawn failed:",e,flush=True)
 def start_watch(self):
  if self._watch_task and not self._watch_task.done():return
  self._watch_task=asyncio.create_task(self._watch_loop())
 async def _notify_hub_state(self,up):
  """Clients used to look 'connected' while the agent behind the hub was gone - their
  pings are answered by the hub itself, so the link never went stale. Tell them."""
  msg=json.dumps({"jsonrpc":"2.0","method":"_x.ai/remote/hub","params":{"up":bool(up)}},separators=(",",":"))
  for c in list(self.clients):
   try:
    if not c.closed:await c.send_str(msg)
   except Exception:pass
 async def _watch_loop(self):
  hb=0.0
  while True:
   try:
    down=self._agent is None or self._agent.closed
    # a dead upstream with clients waiting is an outage, not a curiosity - hurry
    await asyncio.sleep(2 if (down and self.clients) else 10)
    # A BACKGROUND TAB CANNOT KEEP ITS OWN LINK ALIVE. Chrome throttles setInterval to about
    # once a minute in a hidden tab, so the client's 4s keepalive stops firing, its own
    # "silent > 45s" check trips, and it closes the socket it was trying to protect. Inbound
    # frames are NOT throttled, so liveness has to come from this side. The client already
    # refreshes linkLastRx on every message and already handles this method.
    if self.clients and time.time()-hb>=15:
     hb=time.time()
     await self._notify_hub_state(bool(self._agent and not self._agent.closed))
    if self.clients or self.pending or self._rpc_futs:
     ok=await self.ensure(retries=2,delay=0.25)
     if not ok:self._maybe_spawn_agent()
    elif self._agent is None or self._agent.closed:
     await self.ensure(retries=1,delay=0.15)
   except asyncio.CancelledError:return
   except Exception as e:
    print("[hub] watch:",e,flush=True)
 def _next_id(self):
  self._nid+=1
  return self._nid
 def _next_term_id(self):
  self._term_n+=1
  return "term-%d-%s"%(self._term_n,uuid.uuid4().hex[:8])
 async def call_rpc(self,method:str,params=None,timeout=90.0):
  if not await self.ensure():
   raise RuntimeError("agent offline · "+(self._last_err or "no hub"))
  nid=self._next_id()
  fut=asyncio.get_event_loop().create_future()
  self._rpc_futs[nid]=fut
  payload={"jsonrpc":"2.0","id":nid,"method":method,"params":params or {}}
  try:
   await self._agent.send_str(json.dumps(payload,separators=(",",":")))
  except Exception as e:
   self._rpc_futs.pop(nid,None)
   raise RuntimeError(str(e))
  try:
   return await asyncio.wait_for(fut,timeout=timeout)
  except Exception:
   self._rpc_futs.pop(nid,None)
   raise
 async def inject_prompt(self,session_id:str,text:str,timeout=300.0):
  sid=str(session_id or "").strip()
  t=str(text or "").strip()
  if not sid or not t:raise ValueError("sessionId and text required")
  return await self.call_rpc("session/prompt",{"sessionId":sid,"prompt":[{"type":"text","text":t}]},timeout=timeout)
 async def set_model_effort(self,session_id:str,model_id:str,effort:str):
  sid=str(session_id or "").strip()
  mid=str(model_id or "").strip() or "grok-4.5"
  eff=str(effort or "").strip().lower()
  if not sid:raise ValueError("sessionId required")
  if eff not in ("none","minimal","low","medium","high","xhigh","max"):
   raise ValueError("effort must be low|medium|high|xhigh (or none/minimal/max)")
  if eff=="max":eff="xhigh"
  return await self.call_rpc("session/set_model",{"sessionId":sid,"modelId":mid,"_meta":{"reasoningEffort":eff}},timeout=30.0)
 async def ensure(self,retries=3,delay=0.2):
  for i in range(max(1,retries)):
   async with self._lock:
    if self._agent is not None and not self._agent.closed:return True
    await self._open()
    if self._agent is not None and not self._agent.closed:return True
   if i+1<retries:await asyncio.sleep(delay)
  return False
 async def _open(self):
  from aiohttp import ClientSession,ClientTimeout
  await self._close_unlocked(keep_init=False)
  try:
   self._session=ClientSession(timeout=ClientTimeout(total=None,connect=8,sock_connect=8,sock_read=None))
   self._agent=await self._session.ws_connect(self.agent_ws,heartbeat=None,max_msg_size=16*1024*1024,autoping=False,receive_timeout=None)
   self._alive=True
   self._last_err=""
   self._reader=asyncio.create_task(self._pump())
   print("[hub] upstream agent connected · clients=%d"%len(self.clients),flush=True)
   asyncio.create_task(self._notify_hub_state(True))
  except Exception as e:
   self._last_err=re.sub(r"server-key=[^&'\s]+","server-key=***",str(e))[:200]
   print("[hub] upstream open failed:",e,flush=True)
   await self._close_unlocked(keep_init=False)
 async def _close_unlocked(self,keep_init=False):
  self._alive=False
  if self._reader and self._reader is not asyncio.current_task():
   self._reader.cancel()
   try:await self._reader
   except Exception:pass
   self._reader=None
  elif self._reader:
   self._reader=None
  if self._agent is not None:
   try:
    if not self._agent.closed:await self._agent.close()
   except Exception:pass
   self._agent=None
  if self._session is not None:
   try:await self._session.close()
   except Exception:pass
   self._session=None
  for tid,term in list(self._terms.items()):
   try:await term.release()
   except Exception:pass
  self._terms.clear()
  self._hub_rev_ids.clear()
  dead=list(self.pending.items())
  self.pending.clear()
  for nid,ent in dead:
   client=ent[0] if ent else None
   orig=ent[1] if ent and len(ent)>1 else None
   try:
    if client is not None and not client.closed and orig is not None:
     await client.send_str(json.dumps({"jsonrpc":"2.0","id":orig,"error":{"code":-32001,"message":"agent disconnected"}}))
   except Exception:pass
  dead_rpc=list(self._rpc_futs.items())
  self._rpc_futs.clear()
  for nid,fut in dead_rpc:
   if not fut.done():fut.set_exception(RuntimeError("agent disconnected"))
  if not keep_init:
   self._init_result=None
   self._init_error=None
   self._init_done=False
 async def close(self):
  async with self._lock:
   await self._close_unlocked(keep_init=False)
 async def _pump(self):
  from aiohttp import WSMsgType
  try:
   async for msg in self._agent:
    if msg.type==WSMsgType.TEXT:await self._from_agent(msg.data)
    elif msg.type==WSMsgType.BINARY:
     try:await self._from_agent(msg.data.decode("utf-8","replace"))
     except Exception:pass
    elif msg.type in (WSMsgType.CLOSE,WSMsgType.ERROR,WSMsgType.CLOSED):break
  except asyncio.CancelledError:return
  except Exception as e:print("[hub] pump error:",e,flush=True)
  finally:
   print("[hub] upstream closed · watcher retries every 2s while clients wait",flush=True)
   async with self._lock:
    await self._close_unlocked(keep_init=False)
   await self._notify_hub_state(False)
 async def _reply_agent(self,rid,result=None,error=None):
  if self._agent is None or self._agent.closed:return
  if rid is not None:self._hub_rev_ids.discard(rid)
  payload={"jsonrpc":"2.0","id":rid,"error":error} if error is not None else {"jsonrpc":"2.0","id":rid,"result":result}
  try:await self._agent.send_str(json.dumps(payload,separators=(",",":")))
  except Exception as e:print("[hub] reverse reply failed:",e,flush=True)
 async def _handle_reverse(self,obj):
  method=str(obj.get("method") or "")
  rid=obj.get("id")
  params=obj.get("params") if isinstance(obj.get("params"),dict) else {}
  if rid is not None:self._hub_rev_ids.add(rid)
  try:
   if method in ("fs/read_text_file","fs/readTextFile"):
    path=str(params.get("path") or "")
    if not path:raise ValueError("path required")
    p=Path(path)
    if not p.is_file():raise FileNotFoundError(path)
    raw=p.read_text(encoding="utf-8",errors="replace")
    lines=raw.splitlines(keepends=True)
    line=params.get("line")
    limit=params.get("limit")
    if line is not None:
     try:start=max(0,int(line)-1)
     except Exception:start=0
     lines=lines[start:]
    if limit is not None:
     try:lines=lines[:max(0,int(limit))]
     except Exception:pass
    content="".join(lines)
    if len(content)>MAX_READ:content=content[:MAX_READ]
    await self._reply_agent(rid,{"content":content})
    await self._broadcast(json.dumps({"jsonrpc":"2.0","method":"_x.ai/remote/client_rpc","params":{"method":method,"path":path,"ok":True}},separators=(",",":")))
    return True
   if method in ("fs/write_text_file","fs/writeTextFile"):
    path=str(params.get("path") or "")
    content=params.get("content")
    if content is None:content=""
    if not path:raise ValueError("path required")
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    text=str(content)
    if len(text.encode("utf-8",errors="replace"))>MAX_WRITE:raise ValueError("content too large")
    p.write_text(text,encoding="utf-8")
    await self._reply_agent(rid,{})
    await self._broadcast(json.dumps({"jsonrpc":"2.0","method":"_x.ai/remote/client_rpc","params":{"method":method,"path":path,"ok":True}},separators=(",",":")))
    return True
   if method=="terminal/create":
    cmd=str(params.get("command") or "")
    args=params.get("args") if isinstance(params.get("args"),list) else []
    cwd=params.get("cwd") or None
    env_list=params.get("env") if isinstance(params.get("env"),list) else []
    limit=params.get("outputByteLimit") or 1_048_576
    if not cmd:raise ValueError("command required")
    env=os.environ.copy()
    for e in env_list:
     if isinstance(e,dict) and e.get("name"):env[str(e["name"])]=str(e.get("value") or "")
    work=cwd if cwd and Path(str(cwd)).is_dir() else None
    creation=getattr(subprocess,"CREATE_NO_WINDOW",0) if sys.platform=="win32" else 0
    argv=[str(a) for a in args]
    if argv:
     proc=await asyncio.create_subprocess_exec(cmd,*argv,cwd=work,env=env,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,creationflags=creation)
    elif sys.platform=="win32":
     proc=await asyncio.create_subprocess_exec("powershell.exe","-NoProfile","-NonInteractive","-Command",cmd,cwd=work,env=env,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,creationflags=creation)
    else:
     proc=await asyncio.create_subprocess_shell(cmd,cwd=work,env=env,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    tid=self._next_term_id()
    term=HubTerminal(tid,proc,limit=limit)
    self._terms[tid]=term
    term.start_readers()
    await self._reply_agent(rid,{"terminalId":tid})
    await self._broadcast(json.dumps({"jsonrpc":"2.0","method":"_x.ai/remote/client_rpc","params":{"method":method,"terminalId":tid,"command":cmd,"ok":True}},separators=(",",":")))
    return True
   if method=="terminal/output":
    tid=str(params.get("terminalId") or "")
    term=self._terms.get(tid)
    if not term:raise KeyError("unknown terminal")
    await self._reply_agent(rid,await term.output())
    return True
   if method in ("terminal/wait_for_exit","terminal/waitForExit"):
    tid=str(params.get("terminalId") or "")
    term=self._terms.get(tid)
    if not term:raise KeyError("unknown terminal")
    await self._reply_agent(rid,await term.wait_exit())
    return True
   if method=="terminal/kill":
    tid=str(params.get("terminalId") or "")
    term=self._terms.get(tid)
    if not term:raise KeyError("unknown terminal")
    await self._reply_agent(rid,await term.kill())
    return True
   if method=="terminal/release":
    tid=str(params.get("terminalId") or "")
    term=self._terms.pop(tid,None)
    if term:await term.release()
    await self._reply_agent(rid,{})
    return True
   if method in ("session/request_permission","session/requestPermission") or "permission" in method or "ask_user" in method:
    opts=params.get("options") if isinstance(params.get("options"),list) else []
    allow="allow"
    for o in opts:
     if not isinstance(o,dict):continue
     oid=str(o.get("optionId") or o.get("id") or "")
     if re.search(r"allow|approve|yes|accept",oid,re.I):
      allow=oid;break
    if allow=="allow" and opts and isinstance(opts[0],dict):
     allow=str(opts[0].get("optionId") or opts[0].get("id") or "allow")
    await self._reply_agent(rid,{"outcome":{"outcome":"selected","optionId":allow}})
    await self._broadcast(json.dumps({"jsonrpc":"2.0","method":"_x.ai/remote/auto_permission","params":{"optionId":allow,"tool":(params.get("toolCall") or {}).get("title") if isinstance(params.get("toolCall"),dict) else None}},separators=(",",":")))
    return True
  except Exception as e:
   print("[hub] reverse %s failed: %s"%(method,e),flush=True)
   await self._reply_agent(rid,error={"code":-32000,"message":str(e)[:400]})
   return True
  return False
 async def _from_agent(self,raw:str):
  try:obj=json.loads(raw)
  except Exception:
   await self._broadcast(raw);return
  rid=obj.get("id",None)
  method=obj.get("method")
  is_resp=rid is not None and method is None
  if is_resp:
   fut=self._rpc_futs.pop(rid,None)
   if fut is not None and not fut.done():
    fut.set_result(obj)
    await self._broadcast(json.dumps({"jsonrpc":"2.0","method":"_x.ai/remote/rpc_done","params":{"id":rid,"ok":"error" not in obj}},separators=(",",":")))
    return
   ent=self.pending.pop(rid,None)
   if not ent:return
   client,orig,meta=ent if len(ent)==3 else (ent[0],ent[1],{})
   if meta.get("init"):
    if "result" in obj:
     self._init_result=obj.get("result")
     self._init_error=None
     self._init_done=True
    elif "error" in obj:
     # Cache SUCCESS only. A cached init error was served to every later client until the
     # upstream happened to cycle - one transient failure during agent boot poisoned the
     # hub for everyone. The requester still gets this error; the next initialize goes
     # upstream fresh.
     self._init_error=None
     self._init_result=None
     self._init_done=False
   obj["id"]=orig
   data=json.dumps(obj,separators=(",",":"))
   try:
    if client is not None and not client.closed:await client.send_str(data)
   except Exception:pass
   if meta.get("detached"):
    await self._broadcast(json.dumps({"jsonrpc":"2.0","method":"_x.ai/remote/rpc_done","params":{"id":orig,"ok":"error" not in obj,"detached":True}},separators=(",",":")))
   return
  if rid is not None and method:
   handled=await self._handle_reverse(obj)
   if handled:return
   self._agent_req_ids.add(rid)
  await self._broadcast(raw if isinstance(raw,str) else json.dumps(obj,separators=(",",":")))
 async def _broadcast(self,data:str):
  dead=[]
  for c in list(self.clients):
   try:
    if c.closed:dead.append(c);continue
    await c.send_str(data)
   except Exception:dead.append(c)
  for c in dead:
   self.clients.discard(c)
   self._detach_client_pending(c)
 def _detach_client_pending(self,client):
  for k,v in list(self.pending.items()):
   if not v or v[0] is not client:continue
   orig=v[1] if len(v)>1 else None
   meta=dict(v[2]) if len(v)>2 and isinstance(v[2],dict) else {}
   meta["detached"]=True
   self.pending[k]=(None,orig,meta)
  n=sum(1 for v in self.pending.values() if isinstance(v,tuple) and len(v)>2 and isinstance(v[2],dict) and v[2].get("detached"))
  if n:print("[hub] detached %d in-flight RPC(s) · turns keep running on PC"%n,flush=True)
 def _drop_client_pending(self,client):
  self._detach_client_pending(client)
 async def _reply_err(self,client,orig,msg,code=-32000):
  if orig is None:
   try:await client.send_str(json.dumps({"jsonrpc":"2.0","method":"error","params":{"message":msg}}))
   except Exception:pass
   return
  try:await client.send_str(json.dumps({"jsonrpc":"2.0","id":orig,"error":{"code":code,"message":msg}}))
  except Exception:pass
 async def handle_client(self,client):
  from aiohttp import WSMsgType
  self.clients.add(client)
  print("[hub] client join from remote · n=%d"%len(self.clients),flush=True)
  try:
   # A cold boot spawns the agent AFTER the web port is serving, so the first phone can
   # arrive up to ~18s before :2419 listens. Wait it out instead of failing the first
   # connection - the client is showing "connecting..." either way.
   up=await self.ensure(retries=24,delay=0.5)
   if not up:
    try:await client.send_str(json.dumps({"jsonrpc":"2.0","method":"error","params":{"message":"agent hub unavailable · start agent serve on :2419 · "+(self._last_err or "")}}))
    except Exception:pass
   async for msg in client:
    raw=None
    if msg.type==WSMsgType.TEXT:raw=msg.data
    elif msg.type==WSMsgType.BINARY:
     try:raw=msg.data.decode("utf-8","replace")
     except Exception:raw=None
    elif msg.type in (WSMsgType.CLOSE,WSMsgType.ERROR,WSMsgType.CLOSED):break
    if raw is None:continue
    try:peek=json.loads(raw)
    except Exception:peek=None
    if isinstance(peek,dict) and peek.get("method")=="_x.ai/remote/ping":
     params=peek.get("params") if isinstance(peek.get("params"),dict) else {}
     try:
      await client.send_str(json.dumps({"jsonrpc":"2.0","method":"_x.ai/remote/pong","params":{"t":params.get("t"),"s":time.time(),"clients":len(self.clients),"hub_up":bool(self._agent and not self._agent.closed)}},separators=(",",":")))
     except Exception:pass
     continue
    await self._to_agent(client,raw)
  except Exception as e:
   print("[hub] client error:",e,flush=True)
  finally:
   self.clients.discard(client)
   self._detach_client_pending(client)
   print("[hub] client leave · n=%d · in-flight turns stay on hub"%len(self.clients),flush=True)
 async def _to_agent(self,client,raw:str):
  try:obj=json.loads(raw)
  except Exception:
   if not await self.ensure():
    await self._reply_err(client,None,"agent offline")
    return
   try:await self._agent.send_str(raw)
   except Exception as e:await self._reply_err(client,None,str(e))
   return
  method=obj.get("method")
  orig=obj.get("id",None)
  if method=="_x.ai/remote/ping":
   params=obj.get("params") if isinstance(obj.get("params"),dict) else {}
   try:
    await client.send_str(json.dumps({"jsonrpc":"2.0","method":"_x.ai/remote/pong","params":{"t":params.get("t"),"s":time.time(),"clients":len(self.clients),"hub_up":bool(self._agent and not self._agent.closed)}},separators=(",",":")))
   except Exception:pass
   return
  if method=="initialize" and orig is not None and self._init_done and self._init_result is not None:
   try:await client.send_str(json.dumps({"jsonrpc":"2.0","id":orig,"result":self._init_result},separators=(",",":")))
   except Exception:pass
   return
  if method=="initialize" and orig is not None and self._init_done and self._init_error is not None:
   try:await client.send_str(json.dumps({"jsonrpc":"2.0","id":orig,"error":self._init_error},separators=(",",":")))
   except Exception:pass
   return
  # initialize is the one request worth waiting for: it is how every client starts, and
  # "agent offline" here is what made first connections fail while the agent was still
  # booting. Everything else keeps the fast path - a prompt against a dead agent should
  # error quickly, not hang.
  patient=method in ("initialize","session/load","session/new")
  if not await self.ensure(retries=(30 if patient else 3),delay=(0.5 if patient else 0.2)):
   await self._reply_err(client,orig,"agent offline · is serve on :2419? "+(self._last_err or ""),-32001)
   return
  if orig is not None and method:
   self._nid+=1
   nid=self._nid
   meta={"init":method=="initialize"}
   self.pending[nid]=(client,orig,meta)
   obj["id"]=nid
   try:await self._agent.send_str(json.dumps(obj,separators=(",",":")))
   except Exception as e:
    self.pending.pop(nid,None)
    await self._reply_err(client,orig,str(e))
   return
  if orig is not None and not method:
   if orig in self._hub_rev_ids:return
   if orig not in self._agent_req_ids:return
   self._agent_req_ids.discard(orig)
  try:await self._agent.send_str(json.dumps(obj,separators=(",",":")))
  except Exception as e:await self._reply_err(client,orig,str(e))
def parse_loop_interval(raw:str):
 s=str(raw or "").strip().lower().replace("every","").strip()
 if not s:return None
 m=re.fullmatch(r"(\d+)\s*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)?",s)
 if not m:return None
 n=int(m.group(1));u=(m.group(2) or "m")[0]
 sec=n if u=="s" else (n*60 if u=="m" else (n*3600 if u=="h" else n*86400))
 if sec<60:sec=60
 if sec>7*86400:sec=7*86400
 label=("%ds"%sec) if sec<3600 and sec%60 else (("%dm"%(sec//60)) if sec<86400 and sec%3600==0 else (("%dh"%(sec//3600)) if sec%86400==0 else ("%ds"%sec)))
 if sec>=86400 and sec%86400==0:label="%dd"%(sec//86400)
 elif sec>=3600 and sec%3600==0:label="%dh"%(sec//3600)
 elif sec%60==0:label="%dm"%(sec//60)
 else:label="%ds"%sec
 return sec,label
def parse_loop_command(text:str):
 t=str(text or "").strip()
 if not t.lower().startswith("/loop"):return None
 body=t[5:].strip()
 if not body:return {"action":"help"}
 low=body.lower()
 if low in ("stop","cancel","clear","off","list","status","ls"):return {"action":low if low!="ls" else "list"}
 if low.startswith("stop ") or low.startswith("cancel "):
  return {"action":"stop","id":body.split(None,1)[1].strip()}
 # /loop 5m prompt...  or /loop prompt every 5m
 m=re.match(r"^(\d+\s*(?:s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours|d|day|days)?)\s+(.+)$",body,re.I)
 if m:
  iv=parse_loop_interval(m.group(1))
  if iv:return {"action":"create","interval_sec":iv[0],"interval_label":iv[1],"prompt":m.group(2).strip()}
 m2=re.match(r"^(.+?)\s+every\s+(\d+\s*(?:s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours|d|day|days)?)\s*$",body,re.I)
 if m2:
  iv=parse_loop_interval(m2.group(2))
  if iv:return {"action":"create","interval_sec":iv[0],"interval_label":iv[1],"prompt":m2.group(1).strip()}
 return {"action":"create","interval_sec":300,"interval_label":"5m","prompt":body,"assumed":True}
class RemoteLoopManager:
 def __init__(self,hub:AgentHub,store:Path):
  self.hub=hub
  self.store=store
  self.jobs={}
  self._tasks={}
  self._load()
 def _load(self):
  try:
   if self.store.is_file():
    raw=json.loads(self.store.read_text(encoding="utf-8"))
    if isinstance(raw,dict) and isinstance(raw.get("jobs"),list):
     for j in raw["jobs"]:
      if isinstance(j,dict) and j.get("id") and j.get("sessionId") and j.get("prompt"):
       if not j.get("expires_at"):j["expires_at"]=float(j.get("created_at") or time.time())+7*86400
       self.jobs[j["id"]]=j
  except Exception as e:print("[loop] load failed:",e,flush=True)
 def _save(self):
  try:
   self.store.parent.mkdir(parents=True,exist_ok=True)
   self.store.write_text(json.dumps({"jobs":list(self.jobs.values())},indent=2),encoding="utf-8")
  except Exception as e:print("[loop] save failed:",e,flush=True)
 def list_jobs(self,session_id=None):
  items=list(self.jobs.values())
  if session_id:items=[j for j in items if str(j.get("sessionId"))==str(session_id)]
  return items
 def stop(self,job_id=None,session_id=None):
  removed=[]
  if job_id:
   j=self.jobs.pop(str(job_id),None)
   if j:removed.append(j)
   t=self._tasks.pop(str(job_id),None)
   if t:t.cancel()
  elif session_id:
   for jid,j in list(self.jobs.items()):
    if str(j.get("sessionId"))==str(session_id):
     self.jobs.pop(jid,None);removed.append(j)
     t=self._tasks.pop(jid,None)
     if t:t.cancel()
  self._save()
  return removed
 def create(self,session_id:str,prompt:str,interval_sec:int,interval_label:str,cwd:str=""):
  if len(self.jobs)>=50:raise RuntimeError("max 50 loops")
  jid="loop-"+uuid.uuid4().hex[:10]
  now=time.time()
  job={"id":jid,"sessionId":str(session_id),"prompt":str(prompt),"interval_sec":int(interval_sec),"interval_label":str(interval_label),"cwd":str(cwd or ""),"created_at":now,"fires":0,"last_fire":0,"last_error":"","expires_at":now+7*86400}
  self.jobs[jid]=job
  self._save()
  self._tasks[jid]=asyncio.create_task(self._run(jid))
  return job
 def start_all(self):
  for jid in list(self.jobs.keys()):
   if jid not in self._tasks or self._tasks[jid].done():
    self._tasks[jid]=asyncio.create_task(self._run(jid))
 async def _run(self,jid:str):
  try:
   while jid in self.jobs:
    job=self.jobs.get(jid)
    if not job:break
    if time.time()>float(job.get("expires_at") or 0):
     self.jobs.pop(jid,None);self._save();break
    try:
     note="[REMOTE LOOP · %s · fire %d]\n%s"%(job.get("interval_label") or "?",int(job.get("fires") or 0)+1,job.get("prompt") or "")
     await self.hub.inject_prompt(job["sessionId"],note,timeout=600.0)
     job["fires"]=int(job.get("fires") or 0)+1
     job["last_fire"]=time.time()
     job["last_error"]=""
     self._save()
     try:
      await self.hub._broadcast(json.dumps({"jsonrpc":"2.0","method":"_x.ai/remote/loop_fire","params":{"id":jid,"sessionId":job["sessionId"],"fires":job["fires"],"interval":job.get("interval_label")}},separators=(",",":")))
     except Exception:pass
    except Exception as e:
     job["last_error"]=str(e)[:200]
     self._save()
     print("[loop] fire failed",jid,e,flush=True)
    await asyncio.sleep(max(60,int(job.get("interval_sec") or 300)))
  except asyncio.CancelledError:
   return
  finally:
   self._tasks.pop(jid,None)
async def main_async(a):
 try:
  import aiohttp
  from aiohttp import web,WSMsgType,ClientSession,ClientTimeout
 except ImportError:
  subprocess.check_call([sys.executable,"-m","pip","install","aiohttp","-q"])
  import aiohttp
  from aiohttp import web,WSMsgType,ClientSession,ClientTimeout
 agent_host=a.agent_host or "127.0.0.1"
 agent_ws="ws://%s:%d/ws?server-key=%s"%(agent_host,a.agent_port,a.secret)
 lan=lan_ip()
 work_root=Path(a.cwd).expanduser().resolve()
 state={"cwd":str(work_root)}
 hub=AgentHub(agent_ws)
 hub.agent_port=a.agent_port
 loops=RemoteLoopManager(hub,LOOP_STORE)
 keyq=("?key=%s"%a.secret) if a.secret else ""
 cfg={"agent_host":agent_host,"agent_port":a.agent_port,"secret":"(held server-side)","cwd":state["cwd"],"ws_url":"ws://%s:%d/ws"%(lan,a.port),"ws_path":"/ws","ui":"http://%s:%d/%s"%(lan,a.port,keyq),"watch":"http://%s:%d/watch%s"%(lan,a.port,keyq),"lan_ip":lan,"proxy":True,"hub":True,"ide":True,"auth":bool(a.secret),"features":["fs","ide","review","multi-client-hub","skills-scan","git","project-context","stop-turn","todos","voice-tts","voice-go","xr-ar","watch-companion","msg-queue","remote-loop","effort"]}
 try:(ROOT/"runtime-config.json").write_text(json.dumps(cfg,indent=2),encoding="utf-8")
 except Exception:pass
 def root_path():
  return Path(state["cwd"]).expanduser().resolve()
 def safe_path(raw):
  root=root_path()
  if not raw or raw in (".","/"):return root
  p=Path(raw)
  if not p.is_absolute():p=root/p
  p=p.expanduser().resolve()
  if not under_root(p,root):raise web.HTTPForbidden(text="path outside workspace")
  return p
 async def index(_):
  return web.FileResponse(WEB/"index.html",headers={"Cache-Control":"no-store"})
 async def watch_page(_):
  p=WEB/"watch.html"
  if not p.is_file():raise web.HTTPNotFound()
  return web.FileResponse(p,headers={"Cache-Control":"no-store"})
 async def config(_):
  cfg["cwd"]=state["cwd"];cfg["clients"]=len(hub.clients)
  return web.json_response(cfg,headers={"Cache-Control":"no-store"})
 async def static(request):
  name=request.match_info.get("name","")
  name=unquote(str(name or "")).replace("\\","/").lstrip("/")
  if not name or ".." in name.split("/"):raise web.HTTPNotFound()
  p=(WEB/name).resolve()
  if not under_root(p,WEB) or not p.is_file():raise web.HTTPNotFound()
  ctype=mimetypes.guess_type(str(p))[0] or "application/octet-stream"
  if name.endswith(".webmanifest"):ctype="application/manifest+json"
  if name.endswith(".woff2"):ctype="font/woff2"
  elif name.endswith(".woff"):ctype="font/woff"
  return web.FileResponse(p,headers={"Content-Type":ctype,"Cache-Control":"public, max-age=86400"})
 def _peer_loopback(request):
  try:peer=request.remote or ""
  except Exception:peer=""
  return peer in ("127.0.0.1","::1","::ffff:127.0.0.1") or str(peer).startswith("127.")
 async def health(_):
  ag=listen_pids_port(a.agent_port,exclude_self=False)
  hub_up=hub._agent is not None and not getattr(hub._agent,"closed",True)
  return web.json_response({"ok":True,"ui":True,"ready":bool(hub_up and ag),"agent_ws_local":"ws://%s:%d/ws"%(agent_host,a.agent_port),"detail":"","cwd":state["cwd"],"hub_clients":len(hub.clients),"hub_up":hub_up,"hub_err":getattr(hub,"_last_err","") or "","init_cached":bool(getattr(hub,"_init_done",False)),"agent_listening":bool(ag)},headers={"Cache-Control":"no-store"})
 async def health_deep(_):
  ok=False;detail=""
  try:
   async with ClientSession(timeout=ClientTimeout(total=6,connect=3)) as s:
    async with s.ws_connect(agent_ws,heartbeat=None) as w:
     await w.send_str(json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1,"clientInfo":{"name":"health","version":"0"},"clientCapabilities":{}}}))
     msg=await asyncio.wait_for(w.receive(),timeout=5)
     ok=msg.type==WSMsgType.TEXT and "result" in json.loads(msg.data)
  except Exception as e:detail=re.sub(r"server-key=[^&'\s]+","server-key=***",str(e))[:200]
  hub_up=hub._agent is not None and not getattr(hub._agent,"closed",True)
  return web.json_response({"ok":ok,"agent_ws_local":"ws://%s:%d/ws"%(agent_host,a.agent_port),"detail":detail,"cwd":state["cwd"],"hub_clients":len(hub.clients),"hub_up":hub_up,"hub_err":getattr(hub,"_last_err","") or "","init_cached":bool(getattr(hub,"_init_done",False))},headers={"Cache-Control":"no-store"})
 async def pair(request):
  if not _peer_loopback(request):
   raise web.HTTPForbidden(text="pair is loopback-only")
  try:
   from pairing import addresses,page,ensure_segno
   pub=getattr(a,"public_host","") or os.environ.get("GROK_REMOTE_PUBLIC_HOST","")
   addrs=addresses(a.port,a.secret,public_host=pub)
   html=page(addrs,cwd=state.get("cwd") or "",have_qr=ensure_segno(),port=a.port)
  except Exception as e:
   html="<!doctype html><meta charset=utf-8><title>Pair</title><p>Pairing unavailable: %s</p>"%str(e)[:240]
  return web.Response(text=html,content_type="text/html",headers={"Cache-Control":"no-store"})
 async def fs_root(_):
  r=root_path()
  return web.json_response({"root":str(r),"exists":r.is_dir()})
 async def fs_set_root(request):
  try:body=await request.json()
  except Exception:body={}
  raw=(body.get("path") or body.get("cwd") or "").strip()
  if not raw:raise web.HTTPBadRequest(text="path required")
  p=Path(raw).expanduser().resolve()
  if not p.is_dir():raise web.HTTPBadRequest(text="not a directory")
  state["cwd"]=str(p);cfg["cwd"]=state["cwd"]
  return web.json_response({"ok":True,"root":state["cwd"]})
 async def fs_list(request):
  rel=request.rel_url.query.get("path") or "."
  p=safe_path(rel)
  if not p.is_dir():raise web.HTTPBadRequest(text="not a directory")
  dirs=[];files=[]
  try:entries=sorted(p.iterdir(),key=lambda x:(not x.is_dir(),x.name.lower()))
  except PermissionError:raise web.HTTPForbidden(text="permission denied")
  for e in entries:
   if e.name.startswith(".") and e.name not in (".env",".gitignore"):continue
   if e.is_dir() and e.name in SKIP_DIR:continue
   try:
    st=e.stat()
    item={"name":e.name,"path":str(e),"rel":str(e.relative_to(root_path())).replace("\\","/"),"mtime":int(st.st_mtime)}
    if e.is_dir():dirs.append(item)
    else:item["size"]=st.st_size;item["text"]=is_text_path(e);files.append(item)
   except OSError:continue
  parent=None
  root=root_path()
  if p!=root:
   try:parent=str(p.parent.relative_to(root)).replace("\\","/") if p.parent!=root else "."
   except Exception:parent="."
  return web.json_response({"path":str(p),"rel":"." if p==root else str(p.relative_to(root)).replace("\\","/"),"parent":parent,"dirs":dirs,"files":files,"root":str(root)})
 async def fs_read(request):
  rel=request.rel_url.query.get("path") or ""
  if not rel:raise web.HTTPBadRequest(text="path required")
  p=safe_path(rel)
  if not p.is_file():raise web.HTTPNotFound(text="not a file")
  size=p.stat().st_size
  if size>MAX_READ:raise web.HTTPRequestEntityTooLarge(text="file too large")
  if not is_text_path(p):
   return web.json_response({"path":str(p),"binary":True,"size":size,"text":False})
  data=p.read_bytes()
  try:text=data.decode("utf-8-sig")
  except UnicodeDecodeError:text=data.decode("latin-1",errors="replace")
  return web.json_response({"path":str(p),"rel":str(p.relative_to(root_path())).replace("\\","/"),"text":True,"content":text,"size":size,"name":p.name})
 async def fs_write(request):
  try:body=await request.json()
  except Exception:raise web.HTTPBadRequest(text="json required")
  rel=(body.get("path") or "").strip()
  content=body.get("content")
  if not rel or content is None:raise web.HTTPBadRequest(text="path and content required")
  if not isinstance(content,str):raise web.HTTPBadRequest(text="content must be string")
  if len(content.encode("utf-8"))>MAX_WRITE:raise web.HTTPRequestEntityTooLarge(text="content too large")
  p=safe_path(rel)
  if p.exists() and p.is_dir():raise web.HTTPBadRequest(text="path is directory")
  p.parent.mkdir(parents=True,exist_ok=True)
  p.write_text(content,encoding="utf-8",newline="\n")
  return web.json_response({"ok":True,"path":str(p),"rel":str(p.relative_to(root_path())).replace("\\","/"),"size":p.stat().st_size})
 async def fs_mkdir(request):
  try:body=await request.json()
  except Exception:raise web.HTTPBadRequest(text="json required")
  rel=(body.get("path") or "").strip()
  if not rel:raise web.HTTPBadRequest(text="path required")
  p=safe_path(rel)
  p.mkdir(parents=True,exist_ok=True)
  return web.json_response({"ok":True,"path":str(p)})

 async def skills_list(request):
  cwd=request.rel_url.query.get("cwd") or state["cwd"]
  items=scan_skills(cwd)
  return web.json_response({"ok":True,"cwd":cwd,"count":len(items),"skills":items},headers={"Cache-Control":"no-store"})
 async def session_history(request):
  sid=(request.rel_url.query.get("sessionId") or request.rel_url.query.get("id") or "").strip()
  cwd=(request.rel_url.query.get("cwd") or state["cwd"] or "").strip()
  live=str(request.rel_url.query.get("live") or "").lower() in ("1","true","yes")
  try:limit=min(4000,max(20,int(request.rel_url.query.get("limit") or ("400" if live else "100"))))
  except Exception:limit=400 if live else 100
  try:since_bytes=int(request.rel_url.query.get("since") or request.rel_url.query.get("since_bytes") or "0")
  except Exception:since_bytes=0
  before_raw=request.rel_url.query.get("before") or request.rel_url.query.get("before_bytes")
  before_bytes=None
  if before_raw not in (None,""):
   try:before_bytes=int(before_raw)
   except Exception:before_bytes=None
  try:max_bytes=min(12_000_000,max(64_000,int(request.rel_url.query.get("max_bytes") or ("512000" if live else ("1200000" if before_bytes is not None else "400000")))))
  except Exception:max_bytes=512000 if live else 400000
  chat_only=str(request.rel_url.query.get("chat_only") or request.rel_url.query.get("messages") or "").lower() in ("1","true","yes")
  if not sid:raise web.HTTPBadRequest(text="sessionId required")
  sdir=find_session_dir(sid,cwd or None)
  if not sdir:
   return web.json_response({"ok":False,"error":"session dir not found","sessionId":sid,"cwd":cwd,"events":[],"meta":{"has_more":False}},status=404,headers={"Cache-Control":"no-store"})
  events,meta=await asyncio.get_event_loop().run_in_executor(None,lambda:read_session_updates(sdir,limit=limit,max_bytes=max_bytes,since_bytes=since_bytes,live=live,before_bytes=before_bytes,chat_only=chat_only))
  info=read_session_info(sdir)
  title=info.get("title") or ""
  meta=dict(meta or {})
  meta["resolvedSid"]=sid
  meta["resolvedDir"]=str(sdir)
  if info.get("cwd"):meta["resolvedCwd"]=info.get("cwd")
  return web.json_response({"ok":True,"sessionId":sid,"cwd":cwd,"title":title,"dir":str(sdir),"events":events,"meta":meta,"count":len(events)},headers={"Cache-Control":"no-store"})
 async def session_titles(request):
  body={}
  try:body=await request.json()
  except Exception:pass
  ids=body.get("ids") or body.get("sessionIds") or []
  if isinstance(ids,str):ids=[ids]
  cwd=str(body.get("cwd") or state["cwd"] or "")
  def _titles():
   out={}
   for raw in list(ids)[:250]:
    sid=str(raw or "").strip()
    if not sid or sid in out:continue
    sdir=find_session_dir(sid,cwd or None)
    if not sdir:sdir=find_session_dir(sid,None)
    if not sdir:continue
    info=read_session_info(sdir)
    mtime=0
    try:
     up=sdir/"updates.jsonl"
     if up.is_file():mtime=int(up.stat().st_mtime*1000)
     else:
      sm=sdir/"summary.json"
      if sm.is_file():mtime=int(sm.stat().st_mtime*1000)
    except Exception:pass
    if info.get("title") or info.get("cwd") or mtime:
     out[sid]={"title":info.get("title") or "","cwd":info.get("cwd") or "","dir":str(sdir),"mtime":mtime,"updatedAt":mtime}
   return out
  out=await asyncio.get_event_loop().run_in_executor(None,_titles)
  return web.json_response({"ok":True,"titles":out,"count":len(out)},headers={"Cache-Control":"no-store"})
 async def session_signals(request):
  sid=(request.rel_url.query.get("sessionId") or request.rel_url.query.get("id") or "").strip()
  cwd=(request.rel_url.query.get("cwd") or state["cwd"] or "").strip()
  if not sid:raise web.HTTPBadRequest(text="sessionId required")
  sdir=find_session_dir(sid,cwd or None)
  if not sdir:
   return web.json_response({"ok":False,"error":"session dir not found","sessionId":sid},status=404,headers={"Cache-Control":"no-store"})
  sig={}
  try:
   p=sdir/"signals.json"
   if p.is_file():sig=json.loads(p.read_text(encoding="utf-8",errors="replace")) or {}
  except Exception as e:
   return web.json_response({"ok":False,"error":str(e),"sessionId":sid},status=500,headers={"Cache-Control":"no-store"})
  used=sig.get("contextTokensUsed")
  if used is None:used=sig.get("context_tokens_used")
  win=sig.get("contextWindowTokens")
  if win is None:win=sig.get("context_window_tokens")
  usage=sig.get("contextWindowUsage")
  if usage is None and used is not None and win:
   try:usage=round(100.0*float(used)/float(win),1)
   except Exception:usage=None
  return web.json_response({
   "ok":True,"sessionId":sid,"dir":str(sdir),
   "contextTokensUsed":used,"contextWindowTokens":win,"contextWindowUsage":usage,
   "turnCount":sig.get("turnCount"),"toolCallCount":sig.get("toolCallCount"),
   "primaryModelId":sig.get("primaryModelId") or sig.get("primary_model_id"),
   "signals":sig
  },headers={"Cache-Control":"no-store"})
 async def room_feed(request):
  if room_store is None:return web.json_response({"ok":False,"error":"room module unavailable"},status=503)
  since=request.query.get("since") or 0
  limit=request.query.get("limit") or 200
  msgs=room_store.feed(since,limit)
  last=int(msgs[-1]["id"]) if msgs else int(since or 0)
  return web.json_response({"ok":True,"messages":msgs,"last":last,"limit":room_store.LIMIT},
   headers={"Cache-Control":"no-store"})
 async def room_say(request):
  if room_store is None:return web.json_response({"ok":False,"error":"room module unavailable"},status=503)
  try:body=await request.json()
  except Exception:body={}
  who=body.get("who") or request.query.get("who") or "agent"
  text=body.get("text") or request.query.get("text") or ""
  out=room_store.say(who,text,body.get("kind") or "say")
  return web.json_response(out,status=200 if out.get("ok") else 400,headers={"Cache-Control":"no-store"})
 async def room_members(_):
  if room_store is None:return web.json_response({"ok":False,"error":"room module unavailable"},status=503)
  return web.json_response({"ok":True,"members":room_store.members()},headers={"Cache-Control":"no-store"})
 async def room_clear(_):
  if room_store is None:return web.json_response({"ok":False,"error":"room module unavailable"},status=503)
  return web.json_response(room_store.clear())
 async def session_archived_get(_):
  ids=load_archived_ids()
  return web.json_response({"ok":True,"ids":ids,"count":len(ids),"path":str(archive_store_path())},headers={"Cache-Control":"no-store"})
 async def session_archived_set(request):
  try:body=await request.json()
  except Exception:body={}
  ids=load_archived_ids()
  if "ids" in body and isinstance(body.get("ids"),list):
   ids=save_archived_ids(body.get("ids"))
  elif body.get("id") or body.get("sessionId"):
   sid=str(body.get("id") or body.get("sessionId") or "").strip()
   if not sid:raise web.HTTPBadRequest(text="id required")
   want=body.get("archived")
   if want is None:want=sid not in ids
   else:want=bool(want)
   s=set(ids)
   if want:s.add(sid)
   else:s.discard(sid)
   ids=save_archived_ids(sorted(s))
  else:
   raise web.HTTPBadRequest(text="ids[] or id required")
  return web.json_response({"ok":True,"ids":ids,"count":len(ids)},headers={"Cache-Control":"no-store"})
 async def session_rename(request):
  try:body=await request.json()
  except Exception:raise web.HTTPBadRequest(text="json required")
  sid=str(body.get("sessionId") or body.get("id") or "").strip()
  title=str(body.get("title") or body.get("name") or "").strip()
  cwd=str(body.get("cwd") or state.get("cwd") or "").strip()
  if not sid:raise web.HTTPBadRequest(text="sessionId required")
  if not title:raise web.HTTPBadRequest(text="title required")
  if len(title)>160:title=title[:160].rstrip()
  sdir=find_session_dir(sid,cwd or None)
  if not sdir:
   return web.json_response({"ok":False,"error":"session dir not found","sessionId":sid},status=404,headers={"Cache-Control":"no-store"})
  summ_path=sdir/"summary.json"
  summ={}
  try:
   if summ_path.is_file():
    summ=json.loads(summ_path.read_text(encoding="utf-8",errors="replace")) or {}
    if not isinstance(summ,dict):summ={}
  except Exception:summ={}
  prev=str(summ.get("remote_title") or summ.get("generated_title") or summ.get("session_summary") or "")
  summ["remote_title"]=title
  summ["generated_title"]=title
  summ["session_summary"]=title
  try:
   from datetime import datetime,timezone
   summ["updated_at"]=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
  except Exception:pass
  try:
   summ_path.write_text(json.dumps(summ,ensure_ascii=False,indent=2),encoding="utf-8")
  except Exception as e:
   return web.json_response({"ok":False,"error":str(e),"sessionId":sid},status=500,headers={"Cache-Control":"no-store"})
  return web.json_response({"ok":True,"sessionId":sid,"title":title,"previous":prev,"dir":str(sdir)},headers={"Cache-Control":"no-store"})
 async def voice_status(_):
  key=xai_api_key()
  return web.json_response({"ok":True,"tts":bool(key),"stt":"browser","provider":"xai" if key else "browser-fallback","voices":["eve","ara","leo","rex","sal","luna","orion","helix"],"hint":None if key else "Set XAI_API_KEY for real Grok voice (else browser speechSynthesis)"},headers={"Cache-Control":"no-store"})
 async def tts_proxy(request):
  key=xai_api_key()
  if not key:return web.json_response({"ok":False,"error":"XAI_API_KEY not set — browser fallback only"},status=503)
  try:body=await request.json()
  except Exception:body={}
  text=str(body.get("text") or body.get("input") or "").strip()
  if not text:raise web.HTTPBadRequest(text="text required")
  if len(text)>15000:text=text[:14990]+"…"
  voice_id=str(body.get("voice_id") or body.get("voice") or "eve").strip() or "eve"
  language=str(body.get("language") or "en").strip() or "en"
  speed=body.get("speed")
  payload={"text":text,"voice_id":voice_id,"language":language,"output_format":{"codec":"mp3","sample_rate":24000,"bit_rate":128000},"text_normalization":True}
  if speed is not None:
   try:payload["speed"]=max(0.7,min(1.5,float(speed)))
   except Exception:pass
  try:
   timeout=ClientTimeout(total=60,connect=10,sock_connect=10,sock_read=50)
   async with ClientSession(timeout=timeout) as sess:
    async with sess.post("https://api.x.ai/v1/tts",headers={"Authorization":"Bearer "+key,"Content-Type":"application/json","Accept":"audio/mpeg"},json=payload) as resp:
     data=await resp.read()
     if resp.status!=200:
      err=data.decode("utf-8","replace")[:400]
      return web.json_response({"ok":False,"error":err or ("HTTP "+str(resp.status)),"status":resp.status},status=502 if resp.status>=500 else 400)
     return web.Response(body=data,headers={"Content-Type":resp.headers.get("Content-Type","audio/mpeg"),"Cache-Control":"no-store","X-Voice-Id":voice_id})
  except Exception as e:
   return web.json_response({"ok":False,"error":str(e)[:300]},status=502)
 def run_git(args,cwd,timeout=12):
  git=shutil.which("git")
  if not git:return None,"git not found"
  try:
   p=subprocess.run([git,*args],cwd=str(cwd),capture_output=True,text=True,timeout=timeout,encoding="utf-8",errors="replace")
   return p,None
  except Exception as e:return None,str(e)
 async def git_status(request):
  root=root_path()
  p,err=run_git(["rev-parse","--is-inside-work-tree"],root)
  if err:return web.json_response({"ok":False,"error":err,"git":False})
  if not p or p.returncode!=0:return web.json_response({"ok":True,"git":False,"root":str(root)})
  branch_p,_=run_git(["rev-parse","--abbrev-ref","HEAD"],root)
  branch=(branch_p.stdout.strip() if branch_p and branch_p.returncode==0 else "?")
  short_p,_=run_git(["rev-parse","--short","HEAD"],root)
  sha=(short_p.stdout.strip() if short_p and short_p.returncode==0 else "")
  st_p,_=run_git(["status","--porcelain","-b"],root)
  lines=(st_p.stdout.splitlines() if st_p else [])
  head=lines[0] if lines else ""
  files=[ln for ln in lines[1:] if ln.strip()]
  ahead=behind=0
  import re as _re
  m=_re.search(r"ahead\s+(\d+)",head);ahead=int(m.group(1)) if m else 0
  m=_re.search(r"behind\s+(\d+)",head);behind=int(m.group(1)) if m else 0
  dirty=[{"code":f[:2],"path":f[3:].strip()} for f in files[:80]]
  return web.json_response({"ok":True,"git":True,"root":str(root),"branch":branch,"sha":sha,"ahead":ahead,"behind":behind,"dirty":len(files),"files":dirty,"head":head},headers={"Cache-Control":"no-store"})
 async def git_diff(request):
  root=root_path()
  path=request.rel_url.query.get("path") or ""
  staged=request.rel_url.query.get("staged") in ("1","true","yes")
  args=["diff","--no-color"]
  if staged:args.append("--cached")
  if path:args+=["--",path]
  p,err=run_git(args,root,timeout=20)
  if err:return web.json_response({"ok":False,"error":err})
  text=(p.stdout if p else "")[:200000]
  return web.json_response({"ok":True,"path":path,"staged":staged,"diff":text,"code":p.returncode if p else -1},headers={"Cache-Control":"no-store"})
 async def git_log(request):
  root=root_path()
  n=min(30,max(1,int(request.rel_url.query.get("n") or 12)))
  p,err=run_git(["log","-"+str(n),"--pretty=format:%h%x09%ad%x09%s","--date=short"],root)
  if err:return web.json_response({"ok":False,"error":err,"commits":[]})
  commits=[]
  for ln in (p.stdout.splitlines() if p else []):
   parts=ln.split("\t",2)
   if len(parts)>=3:commits.append({"hash":parts[0],"date":parts[1],"subject":parts[2]})
  return web.json_response({"ok":True,"commits":commits},headers={"Cache-Control":"no-store"})
 async def project_context(request):
  root=root_path()
  names=["AGENTS.md","CLAUDE.md","Claude.md",".cursorrules","README.md","package.json","pyproject.toml","Cargo.toml","go.mod"]
  found=[]
  for n in names:
   p=root/n
   if p.is_file():
    try:
     text=p.read_text(encoding="utf-8",errors="replace")
     found.append({"name":n,"rel":n,"size":len(text),"preview":text[:4000]})
    except Exception:pass
  git_p,_=run_git(["rev-parse","--abbrev-ref","HEAD"],root)
  branch=git_p.stdout.strip() if git_p and git_p.returncode==0 else None
  return web.json_response({"ok":True,"root":str(root),"branch":branch,"files":found},headers={"Cache-Control":"no-store"})
 def listen_pids(port:int):
  return listen_pids_port(port,exclude_self=True)
 def kill_pids(pids):
  return kill_pids_list(pids)
 async def stack_status(request):
  ui=listen_pids(a.port);ag=listen_pids(a.agent_port)
  hub_up=hub._agent is not None and not getattr(hub._agent,"closed",True)
  return web.json_response({"ok":True,"ui_port":a.port,"agent_port":a.agent_port,"ui_pids":ui,"agent_pids":ag,"self_pid":os.getpid(),"lan":lan,"cwd":state["cwd"],"hub_up":hub_up,"hub_err":getattr(hub,"_last_err","") or "","agent_listening":bool(ag)},headers={"Cache-Control":"no-store"})
 async def stack_stop(request):
  keep_agent=False
  try:
   body=await request.json()
   keep_agent=bool(body.get("keep_agent"))
  except Exception:pass
  agent_pids=[] if keep_agent else listen_pids(a.agent_port)
  self_pid=os.getpid()
  async def _shutdown():
   await asyncio.sleep(0.35)
   try:await hub.close()
   except Exception:pass
   if agent_pids:kill_pids(agent_pids)
   await asyncio.sleep(0.15)
   try:os._exit(0)
   except Exception:
    try:sys.exit(0)
    except Exception:pass
  asyncio.create_task(_shutdown())
  return web.json_response({"ok":True,"stopping":True,"self_pid":self_pid,"agent_pids":agent_pids,"message":"Remote UI stopping; agent serve will stop unless keep_agent"})
 async def stack_start(request):
  body={}
  try:body=await request.json()
  except Exception:pass
  force=bool(body.get("force") or body.get("restart"))
  cwd=str(body.get("cwd") or state["cwd"] or a.cwd)
  agent_up=bool(listen_pids_port(a.agent_port,exclude_self=False))
  killed=[];started=False;msg="";attempts=[]
  async def spawn_agent(reason):
   nonlocal killed,started,msg
   hard=reason in ("force","hub-auth-retry")
   if hard:
    killed=claim_port(a.agent_port,"agent")
    try:await hub.close()
    except Exception:pass
    await asyncio.sleep(0.25)
   start_agent_process(a.secret,a.agent_port,cwd,force=hard)
   started=True
   ok_listen=await asyncio.get_event_loop().run_in_executor(None,lambda:wait_port(a.agent_port,24))
   attempts.append({"reason":reason,"listen":ok_listen,"killed":killed})
   if not ok_listen:
    raise RuntimeError("agent did not bind :%d after %s"%(a.agent_port,reason))
   msg="agent started on :%d (%s)"%(a.agent_port,reason)
  try:
   if force or not agent_up:
    await spawn_agent("force" if force else "missing")
   up=await hub.ensure(retries=8,delay=0.35)
   if not up:
    await spawn_agent("hub-auth-retry")
    up=await hub.ensure(retries=10,delay=0.4)
   if not up:
    err=getattr(hub,"_last_err","") or "hub could not open agent websocket"
    return web.json_response({"ok":False,"error":err,"message":msg,"killed":killed,"started":started,"attempts":attempts,"agent_pids":listen_pids_port(a.agent_port,exclude_self=False),"hub_up":False,"hub_err":err,"hint":"Secret mismatch is usually fixed by force-restart (already attempted). Check logs/agent.log"},status=503)
   return web.json_response({"ok":True,"message":msg or "agent ready","killed":killed,"started":started,"attempts":attempts,"agent_pids":listen_pids_port(a.agent_port,exclude_self=False),"hub_up":True,"hub_err":""})
  except Exception as e:
   return web.json_response({"ok":False,"error":str(e),"killed":killed,"started":started,"attempts":attempts,"hub_err":getattr(hub,"_last_err","") or ""},status=500)
 async def stack_shortcut(request):
  script=ROOT/"scripts"/"install-shortcut.ps1"
  if not script.is_file():
   return web.json_response({"ok":False,"error":"install-shortcut.ps1 missing"},status=404)
  try:
   p=subprocess.run(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",str(script)],capture_output=True,text=True,timeout=30,encoding="utf-8",errors="replace")
   return web.json_response({"ok":p.returncode==0,"code":p.returncode,"out":(p.stdout or "")[-2000:],"err":(p.stderr or "")[-1000:]})
  except Exception as e:
   return web.json_response({"ok":False,"error":str(e)},status=500)
 async def ws_proxy(request):
  client=web.WebSocketResponse(heartbeat=12,max_msg_size=16*1024*1024,autoping=True)
  await client.prepare(request)
  await hub.handle_client(client)
  return client
 app=web.Application(client_max_size=8*1024*1024,middlewares=[make_auth_middleware(a.secret)])
 app.router.add_get("/",index)
 app.router.add_get("/index.html",index)
 app.router.add_get("/watch",watch_page)
 app.router.add_get("/watch.html",watch_page)
 app.router.add_get("/config.json",config)
 app.router.add_get("/config",config)
 app.router.add_get("/health",health)
 app.router.add_get("/health/deep",health_deep)
 app.router.add_get("/pair",pair)
 app.router.add_get("/ws",ws_proxy)
 app.router.add_get("/static/{name:.*}",static)
 app.router.add_get("/api/fs/root",fs_root)
 app.router.add_post("/api/fs/root",fs_set_root)
 app.router.add_get("/api/fs/list",fs_list)
 app.router.add_get("/api/fs/read",fs_read)
 app.router.add_post("/api/fs/write",fs_write)
 app.router.add_post("/api/fs/mkdir",fs_mkdir)
 app.router.add_get("/api/skills/list",skills_list)
 app.router.add_get("/api/session/history",session_history)
 app.router.add_post("/api/session/titles",session_titles)
 app.router.add_get("/api/session/signals",session_signals)
 app.router.add_get("/api/room/feed",room_feed)
 app.router.add_post("/api/room/say",room_say)
 app.router.add_get("/api/room/members",room_members)
 app.router.add_post("/api/room/clear",room_clear)
 app.router.add_get("/api/session/archived",session_archived_get)
 app.router.add_post("/api/session/archived",session_archived_set)
 app.router.add_post("/api/session/rename",session_rename)
 app.router.add_get("/api/voice/status",voice_status)
 app.router.add_post("/api/tts",tts_proxy)
 app.router.add_get("/api/git/status",git_status)
 app.router.add_get("/api/git/diff",git_diff)
 app.router.add_get("/api/git/log",git_log)
 app.router.add_get("/api/project/context",project_context)
 app.router.add_get("/api/stack/status",stack_status)
 app.router.add_post("/api/stack/stop",stack_stop)
 app.router.add_post("/api/stack/start",stack_start)
 app.router.add_post("/api/stack/shortcut",stack_shortcut)
 async def loops_list(request):
  sid=(request.rel_url.query.get("sessionId") or "").strip() or None
  return web.json_response({"ok":True,"jobs":loops.list_jobs(sid)},headers={"Cache-Control":"no-store"})
 async def loops_create(request):
  try:body=await request.json()
  except Exception:raise web.HTTPBadRequest(text="json required")
  sid=str(body.get("sessionId") or "").strip()
  prompt=str(body.get("prompt") or "").strip()
  interval=body.get("interval") or body.get("interval_sec") or body.get("every")
  if not sid or not prompt:raise web.HTTPBadRequest(text="sessionId and prompt required")
  if isinstance(interval,(int,float)):
   sec=max(60,min(7*86400,int(interval)))
   lab=("%dm"%(sec//60)) if sec%60==0 else ("%ds"%sec)
   if sec>=3600 and sec%3600==0:lab="%dh"%(sec//3600)
  else:
   iv=parse_loop_interval(str(interval or "5m"))
   if not iv:raise web.HTTPBadRequest(text="bad interval")
   sec,lab=iv
  try:
   job=loops.create(sid,prompt,sec,lab,cwd=str(body.get("cwd") or state.get("cwd") or ""))
  except Exception as e:
   return web.json_response({"ok":False,"error":str(e)},status=400)
  return web.json_response({"ok":True,"job":job})
 async def loops_stop(request):
  try:body=await request.json()
  except Exception:body={}
  jid=str((body or {}).get("id") or request.rel_url.query.get("id") or "").strip()
  sid=str((body or {}).get("sessionId") or request.rel_url.query.get("sessionId") or "").strip()
  removed=loops.stop(job_id=jid or None,session_id=sid or None)
  return web.json_response({"ok":True,"removed":removed,"count":len(removed)})
 async def effort_set(request):
  try:body=await request.json()
  except Exception:raise web.HTTPBadRequest(text="json required")
  sid=str(body.get("sessionId") or "").strip()
  effort=str(body.get("effort") or body.get("reasoningEffort") or "").strip().lower()
  model=str(body.get("modelId") or body.get("model") or "grok-4.5").strip()
  if not sid or not effort:raise web.HTTPBadRequest(text="sessionId and effort required")
  try:
   res=await hub.set_model_effort(sid,model,effort)
  except Exception as e:
   return web.json_response({"ok":False,"error":str(e)},status=500)
  if res and res.get("error"):
   return web.json_response({"ok":False,"error":res.get("error"),"raw":res},status=400)
  return web.json_response({"ok":True,"effort":effort,"modelId":model,"result":res.get("result") if res else None})
 app.router.add_get("/api/loops",loops_list)
 app.router.add_post("/api/loops",loops_create)
 app.router.add_delete("/api/loops",loops_stop)
 app.router.add_post("/api/loops/stop",loops_stop)
 app.router.add_post("/api/effort",effort_set)
 print("Grok Remote UI+hub   http://%s:%d/%s"%(lan,a.port,keyq),flush=True)
 print("Pair on this PC      http://127.0.0.1:%d/pair"%a.port,flush=True)
 print("Multi-client WS      ws://%s:%d/ws  -> shared agent %s:%d"%(lan,a.port,agent_host,a.agent_port),flush=True)
 if a.secret:print("Access key required   paired link above carries it once; unauthenticated requests get 401",flush=True)
 print("Workspace            %s"%state["cwd"],flush=True)
 runner=web.AppRunner(app);await runner.setup()
 site=web.TCPSite(runner,a.bind,a.port)
 try:
  await site.start()
 except OSError as e:
  # Port busy is NOT automatically a zombie. Two stacked supervisors used to reach this
  # branch and claim_port would MURDER the healthy instance, whose supervisor respawned it
  # and murdered ours - every cycle dropped all phone clients. If whoever holds the port
  # answers /health like a live grok-remote, this copy stands down (exit 97 tells the
  # supervisor loop to stop respawning).
  try:
   from aiohttp import ClientSession,ClientTimeout
   async with ClientSession(timeout=ClientTimeout(total=4,connect=2)) as _s:
    async with _s.get("http://127.0.0.1:%d/health"%a.port) as _r:
     if _r.status==200 and "ok" in (await _r.text())[:200]:
      print("[bind] :%d already served by a HEALTHY grok-remote — standing down"%a.port,flush=True)
      sys.exit(97)
  except SystemExit:raise
  except Exception:pass
  print("[bind] :%d busy (%s) — no healthy responder, claiming port and retry"%(a.port,e),flush=True)
  claim_port(a.port,"ui")
  await asyncio.sleep(0.6)
  site=web.TCPSite(runner,a.bind,a.port)
  await site.start()
 if getattr(a,"ensure_agent",False) or not listen_pids(a.agent_port):
  try:
   if not listen_pids(a.agent_port):
    print("[boot] agent not on :%d — starting"%a.agent_port,flush=True)
    start_agent_process(a.secret,a.agent_port,state["cwd"])
    await asyncio.get_event_loop().run_in_executor(None,lambda:wait_port(a.agent_port,18))
   await hub.ensure(retries=5,delay=0.35)
  except Exception as e:
   print("[boot] agent ensure failed:",e,flush=True)
 if str(a.agent_host) in ("127.0.0.1","localhost","::1"):
  hub.spawn_agent=lambda:start_agent_process(a.secret,a.agent_port,state["cwd"])
 try:
  loops.start_all()
  hub.start_watch()
  print("[loop] restored %d job(s)"%len(loops.jobs),flush=True)
  print("[hub] wireless watch · client heartbeat 12s · upstream keepalive",flush=True)
  try:
   from pairing import addresses,banner,ensure_segno,utf8_stdout
   utf8_stdout();banner(addresses(a.port,a.secret,public_host=getattr(a,"public_host","") or ""),a.port,have_qr=ensure_segno())
  except Exception as e:
   print("[pair] banner skipped:",e,flush=True)
  while True:await asyncio.sleep(3600)
 finally:
  for t in list(loops._tasks.values()):
   try:t.cancel()
   except Exception:pass
  await hub.close()
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--port",type=int,default=2421);ap.add_argument("--bind",default="0.0.0.0")
 ap.add_argument("--agent-host",default="127.0.0.1");ap.add_argument("--agent-port",type=int,default=2419)
 ap.add_argument("--secret",default=os.environ.get("GROK_AGENT_SECRET",""))
 ap.add_argument("--cwd",default=os.getcwd())
 ap.add_argument("--public-host",default=os.environ.get("GROK_REMOTE_PUBLIC_HOST",""))
 ap.add_argument("--claim-ports",action="store_true",help="kill other listeners on UI+agent ports before bind")
 ap.add_argument("--ensure-agent",action="store_true",help="start agent serve if not listening")
 a=ap.parse_args()
 if not a.secret:
  print("ERROR: --secret or GROK_AGENT_SECRET required",file=sys.stderr);sys.exit(2)
 if a.claim_ports or os.environ.get("GROK_REMOTE_CLAIM_PORTS")=="1":
  claim_port(a.port,"ui")
  claim_port(a.agent_port,"agent")
 a.ensure_agent=bool(a.ensure_agent or os.environ.get("GROK_REMOTE_ENSURE_AGENT","1")!="0")
 try:asyncio.run(main_async(a))
 except KeyboardInterrupt:pass
if __name__=="__main__":main()
