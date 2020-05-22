rem Set current directory to the batchfile directory.
cd /d %~dp0
pyinstaller BuildKML.py --onefile -n BuildKML
pause