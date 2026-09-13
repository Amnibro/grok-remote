"""Regression: an upstream drop must not wedge a session id, and a slow client must not be
muted while its socket stays open. Run against the pre-fix backup to prove it fails there:
  GROK_SERVER_PY=backups/server.py.v1.9.15_pre_session_wedge.bak python -m unittest tests.test_hub_session_wedge -v
"""
import os,sys,json,asyncio,importlib.util,importlib.machinery,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
def load_server():
    p=Path(os.environ.get("GROK_SERVER_PY") or (ROOT/"server.py"))
    if not p.is_absolute():p=ROOT/p
    spec=importlib.util.spec_from_file_location("server_under_test",p,loader=importlib.machinery.SourceFileLoader("server_under_test",str(p)))
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
class FakeWS:
    def __init__(s,stall=False):
        s.sent=[];s.closed=False;s.stall=stall
    async def send_str(s,data):
        if s.stall:await asyncio.sleep(30)
        s.sent.append(data)
    async def close(s):s.closed=True
    def loads(s,method):
        out=[]
        for d in s.sent:
            try:o=json.loads(d)
            except Exception:continue
            if o.get("method")==method:out.append(o)
        return out
class HubSessionWedge(unittest.IsolatedAsyncioTestCase):
    SID="11111111-2222-3333-4444-555555555555"
    def setUp(s):
        s.mod=load_server()
        s.tmp=tempfile.mkdtemp(prefix="grokwedge_")
        s.hub=s.mod.AgentHub("ws://127.0.0.1:2419/ws")
        s.hub.work=s.mod.WorkBoard(str(Path(s.tmp)/"work.sqlite"))
        async def ensure(*a,**k):return s.hub._agent is not None and not s.hub._agent.closed
        s.hub.ensure=ensure
    def up(s):
        ws=FakeWS();s.hub._agent=ws;s.hub._alive=True;return ws
    async def load(s,client,rid=1):
        await s.hub._to_agent(client,json.dumps({"jsonrpc":"2.0","id":rid,"method":"session/load","params":{"sessionId":s.SID,"cwd":"."}}))
        await asyncio.sleep(0.3)
    async def finish_load(s,ws):
        fwd=ws.loads("session/load")
        s.assertTrue(fwd,"session/load never reached the agent")
        await s.hub._from_agent(json.dumps({"jsonrpc":"2.0","id":fwd[-1]["id"],"result":{"modes":{}}}))
        await asyncio.sleep(0.05)
    async def test_upstream_drop_midload_does_not_wedge_the_session(s):
        ws=s.up()
        c1=FakeWS()
        await s.load(c1)
        s.assertTrue(ws.loads("session/load"),"first load should reach the agent")
        await s.hub._close_unlocked(keep_init=False)
        ws2=s.up()
        c2=FakeWS()
        await s.load(c2,rid=2)
        s.assertTrue(ws2.loads("session/load"),"after an upstream drop the next session/load must go upstream again, not wait on a dead Event")
    async def test_prompt_after_drop_is_not_stalled(s):
        ws=s.up()
        await s.load(FakeWS())
        await s.hub._close_unlocked(keep_init=False)
        ws2=s.up()
        c=FakeWS()
        await s.hub._to_agent(c,json.dumps({"jsonrpc":"2.0","id":9,"method":"session/prompt","params":{"sessionId":s.SID,"prompt":[{"type":"text","text":"hi"}]}}))
        await asyncio.sleep(0.3)
        s.assertTrue(ws2.loads("session/prompt"),"a prompt must not sit behind a load event the dead upstream left unset")
    async def test_cached_load_is_dropped_when_the_agent_restarts(s):
        ws=s.up()
        await s.load(FakeWS())
        await s.finish_load(ws)
        await s.hub._close_unlocked(keep_init=False)
        ws2=s.up()
        await s.load(FakeWS(),rid=3)
        s.assertTrue(ws2.loads("session/load"),"a load cached from the old agent process must not be replayed to a client the new agent never loaded")
    async def test_second_client_joins_an_inflight_load(s):
        ws=s.up()
        await s.load(FakeWS())
        c2=FakeWS()
        await s.load(c2,rid=7)
        s.assertEqual(len(ws.loads("session/load")),1,"a concurrent attach should join the in-flight load, not double it")
        await s.finish_load(ws)
        await asyncio.sleep(0.05)
        s.assertTrue(any(json.loads(d).get("id")==7 for d in c2.sent),"the joined client must get the load result")
    async def test_load_timeout_does_not_wedge_the_session(s):
        s.mod.RPC_REPLY_TIMEOUT["session/load"]=0.05
        ws=s.up()
        c1=FakeWS()
        await s.load(c1)
        s.assertTrue(ws.loads("session/load"),"first load should reach the agent")
        await asyncio.sleep(0.25)
        c2=FakeWS()
        await s.load(c2,rid=2)
        s.assertEqual(len(ws.loads("session/load")),2,"a timed-out session/load must drop the lock so the next attach can reach the agent")
        errs=[json.loads(d) for d in c1.sent if json.loads(d).get("error")]
        s.assertTrue(errs,"the waiting client must get the load timeout")
    async def test_cid_reconnect_rebinds_inflight_rpc(s):
        ws=s.up()
        c1=FakeWS();c2=FakeWS()
        await s.hub._claim_cid(c1,"c-phone-1")
        await s.hub._to_agent(c1,json.dumps({"jsonrpc":"2.0","id":3,"method":"session/new","params":{"cwd":"."}}))
        await asyncio.sleep(0.05)
        s.assertTrue(ws.loads("session/new"),"session/new must reach the agent")
        fwd=ws.loads("session/new")[-1]
        await s.hub._claim_cid(c2,"c-phone-1")
        await s.hub._from_agent(json.dumps({"jsonrpc":"2.0","id":fwd["id"],"result":{"sessionId":"aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"}}))
        s.assertTrue(any(json.loads(d).get("id")==3 and "result" in json.loads(d) for d in c2.sent),"the reconnected phone must get the session/new result")
    async def test_wait_for_exit_does_not_block_the_pump(s):
        src=(ROOT/"server.py").read_text(encoding="utf-8")
        wait=src[src.find('if method in ("terminal/wait_for_exit"'):src.find("if method==\"terminal/kill\"")]
        s.assertIn("asyncio.create_task(_later())",wait)
        s.assertIn("RPC_REPLY_TIMEOUT",src)
        s.assertIn('app.router.add_post("/api/session/new",session_new_http)',src)
        s.assertIn("_rebind_client_pending",src)
        expire=src[src.find("async def _rpc_expire"):src.find("async def _from_agent")]
        s.assertIn("_load_finish(sid,keep=False)",expire)
        s.assertIn('"session/load"',expire)
    async def test_unreachable_client_is_closed_not_silently_muted(s):
        s.up()
        slow=FakeWS(stall=True)
        s.hub.clients.add(slow)
        s.hub._client_seq.append(slow)
        s.mod.BROADCAST_SEND_TIMEOUT=0.2
        await s.hub._broadcast(json.dumps({"jsonrpc":"2.0","method":"session/update","params":{}}))
        s.assertNotIn(slow,s.hub.clients)
        s.assertTrue(slow.closed,"a client the hub gave up on must be closed so it reconnects, not left open answering pings with no data")
if __name__=="__main__":unittest.main()
