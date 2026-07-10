from pathlib import Path
p=Path(__file__).resolve().parents[1]/"server.py"
text=p.read_text(encoding="utf-8")
helper=r'''
def parse_frontmatter(text):
 meta={}; body=text
 if text.startswith("---"):
  parts=text.split("---",2)
  if len(parts)>=3:
   raw=parts[1]; body=parts[2].lstrip("\n")
   key=None; acc=[]
   def flush():
    nonlocal key,acc
    if key is not None:
     meta[key]=" ".join(acc).strip().strip('"').strip("'")
     key=None;acc=[]
   for line in raw.splitlines():
    if not line.strip():
     continue
    if (line.startswith(" ") or line.startswith("\t")) and key is not None:
     acc.append(line.strip());continue
    flush()
    if ":" in line:
     k,v=line.split(":",1);k=k.strip();v=v.strip()
     if v in ("|",">",">-","|-") or v=="":
      key=k;acc=[]
     else:
      meta[k]=v.strip('"').strip("'")
   flush()
 return meta,body
def skill_roots(cwd):
 home=Path.home()/".grok"
 roots=[]
 for r in [home/"skills",home/"bundled"/"skills",home/"plugins",home/"installed-plugins",home/"marketplace-cache"]:
  if r.is_dir():roots.append(r)
 if cwd:
  c=Path(cwd)
  for r in [c/".grok"/"skills",c/".agents"/"skills",c/"skills"]:
   if r.is_dir():roots.append(r)
 return roots
def scan_skills(cwd):
 seen=set();out=[]
 for root in skill_roots(cwd):
  try:files=list(root.rglob("SKILL.md"))
  except Exception:continue
  for f in files:
   try:
    if any(part in f.parts for part in ("node_modules",".git")):continue
    raw=f.read_text(encoding="utf-8",errors="replace")
    meta,body=parse_frontmatter(raw)
    name=(meta.get("name") or f.parent.name).strip()
    if not name or name.lower() in seen:continue
    seen.add(name.lower())
    desc=meta.get("description") or ""
    if len(desc)>240:desc=desc[:237]+"..."
    sp=str(f).replace("\\","/")
    src="user"
    if "/bundled/" in sp:src="bundled"
    elif "/marketplace-cache/" in sp:src="marketplace"
    elif "/plugins/" in sp or "/installed-plugins/" in sp:src="plugin"
    inv=str(meta.get("user-invocable","true")).lower() not in ("false","0","no")
    out.append({"name":name,"description":desc,"when":meta.get("when-to-use") or "","hint":meta.get("argument-hint") or "","source":src,"path":str(f),"kind":"skill","userInvocable":inv,"invoke":"/"+name})
   except Exception:continue
 home=Path.home()/".grok"
 cmd_roots=[]
 for r in [home/"plugins",home/"installed-plugins",home/"marketplace-cache"]:
  if r.is_dir():cmd_roots.append(r)
 if cwd:
  c=Path(cwd)
  for r in [c/".grok"/"commands",c/"commands"]:
   if r.is_dir():cmd_roots.append(r)
 for root in cmd_roots:
  try:files=list(root.rglob("*.md"))
  except Exception:continue
  for f in files:
   try:
    if "commands" not in f.parts:continue
    if f.name.lower() in ("readme.md","changelog.md","license.md"):continue
    if any(part in f.parts for part in ("node_modules",".git")):continue
    raw=f.read_text(encoding="utf-8",errors="replace")
    meta,body=parse_frontmatter(raw)
    name=(meta.get("name") or f.stem).strip().lstrip("/")
    if not name or name.lower() in seen:continue
    seen.add(name.lower())
    desc=meta.get("description") or ""
    if len(desc)>240:desc=desc[:237]+"..."
    out.append({"name":name,"description":desc,"when":"","hint":meta.get("argument-hint") or "","source":"command","path":str(f),"kind":"command","userInvocable":True,"invoke":"/"+name})
   except Exception:continue
 order={"bundled":0,"user":1,"plugin":2,"command":3,"marketplace":4,"agent":5}
 out.sort(key=lambda x:(order.get(x["source"],9),x["name"].lower()))
 return out
'''
if "def scan_skills" not in text:
 text=text.replace('return p.suffix==""\n','return p.suffix==""\n'+helper+'\n')
 print("helper inserted")
else:
 print("helper exists")
route_code='''
 async def skills_list(request):
  cwd=request.rel_url.query.get("cwd") or state["cwd"]
  items=scan_skills(cwd)
  return web.json_response({"ok":True,"cwd":cwd,"count":len(items),"skills":items},headers={"Cache-Control":"no-store"})
'''
if "async def skills_list" not in text:
 text=text.replace(" async def ws_proxy(request):",route_code+" async def ws_proxy(request):")
 print("handler inserted")
else:
 print("handler exists")
if 'add_get("/api/skills/list"' not in text:
 text=text.replace('app.router.add_post("/api/fs/mkdir",fs_mkdir)','app.router.add_post("/api/fs/mkdir",fs_mkdir)\n app.router.add_get("/api/skills/list",skills_list)')
 print("route registered")
else:
 print("route exists")
text=text.replace('"features":["fs","ide","review","multi-client-hub"]','"features":["fs","ide","review","multi-client-hub","skills-scan"]')
p.write_text(text,encoding="utf-8")
print("wrote",p.stat().st_size)
ns={}
exec(helper,{"Path":Path},ns)
items=ns["scan_skills"](r"C:\\Users\\antho\\Documents\\ai")
print("scanned",len(items))
print([i["name"]+":"+i["source"] for i in items[:30]])
print("design",any(i["name"]=="design" for i in items))
print("execute-plan",any(i["name"]=="execute-plan" for i in items))
print("check-work",any(i["name"]=="check-work" for i in items))
print("remote",any(i["name"]=="remote" for i in items))
