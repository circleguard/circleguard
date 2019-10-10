from subprocess import Popen
from pathlib import Path
DIR = Path(__file__).parent

print("creating venv")
sp = Popen(f"python3 -m venv {DIR / 'build-env'} --clear", shell=True)
sp.wait()

print("activating venv")
sp = Popen(f"source {DIR / 'build-env/bin/activate'}", shell=True)
sp.wait()

print("installing pip requirements")
sp = Popen(f"pip install -r {DIR / 'requirements_build_mac.txt'}", shell=True)
sp.wait()

print("building")
sp = Popen(f"pyinstaller {DIR / 'gui_mac.spec'} --noconfirm", shell=True)
sp.wait()

print("deleting venv")
sp = Popen(f"rm -rf {DIR / 'build-env'}", shell=True)
sp.wait()
