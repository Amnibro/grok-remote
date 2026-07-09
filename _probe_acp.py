import asyncio,json,sys
try:
 import websockets
except ImportError:
 import subprocess;subprocess.check_call([sys.executable,"-m","pip","install","websockets","-q"]);import websockets
URI=sys.argv[1] if len(sys.argv)>1 else "ws://127.0.0.1:2420/ws?server-key=testsecret123"
async def main():
 async with websockets.connect(URI,open_timeout=8) as ws:
  nid=0
  async def req(method,params):
   nonlocal nid;nid+=1;i=nid
   await ws.send(json.dumps({"jsonrpc":"2.0","id":i,"method":method,"params":params}))
   while True:
    raw=await asyncio.wait_for(ws.recv(),timeout=30)
    data=json.loads(raw)
    if data.get("id")==i:return data
    print("EVT",json.dumps(data)[:300])
  r=await req("initialize",{"protocolVersion":1,"clientInfo":{"name":"android-probe","version":"0.1"},"clientCapabilities":{"fs":{"readTextFile":True,"writeTextFile":True},"terminal":True}})
  print("INIT",json.dumps(r)[:800])
  r2=await req("session/new",{"cwd":r"C:\\Users\\antho\\Documents\\ai","mcpServers":[]})
  print("NEW",json.dumps(r2)[:800])
  sid=(r2.get("result") or {}).get("sessionId")
  if not sid:print("no session");return
  await ws.send(json.dumps({"jsonrpc":"2.0","id":99,"method":"session/prompt","params":{"sessionId":sid,"prompt":[{"type":"text","text":"Reply with exactly the word PONG and nothing else."}]}}))
  print("PROMPT sent")
  for _ in range(40):
   raw=await asyncio.wait_for(ws.recv(),timeout=90)
   data=json.loads(raw)
   print("<<",json.dumps(data)[:500])
   if data.get("id")==99:break
asyncio.run(main())
