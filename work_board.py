import os,re,sqlite3,time,threading,hashlib,base64,mimetypes
from pathlib import Path
_TERM=("completed","failed","error","cancelled","canceled")
def db_path():
 base=os.environ.get("GROK_PLUGIN_DATA") or str(Path.home()/".grok"/"plugin-data"/"grok-remote")
 Path(base).mkdir(parents=True,exist_ok=True)
 return str(Path(base)/"work.sqlite")
def strip_ask(t):
 t=str(t or "")
 t=re.sub(r"\[AGENT SETUP[\s\S]*?\[END AGENT SETUP\]","",t,flags=re.I)
 t=re.sub(r"\[INTERJECT[^\]]*\]","",t,flags=re.I)
 t=re.sub(r"\[Queued guidance[^\]]*\]","",t,flags=re.I)
 t=re.sub(r"\[FYI[^\]]*\]","",t,flags=re.I)
 t=re.sub(r"\[Reaction meter[^\]]*\][\s\S]*?(?:\n{2,}|$)","",t,flags=re.I)
 return re.sub(r"\s+"," ",t).strip()[:240]
def _b64(raw):
 s=str(raw or "").strip()
 if not s:return b""
 if "," in s[:80] and s.lower().startswith("data:"):s=s.split(",",1)[1]
 try:return base64.b64decode(s,validate=False)
 except Exception:return b""
STALL_SECS=240.0
STALL_QUIET=5.0
class WorkBoard:
 def __init__(self,path=None):
  self.path=path or db_path()
  self._l=threading.Lock()
  self._init()
 def att_root(self):
  return str(Path(self.path).parent/"att")
 def _cx(self):
  c=sqlite3.connect(self.path,timeout=8,isolation_level=None)
  c.row_factory=sqlite3.Row
  c.execute("PRAGMA journal_mode=WAL")
  c.execute("PRAGMA synchronous=NORMAL")
  return c
 def _init(self):
  with self._l:
   c=self._cx()
   try:
    c.executescript("""
CREATE TABLE IF NOT EXISTS jobs(sid TEXT PRIMARY KEY,title TEXT,cwd TEXT,phase TEXT,detail TEXT,last_user TEXT,last_user_at REAL,queue TEXT,running INTEGER NOT NULL DEFAULT 0,updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS tools(sid TEXT NOT NULL,tool_id TEXT NOT NULL,title TEXT,status TEXT,cmd TEXT,updated REAL NOT NULL,PRIMARY KEY(sid,tool_id));
CREATE TABLE IF NOT EXISTS asks(id INTEGER PRIMARY KEY AUTOINCREMENT,sid TEXT NOT NULL,text TEXT NOT NULL,at REAL NOT NULL,acked INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS atts(id TEXT PRIMARY KEY,sid TEXT NOT NULL,name TEXT,mime TEXT,path TEXT,sha TEXT,text_key TEXT,at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS ix_asks_sid ON asks(sid,at);
CREATE INDEX IF NOT EXISTS ix_jobs_run ON jobs(running,updated);
CREATE INDEX IF NOT EXISTS ix_atts_sid ON atts(sid,at);
CREATE UNIQUE INDEX IF NOT EXISTS ix_atts_sha ON atts(sid,sha);
""")
   finally:c.close()
 def _job(self,c,sid):
  r=c.execute("SELECT * FROM jobs WHERE sid=?",(sid,)).fetchone()
  if r:return dict(r)
  now=time.time()
  c.execute("INSERT INTO jobs(sid,title,cwd,phase,detail,last_user,last_user_at,queue,running,updated) VALUES(?,?,?,?,?,?,?,?,?,?)",(sid,"","","idle","", "",0,"",0,now))
  return dict(c.execute("SELECT * FROM jobs WHERE sid=?",(sid,)).fetchone())
 def _open_n(self,c,sid):
  return c.execute("SELECT COUNT(*) FROM tools WHERE sid=? AND lower(COALESCE(status,'')) NOT IN ('completed','failed','error','cancelled','canceled')",(sid,)).fetchone()[0]
 def _tool_n(self,c,sid):
  return c.execute("SELECT COUNT(*) FROM tools WHERE sid=?",(sid,)).fetchone()[0]
 def _idle_if_clear(self,c,sid,now):
  if self._open_n(c,sid):return False
  c.execute("UPDATE jobs SET running=0,phase=?,detail=?,updated=? WHERE sid=?",("idle","",now,sid))
  c.execute("UPDATE asks SET acked=1 WHERE sid=? AND acked=0",(sid,))
  return True
 def note_prompt(self,sid,text,title="",cwd=""):
  sid=str(sid or "").strip()
  if not sid:return False
  ask=strip_ask(text)
  now=time.time()
  with self._l:
   c=self._cx()
   try:
    self._job(c,sid)
    if ask:c.execute("INSERT INTO asks(sid,text,at,acked) VALUES(?,?,?,0)",(sid,ask,now))
    c.execute("UPDATE jobs SET last_user=COALESCE(NULLIF(?,''),last_user),last_user_at=?,phase=?,detail=?,running=1,title=COALESCE(NULLIF(?,''),title),cwd=COALESCE(NULLIF(?,''),cwd),updated=? WHERE sid=?",(ask,now,"waiting",ask[:80] if ask else "prompt",title or "",cwd or "",now,sid))
   finally:c.close()
  return True
 def note_update(self,sid,upd,meta=None):
  sid=str(sid or "").strip()
  if not sid or not isinstance(upd,dict):return False
  k=str(upd.get("sessionUpdate") or upd.get("kind") or "")
  now=time.time()
  meta=meta if isinstance(meta,dict) else {}
  st=str((meta.get("updateParams") or {}).get("status") or upd.get("status") or "")
  with self._l:
   c=self._cx()
   try:
    self._job(c,sid)
    if k in ("user_message_chunk",):
     tx=""
     ct=upd.get("content")
     if isinstance(ct,dict):tx=str(ct.get("text") or "")
     elif isinstance(ct,list):
      tx=" ".join(str((x or {}).get("text") or "") for x in ct if isinstance(x,dict))
     tx=strip_ask(tx)
     if tx:c.execute("UPDATE jobs SET last_user=?,last_user_at=?,updated=? WHERE sid=?",(tx,now,now,sid))
    elif k=="agent_thought_chunk":
     c.execute("UPDATE jobs SET phase=?,detail=?,running=1,updated=? WHERE sid=?",("thinking","thinking",now,sid))
    elif k=="agent_message_chunk":
     c.execute("UPDATE jobs SET phase=?,detail=?,running=1,updated=? WHERE sid=?",("responding","writing",now,sid))
    elif k in ("tool_call","tool_call_update"):
     tid=str(upd.get("toolCallId") or upd.get("id") or "")
     title=str(upd.get("title") or upd.get("toolName") or upd.get("kind") or "tool")
     ri=upd.get("rawInput") if isinstance(upd.get("rawInput"),dict) else {}
     cmd=str(ri.get("command") or ri.get("path") or ri.get("query") or "")[:160]
     if tid:
      c.execute("INSERT INTO tools(sid,tool_id,title,status,cmd,updated) VALUES(?,?,?,?,?,?) ON CONFLICT(sid,tool_id) DO UPDATE SET title=COALESCE(NULLIF(excluded.title,''),tools.title),status=COALESCE(NULLIF(excluded.status,''),tools.status),cmd=COALESCE(NULLIF(excluded.cmd,''),tools.cmd),updated=excluded.updated",(sid,tid,title,st or "Pending",cmd,now))
     low=st.lower()
     open_n=self._open_n(c,sid)
     if low in _TERM and not open_n:
      self._idle_if_clear(c,sid,now)
     else:
      c.execute("UPDATE jobs SET phase=?,detail=?,running=1,updated=? WHERE sid=?",("tools",title[:80],now,sid))
    elif k in ("turn_completed","task_completed"):
     if self._open_n(c,sid):
      c.execute("UPDATE jobs SET phase=?,detail=?,running=1,updated=? WHERE sid=?",("tools","command running",now,sid))
     else:
      self._idle_if_clear(c,sid,now)
   finally:c.close()
  return True
 def note_queue(self,sid,entries,running_id=None):
  sid=str(sid or "").strip()
  if not sid:return False
  bits=[]
  for e in entries or []:
   if isinstance(e,dict):bits.append(strip_ask(e.get("text") or "")[:80])
   else:bits.append(strip_ask(e)[:80])
  q=" · ".join([b for b in bits if b])[:400]
  now=time.time()
  with self._l:
   c=self._cx()
   try:
    self._job(c,sid)
    if running_id or q:
     c.execute("UPDATE jobs SET queue=?,running=1,phase=CASE WHEN ? THEN 'waiting' ELSE phase END,updated=? WHERE sid=?",(q,1 if running_id else 0,now,sid))
    else:
     c.execute("UPDATE jobs SET queue=?,updated=? WHERE sid=?",("",now,sid))
     if not self._open_n(c,sid):
      ph=str((c.execute("SELECT phase FROM jobs WHERE sid=?",(sid,)).fetchone() or ["idle"])[0] or "")
      if ph in ("waiting","tools"):self._idle_if_clear(c,sid,now)
   finally:c.close()
  return True
 def mark_cancel(self,sid):
  sid=str(sid or "").strip()
  if not sid:return False
  now=time.time()
  with self._l:
   c=self._cx()
   try:
    c.execute("UPDATE jobs SET running=0,phase=?,detail=?,updated=? WHERE sid=?",("idle","cancelled",now,sid))
    c.execute("UPDATE tools SET status=?,updated=? WHERE sid=? AND lower(COALESCE(status,'')) NOT IN ('completed','failed','error','cancelled','canceled')",("cancelled",now,sid))
    c.execute("UPDATE asks SET acked=1 WHERE sid=? AND acked=0",(sid,))
   finally:c.close()
  return True
 def heal(self,sid=None):
  now=time.time()
  with self._l:
   c=self._cx()
   try:
    q="SELECT sid,phase FROM jobs WHERE running=1"
    args=[]
    if sid:
     q+=" AND sid=?";args.append(str(sid))
    rows=list(c.execute(q,args).fetchall())
    n=0
    for r in rows:
     s=r["sid"]
     if self._open_n(c,s):continue
     jr=c.execute("SELECT last_user_at,updated FROM jobs WHERE sid=?",(s,)).fetchone()
     la=float((jr["last_user_at"] if jr else 0) or 0)
     up=float((jr["updated"] if jr else 0) or 0)
     # A prompt the agent ACCEPTED and answered with nothing never reached the checks below:
     # last_tool < last_ask sent it to `continue`, so the job stayed running forever and the
     # client spun. Total silence since the ask is the tell - a live turn bumps `updated` on
     # every session/update, so a real long turn never looks like this.
     if la and now-la>STALL_SECS and up<=la+STALL_QUIET:
      c.execute("UPDATE jobs SET running=0,phase=?,detail=?,updated=? WHERE sid=?",("stalled","agent accepted the prompt and returned nothing",now,s))
      c.execute("UPDATE asks SET acked=1 WHERE sid=? AND acked=0",(s,))
      n+=1;continue
     if self._tool_n(c,s)<=0:continue
     ph=str(r["phase"] or "")
     if ph not in ("waiting","tools"):continue
     job=c.execute("SELECT last_user_at FROM jobs WHERE sid=?",(s,)).fetchone()
     tu=c.execute("SELECT MAX(updated) FROM tools WHERE sid=?",(s,)).fetchone()
     last_ask=float((job[0] if job else 0) or 0)
     last_tool=float((tu[0] if tu else 0) or 0)
     if last_ask and last_tool and last_tool<last_ask:continue
     self._idle_if_clear(c,s,now)
     n+=1
    return n
   finally:c.close()
 def snapshot(self,sid=None):
  self.heal(sid)
  with self._l:
   c=self._cx()
   try:
    if sid:
     rows=c.execute("SELECT * FROM jobs WHERE sid=?",(str(sid),)).fetchall()
    else:
     rows=c.execute("SELECT * FROM jobs ORDER BY running DESC,updated DESC LIMIT 40").fetchall()
    out=[]
    for r in rows:
     d=dict(r)
     d["tools"]=[dict(x) for x in c.execute("SELECT tool_id AS id,title,status,cmd,updated FROM tools WHERE sid=? ORDER BY updated DESC LIMIT 12",(d["sid"],)).fetchall()]
     d["asks"]=[dict(x) for x in c.execute("SELECT id,text,at,acked FROM asks WHERE sid=? ORDER BY at DESC LIMIT 8",(d["sid"],)).fetchall()]
     d["running"]=bool(d.get("running"))
     out.append(d)
    return out
   finally:c.close()
 def save_att(self,sid,name,mime,raw,text_key=""):
  sid=str(sid or "").strip()
  if not sid or not raw:return None
  if not isinstance(raw,(bytes,bytearray)):raw=_b64(raw)
  if not raw:return None
  if len(raw)>28*1024*1024:return None
  mime=str(mime or "").split(";")[0].strip().lower() or "application/octet-stream"
  if not (mime.startswith("image/") or mime.startswith("video/") or mime in ("application/octet-stream",)):
   if not re.search(r"\.(png|jpe?g|gif|webp|bmp|svg|mp4|webm|mov|m4v)$",str(name or ""),re.I):return None
  sha=hashlib.sha256(bytes(raw)).hexdigest()
  aid=sha[:24]
  ext=Path(str(name or "")).suffix.lower()
  if not ext:
   ext=mimetypes.guess_extension(mime) or (".png" if mime.startswith("image/") else ".bin")
  root=Path(self.att_root())/re.sub(r"[^A-Za-z0-9._-]","_",sid)[:80]
  root.mkdir(parents=True,exist_ok=True)
  dest=root/(aid+ext)
  if not dest.is_file():dest.write_bytes(bytes(raw))
  now=time.time()
  key=strip_ask(text_key)[:80]
  with self._l:
   c=self._cx()
   try:
    c.execute("INSERT OR IGNORE INTO atts(id,sid,name,mime,path,sha,text_key,at) VALUES(?,?,?,?,?,?,?,?)",(aid,sid,str(name or "file")[:180],mime,str(dest),sha,key,now))
    if key:c.execute("UPDATE atts SET text_key=COALESCE(NULLIF(?,''),text_key) WHERE id=?",(key,aid))
   finally:c.close()
  return {"id":aid,"sid":sid,"name":str(name or "file"),"mime":mime,"url":"/api/att/"+aid,"sha":sha,"text_key":key}
 def ingest_prompt(self,sid,blocks):
  sid=str(sid or "").strip()
  out=[]
  if not sid or not isinstance(blocks,list):return out
  text_key=""
  for b in blocks:
   if isinstance(b,dict) and b.get("type")=="text":
    tx=strip_ask(b.get("text") or "")
    if tx and not text_key:text_key=tx[:80]
  for b in blocks:
   if not isinstance(b,dict):continue
   typ=str(b.get("type") or "")
   if typ=="image" or str(b.get("mimeType") or "").startswith("image/"):
    rec=self.save_att(sid,b.get("name") or "image",b.get("mimeType") or "image/png",b.get("data") or "",text_key)
    if rec:out.append(rec)
   elif typ in ("resource","video"):
    res=b.get("resource") if isinstance(b.get("resource"),dict) else b
    mime=str(res.get("mimeType") or b.get("mimeType") or "")
    blob=res.get("blob") or b.get("data") or b.get("blob")
    uri=str(res.get("uri") or b.get("uri") or "")
    name=Path(uri.replace("file:///","")).name if uri else (b.get("name") or "file")
    rec=self.save_att(sid,name,mime,blob or "",text_key)
    if rec:out.append(rec)
  return out
 def list_atts(self,sid):
  sid=str(sid or "").strip()
  if not sid:return []
  with self._l:
   c=self._cx()
   try:
    rows=c.execute("SELECT id,sid,name,mime,text_key,at FROM atts WHERE sid=? ORDER BY at ASC",(sid,)).fetchall()
    return [{"id":r["id"],"sid":r["sid"],"name":r["name"],"mime":r["mime"],"text_key":r["text_key"],"at":r["at"],"url":"/api/att/"+r["id"]} for r in rows]
   finally:c.close()
 def get_att(self,aid):
  aid=str(aid or "").strip()
  if not aid:return None
  with self._l:
   c=self._cx()
   try:
    r=c.execute("SELECT * FROM atts WHERE id=?",(aid,)).fetchone()
    return dict(r) if r else None
   finally:c.close()
