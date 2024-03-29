# -*- mode: python -*-

block_cipher = None
from os.path import expanduser
import os
import zipfile
os.path.expanduser
from circleguard import __version__ # circlecore version, not gui


# https://github.com/pyinstaller/pyinstaller/wiki/Recipe-remove-tkinter-tcl
import sys
sys.modules['FixTk'] = None

def zipdir(path, ziph, sub_folder=""):
    length = len(path)
    for root, dirs, files in os.walk(path):
        folder = root[length:] # path without "parent"
        if sub_folder != "":
            folder = sub_folder + folder
        for file in files:
            ziph.write(os.path.join(root, file), os.path.join(folder, file))

# Analysis options documentation here
# https://github.com/pyinstaller/pyinstaller/blob/develop/PyInstaller/building/build_main.py#L133

# build with pyinstaller
a = Analysis(['circleguard/main.py'],
             pathex=['.'],
             datas=[('resources/','resources/')],
             hiddenimports=[],
             hookspath=["."],
             runtime_hooks=[],
             # https://github.com/pyinstaller/pyinstaller/wiki/Recipe-remove-tkinter-tcl for
             # tkinter excludes, the others are added by us
             excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter', 'IPython'],
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
          console=False, icon='./resources/logo/logo_mac.icns')
app = BUNDLE(exe,
            name='Circleguard.app',
            icon='./resources/logo/logo_mac.icns',
            bundle_identifier=None,
            info_plist={
                'NSHighResolutionCapable': 'True',
                'CFBundleShortVersionString': __version__,
                # register our ``circleguard://`` scheme
                "CFBundleIdentifier": "circleguard",
                "CFBundleURLTypes": [{
                    "CFBundleURLName": "Circleguard",
                    "CFBundleURLSchemes": [
                        "circleguard"
                    ]
                }]
            })

print("Creating zip")
zipf = zipfile.ZipFile('./Circleguard_osx.app.zip', 'w', zipfile.ZIP_DEFLATED)
zipdir('./dist/Circleguard.app', zipf, "./Circleguard.app")
zipf.close()
print("Moving zip")
os.rename("./Circleguard_osx.app.zip", "./dist/Circleguard_osx.app.zip")
print("Finished zip")
