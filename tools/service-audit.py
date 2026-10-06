import re,json,sys,os,urllib.request
root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s=open(os.path.join(root,"motion_service.py"),encoding="utf-8").read()
d=json.load(urllib.request.urlopen(os.environ.get("MOTION_CLIPS_URL") or "http://127.0.0.1:2423/motion/clips",timeout=8))
live=set(d["clips"])
def names(var,open_c,close_c):
    m=re.search(var+r'\s*=\s*\%s(.*?)\%s'%(open_c,close_c),s,re.S)
    return sorted(set(re.findall(r'"([a-zA-Z0-9_]+)"',m.group(1)))) if m else []
res={};counts={}
for var,o,c in [("BASE","{","}"),("TRAVEL","{","}"),("IDLES","[","]"),("LIFE","[","]")]:
    n=names(var,o,c)
    res[var+"_missing"]=[x for x in n if x not in live]
    counts[var]=len(n)
res["emote_missing"]=sorted({v for v in d.get("emotes",{}).items() and d.get("emotes",{}).values() if v not in live})
idles=set(names("IDLES","[","]")); base=set(names("BASE","{","}"))
res["idles_not_base"]=sorted(idles-base)
bad=any(v for k,v in res.items() if k.endswith("_missing") or k=="idles_not_base") or not all(counts.get(v,0)>0 for v in ("BASE","TRAVEL","IDLES","LIFE"))
res["counts"]=counts
res["parsed_ok"]=all(counts.get(v,0)>0 for v in ("BASE","TRAVEL","IDLES","LIFE"))
print(json.dumps(res))
sys.exit(1 if bad else 0)
