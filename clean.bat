
echo off
set filename=%~f0
for %%F in ("%filename%") do set script_dir=%%~dpF

rmdir /Q /S %script_dir%dist 2>NUL

del /Q /F %script_dir%extargsparse\__lib__.py.touched 2>NUL
del /Q /F %script_dir%extargsparse\__key__.py.touched 2>NUL
del /Q /F %script_dir%extargsparse\__init__.py.touched 2>NUL

del /Q /F %script_dir%extargsparse\__lib__.py 2>NUL
del /Q /F %script_dir%extargsparse\__key__.py 2>NUL
del /Q /F %script_dir%extargsparse\__init__.py 2>NUL

del /Q /F %script_dir%setup.py 2>NUL
