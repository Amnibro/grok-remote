#!/usr/bin/env bash
CHROME="${CHROME:-/c/Users/antho/.cache/puppeteer/chrome/win64-131.0.6778.204/chrome-win64/chrome.exe}"
KEY="${XR_KEY:-619d26facd6fb9381c9dd3688b1ca6a3}"
HUB="${HUB:-http://127.0.0.1:2421}"
MS="${MS:-http://127.0.0.1:2423}"
PLUG="${PLUG:-/c/Users/antho/.grok/plugins/grok-remote}"
MIRROR="${MIRROR:-/c/Users/antho/Documents/ai/grok-remote}"
TAG="suite$$"
PORT=9401
PASS=0
FAIL=0
T0=$(date +%s)
LAP=$T0
phase(){ N=$(date +%s); [ "$LAP" != "$T0" ] && printf '        (%ds)\n' "$((N-LAP))"; LAP=$N; echo "$1"; }
ok(){ PASS=$((PASS+1)); printf '  PASS  %s\n' "$1"; }
no(){ FAIL=$((FAIL+1)); printf '  FAIL  %s\n' "$1"; }
chk(){ [ "$2" = "$3" ] && ok "$1 ($3)" || no "$1 (want $3, got $2)"; }
has(){ case "$2" in *"$3"*) ok "$1";; *) no "$1 (missing '$3' in: $(printf '%.90s' "$2"))";; esac; }
lt(){ N=$(printf '%s' "$2" | grep -o "\"$3\":[0-9]*" | head -1 | cut -d: -f2); [ -n "$N" ] && [ "$N" -lt "$4" ] && ok "$1 ($3=$N < $4)" || no "$1 ($3=${N:-none}, want < $4)"; }
gt(){ N=$(printf '%s' "$2" | grep -o "\"$3\":[0-9]*" | head -1 | cut -d: -f2); [ -n "$N" ] && [ "$N" -gt "$4" ] && ok "$1 ($3=$N > $4)" || no "$1 ($3=${N:-none}, want > $4)"; }
cleanup(){
  powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object { \$_.CommandLine -like '*$TAG*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1
  sleep 3
  rm -rf "/c/Users/antho/AppData/Local/Temp/$TAG" 2>/dev/null
}
trap cleanup EXIT
live(){ CDP_PORT=$PORT CDP_PAGE="$2" node "$PLUG/tests/xr-live.mjs" "$1"; }

phase "== services =="
chk "hub /xr" "$(curl -s -m 8 -o /dev/null -w '%{http_code}' "$HUB/xr?key=$KEY")" "200"
chk "hub /health" "$(curl -s -m 8 -o /dev/null -w '%{http_code}' "$HUB/health")" "200"
MSTATE=$(curl -s -m 6 "$MS/motion/state")
has "motion service state" "$MSTATE" '"base"'
CI=$(python "$PLUG/tools/clip-invariants.py" 2>/dev/null)
case "$CI" in *'"parsed_ok": true'*) ok "clip invariant scan actually ran";; *) no "clip invariant scan actually ran ($CI)";; esac
case "$CI" in *'"root_motion": []'*) ok "no clip carries root motion";; *) no "no clip carries root motion ($CI)";; esac
case "$CI" in *'"empty_or_broken": []'*) ok "no empty or unparseable clip";; *) no "no empty or unparseable clip ($CI)";; esac
case "$CI" in *'"idles_with_loop_seam": []'*) ok "idle clips loop seamlessly";; *) no "idle clips loop seamlessly ($CI)";; esac

SA=$(python "$PLUG/tools/service-audit.py" 2>/dev/null)
case "$SA" in *'"parsed_ok": true'*) ok "service list scan actually ran";; *) no "service list scan actually ran ($SA)";; esac
case "$SA" in *'"BASE_missing": []'*) ok "service clip lists all exist";; *) no "service clip lists all exist ($SA)";; esac
case "$SA" in *'"idles_not_base": []'*) ok "idle clips classify as base";; *) no "idle clips classify as base ($SA)";; esac

BA=$(python "$PLUG/tools/brief-audit.py" 2>/dev/null)
case "$BA" in *'"parsed_ok": true'*) ok "briefing scan actually ran";; *) no "briefing scan actually ran ($BA)";; esac
case "$BA" in *'"missing": []'*) ok "briefing names all exist";; *) no "briefing names all exist ($BA)";; esac
case "$BA" in *'"fallback_missing": []'*) ok "fallback clip list all exist";; *) no "fallback clip list all exist ($BA)";; esac
grep -q "^IDLES = " "$PLUG/motion_service.py" && ok "idle drift set present" || no "idle drift set present"
grep -q "^LIFE = " "$PLUG/motion_service.py" && ok "life beat set present" || no "life beat set present"
curl -s -m 6 -X POST -H "content-type: application/json" -d '{"clip":"salute"}' "$MS/motion/play" >/dev/null
chk "gesture state set on play" "$(curl -s -m 6 "$MS/motion/state" | python -c 'import sys,json;print(json.load(sys.stdin)["gesture"])')" "salute"
sleep 13
chk "gesture state clears when stale" "$(curl -s -m 6 "$MS/motion/state" | python -c 'import sys,json;print(json.load(sys.stdin)["gesture"])')" "None"
curl -s -m 6 "$MS/motion/state" | grep -q gesture_at && no "gesture_at leaks into api" || ok "gesture_at hidden from api"
for m in xr-panels xr-compose xr-motion xr-brain xr-voice xr-ik; do
  chk "module $m.js" "$(curl -s -m 6 -o /dev/null -w '%{http_code}' "$HUB/static/$m.js")" "200"
done

phase "== mirror parity =="
for f in web/xr.html web/xr-panels.js web/xr-compose.js web/xr-motion.js web/xr-brain.js web/xr-voice.js web/xr-ik.js web/motion-lab.html web/pose-harvest.html web/index.html web/watch.html web/clip_index.json tools/clip-index.mjs motion_service.py docs/COMPANION_ARCHITECTURE.md; do
  A=$(md5sum "$PLUG/$f" 2>/dev/null | cut -d' ' -f1)
  B=$(md5sum "$MIRROR/$f" 2>/dev/null | cut -d' ' -f1)
  [ -n "$A" ] && [ "$A" = "$B" ] && ok "mirrored $f" || no "mirrored $f ($A vs $B)"
done

CIX=$(curl -s -m 6 "$HUB/static/clip_index.json" | python -c 'import sys,json;d=json.load(sys.stdin);print(d["built"])' 2>/dev/null)
[ "${CIX:-0}" -ge 90 ] && ok "clip index built ($CIX clips)" || no "clip index built (got ${CIX:-none})"

phase "== static pages =="
bash "$PLUG/tests/page-smoke.sh" motion-lab.html "lab ok" >/dev/null 2>&1 && ok "motion-lab boots" || no "motion-lab boots"
bash "$PLUG/tests/page-smoke.sh" pose-harvest.html "harvest ok" >/dev/null 2>&1 && ok "pose-harvest boots" || no "pose-harvest boots"
for f in motion-lab pose-harvest; do
  grep -q "window.__errors" "$PLUG/web/$f.html" && ok "$f has error bus" || no "$f has error bus"
  grep -q "companionModel" "$PLUG/web/$f.html" && ok "$f honours avatar choice" || no "$f honours avatar choice"
done

phase "== live renderer =="
"$CHROME" --headless=new --disable-gpu --enable-unsafe-swiftshader --autoplay-policy=no-user-gesture-required \
  --use-fake-device-for-media-stream --use-fake-ui-for-media-stream \
  --remote-debugging-port=$PORT --user-data-dir="/c/Users/antho/AppData/Local/Temp/$TAG" \
  "$HUB/xr?key=$KEY&auto=1" >/dev/null 2>&1 &
waitfor(){ for i in $(seq 1 "$2"); do R=$(live "$1" "auto=1" 2>/dev/null); case "$R" in *"$3"*) return 0;; esac; sleep 2; done; return 1; }
sleep 8
waitfor 'JSON.stringify({ready:!!(window.__xr&&__xr.brain()&&__xr.brain().ready())})' 25 '"ready":true' || printf '  note  renderer slow to become ready
'
R=$(live 'JSON.stringify({mods:__xr.mods().length,ready:!!(__xr.brain()&&__xr.brain().ready())})' "auto=1")
has "renderer modules + brain session" "$R" '"ready":true'
chk "renderer attached to motion ws" "$(curl -s -m 6 "$MS/motion/state" | python -c 'import sys,json;print(json.load(sys.stdin)["clients"])')" "1"

G0=$(curl -s -m 6 "$MS/motion/state" | python -c 'import sys,json;print(json.load(sys.stdin)["gesture"])')
WANT=salute; [ "$G0" = "salute" ] && WANT=agree
live "(()=>{const b=__xr.brain();b.B.accum='ok. [[motion:$WANT]] done.';b.B.spokenUpto=0;b.B.lastSpoken='';b.flushSentences(true);return 'sent'})()" "auto=1" >/dev/null
sleep 3
chk "brain tag → motion service" "$(curl -s -m 6 "$MS/motion/state" | python -c 'import sys,json;print(json.load(sys.stdin)["gesture"])')" "$WANT"

live '(()=>{const v=__xr.voice();v.speak("suite check");return "q"})()' "auto=1" >/dev/null
sleep 10
has "tts queue drains to idle" "$(live 'JSON.stringify({q:__xr.voice().queued(),s:__xr.voiceV.speaking})' "auto=1")" '"q":0'

has "renderer error bus clean" "$(live 'JSON.stringify({n:__xr.errors().length,last:(__xr.errors().slice(-1)[0]||{}).msg||""})' "auto=1")" '"n":0'

PROMPT=$(live '(async()=>{__xr.resetBraidSig();const b=__xr.brain();const real=b.req;let cap=null;b.req=async(m,p)=>{cap={m,p};return {result:{}}};await window.__ask("suite prompt probe");b.req=real;const t=cap&&cap.p&&cap.p.prompt&&cap.p.prompt[0]?cap.p.prompt[0].text:"";return JSON.stringify({len:t.length,braid:t.includes("Braid room is live"),tiers:t.includes("explosive (celebration only"),reach:t.includes("[[reach:SIDE TARGET]]"),hitch:t.includes("do NOT loop cleanly"),ail:t.includes("Your body is reporting problems")})})()' "auto=1")
has "prompt carries clip tiers" "$PROMPT" '"tiers":true'
has "prompt carries reach tag" "$PROMPT" '"reach":true'
has "prompt warns about hitching loops" "$PROMPT" '"hitch":true'
BRAIDLIVE=$(curl -s -m 6 "$HUB/api/xr/braid?key=$KEY" | grep -o '"live": *true' | head -1)
if [ -n "$BRAIDLIVE" ]; then
  has "prompt carries Braid context" "$PROMPT" '"braid":true'
else
  printf '  SKIP  prompt carries Braid context (Braid :8788 offline)
'
fi
DELTA=$(live '(async()=>{const b=__xr.brain();const real=b.req;const s=[];b.req=async(m,p)=>{s.push(p.prompt[0].text.length);return{result:{}}};await window.__ask("d1");await window.__ask("d2");b.req=real;return JSON.stringify({second:s[1]})})()' "auto=1")
lt "steady-state turn stays small" "$DELTA" "second" 60
has "no body-fault note when healthy" "$PROMPT" '"ail":false'
has "body-fault note fires when broken" "$(live '(async()=>{__xr.noteErr("console","suite synthetic fault");const b=__xr.brain();const real=b.req;let cap=null;b.req=async(m,p)=>{cap={m,p};return{result:{}}};await window.__ask("suite fault probe");b.req=real;return JSON.stringify({ail:cap.p.prompt[0].text.includes("Your body is reporting problems")})})()' "auto=1")" '"ail":true'

gt "clips drive real bones" "$(live 'JSON.stringify({d:__xr.rig().driven})' "auto=1")" "d" 10

SELFN=$(live '(async()=>{__xr.vision().last=0;const b=__xr.brain();const real=b.req;let cap=null;b.req=async(m,p)=>{cap=p;return{result:{}}};await window.__ask("self note probe");b.req=real;const t=cap.prompt[0].text;return JSON.stringify({self:t.includes("render of YOUR OWN BODY"),cam:t.includes("camera eyes are ON"),src:__xr.vision().src})})()' "auto=1")
has "self-view note when camera off" "$SELFN" '"self":true'
has "no false camera claim" "$SELFN" '"cam":false'

has "rig compatibility check" "$(live 'JSON.stringify(__xr.rig())' "auto=1")" '"pct":100'

MOVE=$(live '(async()=>{const p=window.__panels;const b=__xr.brain();const real=b.req;let cap=null;b.req=async(m,pp)=>{cap=pp;return{result:{}}};for(let i=0;i<5;i++){p.addConvo("you","q"+i);p.addConvo("her","a"+i)}await window.__ask("calm");const calm=cap.prompt[0].text.includes("Body note");for(let i=0;i<6;i++){p.addConvo("move","motion: joyful_jump");p.addConvo("her","r"+i)}await window.__ask("busy");const busy=cap.prompt[0].text.includes("Body note");b.req=real;return JSON.stringify({calm,busy})})()' "auto=1")
has "no pacing nudge when calm" "$MOVE" '"calm":false'
has "pacing nudge when over-gesturing" "$MOVE" '"busy":true'

PHONE=$(CDP_PORT=$PORT node "$PLUG/tests/xr-mobile.mjs" 390 844 '(()=>{const p=window.__panels;p.showBar();["h","t","j","b","v"].forEach(k=>p.doKey(k));return new Promise(r=>setTimeout(()=>{const vw=innerWidth;const named=[[d=>/^base /.test(d.textContent||"")],[d=>/CONVERSATION/.test(d.textContent||"")],[d=>/JUKEBOX/.test(d.textContent||"")],[d=>/^BRAID/.test(d.textContent||"")],[d=>/CODE MAP/.test(d.textContent||"")]];let ok=0,seen=0,widest=0;for(const [f] of named){const d=[...document.querySelectorAll("div")].find(f);if(!d)continue;const b=d.getBoundingClientRect();if(b.width<=0)continue;seen++;widest=Math.max(widest,Math.round(b.width));if(b.right<=vw+1&&b.left>=-1)ok++}["h","t","j","b","v"].forEach(k=>p.doKey(k));p.touchBar.style.display="none";r(JSON.stringify({vw,seen,ok,widest}))},4000))})()')
has "all panels measured on phone" "$PHONE" '"seen":5'
has "all panels fit a 390px phone" "$PHONE" '"ok":5'
lt "widest panel fits phone width" "$PHONE" "widest" 391

TOUCH=$(live '(()=>{const p=window.__panels;const hidden=p.touchBar.style.display||"none";dispatchEvent(new TouchEvent("touchstart",{bubbles:true}));return new Promise(r=>setTimeout(()=>{const shown=p.touchBar.style.display;const btn=[...p.touchBar.children].find(b=>b.getAttribute("data-key")==="h");btn.dispatchEvent(new PointerEvent("pointerdown",{bubbles:true}));setTimeout(()=>{const hud=[...document.querySelectorAll("div")].find(d=>/^base /.test(d.textContent||""));r(JSON.stringify({hidden,shown,btns:p.touchBar.children.length,hudOpen:hud?hud.style.display:"missing"}))},600)},600))})()' "auto=1")
has "touch bar hidden on desktop" "$TOUCH" '"hidden":"none"'
has "touch bar appears on touch" "$TOUCH" '"shown":"flex"'
has "touch bar has all panel buttons" "$TOUCH" '"btns":7'
has "touch button opens its panel" "$TOUCH" '"hudOpen":"block"'
MATRIX=$(CDP_PORT=$PORT node "$PLUG/tests/xr-mobile.mjs" 360 640 '(()=>{const p=window.__panels;p.showBar();return new Promise(r=>setTimeout(()=>{const ids=["cap","exit","talk","typeRow"];const els={};for(const k of ids){const e=document.getElementById(k);if(e){const b=e.getBoundingClientRect();if(b.width>0&&b.height>0)els[k]=b}}els.touchBar=p.touchBar.getBoundingClientRect();const names=Object.keys(els);const ov=(a,b)=>!(a.bottom<=b.top||a.top>=b.bottom||a.right<=b.left||a.left>=b.right);const hits=[];for(let i=0;i<names.length;i++)for(let j=i+1;j<names.length;j++){if(ov(els[names[i]],els[names[j]]))hits.push(names[i]+"~"+names[j])}const off=names.filter(n=>els[n].bottom>innerHeight+1);p.touchBar.style.display="none";r(JSON.stringify({n:names.length,overlaps:hits,offscreen:off}))},1000))})()')
gt "chrome elements all measured" "$MATRIX" "n" 4
has "no overlapping controls on a small phone" "$MATRIX" '"overlaps":[]'
has "no control pushed offscreen" "$MATRIX" '"offscreen":[]'

OVL=$(CDP_PORT=$PORT node "$PLUG/tests/xr-mobile.mjs" 390 844 '(()=>{const p=window.__panels;p.showBar();return new Promise(r=>setTimeout(()=>{const bar=p.touchBar.getBoundingClientRect();const tr=document.getElementById("typeRow").getBoundingClientRect();const tk=document.getElementById("talk").getBoundingClientRect();const ov=(a,b)=>!(a.bottom<=b.top||a.top>=b.bottom||a.right<=b.left||a.left>=b.right);const res={w:Math.round(bar.width),onType:ov(bar,tr),onTalk:ov(bar,tk)};p.touchBar.style.display="none";r(JSON.stringify(res))},900))})()')
gt "touch bar renders on phone" "$OVL" "w" 40
has "touch bar clear of the text input" "$OVL" '"onType":false'
has "touch bar clear of the talk button" "$OVL" '"onTalk":false'

JUKE=$(live '(()=>{window.dispatchEvent(new KeyboardEvent("keydown",{key:"j",bubbles:true}));return new Promise(r=>setTimeout(()=>{const jb=[...document.querySelectorAll("div")].find(d=>/JUKEBOX/.test(d.textContent||""));const rows=jb?[...jb.children].slice(1).map(c=>c.textContent):[];const uniq=new Set(rows.map(x=>x.split("  ")[0]));r(JSON.stringify({rows:rows.length,uniq:uniq.size,first:rows[0]||""}))},3500))})()' "auto=1")
gt "jukebox lists the library" "$JUKE" "rows" 50
has "jukebox is deduped" "$JUKE" '"rows":97,"uniq":97'
has "jukebox sorts calmest first" "$JUKE" '"first":"acknowledging'

TIER=$(live '(()=>{const p=window.__panels;p.addConvo("move","motion: joyful_jump");p.addConvo("move","motion: idle_loop");return new Promise(r=>setTimeout(()=>{const rows=[...document.getElementById("clog").children].slice(-2).map(c=>c.textContent);r(JSON.stringify({rows,n:rows.length}))},900))})()' "auto=1")
has "transcript annotates move energy" "$TIER" 'explosive 118.5'
has "transcript flags hitching moves" "$TIER" 'hitches'

MAP=$(live '(()=>{window.dispatchEvent(new KeyboardEvent("keydown",{key:"v",bubbles:true}));return new Promise(r=>setTimeout(()=>{const NL=String.fromCharCode(10);const d=[...document.querySelectorAll("div")].find(e=>/CODE MAP/.test(e.textContent||""));const rows=d?d.textContent.split(NL).filter(l=>l.indexOf("xr-")>=0):[];const mods=__xr.mods().filter(m=>m!=="core"&&m.indexOf("sid:")!==0);r(JSON.stringify({rows:rows.length,mods:mods.length,zero:rows.filter(l=>l.indexOf(" 0 lines")>=0).length}))},6000))})()' "auto=1")
chk "xr modules revalidate instead of caching a day" "$(curl -s -m 6 -D- -o /dev/null "$HUB/static/xr-deform.js" | grep -i '^cache-control' | tr -d '
' | cut -d' ' -f2)" "no-cache"
has "big static assets still cache" "$(curl -s -m 6 -D- -o /dev/null "$HUB/static/three.module.js" | tr -d '
')" "max-age=86400"

LAGH=$(node "$PLUG/tests/lag.mjs" 2>/dev/null)
lf(){ printf '%s' "$LAGH" | grep -o "\"$1\":[0-9]*" | cut -d: -f2; }
gt "lag rate is near base when she is calm" "$LAGH" "calmRate" 600
lt "a transient gesture drops the lag rate" "$LAGH" "fastRate" 400
gt "the burst registers as excess speed" "$LAGH" "burstExcess" 100
gt "the rate recovers after the gesture" "$LAGH" "settleRate" 600
chk "slow texture trails the fast one" "$(lf slowIsSlower)" "1"
chk "lag guards catch bad inputs" "$(lf guards)" "3"
chk "makeLag refuses a rigless skeleton" "$(lf nullTex)" "1"
chk "loose-bone pattern matches scarf not Head" "$(printf '%s' "$LAGH" | grep -o '"looseMatch":"[01]*"' | cut -d'"' -f4)" "010"
gt "hair flex finds points on a stub rig" "$LAGH" "hairPts" 10
gt "strands separate while she moves" "$LAGH" "strandWorst" 2
lt "strands converge when she is still" "$LAGH" "strandCalm" 2
chk "strand meter guards bad inputs" "$(lf spGuards)" "2"
chk "strand meter samples nothing with no loose points" "$(lf spZeroSampled)" "0"

DEF=$(node "$PLUG/tests/deform.mjs" 2>/dev/null)
df(){ printf '%s' "$DEF" | grep -o "\"$1\":[0-9]*" | cut -d: -f2; }
chk "cpu skin deforms every point" "$(df movedPct)" "100"
gt "cpu skin runs the whole cloud" "$DEF" "skinN" 10000
lt "cpu skin loop stays under a frame" "$DEF" "skinMs" 1600
chk "cpu skin bails on missing inputs" "$(df guardsHit)" "3"
chk "cpu skin survives out-of-range bone indices" "$(df oobSafe)" "1"
gt "cloth sim steps every point" "$DEF" "clothN" 1000
lt "cloth loop stays under a frame" "$DEF" "clothMs" 1600
chk "cloth bails on missing state" "$(df clothGuards)" "2"
chk "cloth never detaches from the body" "$(df within)" "1"
lt "stray radius stays inside the elastic limit" "$DEF" "strayMm" 27
grep -q "stepPhysics" "$PLUG/web/xr.html" && no "dead cloth sim removed from xr.html" || ok "dead cloth sim removed from xr.html"

LAGV=$(live '(async()=>{const r=[];for(let i=0;i<30;i++){r.push(__xr.lagInfo());await new Promise(x=>setTimeout(x,110))}
await fetch("http://"+location.hostname+":2423/motion/play",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({clip:"salute"})});
await new Promise(x=>setTimeout(x,600));const g=[];for(let i=0;i<24;i++){g.push(__xr.lagInfo());await new Promise(x=>setTimeout(x,90))}
const mx=a=>Math.max(...a),mn=a=>Math.min(...a),av=a=>a.reduce((p,c)=>p+c,0)/a.length;const c=__xr.cloth();const sp=__xr.strands();
return JSON.stringify({pts:c.hair.pts,pct:c.hair.pct,lag:c.lag?1:0,w:c.w,maxFlex:Math.round(c.hair.max*100),span:Math.round(c.hair.span*1000),restRate:Math.round(av(r.slice(15).map(x=>x.rate))*100),gestRate:Math.round(mn(g.map(x=>x.rate))*100),restSpeed:Math.round(av(r.slice(15).map(x=>x.speed))*100),gestSpeed:Math.round(mx(g.map(x=>x.speed))*100),slowRate:Math.round((__xr.lagSlow().rate)*100),strandN:sp.sampled,strandWorst:Math.round(sp.worstMm),strandMean:Math.round(sp.meanMm)})})()' "auto=1")
gt "avatar has loose hair points" "$LAGV" "pts" 500
gt "loose points reach real looseness" "$LAGV" "maxFlex" 30
gt "hair span is a real length" "$LAGV" "span" 100
chk "lag bone texture is live" "$(printf '%s' "$LAGV" | grep -o '\"lag\":[0-9]*' | cut -d: -f2)" "1"
chk "cloth weight is switched on" "$(printf '%s' "$LAGV" | grep -o '\"w\":[0-9]*' | cut -d: -f2)" "1"
LVR=$(printf '%s' "$LAGV" | grep -o '"restSpeed":[0-9]*' | cut -d: -f2)
LVG=$(printf '%s' "$LAGV" | grep -o '"gestSpeed":[0-9]*' | cut -d: -f2)
LRR=$(printf '%s' "$LAGV" | grep -o '"restRate":[0-9]*' | cut -d: -f2)
LRG=$(printf '%s' "$LAGV" | grep -o '"gestRate":[0-9]*' | cut -d: -f2)
[ -n "$LVG" ] && [ -n "$LVR" ] && [ "$LVG" -gt "$LVR" ] && ok "rig speed reads higher under a gesture (gesture=$LVG rest=$LVR)" || no "rig speed reads higher under a gesture (gesture=${LVG:-none} rest=${LVR:-none})"
[ -n "$LRG" ] && [ -n "$LRR" ] && [ "$LRG" -lt "$LRR" ] && ok "fast motion buys more hair trail (rate gesture=$LRG rest=$LRR)" || no "fast motion buys more hair trail (rate gesture=${LRG:-none} rest=${LRR:-none})"
gt "hair still settles when she is calm" "$LAGV" "restRate" 250
gt "strand sample is real" "$LAGV" "strandN" 50
gt "strands separate from each other" "$LAGV" "strandWorst" 8
gt "the whole ponytail is not one slab" "$LAGV" "strandMean" 4
LSF=$(printf '%s' "$LAGV" | grep -o '"gestRate":[0-9]*' | cut -d: -f2)
LSS=$(printf '%s' "$LAGV" | grep -o '"slowRate":[0-9]*' | cut -d: -f2)
[ -n "$LSS" ] && [ -n "$LSF" ] && [ "$LSS" -lt "$LSF" ] && ok "slow lag trails the fast one (slow=$LSS fast=$LSF)" || no "slow lag trails the fast one (slow=${LSS:-none} fast=${LSF:-none})"

SKIN=$(node "$PLUG/tests/skin-bind.mjs" 2>/dev/null)
sf(){ printf '%s' "$SKIN" | grep -o "\"$1\":[0-9]*" | cut -d: -f2; }
chk "synthetic rig builds all 12 bones" "$(sf bones)" "12"
chk "every capsule binds to a bone" "$(sf segs)" "$(sf capsules)"
chk "every joint owns its own point" "$(sf hit)" "$(sf of)"
chk "skin weights sum to one (low)" "$(sf sumLo)" "1000000"
chk "skin weights sum to one (high)" "$(sf sumHi)" "1000000"
chk "every body point blends 2+ bones" "$(sf blendPct)" "100"
chk "blend meter reads zero on a rigid bind" "$(sf rigidCtrlPct)" "0"
lt "skin bind stays fast" "$SKIN" "bindMs" 200
chk "skin bind survives an empty cloud" "$(sf emptyLen)" "0"
chk "skin bind survives a boneless rig" "$(sf noBoneNonZero)" "0"

GEO=$(node "$PLUG/tests/body-geom.mjs" 2>/dev/null)
gf(){ printf '%s' "$GEO" | grep -o "\"$1\":-\?[0-9]*" | cut -d: -f2; }
chk "point cloud scales to 1.70m" "$(gf h)" "1700"
chk "point cloud stands on the floor" "$(gf feet)" "0"
chk "point cloud centers on x" "$(gf cx)" "0"
chk "point cloud faces the camera" "$(gf zFlipped)" "1"
chk "leg points get their flex weight" "$(gf flexSet)" "$(gf legs)"
gt "repose actually moves arm points" "$GEO" "moved" 10
gt "repose moves them a real distance" "$GEO" "maxMoveMm" 20
chk "meterize survives an empty cloud" "$(gf emptySafe)" "1"
chk "repose survives missing stats" "$(gf nullSSafe)" "1"

SEAM=$(node "$PLUG/tests/pose-seam.mjs" 2>/dev/null)
gt "fallback clips cover every bone" "$SEAM" "tracks" 8
chk "fallback idle loop is seamless" "$(printf '%s' "$SEAM" | grep -o '"idleDeg":[0-9]*' | cut -d: -f2)" "0"
chk "fallback talk loop is seamless" "$(printf '%s' "$SEAM" | grep -o '"talkDeg":[0-9]*' | cut -d: -f2)" "0"
gt "seam meter detects a real seam" "$SEAM" "rampDeg" 1000
chk "clip builder survives a missing skeleton" "$(printf '%s' "$SEAM" | grep -o '"nullSafe":[0-9]*' | cut -d: -f2)" "1"

gt "code map lists every loaded module" "$MAP" "rows" 7
gt "code map counts modules" "$MAP" "mods" 7
MODN=$(printf '%s' "$MAP" | grep -o '"mods":[0-9]*' | cut -d: -f2)
ROWN=$(printf '%s' "$MAP" | grep -o '"rows":[0-9]*' | cut -d: -f2)
chk "code map row count matches module count" "${ROWN:-norows}" "${MODN:-nomods}"
has "no unreadable module in map" "$MAP" '"zero":0'

SMOOTH=$(live '(async()=>{const k=__xr.ik().chain("right");const V=Object.getPrototypeOf(k.root.position).constructor;const p=new V();const s=[];const t0=performance.now();__xr.motion().motionPlay("wave_hello","gesture",0.4);await new Promise(res=>{const step=()=>{k.end.getWorldPosition(p);s.push([performance.now()-t0,p.x,p.y,p.z]);if(performance.now()-t0<2000)requestAnimationFrame(step);else res()};requestAnimationFrame(step)});let mx=0,tot=0;for(let i=1;i<s.length;i++){const a=s[i-1],b=s[i];const d=Math.hypot(b[1]-a[1],b[2]-a[2],b[3]-a[3]);if(d>mx)mx=d;tot+=d}return JSON.stringify({jumpMm:Math.round(mx*1000),pathMm:Math.round(tot*1000)})})()' "auto=1")
lt "gesture start has no pop" "$SMOOTH" "jumpMm" 200
gt "gesture actually moves the arm" "$SMOOTH" "pathMm" 100

BONE=$(live '(async()=>{const b=__xr.brain();b.B.accum="x. [[compose:suitebone|400:Hips=0,60,0 LeftArm=0,0,50|1200:rest]] y.";b.B.spokenUpto=0;b.B.lastSpoken="";b.flushSentences(true);await new Promise(r=>setTimeout(r,1800));const c=__xr.composeStats()||{};return JSON.stringify({skipped:(c.skipped||[]).join(","),peakBone:c.peakBone||""})})()' "auto=1")
has "compose rejects illegal bones" "$BONE" '"skipped":"Hips"'
has "compose keeps legal bones" "$BONE" '"peakBone":"LeftArm"'

SHOT=$(live '(async()=>{const u=__xr.solidShot();if(!u)return JSON.stringify({shot:0});const i=new Image();await new Promise(r=>{i.onload=r;i.onerror=r;i.src=u});return JSON.stringify({shot:u.length,w:i.width,h:i.height,fov:Math.round(__dbg.camera.fov)})})()' "auto=1")
gt "solid self-view renders" "$SHOT" "shot" 3000
has "self-view is portrait 480x640" "$SHOT" '"w":480,"h":640'
has "camera restored after shot" "$SHOT" '"fov":58'

HOLD=$(live '(()=>{const b=__xr.brain();b.B.accum="x. [[compose:suitehold|400:RightArm=0,0,-60|1200:rest]] y.";b.B.spokenUpto=0;b.B.lastSpoken="";b.flushSentences(true);return new Promise(r=>setTimeout(()=>r(JSON.stringify({held:__xr.vision().hold>Date.now(),peak:(__xr.composeStats()||{}).peakDeg})),1500))})()' "auto=1")
has "compose holds the vision loop" "$HOLD" '"held":true'
has "compose measures its own amplitude" "$HOLD" '"peak":60'

has "arm IK solves" "$(live '(()=>{__reach("right front");const k=__xr.ik();return JSON.stringify({w:k.state.weight,err:+k.state.err.toFixed(3)})})()' "auto=1")" '"err":0'
live '(()=>{__reach("release");return "r"})()' "auto=1" >/dev/null

live '(()=>{window.dispatchEvent(new KeyboardEvent("keydown",{key:"c",bubbles:true}));return "cam"})()' "auto=1" >/dev/null
sleep 6
LOOK=$(live '(async()=>{await new Promise(r=>setTimeout(r,9000));const L=__xr.look()?__xr.look().L:null;return JSON.stringify({loaded:!!__xr.look(),on:L&&L.on,frames:L?L.frames:-1})})()' "auto=1")
has "look module loaded" "$LOOK" '"loaded":true'
gt "look runs detection on camera" "$LOOK" "frames" 0

has "vision loop captures" "$(live 'JSON.stringify(__xr.vision())' "auto=1")" '"on":true'
has "camera note when camera on" "$(live '(async()=>{const b=__xr.brain();const real=b.req;let cap=null;b.req=async(m,p)=>{cap=p;return{result:{}}};await window.__ask("cam note probe");b.req=real;return JSON.stringify({cam:cap.prompt[0].text.includes("camera eyes are ON")})})()' "auto=1")" '"cam":true'

RECAP=$(live '(async()=>{const p=window.__panels;p.addConvo("you","suite seed question");p.addConvo("her","suite seed answer");p.addConvo("you","suite second");p.addConvo("her","suite second answer");window.__recapSent=false;const b=__xr.brain();const real=b.req;let cap=null;b.req=async(m,pp)=>{cap=pp;return{result:{}}};await window.__ask("suite current turn");b.req=real;const t=cap.prompt[0].text;const i=t.indexOf("[You and Anthony were");return JSON.stringify({has:i>=0,leaksCurrent:i>=0?t.slice(i,t.indexOf("]",i)).includes("suite current turn"):false})})()' "auto=1")
has "convo recap survives reload" "$RECAP" '"has":true'
has "recap excludes the current turn" "$RECAP" '"leaksCurrent":false'

if [ -n "$QUICK" ]; then
  phase "== local avatar (skipped: QUICK) =="
else
phase "== local avatar =="
live '(async()=>{const buf=await (await fetch("/static/model.glb")).arrayBuffer();const db=await new Promise((res,rej)=>{const r=indexedDB.open("companionAvatar",1);r.onupgradeneeded=()=>r.result.createObjectStore("f");r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)});await new Promise((res,rej)=>{const t=db.transaction("f","readwrite");t.objectStore("f").put({buf,name:"suite_avatar.glb"},"avatar");t.oncomplete=res;t.onerror=()=>rej(t.error)});localStorage.setItem("companionModel","__local");location.reload();return "stored"})()' "auto=1" >/dev/null
sleep 6
waitfor 'JSON.stringify({f:__xr.rig().file})' 20 'suite_avatar.glb' || printf '  note  local avatar slow to load
'
LA=$(live 'JSON.stringify({f:__xr.rig().file,d:__xr.rig().driven,e:__xr.errors().length})' "auto=1")
has "local avatar loads from IndexedDB" "$LA" 'suite_avatar.glb (local)'
gt "local avatar animates" "$LA" "d" 10
has "local avatar load is clean" "$LA" '"e":0'
live '(async()=>{const db=await new Promise((res,rej)=>{const r=indexedDB.open("companionAvatar",1);r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)});const t=db.transaction("f","readwrite");t.objectStore("f").delete("avatar");localStorage.removeItem("companionModel");return "cleared"})()' "auto=1" >/dev/null

fi

phase "== chat surfaces =="
curl -s -m 6 -X PUT "http://127.0.0.1:$PORT/json/new?http%3A%2F%2F127.0.0.1%3A2421%2F%3Fkey%3D$KEY" >/dev/null
sleep 10
STRIP=$(CDP_PORT=$PORT CDP_PAGE="2421/?key" node "$PLUG/tests/xr-live.mjs" '(()=>{const f=window.takeAgentRx;if(typeof f!=="function")return "NO_FN";return JSON.stringify({body:f("a [[motion:agree]] b").trim(),bare:f("a [[wave]] b").trim(),wiki:f("keep [[MyWiki]]").trim()})})()')
has "hub chat strips body tags" "$STRIP" '"body":"a b"'
has "hub chat strips bare tags" "$STRIP" '"bare":"a b"'
has "hub chat keeps wiki links" "$STRIP" '"wiki":"keep [[MyWiki]]"'
curl -s -m 6 -X PUT "http://127.0.0.1:$PORT/json/new?http%3A%2F%2F127.0.0.1%3A2421%2Fstatic%2Fmotion-lab.html%3Fkey%3D$KEY" >/dev/null
sleep 12
LABSEAM=$(CDP_PORT=$PORT CDP_PAGE="motion-lab" node "$PLUG/tests/xr-live.mjs" '(()=>{const L=window.lab;if(!L)return JSON.stringify({err:"no lab"});L.setBone("RightArm",0,0,-60);L.snapKey();L.setBone("RightArm",0,0,-10);L.snapKey();const open=document.getElementById("seam").textContent;L.setBone("RightArm",0,0,-60);L.snapKey();const closed=document.getElementById("seam").textContent;return JSON.stringify({open,closed})})()')
has "lab flags an open loop" "$LABSEAM" 'HITCHES hard'
has "lab confirms a closed loop" "$LABSEAM" 'loops clean'

BADGE=$(CDP_PORT=$PORT CDP_PAGE="2421/?key" node "$PLUG/tests/xr-live.mjs" '(async()=>{await compPoll();const b=document.getElementById("compBadge");const r=b.getBoundingClientRect();return JSON.stringify({rendered:r.width>0&&r.height>0,w:Math.round(r.width),txt:document.getElementById("compTxt").textContent,href:b.getAttribute("href")})})()')
has "hub companion badge renders" "$BADGE" '"rendered":true'
gt "hub badge has real width" "$BADGE" "w" 40
has "hub companion badge links to /xr" "$BADGE" '"href":"/xr'
grep -q "function stripBody" "$PLUG/web/watch.html" && ok "watch page has stripBody" || no "watch page has stripBody"

echo
for c in suitehold suitebone shottest holdtest synthtest; do rm -f "$PLUG/clips/$c.json" 2>/dev/null; done

printf 'RESULT  %d passed, %d failed in %ds%s\n' "$PASS" "$FAIL" "$(( $(date +%s) - T0 ))" "${QUICK:+ (QUICK)}"
[ "$FAIL" -eq 0 ]
