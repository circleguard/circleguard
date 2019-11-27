# -*- mode: python -*-

block_cipher = None
from os.path import expanduser
os.path.expanduser
from circleguard import __version__ # circlecore version, not gui
a = Analysis(['circleguard/gui.py'],
             pathex=['.'],
             datas=[('circleguard/resources/','resources/'), ('circleguard/examples', 'examples/')],
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
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='Circleguard',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=False , icon='./circleguard/resources/logo_mac.ico')
app = BUNDLE(exe,
             name='Circleguard.app',
             icon='./circleguard/resources/logo_mac.icns',
             bundle_identifier=None,
             info_plist={
              'NSHighResolutionCapable': 'True',
              'CFBundleShortVersionString': __version__
             }
       )