from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_pair_in_upper_right_menus():
    html=(ROOT/"web"/"index.html").read_text(encoding="utf-8")
    assert 'id="btnPairPhone"' in html
    assert 'id="btnPairPhoneMore"' in html
    assert "function openPairPhone(" in html
    assert "async function openAppUrl(" in html
    assert 'openAppUrl(dest,{sameWindowFallback:true})' in html
    assert 'id="btnHealthMore"' in html
    orbit=html[html.find('id="orbitMenu"'):html.find('id="setup"')]
    assert 'id="btnPairPhone"' in orbit
    more=html[html.find('id="moreMenu"'):html.find('id="orbitMenu"')]
    assert 'id="btnPairPhoneMore"' in more
    assert 'data-layer="home"' in more
    assert 'data-goto="chat"' in more
    assert "function showMoreLayer" in html
    assert "function bindMoreLayers" in html
    priv=html[html.find("if(btnPrivacy)"):html.find("if(btnPrivacy)")+160]
    assert "closeMoreMenu()" not in priv
    lay=html[html.find("if(btnLayoutToggle)"):html.find("if(btnLayoutToggle)")+180]
    assert "closeMoreMenu()" not in lay
def test_sess_filters_core_only_single_line():
    html=(ROOT/"web"/"index.html").read_text(encoding="utf-8")
    css=(ROOT/"web"/"braid-layout.css").read_text(encoding="utf-8")
    fn=html[html.find("function paintSessScopeChips"):html.find("function mergeArchivedStubs")]
    assert '["active","Active"],["live","Live"],["archived","Archived"],["all","All"]' in fn
    assert "Object.keys(appCounts)" not in fn
    assert '["app:"' not in fn
    assert ".sess-scope-rail{display:flex;flex-wrap:nowrap" in html.replace("\n","") or "flex-wrap:nowrap" in html[html.find(".sess-scope-rail"):html.find(".sess-scope-rail")+220]
    assert "sess-scope-rail" in css
    assert "flex-wrap:nowrap" in css[css.find("sess-scope-rail"):css.find("sess-scope-rail")+400]
def test_scient_and_defunct_module_chips_gone():
    html=(ROOT/"web"/"index.html").read_text(encoding="utf-8")
    fn=html[html.find("function paintSessScopeChips"):html.find("function mergeArchivedStubs")]
    assert "Amni-scient" not in fn
    assert "appCounts" not in fn
    logo=html[html.find('id="logo"'):html.find('id="logo"')+260]
    assert "AMNI-SCIENT" not in logo
    assert "GROK BUILD" in logo or "GROK" in logo
    assert 'id="btnDelve"' not in html
    assert "DEAD_VARIANTS" in html
    assert "t.id!==\"scient\"" not in html[html.find("function paintThemeChips"):html.find("let uiLayout")]
    paint=html[html.find("function paintThemeChips"):html.find("let uiLayout")]
    assert "DEAD_VARIANTS.has(t.id)" in paint
def test_braid_md_and_work_dock_wired():
    html=(ROOT/"web"/"index.html").read_text(encoding="utf-8")
    assert 'src="/static/md.js' in html
    assert 'src="/static/work-dock.js"' in html
    assert 'id="btnWork"' in html
    assert "window.mdbody_safe" in html
    assert "window.grokWork" in html
    md=(ROOT/"web"/"md.js").read_text(encoding="utf-8")
    assert "function md(" in md
    assert 'class="path-link"' in md
    assert "Ctrl+click to open" in md
    dock=(ROOT/"web"/"work-dock.js").read_text(encoding="utf-8")
    assert "window.grokWork" in dock
    assert "/api/fs/list" in dock
def test_interject_keeps_prior_and_no_auto_cancel_pile():
    html=(ROOT/"web"/"index.html").read_text(encoding="utf-8")
    wrap=html[html.find("function wrapForMode"):html.find("function paintMsgQueue")]
    assert "Drop the in-flight plan" not in wrap
    assert "Keep every prior user message" in wrap
    assert "[Reaction meter" not in wrap
    assert "cancelling the pile" not in html
    assert "nSetup>=" not in html
    send=html[html.find("send.onclick="):html.find("const btnCancelTurn")]
    assert "if(sendInFlight&&!dbl)return" not in send
    keys=html[html.find('box.addEventListener("keydown"'):html.find('box.addEventListener("input"')]
    assert "if(sendInFlight&&!dbl)return" not in keys
    enq=html[html.find("function enqueueMsg"):html.find("function markAgentAttach")]
    assert "paintLocalUserTurn" not in enq
    assert "Queued · " not in enq
    assert "function echoQueuedSend" in html
    echo=html[html.find("function echoQueuedSend"):html.find("async function sendQueuedNow")]
    assert "paintLocalUserTurn" in echo
    now=html[html.find("async function sendQueuedNow"):html.find("function enqueueMsg")]
    assert "echoQueuedSend(item)" in now
    drain=html[html.find("async function drainMsgQueue"):html.find("function nextId")]
    assert "echoQueuedSend(item)" in drain
    assert "function finishTurnOrKeep" in html
    assert "pendingTools" in html
    assert "command still running" in html
    assert 'id="workNow"' in html
    assert 'id="workKill"' in html
    assert "function paintWorkNow" in html
    assert "function workIsOn" in html
    assert "function fillThoughtBub" in html
    assert html.find('id="feed"') < html.find('id="workLine"') < html.find('id="box"')
    assert 'id="lbPhase"' not in html
    assert 'id="workBoard"' in html
    assert "function hydrateWork" in html
    assert "const HISTORY_PAGE=50" in html
    assert "attachReplay" in html
    assert "function killWork" in html
    assert 'p.kind==="prompt"' in html
    assert 'effortLevels=["low","medium","high","xhigh"]' in html
def test_overlay_layers_and_portals_are_consistent():
    html=(ROOT/"web"/"index.html").read_text(encoding="utf-8")
    braid=(ROOT/"web"/"braid-layout.css").read_text(encoding="utf-8")
    cockpit=(ROOT/"web"/"cockpit-features.js").read_text(encoding="utf-8")
    for token in ("--z-app-chrome:100","--z-modal:1000","--z-tour:1200","--z-menu:1300","--z-popover:1310"):
        assert token in html
    assert "z-index:var(--z-app-chrome)!important" in html
    assert ".sheet{display:none;position:fixed;inset:0;z-index:var(--z-modal)" in html
    assert "z-index:var(--z-popover)!important" in braid
    assert 'document.body.appendChild(sm)' in cockpit
    assert 'requestAnimationFrame(place)' in cockpit
    sess=html[html.find("function placeSessFilterPop"):html.find("function syncSessFilterChrome")]
    assert "document.body.appendChild(pop)" in sess
    assert 'pop.style.zIndex="var(--z-popover)"' in sess
    rx=html[html.find("function showRxPop"):html.find("function bindMsgPress")]
    assert "document.body.appendChild(p)" in rx
def test_theme_is_bootstrapped_before_styles_load():
    html=(ROOT/"web"/"index.html").read_text(encoding="utf-8")
    head=html[:html.find('<link rel="stylesheet"')]
    assert 'root.setAttribute("data-variant",variant)' in head
    assert 'root.setAttribute("data-mode",mode)' in head
    assert 'variant==="grok"?(mode==="light"?"#f4f4f5":"#111113")' in head
def test_agent_restart_reattaches_active_session():
    html=(ROOT/"web"/"index.html").read_text(encoding="utf-8")
    fn=html[html.find("async function reattachSessionAfterHubRestart"):html.find("(function(){var f=document.getElementById")]
    assert 'markAgentAttach(attachId,false)' in fn
    assert 'req("session/load",{sessionId:attachId,cwd:attachCwd,mcpServers:[]},12000)' in fn
    assert 'markAgentAttach(attachId,true)' in fn
    assert "await reattachSessionAfterHubRestart()" in fn
def test_archive_skin_supports_braid_and_legacy():
    html=(ROOT/"web"/"index.html").read_text(encoding="utf-8")
    skin=(ROOT/"web"/"grok-archive-skin.css").read_text(encoding="utf-8")
    cockpit=(ROOT/"web"/"cockpit-features.js").read_text(encoding="utf-8")
    link='<link rel="stylesheet" href="/static/grok-archive-skin.css?v=19"/>'
    assert link in html
    assert html.find("</style>") < html.find(link) < html.find("katex.min.css")
    assert 'html[data-layout="braid"][data-variant="grok"]' in skin
    assert 'html[data-layout="legacy"][data-variant="grok"]' in skin
    assert '--archive-content-max: 720px' in skin
    assert '--braid-sidebar: 260px' in skin
    assert 'background: transparent !important' in skin
    assert 'flex-wrap: wrap !important' in skin
    assert 'data-variant="scient"' not in skin
    assert "openAppUrl(v,{sameWindowFallback:true})" in html
    assert "window.openAppUrl" in cockpit
    assert "window.paintFootQuiet" in cockpit
    assert 'btnSkills.style.display=on?"":"none"' in html
    assert "encodeURIComponent(cwd)" in html
    assert "encodeURIComponent(cwd||" not in html
    assert "sidebar-collapsed .btn-settings.foot-settings" in html
    assert 'fetch("/api/companion/state"' in html
    assert ':2423/motion/state' not in html
    assert 'isDemoMode()&&expectSid.startsWith("demo-")' in html
    assert 'attachCwd&&!isDemoMode()' in html
def test_agent_bar_and_session_rail_stay_put():
    html=(ROOT/"web"/"index.html").read_text(encoding="utf-8")
    skin=(ROOT/"web"/"grok-archive-skin.css").read_text(encoding="utf-8")
    braid=(ROOT/"web"/"braid-layout.css").read_text(encoding="utf-8")
    work=html[html.find(".work-line{"):html.find(".work-line{")+420]
    assert "display:flex" in work
    assert "display:none" not in work
    on=html[html.find('.work-line[data-on="1"]'):html.find('.work-line[data-on="1"]')+80]
    assert "display:flex" not in on
    assert "function paintWorkNow" in html
    paint=html[html.find("function paintWorkNow"):html.find("function applyWorkJob")]
    assert "workTimer" not in paint
    assert "workTick" not in paint
    assert "bits.join(" in paint
    assert "function applySessRow" in html
    assert "function sessRowClass" in html
    assert "function syncSessionWorkMarks" in html
    assert "structSig" in html
    render=html[html.find("function renderSessions"):html.find("const HORIZON_PUNS")]
    assert "applySessRow(existing" in render
    assert "syncSessionWorkMarks" in html[html.find('method==="_x.ai/work/changed"'):html.find('method==="_x.ai/queue/changed"')]
    assert 'html[data-variant="grok"] .work-line' in skin
    assert 'html[data-variant="grok"] #picker.panel.on' in skin
    assert "function isPlaceholderSid" in html
    assert "missing:true" in html[html.find("async function paintDiskHistory"):html.find("async function loadOlderHistory")]
    assert "if(!ok&&lastErr&&!/invalid params" in html
    assert "border-top: none !important" in skin
    assert ".thought-row .nm" in skin
    assert "font-style: italic" in skin
    assert "border-radius: 22px 22px 8px 22px" in skin
    assert "border-left: 3px solid #52525b" in skin
    assert "background: #c4c4c8 !important" in skin
    assert "#railHint" in skin
    assert 'id="footQuiet"' in html
    assert 'id="btnStatusDebug"' in html
    assert "function paintFootQuiet" in html
    assert "function toggleStatusDebug" in html
    assert "window.paintFootQuiet" in html
    assert 'id="agentRail"' in html
    assert 'id="agentRailList"' in html
    assert "function placeAgentView" in html
    assert "function dismissAgentView" in html
    assert "function syncAgentRail" in html
    assert "function bindAgentRail" in html
    assert "function paintAgentJobs" in html
    assert "placeAgentView(el)" in html
    assert "placeAgentView(row)" in html
    assert "clearAgentRail()" in html
    assert ".agent-rail" in skin
    assert "2026-09-01-pub-priv" in html
    assert "else showPage(\"setup\",true)" not in html[html.find("const doAuto="):html.find("const forceTour=")]
    assert "const linking=connecting||!!(ws&&(ws.readyState===0||ws.readyState===1))" in html
    assert "#chatStage:not(.on){display:none!important" in html
    assert "#chatStage:not(.on){display:none!important" in braid
    assert 'src="/static/chat-runtime.js?v=2026-09-01-pub-priv"' in html
    assert "braid-layout.css?v=1.8.28" in html
    assert "grok-archive-skin.css?v=19" in html
    assert "function stampMsgRow" in html
    assert "className=\"msg-at\"" in html
    assert "_x.ai/remote/loop_fire" in html
    assert "bits.length>0" in html
    assert "inset 3px 0 0" not in html
    assert "inset 3px 0 0" not in braid
    assert "inset 3px 0 0" not in skin
    assert "function uniqDotBits" in html
    assert "function collapseRepeatNote" in html
    assert "function workLineKind" in html
    assert "if(agentQueueNote)bits.push" not in html
    assert '.work-line{display:flex' in html and "overflow:visible" in html[html.find(".work-line{display:flex"):html.find(".work-line{display:flex")+400]
    assert "else if(t===\"tool_call\"){curAgent=null;curThought=null;curThoughtRow=null}" in html
    assert "work-spin-slot" in html
    assert ".work-line .send-spin[hidden]{display:none!important}" in html
    assert ".work-line .send-spin[hidden]{visibility:hidden;display:block!important" not in html
    assert "rows.slice(0,-1).forEach(r=>r.classList.add(\"dismissed\"))" in html
    assert "function feedHasUserText" in html
    assert "if(!replaying&&display&&feedHasUserText(display)&&!media)" in html
    assert "/returned nothing/i.test(String(job.detail||\"\"))" in html
    assert ".work-kill,.work-kill[hidden]{display:none!important" in html
    assert "kill.hidden=true" in html
    assert "meta.reset" in html[html.find("async function diskLiveCatchup"):html.find("async function softCatchup")]
    assert "window.grokChat.open" in html
    assert "Do not wait on upstream ensure" in (ROOT/"server.py").read_text(encoding="utf-8")
    hub=(ROOT/"server.py").read_text(encoding="utf-8")
    assert "inbox=asyncio.Queue()" in hub
    assert "heartbeat=45" in hub
    onopen=html[html.find("ws.onopen=async"):html.find("ws.onmessage=")]
    assert onopen.find("_x.ai/remote/hello") < onopen.find('req("initialize"')
    assert onopen.find("fetchSessions") > onopen.find('req("initialize"')
    assert "if(connecting||hubReinitBusy)return" in html
    assert "chip._hitchAt" in html
    assert "function settleRailTools" in html
    assert "function dropAckedQueue" in html
    assert "function bindPathOpens" in html
    assert "function openExternalTarget" in html
    assert 'fetch("/api/open"' in html
    bind=html[html.find("function bindPathOpens"):html.find("window.bindPathOpens")]
    assert "openLocInIde" not in bind
    assert "e.ctrlKey||e.metaKey" in bind
    assert "a.md-a" in bind
    cockpit=(ROOT/"web"/"cockpit-features.js").read_text(encoding="utf-8")
    wire=cockpit[cockpit.find("function wireToolPathClicks"):cockpit.find("function injectChrome")]
    assert "openLocInIde" not in wire
    assert "window.bindPathOpens" in wire
    hub=(ROOT/"server.py").read_text(encoding="utf-8")
    assert "app.router.add_post(\"/api/open\",open_external)" in hub
    assert "def classify_open_target" in hub
    assert "function selectionIn" in html
    assert "if(selectionIn(bub))return" in html[html.find("function bindMsgPress"):html.find("function wireRx")]
    assert ".bub{cursor:text;-webkit-touch-callout:default;-webkit-user-select:text;user-select:text}" in html
    assert "function sessionIsWorking" in html
    assert "d.className=sessRowClass(st)" in html
    assert "sess-dot" in html[html.find("function sessTitleHtml"):html.find("function sessMetaHtml")]
    assert "open-mark" not in html[html.find("function sessTitleHtml"):html.find("function sessMetaHtml")]
    assert "open-mark" not in html[html.find("function paintSessionCurrent"):html.find("function setSelectedSession")]
    assert "2026-09-01-pub-priv" in html
    assert 'id="moreMenuStatus"' not in html
    assert "menu.style.maxHeight" in html[html.find("function placeFixedMenu"):html.find("function protectMath")]
    assert "placeFixedMenu(m,a)" in html[html.find("function showMoreLayer"):html.find("function bindMoreLayers")]
    assert "function sessionNew" in html
    assert 'fetch("/api/session/new"' in html
    assert "await waitAgentAttach(sendSid,2500)" in html
    assert "staleBusy" in html[html.find("async function drainMsgQueue"):html.find("function nextId")]
    assert "#sessList:not([data-ready" not in html
    assert "#sessList:not([data-ready" not in braid
    assert "function revealSessList" in html
    assert "function paintCancelBtn" in html
    assert "return cancelShown" in html[html.find("function workIsOn"):html.find("function collapseRepeatNote")]
    assert "agent_thought_chunk|agent_message_chunk" not in html[html.find("async function diskLiveCatchup"):html.find("async function softCatchup")]
    assert "if(!replaying&&!historyPainting&&!cancelInFlight" in html[html.find("else if(t===\"agent_thought_chunk\")"):html.find("else if(t===\"tool_call\"")]
    assert "socket timeout" in html
    assert "if(!sessionIdsMatch(sessionId,sid))return" in html
    assert "if(evSid&&expectSid&&!sessionIdsMatch(evSid,expectSid))continue" in html
    runtime=(ROOT/"web"/"chat-runtime.js").read_text(encoding="utf-8")
    assert "function createChatRuntime" in runtime
    assert "function idsMatch" in runtime
    assert "belongs" in runtime
    assert "function ensureHome" in runtime
    assert "agent-home-act" in runtime
    assert "placeBatch" in runtime
    assert 'classList.contains("settled")' in runtime
    assert "function turnHasAgentReply" in html
    assert "underReply" in html
    assert "title(id)" in html[html.find("function paintAgentJobs"):html.find("async function hydrateWork")]
def test_idle_chain_uses_seamless_mixamo():
    srv=(ROOT/"motion_service.py").read_text(encoding="utf-8")
    idles=srv[srv.find("IDLES"):srv.find("IDLE_W")]
    life=srv[srv.find("LIFE ="):srv.find("LIFE_HEAD =")]
    extra=srv[srv.find("def extra_life"):srv.find("def weighted")]
    alive=srv[srv.find("async def alive_loop"):]
    assert "talking_on_phone" in idles
    assert "guitar_playing" in idles
    assert "point_ahead" in life
    assert "hand_on_heart" in life
    assert "standing_clap" not in life
    assert "wave_hello" in life
    assert "interact" in life
    assert "female_walk" not in life
    assert "kneel" in extra
    assert "acknowledging" in extra
    assert "pick_chain" in srv
    pc=srv[srv.find("def pick_chain"):srv.find("async def get_alive")]
    assert "c != HOME and c != cur]" in pc
    assert "c != prev" not in pc
    assert "random.random() < 0.99" in pc
    assert "random.random() < 0.04" in pc
    assert "return cur" in pc
    assert "if keep_idle(clip):" in srv[srv.find("async def fire"):srv.find("async def drain_loop")]
    assert "dur = min(dur, 2.6)" in srv
    js=(ROOT/"web"/"xr-motion.js").read_text(encoding="utf-8")
    assert "keepIdle(name)&&(c.duration||1.2)>2.8" in js.replace(" ","")
    assert "keepIdle(name)?2800:8000" in js.replace(" ","")
    assert "IDLE_DWELL" in srv
    assert "/motion/alive" in srv
    assert "LIFE_HEAD" in srv
    head=srv[srv.find("LIFE_HEAD ="):srv.find("ARM_LEFT")]
    soft=srv[srv.find("LIFE_SOFT ="):srv.find("LIFE_HEAD =")]
    assert "look_over_shoulder" not in head
    assert "look_over_shoulder" not in soft
    assert "module_check" in head
    assert "bow_apology" in head
    assert "chin_think" in soft
    assert "waist_side_stretch" in soft
    assert "sun_salute" in soft
    assert "interact" in soft
    assert "bow_apology" in soft
    assert "agree" not in soft
    assert "look_over_shoulder" in life
    assert "def prop_ok(" in srv
    assert "prop idle keeps the arms" in srv
    assert "idle recover" in alive
    assert "uniform(4, 506)" in alive[alive.find('"idle recover"'):alive.find("quiet =")]
    assert "dwell0 >= need0" not in alive[alive.find("nxtb = pick_chain"):alive.find("if not did")]
    assert "stay = nxtb == state.get(\"base\")" in alive[alive.find("nxtb = pick_chain"):alive.find("if not did")]
    assert "if stay:" in alive[alive.find("nxtb = pick_chain"):alive.find("if not did")]
    assert "dwell < need" in alive
    assert "uniform(4, 506)" in alive[alive.find("if dwell < need"):alive.find("pick = pick_chain")]
    em=srv[srv.find("EMOTES"):srv.find("state =")]
    assert '"talk": "chin_think"' in em
    assert "sitting_talking" not in em
    base=srv[srv.find("BASE"):srv.find("EMOTES")]
    assert "sitting" not in base
    js=(ROOT/"web"/"xr-motion.js").read_text(encoding="utf-8")
    assert "warmPool" in js
    assert "guitar_life" in srv[srv.find("async def get_alive"):srv.find("async def alive_loop")]
    assert "arm_right" in srv[srv.find("async def get_alive"):srv.find("async def alive_loop")]
    assert "arm_left" in srv[srv.find("async def get_alive"):srv.find("async def alive_loop")]
    assert "hold_gaze" in srv[srv.find("async def get_alive"):srv.find("async def alive_loop")]
    assert "HOLD_GAZE" in srv
    assert "j.hold_gaze" in js
    assert "HEAD.clear()" in js.replace(" ","")
    assert "bow_apology" in srv[srv.find("HOLD_GAZE"):srv.find("def extra_life")]
    assert "bow_apology" in js[js.find("HEAD=new Set"):js.find("GUITAR=new Set")]
    assert "j.guitar_life" in js
    assert "j.arm_right" in js
    assert "GUITAR.clear()" in js.replace(" ","")
    assert "SOFT.clear()" in js.replace(" ","")
    assert "RIGHT.clear()" in js.replace(" ","")
    assert "LEFT.clear()" in js.replace(" ","")
    assert "idle.fadeOut(0.28)" in js.replace(" ","")
    assert "c.duration>4" in js.replace(" ","")
    assert "pendingBase" in js
    assert "actGesture!==a" in js.replace(" ","")
    assert "c in lasts" not in srv
    assert "uniform(4, 506)" in alive[alive.find('"idle chain"'):alive.find("if busy")]
    assert "nxt = random.uniform(4, 506)" in alive[:alive.find("while True")]
    assert "nxt = random.uniform(4, 506)" in alive[alive.find("if not clients"):alive.find("since += ")]
    assert "nap = random.uniform(4, 506)" in alive[alive.find("while True"):alive.find("if state.get(\"follow_base\")")]
    assert "min(1, len(pool) - 1)" not in srv
    assert "win = REPEAT_WINDOW" in srv
    assert "REPEAT_WINDOW = 10.0" in srv
    assert alive.find("follow_base") < alive.find("if since < nxt")
    assert "since += time.time() - t0" in alive or "since+=time.time()-t0" in alive.replace(" ","")
    assert '"walk"' in srv[srv.find("if clip in TRAVEL"):srv.find("if clip in TRAVEL")+280]
    assert '"up"' in alive[alive.find("random.choices"):alive.find("random.choices")+180]
    assert '"user", "user", "user"' not in alive[alive.find("random.choices"):alive.find("random.choices")+180]
    assert '"left", "right"' in alive[alive.find("random.choices"):alive.find("random.choices")+180]
    assert "last_prop" in srv
    assert "c != lp" in pc
    assert "prefer and random.random() < 0.99" in pc
    assert "FAM" not in srv
    assert "last_fam" not in srv
    assert "fam=False" not in srv
    assert "fadeS*1000+120" in js.replace(" ","")
    assert "fadeS=Math.max(fade,0.5)" in js.replace(" ","")
    assert 'fire(nb, "base", random.uniform(0.5, 0.9), "idle chain")' in srv
    assert "getActIdle()===a" in js.replace(" ","")
    assert "idle.timeScale=0" in js.replace(" ","")
    assert "idl.paused=false" in js.replace(" ","")
    assert "idl.paused=false;idl.timeScale=0.86+Math.random()*0.28" in js.replace(" ","")
    assert "idl.time=(idl.time+" in js.replace(" ","")
    assert "if(idl.timeScale===0)idl.timeScale" not in js.replace(" ","")
    assert "idle after gesture" in srv
    assert "since = 0.0" in alive or "since=0.0" in alive.replace(" ","")
    assert '"dance"' in srv[srv.find("if clip in TRAVEL"):srv.find("if clip in TRAVEL")+360]
    assert "random.random() < 0.66" in pc
    assert "c != HOME]" in pc
    assert "return weighted(alts, [IDLE_W.get(c, 1) for c in alts])" in pc
    assert '"standing_w_briefcase_idle": 3' in srv[srv.find("IDLE_W"):srv.find("IDLE_DWELL")]
    assert "pick == cur" in srv or "pick==cur" in srv.replace(" ","")
    assert "if quiet >= IDLE_DWELL.get" in srv
    assert "random.random() < 0.90" not in srv[srv.find("quiet = "):srv.find("def ok")]
    assert "!getActIdle()" in js.replace(" ","")
    assert "prev.paused=false" in js.replace(" ","")
    assert "prev.timeScale=0.86+Math.random()*0.28" in js.replace(" ","")
    assert "prev.time=(prev.time+" in js.replace(" ","")
    assert "oc.duration*0.15" in js.replace(" ","")
    assert "if(prev.timeScale===0)prev.timeScale=0.94" not in js.replace(" ","")
    assert "span/Math.abs(ts)*1000" in js.replace(" ","")
    assert "idle rephase" in srv
    assert "await fire(cur," in srv or "await fire(cur ," in srv
    em=srv[srv.find("EMOTES"):srv.find("state =")]
    assert '"excited": "excited_bounce"' in em
    assert '"jump": "excited_bounce"' in em
    assert "a.timeScale=0.86" in js.replace(" ","")
    assert '"jump"' in srv[srv.find("if clip in TRAVEL"):srv.find("if clip in TRAVEL")+480]
    assert "fade>=1.05" not in js.replace(" ","")
    assert "getActIdle()===a" in js.replace(" ","")
    jsIdle=js.replace(" ","")
    aBlk=jsIdle[jsIdle.find("getActIdle()===a"):jsIdle.find("if(actGesture)")]
    assert "a.timeScale=0.86+Math.random()*0.28" in aBlk
    assert "state.get(\"base\") != clip" in srv or "state.get('base')!=clip" in srv.replace(" ","")
    assert "function endGesture(" in js
    assert 'addEventListener("finished"' in js
    assert '"standing_w_briefcase_idle": 255.0' in srv[srv.find("IDLE_DWELL"):srv.find("LIFE =")]
    assert '"talking_on_phone": 255.0' in srv[srv.find("IDLE_DWELL"):srv.find("LIFE =")]
    assert '"guitar_playing": 255.0' in srv[srv.find("IDLE_DWELL"):srv.find("LIFE =")]
    assert '"kneel"' in srv[srv.find("if clip in TRAVEL"):srv.find("if clip in TRAVEL")+420]
    assert "gestureHold=performance.now()+480" in js.replace(" ","")
    assert '"angry"' in srv[srv.find("if clip in TRAVEL"):srv.find("if clip in TRAVEL")+450]
    assert "nxt - since" in alive or "nxt-since" in alive.replace(" ","")
    assert "clip not in HOLD_GAZE" in alive
    html=(ROOT/"web"/"xr.html").read_text(encoding="utf-8")
    assert "!holding&&motionState.gazeTarget" in html.replace(" ","")
    assert "gazeUntil=performance.now()+2800" in js.replace(" ","")
    assert "gazeUntil=now+2800" in html.replace(" ","")
    assert "lookT=t+2.8" in html.replace(" ","")
    assert "motionState.gz" in html
    assert "sitting_talking" not in html[html.find("You are in the room"):html.find("You are in the room")+800]
    assert "Stay standing" in html
    assert 'if clip == "standing_greeting"' in srv
    assert "FADE_PAD" in srv
    assert 'if clip == "acknowledging"' in srv
    assert "mixerHooked===mixer" in js.replace(" ","")
    assert "function queueBase(" in js
    assert "function flushBase(" in js
    assert "rephase_at" in srv
    em=srv[srv.find("EMOTES"):srv.find("state =")]
    assert '"greet": "wave_hello"' in em
    assert '"sneaky": "look_over_shoulder"' in em
    assert "busy = now < state.get(\"gesture_until\", 0) + fade_pad()" in srv or "busy=now<state.get(\"gesture_until\",0)+fade_pad()" in srv.replace(" ","")
    assert "def fade_pad(" in srv
    assert "jab_cross" in srv[srv.find("if clip in TRAVEL"):srv.find("if clip in TRAVEL")+500]
    assert "if(pbTimer){clearTimeout(pbTimer)" in js.replace(" ","")
    assert "headBone" in html
    em=srv[srv.find("EMOTES"):srv.find("state =")]
    assert '"come": "interact"' in em
    assert "if(pendingBase)queueBase" in js.replace(" ","")
    assert "if(pendingBase){queueBase" not in js.replace(" ","")
    assert "gazeWP" in html
    assert "xrP" in html
    assert "function clientPropOk(" in js
    assert "const HEAD=new Set" in js
    assert "GUITAR=new Set" in js
    assert "curBase===\"guitar_playing\"&&GUITAR.has(clip)" in js.replace(" ","")
    assert "SOFT=new Set" in js
    assert "layer!==\"base\"&&(gestureSkip(name)||!clientPropOk" in js.replace(" ","")
    assert "const HOME=" in js[:js.find("curBase")]
    assert "curBase=HOME" in js.replace(" ","")
    assert "if(d.layer===\"base\")curBase=d.clip" in js.replace(" ","")
    assert "if(d.type===\"state\"&&d.base)" in js.replace(" ","")
    assert '"beckon"' in srv[srv.find("if clip in TRAVEL"):srv.find("if clip in TRAVEL")+520]
    assert "life_head" in js
    assert "life_soft" in js
    assert "function keepIdle(" in js
    assert "if(keepIdle(name))" in js.replace(" ","")
    assert "if(keepIdle(name))a.setEffectiveWeight(1).play()" in js.replace(" ","")
    assert "if(keepIdle(name)){idle.paused=false;idle.timeScale=0.86+Math.random()*0.28" in js.replace(" ","")
    assert "idle.time=(idle.time+" in js.replace(" ","")
    assert "ic.duration*0.15" in js.replace(" ","")
    assert "Math.min(6,ic.duration*0.15)" in js.replace(" ","")
    assert "Math.min(6,c.duration*0.15)" in js.replace(" ","")

    assert "if random.random() < 0.92" not in srv[srv.find("life beat"):srv.find("if not did")]
    assert "0.0 if keep_idle(clip) else FADE_PAD" in srv
    assert "nxtb = pick_chain" in srv[srv.find("did = True"):srv.find("if not did")]
    assert "if quiet >= IDLE_DWELL.get" in srv
    assert "random.random() < 0.90" not in srv[srv.find("quiet = "):srv.find("def ok")]
    assert "baseHold" in js
    assert "baseHold-performance.now()" in js.replace(" ","")
    assert "if(layer===\"base\"&&performance.now()<baseHold)" in js.replace(" ","")
    assert "def keep_idle(" in srv
    assert "clip in ARM_RIGHT" in srv[srv.find("def keep_idle"):srv.find("def fade_pad")]
    assert "return 0.0 if keep_idle" in srv or "return 0.0 if keep_idle" in srv.replace(" ","")
    assert "chin_think" in js[js.find("HEAD=new Set"):js.find("GUITAR=new Set")]
    assert 'LIFE_HEAD + ["chin_think", "hand_on_heart", "blow_kiss"]' in srv
    assert "clip in GUITAR_LIFE" in srv[srv.find("def keep_idle"):srv.find("def fade_pad")]
    assert "blow_kiss" in js[js.find("HEAD=new Set"):js.find("GUITAR=new Set")]
    assert "blow_kiss" in srv[srv.find("ARM_RIGHT"):srv.find("def extra_life")]
    assert "curBase===\"talking_on_phone\"&&SOFT.has(clip)" in js.replace(" ","")
    assert "talking_on_phone\" and clip in LIFE_SOFT" in srv[srv.find("def keep_idle"):srv.find("def fade_pad")]
    em=srv[srv.find("EMOTES"):srv.find("state =")]
    assert '"dance": "excited_bounce"' in em
    assert '"angry": "dismissing_gesture"' in em
    assert '"punch": "dismissing_gesture"' in em
    assert '"punch"' in srv[srv.find("if clip in TRAVEL"):srv.find("if clip in TRAVEL")+560]
    assert "clip not in HOLD_GAZE" in alive
    assert "getClip().name" in js.replace(" ","")
    assert "nm!==String(d.base)" in js.replace(" ","")
    assert "if(!keepIdle(state.lastGesture||\"\"))idl.fadeIn(0.45)" in js.replace(" ","")
    assert "%Math.max(0.01,c.duration)" in js.replace(" ","")
    em=srv[srv.find("EMOTES"):srv.find("state =")]
    assert '"walk": "look_over_shoulder"' in em
    assert '"run": "point_ahead"' in em
    assert '"jog": "waist_side_stretch"' in em
    assert '"squat": "waist_side_stretch"' in em
    assert "if(actGesture){" in js.replace(" ","")
    assert "setTimeout(()=>{try{g.stop()" in js.replace(" ","")
    assert "c.duration>4" in js.replace(" ","")
    assert "c.duration*0.35" in js.replace(" ","")
    assert "Math.min(8,c.duration*0.35)" in js.replace(" ","")
    assert "Math.min(0.45,c.duration*0.2)" in js.replace(" ","")
    assert "ts=0.86+Math.random()*0.28" in js.replace(" ","")
    assert "a.timeScale=0.86+Math.random()*0.28" in js.replace(" ","")
    assert "LIFE_W" not in srv
    assert "2 if clip_dur(c) <= 4.0 else 1" in srv
    assert "function travelSkip(" in js
    assert "gestureSkip(name)||!clientPropOk" in js.replace(" ","")
    assert "want=!holding&&motionState.gazeTarget" in html.replace(" ","")
    assert "want?yaw:0" in html.replace(" ","")
    life=srv[srv.find("LIFE ="):srv.find("LIFE_HEAD =")]
    assert "surprised" not in life
    assert '"sad": "bow_apology"' in srv[srv.find("EMOTES"):srv.find("state =")]
    extra=srv[srv.find("def extra_life"):srv.find("def fade_pad")]
    assert "surprised" in extra
    assert "sad_pose" in extra
    extra=srv[srv.find("def extra_life"):srv.find("def fade_pad")]
    assert "wave_hello" in extra
    assert "standing_clap" in extra
    em=srv[srv.find("EMOTES"):srv.find("state =")]
    assert '"clap": "standing_clap"' in em
    assert '"wave": "wave_hello"' in em
    life=srv[srv.find("LIFE ="):srv.find("LIFE_HEAD =")]
    assert "excited_bounce" not in life
    assert "blow_kiss" in life
    extra=srv[srv.find("def extra_life"):srv.find("def fade_pad")]
    assert "excited_bounce" in extra
    assert "blow_kiss" in extra
    assert "travelSkip(name)||!canLoop(name)" in js.replace(" ","")
    life=srv[srv.find("LIFE ="):srv.find("LIFE_HEAD =")]
    assert "agree" not in life
    extra=srv[srv.find("def extra_life"):srv.find("def fade_pad")]
    assert "agree" in extra
    em=srv[srv.find("EMOTES"):srv.find("state =")]
    assert '"yes": "agree"' in em
    assert '"nod": "agree"' in em
    assert "ARM_LEFT" in srv
    assert "c not in ARM_LEFT" in srv
    assert "waist_side_stretch" in srv[srv.find("ARM_LEFT"):srv.find("def extra_life")]
    assert "chin_think" in srv[srv.find("ARM_LEFT"):srv.find("def extra_life")]
    assert "clip in ARM_LEFT" in srv[srv.find("def prop_ok"):srv.find("def weighted")]
    assert "LEFT=new Set" in js
    assert "curBase===HOME)return!LEFT.has" in js.replace(" ","")
    assert "ARM_HOME" in srv
    assert '"chin_think": "module_check"' in srv
    assert '"interact": "point_ahead"' in srv
    assert "clip in ARM_HOME" in srv
    assert "min(fresh or pool, key=lambda c: recent.get(c, 0.0))" in srv or "min(freshorpool,key=lambda c:recent.get(c,0.0))" in srv.replace(" ","")
    assert "GUITAR_LIFE if b == \"guitar_playing\"" in srv
    drain=srv[srv.find("async def drain_loop"):srv.find("async def play")]
    assert "ARM_HOME" in drain
    assert "min(fresh or pool, key=lambda c: recent.get(c, 0.0))" in srv or "min(freshorpool,key=lambda c:recent.get(c,0.0))" in srv.replace(" ","")
    assert "not remapped and not d.get(\"force\")" in srv or "not remapped and not d.get('force')" in srv
    assert '"agree": "module_check"' in srv[srv.find("ARM_HOME"):srv.find("def extra_life")]
    assert "clip!==\"agree\"" in js.replace(" ","")
    assert "ARM_RIGHT" in srv
    assert "RIGHT=new Set" in js
    assert "curBase===HOME&&RIGHT.has" in js.replace(" ","")
    assert "life_clip" in srv
    assert "life_clip" in srv
    assert "if did and life_clip and keep_idle" not in srv
    assert "if did else random.uniform" not in srv

    assert "function holdGaze(" in js
    assert "holdGaze(name)||!keepIdle(name)" in js.replace(" ","")
    assert '"surprised": "machinamachina_spark"' in srv[srv.find("ARM_HOME"):srv.find("def extra_life")]
    assert "look_over_shoulder" in js[js.find("HEAD=new Set"):js.find("GUITAR=new Set")]
    assert "hand_on_heart" in js[js.find("HEAD=new Set"):js.find("GUITAR=new Set")]
    assert "function holdGaze(clip){return HEAD.has(clip)}" in js.replace(" ","") or "functionholdGaze(clip){returnHEAD.has(clip)}" in js.replace(" ","")
    assert "...h]" in js or ",...h]" in js.replace(" ","")
    assert '"think": "chin_think"' in srv[srv.find("EMOTES"):srv.find("state =")]
    em=srv[srv.find("EMOTES"):srv.find("state =")]
    assert '"thanks": "bow_apology"' in em
    assert '"thank": "bow_apology"' in em
    assert "rephase_at\", 0) < 4" not in srv and "rephase_at', 0)<4" not in srv.replace(" ","")
    assert "rephase_at\", 0) >= 4" not in srv and "rephase_at', 0)>=4" not in srv.replace(" ","")
    assert "uniform(4, 506)" in srv[srv.find("rephase_at"):srv.find("idle rephase")]
    assert '"standing_clap": "wave_hello"' in srv[srv.find("ARM_HOME"):srv.find("def extra_life")]
    em=srv[srv.find("EMOTES"):srv.find("state =")]
    assert '"love": "hand_on_heart"' in em
    assert '"heart": "hand_on_heart"' in em
    assert '"guitar_playing": 3' in srv[srv.find("IDLE_W"):srv.find("IDLE_DWELL")]
    assert '"talking_on_phone": 3' in srv[srv.find("IDLE_W"):srv.find("IDLE_DWELL")]
    assert "standing_clap" in js[js.find("curBase===HOME"):js.find("function holdGaze")]
if __name__=="__main__":
    test_pair_in_upper_right_menus()
    test_sess_filters_core_only_single_line()
    test_scient_and_defunct_module_chips_gone()
    test_braid_md_and_work_dock_wired()
    test_interject_keeps_prior_and_no_auto_cancel_pile()
    test_overlay_layers_and_portals_are_consistent()
    test_theme_is_bootstrapped_before_styles_load()
    test_agent_restart_reattaches_active_session()
    test_archive_skin_supports_braid_and_legacy()
    test_agent_bar_and_session_rail_stay_put()
    test_idle_chain_uses_seamless_mixamo()
    print("ok")
