#!/usr/bin/env python3
import argparse,ipaddress,json,os,re,shlex,shutil,signal,socket,subprocess,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
APP="grok-remote"
HOME=Path.home()
WIN=os.name=="nt"
MAC=sys.platform=="darwin"
DATA=Path(os.environ.get("GROK_PLUGIN_DATA") or HOME/".grok"/"plugin-data"/APP)
XDG_DATA=Path(os.environ.get("XDG_DATA_HOME") or HOME/".local"/"share")
XDG_CFG=Path(os.environ.get("XDG_CONFIG_HOME") or HOME/".config")
UNITS=XDG_CFG/"systemd"/"user"
BIN=HOME/".local"/"bin"
DESKTOP_FILE=XDG_DATA/"applications"/(APP+".desktop")
LAUNCH_AGENT=HOME/"Library"/"LaunchAgents"/"com.amnibro.grok-remote.plist"
DEFAULTS={"autostart":False,"autostart_on_session":True,"autostart_on_boot":False,"cwd":"","ui_port":2421,"agent_port":2419,"always_approve":True,"leader":True}
CHROMIUMS=("google-chrome-stable","google-chrome","chromium","chromium-browser","brave","brave-browser","microsoft-edge-stable","microsoft-edge","vivaldi-stable","vivaldi")
TASK_WIDGETS=("org.kde.plasma.icontasks","org.kde.plasma.taskmanager")
def cfg_load():
 c=dict(DEFAULTS)
 for p in (ROOT/"config.default.json",DATA/"config.json"):
  try:c.update(json.loads(p.read_text(encoding="utf-8-sig")))
  except Exception:pass
 return c
def cfg_save(c):
 DATA.mkdir(parents=True,exist_ok=True);p=DATA/"config.json";t=p.with_name(p.name+".tmp")
 t.write_text(json.dumps(c,indent=2),encoding="utf-8");os.replace(t,p)
 return p
def log(m,echo=True):
 d=DATA/"logs";d.mkdir(parents=True,exist_ok=True)
 with open(d/"autostart.log","a",encoding="utf-8") as f:f.write("[%s] %s\n"%(time.strftime("%Y-%m-%d %H:%M:%S"),m))
 echo and print(m)
def port_open(port:int,host="127.0.0.1",timeout=0.2):
 try:
  with socket.create_connection((host,int(port)),timeout=timeout):return True
 except Exception:return False
def _proc_listen_inodes(port:int):
 inodes=set()
 for fn in ("/proc/net/tcp","/proc/net/tcp6"):
  try:
   with open(fn,encoding="ascii",errors="replace") as f:
    next(f,None)
    for line in f:
     parts=line.split()
     ok=len(parts)>=10 and parts[3]=="0A" and parts[9]!="0" and int(parts[1].rsplit(":",1)[1],16)==port
     ok and inodes.add(parts[9])
  except Exception:pass
 return inodes
def _proc_pids_for_inodes(inodes):
 pids=set()
 if not inodes:return pids
 want={"socket:[%s]"%i for i in inodes}
 try:names=[d for d in os.listdir("/proc") if d.isdigit()]
 except Exception:return pids
 for d in names:
  try:fds=os.listdir("/proc/%s/fd"%d)
  except OSError:continue
  for fd in fds:
   try:
    if os.readlink("/proc/%s/fd/%s"%(d,fd)) in want:pids.add(int(d));break
   except OSError:continue
 return pids
def listen_pids_port(port:int,exclude_self=True):
 pids=set();port=int(port)
 try:
  if WIN:
   out=subprocess.run(["netstat","-ano"],capture_output=True,text=True,timeout=8,encoding="utf-8",errors="replace").stdout or ""
   for line in out.splitlines():
    parts=line.split()
    try:
     if "LISTENING" in line and len(parts)>=5 and int(parts[1].rsplit(":",1)[1])==port:pids.add(int(parts[-1]))
    except Exception:continue
  elif os.path.isdir("/proc/net"):
   inodes=_proc_listen_inodes(port);pids=_proc_pids_for_inodes(inodes)
   if inodes and not pids and shutil.which("ss"):
    out=subprocess.run(["ss","-ltnpH","sport = :%d"%port],capture_output=True,text=True,timeout=5,encoding="utf-8",errors="replace").stdout or ""
    pids={int(x) for x in re.findall(r"pid=(\d+)",out)}
  elif shutil.which("lsof"):
   out=subprocess.run(["lsof","-nP","-iTCP:%d"%port,"-sTCP:LISTEN","-t"],capture_output=True,text=True,timeout=5,encoding="utf-8",errors="replace").stdout or ""
   pids={int(x) for x in out.split() if x.strip().isdigit()}
 except Exception:pass
 exclude_self and pids.discard(os.getpid())
 return sorted(p for p in pids if p>0)
def cmdline(pid):
 try:return Path("/proc/%d/cmdline"%pid).read_bytes().replace(b"\0",b" ").decode("utf-8","replace")
 except Exception:pass
 try:return subprocess.run(["ps","-o","command=","-p",str(pid)],capture_output=True,text=True,timeout=3).stdout.strip()
 except Exception:return ""
def health(port,timeout=4):
 try:
  with urllib.request.urlopen("http://127.0.0.1:%d/health"%int(port),timeout=timeout) as r:return json.loads(r.read().decode("utf-8","replace") or "{}")
 except Exception:return None
def has_systemd():
 return sys.platform.startswith("linux") and bool(shutil.which("systemctl")) and Path("/run/user/%d/systemd"%os.getuid()).is_dir()
def unit_name():
 for n in (APP+".service","amni-"+APP+".service"):
  if (UNITS/n).is_file():return n
 return ""
def systemctl(*a,check=False):
 r=subprocess.run(["systemctl","--user",*a],capture_output=True,text=True,timeout=30)
 return r.returncode==0 if not check else r
def unit_active(u):
 return bool(u) and has_systemd() and systemctl("is-active","--quiet",u)
def secret():
 s=(os.environ.get("GROK_AGENT_SECRET") or "").strip()
 f=ROOT/".ui-secret"
 return s or (f.read_text(encoding="utf-8",errors="replace").strip() if f.is_file() else "")
def hook_event():
 try:
  raw="" if sys.stdin is None or sys.stdin.isatty() else sys.stdin.read()
  ev=json.loads(raw) if raw.strip() else {}
  return ev if isinstance(ev,dict) else {}
 except Exception:return {}
def workspace(explicit="",cfg=None,ev=None):
 cfg=cfg or cfg_load();ev=ev or {};pwd=os.getcwd()
 own={str(ROOT),str(ROOT/"scripts"),str(ROOT/"desktop-tauri")}
 cands=[explicit,cfg.get("cwd"),ev.get("cwd"),ev.get("workspaceRoot"),os.environ.get("GROK_PROJECT_DIR"),os.environ.get("GROK_REMOTE_CWD"),"" if pwd in own or pwd==str(HOME) else pwd,str(HOME/"ai"),str(HOME/"Documents"/"ai"),str(HOME)]
 return next(str(Path(c).expanduser()) for c in cands if c and Path(str(c)).expanduser().is_dir())
def ui_url(port,lan=False):
 rc={}
 try:rc=json.loads((ROOT/"runtime-config.json").read_text(encoding="utf-8"))
 except Exception:pass
 cu=(ROOT/"connect.url").read_text(encoding="utf-8",errors="replace").strip() if (ROOT/"connect.url").is_file() else ""
 k=secret()
 local="http://127.0.0.1:%d/?auto=1%s"%(int(port),"&key="+k if k else "")
 return (cu or rc.get("ui") or local) if lan else local
def ps1(name,*args):
 sh=shutil.which("powershell") or shutil.which("pwsh")
 if not sh:sys.exit("PowerShell not found")
 return subprocess.run([sh,"-NoProfile","-ExecutionPolicy","Bypass","-File",str(ROOT/"scripts"/name),*args]).returncode
def spawn_hub(cfg,cwd):
 DATA.joinpath("logs").mkdir(parents=True,exist_ok=True)
 out=open(DATA/"logs"/"hub.log","ab")
 argv=["sh",str(ROOT/"start.sh"),"--port",str(cfg["ui_port"]),"--agent-port",str(cfg["agent_port"]),"--cwd",cwd,"--ensure-agent"]
 env=dict(os.environ,GROK_PROJECT_DIR=cwd,PATH=os.pathsep.join([str(HOME/".grok"/"bin"),os.environ.get("PATH","")]))
 return subprocess.Popen(argv,cwd=str(ROOT),env=env,stdout=out,stderr=out,stdin=subprocess.DEVNULL,start_new_session=True)
def wait_up(port,secs):
 t=time.time()
 while time.time()-t<secs:
  if port_open(port,timeout=0.3):return True
  time.sleep(0.25)
 return False
def cmd_start(o):
 if WIN:return ps1("ensure-running.ps1",*(["-Force","-IgnoreConfig"] if o.force else []),"-Reason",o.reason,*(["-Cwd",o.cwd] if o.cwd else []))
 cfg=cfg_load();ev=hook_event() if o.reason=="session" else {}
 skip="autostart=false" if not o.force and not cfg.get("autostart") else ("autostart_on_session=false" if not o.force and o.reason=="session" and cfg.get("autostart_on_session") is False else "")
 if skip:return log("skip (%s): %s"%(o.reason,skip),echo=not o.quiet) or 0
 port=int(cfg["ui_port"])
 if port_open(port):return log("ok (%s): already listening on :%d"%(o.reason,port),echo=not o.quiet) or 0
 u=unit_name()
 if u and has_systemd() and systemctl("start",u):
  log("started %s (%s)"%(u,o.reason),echo=not o.quiet)
  return 0 if not o.wait or wait_up(port,o.wait) else 1
 lock=None
 try:
  import fcntl
  lock=open(DATA/"start.lock","a");fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:return log("start already in progress (%s)"%o.reason,echo=not o.quiet) or 0
 except Exception:pass
 cwd=workspace(o.cwd,cfg,ev);p=spawn_hub(cfg,cwd)
 log("spawned hub pid=%d (%s) cwd=%s ui=%d log=%s"%(p.pid,o.reason,cwd,port,DATA/"logs"/"hub.log"),echo=not o.quiet)
 return 0 if not o.wait or wait_up(port,o.wait) else (print("hub did not open :%d within %ss, see %s"%(port,o.wait,DATA/"logs"/"hub.log")) or 1)
def kill(pids,grace=3.0):
 for sig in (signal.SIGTERM,signal.SIGKILL):
  for p in pids:
   try:os.kill(p,sig)
   except (ProcessLookupError,PermissionError):pass
  t=time.time()
  while time.time()-t<grace and any(Path("/proc/%d"%p).exists() and "Z" not in (Path("/proc/%d/stat"%p).read_text(errors="replace").rsplit(")",1)[-1][:3]) for p in pids if Path("/proc/%d/stat"%p).exists()):time.sleep(0.1)
def cmd_stop(o):
 if WIN:return ps1("stop-remote.ps1",*(["-KeepAgent"] if o.keep_agent else []))
 cfg=cfg_load();u=unit_name()
 if unit_active(u):systemctl("stop",u);print("stopped %s"%u)
 ui=[p for p in listen_pids_port(cfg["ui_port"]) if "server.py" in cmdline(p)]
 ag=[] if o.keep_agent else [p for p in listen_pids_port(cfg["agent_port"]) if re.search(r"\bagent\b.*\bserve\b",cmdline(p))]
 kill(ui+ag)
 print("stopped ui=%s agent=%s"%(ui or "-",ag or ("kept" if o.keep_agent else "-")))
 left=listen_pids_port(cfg["ui_port"])
 left and print("still listening on :%d -> %s (not a grok-remote hub, left alone)"%(cfg["ui_port"],left))
 return 0
def cmd_restart(o):
 u=unit_name()
 if unit_active(u):return 0 if systemctl("restart",u) else 1
 o.keep_agent=True;cmd_stop(o);time.sleep(0.6);o.force=True;o.reason="restart"
 return cmd_start(o)
def cmd_status(o):
 cfg=cfg_load();port=int(cfg["ui_port"]);h=health(port);u=unit_name()
 st={"ui_port":port,"listening":port_open(port),"health":h,"agent_port":cfg["agent_port"],"agent_listening":port_open(cfg["agent_port"]),"unit":u or None,"unit_active":unit_active(u) if u else None,"config":str(DATA/"config.json"),"autostart":cfg.get("autostart"),"autostart_on_boot":cfg.get("autostart_on_boot"),"cwd":cfg.get("cwd") or workspace("",cfg),"installed":DESKTOP_FILE.is_file() if not WIN else None,"pinned":pinned() if not WIN else None}
 print(json.dumps(st,indent=2) if o.json else "\n".join("%-18s %s"%(k,v if not isinstance(v,dict) else "ok" if v.get("ok") else v) for k,v in st.items()))
 return 0 if st["listening"] else 3
def cmd_url(o):
 cfg=cfg_load();u=ui_url(cfg["ui_port"],lan=not o.local);print(u)
 o.qr and shutil.which("qrencode") and subprocess.run(["qrencode","-t","ansiutf8",u])
 return 0
def desktop_app():
 for p in (BIN/"grok-remote-desktop",ROOT/"desktop-tauri"/"src-tauri"/"target"/"release"/"grok-remote-desktop",Path("/usr/bin/grok-remote-desktop")):
  if p.is_file() and os.access(p,os.X_OK):return p
 return None
def browser_argv(url):
 b=next((shutil.which(x) for x in CHROMIUMS if shutil.which(x)),None)
 return [b,"--app="+url,"--class="+APP,"--user-data-dir="+str(DATA/"browser"),"--no-first-run","--no-default-browser-check"] if b else [shutil.which("xdg-open") or "open",url]
def cmd_open(o):
 cfg=cfg_load();port=int(cfg["ui_port"]);app=None if o.browser else desktop_app()
 if WIN:return ps1("open-remote-ui.ps1")
 if app:return subprocess.Popen([str(app)],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL) and 0
 if not port_open(port):
  o.force=True;o.reason="open";o.cwd=o.cwd or "";o.wait=25;o.quiet=True
  if cmd_start(o):return 1
 subprocess.Popen(browser_argv(ui_url(port)+"&desktop=1"),start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 return 0
def icon_src():
 return next((p for p in (ROOT/"web"/"icon-512.png",ROOT/"desktop-tauri"/"src-tauri"/"icons"/"128x128.png",ROOT/"web"/"icon-192.png") if p.is_file()),None)
def desktop_entry():
 py=shlex.quote(sys.executable);ctl=shlex.quote(str(ROOT/"grok_remote_ctl.py"))
 app=desktop_app()
 ex=shlex.quote(str(app)) if app else "%s %s open"%(py,ctl)
 wm="grok-remote-desktop" if app else APP
 return "\n".join(["[Desktop Entry]","Type=Application","Name=Grok Remote","GenericName=Agent cockpit","Comment=Drive Grok Build from this desktop, your phone or a browser","Exec="+ex,"Icon="+APP,"Terminal=false","Categories=Development;Network;RemoteAccess;","Keywords=grok;agent;remote;ai;companion;","StartupNotify=true","StartupWMClass="+wm,"Actions=stop;restart;browser;","","[Desktop Action stop]","Name=Stop hub","Exec=%s %s stop"%(py,ctl),"","[Desktop Action restart]","Name=Restart hub","Exec=%s %s restart"%(py,ctl),"","[Desktop Action browser]","Name=Open in browser","Exec=%s %s open --browser"%(py,ctl),""])
def kde_eval(js):
 q=shutil.which("qdbus6") or shutil.which("qdbus")
 if not q or "KDE" not in os.environ.get("XDG_CURRENT_DESKTOP",""):return None
 r=subprocess.run([q,"org.kde.plasmashell","/PlasmaShell","org.kde.PlasmaShell.evaluateScript",js],capture_output=True,text=True,timeout=15)
 return r.stdout.strip() if r.returncode==0 else None
def kde_launchers_js(op):
 return 'var a="applications:%s.desktop",o=[];panels().forEach(function(p){p.widgets().forEach(function(w){if(%s.indexOf(w.type)<0)return;w.currentConfigGroup=["General"];var l=String(w.readConfig("launchers","")||"").split(",").filter(function(x){return x});var has=l.indexOf(a)>=0;if("%s"=="add"&&!has){l.push(a);w.writeConfig("launchers",l.join(","));w.reloadConfig()}if("%s"=="del"&&has){l.splice(l.indexOf(a),1);w.writeConfig("launchers",l.join(","));w.reloadConfig()}o.push(has?"1":"0")})});print(o.join(""))'%(APP,json.dumps(list(TASK_WIDGETS)),op,op)
def gnome_favs(key="org.gnome.shell"):
 if not shutil.which("gsettings"):return None
 r=subprocess.run(["gsettings","get",key,"favorite-apps"],capture_output=True,text=True)
 try:return json.loads(r.stdout.strip().replace("@as ","").replace("'",'"')) if r.returncode==0 else None
 except Exception:return None
def desktop_kind():
 d=os.environ.get("XDG_CURRENT_DESKTOP","").upper()
 return "kde" if "KDE" in d else "gnome" if any(x in d for x in ("GNOME","UNITY","UBUNTU","POP")) else "cinnamon" if "CINNAMON" in d else "other"
def pinned():
 k=desktop_kind();me=APP+".desktop"
 if k=="kde":
  r=kde_eval(kde_launchers_js("get"));return None if r is None else "1" in r
 f=gnome_favs("org.cinnamon" if k=="cinnamon" else "org.gnome.shell") if k in ("gnome","cinnamon") else None
 return None if f is None else any(x.endswith(me) for x in f)
def pin(on=True):
 k=desktop_kind();me=APP+".desktop"
 if k=="kde":
  r=kde_eval(kde_launchers_js("add" if on else "del"))
  return (r is not None and bool(r),"KDE Plasma task manager" if r else "no Plasma task manager found (right-click Grok Remote in the app menu -> Pin to Task Manager)")
 if k in ("gnome","cinnamon"):
  key="org.cinnamon" if k=="cinnamon" else "org.gnome.shell";f=gnome_favs(key)
  if f is None:return (False,"gsettings unavailable")
  f=[x for x in f if not x.endswith(me)]+([me] if on else [])
  ok=subprocess.run(["gsettings","set",key,"favorite-apps",str(f)],capture_output=True).returncode==0
  return (ok,"%s favorites"%k.title())
 return (False,"this desktop has no scripted pin; open your app menu, find Grok Remote and add it to your panel/dock")
def refresh_menus():
 for c in (["update-desktop-database",str(DESKTOP_FILE.parent)],["kbuildsycoca6"],["kbuildsycoca5"],["xdg-desktop-menu","forceupdate"],["gtk-update-icon-cache","-q","-t",str(XDG_DATA/"icons"/"hicolor")]):
  shutil.which(c[0]) and subprocess.run(c,capture_output=True,timeout=60)
def install_icons():
 src=icon_src()
 if not src:return
 for sz in ("512x512","256x256","128x128"):
  d=XDG_DATA/"icons"/"hicolor"/sz/"apps";d.mkdir(parents=True,exist_ok=True)
  shutil.which("magick") and sz!="512x512" and subprocess.run(["magick",str(src),"-resize",sz,str(d/(APP+".png"))],capture_output=True).returncode==0 or shutil.copyfile(src,d/(APP+".png"))
def install_cli():
 BIN.mkdir(parents=True,exist_ok=True);l=BIN/APP
 if l.is_symlink() or l.exists():l.unlink()
 l.symlink_to(ROOT/"grok_remote_ctl.py");(ROOT/"grok_remote_ctl.py").chmod(0o755)
 return l
def cmd_install(o):
 if WIN:return ps1("install-shortcut.ps1")
 res={"ok":True,"steps":[]}
 if MAC:
  l=install_cli();res["steps"].append("cli: %s"%l)
  res["steps"].append("open with: grok-remote open (pin the browser window to the Dock with right-click > Options > Keep in Dock)")
 else:
  install_icons();DESKTOP_FILE.parent.mkdir(parents=True,exist_ok=True);DESKTOP_FILE.write_text(desktop_entry(),encoding="utf-8");DESKTOP_FILE.chmod(0o755)
  res["steps"].append("menu: %s"%DESKTOP_FILE)
  l=install_cli();res["steps"].append("cli: %s%s"%(l,"" if str(BIN) in os.environ.get("PATH","").split(os.pathsep) else " (add ~/.local/bin to PATH)"))
  refresh_menus()
  if o.pin:
   ok,how=pin(True);res["pinned"]=ok;res["steps"].append(("pinned: " if ok else "pin: ")+how)
 o.autostart and res["steps"].append(autostart("boot",o.cwd))
 res["hint"]=pin_hint()
 print(json.dumps(res,indent=2) if o.json else "\n".join(res["steps"]+["",res["hint"]]))
 return 0
def pin_hint():
 k="mac" if MAC else "win" if WIN else desktop_kind()
 return {"kde":"Grok Remote is in your app launcher. To pin: right-click it -> Pin to Task Manager (or run: grok-remote pin).","gnome":"Grok Remote is in Activities. To pin: right-click it -> Pin to Dash (or run: grok-remote pin).","cinnamon":"Grok Remote is in the Menu. To pin: right-click it -> Add to panel.","mac":"Run grok-remote open, then right-click the Dock icon -> Options -> Keep in Dock.","win":"Start Menu -> Grok Remote, right-click -> Pin to Start / More -> Pin to taskbar."}.get(k,"Grok Remote is in your app menu; right-click it to add it to your panel or dock.")
def cmd_uninstall(o):
 if WIN:return ps1("install-autostart.ps1","-Disable")
 not MAC and pinned() and pin(False)
 for p in [DESKTOP_FILE]+[XDG_DATA/"icons"/"hicolor"/s/"apps"/(APP+".png") for s in ("512x512","256x256","128x128")]:
  p.is_file() and p.unlink()
 l=BIN/APP;l.is_symlink() and l.resolve()==(ROOT/"grok_remote_ctl.py").resolve() and l.unlink()
 o.autostart and print(autostart("off"))
 refresh_menus();print("removed launcher, icon and cli link%s"%(" and autostart" if o.autostart else " (autostart kept, use: grok-remote autostart off)"))
 return 0
def unit_text(cfg,cwd):
 return "\n".join(["[Unit]","Description=Grok Remote hub (:%d, agent :%d)"%(cfg["ui_port"],cfg["agent_port"]),"After=network-online.target","","[Service]","WorkingDirectory=%s"%ROOT,"Environment=PATH=%s/.grok/bin:%s/.local/bin:/usr/local/bin:/usr/bin:/bin"%(HOME,HOME),"Environment=GROK_PROJECT_DIR=%s"%cwd,"ExecStart=/bin/sh %s --port %d --agent-port %d --cwd %s"%(shlex.quote(str(ROOT/"start.sh")),cfg["ui_port"],cfg["agent_port"],shlex.quote(cwd)),"Restart=on-failure","RestartSec=10","RestartPreventExitStatus=97","KillMode=process","TimeoutStopSec=20","","[Install]","WantedBy=default.target",""])
def plist_text(cfg,cwd):
 args="".join("<string>%s</string>"%x for x in ["/bin/sh",str(ROOT/"start.sh"),"--port",str(cfg["ui_port"]),"--agent-port",str(cfg["agent_port"]),"--cwd",cwd])
 return '<?xml version="1.0" encoding="UTF-8"?>\n<plist version="1.0"><dict><key>Label</key><string>com.amnibro.grok-remote</string><key>ProgramArguments</key><array>%s</array><key>WorkingDirectory</key><string>%s</string><key>RunAtLoad</key><true/><key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict><key>StandardOutPath</key><string>%s</string><key>StandardErrorPath</key><string>%s</string></dict></plist>\n'%(args,ROOT,DATA/"logs"/"hub.log",DATA/"logs"/"hub.log")
def write_session_hook():
 d=HOME/".grok"/"hooks";d.mkdir(parents=True,exist_ok=True)
 cmd="%s %s start --reason session --quiet"%(shlex.quote(sys.executable),shlex.quote(str(ROOT/"grok_remote_ctl.py")))
 (d/"grok-remote-autostart.json").write_text(json.dumps({"hooks":{"SessionStart":[{"hooks":[{"type":"command","command":cmd,"timeout":15}]}]}},indent=2),encoding="utf-8")
 return d/"grok-remote-autostart.json"
def autostart(mode,cwd=""):
 cfg=cfg_load()
 if mode=="off":
  cfg.update(autostart=False,autostart_on_boot=False);cfg_save(cfg)
  u=unit_name();u and has_systemd() and systemctl("disable",u)
  MAC and LAUNCH_AGENT.is_file() and (subprocess.run(["launchctl","unload",str(LAUNCH_AGENT)],capture_output=True),LAUNCH_AGENT.unlink())
  h=HOME/".grok"/"hooks"/"grok-remote-autostart.json";h.is_file() and h.unlink()
  return "autostart off (%s%s)"%(DATA/"config.json",", %s disabled, still running until stop"%u if u else "")
 cfg.update(autostart=True,autostart_on_session=True,autostart_on_boot=mode=="boot")
 cwd and cfg.update(cwd=cwd);cfg["cwd"]=cfg.get("cwd") or workspace("",cfg);cfg_save(cfg)
 out=["autostart on: session hook %s"%write_session_hook()]
 if mode=="boot" and has_systemd():
  u=unit_name() or APP+".service";p=UNITS/u
  if u==APP+".service":UNITS.mkdir(parents=True,exist_ok=True);p.write_text(unit_text(cfg,cfg["cwd"]),encoding="utf-8");systemctl("daemon-reload")
  out.append("login: systemd --user %s %s"%(u,"enabled" if systemctl("enable",u) else "enable FAILED"))
 elif mode=="boot" and MAC:
  LAUNCH_AGENT.parent.mkdir(parents=True,exist_ok=True);LAUNCH_AGENT.write_text(plist_text(cfg,cfg["cwd"]),encoding="utf-8")
  subprocess.run(["launchctl","load","-w",str(LAUNCH_AGENT)],capture_output=True);out.append("login: %s"%LAUNCH_AGENT)
 elif mode=="boot":
  d=XDG_CFG/"autostart";d.mkdir(parents=True,exist_ok=True)
  (d/(APP+".desktop")).write_text("[Desktop Entry]\nType=Application\nName=Grok Remote hub\nExec=%s %s start --force --reason boot --quiet\nX-GNOME-Autostart-enabled=true\nNoDisplay=true\n"%(shlex.quote(sys.executable),shlex.quote(str(ROOT/"grok_remote_ctl.py"))),encoding="utf-8")
  out.append("login: %s"%(d/(APP+".desktop")))
 return "\n".join(out+["cwd: %s"%cfg["cwd"]])
def cmd_autostart(o):
 if WIN:return ps1("install-autostart.ps1",*({"off":["-Disable"],"boot":["-Boot"]}.get(o.mode,[])),*(["-Cwd",o.cwd] if o.cwd else []))
 if o.mode=="status":
  c=cfg_load();u=unit_name()
  print("config   %s\nsession  %s\nboot     %s\nunit     %s\ncwd      %s"%(DATA/"config.json",bool(c.get("autostart") and c.get("autostart_on_session") is not False),bool(c.get("autostart_on_boot")),"%s (%s)"%(u,"enabled" if has_systemd() and systemctl("is-enabled","--quiet",u) else "disabled") if u else "-",c.get("cwd") or "-"))
  return 0
 print(autostart(o.mode,o.cwd));return 0
def cmd_pin(o):
 if WIN or MAC:print(pin_hint());return 0
 DESKTOP_FILE.is_file() or (o.__dict__.update(pin=False,autostart=False,json=False,cwd=""),cmd_install(o))
 ok,how=pin(not o.off);print(("%s: %s"%("unpinned" if o.off else "pinned",how)) if ok else "could not pin automatically, %s\n%s"%(how,pin_hint()))
 return 0 if ok else 2
def which_tts():
 return [x for x in ("piper","espeak-ng","espeak","spd-say","say") if shutil.which(x)]
def cmd_doctor(o):
 cfg=cfg_load();rows=[]
 add=lambda ok,name,detail="",fix="":rows.append((ok,name,detail,fix))
 add(sys.version_info>=(3,10),"python",sys.version.split()[0],"install Python 3.10+")
 try:
  import aiohttp;add(True,"aiohttp",aiohttp.__version__)
 except Exception:
  venv=DATA/"venv"/("Scripts" if WIN else "bin")/("python.exe" if WIN else "python")
  add(venv.is_file(),"aiohttp","not importable by %s%s"%(sys.executable,", venv present" if venv.is_file() else ""),distro_hint("aiohttp"))
 g=shutil.which("grok") or next((str(p) for p in (HOME/".grok"/"bin"/"grok",HOME/".grok"/"bin"/"grok.exe") if p.is_file()),"")
 add(bool(g),"grok cli",g or "missing","install Grok Build: https://x.ai/cli")
 h=health(cfg["ui_port"],timeout=3);add(bool(h and h.get("ok")),"hub :%d"%cfg["ui_port"],"ready" if h and h.get("ready") else "up, agent not ready" if h else "down","grok-remote start")
 add(port_open(cfg["agent_port"]),"agent :%d"%cfg["agent_port"],"listening" if port_open(cfg["agent_port"]) else "down","the hub spawns it; check %s"%(ROOT/"logs"/"agent.spawn.log"))
 fw=firewall_status(int(cfg["ui_port"]));add(fw["lan_allowed"] is not False and fw["mesh_allowed"] is not False,"firewall","%s, phones on %s %s"%(fw["kind"],fw["lan_net"] or "lan","allowed" if fw["lan_allowed"] else "blocked" if fw["lan_allowed"] is False else "unknown"),"grok-remote firewall --open   ("+fw["fix"]+")")
 t=which_tts();add(bool(t) or WIN,"tts (companion voice)",", ".join(t) or ("SAPI" if WIN else "none"),distro_hint("espeak-ng"))
 add(bool(shutil.which("qrencode")),"qrencode","terminal pairing QR",distro_hint("qrencode"))
 not WIN and not MAC and add(DESKTOP_FILE.is_file(),"launcher",str(DESKTOP_FILE) if DESKTOP_FILE.is_file() else "not installed","grok-remote install --pin")
 not WIN and not MAC and add(bool(pinned()),"pinned",desktop_kind(),"grok-remote pin")
 for ok,n,d,f in rows:print("%s %-22s %s%s"%("ok  " if ok else "FIX ",n,d,"" if ok or not f else "   -> "+f))
 return 0 if all(r[0] for r in rows) else 1
def distro_id():
 try:
  t=Path("/etc/os-release").read_text();m=dict(re.findall(r'^(\w+)="?([^"\n]*)"?',t,re.M))
  return (m.get("ID","")+" "+m.get("ID_LIKE","")).lower()
 except Exception:return ""
def distro_hint(pkg):
 d=distro_id()
 py={"aiohttp":"python-aiohttp"}.get(pkg,pkg)
 return ("sudo pacman -S %s"%py) if "arch" in d else ("sudo apt install %s"%("python3-aiohttp" if pkg=="aiohttp" else pkg)) if any(x in d for x in ("debian","ubuntu")) else ("sudo dnf install %s"%("python3-aiohttp" if pkg=="aiohttp" else pkg)) if any(x in d for x in ("fedora","rhel")) else ("sudo zypper install %s"%("python3-aiohttp" if pkg=="aiohttp" else pkg)) if "suse" in d else ("brew install %s"%pkg if MAC else "install %s"%pkg)
def iface_ips():
 out=""
 try:out=subprocess.run(["ip","-o","-4","addr","show"],capture_output=True,text=True,timeout=3).stdout if shutil.which("ip") else ""
 except Exception:pass
 return [(m.group(1),m.group(2),int(m.group(3))) for m in re.finditer(r"^\d+:\s+(\S+)\s+inet\s+([\d.]+)/(\d+)",out,re.M) if m.group(1)!="lo"]
def mesh_ip():
 return next((ip for _,ip,_ in iface_ips() if ipaddress.ip_address(ip) in ipaddress.ip_network("100.64.0.0/10")),"")
def lan_net(lan):
 return next((str(ipaddress.ip_network("%s/%d"%(ip,n),strict=False)) for _,ip,n in iface_ips() if ip==lan),"%s/24"%lan if lan else "")
def _port_in(spec,port):
 return any((int(x.split(":")[0])<=port<=int(x.split(":")[-1])) for x in spec.split(",") if re.fullmatch(r"\d+(:\d+)?",x)) or spec=="any"
def ufw_allows(port,ip,path="/etc/ufw/user.rules"):
 try:rules=Path(path).read_text(errors="replace")
 except Exception:return None
 for m in re.finditer(r"^### tuple ### (allow|limit) (tcp|any) (\S+) \S+ \S+ (\S+) in\b",rules,re.M):
  try:
   if _port_in(m.group(3),port) and ipaddress.ip_address(ip) in ipaddress.ip_network(m.group(4).replace("::/0","0.0.0.0/0"),strict=False):return True
  except ValueError:continue
 return False
def firewall_status(port,lan=""):
 lan=lan or next((ip for _,ip,_ in iface_ips() if not ipaddress.ip_address(ip).is_link_local and ipaddress.ip_address(ip) not in ipaddress.ip_network("100.64.0.0/10")),"")
 mesh=mesh_ip();net=lan_net(lan)
 try:ufw_on=re.search(r"^ENABLED=yes",Path("/etc/ufw/ufw.conf").read_text(),re.M) is not None
 except Exception:ufw_on=False
 if ufw_on:
  pol=re.search(r'^DEFAULT_INPUT_POLICY="?(\w+)',Path("/etc/default/ufw").read_text(errors="replace"),re.M) if Path("/etc/default/ufw").is_file() else None
  closed=(pol.group(1) if pol else "DROP").upper()!="ACCEPT"
  ok_lan=not closed or bool(lan and ufw_allows(port,lan));ok_mesh=not closed or not mesh or bool(ufw_allows(port,mesh))
  fix=" && ".join(([] if ok_lan else ["sudo ufw allow from %s to any port %d proto tcp comment 'Grok Remote, local network'"%(net,port)])+([] if ok_mesh else ["sudo ufw allow from 100.64.0.0/10 to any port %d proto tcp comment 'Grok Remote, meshnet'"%port]))
  return {"kind":"ufw","active":True,"lan_allowed":ok_lan,"mesh_allowed":ok_mesh if mesh else None,"lan_ip":lan,"lan_net":net,"mesh_ip":mesh,"fix":fix}
 if shutil.which("firewall-cmd"):
  r=subprocess.run(["firewall-cmd","--query-port=%d/tcp"%port],capture_output=True,text=True)
  st=r.stdout.strip()
  return {"kind":"firewalld","active":st in ("yes","no"),"lan_allowed":None if st not in ("yes","no") else st=="yes","mesh_allowed":None,"lan_ip":lan,"lan_net":net,"mesh_ip":mesh,"fix":"" if st!="no" else "sudo firewall-cmd --add-port=%d/tcp --permanent && sudo firewall-cmd --reload"%port}
 return {"kind":"none" if not WIN else "windows","active":False,"lan_allowed":None if WIN else True,"mesh_allowed":None,"lan_ip":lan,"lan_net":net,"mesh_ip":mesh,"fix":'netsh advfirewall firewall add rule name="Grok Remote" dir=in action=allow protocol=TCP localport=%d profile=private'%port if WIN else ""}
def cmd_firewall(o):
 cfg=cfg_load();st=firewall_status(int(cfg["ui_port"]))
 print(json.dumps(st,indent=2) if o.json else "firewall  %s%s\nlan       %s (%s) %s\nmeshnet   %s %s"%(st["kind"]," (active)" if st["active"] else "",st["lan_ip"] or "-",st["lan_net"] or "-","reachable" if st["lan_allowed"] else "BLOCKED" if st["lan_allowed"] is False else "unknown",st["mesh_ip"] or "-","" if st["mesh_allowed"] is None else "reachable" if st["mesh_allowed"] else "BLOCKED"))
 if not st["fix"]:return 0
 if not o.open:return print("\nfix: %s\nor run: grok-remote firewall --open"%st["fix"]) or 2
 return subprocess.run(st["fix"],shell=True).returncode
def main(argv=None):
 ap=argparse.ArgumentParser(prog=APP,description="Control the Grok Remote hub on Linux, macOS and Windows")
 sp=ap.add_subparsers(dest="cmd")
 s=sp.add_parser("start",help="start the hub if it is not running");s.add_argument("--cwd",default="");s.add_argument("--force",action="store_true",help="ignore the autostart config");s.add_argument("--reason",default="manual");s.add_argument("--wait",type=float,default=0);s.add_argument("--quiet",action="store_true");s.set_defaults(fn=cmd_start)
 s=sp.add_parser("hook",help="Grok SessionStart hook entry");s.add_argument("--cwd",default="");s.set_defaults(fn=cmd_start,force=False,reason="session",wait=0,quiet=True)
 s=sp.add_parser("stop",help="stop only the remote hub and its agent serve");s.add_argument("--keep-agent",action="store_true");s.set_defaults(fn=cmd_stop)
 s=sp.add_parser("restart",help="restart the hub, keep the agent");s.add_argument("--cwd",default="");s.set_defaults(fn=cmd_restart,wait=20,quiet=False,keep_agent=True)
 s=sp.add_parser("status");s.add_argument("--json",action="store_true");s.set_defaults(fn=cmd_status)
 s=sp.add_parser("url",help="print the phone pairing link");s.add_argument("--local",action="store_true");s.add_argument("--qr",action="store_true");s.set_defaults(fn=cmd_url)
 s=sp.add_parser("open",help="start if needed and open the desktop window");s.add_argument("--browser",action="store_true");s.add_argument("--cwd",default="");s.set_defaults(fn=cmd_open)
 s=sp.add_parser("install",help="add to the app menu (and optionally pin + autostart)");s.add_argument("--pin",action="store_true");s.add_argument("--autostart",action="store_true");s.add_argument("--cwd",default="");s.add_argument("--json",action="store_true");s.set_defaults(fn=cmd_install)
 s=sp.add_parser("uninstall");s.add_argument("--autostart",action="store_true",help="also turn autostart off");s.set_defaults(fn=cmd_uninstall)
 s=sp.add_parser("pin",help="pin the launcher to the taskbar/dock");s.add_argument("--off",action="store_true");s.set_defaults(fn=cmd_pin)
 s=sp.add_parser("autostart");s.add_argument("mode",nargs="?",default="on",choices=["on","off","boot","status"]);s.add_argument("--cwd",default="");s.set_defaults(fn=cmd_autostart)
 s=sp.add_parser("firewall",help="check (and with --open, fix) phone access through the firewall");s.add_argument("--open",action="store_true");s.add_argument("--json",action="store_true");s.set_defaults(fn=cmd_firewall)
 s=sp.add_parser("doctor",help="check python, grok, ports, firewall, tts, launcher");s.set_defaults(fn=cmd_doctor)
 o=ap.parse_args(argv)
 return o.fn(o) if getattr(o,"fn",None) else (ap.print_help() or 0)
if __name__=="__main__":sys.exit(main())
