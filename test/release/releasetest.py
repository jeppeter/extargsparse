#! /usr/bin/env python

import os
import sys

def _release_path_test(curpath,*paths):
    testfile = os.path.join(curpath,*paths)
    if os.path.exists(testfile):
        if curpath != sys.path[0]:
            if curpath in sys.path:
                sys.path.remove(curpath)
            oldpath=sys.path
            sys.path = [curpath]
            sys.path.extend(oldpath)
    return

def _reload_extargs_path(curpath):
	return _release_path_test(curpath,'extargsparse','__init__.py')

def _reload_extargs_debug_path(curpath):
	return _release_path_test(curpath,'__lib_debug__.py')

def _reload_rtools_path(curpath):
	return _release_path_test(curpath,'rtools.py')

topdir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)),'..','..'))
_reload_extargs_path(topdir)
_reload_rtools_path(topdir)

import extargsparse
import logging
import unittest
import re
import importlib
import rtools
import tempfile
import subprocess
import platform

if sys.version[0] == '2':
	import StringIO
else:
	import io as StringIO

test_placer_holder=True

class debug_version_test(unittest.TestCase):
    def setUp(self):
        keyname = '_%s__logger'%(self.__class__.__name__)
        if getattr(self,keyname,None) is None:
            self.__logger = _LoggerObject()
        return

    def info(self,msg,callstack=1):
        return self.__logger.info(msg,(callstack + 1))

    def error(self,msg,callstack=1):
        return self.__logger.error(msg,(callstack + 1))

    def warn(self,msg,callstack=1):
        return self.__logger.warn(msg,(callstack + 1))

    def debug(self,msg,callstack=1):
        return self.__logger.debug(msg,(callstack + 1))

    def fatal(self,msg,callstack=1):
        return self.__logger.fatal(msg,(callstack + 1))

    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass


    def test_A001(self):
    	verfile = os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','VERSION')
    	vernum = '0.0.1'
    	with open(verfile,'r') as f:
    		for l in f:
    			l = l.rstrip('\r\n')
    			vernum = l
    	self.assertEqual(vernum , extargsparse.__version__)
    	sarr = re.split('\.',vernum)
    	self.assertEqual(len(sarr),3)
    	i = 0
    	while i < len(sarr):
    		sarr[i] = int(sarr[i])
    		self.assertEqual(extargsparse.__version_info__[i],sarr[i])
    		i += 1
    	return




def set_log_level(args):
    loglvl= logging.ERROR
    if args.verbose >= 3:
        loglvl = logging.DEBUG
    elif args.verbose >= 2:
        loglvl = logging.INFO
    elif args.verbose >= 1 :
        loglvl = logging.WARN
    # we delete old handlers ,and set new handler
    logging.basicConfig(level=loglvl,format='%(asctime)s:%(filename)s:%(funcName)s:%(lineno)d\t%(message)s')
    return


def release_handler(args,parser):
	set_log_level(args)
	global topdir
	_reload_extargs_debug_path(os.path.join(topdir,'src','extargsparse'))
	mod = importlib.import_module('__lib_debug__')
	includes = args.release_importnames
	logging.info('args %s includes %s'%(repr(args),includes))
	repls = dict()
	for p in args.release_adds:
		key = '\\b(%s)\\b'%(p)
		repls[key] = 'extargsparse.\\1'

	repls['EXTARGS_RELEASE_MODE=False'] = 'EXTARGS_RELEASE_MODE=True'
	logging.info('includes %s repls %s'%(includes,repr(repls)))
	s = rtools.release_get_catch(mod,includes,[],repls)
	outs = slash_string(s)
	releaserepls = dict()
	releasekey = 'test_placer_holder'
	releasekey += '='
	releasekey += "True"
	releaserepls[releasekey] = outs
	logging.info('releaserepls %s'%(repr(releaserepls)))
	rtools.release_file(None,args.release_output,[],[],[],releaserepls)
	sys.exit(0)
	return

def test_handler(args,parser):
	set_log_level(args)
	testargs = []
	if args.verbose >= 3:
		if '-v' not in args.subnargs and '--verbose' not in subnargs:
			testargs.append('-v')
	testargs.extend(args.subnargs)
	sys.argv[1:] = testargs
	unittest.main()

	sys.exit(0)
	return

def slash_string(s):
	outs =''
	for c in s:
		if c == '\\':
			outs += '\\\\'
		else:
			outs += c
	return outs

def main():
	outputfile_orig = os.path.join(os.path.dirname(os.path.abspath(__file__)),'release.py')
	outputfile = slash_string(outputfile_orig)
	commandline_fmt = '''
		{
			"verbose|v" : "+",
			"release<release_handler>##release file##" : {
				"output|O" : "%s",
				"importnames|I" : ["debug_args_function","debug_tcebase","debug_extargs_test_case","_LoggerObject"],
				"adds|A" : ["ExtArgsParse","ExtArgsOptions","set_attr_args","SUB_COMMAND_JSON_SET","COMMAND_JSON_SET","ENVIRONMENT_SET","ENV_SUB_COMMAND_JSON_SET","ENV_COMMAND_JSON_SET"]
			},
			"test<test_handler>##test mode##" : {
				"$" : "*"
			}
		}
	'''
	commandline = commandline_fmt%(outputfile)
	options = extargsparse.ExtArgsOptions()
	parser = extargsparse.ExtArgsParse(options)
	parser.load_command_line_string(commandline)
	args = parser.parse_command_line()
	return

if __name__ == '__main__':
	main()
