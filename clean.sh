#! /bin/bash

_script_file=`readlink -f $0`
script_dir=`dirname $_script_file`

rm -rf $script_dir/dist

rm -f $script_dir/extargsparse/__lib__.py.touched 
rm -f $script_dir/extargsparse/__init__.py.touched
rm -f $script_dir/extargsparse/__key__.py.touched
rm -f $script_dir/test/release/release.py.touched

rm -f $script_dir/extargsparse/__lib__.py
rm -f $script_dir/extargsparse/__init__.py
rm -f $script_dir/extargsparse/__key__.py
rm -f $script_dir/test/release/release.py

rm -f $script_dir/setup.py

