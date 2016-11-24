# extargsparse 
> python command package for json string set

### simple example
```python
import extargsparse
import sys
commandline = '''
{
	"verbose|v<verbosemode>##increment verbose mode##" : "+",
	"flag|f<flagmode>## flag set##" : false,
	"number|n" : 0,
	"list|l<listarr>" : [],
	"string|s" : "string_var",
	"$" : "*"
}
'''

def main():
    parser = extargsparse.ExtArgsParse(usage=' sample commandline parser ')
    parser.load_command_line_string(commandline)
    args = parser.parse_command_line()
    print ('verbose = %d'%(args.verbose))
    print ('flag = %s'%(args.flag))
    print ('number = %d'%(args.number))
    print ('list = %s'%(args.list))
    print ('string = %s'%(args.string))
    print ('args = %s'%(args.args))
    s = parser.shell_eval_out()
    sys.stdout.write('\n')
    sys.stdout.write('shell output:\n')
    sys.stdout.write('%s'%(s))
    return

if __name__ == '__main__':
    main()
```

> if the command line like this
> python test.py -vvvv -f -n 30 -l bar1 -l bar2 var1 var2

> result is like this

```shell
verbose = 4
flag = True
number = 30
list = ['bar1', 'bar2']
string = string_var
args = ['var1', 'var2']

shell output:
flagmode=1
string=string_var
declare -A args
args[0]=var1
args[1]=var2
number=30
verbosemode=4
declare -A listarr
listarr[0]=bar1
listarr[1]=bar2
```


### some complex example

```python
import extargsparse
commandline = '''
{
	"verbose|v" : "+",
	"port|p" : 3000,
	"dep" : {
		"list|l" : [],
		"string|s" : "s_var",
		"$" : "+"
	}
}
'''

def main():
    parser = extargsparse.ExtArgsParse(usage=' sample commandline parser ')
    parser.load_command_line_string(commandline)
    args = parser.parse_command_line(['-vvvv','-p','5000','dep','-l','arg1','--dep-list','arg2','cc','dd'])
    print ('verbose = %d'%(args.verbose))
    print ('port = %s'%(args.port))
    print ('subcommand = %s'%(args.subcommand))
    print ('list = %s'%(args.dep_list))
    print ('string = %s'%(args.dep_string))
    print ('subnargs = %s'%(args.subnargs))
```

> result is like this

```shell
verbose = 4
port = 5000
subcommand = dep
list = ['arg1','arg2']
string = 's_var'
subnargs = ['cc','dd']
```

### multiple sub command  

```python
import extargsparse
loads = '''
    {
      "verbose|v" : "+",
      "port|p" : 3000,
      "dep" : {
        "list|l" : [],
        "string|s" : "s_var",
        "$" : "+"
      },
      "rdep" : {
        "list|L" : [],
        "string|S" : "s_rdep",
        "$" : 2
      }
    }
'''

def main():
    parser = extargsparse.ExtArgsParse()
    parser.load_command_line_string(loads)
    args = parser.parse_command_line(['-vvvv','-p','5000','rdep','-L','arg1','--rdep-list','arg2','cc','dd'])
    print('verbose %d'%(args.verbose))
    print('port %d'%(args.port))
    print('subcommand %s'%(args.subcommand))
    print('rdep_list %s'%(args.rdep_list))
    print('rdep_string %s'%(args.rdep_string))
    print('subnargs %s'%(args.subnargs))
    return

if __name__ == '__main__':
  main()  

```

> result is two subcommand prepared 
```shell
verbose 4
port 5000
subcommand rdep
rdep_list ['arg1','arg2']
subnargs ['cc','dd']
```

### use in multi load_command_line_string 

```python

import extargsparse

def load_s_1(parser):
    load1 = '''
    {
      "verbose|v" : "+",
      "port|p" : 3000,
      "dep" : {
        "list|l" : [],
        "string|s" : "s_var",
        "$" : "+"
      }
    }
    '''
    parser.load_command_line_string(load1)
    return parser

def load_s_2(parser):
    load2 = '''
    {
      "rdep" : {
        "list|L" : [],
        "string|S" : "s_rdep",
        "$" : 2
      }
    }
    '''
    parser.load_command_line_string(load2)
    return parser

def main():
    parser = extargsparse.ExtArgsParse()
    parser = load_s_1(parser)
    parser = load_s_2(parser)
    args = parser.parse_load_command(['-p','7003','-vvvvv','rdep','-L','foo1','-S','new_var','zz','64'])
    print('port %d'%(args.port))
    print('verbose %d'%(args.verbose))
    print('subcommand %s'%(args.subcommand))
    print('rdep_list %s'%(args.rdep_list))
    print('rdep_string %s'%(args.rdep_string))
    print('subnargs %s'%(args.subnargs))
    return

if __name__ == '__main__':
  main()  

```

> result

```shell
verbose 5
port 7003
subcommand rdep
rdep_list ['foo1']
rdep_string new_var
subnargs ['zz','64']
```


### callback handle function example

```python
import extargsparse
import os
commandline = '''
{
	"verbose|v" : "+",
	"port|p" : 3000,
	"dep<__main__.dep_handler>" : {
		"list|l" : [],
		"string|s" : "s_var",
		"$" : "+"
	}
}
'''

def dep_handler(args,context):
    print ('verbose = %d'%(args.verbose))
    print ('port = %s'%(args.port))
    print ('subcommand = %s'%(args.subcommand))
    print ('list = %s'%(args.dep_list))
    print ('string = %s'%(args.dep_string))
    print ('subnargs = %s'%(args.subnargs))
    print ('context["base"] = %s'%(context['base']))
    os.exit(0)
    return

def main():
    context = dict()
    context['base'] = 'basenum'
    parser = extargsparse.ExtArgsParse(usage=' sample commandline parser ')
    parser.load_command_line_string(commandline)
    args = parser.parse_command_line(['-vvvv','-p',5000,'dep','-l','arg1','-l','arg2','cc','dd'],context)
```

> result is like this

```shell
verbose = 4
port = 5000
subcommand = dep
list = ['arg1','arg2']
string = 's_var'
subnargs = ['cc','dd']
context["base"] = basenum
```


### with extension flag example

```python
import extargsparse
import os
commandline = '''
{
	"verbose|v" : "+",
	"port|p+http" : 3000,
	"dep<__main__.dep_handler>" : {
		"list|l" : [],
		"string|s" : "s_var",
		"$" : "+"
	}
}
'''

def dep_handler(args):
    print ('verbose = %d'%(args.verbose))
    print ('port = %s'%(args.http_port))
    print ('subcommand = %s'%(args.subcommand))
    print ('list = %s'%(args.dep_list))
    print ('string = %s'%(args.dep_string))
    print ('subnargs = %s'%(args.subnargs))
    os.exit(0)
    return

def main():
    parser = extargsparse.ExtArgsParse(usage=' sample commandline parser ')
    parser.load_command_line_string(commandline)
    args = parser.parse_command_line(['-vvvv','-p',5000,'dep','-l','arg1','-l','arg2','cc','dd'])
```

> result is like this

```shell
verbose = 4
port = 5000
subcommand = dep
list = ['arg1','arg2']
string = 's_var'
subnargs = ['cc','dd']
```

### with extension flag bundle example

```python
import extargsparse
import os
commandline = '''
{
	"verbose|v" : "+",
	"+http" : {
		"port|p" : 3000,
		"visual_mode|V" : false
	},
	"dep<__main__.dep_handler>" : {
		"list|l" : [],
		"string|s" : "s_var",
		"$" : "+"
	}
}
'''

def dep_handler(args):
    print ('verbose = %d'%(args.verbose))
    print ('port = %s'%(args.http_port))
    print ('visual_mode = %s'%(args.http_visual_mode))
    print ('subcommand = %s'%(args.subcommand))
    print ('list = %s'%(args.dep_list))
    print ('string = %s'%(args.dep_string))
    print ('subnargs = %s'%(args.subnargs))
    os.exit(0)
    return

def main():
    parser = extargsparse.ExtArgsParse(usage=' sample commandline parser ')
    parser.load_command_line_string(commandline)
    args = parser.parse_command_line(['-vvvv','-p','5000','--http-visual-mode','dep','-l','arg1','--dep-list','arg2','cc','dd'])
```

> result is like this

```shell
verbose = 4
port = 5000
visual_mode = True
subcommand = dep
list = ['arg1','arg2']
string = 's_var'
subnargs = ['cc','dd']
```
### with complex flag set

```python
import extargsparse
import os
commandline = '''
{
	"verbose|v" : "+",
	"$port|p" : {
		"value" : 3000,
		"type" : "int",
		"nargs" : 1 , 
		"helpinfo" : "port to connect"
	},
	"dep<__main__.dep_handler>" : {
		"list|l" : [],
		"string|s" : "s_var",
		"$" : "+"
	}
}
'''

def dep_handler(args):
    print ('verbose = %d'%(args.verbose))
    print ('port = %s'%(args.port))
    print ('subcommand = %s'%(args.subcommand))
    print ('list = %s'%(args.list))
    print ('string = %s'%(args.string))
    print ('subnargs = %s'%(args.subnargs))
    os.exit(0)
    return

def main():
    parser = extargsparse.ExtArgsParse(usage=' sample commandline parser ')
    parser.load_command_line_string(commandline)
    args = parser.parse_command_line(['-vvvv','-p','5000','dep','-l','arg1','-l','arg2','cc','dd'])
```

> result is like this

```shell
verbose = 4
port = 5000
subcommand = dep
list = ['arg1','arg2']
string = 's_var'
subnargs = ['cc','dd']
```

### shellout example
```python
import extargsparse
import sys
commandline = '''
{
  "verbose|v<verbosemode>##increment verbose mode##" : "+",
  "flag|f<flagmode>## flag set##" : false,
  "number|n" : 0,
  "list|l<listarr>" : [],
  "string|s" : "string_var",
  "dep<CHOICECOMMAND>" : {
      "$<DEPAPPS>" : "+"
  }
}
'''

def main():
    parser = extargsparse.ExtArgsParse(usage=' sample commandline parser ')
    parser.load_command_line_string(commandline)
    s = parser.shell_eval_out()
    sys.stdout.write('shell output:\n')
    sys.stdout.write('%s'%(s))
    return

if __name__ == '__main__':
    main()
```

> if the command line like this
> python test.py -vvv dep ccc

> result is like this

```shell
shell output:
flagmode=0
string=string_var
number=0
verbosemode=3
declare -A listarr
CHOICECOMMAND=dep
declare -A DEPAPPS
DEPAPPS[0]=ccc
```


## Rules

* all key is with value of dict will be flag
 **   like this 'flag|f' : true
     --flag or -f will set the False value for this ,default value is True
 **  like 'list|l' : [] 
     --list or -l will append to the flag value ,default is []

* if value is dict, the key is not start with special char ,it will be the sub command name 
  ** for example 'get' : {
       'connect|c' : 'http://www.google.com',
       'newone|N' : false
  } this will give the sub command with two flag (--get-connect or -c ) and ( --get-newone or -N ) default value is 'http://www.google.com' and False

* if value is dict , the key start with '$' it means the flag description dict 
  ** for example '$verbose|v' : {
  	'value' : 0,
  	'type' : '+',
  	'nargs' : 0,
  	'help' : 'verbose increment'
  }   it means --verbose or -v will be increment and default value 0 and need args is 0  help (verbose increment)

* if the value is dict ,the key start with '+' it means add more bundles of flags
  **  for example  	'+http' : {
		'port|p' : 3000,
		'visual_mode|V' : false
	} --http-port or -p  and --http-visual-mode or -V will set the flags ,short form it will not affected

* if in flagmode , follows <.*> it will be set for shell output value
  ** for example '$verbose|v<verbosemode>' : '+'
    call shell_eval_out will add 
    verbosemode=%d\n
    in the return string see the [simple example](#simple-example)

* if the subcommand follows <.*> it will call function 
  **  for example 	'dep<__main__.dep_handler>' : {
		'list|l' : [],
		'string|s' : 's_var',
		'$' : '+'
	}  the dep_handler will call __main__ it is the main package ,other packages will make the name of it ,and the 
	   args is the only one add
  if you just call shell_eval_out it will make the function name as the variable  to set for the commandname see [shellout example](#shellout-example)

* special flag '$' is for args in main command '$' for subnargs in sub command


* special flag --json for parsing args in json file in main command
* special flag '--%s-json'%(args.subcommand) for  subcommand for example
   ** --dep-json dep.json will set the json command for dep sub command ,and it will give the all omit the command
   for example 	"dep<__main__.dep_handler>" : {
		"list|l" : [],
		"string|s" : "s_var",
		"$" : "+"
	}  
    in dep.json
    {
    	"list" : ["jsonval1","jsonval2"],
    	"string" : "jsonstring"
    }

*** example
```python
import extargsparse
import os
commandline = '''
{
	"verbose|v" : "+",
	"+http" : {
		"port|p" : 3000,
		"visual_mode|V" : false
	},
	"dep<__main__.dep_handler>" : {
		"list|l" : [],
		"string|s" : "s_var",
		"$" : "+"
	}
}
'''

def dep_handler(args):
    print ('verbose = %d'%(args.verbose))
    print ('port = %s'%(args.http_port))
    print ('visual_mode = %s'%(args.http_visual_mode))
    print ('subcommand = %s'%(args.subcommand))
    print ('list = %s'%(args.dep_list))
    print ('string = %s'%(args.dep_string))
    print ('subnargs = %s'%(args.subnargs))
    os.exit(0)
    return

def main():
    parser = extargsparse.ExtArgsParse(usage=' sample commandline parser ')
    parser.load_command_line_string(commandline)
    args = parser.parse_command_line(['-vvvv','-p','5000','--http-visual-mode','dep','--dep-json','dep.json','-l','arg1','--dep-list','arg2','cc','dd'])
```

result like this
```shell
verbose = 4
port = 5000
visual_mode = True
subcommand = dep
list = ['arg1','arg2']
string = 'jsonstring'
subnargs = ['cc','dd']
```
> because we modify the value in the command line ,so the json file value is ignored

*  you can specify the main command line to handle the json for example
   {
   	 "dep" : {
   	 	"string" : "jsonstring",
   	 	"list" : ["jsonlist1","jsonlist2"]
   	 },
   	 "port" : 6000,
   	 "verbose" : 4
   }

* you can specify the json file by environment value for main file json file the value is
   **EXTARGSPARSE_JSONFILE
      for subcommand json file is
      DEP_JSONFILE  DEP is the subcommand name uppercase

   ** by the environment variable can be set for main command
      EXTARGSPARSE_PORT  is for the main command -p|--port etc
      for sub command is for DEP_LIST for dep command --list


* note the priority of command line is  this can be change or omit by the extargsparse.ExtArgsParse(priority=[])
   **   command input 
   **   subcommand json file input extargsparse.SUB_COMMAND_JSON_SET
   **   command json file input extargsparse.COMMAND_JSON_SET
   **   environment variable input _if the common args not with any _ in the flag dest ,it will start with EXTARGS_  extargsparse.ENVIRONMENT_SET
   **   environment subcommand json file input extargsparse.ENV_SUB_COMMAND_JSON_SET
   **   environment json file input  extargsparse.ENV_COMMAND_JSON_SET
   **   default value input by the load string


* flag option key
   **  flagname the flagname of the value
   **  shortflag flag set for the short
   **  value  the default value of flag
   **  nargs it accept args "*" for any "?" 1 or 0 "+" equal or more than 1 , number is the number
   **  helpinfo for the help information
   **  varname for the shell eval option

* flag format description
   **  if the key is flag it must with format like this 
           [$]?flagname|shortflag+prefix##helpinfo##
        $ is flag start character ,it must be the first character
        flagname name of the flag it is required
        shortflag is just after flagname with |,it is optional
        prefix is just after shortflag with + ,it is optional
        helpinfo is just after prefix with ## and end with ## ,it is optional ,and it must be last part

* command format description
  ** if the key is command ,it must with format like this
           cmdname<function>##helpinfo##
        cmdname is the command name
        function is just after cmdname ,it can be the optional ,it will be the call function name ,it include the packagename like '__main__.call_handler'
        helpinfo is just after function ,it between ## ## it is optional

* enable debug 
  ** you can specified the environment value EXTARGSPARSE_LOGLEVELV=DEBUG to enable the debug of extargsparse

# Most Complex Example

```python
#!/usr/bin/python
import tempfile
import os
import sys
import extargsparse


def main():
  commandline= '''
  {
    "verbose|v" : "+",
    "rollback|R" : true,
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
    parser = extargsparse.ExtArgsParse(priority=[extargsparse.ENV_COMMAND_JSON_SET,extargsparse.ENVIRONMENT_SET,extargsparse.ENV_SUB_COMMAND_JSON_SET])
    parser.load_command_line_string(commandline)
    os.environ['DEP_STRING'] = depstrval
    os.environ['DEP_LIST'] = depliststr
    os.environ['HTTP_VISUAL_MODE']=httpvmstr
    
    args = parser.parse_command_line(['-p','9000','--no-rollback','dep','--dep-string','ee','ww'])
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
```

> result is

```shell
args.verbose 3
args.port 9000
args.rollback False
args.dep_list [u'jsonval1', u'jsonval2']
args.dep_string ee
args.http_visual_mode True
args.http_url http://www.yahoo.com
args.subcommand dep
args.subnargs ['ww']
```
