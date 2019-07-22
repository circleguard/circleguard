# -*- mode: python -*-

block_cipher = None
from os.path import *
import sys
import winshell
os.path.expanduser
a = Analysis(['circleguard/gui.py'],
             pathex=['.', 'C:/Program Files (x86)/Windows Kits/10/Redist/ucrt/DLLs/x64', expanduser('~/AppData/Local/Programs/Python/Python37/')],
             binaries=[(expanduser('~/AppData/Local/Programs/Python/Python37/Lib/tkinter'), 'tk'), (expanduser('~/AppData/Local/Programs/Python/Python37/tcl'), 'tcl')],
             datas=[('circleguard/resources/','resources/'), ('circleguard/db/','db/')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          name='Circleguard_x64',
          exclude_binaries=True,
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=False , icon='./circleguard/resources/logo.ico')
coll = COLLECT(
          exe,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='Circleguard_x64',
          strip=False,
          upx=True
)


shortcut = winshell.shortcut(abspath(".\dist\Circleguard_x64\Circleguard_x64.exe"))
shortcut.write(abspath("./dist/Circleguard_x64.lnk"))
