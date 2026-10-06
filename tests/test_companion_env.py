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
class Linux(unittest.TestCase):
 def test_loginctl_idle(self):
  self.assertEqual(ce.loginctl_idle("IdleHint=no\nIdleSinceHint=0",100),0.0)
  self.assertAlmostEqual(ce.loginctl_idle("IdleHint=yes\nIdleSinceHint=40000000",100),60.0)
  self.assertIsNone(ce.loginctl_idle("",100))
 def test_dbus_numbers(self):
  self.assertEqual(ce._num("(uint32 1500,)"),1500)
  self.assertEqual(ce._num("(uint64 7,)"),7)
  self.assertIsNone(ce._num(""))
 def test_sway_focus(self):
  tree={"nodes":[{"type":"output","nodes":[{"type":"con","name":"vim","focused":False},{"type":"con","name":"term","focused":True,"app_id":"foot"}]}]}
  self.assertEqual(ce._focused(tree)["name"],"term")
 def test_backend_choice(self):
  names=lambda env:[f.__name__ for f in ce._linux_backends(env)]
  self.assertEqual(names({"XDG_CURRENT_DESKTOP":"KDE","XDG_SESSION_TYPE":"wayland","DISPLAY":":0"}),["_kdotool"])
  self.assertEqual(names({"DISPLAY":":0","XDG_SESSION_TYPE":"x11"}),["_xdotool"])
  self.assertEqual(names({"SWAYSOCK":"/run/s","WAYLAND_DISPLAY":"wayland-1"}),["_swaymsg"])
  self.assertEqual(names({}),[])
 def test_missing_tools_degrade(self):
  orig=ce.shutil.which;ce.shutil.which=lambda _:None
  try:
   self.assertEqual(ce._run(["kdotool","getactivewindow"]),"")
   self.assertIn(ce.idle_seconds(),(None,0.0)) if sys.platform.startswith("linux") else None
  finally:ce.shutil.which=orig
if __name__=="__main__":unittest.main()
