import io,os,re,shutil,socket,subprocess,sys
def _probe(target):
 s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
 try:
  s.connect((target,80));return s.getsockname()[0]
 except Exception:return ""
 finally:
  try:s.close()
  except Exception:pass
def _ismesh(ip):
 try:
  a,b=[int(x) for x in ip.split(".")[:2]];return a==100 and 64<=b<=127
 except Exception:return False
def _hostips():
 try:return [r[4][0] for r in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET)]
 except Exception:return []
def _cls(ip,primary,mesh):
 if ip and ip==primary:return("Wi-Fi","Same network as this PC","lan",6)
 if ip and ip==mesh:return("Meshnet","Works anywhere on your Tailscale network","mesh",4)
 try:a,b=[int(x) for x in ip.split(".")[:2]]
 except Exception:return("Other","Unrecognised adapter","other",1)
 if a==127:return("This PC","Only this computer","local",0)
 if a==169 and b==254:return("","","skip",-1)
 if _ismesh(ip):return("Meshnet","Works anywhere on your Tailscale network","mesh",4)
 return("Other","Usually a virtual adapter - try Wi-Fi first","other",1)
def _netinfo(port=2421):
 try:
  from remote_auth import tailscale_snapshot
  return tailscale_snapshot(port) or {}
 except Exception:
  return {}
def addresses(port,key,public_host="",net=None):
 primary=_probe("8.8.8.8");mesh=_probe("100.64.0.1")
 if not _ismesh(mesh):mesh=""
 if net is None:net=_netinfo(port)
 ts=str((net or {}).get("ip") or "")
 if ts and _ismesh(ts) and not mesh:mesh=ts
 seen=set();out=[]
 for ip in [primary,mesh,ts]+_hostips():
  if not ip or ip in seen:continue
  seen.add(ip)
  name,note,kind,rank=_cls(ip,primary,mesh)
  if rank<0:continue
  out.append({"ip":ip,"name":name,"note":note,"kind":kind,"rank":rank,"url":url_for(ip,port,key)})
 dns=str((net or {}).get("dns") or "").strip()
 if dns and (net or {}).get("serve"):
  out.append({"ip":dns,"name":"HTTPS · away","note":"Tailscale HTTPS — Home Screen app + off-LAN. Same tailnet on PC and phone.","kind":"https","rank":5,"url":url_for(dns,443,key,https=True)})
 raw_pub=public_host or str((net or {}).get("public") or (net or {}).get("public_url") or "")
 pe=public_entry(raw_pub,port,key)
 if pe and pe["ip"] not in seen and pe["url"] not in [x.get("url") for x in out]:
  out.append(pe)
 out.sort(key=lambda d:-d["rank"])
 return out
def url_for(host,port,key,https=False):
 q=("?key=%s&auto=1"%key) if key else "?auto=1"
 if https:
  if int(port or 443) in (443,80,0):
   return "https://%s/%s"%(host,q)
  return "https://%s:%d/%s"%(host,int(port),q)
 return "http://%s:%d/%s"%(host,port,q)
def public_entry(raw,port,key):
 try:
  from public_net import parse_public_origin,pair_token
  p=parse_public_origin(raw,default_port=port)
 except Exception:
  p=None
 if not p:return None
 if p.get("kind")=="pub" or p.get("https"):
  tok=pair_token(key) if key else ""
  q=("?t=%s&auto=1"%tok) if tok else "?auto=1"
  url="%s/%s"%(p["origin"],q)
  return {"ip":p["host"],"name":"Internet","note":"HTTPS · Cloudflare or open 443. Phone asks for the Away PIN on this page — the link does not carry the pairing key.","kind":"pub","rank":8,"url":url}
 return {"ip":p["host"],"name":"Internet","note":"Needs port %d forwarded on your router"%p["port"],"kind":"wan","rank":3,"url":url_for(p["host"],p["port"],key)}
_SEGNO={"tried":False,"ok":False}
def ensure_segno():
 try:
  import segno;return True
 except ImportError:pass
 if _SEGNO["tried"]:return _SEGNO["ok"]
 _SEGNO.update(tried=True,ok=bool(shutil.which("qrencode")))
 if _SEGNO["ok"] or str(os.environ.get("GROK_REMOTE_NO_PIP") or "")=="1":return _SEGNO["ok"]
 try:
  subprocess.run([sys.executable,"-m","pip","install","-q","segno"],timeout=60,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  import importlib;importlib.invalidate_caches();import segno;_SEGNO["ok"]=True;return True
 except Exception:return False
def _qrencode(url,*fmt):
 q=shutil.which("qrencode")
 try:return subprocess.run([q,"-l","M","-m","4",*fmt,"-o","-",url],capture_output=True,timeout=10).stdout.decode("utf-8","replace") if q else ""
 except Exception:return ""
def qr_svg(url,scale=8):
 try:
  import segno
  b=io.BytesIO();segno.make(url,error="m").save(b,kind="svg",scale=scale,border=4,dark="#000000",light="#ffffff");s=b.getvalue().decode("utf-8")
 except ImportError:s=_qrencode(url,"-t","SVG","-s",str(scale))
 except Exception:return ""
 try:
  s=re.sub(r'<!--.*?-->',"",re.sub(r'<\?xml[^>]*\?>',"",s,count=1),flags=re.S).replace('preserveAspectRatio="none"',"").strip()
  m=re.search(r'\bwidth="(\d+(?:\.\d+)?)"[^>]*\bheight="(\d+(?:\.\d+)?)"',s)
  s=s.replace("<svg ","<svg viewBox=\"0 0 %s %s\" preserveAspectRatio=\"xMidYMid meet\" "%(m.group(1),m.group(2)),1) if m and "viewBox" not in s else s.replace("<svg ","<svg preserveAspectRatio=\"xMidYMid meet\" ",1) if "preserveAspectRatio" not in s else s
  return s if "<svg" in s else ""
 except Exception:return ""
def qr_terminal(url,out=None):
 try:
  import segno
  segno.make(url,error="m").terminal(out=out or sys.stdout,compact=True);return True
 except ImportError:
  t=_qrencode(url,"-t","UTF8");(out or sys.stdout).write(t);return bool(t)
 except Exception:return False
def utf8_stdout():
 for s in (sys.stdout,sys.stderr):
  try:s.reconfigure(encoding="utf-8")
  except Exception:pass
_CSS="""*{box-sizing:border-box}:root{--bg:#FBFAF8;--card:#fff;--ink:#1a1720;--dim:#6b6574;--line:#E7E3DB;--accent:#5A48B0}
@media(prefers-color-scheme:dark){:root{--bg:#0A0B0E;--card:#161a22;--ink:#eef1f6;--dim:#9aa3b2;--line:#2a3140;--accent:#A88FE8}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;padding:28px 18px 60px}
.wrap{max-width:940px;margin:0 auto}h1{font-size:1.5rem;margin:0 0 4px;letter-spacing:-.02em}
.sub{color:var(--dim);margin:0 0 26px}
.grid{display:grid;gap:18px;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px;display:flex;flex-direction:column;gap:12px;overflow:visible}
.card.best{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 18%,transparent)}
.hd{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.nm{font-weight:650;font-size:1.05rem}.tag{font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;color:#fff;background:var(--accent);padding:2px 7px;border-radius:99px}
.note{color:var(--dim);font-size:.85rem;margin:-6px 0 0}
.qr{background:#fff;border-radius:16px;padding:18px;display:flex;justify-content:center;align-items:center;overflow:visible}.qr svg{width:min(280px,100%);height:auto;aspect-ratio:1/1;max-width:100%;display:block}
.u{font:12px ui-monospace,Consolas,monospace;color:var(--dim);word-break:break-all;background:var(--bg);border:1px solid var(--line);border-radius:9px;padding:8px}
button{font:inherit;font-size:.9rem;padding:9px 12px;border-radius:9px;border:1px solid var(--line);background:var(--bg);color:var(--ink);cursor:pointer}
button:hover{border-color:var(--accent)}button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.steps{margin:34px 0 0;padding:18px 20px;background:var(--card);border:1px solid var(--line);border-radius:16px}
.steps h2{font-size:.78rem;text-transform:uppercase;letter-spacing:.1em;color:var(--dim);margin:0 0 10px}
.steps ol{margin:0;padding-left:20px}.steps li{margin:5px 0}
.here{margin:26px 0 0;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.here a{display:inline-block;padding:11px 16px;border-radius:10px;background:var(--accent);color:#fff;text-decoration:none;font-weight:600}
.here a:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.here span{color:var(--dim);font-size:.9rem}
.more{margin:22px 0 0}.more summary{cursor:pointer;color:var(--dim);font-size:.9rem;padding:8px 0}
.more summary:hover{color:var(--ink)}.more .grid{margin-top:14px}
.none{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px}
code{font:13px ui-monospace,Consolas,monospace;background:var(--bg);padding:2px 5px;border-radius:5px;border:1px solid var(--line)}
.serve{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:12px}
.serve button{background:var(--accent);color:#fff;border-color:var(--accent);font-weight:650}
.serve .st{color:var(--dim);font-size:.85rem}"""
def banner(addrs,port,have_qr=True):
 best=addrs[0] if addrs else None
 print("")
 if not best:
  print("  No network address found - connect this PC to Wi-Fi or Ethernet.");print("");return
 print("  SCAN WITH YOUR PHONE CAMERA   (%s - %s)"%(best["name"],best["note"]))
 print("")
 if not(have_qr and qr_terminal(best["url"])):print("  (QR unavailable - type the link below on your phone)")
 print("")
 print("  %s"%best["url"])
 print("")
 for x in addrs[1:]:
  if x["kind"]!="local":print("  %-10s %s"%(x["name"]+":",x["url"]))
 print("")
 print("  All codes / help:  http://127.0.0.1:%d/pair"%port)
 print("")
def _cli():
 import argparse,json
 ap=argparse.ArgumentParser()
 ap.add_argument("--port",type=int,default=2421);ap.add_argument("--key",default="")
 ap.add_argument("--public-host",default="");ap.add_argument("--json",action="store_true")
 a=ap.parse_args()
 utf8_stdout()
 addrs=addresses(a.port,a.key,public_host=a.public_host)
 if a.json:print(json.dumps(addrs));return
 banner(addrs,a.port,have_qr=ensure_segno())
def _esc(s):
 return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")
def _card(a,best=False,have_qr=True):
 svg=qr_svg(a["url"]) if have_qr else ""
 qr=('<div class="qr">%s</div>'%svg) if svg else '<div class="u">QR unavailable - open the link below by hand</div>'
 return '<div class="card%s"><div class="hd"><span class="nm">%s</span>%s</div><p class="note">%s</p>%s<div class="u">%s</div><button data-u="%s">Copy link</button></div>'%(
  " best" if best else "",_esc(a["name"]),'<span class="tag">Start here</span>' if best else "",_esc(a["note"]),qr,_esc(a["url"]),_esc(a["url"]))
def page(addrs,cwd="",have_qr=True,port=2421,net=None,pin="",npub=""):
 shown=[a for a in addrs if a["kind"] not in("local","other")]
 extra=[a for a in addrs if a["kind"]=="other"]
 if not shown and extra:shown,extra=extra,[]
 cards="".join(_card(a,best=(i==0),have_qr=have_qr) for i,a in enumerate(shown))
 body=('<div class="grid">%s</div>'%cards) if cards else '<div class="none">No network address found. Connect this PC to Wi-Fi or Ethernet, then reload.</div>'
 if extra:
  body+='<details class="more"><summary>Other network adapters (%d) - only if the ones above fail</summary><div class="grid">%s</div></details>'%(
   len(extra),"".join(_card(a,have_qr=have_qr) for a in extra))
 net=net or {}
 serve_on=bool(net.get("serve") and net.get("dns"))
 serve_lab="HTTPS is on — scan the HTTPS · away code, then Add to Home Screen." if serve_on else ("Tailscale is on this PC. Enable HTTPS so the phone gets https://%s (needed for a full Home Screen app off-LAN)."%_esc(net.get("dns") or "your-pc.ts.net") if net.get("ok") or net.get("ip") or net.get("dns") else "Install Tailscale on this PC and the phone (same tailnet). Then enable HTTPS here.")
 serve_btn="" if serve_on else "<button type=button id=btnServe>Enable Tailscale HTTPS</button>"
 pin_html=("<p class=st>Away PIN (phone asks once; the Internet link does not contain the pairing key): <code id=awayPin>%s</code></p>"%_esc(pin)) if pin else ""
 npub_html=("<div class=steps id=nostr><h2>Nostr text inbox</h2><ol>"
  "<li>Send a NIP-04 encrypted DM to this npub. Relays see ciphertext, not the prompt.</li>"
  "<li>Only senders on the allowlist are accepted. It lands in its own <b>Nostr inbox</b> chat on this PC. npub is not shown on the public HTTPS page.</li>"
  "</ol><div class=u id=nostrNpub>%s</div><button data-u=\"%s\">Copy npub</button></div>"%(_esc(npub),_esc(npub))) if npub else ""
 return ("<!doctype html><html><head><meta charset=utf-8><meta name=viewport content=\"width=device-width,initial-scale=1\">"
  "<title>Pair your phone - Grok Remote</title><style>%s</style></head><body><div class=wrap>"
  "<h1>Point your phone camera at a code</h1>"
  "<p class=sub>Tap the link it shows. That is the whole setup - the key is inside the code, so there is nothing to type.%s</p>"
  "%s"
  "<div class=here><a href=\"http://127.0.0.1:%d/?auto=1\">Open it on this computer instead</a><span>No phone needed - runs right here.</span></div>"
  "<div class=steps id=home><h2>Add to Home Screen</h2><ol>"
  "<li>Open the paired link on the phone (scan a code above).</li>"
  "<li><b>iPhone / iPad:</b> Share → Add to Home Screen. No App Store.</li>"
  "<li><b>Android:</b> Chrome menu → Install app or Add to Home Screen.</li>"
  "<li>Wi-Fi HTTP still pins to the Home Screen. A full installable PWA (service worker) needs the HTTPS link below.</li>"
  "</ol></div>"
  "<div class=steps id=away><h2>Away from home</h2><ol>"
  "<li><b>Internet:</b> Cloudflare tunnel or open 443. Scan the <b>Internet</b> code. The phone asks for the Away PIN shown on this PC. Cellular works.</li>"
  "<li>Save a hostname below, or start a Cloudflare quick tunnel from this PC (needs <code>cloudflared</code>).</li>"
  "<li>Or send text as a Nostr DM to the inbox below — no public hostname required.</li>"
  "<li>Or use <b>Meshnet / Tailscale</b> if both devices are on the same tailnet — no open ports.</li>"
  "<li>Do not use Tailscale Funnel. Cloudflare named tunnels stay on your account; quick tunnels are temporary <code>trycloudflare.com</code> links.</li>"
  "</ol>"
  "%s"
  "<div class=serve style=\"flex-direction:column;align-items:stretch\">"
  "<input id=publicHost placeholder=\"https://your-hostname.example\" autocomplete=off style=\"font:13px ui-monospace,Consolas,monospace;padding:8px;border-radius:9px;border:1px solid var(--line);background:var(--bg);color:var(--ink)\">"
  "<div style=\"display:flex;gap:10px;flex-wrap:wrap\">"
  "<button type=button id=btnSavePublic>Save public URL</button>"
  "<button type=button id=btnCfTunnel>Start Cloudflare tunnel</button>"
  "%s</div><p class=st id=serveSt>%s</p></div></div>"
  "%s"
  "<div class=steps><h2>If the camera does not work</h2><ol>"
  "<li>Open your phone browser and type the link printed under a code.</li>"
  "<li>Use <b>Wi-Fi</b> when the phone is on the same network as this PC.</li>"
  "<li>Use the <b>Internet</b> code (Cloudflare / 443) when you are away. Meshnet still works if both devices are on Tailscale.</li>"
  "<li>Nothing loads at all? A firewall is likely blocking the hub port - on Windows rerun the launcher and accept the prompt; on Linux or macOS run <code>grok-remote doctor</code> for the exact fix.</li>"
  "</ol></div></div>"
  "<script>document.addEventListener('click',function(e){var b=e.target.closest('button[data-u]');if(!b)return;"
  "navigator.clipboard.writeText(b.dataset.u).then(function(){var t=b.textContent;b.textContent='Copied';setTimeout(function(){b.textContent=t},1400)})});"
  "(function(){var b=document.getElementById('btnServe');if(b)b.onclick=function(){b.disabled=true;var st=document.getElementById('serveSt');if(st)st.textContent='Enabling…';"
  "fetch('/api/net/tailscale-serve',{method:'POST'}).then(function(r){return r.json()}).then(function(j){if(j&&j.ok)location.reload();else{b.disabled=false;if(st)st.textContent=(j&&j.error)||'Could not enable serve';}})"
  ".catch(function(){b.disabled=false;if(st)st.textContent='Could not reach the hub';});};"
  "var inp=document.getElementById('publicHost');var sp=document.getElementById('btnSavePublic');var cf=document.getElementById('btnCfTunnel');"
  "fetch('/api/net',{cache:'no-store'}).then(function(r){return r.json()}).then(function(j){if(!j)return;if(inp&&(j.public_origin||j.public_url))inp.value=j.public_origin||'';var st=document.getElementById('serveSt');if(st&&j.tunnel&&j.tunnel.url)st.textContent='Tunnel '+j.tunnel.url;}).catch(function(){});"
  "if(sp)sp.onclick=function(){var st=document.getElementById('serveSt');sp.disabled=true;if(st)st.textContent='Saving…';"
  "fetch('/api/net/public',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:inp&&inp.value||''})}).then(function(r){return r.json()}).then(function(j){if(j&&j.ok)location.reload();else{sp.disabled=false;if(st)st.textContent=(j&&j.error)||'Could not save';}}).catch(function(){sp.disabled=false;if(st)st.textContent='Could not reach the hub';});};"
  "if(cf)cf.onclick=function(){var st=document.getElementById('serveSt');cf.disabled=true;if(st)st.textContent='Starting cloudflared…';"
  "fetch('/api/net/cloudflare-tunnel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'start'})}).then(function(r){return r.json()}).then(function(j){if(j&&j.ok)location.reload();else{cf.disabled=false;if(st)st.textContent=(j&&j.error)||'cloudflared failed';}}).catch(function(){cf.disabled=false;if(st)st.textContent='Could not reach the hub';});};"
  "})();</script>"
  "</body></html>")%(_CSS," Working folder: <code>%s</code>"%_esc(cwd) if cwd else "",body,port,pin_html,serve_btn,serve_lab,npub_html)

if __name__=="__main__":_cli()
