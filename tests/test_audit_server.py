import os,sys,json,time,socket,asyncio,sqlite3,tempfile,unittest,subprocess,importlib.util,importlib.machinery
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
_TMP=tempfile.mkdtemp(prefix="grokaudit_")
os.environ.setdefault("GROK_PLUGIN_DATA",_TMP)
def load_server():
    p=Path(os.environ.get("GROK_SERVER_PY") or (ROOT/"server.py"))
    if not p.is_absolute():p=ROOT/p
    spec=importlib.util.spec_from_file_location("srv_audit",p,loader=importlib.machinery.SourceFileLoader("srv_audit",str(p)))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
SRV=load_server()
SID="11111111-2222-3333-4444-555555555555"
SID2="22222222-3333-4444-5555-666666666666"
class FakeWS:
    def __init__(s):s.sent=[];s.closed=False;s.close_code=None
    async def send_str(s,d):s.sent.append(d)
    async def close(s,code=1000,message=b""):s.closed=True;s.close_code=code
    def objs(s):
        out=[]
        for d in s.sent:
            try:out.append(json.loads(d))
            except Exception:pass
        return out
    def method(s,m):return [o for o in s.objs() if o.get("method")==m]
    def reply(s,i):return [o for o in s.objs() if o.get("id")==i and o.get("method") is None]
def board(tmp):return SRV.WorkBoard(str(Path(tmp)/"w.sqlite"))
class HubBase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(s):
        s.tmp=tempfile.mkdtemp(prefix="grokhub_")
        s.hub=SRV.AgentHub("ws://127.0.0.1:1/ws")
        s.hub.work=board(s.tmp)
        async def ensure(*a,**k):return s.hub._agent is not None and not s.hub._agent.closed
        s.hub.ensure=ensure
        s.agent=FakeWS();s.hub._agent=s.agent
    async def fwd(s,method):
        await asyncio.sleep(0.05)
        return s.agent.method(method)
async def _agent_server(handler):
    from aiohttp import web
    app=web.Application();app.router.add_get("/ws",handler)
    r=web.AppRunner(app);await r.setup();site=web.TCPSite(r,"127.0.0.1",0);await site.start()
    return r,site._server.sockets[0].getsockname()[1]
class DeadlockAndHung(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(s):
        from aiohttp import web
        s.web=web;s.mode="silent";s.conns=[]
        async def h(req):
            ws=web.WebSocketResponse();await ws.prepare(req);s.conns.append(ws)
            async for msg in ws:
                try:o=json.loads(msg.data)
                except Exception:continue
                if s.mode=="init-only" and o.get("method")=="initialize":
                    await ws.send_str(json.dumps({"jsonrpc":"2.0","id":o["id"],"result":{"protocolVersion":1}}))
            return ws
        s.runner,s.port=await _agent_server(h)
        s.hub=SRV.AgentHub("ws://127.0.0.1:%d/ws"%s.port);s.hub.agent_port=s.port
        s.hub.work=board(tempfile.mkdtemp())
    async def asyncTearDown(s):
        try:await asyncio.wait_for(s.hub.close(),3)
        except Exception:pass
        await s.runner.cleanup()
    async def test_close_with_live_pump_returns(s):
        s.assertTrue(await s.hub.ensure())
        await asyncio.sleep(0.1)
        await asyncio.wait_for(s.hub.close(),3)
        s.assertIsNone(s.hub._agent)
        s.assertTrue(await asyncio.wait_for(s.hub.ensure(retries=1),5),"ensure after close must reconnect, not hang")
    async def test_agent_side_close_is_cleaned_up_and_reconnects(s):
        s.assertTrue(await s.hub.ensure())
        await asyncio.sleep(0.1)
        await s.conns[-1].close()
        for _ in range(40):
            if s.hub._agent is None:break
            await asyncio.sleep(0.05)
        s.assertIsNone(s.hub._agent,"a dropped upstream must be torn down by the pump's hand-off task")
        s.assertTrue(await asyncio.wait_for(s.hub.ensure(retries=1),5))
    async def test_hung_but_alive_agent_is_not_respawned(s):
        s.mode="init-only"
        spawned=[]
        s.hub.spawn_agent=lambda force=False:spawned.append(force)
        s.assertTrue(await s.hub.ensure())
        s.hub._hung_agent=True
        await asyncio.wait_for(s.hub._recover_hung(),15)
        s.assertEqual(spawned,[],"an agent that answers a side-connection initialize is slow, not dead")
        s.assertTrue(s.hub._agent_ok())
    async def test_dead_agent_is_killed_and_respawned(s):
        s.mode="silent"
        spawned=[]
        s.hub.spawn_agent=lambda force=False:spawned.append(force)
        old=SRV.PROBE_TIMEOUT;SRV.PROBE_TIMEOUT=0.5
        try:
            s.assertTrue(await s.hub.ensure())
            s.hub._hung_agent=True
            await asyncio.wait_for(s.hub._recover_hung(),15)
            s.assertEqual(spawned,[True],"a failed probe means kill + respawn (force)")
        finally:SRV.PROBE_TIMEOUT=old
class HubRules(HubBase):
    async def test_slow_session_new_or_list_never_flags_hung(s):
        SRV.RPC_REPLY_TIMEOUT["session/new"]=0.05;SRV.RPC_REPLY_TIMEOUT["_x.ai/sessions/list"]=0.05
        try:
            c=FakeWS()
            await s.hub._to_agent(c,json.dumps({"jsonrpc":"2.0","id":1,"method":"session/new","params":{"cwd":".","_grReq":"g-late"}}))
            await s.hub._to_agent(c,json.dumps({"jsonrpc":"2.0","id":2,"method":"_x.ai/sessions/list","params":{}}))
            await asyncio.sleep(0.3)
            s.assertFalse(s.hub._hung_agent,"S3: slow session/new or sessions/list must not restart the agent")
            s.assertTrue(c.reply(1) and "error" in c.reply(1)[0])
            fwd=s.agent.method("session/new")[0]
            s.assertNotIn("_grReq",fwd["params"],"_grReq is stripped before the agent")
            await s.hub._from_agent(json.dumps({"jsonrpc":"2.0","id":fwd["id"],"result":{"sessionId":SID}}))
            obj=await asyncio.wait_for(s.hub.new_session({"cwd":"."},gr_req="g-late"),2)
            s.assertEqual(obj["result"]["sessionId"],SID,"a late reply still resolves the _grReq cache")
            s.assertEqual(len(s.agent.method("session/new")),1)
            s.assertIn(SID,s.hub._created)
        finally:
            SRV.RPC_REPLY_TIMEOUT["session/new"]=90.0;SRV.RPC_REPLY_TIMEOUT["_x.ai/sessions/list"]=15.0
    async def test_duplicate_grreq_creates_one_session(s):
        c1,c2=FakeWS(),FakeWS()
        await s.hub._to_agent(c1,json.dumps({"jsonrpc":"2.0","id":1,"method":"session/new","params":{"cwd":".","_grReq":"g1"}}))
        await s.hub._to_agent(c2,json.dumps({"jsonrpc":"2.0","id":9,"method":"session/new","params":{"cwd":".","_grReq":"g1"}}))
        fwd=await s.fwd("session/new")
        s.assertEqual(len(fwd),1,"in-flight duplicate must wait, not create a second session")
        await s.hub._from_agent(json.dumps({"jsonrpc":"2.0","id":fwd[0]["id"],"result":{"sessionId":SID}}))
        await asyncio.sleep(0.05)
        s.assertEqual(c1.reply(1)[0]["result"]["sessionId"],SID)
        s.assertEqual(c2.reply(9)[0]["result"]["sessionId"],SID)
        obj=await s.hub.new_session({"cwd":"."},gr_req="g1")
        s.assertEqual(obj["result"]["sessionId"],SID)
        s.assertEqual(len(s.agent.method("session/new")),1)
        changed=[o for o in c1.method("_x.ai/sessions/changed")]
        await asyncio.sleep(0.4)
    async def test_prompt_id_is_forwarded_once(s):
        c=FakeWS()
        s.hub._load_begin(SID);s.hub._load_finish(SID,{"ok":1})
        msg={"jsonrpc":"2.0","id":4,"method":"session/prompt","params":{"sessionId":SID,"prompt":[{"type":"text","text":"hi"}],"_grPromptId":"p-1"}}
        await s.hub._to_agent(c,json.dumps(msg))
        msg["id"]=5
        await s.hub._to_agent(c,json.dumps(msg))
        fwd=await s.fwd("session/prompt")
        s.assertEqual(len(fwd),1,"a prompt the hub already accepted must never run twice")
        s.assertNotIn("_grPromptId",fwd[0]["params"])
        s.assertEqual(c.reply(5)[0]["result"],{"stopReason":"duplicate","duplicateOf":"p-1"})
        dup=await s.hub.send_prompt(SID,[{"type":"text","text":"hi"}],gr_pid="p-1")
        s.assertTrue(dup.get("duplicate"))
        await s.hub._from_agent(json.dumps({"jsonrpc":"2.0","id":fwd[0]["id"],"result":{"stopReason":"end_turn"}}))
        done=[o for o in c.objs() if o.get("method")=="_x.ai/remote/rpc_done"]
        s.assertTrue(c.reply(4))
    async def test_completion_notice_carries_sid_id_cid(s):
        c=FakeWS();s.hub.clients.add(c)
        await s.hub._claim_cid(c,"cid-abcd")
        s.hub._load_begin(SID);s.hub._load_finish(SID,{"ok":1})
        await s.hub._to_agent(c,json.dumps({"jsonrpc":"2.0","id":41,"method":"session/prompt","params":{"sessionId":SID,"prompt":[{"type":"text","text":"x"}]}}))
        fwd=await s.fwd("session/prompt")
        await s.hub._from_agent(json.dumps({"jsonrpc":"2.0","id":fwd[0]["id"],"result":{"stopReason":"end_turn"}}))
        note=c.method("_x.ai/remote/rpc_done")[-1]["params"]
        s.assertEqual((note["id"],note["sessionId"],note["cid"]),(41,SID,"cid-abcd"))
    async def test_http_prompt_loads_session_first_and_sees_rejection(s):
        task=asyncio.create_task(s.hub.send_prompt(SID,[{"type":"text","text":"x"}],gr_pid="p-http",wait=2.0,via="http"))
        await asyncio.sleep(0.05)
        loads=s.agent.method("session/load")
        s.assertTrue(loads,"S6: the HTTP fallback must session/load before prompting")
        s.assertFalse(s.agent.method("session/prompt"))
        await s.hub._from_agent(json.dumps({"jsonrpc":"2.0","id":loads[0]["id"],"result":{}}))
        await asyncio.sleep(0.05)
        p=s.agent.method("session/prompt")
        s.assertTrue(p)
        await s.hub._from_agent(json.dumps({"jsonrpc":"2.0","id":p[0]["id"],"error":{"code":-32000,"message":"nope"}}))
        obj=await task
        s.assertEqual(obj["error"]["message"],"nope","the agent's rejection must reach the HTTP caller")
    async def test_prompt_liveness_fails_only_when_probe_fails(s):
        c=FakeWS()
        s.hub._load_begin(SID);s.hub._load_finish(SID,{"ok":1})
        await s.hub._to_agent(c,json.dumps({"jsonrpc":"2.0","id":7,"method":"session/prompt","params":{"sessionId":SID,"prompt":[{"type":"text","text":"long"}]}}))
        await asyncio.sleep(0.05)
        old=SRV.PROMPT_IDLE_SECS;SRV.PROMPT_IDLE_SECS=0.01
        try:
            async def alive():return True
            s.hub.probe_agent=alive
            await asyncio.sleep(0.05)
            await s.hub._check_prompt_liveness()
            s.assertFalse(c.reply(7),"a quiet turn on a live agent keeps waiting")
            async def dead():return False
            s.hub.probe_agent=dead;s.hub._liveness_probe_at=0
            await asyncio.sleep(0.05)
            await s.hub._check_prompt_liveness()
            r=c.reply(7)
            s.assertTrue(r and r[0]["error"]["code"]==-32002)
            s.assertEqual(s.hub.work.snapshot(SID)[0]["phase"],"failed")
            s.assertTrue(s.hub._hung_agent)
        finally:SRV.PROMPT_IDLE_SECS=old
    async def test_missing_sid_filled_only_with_exactly_one_inflight(s):
        ev=lambda:{"jsonrpc":"2.0","method":"session/update","params":{"update":{"sessionUpdate":"agent_message_chunk","content":{"type":"text","text":"x"}}}}
        o=ev();s.assertFalse(s.hub._ensure_session_id(o));s.assertNotIn("sessionId",o["params"])
        s.hub.pending[100]=(None,1,{"method":"session/prompt","sid":SID})
        o=ev();s.assertTrue(s.hub._ensure_session_id(o));s.assertEqual(o["params"]["sessionId"],SID)
        s.hub.pending[101]=(None,2,{"method":"session/prompt","sid":SID2})
        o=ev();s.assertFalse(s.hub._ensure_session_id(o),"two sessions in flight: never guess")
        q={"jsonrpc":"2.0","method":"_x.ai/queue/changed","params":{"entries":[]}}
        s.assertFalse(s.hub._ensure_session_id(q))
        s.hub._last_sid=SID2
        s.hub.pending.clear()
        o=ev();s.assertFalse(s.hub._ensure_session_id(o),"the old global _last_sid must not be used")
    async def test_replay_goes_only_to_the_loader_and_skips_work_board(s):
        loader,other=FakeWS(),FakeWS()
        s.hub.clients.update({loader,other})
        await s.hub._to_agent(loader,json.dumps({"jsonrpc":"2.0","id":1,"method":"session/load","params":{"sessionId":SID,"cwd":"."}}))
        fwd=await s.fwd("session/load")
        for k in ("user_message_chunk","tool_call","agent_message_chunk"):
            await s.hub._from_agent(json.dumps({"jsonrpc":"2.0","method":"session/update","params":{"sessionId":SID,"update":{"sessionUpdate":k,"toolCallId":"t1","content":{"type":"text","text":"old"}}}}))
        s.assertEqual(len(loader.method("session/update")),3)
        s.assertEqual(other.method("session/update"),[],"replay must not be broadcast to other devices")
        s.assertEqual(s.hub.work.snapshot(SID),[],"replayed events must not touch the work board")
        await s.hub._from_agent(json.dumps({"jsonrpc":"2.0","id":fwd[0]["id"],"result":{}}))
        await s.hub._from_agent(json.dumps({"jsonrpc":"2.0","method":"session/update","params":{"sessionId":SID,"update":{"sessionUpdate":"agent_message_chunk","content":{"type":"text","text":"live"}}}}))
        s.assertEqual(len(other.method("session/update")),1,"live events after the load broadcast again")
    async def test_heartbeat_lists_busy_sessions(s):
        c=FakeWS();s.hub.clients.add(c)
        s.hub.pending[5]=(c,1,{"method":"session/prompt","sid":SID,"t":time.time()})
        await s.hub._notify_hub_state(True)
        s.assertEqual(c.method("_x.ai/remote/hub")[-1]["params"]["busy"],[SID])
    async def test_turn_completed_pushes_work_board(s):
        c=FakeWS();s.hub.clients.add(c)
        s.hub.work.note_prompt(SID,"go")
        await s.hub._from_agent(json.dumps({"jsonrpc":"2.0","method":"_x.ai/session/update","params":{"sessionId":SID,"update":{"sessionUpdate":"turn_completed"}}}))
        await asyncio.sleep(0.5)
        s.assertTrue(c.method("_x.ai/work/changed"),"S15: turn completion must push the work board")
        s.assertFalse(s.hub.work.snapshot(SID)[0]["running"])
    async def test_agent_connect_heals_stale_jobs(s):
        w=s.hub.work
        w.note_prompt(SID,"x")
        w.note_update(SID,{"sessionUpdate":"tool_call","toolCallId":"t1","title":"run"},{"updateParams":{"status":"in_progress"}})
        w.note_prompt(SID2,"y");w.note_update(SID2,{"sessionUpdate":"agent_thought_chunk"},{})
        s.assertTrue(w.snapshot(SID)[0]["running"])
        s.hub._on_upstream_up(FakeWS())
        await asyncio.sleep(0.05)
        s.assertFalse(w.snapshot(SID)[0]["running"],"open tool rows from a dead turn must not spin forever")
        s.assertFalse(w.snapshot(SID2)[0]["running"],"a job left 'thinking' must be idled too")
    async def test_set_model_patches_cached_load(s):
        s.hub._load_begin(SID);s.hub._load_finish(SID,{"models":{"currentModelId":"a","availableModels":[{"modelId":"a"},{"modelId":"b","_meta":{"reasoningEffort":"low"}}]}})
        c=FakeWS()
        await s.hub._to_agent(c,json.dumps({"jsonrpc":"2.0","id":3,"method":"session/set_model","params":{"sessionId":SID,"modelId":"b","_meta":{"reasoningEffort":"high"}}}))
        fwd=await s.fwd("session/set_model")
        await s.hub._from_agent(json.dumps({"jsonrpc":"2.0","id":fwd[0]["id"],"result":{}}))
        res=s.hub._loads[SID]["res"]["models"]
        s.assertEqual(res["currentModelId"],"b")
        s.assertEqual(res["availableModels"][1]["_meta"]["reasoningEffort"],"high")
    async def test_load_eviction_never_strands_inflight(s):
        for i in range(SRV.HUB_MAX_LOADS):s.hub._load_begin("inflight-%d"%i)
        s.hub._load_begin("one-more")
        s.assertTrue(all(("inflight-%d"%i) in s.hub._loads for i in range(SRV.HUB_MAX_LOADS)))
    async def test_cid_conflict_refuses_a_live_duplicate_tab(s):
        a,b,c=FakeWS(),FakeWS(),FakeWS()
        s.assertTrue(await s.hub._claim_cid(a,"cid-1234","page-A"))
        a._last_rx=time.time()
        s.assertFalse(await s.hub._claim_cid(b,"cid-1234","page-B"),"a duplicated tab (other nonce) must not steal a live socket")
        s.assertEqual(b.close_code,4409)
        s.assertFalse(a.closed)
        s.assertTrue(await s.hub._claim_cid(c,"cid-1234","page-A"),"the same page reconnecting replaces its old socket")
        s.assertTrue(a.closed)
        d=FakeWS();c._last_rx=time.time()-60
        s.assertTrue(await s.hub._claim_cid(d,"cid-1234","page-Z"),"a silent old socket is replaced")
class Auth(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(s):
        from aiohttp import web
        from aiohttp.test_utils import TestServer,TestClient
        s.allow={"hosts":set(),"origins":set()}
        async def ok(_):return web.json_response({"ok":True})
        async def ws(req):
            w=web.WebSocketResponse();await w.prepare(req);await w.send_str("hi");await w.close();return w
        app=web.Application(middlewares=[SRV.make_auth_middleware("k"*20,allow=lambda:(s.allow["hosts"],s.allow["origins"]))])
        app.router.add_get("/",ok);app.router.add_get("/static/{n:.*}",ok);app.router.add_get("/api/x",ok);app.router.add_post("/api/x",ok);app.router.add_get("/ws",ws)
        s.srv=TestServer(app,host="127.0.0.1");s.cl=TestClient(s.srv);await s.cl.start_server()
        h="127.0.0.1:%d"%s.srv.port
        s.allow["hosts"]={h,"localhost:%d"%s.srv.port};s.allow["origins"]={"http://"+h}
        s.good="http://"+h
    async def asyncTearDown(s):await s.cl.close()
    async def wsclose(s,path,**kw):
        w=await s.cl.ws_connect(path,**kw)
        m=await w.receive()
        code=w.close_code
        await w.close()
        return m,code
    async def test_demo_serves_static_only(s):
        s.assertEqual((await s.cl.get("/static/a.js?demo=1",headers={"Host":"evil.example"})).status,200)
        s.assertEqual((await s.cl.get("/api/x?demo=1",headers={"Host":"evil.example"})).status,401,"demo=1 must not open /api")
        m,code=await s.wsclose("/ws?demo=1",headers={"Host":"evil.example"})
        s.assertEqual(code,4401,"demo=1 must not open /ws")
    async def test_loopback_needs_our_host_and_origin(s):
        s.assertEqual((await s.cl.get("/api/x",headers={"Host":"evil.example:1"})).status,401,"DNS rebinding: foreign Host gets no loopback bypass")
        s.assertEqual((await s.cl.get("/api/x")).status,200)
        s.cl.session.cookie_jar.clear()
        m,code=await s.wsclose("/ws",origin="http://evil.example")
        s.assertEqual(code,4403)
        m,code=await s.wsclose("/ws",origin=s.good)
        s.assertEqual(m.data,"hi")
        r=await s.cl.post("/api/x",headers={"Origin":"http://evil.example"})
        s.assertEqual(r.status,403)
    async def test_cookie_never_authorizes_cross_origin_writes(s):
        r=await s.cl.post("/api/x",headers={"Origin":"http://evil.example","Host":"evil.example","Cookie":"grok_remote_key="+"k"*20})
        s.assertEqual(r.status,403)
        r=await s.cl.post("/api/x?key="+"k"*20,headers={"Origin":"http://evil.example","Host":"evil.example"})
        s.assertEqual(r.status,200,"an explicit key is not an ambient credential")
    async def test_unauth_lan_page_never_shows_the_key(s):
        src=(ROOT/"server.py").read_text(encoding="utf-8")
        mw=src[src.find("def make_auth_middleware"):src.find("def under_root")]
        s.assertNotIn("?key=%s",mw)
def ev(kind,text="",i=0):
    u={"sessionUpdate":kind,"content":{"type":"text","text":text}}
    if kind.startswith("tool_call"):u.update({"toolCallId":"t%d"%i,"title":"c%d"%i,"status":"completed"})
    return json.dumps({"method":"session/update","params":{"sessionId":SID,"update":u}},separators=(",",":"))+"\n"
class History(unittest.TestCase):
    def setUp(s):
        s.d=Path(tempfile.mkdtemp());s.p=s.d/"updates.jsonl"
    def test_partial_last_line_is_never_skipped(s):
        s.p.write_text(ev("user_message_chunk","one")+ev("agent_message_chunk","two"))
        full=s.p.stat().st_size
        line=ev("agent_message_chunk","three")
        with s.p.open("a") as f:f.write(line[:20])
        got,meta=SRV.read_session_updates(s.d,live=True,since_bytes=0)
        s.assertEqual(meta["end"],full,"end must stop at the last newline")
        s.assertEqual(meta["size"],full,"size (used as live-tail start) must exclude the partial line")
        with s.p.open("a") as f:f.write(line[20:])
        got,meta=SRV.read_session_updates(s.d,live=True,since_bytes=full)
        s.assertEqual([e["params"]["update"]["content"]["text"] for e in got],["three"])
        with s.p.open("a") as f:f.write(line[:5])
        got,meta2=SRV.read_session_updates(s.d,live=True,since_bytes=meta["end"])
        s.assertEqual(got,[]);s.assertEqual(meta2["end"],meta["end"],"a cursor never advances over a fragment")
    def test_backward_pages_are_contiguous_and_complete(s):
        rows=[]
        for t in range(12):
            rows.append(ev("user_message_chunk","u%d"%t))
            rows+= [ev("tool_call","",t*100+i) for i in range(30)]
            rows.append(ev("agent_message_chunk","a%d"%t))
        s.p.write_text("".join(rows))
        for chat_only in (True,False):
            seen=[];before=None;pages=0
            while True:
                got,meta=SRV.read_session_updates(s.d,limit=20,chat_only=chat_only,before_bytes=before)
                seen=got+seen;pages+=1
                if not meta["has_more"]:break
                s.assertLess(meta["older_before"],before if before is not None else 1e18)
                before=meta["older_before"]
                s.assertLess(pages,200)
            tools=sum(1 for e in seen if e["params"]["update"]["sessionUpdate"]=="tool_call")
            s.assertEqual(tools,12*30,"S8: every aux row must be reachable by scrolling up (chat_only=%s)"%chat_only)
            texts=[e["params"]["update"]["content"]["text"] for e in seen if e["params"]["update"]["sessionUpdate"]!="tool_call"]
            s.assertEqual(texts,[x for t in range(12) for x in ("u%d"%t,"a%d"%t)],"no gaps, no overlap, in order")
    def test_live_forward_paging_reports_more(s):
        s.p.write_text("".join(ev("tool_call","",i) for i in range(50)))
        got,meta=SRV.read_session_updates(s.d,live=True,since_bytes=1,limit=10) if False else (None,None)
        start=len(ev("tool_call","",0))
        got,meta=SRV.read_session_updates(s.d,live=True,since_bytes=start,limit=10)
        s.assertEqual(len(got),10);s.assertTrue(meta["has_more"])
        n=10
        while meta["has_more"]:
            got,meta=SRV.read_session_updates(s.d,live=True,since_bytes=meta["end"],limit=10);n+=len(got)
        s.assertEqual(n,49,"catch-up pages forward through every event, none skipped")
class Atts(unittest.TestCase):
    PNG=bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c020000000b4944415478da63fcff1f0003030200efa2a75b0000000049454e44ae426082")
    def test_same_image_in_two_sessions(s):
        w=board(tempfile.mkdtemp())
        w.save_att("sa","a.png","image/png",s.PNG);w.save_att("sb","a.png","image/png",s.PNG)
        s.assertEqual(len(w.list_atts("sa")),1);s.assertEqual(len(w.list_atts("sb")),1,"S18: the second session's row was silently dropped")
    def test_old_schema_migrates(s):
        d=tempfile.mkdtemp();p=str(Path(d)/"w.sqlite")
        c=sqlite3.connect(p);c.execute("CREATE TABLE atts(id TEXT PRIMARY KEY,sid TEXT NOT NULL,name TEXT,mime TEXT,path TEXT,sha TEXT,text_key TEXT,at REAL NOT NULL)")
        c.execute("INSERT INTO atts VALUES('abc','sa','n','image/png','/x','sha1','',1)");c.commit();c.close()
        w=SRV.WorkBoard(p)
        c=sqlite3.connect(p);pk={r[1] for r in c.execute("PRAGMA table_info(atts)") if r[5]};c.close()
        s.assertEqual(pk,{"sid","id"})
        s.assertEqual(len(w.list_atts("sa")),1,"existing rows survive the migration")
class Meta(unittest.IsolatedAsyncioTestCase):
    async def test_migrate_update_atomic_and_safe(s):
        d=Path(tempfile.mkdtemp())
        (d/"archived_sessions.json").write_text(json.dumps({"ids":[SID]}))
        sess=d/"sessions"/"cwdenc"/SID2;sess.mkdir(parents=True)
        (sess/"summary.json").write_text(json.dumps({"remote_title":"Manual","generated_title":"Manual"}))
        m=SRV.SessionMeta(d/"session_meta.json")
        m.migrate(sessions_root=d/"sessions",archive_path=d/"archived_sessions.json")
        s.assertTrue(m.get(SID)["archived"]);s.assertEqual(m.get(SID2)["title"],"Manual")
        s.assertIsNone(m.migrate(sessions_root=d/"sessions",archive_path=d/"archived_sessions.json"),"migration runs once")
        await m.update(SID,archived=False)
        s.assertNotIn(SID,m.all(),"cleared entries are dropped")
        await m.update("pending-new-chat",title="Draft")
        s.assertEqual(m.get("pending-new-chat")["title"],"Draft","titles work for sessions not on disk yet")
        s.assertEqual([x.name for x in d.iterdir() if ".tmp" in x.name],[],"atomic write leaves no temp files")
        (d/"session_meta.json").write_text("{broken")
        m2=SRV.SessionMeta(d/"session_meta.json")
        s.assertEqual(m2.all(),{})
        s.assertTrue(any(x.name.startswith("session_meta.json.bad-") for x in d.iterdir()),"corrupt file is kept aside, never silently overwritten")
        m3=SRV.SessionMeta(d/"session_meta.json");await m3.update(SID,title="T")
        before=(d/"session_meta.json").read_text()
        m3._read=lambda:(None,False)
        with s.assertRaises(RuntimeError):await m3.update(SID,title="X")
        s.assertEqual((d/"session_meta.json").read_text(),before,"never save after a failed read")
    def test_summary_json_is_never_written(s):
        src=(ROOT/"server.py").read_text(encoding="utf-8")
        ren=src[src.find("async def session_rename"):src.find("async def session_prompt_http")]
        for w in ("summ_path","write_text","atomic_write","open("):s.assertNotIn(w,ren)
class Resolve(unittest.TestCase):
    def test_prefix_resolution(s):
        d=Path(tempfile.mkdtemp())
        for sid in (SID,"11111111-9999-3333-4444-555555555555",SID2):
            p=d/"enc"/sid;p.mkdir(parents=True);(p/"updates.jsonl").write_text("")
        old=SRV.GROK_SESSIONS;SRV.GROK_SESSIONS=d;SRV.invalidate_session_index()
        try:
            s.assertEqual(SRV.resolve_sid("22222222-3333"),(SID2,None))
            sid,err=SRV.resolve_sid("11111111")
            s.assertTrue(err and "ambiguous" in err)
            s.assertEqual(SRV.resolve_sid(SID),(SID,None))
            s.assertEqual(SRV.resolve_sid("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",None),"a full id not on disk yet passes through")
            s.assertIsNone(SRV.find_session_dir("11111111"),"find_session_dir no longer guesses prefixes")
        finally:SRV.GROK_SESSIONS=old;SRV.invalidate_session_index()
    def test_norm_cwd_both_sides(s):
        s.assertEqual(SRV._norm_cwd("/home/x/ai/"),SRV._norm_cwd("/home/x//ai"))
@unittest.skipUnless(sys.platform.startswith("linux"),"Linux /proc")
class LinuxPids(unittest.TestCase):
    def test_listen_pids_and_kill(s):
        so=socket.socket();so.bind(("127.0.0.1",0));so.listen(1);port=so.getsockname()[1]
        try:s.assertIn(os.getpid(),SRV.listen_pids_port(port,exclude_self=False),"S9: /proc lookup must find our own listener")
        finally:so.close()
        code="import socket,time;s=socket.socket();s.bind(('127.0.0.1',0));s.listen(1);print(s.getsockname()[1],flush=True);time.sleep(60)"
        pr=subprocess.Popen([sys.executable,"-c",code],stdout=subprocess.PIPE,text=True)
        try:
            port=int(pr.stdout.readline())
            pids=SRV.listen_pids_port(port)
            s.assertEqual(pids,[pr.pid])
            out=SRV.kill_pids_list(pids,grace=2)
            pr.wait(timeout=5)
            s.assertTrue(out and out[0]["ok"] is not None)
            s.assertFalse(SRV.port_open(port))
        finally:
            if pr.poll() is None:pr.kill()
class Loops(unittest.IsolatedAsyncioTestCase):
    async def test_restart_respects_last_fire(s):
        fired=[]
        class H:
            async def inject_prompt(self,*a,**k):fired.append(a)
            async def _broadcast(self,*a):pass
        store=Path(tempfile.mkdtemp())/"loops.json"
        store.write_text(json.dumps({"jobs":[{"id":"loop-1","sessionId":SID,"prompt":"p","interval_sec":300,"interval_label":"5m","created_at":time.time()-600,"fires":3,"last_fire":time.time()-10,"expires_at":time.time()+3600}]}))
        lm=SRV.RemoteLoopManager(H(),store);lm.start_all()
        await asyncio.sleep(0.3)
        s.assertEqual(fired,[],"S17: a hub restart must not fire a loop that fired 10s ago")
        for t in list(lm._tasks.values()):t.cancel()
if __name__=="__main__":unittest.main()
