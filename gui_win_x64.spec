# -*- mode: python -*-

block_cipher = None
from pathlib import Path
import sys
import os
from win32com.client import Dispatch
import zipfile
import PyInstaller.config
os.path.expanduser

# https://stackoverflow.com/a/42056050
def zipdir(path, ziph):
    length = len(path)

    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        folder = root[length:] # path without "parent"
        for file in files:
            ziph.write(os.path.join(root, file), os.path.join(folder, file))

# pyinstaller build
PyInstaller.config.CONF['distpath'] = "./dist/Circleguard_win_x64"
a = Analysis(['circleguard/main.py'],
             pathex=['.', 'C:/Program Files (x86)/Windows Kits/10/Redist/ucrt/DLLs/x64', os.path.dirname(sys.executable)],
             datas=[('resources/','resources/')],
             hookspath=["."],
             runtime_hooks=["./hide-internals-runtime-hook.py"],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          name='Circleguard',
          exclude_binaries=True,
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=False , icon='./resources/logo/logo.ico')
coll = COLLECT(
          exe,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='Circleguard',
          strip=False,
          upx=True
)

# post-build script
shell = Dispatch("WScript.Shell")
# Path().resolve() first to deal with relative paths, also converts / to \ because windows
shortcut = shell.CreateShortCut(str(Path("./dist/Circleguard_win_x64/Circleguard.lnk").resolve()))
shortcut.Targetpath = str(Path("./dist/Circleguard_win_x64/Circleguard/Circleguard.exe").resolve())
shortcut.save()

print("Creating zip")
os.chdir("./dist/")
zipf = zipfile.ZipFile('./Circleguard_win_x64.zip', 'w', zipfile.ZIP_DEFLATED)
zipdir('./Circleguard_win_x64/', zipf)
zipf.close()
print("Finished zip")
