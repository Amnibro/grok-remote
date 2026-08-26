import sys,time,tempfile,unittest,importlib.util,importlib.machinery,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
def load():
    p=Path(os.environ.get("GROK_WORK_BOARD") or (ROOT/"work_board.py"))
    if not p.is_absolute():p=ROOT/p
    spec=importlib.util.spec_from_file_location("wb_under_test",p,loader=importlib.machinery.SourceFileLoader("wb_under_test",str(p)))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class StallHeal(unittest.TestCase):
    SID="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    def setUp(s):
        s.mod=load();s.d=tempfile.mkdtemp(prefix="wbstall_")
        s.b=s.mod.WorkBoard(str(Path(s.d)/"w.sqlite"))
    def _age(s,secs):
        import sqlite3
        c=sqlite3.connect(str(Path(s.d)/"w.sqlite"),isolation_level=None)
        old=time.time()-secs
        c.execute("UPDATE jobs SET last_user_at=?,updated=? WHERE sid=?",(old,old+0.2,s.SID));c.close()
    def test_accepted_prompt_with_no_reply_stops_spinning(s):
        s.b.note_prompt(s.SID,"do the thing")
        s.assertTrue(s.b.snapshot(s.SID)[0]["running"],"a fresh prompt is running")
        s._age(600)
        j=s.b.snapshot(s.SID)[0]
        s.assertFalse(j["running"],"a prompt the agent answered with NOTHING must stop spinning · this is the forever-spinner")
        s.assertEqual(j["phase"],"stalled")
    def test_a_live_turn_is_never_marked_stalled(s):
        s.b.note_prompt(s.SID,"long job")
        s._age(600)
        s.b.note_update(s.SID,{"sessionUpdate":"agent_thought_chunk","content":{"type":"text","text":"thinking"}},{})
        j=s.b.snapshot(s.SID)[0]
        s.assertNotEqual(j["phase"],"stalled","an agent that is still streaming must never be called stalled")
if __name__=="__main__":unittest.main()
