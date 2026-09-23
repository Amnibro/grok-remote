"""NIP-04 text inbox for Grok Remote. Relays see ciphertext; npub stays on the PC pair page."""
import asyncio,hashlib,json,os,secrets,time
from pathlib import Path
def _data_dir():
 base=os.environ.get("GROK_PLUGIN_DATA") or str(Path.home()/".grok"/"plugin-data"/"grok-remote")
 p=Path(base);p.mkdir(parents=True,exist_ok=True);return p
def _key_path():
 return _data_dir()/"nostr.json"
_CHARSET="qpzry9x8gf2tvdw0s3jn54khce6mua7l"
def _bech32_hrp_expand(hrp):
 return [ord(x)>>5 for x in hrp]+[0]+[ord(x)&31 for x in hrp]
def _bech32_polymod(values):
 gen=[0x3b6a57b2,0x26508e6d,0x1ea119fa,0x3d4233dd,0x2a1462b3]
 chk=1
 for v in values:
  b=chk>>25
  chk=((chk&0x1ffffff)<<5)^v
  for i in range(5):
   if (b>>i)&1:chk^=gen[i]
 return chk
def _bech32_create(hrp,data):
 values=_bech32_hrp_expand(hrp)+data
 polymod=_bech32_polymod(values+[0,0,0,0,0,0])^1
 return hrp+"1"+"".join(_CHARSET[(d)] for d in data+[ (polymod>>5*(5-i))&31 for i in range(6)])
def _convertbits(data,frombits,tobits,pad=True):
 acc=0;bits=0;ret=[];maxv=(1<<tobits)-1
 for v in data:
  acc=(acc<<frombits)|v
  bits+=frombits
  while bits>=tobits:
   bits-=tobits
   ret.append((acc>>bits)&maxv)
 if pad and bits:ret.append((acc<<(tobits-bits))&maxv)
 return ret
def _bech32_decode(bech):
 b=str(bech or "").strip().lower()
 pos=b.rfind("1")
 if pos<1 or pos+7>len(b):raise ValueError("bad bech32")
 hrp=b[:pos]
 try:data=[_CHARSET.index(c) for c in b[pos+1:]]
 except ValueError:raise ValueError("bad bech32 char")
 if _bech32_polymod(_bech32_hrp_expand(hrp)+data)!=1:raise ValueError("bad bech32 checksum")
 return hrp,data[:-6]
def npub_decode(npub):
 s=str(npub or "").strip().lower()
 if len(s)==64 and all(c in "0123456789abcdef" for c in s):return s
 hrp,data=_bech32_decode(s)
 if hrp!="npub":raise ValueError("not an npub")
 raw=bytes(_convertbits(data,5,8,pad=False))
 if len(raw)!=32:raise ValueError("npub must hold 32 bytes")
 return raw.hex()
def _plugin_cfg():
 try:
  d=json.loads((_data_dir()/"config.json").read_text(encoding="utf-8",errors="replace"))
  return d if isinstance(d,dict) else {}
 except Exception:return {}
def allowed_senders():
 raw=[]
 env=str(os.environ.get("GROK_REMOTE_NOSTR_ALLOW") or "")
 raw+=[x for x in env.replace(";",",").split(",")]
 cfg=_plugin_cfg().get("nostr_allow")
 if isinstance(cfg,str):raw+=cfg.replace(";",",").split(",")
 elif isinstance(cfg,list):raw+=[str(x) for x in cfg]
 out=set()
 for x in raw:
  x=str(x or "").strip()
  if not x:continue
  try:out.add(npub_decode(x))
  except Exception:pass
 return out
def npub_encode(pubkey_hex):
 raw=bytes.fromhex(str(pubkey_hex).strip())
 if len(raw)!=32:raise ValueError("pubkey must be 32 bytes")
 return _bech32_create("npub",_convertbits(raw,8,5))
def _priv_pub():
 from cryptography.hazmat.primitives.asymmetric import ec
 from cryptography.hazmat.primitives import serialization
 sk=ec.generate_private_key(ec.SECP256K1())
 priv=sk.private_numbers().private_value.to_bytes(32,"big")
 pub=sk.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.CompressedPoint)
 # nostr x-only: drop 02/03 prefix
 return priv.hex(),pub[1:].hex()
def load_identity():
 path=_key_path()
 if path.is_file():
  try:
   d=json.loads(path.read_text(encoding="utf-8"))
   if d.get("priv") and d.get("pub") and len(d["pub"])==64:
    d["npub"]=d.get("npub") or npub_encode(d["pub"])
    return d
  except Exception:pass
 priv,pub=_priv_pub()
 d={"priv":priv,"pub":pub,"npub":npub_encode(pub),"created":int(time.time())}
 tmp=path.with_name(path.name+".tmp")
 fd=os.open(str(tmp),os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
 with os.fdopen(fd,"w",encoding="utf-8") as f:f.write(json.dumps(d,indent=2))
 os.replace(tmp,path)
 try:os.chmod(path,0o600)
 except Exception:pass
 return d
def default_relays():
 env=str(os.environ.get("GROK_REMOTE_NOSTR_RELAYS") or "").strip()
 if env:return [x.strip() for x in env.split(",") if x.strip().startswith("wss://")]
 return ["wss://relay.damus.io","wss://nos.lol","wss://relay.primal.net"]
def nostr_switch():
 v=str(os.environ.get("GROK_REMOTE_NOSTR") or "1").strip().lower()
 return v not in ("0","false","off","no")
def nostr_enabled():
 return nostr_switch() and bool(allowed_senders())
def _shared_key(priv_hex,pub_hex):
 from cryptography.hazmat.primitives.asymmetric import ec
 from cryptography.hazmat.primitives import serialization
 x=bytes.fromhex(str(pub_hex).strip())
 if len(x)==33 and x[0] in (2,3):
  peer=ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(),x)
 else:
  if len(x)!=32:raise ValueError("bad pub")
  peer=None
  for prefix in (b"\x02",b"\x03"):
   try:
    peer=ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(),prefix+x)
    break
   except Exception:continue
  if peer is None:raise ValueError("bad pub")
 n=int(priv_hex,16)
 sk=ec.derive_private_key(n,ec.SECP256K1())
 return sk.exchange(ec.ECDH(),peer)
def nip04_encrypt(priv_hex,pub_hex,text):
 import base64
 from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
 from cryptography.hazmat.primitives.padding import PKCS7
 key=_shared_key(priv_hex,pub_hex)
 iv=secrets.token_bytes(16)
 padder=PKCS7(128).padder()
 data=padder.update(str(text).encode("utf-8"))+padder.finalize()
 enc=Cipher(algorithms.AES(key),modes.CBC(iv)).encryptor()
 ct=enc.update(data)+enc.finalize()
 return base64.b64encode(ct).decode("ascii")+"?iv="+base64.b64encode(iv).decode("ascii")
def nip04_decrypt(priv_hex,pub_hex,content):
 import base64
 from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
 from cryptography.hazmat.primitives.padding import PKCS7
 raw=str(content or "")
 if "?iv=" not in raw:raise ValueError("no iv")
 ct_b64,iv_b64=raw.split("?iv=",1)
 key=_shared_key(priv_hex,pub_hex)
 ct=base64.b64decode(ct_b64)
 iv=base64.b64decode(iv_b64)
 dec=Cipher(algorithms.AES(key),modes.CBC(iv)).decryptor()
 padded=dec.update(ct)+dec.finalize()
 unpad=PKCS7(128).unpadder()
 return (unpad.update(padded)+unpad.finalize()).decode("utf-8")
def status():
 ident=load_identity()
 return {"ok":True,"enabled":nostr_enabled(),"allowed":len(allowed_senders()),"npub":ident.get("npub") or "","pub":ident.get("pub") or "","relays":default_relays()}
_seen=set()
_inbox={"task":None,"last_err":"","running":False}
def inbox_status():
 st=status()
 st["running"]=bool(_inbox.get("running"))
 st["error"]=_inbox.get("last_err") or ""
 st["dropped"]=int(_inbox.get("dropped") or 0)
 return st
async def _relay_loop(url,ident,on_text):
 from aiohttp import ClientSession,ClientTimeout,WSMsgType
 sub="gr"+secrets.token_hex(4)
 filt={"kinds":[4],"#p":[ident["pub"]],"limit":20}
 try:
  async with ClientSession(timeout=ClientTimeout(total=None,connect=12,sock_connect=12)) as s:
   async with s.ws_connect(url,heartbeat=20,autoping=True,max_msg_size=512*1024) as ws:
    await ws.send_str(json.dumps(["REQ",sub,filt]))
    async for msg in ws:
     if msg.type!=WSMsgType.TEXT:continue
     try:j=json.loads(msg.data)
     except Exception:continue
     if not isinstance(j,list) or not j:continue
     if j[0]!="EVENT" or len(j)<3:continue
     ev=j[2] if isinstance(j[2],dict) else {}
     eid=str(ev.get("id") or "")
     if not eid or eid in _seen:continue
     if int(ev.get("kind") or 0)!=4:continue
     sender=str(ev.get("pubkey") or "").lower()
     if sender==ident["pub"]:continue
     if sender not in allowed_senders():
      _seen.add(eid)
      _inbox["dropped"]=int(_inbox.get("dropped") or 0)+1
      continue
     _seen.add(eid)
     if len(_seen)>400:
      for x in list(_seen)[:200]:_seen.discard(x)
     try:
      text=nip04_decrypt(ident["priv"],ev.get("pubkey") or "",ev.get("content") or "")
     except Exception:
      continue
     text=str(text or "").strip()
     if text:await on_text(text,ev.get("pubkey") or "")
 except asyncio.CancelledError:
  raise
 except Exception as e:
  _inbox["last_err"]=("%s: %s"%(url,e))[:200]
async def run_inbox(on_text):
 if not nostr_enabled():return
 ident=load_identity()
 _inbox["running"]=True
 tasks=[]
 try:
  while True:
   tasks=[asyncio.create_task(_relay_loop(u,ident,on_text)) for u in default_relays()]
   await asyncio.gather(*tasks,return_exceptions=True)
   await asyncio.sleep(8)
 except asyncio.CancelledError:
  for t in tasks:
   t.cancel()
  raise
 finally:
  _inbox["running"]=False
def start_inbox(loop,on_text):
 if not nostr_enabled():return None
 if _inbox.get("task") and not _inbox["task"].done():return _inbox["task"]
 _inbox["task"]=loop.create_task(run_inbox(on_text))
 return _inbox["task"]
def stop_inbox():
 t=_inbox.get("task")
 _inbox["task"]=None
 if t and not t.done():t.cancel()
