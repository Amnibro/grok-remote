import os,shutil,subprocess,sys,unittest
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]
SCRIPT=REPO/"scripts"/"ensure-running.ps1"
def resolve(cwd,extra=()):
 env=dict(os.environ);env.pop("GROK_PROJECT_DIR",None)
 out=subprocess.run([shutil.which("powershell") or shutil.which("pwsh"),"-NoProfile","-ExecutionPolicy","Bypass","-File",str(SCRIPT),"-IgnoreConfig","-PrintCwd",*extra],cwd=str(cwd),env=env,capture_output=True,text=True,timeout=60)
 return out.stdout.strip().rstrip("\\")
@unittest.skipUnless(shutil.which("powershell") or shutil.which("pwsh"),"PowerShell not installed")
class EnsureRunningCwd(unittest.TestCase):
 def test_repo_root_is_never_the_workspace(self):
  got=resolve(REPO)
  self.assertNotEqual(got.lower(),str(REPO).lower(),"desktop exe launches from the repo root; that must not become the hub workspace")
  self.assertTrue(got,"no cwd printed")
 def test_scripts_dir_is_never_the_workspace(self):
  got=resolve(REPO/"scripts")
  self.assertNotEqual(got.lower(),str(REPO/"scripts").lower())
 def test_a_real_workspace_pwd_is_kept(self):
  other=REPO.parent
  self.assertEqual(resolve(other).lower(),str(other).lower())
 def test_explicit_cwd_wins(self):
  want=str(Path.home())
  self.assertEqual(resolve(REPO,("-Cwd",want)).lower(),want.lower())
if __name__=="__main__":unittest.main()
