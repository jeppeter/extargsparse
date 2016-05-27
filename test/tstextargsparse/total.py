#!/usr/bin/python
import tempfile
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..')))
import extargsparse


def main():
	commandline= '''
	{
		"verbose|v" : "+",
		"+http" : {
			"url|u" : "http://www.google.com",
			"visual_mode|V": false
		},
		"$port|p" : {
			"value" : 3000,
			"type" : "int",
			"nargs" : 1 , 
			"helpinfo" : "port to connect"
		},
		"dep" : {
			"list|l" : [],
			"string|s" : "s_var",
			"$" : "+"
		}
	}
	'''
	jsonfile = None
	depjsonfile = None
	try:
		depstrval = 'newval'
		depliststr = '["depenv1","depenv2"]'
		deplistval = eval(depliststr)
		httpvmstr = "True"
		httpvmval = eval(httpvmstr)
		fd,jsonfile = tempfile.mkstemp(suffix='.json',prefix='parse',dir=None,text=True)
		os.close(fd)
		fd = -1
		fd ,depjsonfile = tempfile.mkstemp(suffix='.json',prefix='parse',dir=None,text=True)
		os.close(fd)
		fd = -1
		with open(jsonfile,'w+') as f:
			f.write('{ "http" : { "url" : "http://www.yahoo.com"} ,"dep":{"list" : ["jsonval1","jsonval2"],"string" : "jsonstring"},"port":6000,"verbose":3}\n')
		with open(depjsonfile,'w+') as f:
			f.write('{"list":["depjson1","depjson2"]}\n')
		delone = True
		while delone:
			delone = False
			for k in os.environ.keys():
				if k.startswith('EXTARGS_') or k.startswith('DEP_') or k == 'EXTARGSPARSE_JSON' or k.startswith('HTTP_'):
					del os.environ[k]
					delone = True
					break

		os.environ['EXTARGSPARSE_JSON'] = jsonfile
		os.environ['DEP_JSON'] = depjsonfile
		parser = extargsparse.ExtArgsParse()
		parser.load_command_line_string(commandline)
		os.environ['DEP_STRING'] = depstrval
		os.environ['DEP_LIST'] = depliststr
		os.environ['HTTP_VISUAL_MODE']=httpvmstr
		
		args = parser.parse_command_line(['-p','9000','dep','--dep-string','ee','ww'])
		print('args.verbose %d'%(args.verbose))
		print('args.port %d'%(args.port))
		print('args.dep_list %s'%(args.dep_list))
		print('args.dep_string %s'%(args.dep_string))
		print('args.http_visual_mode %s'%(args.http_visual_mode))
		print('args.http_url %s'%(args.http_url))
		print('args.subcommand %s'%(args.subcommand))
		print('args.subnargs %s'%(args.subnargs))
	finally:
		if depjsonfile is not None:
			os.remove(depjsonfile)
		depjsonfile = None
		if jsonfile is not None:
			os.remove(jsonfile)
		jsonfile = None
		if 'EXTARGSPARSE_JSON' in os.environ.keys():
			del os.environ['EXTARGSPARSE_JSON']
		if 'DEP_JSON' in os.environ.keys():
			del os.environ['DEP_JSON']
	return

if __name__ == '__main__':
	main()