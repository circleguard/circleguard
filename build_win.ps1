Write-Output "creating venv"
python -m venv build-env --clear
Write-Output "activating venv"
./build-env/Scripts/activate.ps1
# install pip requirements
Write-Output "installing pip requirements"
pip install -r requirements.txt -r requirements_build.txt
# run pyinstaller for x64 & x86
Write-Output "run x64 build"
pyinstaller gui_win_x64.spec --noconfirm
Write-Output "run x86 build"
pyinstaller gui_win_x86.spec --noconfirm
# leave and delete venv
Write-Output "deactivating venv"
deactivate
Write-Output "deleting venv"
Remove-Item ./build-env/ -Recurse -Force
