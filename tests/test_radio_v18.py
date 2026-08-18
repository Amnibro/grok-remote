from pathlib import Path
import ast,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
def test_pair_and_health_wired():
    src=(ROOT/"server.py").read_text(encoding="utf-8")
    ast.parse(src)
    assert 'add_get("/pair",pair)' in src
    assert 'add_get("/health/deep",health_deep)' in src
    assert '"ok":True,"ui":True' in src
    assert 'Cache-Control":"no-store"' in src
    assert 'initialize' in src
    assert 'use_leader_mode' in src
    assert 'use_leader=False' in src
    assert 'force=bool(body.get("force") or body.get("restart"))' in src
    assert 'agent already on' in src
    assert "heartbeat=None" in src
    assert "_x.ai/remote/ping" in src
    assert 'session/load' in src
def test_pairing_page():
    from pairing import addresses,page,url_for
    addrs=addresses(2421,"abc",public_host="")
    html=page(addrs,cwd="C:/tmp",have_qr=False,port=2421)
    assert "Point your phone camera" in html
    assert "C:/tmp" in html
    assert "5A48B0" in html or "A88FE8" in html
    assert url_for("192.168.0.7",2421,"abc").endswith("?key=abc&auto=1")
def test_qr_full_frame():
    from pairing import qr_svg,page
    svg=qr_svg("http://192.168.0.7:2421/?key=abc&auto=1")
    assert svg
    assert 'viewBox="' in svg
    assert "preserveAspectRatio" in svg
    html=page([{"ip":"192.168.0.7","name":"Wi-Fi","note":"same net","kind":"lan","rank":5,"url":"http://192.168.0.7:2421/?key=abc&auto=1"}],have_qr=True,port=2421)
    assert 'viewBox="' in html
    assert "overflow:visible" in html
    assert "aspect-ratio" in html
    ui=(ROOT/"web"/"index.html").read_text(encoding="utf-8")
    assert 'id="phoneQrWrap"' in ui
    assert 'border-radius:10px' not in ui[ui.find('id="phoneQr"'):ui.find('id="phoneQr"')+180]
def test_ui_radio_surface():
    html=(ROOT/"web"/"index.html").read_text(encoding="utf-8")
    assert 'id="radioChip"' in html
    assert 'id="chatMeta"' in html
    assert "linkRtt" in html
    assert "stale link" in html
    assert "silent>45000" in html
    assert 'req("session/load"' in html
    assert "90000" in html
    assert "softCatchup" in html
    assert "startPoll" in html
    css=(ROOT/"web"/"braid-layout.css").read_text(encoding="utf-8")
    assert "max-height:2.2em" in css
    assert "lb-extra{display:inline!important" in css
if __name__=="__main__":
    test_pair_and_health_wired()
    test_pairing_page()
    test_qr_full_frame()
    test_ui_radio_surface()
    print("ok")
