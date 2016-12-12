#! /bin/bash

_script_file=`readlink -f $0`
script_dir=`dirname $_script_file`

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
			/bin/echo -e "import time\ntime.sleep(0.1)" | python
			_checked=`expr $_checked \+ 1`
		else
			_checked=0
			/bin/echo -e "import time\ntime.sleep(0.1)" | python	
			_cnt=`expr $_cnt \+ 1`
			if [ $_cnt -gt $_maxtime ]
				then
				/bin/echo "can not wait ($_waitf)" >&2
				exit 3
			fi
		fi
	done	
}

python $script_dir/src/extargsparse/__lib_debug__.py --release -v $script_dir/extargsparse/__lib__.py
wait_file_until "$script_dir/extargsparse/__lib__.py.touched"
python $script_dir/src/extargsparse/__key_debug__.py --release -v $script_dir/extargsparse/__key__.py
wait_file_until "$script_dir/extargsparse/__key__.py.touched"
