"""Grok Remote: mobile UI + WebSocket proxy to local grok agent serve.
Phone only talks to THIS server (0.0.0.0). Agent can stay on 127.0.0.1.
  GET  /            mobile chat UI
  GET  /config.json connection info
  WS   /ws          proxied to ws://AGENT/ws?server-key=SECRET
"""
import os,sys,json,socket,argparse,asyncio,functools,mimetypes
from pathlib import Path
ROOT=Path(__file__).resolve().parent
WEB=ROOT/"web"
def lan_ip():
 try:
  s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.connect(("8.8.8.8",80));ip=s.getsockname()[0];s.close();return ip
 except Exception:return "127.0.0.1"
async def main_async(a):
 try:
  import aiohttp
  from aiohttp import web,WSMsgType,ClientSession
 except ImportError:
  import subprocess;subprocess.check_call([sys.executable,"-m","pip","install","aiohttp","-q"])
  import aiohttp
  from aiohttp import web,WSMsgType,ClientSession
 agent_host=a.agent_host or "127.0.0.1"
 agent_ws="ws://%s:%d/ws?server-key=%s"%(agent_host,a.agent_port,a.secret)
 lan=lan_ip()
 cfg={"agent_host":agent_host,"agent_port":a.agent_port,"secret":"(held server-side)","cwd":a.cwd,"ws_url":"ws://%s:%d/ws"%(lan,a.port),"ws_path":"/ws","ui":"http://%s:%d/"%(lan,a.port),"lan_ip":lan,"proxy":True}
 try:(ROOT/"runtime-config.json").write_text(json.dumps(cfg,indent=2),encoding="utf-8")
 except Exception:pass
 async def index(_):
  return web.FileResponse(WEB/"index.html")
 async def config(_):
  return web.json_response(cfg,headers={"Cache-Control":"no-store"})
 async def static(request):
  name=request.match_info.get("name","")
  p=(WEB/name).resolve()
  if not str(p).startswith(str(WEB.resolve())) or not p.is_file():raise web.HTTPNotFound()
  ctype=mimetypes.guess_type(str(p))[0] or "application/octet-stream"
  return web.FileResponse(p,headers={"Content-Type":ctype})
 async def health(_):
  ok=False;detail=""
  try:
   import websockets
   async with websockets.connect(agent_ws,open_timeout=3) as w:
    await w.send(json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1,"clientInfo":{"name":"health","version":"0"},"clientCapabilities":{}}}))
    raw=await asyncio.wait_for(w.recv(),timeout=5);ok="result" in json.loads(raw)
  except Exception as e:detail=str(e)[:200]
  return web.json_response({"ok":ok,"agent_ws_local":"ws://%s:%d/ws"%(agent_host,a.agent_port),"detail":detail})
 async def ws_proxy(request):
  client=web.WebSocketResponse(heartbeat=30,max_msg_size=16*1024*1024)
  await client.prepare(request)
  print("[proxy] phone connected from",request.remote,flush=True)
  try:
   async with ClientSession() as session:
    async with session.ws_connect(agent_ws,heartbeat=30,max_msg_size=16*1024*1024) as agent:
     print("[proxy] upstream agent open",flush=True)
     async def c2a():
      async for msg in client:
       if msg.type==WSMsgType.TEXT:await agent.send_str(msg.data)
       elif msg.type==WSMsgType.BINARY:await agent.send_bytes(msg.data)
       elif msg.type in (WSMsgType.CLOSE,WSMsgType.ERROR):break
     async def a2c():
      async for msg in agent:
       if msg.type==WSMsgType.TEXT:await client.send_str(msg.data)
       elif msg.type==WSMsgType.BINARY:await client.send_bytes(msg.data)
       elif msg.type in (WSMsgType.CLOSE,WSMsgType.ERROR):break
     done,pending=await asyncio.wait([asyncio.create_task(c2a()),asyncio.create_task(a2c())],return_when=asyncio.FIRST_COMPLETED)
     for t in pending:t.cancel()
  except Exception as e:
   print("[proxy] error:",e,flush=True)
   if not client.closed:
    try:await client.send_str(json.dumps({"jsonrpc":"2.0","method":"error","params":{"message":str(e)}}))
    except Exception:pass
  finally:
   if not client.closed:await client.close()
   print("[proxy] phone disconnected",flush=True)
  return client
 app=web.Application()
 app.router.add_get("/",index)
 app.router.add_get("/index.html",index)
 app.router.add_get("/config.json",config)
 app.router.add_get("/config",config)
 app.router.add_get("/health",health)
 app.router.add_get("/ws",ws_proxy)
 app.router.add_get("/static/{name}",static)
 print("Grok Remote UI+proxy  http://%s:%d/"%(lan,a.port),flush=True)
 print("Phone WebSocket       ws://%s:%d/ws  ->  %s:%d (secret server-side)"%(lan,a.port,agent_host,a.agent_port),flush=True)
 print("CWD                   %s"%a.cwd,flush=True)
 runner=web.AppRunner(app);await runner.setup()
 site=web.TCPSite(runner,a.bind,a.port);await site.start()
 while True:await asyncio.sleep(3600)
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--port",type=int,default=2421);ap.add_argument("--bind",default="0.0.0.0")
 ap.add_argument("--agent-host",default="127.0.0.1");ap.add_argument("--agent-port",type=int,default=2419)
 ap.add_argument("--secret",default=os.environ.get("GROK_AGENT_SECRET",""))
 ap.add_argument("--cwd",default=os.getcwd())
 a=ap.parse_args()
 if not a.secret:
  print("ERROR: --secret or GROK_AGENT_SECRET required",file=sys.stderr);sys.exit(2)
 try:asyncio.run(main_async(a))
 except KeyboardInterrupt:pass
if __name__=="__main__":main()
