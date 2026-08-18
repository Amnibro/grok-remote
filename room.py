"""Agent chat room (beta) - short messages between the agents sharing this hub.

Deliberately not a transcript. One line each, 240 characters, newest last. Agents post with a
one-line curl (loopback needs no key) or `python room.py say "..."`. The UI polls the feed.
"""
import os,sys,json,time,argparse
from pathlib import Path
LIMIT=240
KEEP=2000
def data_dir():
 base=os.environ.get("GROK_PLUGIN_DATA") or str(Path.home()/".grok"/"plugin-data"/"grok-remote")
 p=Path(base);p.mkdir(parents=True,exist_ok=True);return p
def store_path():return data_dir()/"room.jsonl"
def _read_all():
 p=store_path()
 if not p.is_file():return []
 out=[]
 try:
  with p.open("r",encoding="utf-8",errors="replace") as f:
   for line in f:
    line=line.strip()
    if not line:continue
    try:
     m=json.loads(line)
     if isinstance(m,dict) and m.get("text"):out.append(m)
    except Exception:continue
 except Exception:return []
 return out
def _next_id(msgs):
 n=0
 for m in msgs:
  try:n=max(n,int(m.get("id") or 0))
  except Exception:pass
 return n+1
def clean(text):
 t=" ".join(str(text or "").split())
 return t[:LIMIT]
def say(who,text,kind="say"):
 t=clean(text)
 if not t:return {"ok":False,"error":"empty message"}
 w=" ".join(str(who or "agent").split())[:32] or "agent"
 msgs=_read_all()
 m={"id":_next_id(msgs),"ts":time.time(),"who":w,"text":t,"kind":str(kind or "say")[:12]}
 if len(msgs)>=KEEP:
  msgs=msgs[-(KEEP//2):]
  tmp=store_path().with_suffix(".tmp")
  with tmp.open("w",encoding="utf-8",newline="\n") as f:
   for old in msgs:f.write(json.dumps(old,ensure_ascii=False)+"\n")
  tmp.replace(store_path())
 with store_path().open("a",encoding="utf-8",newline="\n") as f:
  f.write(json.dumps(m,ensure_ascii=False)+"\n")
 return {"ok":True,"message":m}
def feed(since=0,limit=200):
 try:since=int(since or 0)
 except Exception:since=0
 try:limit=max(1,min(int(limit or 200),500))
 except Exception:limit=200
 msgs=[m for m in _read_all() if int(m.get("id") or 0)>since]
 return msgs[-limit:]
def members(window=900):
 now=time.time();seen={}
 for m in _read_all():
  try:ts=float(m.get("ts") or 0)
  except Exception:ts=0
  if now-ts>window:continue
  w=str(m.get("who") or "")
  if not w:continue
  cur=seen.get(w)
  if not cur or ts>cur["last"]:seen[w]={"who":w,"last":ts,"n":(cur["n"]+1 if cur else 1)}
  elif cur:cur["n"]+=1
 return sorted(seen.values(),key=lambda r:-r["last"])
def clear():
 p=store_path()
 try:
  if p.is_file():p.unlink()
 except Exception:pass
 return {"ok":True}
def _who_default():
 return (os.environ.get("GROK_ROOM_WHO") or os.environ.get("GROK_AGENT_NAME")
  or os.environ.get("COMPUTERNAME") or "agent")
def main(argv=None):
 ap=argparse.ArgumentParser(prog="room",description="short messages between agents on this hub")
 sub=ap.add_subparsers(dest="cmd")
 s=sub.add_parser("say",help="post one short line")
 s.add_argument("text",nargs="+");s.add_argument("--who",default=_who_default())
 r=sub.add_parser("read",help="print the feed")
 r.add_argument("--since",type=int,default=0);r.add_argument("--limit",type=int,default=50)
 w=sub.add_parser("watch",help="follow new lines")
 w.add_argument("--interval",type=float,default=2.0)
 sub.add_parser("who",help="who has spoken recently")
 sub.add_parser("clear",help="wipe the room")
 a=ap.parse_args(argv)
 if a.cmd=="say":
  out=say(a.who," ".join(a.text))
  if not out.get("ok"):print("error:",out.get("error"),file=sys.stderr);return 1
  m=out["message"];print("[%d] %s: %s"%(m["id"],m["who"],m["text"]));return 0
 if a.cmd=="read":
  for m in feed(a.since,a.limit):
   print("[%d] %-12s %s"%(m["id"],m["who"],m["text"]))
  return 0
 if a.cmd=="who":
  for m in members():
   print("%-12s %ds ago  x%d"%(m["who"],int(time.time()-m["last"]),m["n"]))
  return 0
 if a.cmd=="watch":
  last=0
  seen=feed(0,500)
  if seen:last=int(seen[-1]["id"])
  try:
   while True:
    for m in feed(last,200):
     print("[%d] %-12s %s"%(m["id"],m["who"],m["text"]),flush=True);last=int(m["id"])
    time.sleep(max(0.5,a.interval))
  except KeyboardInterrupt:return 0
 if a.cmd=="clear":
  clear();print("room cleared");return 0
 ap.print_help();return 1
if __name__=="__main__":sys.exit(main())
