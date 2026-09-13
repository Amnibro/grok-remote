import ctypes,ctypes.wintypes,os,sys,time
def foreground_window():
 if sys.platform!="win32":return {"title":"","exe":""}
 try:
  u=ctypes.windll.user32;k=ctypes.windll.kernel32
  h=u.GetForegroundWindow()
  if not h:return {"title":"","exe":""}
  n=u.GetWindowTextLengthW(h)+1
  buf=ctypes.create_unicode_buffer(n)
  u.GetWindowTextW(h,buf,n)
  pid=ctypes.wintypes.DWORD()
  u.GetWindowThreadProcessId(h,ctypes.byref(pid))
  exe=""
  ph=k.OpenProcess(0x1000,False,pid.value)
  if ph:
   try:
    sz=ctypes.wintypes.DWORD(1024);pb=ctypes.create_unicode_buffer(1024)
    if k.QueryFullProcessImageNameW(ph,0,pb,ctypes.byref(sz)):exe=os.path.basename(pb.value)
   finally:k.CloseHandle(ph)
  return {"title":buf.value[:160],"exe":exe}
 except Exception:return {"title":"","exe":""}
def idle_seconds():
 if sys.platform!="win32":return None
 try:
  class LII(ctypes.Structure):_fields_=[("cbSize",ctypes.c_uint),("dwTime",ctypes.c_uint)]
  li=LII();li.cbSize=ctypes.sizeof(LII)
  if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li)):return None
  return max(0,(ctypes.windll.kernel32.GetTickCount()-li.dwTime)/1000.0)
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
