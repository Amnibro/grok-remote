import os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import server
def test_classify_urls_and_blocks():
    assert server.classify_open_target("https://x.ai/grok")==("url","https://x.ai/grok")
    assert server.classify_open_target("http://127.0.0.1:2421/")[0]=="url"
    assert server.classify_open_target("mailto:a@b.c")==("url","mailto:a@b.c")
    assert server.classify_open_target("www.example.com")==("url","https://www.example.com")
    assert server.classify_open_target("javascript:alert(1)")==(None,"blocked")
    assert server.classify_open_target("data:text/html,hi")==(None,"blocked")
    assert server.classify_open_target("")==(None,"empty")
def test_classify_existing_path():
    with tempfile.TemporaryDirectory() as d:
        f=Path(d)/"readme.md"
        f.write_text("x",encoding="utf-8")
        kind,val=server.classify_open_target(str(f))
        assert kind=="path"
        assert os.path.normcase(os.path.abspath(val))==os.path.normcase(os.path.abspath(str(f)))
        kind2,val2=server.classify_open_target("readme.md",cwd=d)
        assert kind2=="path"
        assert os.path.normcase(os.path.abspath(val2))==os.path.normcase(os.path.abspath(str(f)))
        assert server.classify_open_target("nope-xyz.md",cwd=d)==(None,"missing")
        kind3,val3=server.classify_open_target("📄 "+str(f))
        assert kind3=="path"
if __name__=="__main__":
    test_classify_urls_and_blocks()
    test_classify_existing_path()
    print("ok")
