echo off
set filename=%~f0
for %%F in ("%filename%") do set script_dir=%%~dpF
echo %script_dir%

python %script_dir%src\extargsparse\__lib_debug__.py --release -v %script_dir%extargsparse\__lib__.py
python %script_dir%src\extargsparse\__key_debug__.py --release -v %script_dir%extargsparse\__key__.py
