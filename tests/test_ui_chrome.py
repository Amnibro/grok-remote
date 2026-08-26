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
    assert "Queued · " in enq
    assert "it.echoed=true" in enq
    assert "function finishTurnOrKeep" in html
    assert "pendingTools" in html
    assert "command still running" in html
    assert 'id="workNow"' in html
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
    assert 'variant==="grok"?(mode==="light"?"#fafafa":"#000000")' in head
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
    link='<link rel="stylesheet" href="/static/grok-archive-skin.css?v=4"/>'
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
    assert 'btnSkills.style.display=on?"":"none"' in html
    assert "encodeURIComponent(cwd)" in html
    assert "encodeURIComponent(cwd||" not in html
    assert "sidebar-collapsed .btn-settings.foot-settings" in html
    assert 'fetch("/api/companion/state"' in html
    assert ':2423/motion/state' not in html
    assert 'isDemoMode()&&expectSid.startsWith("demo-")' in html
    assert 'attachCwd&&!isDemoMode()' in html
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
    print("ok")
