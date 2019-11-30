Write-Output "creating venv"
python -m venv build-env --clear

Write-Output "activating venv"
./build-env/Scripts/activate.ps1

echo "installing pip requirements"
pip install -r requirements.txt
echo "installing build requirements"
pip install -r requirements_build_win.txt

Write-Output "building x64"
pyinstaller gui_win_x64.spec --noconfirm
Write-Output "building x86"
pyinstaller gui_win_x86.spec --noconfirm

Write-Output "deactivating venv"
deactivate

Write-Output "deleting venv"
Remove-Item ./build-env/ -Recurse -Force
