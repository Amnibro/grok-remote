from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_pair_in_upper_right_menus():
    html=(ROOT/"web"/"index.html").read_text(encoding="utf-8")
    assert 'id="btnPairPhone"' in html
    assert 'id="btnPairPhoneMore"' in html
    assert "function openPairPhone(" in html
    assert 'window.open("/pair"' in html
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
    logo=html[html.find('id="logo"'):html.find('id="logo"')+120]
    assert "AMNI-SCIENT" not in logo
    assert "GROK BUILD" in logo or "GROK" in logo
    assert 'id="btnDelve"' not in html
    assert "DEAD_VARIANTS" in html
    assert "t.id!==\"scient\"" not in html[html.find("function paintThemeChips"):html.find("let uiLayout")]
    paint=html[html.find("function paintThemeChips"):html.find("let uiLayout")]
    assert "DEAD_VARIANTS.has(t.id)" in paint
def test_braid_md_and_work_dock_wired():
    html=(ROOT/"web"/"index.html").read_text(encoding="utf-8")
    assert 'src="/static/md.js"' in html
    assert 'src="/static/work-dock.js"' in html
    assert 'id="btnWork"' in html
    assert "window.mdbody_safe" in html
    assert "window.grokWork" in html
    md=(ROOT/"web"/"md.js").read_text(encoding="utf-8")
    assert "function md(" in md
    dock=(ROOT/"web"/"work-dock.js").read_text(encoding="utf-8")
    assert "window.grokWork" in dock
    assert "/api/fs/list" in dock
if __name__=="__main__":
    test_pair_in_upper_right_menus()
    test_sess_filters_core_only_single_line()
    test_scient_and_defunct_module_chips_gone()
    test_braid_md_and_work_dock_wired()
    print("ok")
