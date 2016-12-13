#! /usr/bin/env python

import sys
import os


def _reload_extargs_path(curpath):
    _extargs_init_py = os.path.join(curpath,'extargsparse','__init__.py')
    if os.path.exists(_extargs_init_py):
        if curpath != sys.path[0]:
            if curpath in sys.path:
                sys.path.remove(curpath)
            oldpath=sys.path
            sys.path = [curpath]
            sys.path.extend(oldpath)
    return

_reload_extargs_path(os.path.abspath(os.path.dirname(__file__)))
_reload_extargs_path(os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)),'..','..')))
import extargsparse
import rtools

def main():
	print('extargsparse version %s'%(extargsparse.__version__))
	print('extargsparse version info %s'%(repr(extargsparse.__version_info__)))

if __name__ == '__main__':
	main()