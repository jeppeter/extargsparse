echo off
set filename=%~f0
for %%F in ("%filename%") do set script_dir=%%~dpF
echo %script_dir%

del /Q /F %script_dir%extargsparse\__lib__.py.touched 2>NUL
del /Q /F %script_dir%extargsparse\__key__.py.touched 2>NUL
del /Q /F %script_dir%extargsparse\__init__.py.touched 2>NUL

python %script_dir%make_setup.py

python %script_dir%src\extargsparse\__init_debug__.py --release -v %script_dir%extargsparse\__init__.py
call :check_file %script_dir%extargsparse\__init__.py.touched

python %script_dir%src\extargsparse\__lib_debug__.py --release -v %script_dir%extargsparse\__lib__.py
call :check_file %script_dir%extargsparse\__lib__.py.touched

python %script_dir%src\extargsparse\__key_debug__.py --release -v %script_dir%extargsparse\__key__.py
call :check_file %script_dir%extargsparse\__key__.py.touched

goto :end

:check_file

set _waitf=%1
set _maxtime=100
set _cnt=0
set _checked=0
if x%_waitf% == x (
	goto :check_file_end
)

:check_file_again
if %_maxtime% LSS %_cnt% (
	echo "can not wait (%_waitf%) in (%_maxtime%)"
	exit /b 3
)

if exist %_waitf% (
	python -c "import time;time.sleep(0.1)"
	set /A _checked=%_checked%+1
	if %_checked% GTR 3 (
		del /F /Q %_waitf%
		goto :check_file_end
	)
    echo "will check (%_checked%) %_waitf%"
) else (
	set _checked=0
)

set /A _cnt=%_cnt%+1
python -c "import time;time.sleep(0.1)"
goto :check_file_again

:check_file_end
exit /b 0

:makesuredel
if not exist %1 (
	echo "not exist %1"
	exit /b 3
)

del /F /Q %1
exit /b 0

:end



echo on