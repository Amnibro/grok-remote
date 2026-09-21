"""Public HTTPS origin for Grok Remote (Cloudflare tunnel or open 443), Amni-Chat style."""
import json,os,re,shutil,subprocess,threading,time
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
def live_tunnel_url():
 u=str((_cf.get("url") or "")).strip()
 if u:return u
 return str((load_plugin_cfg().get("tunnel_url") or "")).strip()
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
 return {"ok":True,"available":cloudflared_available(),"running":alive,"url":live_tunnel_url(),"error":_cf.get("err") or ""}
def stop_quick_tunnel():
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
  if str(d.get("tunnel_url") or "").find("trycloudflare.com")>=0:
   patch_plugin_cfg(tunnel_url="")
 except Exception:pass
 _cf["url"]=""
 return tunnel_status()
def start_quick_tunnel(port=2421,timeout=22):
 bin=_cloudflared_bin()
 if not bin:
  _cf["err"]="cloudflared not found"
  return False,"cloudflared not found",tunnel_status()
 stop_quick_tunnel()
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
 def _read():
  try:
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
    if m:
     found["u"]=m.group(0).rstrip("/")
     _cf["url"]=found["u"]
     try:patch_plugin_cfg(tunnel_url=found["u"])
     except Exception:pass
     break
  except Exception as e:
   _cf["err"]=str(e)[:200]
 t=threading.Thread(target=_read,daemon=True)
 t.start();t.join(timeout=max(8,int(timeout or 22)))
 if found["u"]:
  return True,"",tunnel_status()
 if proc.poll() is not None:
  _cf["err"]="cloudflared exited"
  return False,_cf["err"],tunnel_status()
 _cf["err"]="tunnel URL not ready yet — wait and refresh"
 return False,_cf["err"],tunnel_status()
