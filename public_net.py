"""Public HTTPS origin for Grok Remote (Cloudflare tunnel or open 443), Amni-Chat style."""
import json,os,re,shutil,signal,subprocess,threading,time
from pathlib import Path
def plugin_data_dir():
 base=os.environ.get("GROK_PLUGIN_DATA") or str(Path.home()/".grok"/"plugin-data"/"grok-remote")
 p=Path(base);p.mkdir(parents=True,exist_ok=True);return p
def plugin_cfg_path():
 return plugin_data_dir()/"config.json"
def load_plugin_cfg():
 path=plugin_cfg_path()
 if not path.is_file():return {}
 try:
  d=json.loads(path.read_text(encoding="utf-8",errors="replace"))
  return d if isinstance(d,dict) else {}
 except Exception:return {}
def patch_plugin_cfg(**kw):
 d=load_plugin_cfg()
 for k,v in kw.items():
  if v is None:continue
  if v=="" and k in d:d.pop(k,None)
  else:d[k]=v
 path=plugin_cfg_path()
 tmp=path.with_suffix(".tmp")
 tmp.write_text(json.dumps(d,indent=2),encoding="utf-8")
 tmp.replace(path)
 return d
def parse_public_origin(raw,default_port=2421):
 s=str(raw or "").strip().rstrip("/")
 if not s:return None
 scheme=""
 rest=s
 if s.lower().startswith("https://"):
  scheme="https";rest=s[8:]
 elif s.lower().startswith("http://"):
  scheme="http";rest=s[7:]
 host=rest.split("/")[0].strip()
 if not host:return None
 port=None
 if host.startswith("[") and "]" in host:
  br=host.find("]")
  name=host[1:br];tail=host[br+1:]
  host=name
  if tail.startswith(":"):
   try:port=int(tail[1:])
   except Exception:pass
 elif host.count(":")==1:
  h,p=host.rsplit(":",1)
  if p.isdigit():
   host,port=h,int(p)
 alpha=any(c.isalpha() for c in host)
 ipv4=bool(host.replace(".","").isdigit())
 if not scheme:
  scheme="https" if (alpha and not ipv4) else "http"
 if port is None:
  if scheme=="https":port=443
  elif alpha and not ipv4:port=80
  else:port=int(default_port or 2421)
 https=scheme=="https"
 if https and int(port) in (80,443):
  origin="https://%s"%host
 elif (not https) and int(port)==80:
  origin="http://%s"%host
 else:
  origin="%s://%s:%d"%(scheme,host,int(port))
 return {"host":host,"port":int(port),"https":bool(https),"origin":origin,"kind":"pub" if https or (alpha and not ipv4) else "wan"}
def named_public_raw():
 env=str(os.environ.get("GROK_REMOTE_PUBLIC_URL") or os.environ.get("GROK_REMOTE_PUBLIC_HOST") or "").strip()
 cfg=str((load_plugin_cfg().get("public_url") or "")).strip()
 return cfg or env
def away_mode():
 return str((load_plugin_cfg().get("away_mode") or "")).strip().lower()
def set_away_mode(mode):
 patch_plugin_cfg(away_mode=str(mode or "").strip().lower())
_probe={"t":0.0,"url":"","ok":False}
def quick_tunnel_live(url,timeout=3):
 url=str(url or "").strip().rstrip("/")
 if "trycloudflare.com" not in url.lower():return False
 now=time.time()
 if _probe.get("url")==url and now-float(_probe.get("t") or 0)<20:
  return bool(_probe.get("ok"))
 ok=False
 try:
  import urllib.request
  req=urllib.request.Request(url+"/health",headers={"User-Agent":"grok-remote"})
  with urllib.request.urlopen(req,timeout=timeout) as r:
   body=r.read(500).decode("utf-8","replace")
   ok=getattr(r,"status",0)==200 and '"ok"' in body.replace(" ","") and "true" in body.lower()
 except Exception:
  ok=False
 _probe["t"]=now;_probe["url"]=url;_probe["ok"]=ok
 return ok
def live_tunnel_url():
 proc=_cf.get("proc")
 alive=bool(proc) and proc.poll() is None
 mem=str((_cf.get("url") or "")).strip()
 if alive and mem:return mem
 saved=str((load_plugin_cfg().get("tunnel_url") or "")).strip()
 if "trycloudflare.com" not in saved.lower():
  return saved if alive else ""
 if alive:return saved
 # Request path must not open a socket. The supervisor fills this cache.
 if _probe.get("url")==saved.rstrip("/") and _probe.get("ok") and time.time()-float(_probe.get("t") or 0)<45:
  return saved
 return ""
def load_public_origin(default_port=2421):
 for raw in (named_public_raw(),live_tunnel_url()):
  p=parse_public_origin(raw,default_port=default_port)
  if p:return p
 return None
def pair_pin(secret):
 import hashlib,hmac
 n=int(hmac.new(b"grok-remote-pin",str(secret or "").encode(),hashlib.sha256).hexdigest()[:12],16)
 return "%06d"%(n%1000000)
def pair_token(secret):
 import hashlib,hmac
 return hmac.new(b"grok-remote-t",str(secret or "").encode(),hashlib.sha256).hexdigest()[:32]
def pair_unlock_ok(secret,token,pin):
 import hmac
 tok=str(token or "").strip()
 p=str(pin or "").strip()
 if len(tok)<16 or len(p)!=6 or not p.isdigit():return False
 return hmac.compare_digest(tok,pair_token(secret)) and hmac.compare_digest(p,pair_pin(secret))
def public_url_for(key,default_port=2421,include_key=False):
 p=load_public_origin(default_port=default_port)
 if not p:return ""
 if include_key and key:
  q="?key=%s&auto=1"%key
 elif key:
  q="?t=%s&auto=1"%pair_token(key)
 else:
  q="?auto=1"
 if p["https"] and int(p["port"]) in (443,80):
  return "%s/%s"%(p["origin"],q)
 return "%s/%s"%(p["origin"],q)
_cf={"proc":None,"url":"","err":""}
_CF_URL=re.compile(r"https://[a-z0-9.-]+\.trycloudflare\.com",re.I)
def _cloudflared_bin():
 p=shutil.which("cloudflared")
 if p:return p
 for c in (r"C:\Program Files\cloudflared\cloudflared.exe",r"C:\Program Files (x86)\cloudflared\cloudflared.exe"):
  if Path(c).is_file():return c
 return ""
def cloudflared_available():
 return bool(_cloudflared_bin())
def tunnel_status():
 proc=_cf.get("proc")
 alive=bool(proc) and proc.poll() is None
 url=live_tunnel_url()
 return {"ok":True,"available":cloudflared_available(),"running":bool(alive or url),"url":url,"error":_cf.get("err") or ""}
def stop_quick_tunnel(forget=False):
 proc=_cf.get("proc")
 _cf["proc"]=None
 if proc and proc.poll() is None:
  try:proc.terminate()
  except Exception:pass
  try:
   proc.wait(timeout=3)
  except Exception:
   try:proc.kill()
   except Exception:pass
 # keep named public_url; drop ephemeral trycloudflare
 try:
  d=load_plugin_cfg()
  kw={}
  if str(d.get("tunnel_url") or "").find("trycloudflare.com")>=0:
   kw["tunnel_url"]=""
  if forget and str(d.get("away_mode") or "")=="cloudflare":
   kw["away_mode"]=""
  if kw:patch_plugin_cfg(**kw)
 except Exception:pass
 _cf["url"]=""
 if forget:
  try:_reap_other_quick_tunnels(int(_sup.get("port") or 2421),0)
  except Exception:pass
 return tunnel_status()
_start_lock=threading.Lock()
def start_quick_tunnel(port=2421,timeout=22):
 bin=_cloudflared_bin()
 if not bin:
  _cf["err"]="cloudflared not found"
  return False,"cloudflared not found",tunnel_status()
 proc=_cf.get("proc")
 if proc and proc.poll() is None and str(_cf.get("url") or ""):
  set_away_mode("cloudflare")
  return True,"",tunnel_status()
 if not _start_lock.acquire(blocking=False):
  return False,"tunnel start already running",tunnel_status()
 try:
  set_away_mode("cloudflare")
  stop_quick_tunnel(forget=False)
  kw={"stdout":subprocess.PIPE,"stderr":subprocess.STDOUT,"stdin":subprocess.DEVNULL}
  if os.name=="nt":
   kw["creationflags"]=0x08000000
   kw["startupinfo"]=subprocess.STARTUPINFO()
   kw["startupinfo"].dwFlags|=subprocess.STARTF_USESHOWWINDOW
  try:
   proc=subprocess.Popen([bin,"tunnel","--no-autoupdate","--url","http://127.0.0.1:%d"%int(port)],**kw)
  except Exception as e:
   _cf["err"]=str(e)[:240]
   return False,_cf["err"],tunnel_status()
  _cf["proc"]=proc
  _cf["err"]=""
  found={"u":""}
  ready=threading.Event()
  def _read():
   try:
    # Keep draining after the URL. Stopping the read fills the pipe and cloudflared stalls.
    while True:
     line=proc.stdout.readline()
     if not line:
      if proc.poll() is not None:break
      time.sleep(0.05);continue
     if isinstance(line,bytes):
      try:txt=line.decode("utf-8","replace")
      except Exception:txt=str(line)
     else:txt=line
     m=_CF_URL.search(txt)
     if m and not found["u"]:
      found["u"]=m.group(0).rstrip("/")
      _cf["url"]=found["u"]
      try:patch_plugin_cfg(tunnel_url=found["u"])
      except Exception:pass
      print("[away] cloudflare %s"%found["u"],flush=True)
      ready.set()
      _reap_other_quick_tunnels(int(port),proc.pid)
   except Exception as e:
    _cf["err"]=str(e)[:200]
    ready.set()
  threading.Thread(target=_read,daemon=True,name="cloudflared-log").start()
  ready.wait(timeout=max(8,int(timeout or 22)))
  if found["u"]:
   return True,"",tunnel_status()
  if proc.poll() is not None:
   _cf["err"]="cloudflared exited"
   return False,_cf["err"],tunnel_status()
  _cf["err"]="tunnel URL not ready yet — wait and refresh"
  return False,_cf["err"],tunnel_status()
 finally:
  _start_lock.release()
_sup={"thread":None,"port":2421,"stop":False,"ts_tried":False}
def _reap_other_quick_tunnels(port,keep_pid):
 """Drop leftover quick tunnels to this port. Leave a named --token tunnel alone."""
 port=int(port or 0);keep=int(keep_pid or 0)
 if port<=0:return
 if os.name!="nt":
  pat=re.compile(r"(?:^|\s)--url[ =]http://(?:127\.0\.0\.1|localhost):%d(?:/|\s|$)"%port)
  for d in (os.listdir("/proc") if os.path.isdir("/proc") else []):
   try:
    if not d.isdigit() or int(d) in (keep,os.getpid(),getattr(_cf.get("proc"),"pid",0)) or os.stat("/proc/"+d).st_uid!=os.getuid():continue
    c=[x.decode("utf-8","replace") for x in Path("/proc/%s/cmdline"%d).read_bytes().split(b"\0") if x];j=" ".join(c)
    c and os.path.basename(c[0]).startswith("cloudflared") and "--token" not in j and pat.search(j) and os.kill(int(d),signal.SIGTERM)
   except Exception:continue
  return
 ps=(
  "Get-CimInstance Win32_Process -Filter \"Name='cloudflared.exe'\" | "
  "Where-Object { $_.ProcessId -ne %d -and $_.CommandLine -match '--url' -and "
  "$_.CommandLine -match '127.0.0.1:%d' -and $_.CommandLine -notmatch '--token' } | "
  "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
 )%(keep,port)
 try:
  subprocess.run(["powershell","-NoProfile","-Command",ps],timeout=8,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 except Exception:pass
def ensure_away(port=2421):
 mode=away_mode()
 if mode=="cloudflare":
  proc=_cf.get("proc")
  if proc and proc.poll() is None and str(_cf.get("url") or ""):
   _sup["cf_fails"]=0
   return tunnel_status()
  saved=str((load_plugin_cfg().get("tunnel_url") or "")).strip()
  if saved and quick_tunnel_live(saved):
   _sup["cf_fails"]=0
   _cf["url"]=saved
   return tunnel_status()
  _sup["cf_fails"]=int(_sup.get("cf_fails") or 0)+1
  # Hub restart leaves the old cloudflared up for a few seconds. Don't open a second one on the first miss.
  if _sup["cf_fails"]<3:
   return tunnel_status()
  start_quick_tunnel(port,timeout=20)
  _sup["cf_fails"]=0
  return tunnel_status()
 if mode=="tailscale" and int(_sup.get("ts_tries") or 0)<5:
  try:
   from remote_auth import enable_tailscale_serve,tailscale_snapshot
   snap=tailscale_snapshot(port,ttl=0)
   if snap.get("serve"):
    _sup["ts_tries"]=5
   else:
    ok,err,_snap=enable_tailscale_serve(port)
    _sup["ts_tries"]=5 if ok else int(_sup.get("ts_tries") or 0)+1
    if not ok and err:print("[away] tailscale:",err,flush=True)
  except Exception as e:
   _sup["ts_tries"]=int(_sup.get("ts_tries") or 0)+1
   print("[away] tailscale:",e,flush=True)
 return tunnel_status()
def start_away_supervisor(port=2421):
 if _sup.get("thread") and _sup["thread"].is_alive():
  _sup["port"]=int(port or 2421)
  return
 _sup["port"]=int(port or 2421)
 _sup["stop"]=False
 def _loop():
  time.sleep(1.5)
  while not _sup.get("stop"):
   try:ensure_away(_sup["port"])
   except Exception as e:print("[away]",e,flush=True)
   time.sleep(25)
 t=threading.Thread(target=_loop,daemon=True,name="away-supervisor")
 _sup["thread"]=t
 t.start()
