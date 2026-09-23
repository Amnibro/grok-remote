import atexit,shutil,tempfile
tempfile.tempdir=tempfile.mkdtemp(prefix="grok-tests-")
atexit.register(shutil.rmtree,tempfile.tempdir,True)
