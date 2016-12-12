#! /bin/bash

_script_file=`readlink -f $0`
script_dir=`dirname $_script_file`

python $script_dir/src/extargsparse/__lib_debug__.py --release -v $script_dir/extargsparse/__lib__.py
python $script_dir/src/extargsparse/__key_debug__.py --release -v $script_dir/extargsparse/__key__.py