from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_pair_in_upper_right_menus():
    html=(ROOT/"web"/"index.html").read_text(encoding="utf-8")
    assert 'id="btnPairPhone"' in html
    assert 'id="btnPairPhoneMore"' in html
    assert "function openPairPhone(" in html
    assert "async function openAppUrl(" in html
    assert 'openAppUrl("/pair",{sameWindowFallback:true})' in html
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
    assert "2026-08-31-settings-menu" in html
    assert "else showPage(\"setup\",true)" not in html[html.find("const doAuto="):html.find("const forceTour=")]
    assert "const linking=connecting||!!(ws&&(ws.readyState===0||ws.readyState===1))" in html
    assert "#chatStage:not(.on){display:none!important" in html
    assert "#chatStage:not(.on){display:none!important" in braid
    assert 'src="/static/chat-runtime.js?v=2026-08-31-settings-menu"' in html
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
    assert "2026-08-31-settings-menu" in html
    assert 'id="moreMenuStatus"' not in html
    assert "menu.style.maxHeight" in html[html.find("function placeFixedMenu"):html.find("function protectMath")]
    assert "placeFixedMenu(m,a)" in html[html.find("function showMoreLayer"):html.find("function bindMoreLayers")]
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
    life=srv[srv.find("LIFE"):srv.find("LIFE_W")]
    extra=srv[srv.find("def extra_life"):srv.find("def weighted")]
    alive=srv[srv.find("async def alive_loop"):]
    assert "talking_on_phone" in idles
    assert "guitar_playing" in idles
    assert "point_ahead" in life
    assert "hand_on_heart" in life
    assert "standing_clap" in life
    assert "wave_hello" in life
    assert "interact" in life
    assert "female_walk" not in life
    assert "kneel" in extra
    assert "acknowledging" in extra
    assert "pick_chain" in srv
    assert "IDLE_DWELL" in srv
    assert "/motion/alive" in srv
    assert "LIFE_HEAD" in srv
    assert "idle recover" in alive
    assert "dwell0 >= need0" in alive
    em=srv[srv.find("EMOTES"):srv.find("state =")]
    assert '"talk": "chin_think"' in em
    assert "sitting_talking" not in em
    base=srv[srv.find("BASE"):srv.find("EMOTES")]
    assert "sitting" not in base
    js=(ROOT/"web"/"xr-motion.js").read_text(encoding="utf-8")
    assert "warmPool" in js
    assert "idle.fadeOut(0.28)" in js.replace(" ","")
    assert "c.duration>8" in js.replace(" ","")
    assert "pendingBase" in js
    assert "actGesture!==a" in js.replace(" ","")
    assert "lasts" in alive
    assert alive.find("follow_base") < alive.find("if since < nxt")
    assert "since += time.time() - t0" in alive or "since+=time.time()-t0" in alive.replace(" ","")
    assert '"walk"' in srv[srv.find("if clip in TRAVEL"):srv.find("if clip in TRAVEL")+280]
    assert '"up"' in alive[alive.find("random.choices"):alive.find("random.choices")+180]
    assert "last_prop" in srv
    assert "FAM =" in srv or "FAM=" in srv.replace(" ","")
    assert "fadeS*1000+120" in js.replace(" ","")
    assert "getActIdle()===a" in js.replace(" ","")
    assert "idle.paused=true" in js.replace(" ","")
    assert "idl.paused=false" in js.replace(" ","")
    assert "idle after gesture" in srv
    assert "since = 0.0" in alive or "since=0.0" in alive.replace(" ","")
    assert '"dance"' in srv[srv.find("if clip in TRAVEL"):srv.find("if clip in TRAVEL")+360]
    assert "random.random() < 0.58" in srv
    assert "pick == cur" in srv or "pick==cur" in srv.replace(" ","")
    assert "0.62 if state.get(\"base\") == HOME" in srv
    assert "!getActIdle()" in js.replace(" ","")
    assert "prev.paused=false" in js.replace(" ","")
    assert "(c.duration||1.2)-a.time)/ts" in js.replace(" ","")
    assert "idle rephase" in srv
    assert "await fire(cur," in srv or "await fire(cur ," in srv
    em=srv[srv.find("EMOTES"):srv.find("state =")]
    assert '"excited": "excited_bounce"' in em
    assert '"jump": "excited_bounce"' in em
    assert "a.timeScale=0.94" in js.replace(" ","")
    assert '"jump"' in srv[srv.find("if clip in TRAVEL"):srv.find("if clip in TRAVEL")+480]
    assert "fade>=1.05" in js.replace(" ","")
    assert "state.get(\"base\") != clip" in srv or "state.get('base')!=clip" in srv.replace(" ","")
    assert "function endGesture(" in js
    assert 'addEventListener("finished"' in js
    assert "24.0" in srv[srv.find("IDLE_DWELL"):srv.find("LIFE =")]
    assert '"kneel"' in srv[srv.find("if clip in TRAVEL"):srv.find("if clip in TRAVEL")+420]
    assert "gestureHold=performance.now()+480" in js.replace(" ","")
    assert '"angry"' in srv[srv.find("if clip in TRAVEL"):srv.find("if clip in TRAVEL")+450]
    assert "nxt - since" in alive or "nxt-since" in alive.replace(" ","")
    assert "startswith(\"look\")" in alive or "startswith('look')" in alive
    html=(ROOT/"web"/"xr.html").read_text(encoding="utf-8")
    assert "!holding&&motionState.gazeTarget" in html.replace(" ","")
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
    assert "busy = now < state.get(\"gesture_until\", 0) + FADE_PAD" in srv or "busy=now<state.get(\"gesture_until\",0)+FADE_PAD" in srv.replace(" ","")
    assert "jab_cross" in srv[srv.find("if clip in TRAVEL"):srv.find("if clip in TRAVEL")+500]
    assert "if(pbTimer){clearTimeout(pbTimer)" in js.replace(" ","")
    assert "headBone" in html
    em=srv[srv.find("EMOTES"):srv.find("state =")]
    assert '"come": "interact"' in em
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
