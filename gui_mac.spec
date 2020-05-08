# -*- mode: python -*-

block_cipher = None
from os.path import expanduser
import os
import zipfile
os.path.expanduser
from circleguard import __version__ # circlecore version, not gui

# https://stackoverflow.com/a/42056050
def zipdir(path, ziph):
    length = len(path)

    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        folder = root[length:] # path without "parent"
        for file in files:
            ziph.write(os.path.join(root, file), os.path.join(folder, file))

# pyinstaller build
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

print("Creating zip")
os.chdir("./dist/")
zipf = zipfile.ZipFile('./Circleguard_osx.app.zip', 'w', zipfile.ZIP_DEFLATED)
zipdir('./', zipf)
zipf.close()
print("Finished zip")
