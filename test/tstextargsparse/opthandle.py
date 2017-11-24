#! /usr/bin/env python


import tempfile
import sys
import os

_extargs_parent_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)),'..','..'))
if _extargs_parent_dir not in sys.path:
	_temp_path = sys.path
	sys.path = [_extargs_parent_dir]
	sys.path.extend(_temp_path)

import extargsparse


def pair_parse(args,validx,keycls,params):
	if (validx + 1) >= len(params):
		raise Exception('need 2 args for [++pair|+p]')
	val = getattr(args,keycls.optdest,None)
	if val is None:
		val = []
	val.append(params[validx])
	val.append(params[(validx+1)])
	setattr(args,keycls.optdest,val)
	return 2

def pair_help(keycls):
	return '[first] [second]'

def single_2_jsonfunc(args,keycls,value):
    if not isinstance(value,list):
        raise Exception('not list value')
    if (len(value) % 2) != 0:
        raise Exception('not even sized')
    setvalue = []
    i = 0
    while i < len(value):
        setvalue.append(value[i])
        i += 2
    setattr(args,keycls.optdest,setvalue)
    return


def main():
	commandline='''
	{
		"verbose|v" : "+",
		"pair|p!optparse=pair_parse;opthelp=pair_help!" : [],
		"even|e!jsonfunc=single_2_jsonfunc!" : [],
		"clr_CA_name" : null,
		"$" : "*"
	}
	'''
	options = extargsparse.ExtArgsOptions()
	options.longprefix = '++'
	options.shortprefix = '+'
	options.jsonlong = 'jsonfile'
	options.helplong = 'usage'
	options.helpshort = '?'
	options.flagnochange = True
	parser = extargsparse.ExtArgsParse(options)
	parser.load_command_line_string(commandline)
	args = parser.parse_command_line()
	print('verbose [%d]'%(args.verbose))
	print('pair (%s)'%(args.pair))
	print('args (%s)'%(args.args))
	print('clr_CA_name (%s)'%(args.clr_CA_name))
	print('event (%s)'%(args.even))
	return

if __name__ == '__main__':
	main()
