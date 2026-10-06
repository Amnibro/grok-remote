import json,sys
def out(o):sys.stdout.write(json.dumps(o)+"\n");sys.stdout.flush()
def upd(sid,u):out({"jsonrpc":"2.0","method":"session/update","params":{"sessionId":sid,"update":u}})
hang=None;perm=None
for line in sys.stdin:
 m=json.loads(line);meth=m.get("method");p=m.get("params") or {}
 if meth=="initialize":out({"jsonrpc":"2.0","id":m["id"],"result":{"protocolVersion":1,"agentCapabilities":{"loadSession":True,"promptCapabilities":{"image":True}}}})
 elif meth=="session/new":out({"jsonrpc":"2.0","id":m["id"],"result":{"sessionId":"fs-1"}})
 elif meth=="session/load":upd(p["sessionId"],{"sessionUpdate":"agent_message_chunk","content":{"type":"text","text":"REPLAY"}});out({"jsonrpc":"2.0","id":m["id"],"result":{}})
 elif meth=="session/prompt":
  sid=p["sessionId"];txt=" ".join(b.get("text","") for b in p["prompt"] if b.get("type")=="text");imgs=sum(1 for b in p["prompt"] if b.get("type")=="image")
  upd(sid,{"sessionUpdate":"agent_thought_chunk","content":{"type":"text","text":"hmm"}})
  upd(sid,{"sessionUpdate":"tool_call","toolCallId":"t1","title":"Read file","kind":"read","status":"pending","rawInput":{"path":"/x"}})
  upd(sid,{"sessionUpdate":"tool_call_update","toolCallId":"t1","status":"completed"})
  if "hang" in txt:hang=m["id"];continue
  if "perm" in txt:perm=(m["id"],sid);out({"jsonrpc":"2.0","id":900,"method":"session/request_permission","params":{"sessionId":sid,"toolCall":{"toolCallId":"t2","title":"Run ls","kind":"execute","rawInput":{"command":"ls"}},"options":[{"optionId":"ok","name":"Allow","kind":"allow_once"},{"optionId":"no","name":"Reject","kind":"reject_once"}]}});continue
  upd(sid,{"sessionUpdate":"agent_message_chunk","content":{"type":"text","text":"Hello there. images=%d"%imgs}})
  out({"jsonrpc":"2.0","id":m["id"],"result":{"stopReason":"end_turn"}})
 elif meth=="session/cancel" and hang is not None:out({"jsonrpc":"2.0","id":hang,"result":{"stopReason":"cancelled"}});hang=None
 elif m.get("id")==900 and perm:
  o=m["result"]["outcome"];upd(perm[1],{"sessionUpdate":"agent_message_chunk","content":{"type":"text","text":"chose %s"%(o.get("optionId") or o.get("outcome"))}})
  out({"jsonrpc":"2.0","id":perm[0],"result":{"stopReason":"end_turn"}});perm=None
