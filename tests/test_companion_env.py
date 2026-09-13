import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import companion_env as ce
class Summarize(unittest.TestCase):
 def test_running_and_latest_tool(self):
  jobs=[{"sid":"a","title":"Fix rail","running":1,"updated":100,"tools":[{"title":"Read x","status":"done","updated":90},{"title":"Edit y","status":"running","updated":95}],"asks":[]},{"sid":"b","title":"Old","running":0,"updated":10,"tools":[],"asks":[{"text":"ok to push?","acked":0}]}]
  w=ce.summarize_work(jobs,now=100)
  self.assertEqual(w["running"],1)
  self.assertEqual(w["running_titles"],["Fix rail"])
  self.assertEqual(w["latest_tool"]["title"],"Edit y")
  self.assertEqual(w["open_asks"][0]["text"],"ok to push?")
  self.assertEqual(w["just_finished"],["Old"])
 def test_empty(self):
  w=ce.summarize_work([],now=5)
  self.assertEqual(w["running"],0);self.assertIsNone(w["latest_tool"]);self.assertEqual(w["open_asks"],[])
 def test_snapshot_shape(self):
  s=ce.snapshot([])
  for k in ("ok","at","clock","weekday","foreground","input_idle_s","work"):self.assertIn(k,s)
  self.assertIn("title",s["foreground"])
if __name__=="__main__":unittest.main()
