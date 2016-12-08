#! /usr/bin/env python

import sys
import os
import importlib
import inspect
import logging
import re
_extargs_parent_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)),'..','..'))
if _extargs_parent_dir not in sys.path:
    _temp_path = sys.path
    sys.path = [_extargs_parent_dir]
    sys.path.extend(_temp_path)
import extargsparse


class MinNumber(object):
	keywords = ['lineno']
	maxval = 0xffffffffffffffff
	def __init__(self):
		self.lineno = self.__class__.maxval
		return

	def __getattr__(self,key,defval):
		if key in self.__dict__.keys():
			return self.__dict__[key]
		return self.__class__.maxval

	def __setattr__(self,key,val):
		if not key.startswith('_'):
			if self.__getattr__(key,self.__class__.maxval) > val:
				self.__dict__[key] = val
			return
		self.__dict__[key] = val
		return

	def __str__(self):
		s = '{'
		i = 0
		for k in dir(self):
			if k.startswith('_'):
				continue
			if i > 0 :
				s += ';'
			s += '%s=%s'%(k,self.__dict__[k])
			i += 1
		s += '}'
		return s


class ModuleSource(object):
	def __init__(self):
		self.__statics = []
		self.__code = dict()
		self.__names = dict()
		return

	def add_code(self,lineno,source,name):
		self.__code[lineno] = source
		self.__names[lineno] = name
		return
	def add_static(self,source):
		self.__statics.append(source)
		return

	def __str__(self):
		s = ''
		for c in self.__statics:
			s += '%s'%(c)
		s += '\n'
		for l in sorted(self.__code.keys()):
			logging.info('[%d] %s'%(l,self.__names[l]))
			s += '%s'%(self.__code[l])
		return s


def get_line_start(linearr,srclines):
	i = 0
	j = 0
	startline = -1
	for l in linearr:
		i += 1
		if j == 0 and l == srclines[j]:
			minline.lineno = i
			j += 1
			startline = i
		elif j > 0 and j < len(srclines) :
			if l == srclines[j]:
				j += 1
			else:
				j = 0
				startline = -1
				logging.error('[%d] lines not match %s'%(j,srclines[j]))
	return startline




def get_source_code(args,source,excludes=[],check_callback=None,ctx=None):
	modsrc = ModuleSource()
	m = importlib.import_module(source)	
	if m is None:
		logging.error('can not load %s\n'%(source))
		return modsrc

	for d in dir(m):
		v = getattr(m,d,None)
		#logging.info('[%s] type %s'%(d,type(v).__name__))
		if d == '__builtins__' or d == '__doc__' or d in excludes:
			continue
		if check_callback is not None:
			check_callback(d,v,ctx)
		if inspect.isclass(v):
			lines,startline =  inspect.getsourcelines(v)
			s = '%s\n'%(inspect.getsource(v))
			#logging.info('[%s] %d'%(d,startline))
			modsrc.add_code(startline,s,d)
		elif inspect.isfunction(v):
			lines,startline = inspect.getsourcelines(v)
			s = '%s\n'%(inspect.getsource(v))
			#logging.info('[%s] %d'%(d,startline))
			modsrc.add_code(startline,s,d)
		elif isinstance(v,int):
			s = '%s=%s\n'%(d,v)
			modsrc.add_static(s)
		elif isinstance(v,str) or (sys.version[0] == '2' and isinstance(v,unicode)):
			s = '%s=%s\n'%(d,v)
			modsrc.add_static(s)		
		else:
			logging.info('[%s] not handle'%(d))
	return modsrc


def check_method_callback(key,val,ctx):
	for k in ctx.checkmethod:
		sarr = re.split('\.',k)
		if key == sarr[0] and len(sarr) > 1:
			# now check whether it is a method
			if sarr[1] not in dir(val):
				raise Exception('%s not method in'%(k))
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




def main():
	commandline='''
	{
		"verbose|v" : "+",
		"excludes|E" : [],
		"input|i" : null,
		"pattern|P" : null,
		"output|o" : null,
		"checkmethod|c" : [],
		"replace|r" : [],
		"$" : "*"
	}
	'''
	parser = extargsparse.ExtArgsParse()
	parser.load_command_line_string(commandline)
	args = parser.parse_command_line()
	set_log_level(args)
	totals = ''
	for c in args.args:
		totals += '%s'%(get_source_code(args,c,args.excludes,check_method_callback,args))
	fout = sys.stdout
	fin = sys.stdin
	lines = re.split('\n',totals)
	if args.output is not None:
		logging.info('%s for output'%(args.output))
		fout = open(args.output,'w+')
	if args.input is not None:
		logging.info('%s for input'%(args.input))
		fin = open(args.input,'r+')
	repat = dict()
	if len(args.replace) > 0:
		for chgpat in args.replace:
			sarr = re.split('=',chgpat,2)
			if len(sarr) > 1:
				repat[sarr[0]] = sarr[1]
			else:
				repat[sarr[0]] = ''
			logging.info('%s=%s'%(sarr[0],repat[sarr[0]]))
	news = ''
	for l in lines:
		if len(args.replace) > 0:
			for k in repat.keys():
				l = re.sub(k,repat[k],l)
		news += '%s\n'%(l)
	# now we should give the replace

	for l in fin:
		l = l.rstrip('\r\n')
		logging.info('in [%s]pattern %s\n'%(l,args.pattern))
		if args.pattern is not None and l == args.pattern :
			l = news
		fout.write('%s\n'%(l))

	if fout != sys.stdout:
		fout.close()
	fout = None

	if fin != sys.stdin:
		fin.close()
	fin = None

if __name__ == '__main__':
	main()



