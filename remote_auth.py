"""Grok Remote access control: password + TOTP 2FA + session tokens."""
import base64,hashlib,hmac,json,os,secrets,struct,time
from pathlib import Path
def data_dir():
 base=os.environ.get("GROK_PLUGIN_DATA") or str(Path.home()/".grok"/"plugin-data"/"grok-remote")
 p=Path(base);p.mkdir(parents=True,exist_ok=True);return p
def store_path():return data_dir()/"access_security.json"
def _default():
 return {
  "version":1,"setup_complete":False,"setup_step":0,
  "access_mode":"lan","require_auth":False,"local_bypass":True,
  "password_hash":"","password_salt":"","totp_secret":"","totp_enabled":False,
  "display_name":"owner","sessions":{},"failed":{},"updated_at":0
 }
def load():
 path=store_path()
 if not path.is_file():return _default()
 try:
  data=json.loads(path.read_text(encoding="utf-8",errors="replace"))
  if not isinstance(data,dict):return _default()
  out=_default();out.update(data)
  if not isinstance(out.get("sessions"),dict):out["sessions"]={}
  if not isinstance(out.get("failed"),dict):out["failed"]={}
  return out
 except Exception:return _default()
def save(data):
 data=dict(data or {});data["updated_at"]=time.time()
 path=store_path();tmp=path.with_suffix(".tmp")
 tmp.write_text(json.dumps(data,indent=2),encoding="utf-8")
 tmp.replace(path)
 return data
def b64(b):return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")
def b64d(s):
 pad="="*((4-len(s)%4)%4);return base64.urlsafe_b64decode((s+pad).encode("ascii"))
def new_salt():return b64(secrets.token_bytes(16))
def hash_password(password,salt_b64,n=2**14,r=8,p=1):
 salt=b64d(salt_b64)
 dk=hashlib.scrypt(password.encode("utf-8"),salt=salt,n=n,r=r,p=p,dklen=32)
 return b64(dk)
def verify_password(password,salt_b64,hash_b64):
 if not password or not salt_b64 or not hash_b64:return False
 try:return hmac.compare_digest(hash_password(password,salt_b64),hash_b64)
 except Exception:return False
def new_totp_secret():
 return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")
def _totp_at(secret_b32,t,step=30,digits=6):
 pad="="*((8-len(secret_b32)%8)%8)
 key=base64.b32decode((secret_b32+pad).upper().encode("ascii"))
 counter=int(t//step)
 msg=struct.pack(">Q",counter)
 h=hmac.new(key,msg,hashlib.sha1).digest()
 o=h[-1]&0x0f
 code=(struct.unpack(">I",h[o:o+4])[0]&0x7fffffff)%(10**digits)
 return ("%0"+str(digits)+"d")%code
def verify_totp(secret_b32,code,window=1):
 if not secret_b32 or not code:return False
 c=str(code).strip().replace(" ","")
 if not c.isdigit():return False
 now=time.time()
 for w in range(-window,window+1):
  if hmac.compare_digest(_totp_at(secret_b32,now+w*30),c.zfill(6)[-6:]):return True
 return False
def otpauth_uri(secret_b32,account="owner",issuer="Grok Remote"):
 from urllib.parse import quote
 label=quote(issuer+":"+account);iss=quote(issuer)
 return "otpauth://totp/%s?secret=%s&issuer=%s&algorithm=SHA1&digits=6&period=30"%(label,secret_b32,iss)
def purge_sessions(data,now=None):
 now=now if now is not None else time.time()
 sess=data.get("sessions") or {}
 keep={k:v for k,v in sess.items() if isinstance(v,dict) and float(v.get("exp") or 0)>now}
 data["sessions"]=keep;return data
def issue_session(data,ttl_hours=168,meta=None):
 data=purge_sessions(data)
 tok=secrets.token_urlsafe(32)
 data.setdefault("sessions",{})[tok]={"exp":time.time()+ttl_hours*3600,"created":time.time(),"meta":meta or {}}
 save(data);return tok
def revoke_session(data,token):
 if token and token in (data.get("sessions") or {}):
  data["sessions"].pop(token,None);save(data)
 return data
def valid_session(data,token):
 if not token:return False
 data=purge_sessions(data)
 ent=(data.get("sessions") or {}).get(token)
 return bool(ent and float(ent.get("exp") or 0)>time.time())
def rate_limited(data,ip,limit=8,window=600):
 now=time.time();failed=data.get("failed") or {}
 arr=[t for t in (failed.get(ip) or []) if now-float(t)<window]
 failed[ip]=arr;data["failed"]=failed
 return len(arr)>=limit
def note_fail(data,ip):
 now=time.time();failed=data.get("failed") or {}
 arr=[t for t in (failed.get(ip) or []) if now-float(t)<600]
 arr.append(now);failed[ip]=arr[-20:];data["failed"]=failed;save(data)
def clear_fails(data,ip):
 failed=data.get("failed") or {}
 if ip in failed:failed.pop(ip,None);data["failed"]=failed;save(data)
def public_status(data,lan_ip="",port=2421,tailscale_ip=None):
 need=bool(data.get("setup_complete") and data.get("require_auth") and data.get("password_hash"))
 return {
  "ok":True,"setup_complete":bool(data.get("setup_complete")),"setup_step":int(data.get("setup_step") or 0),
  "require_auth":need,"totp_enabled":bool(data.get("totp_enabled")),
  "access_mode":data.get("access_mode") or "lan","local_bypass":bool(data.get("local_bypass")),
  "display_name":data.get("display_name") or "owner",
  "lan_ip":lan_ip,"port":port,"tailscale_ip":tailscale_ip,
  "urls":{
   "local":"http://127.0.0.1:%d/"%port,
   "lan":("http://%s:%d/"%(lan_ip,port)) if lan_ip else "",
   "tailscale":("http://%s:%d/"%(tailscale_ip,port)) if tailscale_ip else ""
  }
 }
def detect_tailscale():
 try:
  r=__import__("subprocess").run(["tailscale","ip","-4"],capture_output=True,text=True,timeout=3,encoding="utf-8",errors="replace")
  if r.returncode==0:
   ip=(r.stdout or "").strip().split()[0] if (r.stdout or "").strip() else ""
   if ip and ip.count(".")==3:return ip
 except Exception:pass
 return None
