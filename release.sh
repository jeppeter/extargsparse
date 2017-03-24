#! /bin/bash

_script_file=`readlink -f $0`
script_dir=`dirname $_script_file`

if [ -z "$PYTHON" ]
	then
	PYTHON=python
	export PYTHON
fi
echo "PYTHON [$PYTHON]" >&2

wait_file_until()
{
	_waitf="$1"
	_maxtime=100
	_checked=0
	if [ $# -gt 1 ]
		then
		_maxtime=$2
	fi
	_cnt=0
	while [ 1 ]
	do
		if [ -f "$_waitf" ]
			then
			if [ $_checked -gt 3 ]
				then
				rm -f "$_waitf"
				break
			fi
			/bin/echo -e "import time\ntime.sleep(0.1)" | $PYTHON
			_checked=`expr $_checked \+ 1`
		else
			_checked=0
			/bin/echo -e "import time\ntime.sleep(0.1)" | $PYTHON	
			_cnt=`expr $_cnt \+ 1`
			if [ $_cnt -gt $_maxtime ]
				then
				/bin/echo "can not wait ($_waitf)" >&2
				exit 3
			fi
		fi
	done	
}

rm -f $script_dir/extargsparse/__lib__.py.touched 
rm -f $script_dir/extargsparse/__init__.py.touched
rm -f $script_dir/extargsparse/__key__.py.touched
rm -f $script_dir/test/release/release.py.touched

$PYTHON $script_dir/make_setup.py
$PYTHON $script_dir/src/extargsparse/__lib_debug__.py --release -v $script_dir/extargsparse/__lib__.py
wait_file_until "$script_dir/extargsparse/__lib__.py.touched"
$PYTHON $script_dir/src/extargsparse/__key_debug__.py --release -v $script_dir/extargsparse/__key__.py
wait_file_until "$script_dir/extargsparse/__key__.py.touched"
$PYTHON $script_dir/src/extargsparse/__init_debug__.py --release -v $script_dir/extargsparse/__init__.py
wait_file_until "$script_dir/extargsparse/__init__.py.touched"

$PYTHON $script_dir/test/release/releasetest.py release
wait_file_until "$script_dir/test/release/release.py.touched"

$PYTHON $script_dir/test/release/release.py test
_res=$?
if [ $_res -ne 0 ]
	then
	/bin/echo "can not run ok"
	exit $_res
fi