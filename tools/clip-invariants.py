import json,glob,os,sys
root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
travel=[];empty=[];huge=[]
files=sorted(glob.glob(os.path.join(root,"clips","*.json")))
for f in files:
    try:c=json.load(open(f,encoding="utf-8"))
    except Exception:
        empty.append(os.path.basename(f));continue
    tr=c.get("tracks",[])
    if not tr or not c.get("duration"):
        empty.append(os.path.basename(f));continue
    for t in tr:
        nm=t.get("name","")
        if "hips" not in nm.lower() or ".position" not in nm:continue
        v=t["values"];n=len(t["times"])
        if n<2 or len(v)<n*3:continue
        xs=[v[i*3] for i in range(n)];zs=[v[i*3+2] for i in range(n)]
        d=max(max(xs)-min(xs),max(zs)-min(zs))
        if d>0.02:travel.append([os.path.basename(f),round(d,3)])
    if (c.get("duration") or 0)>90:huge.append([os.path.basename(f),c["duration"]])
import math,re
def seam(c):
    worst=0.0
    for t in c.get("tracks",[]):
        if t.get("type")!="quaternion":continue
        v=t["values"];n=len(t["times"])
        if n<2:continue
        d=sum(x*y for x,y in zip(v[0:4],v[(n-1)*4:(n-1)*4+4]))
        d=max(-1.0,min(1.0,abs(d)))
        worst=max(worst,math.degrees(2*math.acos(d)))
    return round(worst,2)
svc=open(os.path.join(root,"motion_service.py"),encoding="utf-8").read()
m=re.search(r'IDLES\s*=\s*\[(.*?)\]',svc,re.S)
idles=re.findall(r'"([a-zA-Z0-9_]+)"',m.group(1)) if m else []
rough=[]
for n in idles:
    fp=os.path.join(root,"clips",n+".json")
    if not os.path.exists(fp):rough.append([n,"missing"]);continue
    sm=seam(json.load(open(fp,encoding="utf-8")))
    if sm>8:rough.append([n,sm])
print(json.dumps({"clips":len(files),"root_motion":travel,"empty_or_broken":empty,"over_90s":huge,"idles_with_loop_seam":rough,"idles_checked":len(idles),"parsed_ok":len(files)>0 and len(idles)>0}))
sys.exit(1 if (travel or empty or rough or not files or not idles) else 0)
