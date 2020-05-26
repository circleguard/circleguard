from PyInstaller.utils.hooks import collect_data_files

# make sure the resource files in circlevis (eg images) are added by
# pyinstaller. This puts them inside a ``circlevis`` folder in the temporary
# directory, unlike our other resource files which go inside ``resources``.
# circlevis itself handles this weirdness when retrieving resources files.
datas = collect_data_files("circlevis")
