import importlib,io,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO))
def load(tmp):
 env={"GROK_PLUGIN_DATA":str(Path(tmp)/"data"),"XDG_DATA_HOME":str(Path(tmp)/"share"),"XDG_CONFIG_HOME":str(Path(tmp)/"cfg"),"XDG_CURRENT_DESKTOP":""}
 with mock.patch.dict(os.environ,env):
  import grok_remote_ctl as c
  return importlib.reload(c)
class Ctl(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.mkdtemp();self.c=load(self.tmp)
 def test_repo_root_is_never_the_workspace(self):
  with mock.patch("os.getcwd",return_value=str(REPO)),mock.patch.dict(os.environ,{"GROK_PROJECT_DIR":"","GROK_REMOTE_CWD":""}):
   self.assertNotEqual(self.c.workspace("",{"cwd":""}),str(REPO))
 def test_scripts_dir_is_never_the_workspace(self):
  with mock.patch("os.getcwd",return_value=str(REPO/"scripts")),mock.patch.dict(os.environ,{"GROK_PROJECT_DIR":"","GROK_REMOTE_CWD":""}):
   self.assertNotEqual(self.c.workspace("",{"cwd":""}),str(REPO/"scripts"))
 def test_a_real_workspace_pwd_is_kept(self):
  with mock.patch("os.getcwd",return_value=self.tmp),mock.patch.dict(os.environ,{"GROK_PROJECT_DIR":"","GROK_REMOTE_CWD":""}):
   self.assertEqual(self.c.workspace("",{"cwd":""}),self.tmp)
 def test_explicit_cwd_wins_and_missing_dirs_skip(self):
  self.assertEqual(self.c.workspace(self.tmp,{"cwd":"/nope/missing"}),self.tmp)
  self.assertEqual(self.c.workspace("/nope/missing",{"cwd":self.tmp}),self.tmp)
 def test_hook_cwd_used_when_no_config(self):
  with mock.patch.dict(os.environ,{"GROK_PROJECT_DIR":"","GROK_REMOTE_CWD":""}):
   self.assertEqual(self.c.workspace("",{"cwd":""},{"cwd":self.tmp}),self.tmp)
 def test_config_roundtrip_and_defaults(self):
  cfg=self.c.cfg_load();self.assertEqual(cfg["ui_port"],2421);self.assertFalse(cfg["autostart"])
  cfg["cwd"]=self.tmp;self.c.cfg_save(cfg);self.assertEqual(self.c.cfg_load()["cwd"],self.tmp)
 def test_session_hook_respects_autostart_off(self):
  o=type("O",(),{"force":False,"reason":"session","cwd":"","wait":0,"quiet":True})()
  with mock.patch.object(self.c,"spawn_hub") as sp,mock.patch("sys.stdin",io.StringIO('{"cwd":"/tmp"}')):
   self.assertEqual(self.c.cmd_start(o),0);sp.assert_not_called()
  self.assertIn("autostart=false",(Path(self.tmp)/"data"/"logs"/"autostart.log").read_text())
 def test_desktop_entry_is_valid(self):
  e=self.c.desktop_entry()
  self.assertTrue(e.startswith("[Desktop Entry]\nType=Application\n"))
  for k in ("Name=Grok Remote","Icon=grok-remote","Terminal=false","StartupWMClass=","[Desktop Action stop]"):self.assertIn(k,e)
  self.assertNotIn("\nExec=\n",e)
 def test_unit_never_restarts_on_clean_stop(self):
  u=self.c.unit_text(self.c.cfg_load(),self.tmp)
  for k in ("Restart=on-failure","RestartPreventExitStatus=97","KillMode=process","--cwd "+self.tmp,"WantedBy=default.target"):self.assertIn(k,u)
 def test_kde_pin_script_targets_only_task_managers(self):
  js=self.c.kde_launchers_js("add")
  self.assertIn("applications:grok-remote.desktop",js);self.assertIn("org.kde.plasma.icontasks",js);self.assertIn("writeConfig",js)
  g=self.c.kde_launchers_js("get");self.assertIn('if("get"=="add"',g);self.assertIn('if("get"=="del"',g)
 def test_install_and_uninstall_stay_inside_xdg(self):
  home=Path(self.tmp)/"home"
  with mock.patch.object(self.c,"BIN",home/".local"/"bin"),mock.patch.object(self.c,"refresh_menus"),mock.patch.object(self.c,"pinned",return_value=False):
   o=type("O",(),{"pin":False,"autostart":False,"cwd":"","json":True})()
   with mock.patch("sys.stdout",io.StringIO()) as out:self.c.cmd_install(o)
   r=json.loads(out.getvalue());self.assertTrue(r["ok"]);self.assertTrue(self.c.DESKTOP_FILE.is_file());self.assertTrue((home/".local"/"bin"/"grok-remote").is_symlink())
   o.autostart=False
   with mock.patch("sys.stdout",io.StringIO()):self.c.cmd_uninstall(o)
   self.assertFalse(self.c.DESKTOP_FILE.exists());self.assertFalse((home/".local"/"bin"/"grok-remote").exists())
 def test_pid_helpers_find_own_listener(self):
  import socket
  s=socket.socket();s.bind(("127.0.0.1",0));s.listen(1);port=s.getsockname()[1]
  try:
   self.assertTrue(self.c.port_open(port))
   self.assertIn(os.getpid(),self.c.listen_pids_port(port,exclude_self=False))
   self.assertNotIn(os.getpid(),self.c.listen_pids_port(port))
  finally:s.close()
 def test_ufw_rule_parser(self):
  r=Path(self.tmp)/"user.rules"
  r.write_text("### tuple ### allow tcp 2421 0.0.0.0/0 any 192.168.0.0/24 in comment=x\n### tuple ### allow any 7000:7100 0.0.0.0/0 any 100.64.0.0/10 in\n### tuple ### deny tcp 9000 0.0.0.0/0 any 0.0.0.0/0 in\n### tuple ### allow udp 2422 0.0.0.0/0 any 0.0.0.0/0 in\n")
  f=lambda p,ip:self.c.ufw_allows(p,ip,str(r))
  self.assertTrue(f(2421,"192.168.0.50"));self.assertFalse(f(2421,"192.168.1.50"));self.assertTrue(f(7050,"100.114.40.251"));self.assertFalse(f(9000,"192.168.0.5"));self.assertFalse(f(2422,"192.168.0.5"))
  self.assertIsNone(self.c.ufw_allows(2421,"192.168.0.5",str(r)+".missing"))
 def test_firewall_status_shape(self):
  st=self.c.firewall_status(2421)
  for k in ("kind","active","lan_allowed","mesh_allowed","lan_ip","lan_net","mesh_ip","fix"):self.assertIn(k,st)
if __name__=="__main__":unittest.main()
