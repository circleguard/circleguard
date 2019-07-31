# -*- mode: python -*-

block_cipher = None
from os.path import *
import sys
import winshell
os.path.expanduser
a = Analysis(['circleguard/gui.py'],
             pathex=['.', 'C:/Program Files (x86)/Windows Kits/10/Redist/ucrt/DLLs/x86', expanduser('~/AppData/Local/Programs/Python/Python37-32/')],
             binaries=[(expanduser('~/AppData/Local/Programs/Python/Python37-32/Lib/tkinter'), 'tk'), (expanduser('~/AppData/Local/Programs/Python/Python37-32/tcl'), 'tcl')],
             datas=[('circleguard/resources/','resources/'), ('circleguard/db/','db/'), ('circleguard/examples', 'examples/'), ('circleguard/logs', 'logs/')],
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
          name='Circleguard',
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
          name='Circleguard',
          strip=False,
          upx=True
)


shortcut = winshell.shortcut(abspath(".\dist\Circleguard\Circleguard.exe"))
shortcut.write(abspath("./dist/Circleguard.lnk"))
