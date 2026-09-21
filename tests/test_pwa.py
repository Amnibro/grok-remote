from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
def test_pwa_files():
    man=(ROOT/"web"/"manifest.webmanifest").read_text(encoding="utf-8")
    assert '"name": "Grok Remote"' in man
    assert '"start_url": "/?auto=1"' in man
    assert '"display": "standalone"' in man
    assert "/static/icon-192.png" in man
    assert "/static/icon-512.png" in man
    sw=(ROOT/"web"/"sw.js").read_text(encoding="utf-8")
    assert "serviceWorker" not in sw or "skipWaiting" in sw
    assert "skipWaiting" in sw
    assert 'p === "/ws"' in sw or 'p==="/ws"' in sw.replace(" ","")
    for n in ("icon-180.png","icon-192.png","icon-512.png","icon-maskable-512.png"):
        p=ROOT/"web"/n
        assert p.is_file() and p.stat().st_size>200
def test_pwa_html_and_hub():
    html=(ROOT/"web"/"index.html").read_text(encoding="utf-8")
    assert 'rel="manifest" href="/manifest.webmanifest"' in html
    assert 'rel="apple-touch-icon" href="/static/icon-180.png"' in html
    assert 'id="pwaBanner"' in html
    assert 'id="btnInstallApp"' in html
    assert 'id="btnAwayHome"' in html
    assert 'id="awayHome"' in html
    assert "navigator.serviceWorker.register(\"/sw.js\"" in html
    assert "2026-09-12-quiet-copy" in html
    assert 'id="publicUrl"' in html
    assert 'id="btnCfTunnel"' in html
    assert "amni-scient" not in html
    assert "your-hostname.example" in html
    assert "qrserver.com" not in html
    assert "isPublicView" in html
    assert "/api/pair/unlock" in (ROOT/"server.py").read_text(encoding="utf-8")
    srv=(ROOT/"server.py").read_text(encoding="utf-8")
    assert 'add_get("/manifest.webmanifest",pwa_manifest)' in srv
    assert 'add_get("/sw.js",pwa_sw)' in srv
    assert 'add_get("/api/net",net_get)' in srv
    assert 'add_post("/api/net/tailscale-serve",net_tailscale_serve)' in srv
    assert 'add_post("/api/net/public",net_public_set)' in srv
    assert 'add_post("/api/net/cloudflare-tunnel",net_cloudflare_tunnel)' in srv
    assert "request_is_proxied" in srv
    assert '"pwa"' in srv
    lib=(ROOT/"desktop-tauri"/"src-tauri"/"src"/"lib.rs").read_text(encoding="utf-8")
    assert "2026-09-12-quiet-copy" in lib
def test_https_card():
    from pairing import addresses,page,url_for
    net={"ip":"100.64.0.10","dns":"pc.tailnet.ts.net","serve":True,"ok":True}
    addrs=addresses(2421,"k",public_host="",net=net)
    kinds=[a["kind"] for a in addrs]
    assert "https" in kinds
    https=[a for a in addrs if a["kind"]=="https"][0]
    assert https["url"].startswith("https://pc.tailnet.ts.net/")
    html=page(addrs,have_qr=False,port=2421,net=net)
    assert "HTTPS is on" in html
    assert "<button type=button id=btnServe>" not in html
    assert url_for("pc.tailnet.ts.net",443,"k",https=True).endswith("?key=k&auto=1")
def test_public_origin_and_internet_card():
    from public_net import parse_public_origin
    from pairing import addresses,page
    p=parse_public_origin("remote.amni-scient.com",default_port=2421)
    assert p["https"] is True
    assert p["port"]==443
    assert p["origin"]=="https://remote.amni-scient.com"
    assert p["kind"]=="pub"
    q=parse_public_origin("https://chat.example.com:8443")
    assert q["https"] is True and q["port"]==8443
    r=parse_public_origin("https://remote.example.test",default_port=2421)
    assert r["port"]==443
    assert r["origin"]=="https://remote.example.test"
    t=parse_public_origin("https://abc.trycloudflare.com",default_port=2421)
    assert t["origin"]=="https://abc.trycloudflare.com"
    w=parse_public_origin("203.0.113.9",default_port=2421)
    assert w["https"] is False
    assert w["port"]==2421
    assert w["origin"]=="http://203.0.113.9:2421"
    addrs=addresses(2421,"k",public_host="remote.amni-scient.com",net={})
    pub=[a for a in addrs if a["kind"]=="pub"]
    assert pub and pub[0]["rank"]==8
    assert pub[0]["url"].startswith("https://remote.amni-scient.com/")
    assert "key=" not in pub[0]["url"]
    assert "t=" in pub[0]["url"]
    html=page(addrs,have_qr=False,port=2421,net={},pin="123456",npub="npub1test")
    assert "btnSavePublic" in html
    assert "btnCfTunnel" in html
    assert "Cloudflare" in html
    assert "123456" in html
    assert "npub1test" in html
    assert "your-hostname.example" in html
def test_pair_token_and_nostr_nip04():
    from public_net import pair_pin,pair_token,pair_unlock_ok
    from nostr_bridge import nip04_encrypt,nip04_decrypt,_priv_pub,npub_encode
    from server import public_safe_cfg as psc
    pin=pair_pin("secret")
    tok=pair_token("secret")
    assert len(pin)==6 and pin.isdigit()
    assert len(tok)==32
    assert "secret" not in tok
    assert pair_unlock_ok("secret",tok,pin)
    assert not pair_unlock_ok("secret",tok,"000000")
    assert not pair_unlock_ok("secret","0"*32,pin)
    a,b=_priv_pub();c,d=_priv_pub()
    msg="hello from nostr"
    ct=nip04_encrypt(a,d,msg)
    assert msg not in ct
    assert nip04_decrypt(c,b,ct)==msg
    assert npub_encode(b).startswith("npub1")
    red=psc({"lan_ip":"192.168.0.7","ui":"http://192.168.0.7:2421/?key=abc","cwd":"C:/x","public_origin":"https://host.example"})
    assert red["lan_ip"]==""
    assert "key=" not in red["ui"]
    assert red["public_origin"]==""
def test_proxy_does_not_skip_pairing_key():
    from types import SimpleNamespace
    from server import request_is_proxied,request_is_loopback
    class H(dict):
        def get(self,k,default=None):
            return dict.get(self,k,default)
    def req(headers,remote="127.0.0.1"):
        return SimpleNamespace(headers=H(headers),remote=remote)
    assert request_is_loopback(req({}))
    assert not request_is_loopback(req({"CF-Ray":"abc"}))
    assert not request_is_loopback(req({"X-Forwarded-For":"1.2.3.4"}))
    assert request_is_proxied(req({"CF-Connecting-IP":"8.8.8.8"}))
    assert request_is_proxied(req({"X-Forwarded-Proto":"https"}))
    src=(ROOT/"server.py").read_text(encoding="utf-8")
    assert "This public URL does not skip the key" in src
    i=src.find("This public URL does not skip the key")
    chunk=src[max(0,i-900):i+200]
    assert "Open phone link" not in chunk
    assert "lan_ip()" not in chunk
if __name__=="__main__":
    test_pwa_files()
    test_pwa_html_and_hub()
    test_https_card()
    test_public_origin_and_internet_card()
    test_pair_token_and_nostr_nip04()
    test_proxy_does_not_skip_pairing_key()
    print("ok")
