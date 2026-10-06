import ctypes,json,os,re,shutil,subprocess,sys,time
def _run(cmd,timeout=1.5):
 if not shutil.which(cmd[0]):return ""
 try:p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
 except Exception:return ""
 return p.stdout.strip() if p.returncode==0 else ""
def _exe(pid):
 try:return os.path.basename(os.readlink("/proc/%d/exe"%int(pid)))
 except Exception:return ""
def _win(title,exe,via):return {"title":str(title or "")[:160],"exe":str(exe or ""),"via":via}
def _focused(node):
 if not isinstance(node,dict):return None
 if node.get("focused") and node.get("type") in ("con","floating_con"):return node
 return next((f for f in (_focused(n) for n in (node.get("nodes") or [])+(node.get("floating_nodes") or [])) if f),None)
def _win32_fg():
 import ctypes.wintypes
 u=ctypes.windll.user32;k=ctypes.windll.kernel32
 h=u.GetForegroundWindow()
 if not h:return None
 n=u.GetWindowTextLengthW(h)+1;buf=ctypes.create_unicode_buffer(n);u.GetWindowTextW(h,buf,n)
 pid=ctypes.wintypes.DWORD();u.GetWindowThreadProcessId(h,ctypes.byref(pid));exe=""
 ph=k.OpenProcess(0x1000,False,pid.value)
 if ph:
  try:
   sz=ctypes.wintypes.DWORD(1024);pb=ctypes.create_unicode_buffer(1024)
   if k.QueryFullProcessImageNameW(ph,0,pb,ctypes.byref(sz)):exe=os.path.basename(pb.value)
  finally:k.CloseHandle(ph)
 return _win(buf.value,exe,"win32")
def _kdotool():
 w=_run(["kdotool","getactivewindow"])
 return _win(_run(["kdotool","getwindowname",w]),_exe(_run(["kdotool","getwindowpid",w]) or 0),"kdotool") if w else None
def _hyprctl():
 j=json.loads(_run(["hyprctl","activewindow","-j"]) or "{}")
 return _win(j.get("title"),_exe(j.get("pid") or 0) or j.get("class"),"hyprctl") if j.get("title") else None
def _swaymsg():
 f=_focused(json.loads(_run(["swaymsg","-t","get_tree"]) or "{}"))
 return _win(f.get("name"),_exe(f.get("pid") or 0) or f.get("app_id"),"swaymsg") if f else None
def _xdotool():
 w=_run(["xdotool","getactivewindow"])
 return _win(_run(["xdotool","getwindowname",w]),_exe(_run(["xdotool","getwindowpid",w]) or 0),"xdotool") if w else None
def _linux_backends(env=None):
 e=os.environ if env is None else env;wl=e.get("XDG_SESSION_TYPE")=="wayland" or bool(e.get("WAYLAND_DISPLAY"))
 return [f for f,ok in ((_kdotool,"KDE" in e.get("XDG_CURRENT_DESKTOP","").upper()),(_hyprctl,bool(e.get("HYPRLAND_INSTANCE_SIGNATURE"))),(_swaymsg,bool(e.get("SWAYSOCK"))),(_xdotool,bool(e.get("DISPLAY")) and not wl)) if ok]
def foreground_window():
 fns=[_win32_fg] if sys.platform=="win32" else _linux_backends() if sys.platform.startswith("linux") else []
 for f in fns:
  try:w=f()
  except Exception:w=None
  if w and w["title"]:return w
 return {"title":"","exe":"","via":""}
def _idle_win32():
 class LII(ctypes.Structure):_fields_=[("cbSize",ctypes.c_uint),("dwTime",ctypes.c_uint)]
 li=LII();li.cbSize=ctypes.sizeof(LII)
 return max(0,(ctypes.windll.kernel32.GetTickCount()-li.dwTime)/1000.0) if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li)) else None
def _num(s):
 m=re.search(r"(\d+)",re.sub(r"u?int\d+","",s or ""))
 return int(m.group(1)) if m else None
def _idle_linux():
 ss=_run(["qdbus6","org.freedesktop.ScreenSaver","/org/freedesktop/ScreenSaver","org.freedesktop.ScreenSaver.GetSessionIdleTime"]) or _run(["gdbus","call","--session","--dest","org.freedesktop.ScreenSaver","--object-path","/org/freedesktop/ScreenSaver","--method","org.freedesktop.ScreenSaver.GetSessionIdleTime"])
 if _num(ss) is not None:return _num(ss)/1000.0
 mu=_num(_run(["gdbus","call","--session","--dest","org.gnome.Mutter.IdleMonitor","--object-path","/org/gnome/Mutter/IdleMonitor/Core","--method","org.gnome.Mutter.IdleMonitor.GetIdletime"]))
 if mu is not None:return mu/1000.0
 lg=_run(["loginctl","show-session",os.environ.get("XDG_SESSION_ID") or "self","-p","IdleHint","-p","IdleSinceHint"])
 return loginctl_idle(lg,time.time())
def loginctl_idle(text,now):
 kv=dict(l.split("=",1) for l in (text or "").splitlines() if "=" in l)
 if "IdleHint" not in kv:return None
 since=int(kv.get("IdleSinceHint") or 0)
 return max(0.0,now-since/1e6) if kv["IdleHint"]=="yes" and since else 0.0
def idle_seconds():
 try:return _idle_win32() if sys.platform=="win32" else _idle_linux() if sys.platform.startswith("linux") else None
 except Exception:return None
def summarize_work(jobs,now=None):
 now=now or time.time()
 running=[j for j in (jobs or []) if j.get("running")]
 latest=None
 for j in (jobs or []):
  for t in j.get("tools") or []:
   if latest is None or (t.get("updated") or 0)>(latest.get("updated") or 0):latest=dict(t,sid=j.get("sid"),job=j.get("title") or "")
 asks=[dict(a,sid=j.get("sid")) for j in (jobs or []) for a in (j.get("asks") or []) if not a.get("acked")]
 done=[j for j in (jobs or []) if not j.get("running") and (now-(j.get("updated") or 0))<120]
 return {"running":len(running),"running_titles":[str(j.get("title") or j.get("sid") or "")[:80] for j in running[:4]],"latest_tool":{"title":str(latest.get("title") or "")[:120],"status":str(latest.get("status") or ""),"age":round(now-(latest.get("updated") or now),1),"job":str(latest.get("job") or "")[:80]} if latest else None,"open_asks":[{"sid":a.get("sid"),"text":str(a.get("text") or "")[:160]} for a in asks[:4]],"just_finished":[str(j.get("title") or j.get("sid") or "")[:80] for j in done[:4]]}
def snapshot(jobs):
 now=time.time();lt=time.localtime(now)
 return {"ok":True,"at":now,"clock":time.strftime("%H:%M",lt),"weekday":time.strftime("%A",lt),"foreground":foreground_window(),"input_idle_s":idle_seconds(),"work":summarize_work(jobs,now)}
