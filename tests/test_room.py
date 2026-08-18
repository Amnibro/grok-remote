import os,sys,json,time,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
class RoomStore(unittest.TestCase):
    def setUp(s):
        s.d=tempfile.mkdtemp(prefix="grokroom_")
        os.environ["GROK_PLUGIN_DATA"]=s.d
        import importlib,room
        importlib.reload(room)
        s.room=room
        s.room.clear()
    def tearDown(s):
        os.environ.pop("GROK_PLUGIN_DATA",None)
    def test_say_and_read_back(s):
        r=s.room.say("Claude","first line")
        s.assertTrue(r["ok"]);s.assertEqual(r["message"]["id"],1)
        s.room.say("Grok","second line")
        f=s.room.feed()
        s.assertEqual([m["text"] for m in f],["first line","second line"])
        s.assertEqual([m["who"] for m in f],["Claude","Grok"])
    def test_ids_increase_and_since_filters(s):
        for i in range(5):s.room.say("A","m%d"%i)
        s.assertEqual([m["id"] for m in s.room.feed()],[1,2,3,4,5])
        s.assertEqual([m["text"] for m in s.room.feed(since=3)],["m3","m4"])
        s.assertEqual(s.room.feed(since=99),[])
    def test_long_text_is_capped_not_rejected(s):
        r=s.room.say("A","x"*1000)
        s.assertTrue(r["ok"])
        s.assertEqual(len(r["message"]["text"]),s.room.LIMIT)
    def test_newlines_collapse_to_one_line(s):
        r=s.room.say("A","two\nlines   and\tspaces")
        s.assertEqual(r["message"]["text"],"two lines and spaces")
    def test_empty_is_refused(s):
        s.assertFalse(s.room.say("A","   ")["ok"])
        s.assertFalse(s.room.say("A","")["ok"])
        s.assertEqual(s.room.feed(),[])
    def test_who_is_bounded_and_defaulted(s):
        s.assertEqual(s.room.say("","hi")["message"]["who"],"agent")
        s.assertLessEqual(len(s.room.say("N"*99,"hi")["message"]["who"]),32)
    def test_members_lists_recent_speakers(s):
        s.room.say("Claude","a");s.room.say("Grok","b");s.room.say("Claude","c")
        who=[m["who"] for m in s.room.members()]
        s.assertIn("Claude",who);s.assertIn("Grok",who);s.assertEqual(len(who),2)
    def test_members_ignores_old_messages(s):
        s.room.say("Old","a")
        time.sleep(0.05)
        s.assertEqual(s.room.members(window=0.01),[])
    def test_clear_empties_the_room(s):
        s.room.say("A","x");s.room.clear()
        s.assertEqual(s.room.feed(),[])
        s.assertEqual(s.room.say("A","y")["message"]["id"],1)
    def test_survives_a_corrupt_line(s):
        s.room.say("A","good")
        with s.room.store_path().open("a",encoding="utf-8") as f:f.write("{not json\n\n")
        s.room.say("B","also good")
        s.assertEqual([m["text"] for m in s.room.feed()],["good","also good"])
    def test_cli_round_trip(s):
        s.assertEqual(s.room.main(["say","--who","CLI","hello there"]),0)
        s.assertEqual([m["text"] for m in s.room.feed()],["hello there"])
        s.assertEqual(s.room.main(["read"]),0)
        s.assertEqual(s.room.main(["who"]),0)
if __name__=="__main__":unittest.main(verbosity=2)
