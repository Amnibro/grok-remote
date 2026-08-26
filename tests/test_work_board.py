import os,tempfile,base64
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from work_board import WorkBoard,strip_ask
def test_strip():
 assert "hello" in strip_ask("[INTERJECT — x]\n\nhello")
 s=strip_ask("[Reaction meter 0.2 adaptive] Stamp\n\n\nreal ask")
 assert "real ask" in s
def test_cancelled_tool_clears_running():
 fd,p=tempfile.mkstemp(suffix=".sqlite");os.close(fd)
 try:
  w=WorkBoard(p)
  w.note_prompt("sid-a","There's a cliff here","Azno-v2")
  w.note_update("sid-a",{"sessionUpdate":"tool_call","toolCallId":"t1","title":"run_terminal_command","rawInput":{"command":"python -B -u server.py"}},{"updateParams":{"status":"Pending"}})
  assert w.snapshot("sid-a")[0]["running"]==1
  w.note_update("sid-a",{"sessionUpdate":"tool_call_update","toolCallId":"t1"},{"updateParams":{"status":"cancelled"}})
  j=w.snapshot("sid-a")[0]
  assert j["running"]==0
  assert j["phase"]=="idle"
  w.note_prompt("sid-b","please fit")
  w.note_update("sid-b",{"sessionUpdate":"tool_call","toolCallId":"t2","title":"run"},{"updateParams":{"status":"Pending"}})
  w.note_update("sid-b",{"sessionUpdate":"tool_call_update","toolCallId":"t2"},{"updateParams":{"status":"Completed"}})
  w.note_update("sid-b",{"sessionUpdate":"turn_completed"},{})
  assert w.snapshot("sid-b")[0]["running"]==0
  w.note_prompt("sid-c","wait on model")
  c=w.snapshot("sid-c")[0]
  assert c["running"]==1 and c["phase"]=="waiting"
  w.mark_cancel("sid-c")
  assert w.snapshot("sid-c")[0]["running"]==0
 finally:
  try:os.remove(p)
  except Exception:pass
  for s in ("-wal","-shm"):
   try:os.remove(p+s)
   except Exception:pass
def test_heal_waiting_after_cancelled_tools():
 fd,p=tempfile.mkstemp(suffix=".sqlite");os.close(fd)
 try:
  w=WorkBoard(p)
  w.note_prompt("az","cliff")
  w.note_update("az",{"sessionUpdate":"tool_call","toolCallId":"t1","title":"run"},{"updateParams":{"status":"Pending"}})
  import sqlite3
  c=sqlite3.connect(p);c.execute("UPDATE tools SET status='cancelled' WHERE sid='az'");c.execute("UPDATE jobs SET running=1,phase='waiting' WHERE sid='az'");c.commit();c.close()
  n=w.heal("az")
  assert n==1
  j=w.snapshot("az")[0]
  assert j["running"]==0
 finally:
  try:os.remove(p)
  except Exception:pass
  for s in ("-wal","-shm"):
   try:os.remove(p+s)
   except Exception:pass
def test_heal_skips_fresh_prompt():
 fd,p=tempfile.mkstemp(suffix=".sqlite");os.close(fd)
 try:
  w=WorkBoard(p)
  w.note_prompt("s","old")
  w.note_update("s",{"sessionUpdate":"tool_call","toolCallId":"t1","title":"run"},{"updateParams":{"status":"Pending"}})
  w.note_update("s",{"sessionUpdate":"tool_call_update","toolCallId":"t1"},{"updateParams":{"status":"Completed"}})
  w.note_update("s",{"sessionUpdate":"turn_completed"},{})
  w.note_prompt("s","new ask after tools")
  assert w.snapshot("s")[0]["running"]==1
  assert w.heal("s")==0
  assert w.snapshot("s")[0]["running"]==1
  assert w.snapshot("s")[0]["phase"]=="waiting"
 finally:
  try:os.remove(p)
  except Exception:pass
  for s in ("-wal","-shm"):
   try:os.remove(p+s)
   except Exception:pass
def test_att_roundtrip():
 fd,p=tempfile.mkstemp(suffix=".sqlite");os.close(fd)
 try:
  w=WorkBoard(p)
  png=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII=")
  rec=w.save_att("sid-img","dot.png","image/png",png,"look at this cliff")
  assert rec and rec["id"] and rec["url"].startswith("/api/att/")
  items=w.list_atts("sid-img")
  assert len(items)==1 and items[0]["text_key"]
  got=w.get_att(rec["id"])
  assert got and Path(got["path"]).is_file()
  blocks=[{"type":"text","text":"see attached"},{"type":"image","mimeType":"image/png","data":base64.b64encode(png).decode("ascii")}]
  out=w.ingest_prompt("sid-img",blocks)
  assert out
 finally:
  try:os.remove(p)
  except Exception:pass
  for s in ("-wal","-shm"):
   try:os.remove(p+s)
   except Exception:pass
  import shutil
  try:shutil.rmtree(Path(p).parent/"att",ignore_errors=True)
  except Exception:pass
if __name__=="__main__":
 test_strip();test_cancelled_tool_clears_running();test_heal_waiting_after_cancelled_tools();test_heal_skips_fresh_prompt();test_att_roundtrip();print("ok")
