import re,json,sys,urllib.request,os
root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s=open(os.path.join(root,"web","xr.html"),encoding="utf-8").read()
i=s.index('out="[Your hologram body')
j=s.index('"+text;',i)
brief=s[i:j]
d=json.load(urllib.request.urlopen("http://127.0.0.1:2423/motion/clips",timeout=8))
live=set(d["clips"]); em=set(d.get("emotes",{}).keys())
names=set(re.findall(r'\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b',brief))
missing=sorted(c for c in names if c not in live and c not in em and not c.startswith("companion_"))
m=re.search(r'let list="([^"]+)"',s)
fb=[x.strip() for x in m.group(1).split(",")] if m else []
fbmiss=[c for c in fb if c not in live]
print(json.dumps({"referenced":len(names),"missing":missing,"fallback":len(fb),"fallback_missing":fbmiss,"parsed_ok":len(names)>5 and len(fb)>5}))
sys.exit(1 if (missing or fbmiss or len(names)<=5 or len(fb)<=5) else 0)
