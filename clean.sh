#! /bin/bash

_script_file=`readlink -f $0`
script_dir=`dirname $_script_file`


rm -f $script_dir/extargsparse/__lib__.py.touched 
rm -f $script_dir/extargsparse/__init__.py.touched
rm -f $script_dir/extargsparse/__key__.py.touched

rm -f $script_dir/extargsparse/__lib__.py
rm -f $script_dir/extargsparse/__init__.py
rm -f $script_dir/extargsparse/__key__.py

rm -f $script_dir/setup.py