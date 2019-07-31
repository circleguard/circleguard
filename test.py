import zipfile
import os
os. chdir("./dist/")
def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        print(root)
        for file in files:
            ziph.write(os.path.join(root, file))


zipf = zipfile.ZipFile('Circleguard_win_x64.zip', 'w', zipfile.ZIP_DEFLATED)
zipdir('./', zipf)
zipf.close()