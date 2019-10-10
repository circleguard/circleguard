#!/bin/bash
DIR=`dirname $0`
cd $DIR

echo "creating venv"
python3 -m venv build-env --clear

echo "activating venv"
source build-env/bin/activate

echo "installing pip requirements"
pip install -r requirements.txt
echo "installing build requirements"
pip install -r requirements_build_mac.txt

echo "building"
pyinstaller gui_mac.spec --noconfirm

echo "deleting venv"
rm -rf build-env
