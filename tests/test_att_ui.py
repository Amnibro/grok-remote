from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_ui_stashes_and_hydrates_atts():
 html=(ROOT/"web"/"index.html").read_text(encoding="utf-8")
 assert "function stashFiles(" in html
 assert "function hydrateAtts(" in html
 assert "function contentMedia(" in html
 assert "function attNode(" in html
 assert 'fetch("/api/att"' in html
 assert "f._att" in html
 assert "hydrateAtts(openId)" in html
 assert "running=CASE WHEN" not in (ROOT/"work_board.py").read_text(encoding="utf-8")
 srv=(ROOT/"server.py").read_text(encoding="utf-8")
 assert 'add_get("/api/att"' in srv
 assert 'add_post("/api/att"' in srv
 assert "ingest_prompt" in srv
 assert "has_media" in srv
if __name__=="__main__":
 test_ui_stashes_and_hydrates_atts();print("ok")
