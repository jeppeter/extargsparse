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

rm -f $script_dir/src/extargsparse/__key_debug__.pyc
rm -f $script_dir/src/extargsparse/__lib_debug__.pyc

rm -f $script_dir/setup.py

rm -rf $script_dir/extargsparse
rm -f $script_dir/rtools.pyc
rm -rf $script_dir/__pycache__
rm -rf $script_dir/src/extargsparse/__pycache__
rm -rf $script_dir/extargsparse.egg-info
