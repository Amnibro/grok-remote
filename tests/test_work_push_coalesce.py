"""Opening a chat replays its whole transcript over the hub socket. Every replayed tool_call used to
fire its own _x.ai/work/changed, and the client rebuilds the session rail on each one - the desktop
rail flicker. Baseline:
  GROK_SERVER_PY=backups/server.py.v1.9.18_pre_workpush.bak python -m unittest tests.test_work_push_coalesce
"""
import os,sys,json,asyncio,importlib.util,importlib.machinery,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
def load_server():
    p=Path(os.environ.get("GROK_SERVER_PY") or (ROOT/"server.py"))
    if not p.is_absolute():p=ROOT/p
    spec=importlib.util.spec_from_file_location("srv_wp",p,loader=importlib.machinery.SourceFileLoader("srv_wp",str(p)))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class FakeClient:
    def __init__(s):s.sent=[];s.closed=False
    async def send_str(s,d):s.sent.append(d)
    async def close(s):s.closed=True
    def count(s,method):
        n=0
        for d in s.sent:
            try:
                if json.loads(d).get("method")==method:n+=1
            except Exception:pass
        return n
class WorkPushCoalesce(unittest.IsolatedAsyncioTestCase):
    SID="01a02cd3-4030-7d13-9e1d-837bb815083b"
    REPLAY=250
    async def asyncSetUp(s):
        s.mod=load_server();s.tmp=tempfile.mkdtemp(prefix="wpush_")
        s.hub=s.mod.AgentHub("ws://127.0.0.1:2419/ws")
        s.hub.work=s.mod.WorkBoard(str(Path(s.tmp)/"w.sqlite"))
        s.c=FakeClient();s.hub.clients.add(s.c)
    async def test_a_replay_does_not_repaint_the_rail_per_event(s):
        for i in range(s.REPLAY):
            await s.hub._from_agent(json.dumps({"jsonrpc":"2.0","method":"session/update","params":{
                "sessionId":s.SID,"update":{"sessionUpdate":"tool_call_update","toolCallId":"call-%d"%i,"status":"completed"}}}))
        await asyncio.sleep(1.2)
        n=s.c.count("_x.ai/work/changed")
        s.assertGreater(n,0,"the work board must still reach the client")
        s.assertLess(n,20,"%d work/changed frames for %d replayed events · the client rebuilds the session rail on each one, which is the rail flicker"%(n,s.REPLAY))
    async def test_a_live_turn_still_pushes_promptly(s):
        await s.hub._from_agent(json.dumps({"jsonrpc":"2.0","method":"session/update","params":{
            "sessionId":s.SID,"update":{"sessionUpdate":"tool_call","toolCallId":"call-live","status":"in_progress","title":"grep"}}}))
        await asyncio.sleep(0.25)
        s.assertGreaterEqual(s.c.count("_x.ai/work/changed"),1,"a live turn must push the board without waiting for a debounce window")
if __name__=="__main__":unittest.main()
