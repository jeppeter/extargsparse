#!/usr/bin/python

import argparse
import os
import sys
import json
import logging
import unittest
import re
import importlib
import tempfile
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import __key__ as keyparse

COMMAND_SET = 10
SUB_COMMAND_JSON_SET = 20
COMMAND_JSON_SET = 30
ENVIRONMENT_SET = 40
ENV_SUB_COMMAND_JSON_SET = 50
ENV_COMMAND_JSON_SET = 60
DEFAULT_SET = 70

def set_attr_args(self,args,prefix):
    if not issubclass(args.__class__,argparse.Namespace):
        raise Exception('second args not valid argparse.Namespace subclass')
    for p in vars(args).keys():
        if len(prefix) == 0 or p.startswith('%s_'%(prefix)):
            setattr(self,p,getattr(args,p))
    return

def call_func_args(funcname,args,Context):
    mname = '__main__'
    fname = funcname
    try:
        if '.' not in funcname:
            m = importlib.import_module(mname)
        else:
            sarr = re.split('\.',funcname)
            mname = '.'.join(sarr[:-1])
            fname = sarr[-1]
            m = importlib.import_module(mname)
    except ImportError as e:
        sys.stderr.write('can not load %s\n'%(mname))
        return args

    for d in dir(m):
        if d == fname:
            val = getattr(m,d)
            if hasattr(val,'__call__'):
                val(args,Context)
                return args
    sys.stderr.write('can not call %s\n'%(funcname))
    return args




class IntAction(argparse.Action):
     def __init__(self, option_strings, dest, nargs=1, **kwargs):
        super(IntAction,self).__init__(option_strings, dest, **kwargs)
        return

     def __call__(self, parser, namespace, values, option_string=None):
        try:
            intval = int(values)
        except:
            raise Exception('%s not valid number'%(values))
        setattr(namespace,self.dest,intval)
        return

class _ParserCompact(object):
    pass

class ArrayAction(argparse.Action):
     def __init__(self, option_strings, dest, nargs=1, **kwargs):
        argparse.Action.__init__(self,option_strings, dest, **kwargs)
        return

     def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace,self.dest) is None:
            setattr(namespace,self.dest,[])
        lists = getattr(namespace,self.dest)
        if values not in lists:
            lists.append(values)
        setattr(namespace,self.dest,lists)
        return

class FloatAction(argparse.Action):
     def __init__(self, option_strings, dest, nargs=1, **kwargs):
        super(IntAction,self).__init__(option_strings, dest, **kwargs)
        return

     def __call__(self, parser, namespace, values, option_string=None):
        try:
            fval = float(values)
        except:
            raise Exception('%s not valid number'%(values))
        setattr(namespace,self.dest,fval)
        return



class ExtArgsParse(argparse.ArgumentParser):
    reserved_args = ['subcommand','subnargs','json','nargs','extargs']
    priority_args = [SUB_COMMAND_JSON_SET,COMMAND_JSON_SET,ENVIRONMENT_SET,ENV_SUB_COMMAND_JSON_SET,ENV_COMMAND_JSON_SET]
    def __get_help_info(self,keycls):
        helpinfo = ''
        if keycls.type == 'bool':
            if keycls.value :
                helpinfo += '%s set false default(True)'%(keycls.optdest)
            else:
                helpinfo += '%s set true default(False)'%(keycls.optdest)
        elif keycls.type == 'string' and keycls.value == '+':
            if keycls.isflag:
                helpinfo += '%s inc'%(keycls.optdest)
            else:
                raise Exception('cmd(%s) can not set value(%s)'%(keycls.cmdname,keycls.value))
        else:
            if keycls.isflag:
                helpinfo += '%s set default(%s)'%(keycls.optdest,keycls.value)
            else:
                helpinfo += '%s command exec'%(keycls.cmdname)
        if keycls.helpinfo:
            helpinfo = keycls.helpinfo
        return helpinfo

    def __check_flag_insert(self,keycls,curparser=None):
        if curparser :
            for k in curparser.flags:
                if k.flagname != '$' and keycls.flagname != '$':
                    if k.optdest == keycls.optdest:
                        return False
                elif k.flagname == keycls.flagname:
                    return False
            curparser.flags.append(keycls)
        else:
            for k in self.__flags:
                if (k.flagname != '$') and (keycls.flagname != '$'):
                    if k.optdest == keycls.optdest:
                        return False
                elif k.flagname == keycls.flagname:
                    return False
            self.__flags.append(keycls)
        return True

    def __check_flag_insert_mustsucc(self,keycls,curparser=None):
        valid = self.__check_flag_insert(keycls,curparser)
        if not valid:
            cmdname = 'main'
            if curparser:
                cmdname = curparser.cmdname
            raise Exception('(%s) already in command(%s)'%(keycls.flagname,cmdname))
        return

    def __load_command_line_string(self,prefix,keycls,curparser=None):
        self.__check_flag_insert_mustsucc(keycls,curparser)
        longopt = keycls.longopt
        shortopt = keycls.shortopt
        optdest = keycls.optdest
        putparser = self
        if curparser is not None:
            putparser = curparser.parser
        helpinfo = self.__get_help_info(keycls)
        if shortopt:
            putparser.add_argument(shortopt,longopt,dest=optdest,default=None,help=helpinfo)
        else:
            putparser.add_argument(longopt,dest=optdest,default=None,help=helpinfo)
        return True

    def __load_command_line_count(self,prefix,keycls,curparser=None):
        self.__check_flag_insert_mustsucc(keycls,curparser)
        longopt = keycls.longopt
        shortopt = keycls.shortopt
        optdest = keycls.optdest
        putparser = self
        if curparser is not None:
            putparser = curparser.parser
        helpinfo = self.__get_help_info(keycls)
        if shortopt:
            putparser.add_argument(shortopt,longopt,dest=optdest,default=None,action='count',help=helpinfo)
        else:
            putparser.add_argument(longopt,dest=optdest,default=None,action='count',help=helpinfo)
        return True


    def __load_command_line_int(self,prefix,keycls,curparser=None):
        self.__check_flag_insert_mustsucc(keycls,curparser)
        longopt = keycls.longopt
        shortopt = keycls.shortopt
        optdest = keycls.optdest
        helpinfo = self.__get_help_info(keycls)
        putparser = self
        if curparser is not None:
            putparser = curparser.parser

        if shortopt :
            putparser.add_argument(shortopt,longopt,dest=optdest,default=None,action=IntAction,help=helpinfo)
        else:
            putparser.add_argument(longopt,dest=optdest,default=None,action=IntAction,help=helpinfo)
        return True


    def __load_command_line_float(self,prefix,keycls,curparser=None):
        self.__check_flag_insert_mustsucc(keycls,curparser)
        longopt = keycls.longopt
        shortopt = keycls.shortopt
        optdest = keycls.optdest
        helpinfo = self.__get_help_info(keycls)
        putparser = self
        if curparser is not None:
            putparser = curparser.parser

        if shortopt :
            putparser.add_argument(shortopt,longopt,dest=optdest,default=None,action=FloatAction,help=helpinfo)
        else:
            putparser.add_argument(longopt,dest=optdest,default=None,action=FloatAction,help=helpinfo)
        return True

    def __load_command_line_list(self,prefix,keycls,curparser=None):
        self.__check_flag_insert_mustsucc(keycls,curparser)
        longopt = keycls.longopt
        shortopt = keycls.shortopt
        optdest = keycls.optdest
        helpinfo = self.__get_help_info(keycls)
        putparser = self
        if curparser is not None:
            putparser = curparser.parser
        if shortopt :
            putparser.add_argument(shortopt,longopt,dest=optdest,default=None,action=ArrayAction,help=helpinfo)
        else:
            putparser.add_argument(longopt,dest=optdest,default=None,action=ArrayAction,help=helpinfo)
        return True

    def __load_command_line_bool(self,prefix,keycls,curparser=None):
        self.__check_flag_insert_mustsucc(keycls,curparser)
        longopt = keycls.longopt
        shortopt = keycls.shortopt
        optdest = keycls.optdest
        helpinfo = self.__get_help_info(keycls)
        putparser = self
        if curparser is not None:
            putparser = curparser.parser
        if keycls.value :
            if shortopt :
                putparser.add_argument(shortopt,longopt,dest=optdest,default=None,action='store_false',help=helpinfo)
            else:
                putparser.add_argument(longopt,dest=optdest,default=None,action='store_false',help=helpinfo)
        else:
            if shortopt :
                putparser.add_argument(shortopt,longopt,dest=optdest,default=None,action='store_true',help=helpinfo)
            else:
                putparser.add_argument(longopt,dest=optdest,default=None,action='store_true',help=helpinfo)
        return True

    def __load_command_line_args(self,prefix,keycls,curparser=None):
        valid = self.__check_flag_insert(keycls,curparser)
        if not valid :
            return False
        putparser = self
        optdest = 'args'
        if curparser:
            putparser = curparser.parser
            optdest = 'subnargs'
        helpinfo = '%s set '%(optdest)
        if keycls.helpinfo:
            helpinfo = keycls.helpinfo
        if keycls.nargs != 0:
            #logging.info('optdest %s'%(optdest))
            putparser.add_argument(optdest,metavar=optdest,type=str,nargs=keycls.nargs,help=helpinfo)
        return True

    def __load_command_line_jsonfile(self,keycls,curparser=None):
        valid = self.__check_flag_insert(keycls,curparser)
        if not valid:
            return False
        putparser = self
        if curparser :
            putparser = curparser.parser
        longopt = keycls.longopt
        optdest = keycls.optdest
        helpinfo = self.__get_help_info(keycls)
        putparser.add_argument(longopt,dest=optdest,action='store',default=None,help=helpinfo)
        return True

    def __load_command_line_json_added(self,curparser=None):
        prefix = ''
        key = 'json## json input file to get the value set ##'
        value = None
        if curparser :
            prefix = curparser.cmdname
        keycls = keyparse.ExtKeyParse(prefix,key,value,True)
        return self.__load_command_line_jsonfile(keycls,curparser)


    def __init__(self,prog=None,usage=None,description=None,epilog=None,version=None,
                 parents=[],formatter_class=argparse.HelpFormatter,prefix_chars='-',
                 fromfile_prefix_chars=None,argument_default=None,
                 conflict_handler='error',add_help=True,priority=[SUB_COMMAND_JSON_SET,COMMAND_JSON_SET,ENVIRONMENT_SET,ENV_SUB_COMMAND_JSON_SET,ENV_COMMAND_JSON_SET]):
        if sys.version[0] == '2':
            super(ExtArgsParse,self).__init__(prog,usage,description,epilog,version,parents,formatter_class,prefix_chars,
                fromfile_prefix_chars,argument_default,conflict_handler,add_help)
        else:
            super(ExtArgsParse,self).__init__(prog,usage,description,epilog,parents,formatter_class,prefix_chars,
                fromfile_prefix_chars,argument_default,conflict_handler,add_help)                
        self.__logger = logging.getLogger('extargsparse')
        if len(self.__logger.handlers) == 0:
            loglvl = logging.WARN
            if 'EXTARGSPARSE_LOGLEVEL' in os.environ.keys():
                v = os.environ['EXTARGSPARSE_LOGLEVEL']
                if v == 'DEBUG':
                    loglvl = logging.DEBUG
                elif v == 'INFO':
                    loglvl = logging.INFO
            handler = logging.StreamHandler()
            fmt = "%(levelname)-8s [%(filename)-10s:%(funcName)-20s:%(lineno)-5s] %(message)s"
            if 'EXTARGSPARSE_LOGFMT' in os.environ.keys():
                v = os.environ['EXTARGSPARSE_LOGFMT']
                if v is not None and len(v) > 0:
                    fmt = v
            formatter = logging.Formatter(fmt)
            handler.setFormatter(formatter)
            self.__logger.addHandler(handler)
            self.__logger.setLevel(loglvl)
        self.__subparser = None
        self.__cmdparsers = []
        self.__flags = []
        self.__load_command_map = {
            'string' : self.__load_command_line_string,
            'unicode' : self.__load_command_line_string,
            'int' : self.__load_command_line_int,
            'float' : self.__load_command_line_float,
            'list' : self.__load_command_line_list,
            'bool' : self.__load_command_line_bool,
            'args' : self.__load_command_line_args,
            'command' : self.__load_command_subparser,
            'prefix' : self.__load_command_prefix,
            'count': self.__load_command_line_count
        }
        for p in priority:
            if p not in self.__class__.priority_args:
                raise Exception('(%s) not in priority values'%(p))
        self.__load_priority = priority
        self.__parse_set_map = {
            SUB_COMMAND_JSON_SET : self.__parse_sub_command_json_set,
            COMMAND_JSON_SET : self.__parse_command_json_set,
            ENVIRONMENT_SET : self.__parse_environment_set,
            ENV_SUB_COMMAND_JSON_SET : self.__parse_env_subcommand_json_set,
            ENV_COMMAND_JSON_SET : self.__parse_env_command_json_set
        }
        return

    def __find_subparser_inner(self,name):
        for k in self.__cmdparsers:
            if k.cmdname == name:
                return k
        return None


    def __get_subparser_inner(self,keycls):
        cmdparser = self.__find_subparser_inner(keycls.cmdname)
        if cmdparser is not None:
            return cmdparser
        if self.__subparser is None:
            self.__subparser = self.add_subparsers(help='',dest='subcommand')
        helpinfo = self.__get_help_info(keycls)
        parser = self.__subparser.add_parser(keycls.cmdname,help=helpinfo)
        cmdparser = _ParserCompact()
        cmdparser.parser = parser
        cmdparser.flags = []
        cmdparser.cmdname = keycls.cmdname
        cmdparser.typeclass = keycls
        self.__cmdparsers.append(cmdparser)
        return cmdparser


    def __load_command_subparser(self,prefix,keycls,lastparser=None):
        if lastparser :
            raise Exception('(%s) can not make command recursively'%(keycls.origkey))
        if not isinstance( keycls.value,dict):
            raise Exception('(%s) value must be dict'%(keycls.origkey))
        parser = self.__get_subparser_inner(keycls)
        self.__load_command_line_inner(keycls.prefix,keycls.value,parser)
        return True

    def __load_command_prefix(self,prefix,keycls,curparser=None):
        self.__load_command_line_inner(keycls.prefix,keycls.value,curparser)
        return True

    def __load_command_line_inner(self,prefix,d,curparser=None):
        self.__load_command_line_json_added(curparser)
        for k in d.keys():
            v = d[k]
            if curparser:
                # if we have in the mode for this we should make it
                # must be the flag mode
                self.__logger.info('%s , %s , %s , True'%(prefix,k,v))
                keycls = keyparse.ExtKeyParse(prefix,k,v,True)
            else:
                # we can not make sure it is flag mode
                self.__logger.info('%s , %s , %s , False'%(prefix,k,v))
                keycls = keyparse.ExtKeyParse(prefix,k,v,False)
            valid = self.__load_command_map[keycls.type](prefix,keycls,curparser)
            if not valid:
                raise Exception('can not add (%s)'%(k,v))
        return

    def load_command_line(self,d):
        if not isinstance(d,dict):
            raise Exception('input parameter(%s) not dict'%(d))
        self.__load_command_line_inner('',d,None)
        return


    def load_command_line_string(self,s):
        try:
            d = json.loads(s)
        except:
            raise Exception('(%s) not valid json string'%(s))
        #self.__logger.info('d (%s)'%(d))
        self.load_command_line(d)
        return


    def __set_jsonvalue_not_defined(self,args,flagarray,key,value):
        for p in flagarray:
            if p.isflag and p.type != 'prefix' and p.type != 'args':
                if p.optdest == key:
                    if getattr(args,key,None) is None:
                        if str(keyparse.TypeClass(value)) != str(keyparse.TypeClass(p.value)):
                            self.__logger.warn('%s  type (%s) as default value type (%s)'%(key,str(keyparse.TypeClass(value)),str(keyparse.TypeClass(p.value))))
                        self.__logger.info('set (%s)=(%s)'%(key,value))
                        setattr(args,key,value)
                    return args
        # we search for other value
        for p in self.__flags:
            if p.isflag and p.type != 'prefix' and p.type != 'args':
                if p.optdest == key:
                    if getattr(args,key,None) is None:
                        if str(keyparse.TypeClass(value)) != str(keyparse.TypeClass(p.value)):
                            self.__logger.warn('%s  type (%s) as default value type (%s)'%(key,str(keyparse.TypeClass(value)),str(keyparse.TypeClass(p.value))))
                        self.__logger.info('set (%s)=(%s)'%(key,value))
                        setattr(args,key,value)
                    return args
        for parser in self.__cmdparsers:
            for p in parser.flags:
                if p.isflag and p.type != 'prefix' and p.type != 'args':
                    if p.optdest == key:
                        if getattr(args,key,None) is None:
                            if str(keyparse.TypeClass(value)) != str(keyparse.TypeClass(p.value)):
                                self.__logger.warn('%s  type (%s) as default value type (%s)'%(key,str(keyparse.TypeClass(value)),str(keyparse.TypeClass(p.value))))
                            self.__logger.info('set (%s)=(%s)'%(key,value))
                            setattr(args,key,value)
                        return args
        self.__logger.warn('can not search for (%s)'%(key))
        return args

    def __load_jsonvalue(self,args,prefix,jsonvalue,flagarray):
        for k in jsonvalue:
            if isinstance(jsonvalue[k],dict):
                newprefix = ''
                if len(prefix) > 0:
                    newprefix += '%s_'%(prefix)
                newprefix += k
                args = self.__load_jsonvalue(args,newprefix,jsonvalue[k],flagarray)
            else:
                newkey = ''
                if (len(prefix) > 0):
                    newkey += '%s_'%(prefix)
                newkey += k
                args = self.__set_jsonvalue_not_defined(args,flagarray,newkey,jsonvalue[k])
        return args


    def __load_jsonfile(self,args,cmdname,jsonfile,curparser=None):
        assert(jsonfile is not None)
        prefix = ''
        if cmdname is not None :
            prefix += cmdname
        flagarray = self.__flags
        if curparser :
            flagarray = curparser.flags

        fp = None
        try:
            fp = open(jsonfile,'r+')
        except:
            raise Exception('can not open(%s)'%(jsonfile))
        try:
            jsonvalue = json.load(fp)
            fp.close()
            fp = None
        except:
            if fp is not None:
                fp.close()
            fp = None
            raise Exception('can not parse (%s)'%(jsonfile))
        jsonvalue = keyparse.Utf8Encode(jsonvalue).get_val()
        return self.__load_jsonvalue(args,prefix,jsonvalue,flagarray)



    def __set_parser_default_value(self,args,flagarray):
        for keycls in flagarray:
            if keycls.isflag and keycls.type != 'prefix' and keycls.type != 'args':
                self.__set_jsonvalue_not_defined(args,flagarray,keycls.optdest,keycls.value)
        return args

    def __set_default_value(self,args):
        for parser in self.__cmdparsers:
            args = self.__set_parser_default_value(args,parser.flags)

        args = self.__set_parser_default_value(args,self.__flags)
        return args

    def __set_environ_value_inner(self,args,prefix,flagarray):
        for keycls in flagarray:
            if keycls.isflag and keycls.type != 'prefix' and keycls.type != 'args':
                optdest = keycls.optdest
                oldopt = optdest
                if getattr(args,oldopt,None) is not None:
                    # have set ,so we do not set it
                    continue
                optdest = optdest.upper()
                optdest = optdest.replace('-','_')
                if '_' not in optdest:
                    optdest = 'EXTARGS_%s'%(optdest)
                val = os.getenv(optdest,None)               
                if val is not None:
                    # to check the type
                    val = keyparse.Utf8Encode(val).get_val()
                    if keycls.type == 'string':
                        setattr(args,oldopt,val)
                    elif keycls.type == 'bool':                     
                        if val.lower() == 'true':
                            setattr(args,oldopt,True)
                        elif val.lower() == 'false':
                            setattr(args,oldopt,False)
                    elif keycls.type == 'list':
                        try:
                            lval = eval(val)
                            lval = keyparse.Utf8Encode(lval).get_val()
                            if not isinstance(lval,list):
                                raise Exception('(%s) environ(%s) not valid'%(optdest,val))
                            setattr(args,oldopt,lval)
                        except:
                            self.__logger.warn('can not set (%s) for %s = %s'%(optdest,oldopt,val))
                    elif keycls.type == 'int':
                        try:
                            lval = int(val)
                            setattr(args,oldopt,lval)
                        except:
                            self.__logger.warn('can not set (%s) for %s = %s'%(optdest,oldopt,val))
                    elif keycls.type == 'float':
                        try:
                            lval = float(val)
                            setattr(args,oldopt,lval)
                        except:
                            self.__logger.warn('can not set (%s) for %s = %s'%(optdest,oldopt,val))
                    else:
                        raise Exception('internal error when (%s) type(%s)'%(keycls.optdest,keycls.type))
        return args



    def __set_environ_value(self,args):
        for parser in self.__cmdparsers:
            args = self.__set_environ_value_inner(args,parser.cmdname,parser.flags)
        args = self.__set_environ_value_inner(args,'',self.__flags)
        return args

    def __set_command_line_self_args(self):
        for parser in self.__cmdparsers:
            curkey = keyparse.ExtKeyParse(parser.cmdname,'$','*',True)
            self.__load_command_line_args(parser.cmdname,curkey,parser)
        curkey = keyparse.ExtKeyParse('','$','*',True)
        self.__load_command_line_args('',curkey,None)
        return

    def __parse_sub_command_json_set(self,args):
        # now we should get the 
        # first to test all the json file for special command
        if self.__subparser and args.subcommand is not None:
            jsondest = '%s_json'%(args.subcommand)
            curparser = self.__find_subparser_inner(args.subcommand)
            assert(curparser is not None)
            jsonfile = getattr(args,jsondest,None)
            if jsonfile is not None:
                # ok we should make this parse
                args = self.__load_jsonfile(args,args.subcommand,jsonfile,curparser)
        return args

    def __parse_command_json_set(self,args):
        # to get the total command
        if args.json is not None:
            jsonfile = args.json
            args = self.__load_jsonfile(args,'',jsonfile,None)
        return args

    def __parse_environment_set(self,args):
        # now get the environment value
        args = self.__set_environ_value(args)
        return args

    def __parse_env_subcommand_json_set(self,args):
        # now to check for the environment as the put file
        if self.__subparser and args.subcommand is not None:
            jsondest = '%s_json'%(args.subcommand)
            curparser = self.__find_subparser_inner(args.subcommand)
            assert(curparser is not None)
            jsondest = jsondest.replace('-','_')
            jsondest = jsondest.upper()
            jsonfile = os.getenv(jsondest,None)
            if jsonfile is not None:
                # ok we should make this parse
                args = self.__load_jsonfile(args,args.subcommand,jsonfile,curparser)
        return args

    def __parse_env_command_json_set(self,args):
        # to get the json existed 
        jsonfile = os.getenv('EXTARGSPARSE_JSON',None)
        if jsonfile is not None:
            args = self.__load_jsonfile(args,'',jsonfile,None)
        return args




    def parse_command_line(self,params=None,Context=None):
        # we input the self command line args by default
        self.__set_command_line_self_args()
        if params is None:
            params = sys.argv[1:]
        args = self.parse_args(params)

        for p in self.__load_priority:
            args = self.__parse_set_map[p](args)

        # set the default value
        args = self.__set_default_value(args)

        # now test whether the function has
        if self.__subparser and args.subcommand is not None:
            parser = self.__find_subparser_inner(args.subcommand)
            assert(parser is not None)
            funcname = parser.typeclass.function
            if funcname is not None:
                return call_func_args(funcname,args,Context)
        return args

def call_args_function(args,context):
    if hasattr(args,'subcommand'):
        context.has_called_args = args.subcommand
    else:
        context.has_called_args = None
    return

class ExtArgsTestCase(unittest.TestCase):
    def setUp(self):
        if 'EXTARGSPARSE_JSON' in os.environ.keys():
            del os.environ['EXTARGSPARSE_JSON']
        delone = True
        while delone:
            delone = False
            for k in os.environ.keys():
                if k.startswith('EXTARGS_') or k.startswith('DEP_') or k == 'EXTARGSPARSE_JSON' or k.startswith('RDEP_'):
                    del os.environ[k]
                    delone = True
                    break
        return

    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_A001(self):
        loads = '''
        {
            "verbose|v##increment verbose mode##" : "+",
            "flag|f## flag set##" : false,
            "number|n" : 0,
            "list|l" : [],
            "string|s" : "string_var",
            "$" : {
                "value" : [],
                "nargs" : "*",
                "type" : "string"
            }
        }
        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(loads)
        args = parser.parse_command_line(['-vvvv','-f','-n','30','-l','bar1','-l','bar2','var1','var2'])
        self.assertEqual(args.verbose,4)
        self.assertEqual(args.flag,True)
        self.assertEqual(args.number,30)
        self.assertEqual(args.list,['bar1','bar2'])
        self.assertEqual(args.string,'string_var')
        self.assertEqual(args.args,['var1','var2'])
        return

    def test_A002(self):
        loads = '''
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
        parser = ExtArgsParse()
        parser.load_command_line_string(loads)
        args = parser.parse_command_line(['-vvvv','-p','5000','dep','-l','arg1','--dep-list','arg2','cc','dd'])
        self.assertEqual(args.verbose,4)
        self.assertEqual(args.port,5000)
        self.assertEqual(args.subcommand,'dep')
        self.assertEqual(args.dep_list,['arg1','arg2'])
        self.assertEqual(args.dep_string,'s_var')
        self.assertEqual(args.subnargs,['cc','dd'])
        return


    def test_A003(self):
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
        parser = ExtArgsParse()
        parser.load_command_line_string(loads)
        args = parser.parse_command_line(['-vvvv','-p','5000','rdep','-L','arg1','--rdep-list','arg2','cc','dd'])
        self.assertEqual(args.verbose,4)
        self.assertEqual(args.port,5000)
        self.assertEqual(args.subcommand,'rdep')
        self.assertEqual(args.rdep_list,['arg1','arg2'])
        self.assertEqual(args.rdep_string,'s_rdep')
        self.assertEqual(args.subnargs,['cc','dd'])
        return

    def test_A004(self):
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
        parser = ExtArgsParse()
        parser.load_command_line_string(loads)
        args = parser.parse_command_line(['-vvvv','-p','5000','rdep','-L','arg1','--rdep-list','arg2','cc','dd'])
        self.assertEqual(args.verbose,4)
        self.assertEqual(args.port,5000)
        self.assertEqual(args.subcommand,'rdep')
        self.assertEqual(args.rdep_list,['arg1','arg2'])
        self.assertEqual(args.rdep_string,'s_rdep')
        self.assertEqual(args.subnargs,['cc','dd'])
        return

    def test_A005(self):
        formats = '''
        {
            "verbose|v" : "+",
            "port|p" : 3000,
            "dep<%s.call_args_function>" : {
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
        loads = formats%(__name__)
        parser = ExtArgsParse()
        parser.load_command_line_string(loads)
        self.has_called_args = None
        args = parser.parse_command_line(['-p','7003','-vvvvv','dep','-l','foo1','-s','new_var','zz'],self)
        self.assertEqual(args.port,7003)
        self.assertEqual(args.verbose,5)
        self.assertEqual(args.dep_list,['foo1'])
        self.assertEqual(args.dep_string,'new_var')
        self.assertEqual(args.subnargs,['zz'])
        self.assertEqual(self.has_called_args,'dep')
        self.has_called_args = None
        return

    def test_A006(self):
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
        load2 = '''
        {
            "rdep" : {
                "list|L" : [],
                "string|S" : "s_rdep",
                "$" : 2
            }
        }
        '''

        parser = ExtArgsParse()
        parser.load_command_line_string(load1)
        parser.load_command_line_string(load2)
        args = parser.parse_command_line(['-p','7003','-vvvvv','rdep','-L','foo1','-S','new_var','zz','64'])
        self.assertEqual(args.port,7003)
        self.assertEqual(args.verbose,5)
        self.assertEqual(args.rdep_list,['foo1'])
        self.assertEqual(args.rdep_string,'new_var')
        self.assertEqual(args.subnargs,['zz','64'])
        return

    def test_A007(self):
        commandline = '''
        {
            "verbose|v" : "+",
            "port|p+http" : 3000,
            "dep" : {
                "list|l" : [],
                "string|s" : "s_var",
                "$" : "+"
            }
        }
        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        args = parser.parse_command_line(['-vvvv','dep','-l','cc','--dep-string','ee','ww'])
        self.assertEqual(args.verbose,4)
        self.assertEqual(args.http_port, 3000)
        self.assertEqual(args.subcommand,'dep')
        self.assertEqual(args.dep_list,['cc'])
        self.assertEqual(args.dep_string,'ee')
        self.assertEqual(args.subnargs,['ww'])
        return

    def test_A008(self):
        commandline = '''
        {
            "verbose|v" : "+",
            "+http" : {
                "port|p" : 3000,
                "visual_mode|V" : false
            },
            "dep" : {
                "list|l" : [],
                "string|s" : "s_var",
                "$" : "+"
            }
        }
        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        args = parser.parse_command_line(['-vvvv','--http-port','9000','--http-visual-mode','dep','-l','cc','--dep-string','ee','ww'])
        self.assertEqual(args.verbose,4)
        self.assertEqual(args.http_port, 9000)
        self.assertEqual(args.http_visual_mode,True)
        self.assertEqual(args.subcommand,'dep')
        self.assertEqual(args.dep_list,['cc'])
        self.assertEqual(args.dep_string,'ee')
        self.assertEqual(args.subnargs,['ww'])
        return

    def test_A009(self):
        commandline = '''
        {
            "verbose|v" : "+",
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
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        args = parser.parse_command_line(['-vvvv','-p','9000','dep','-l','cc','--dep-string','ee','ww'])
        self.assertEqual(args.verbose,4)
        self.assertEqual(args.port, 9000)
        self.assertEqual(args.subcommand,'dep')
        self.assertEqual(args.dep_list,['cc'])
        self.assertEqual(args.dep_string,'ee')
        self.assertEqual(args.subnargs,['ww'])
        return

    def test_A010(self):
        commandline= '''
        {
            "verbose|v" : "+",
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
        depjsonfile = None
        try:
            fd,depjsonfile = tempfile.mkstemp(suffix='.json',prefix='parse',dir=None,text=True)
            os.close(fd)
            fd = -1
            with open(depjsonfile,'w+') as f:
                f.write('{"list" : ["jsonval1","jsonval2"],"string" : "jsonstring"}\n')

            parser = ExtArgsParse()
            parser.load_command_line_string(commandline)
            args = parser.parse_command_line(['-vvvv','-p','9000','dep','--dep-json',depjsonfile,'--dep-string','ee','ww'])
            self.assertEqual(args.verbose,4)
            self.assertEqual(args.port, 9000)
            self.assertEqual(args.subcommand,'dep')
            self.assertEqual(args.dep_list,['jsonval1','jsonval2'])
            self.assertEqual(args.dep_string,'ee')
            self.assertEqual(args.subnargs,['ww'])
        finally:
            if depjsonfile is not None:
                os.remove(depjsonfile)
            depjsonfile = None
        return

    def test_A011(self):
        commandline= '''
        {
            "verbose|v" : "+",
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
        depjsonfile = None
        try:
            fd,depjsonfile = tempfile.mkstemp(suffix='.json',prefix='parse',dir=None,text=True)
            os.close(fd)
            fd = -1
            with open(depjsonfile,'w+') as f:
                f.write('{"list" : ["jsonval1","jsonval2"],"string" : "jsonstring"}\n')

            parser = ExtArgsParse()
            parser.load_command_line_string(commandline)
            os.environ['DEP_JSON'] = depjsonfile
            args = parser.parse_command_line(['-vvvv','-p','9000','dep','--dep-string','ee','ww'])
            self.assertEqual(args.verbose,4)
            self.assertEqual(args.port, 9000)
            self.assertEqual(args.subcommand,'dep')
            self.assertEqual(args.dep_list,['jsonval1','jsonval2'])
            self.assertEqual(args.dep_string,'ee')
            self.assertEqual(args.subnargs,['ww'])
        finally:
            if depjsonfile is not None:
                os.remove(depjsonfile)
            depjsonfile = None
        return

    def test_A012(self):
        commandline= '''
        {
            "verbose|v" : "+",
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
        try:
            fd,jsonfile = tempfile.mkstemp(suffix='.json',prefix='parse',dir=None,text=True)
            os.close(fd)
            fd = -1
            f = open(jsonfile,'w+')
            f.write('{"dep":{"list" : ["jsonval1","jsonval2"],"string" : "jsonstring"},"port":6000,"verbose":3}\n')
            f.close()
            f = None

            parser = ExtArgsParse()
            parser.load_command_line_string(commandline)
            
            args = parser.parse_command_line(['-p','9000','--json',jsonfile,'dep','--dep-string','ee','ww'])
            self.assertEqual(args.verbose,3)
            self.assertEqual(args.port, 9000)
            self.assertEqual(args.subcommand,'dep')
            self.assertEqual(args.dep_list,['jsonval1','jsonval2'])
            self.assertEqual(args.dep_string,'ee')
            self.assertEqual(args.subnargs,['ww'])
        finally:
            if jsonfile is not None:
                os.remove(jsonfile)
            jsonfile = None
        return

    def test_A013(self):
        commandline= '''
        {
            "verbose|v" : "+",
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
        try:
            fd,jsonfile = tempfile.mkstemp(suffix='.json',prefix='parse',dir=None,text=True)
            os.close(fd)
            fd = -1
            with open(jsonfile,'w+') as f:
                f.write('{"dep":{"list" : ["jsonval1","jsonval2"],"string" : "jsonstring"},"port":6000,"verbose":3}\n')

            os.environ['EXTARGSPARSE_JSON'] = jsonfile
            parser = ExtArgsParse()
            parser.load_command_line_string(commandline)
            
            args = parser.parse_command_line(['-p','9000','dep','--dep-string','ee','ww'])
            self.assertEqual(args.verbose,3)
            self.assertEqual(args.port, 9000)
            self.assertEqual(args.subcommand,'dep')
            self.assertEqual(args.dep_list,['jsonval1','jsonval2'])
            self.assertEqual(args.dep_string,'ee')
            self.assertEqual(args.subnargs,['ww'])
        finally:
            if jsonfile is not None:
                os.remove(jsonfile)
            jsonfile = None
            if 'EXTARGSPARSE_JSON' in os.environ.keys():
                del os.environ['EXTARGSPARSE_JSON']
        return

    def test_A014(self):
        commandline= '''
        {
            "verbose|v" : "+",
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
            fd,jsonfile = tempfile.mkstemp(suffix='.json',prefix='parse',dir=None,text=True)
            os.close(fd)
            fd = -1
            fd ,depjsonfile = tempfile.mkstemp(suffix='.json',prefix='parse',dir=None,text=True)
            os.close(fd)
            fd = -1
            with open(jsonfile,'w+') as f:
                f.write('{"dep":{"list" : ["jsonval1","jsonval2"],"string" : "jsonstring"},"port":6000,"verbose":3}\n')
            with open(depjsonfile,'w+') as f:
                f.write('{"list":["depjson1","depjson2"]}\n')

            os.environ['EXTARGSPARSE_JSON'] = jsonfile
            os.environ['DEP_JSON'] = depjsonfile
            parser = ExtArgsParse()
            parser.load_command_line_string(commandline)
            
            args = parser.parse_command_line(['-p','9000','dep','--dep-string','ee','ww'])
            self.assertEqual(args.verbose,3)
            self.assertEqual(args.port, 9000)
            self.assertEqual(args.subcommand,'dep')
            self.assertEqual(args.dep_list,['depjson1','depjson2'])
            self.assertEqual(args.dep_string,'ee')
            self.assertEqual(args.subnargs,['ww'])
        finally:
            if depjsonfile is not None:
                os.remove(depjsonfile)
            depjsonfile = None
            if jsonfile is not None:
                os.remove(jsonfile)
            jsonfile = None
        return


    def test_A015(self):
        commandline= '''
        {
            "verbose|v" : "+",
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
            fd,jsonfile = tempfile.mkstemp(suffix='.json',prefix='parse',dir=None,text=True)
            os.close(fd)
            fd = -1
            fd ,depjsonfile = tempfile.mkstemp(suffix='.json',prefix='parse',dir=None,text=True)
            os.close(fd)
            fd = -1
            with open(jsonfile,'w+') as f:
                f.write('{"dep":{"list" : ["jsonval1","jsonval2"],"string" : "jsonstring"},"port":6000,"verbose":3}\n')
            with open(depjsonfile,'w+') as f:
                f.write('{"list":["depjson1","depjson2"]}\n')

            os.environ['DEP_JSON'] = depjsonfile
            parser = ExtArgsParse()
            parser.load_command_line_string(commandline)
            
            args = parser.parse_command_line(['-p','9000','--json',jsonfile,'dep','--dep-string','ee','ww'])
            self.assertEqual(args.verbose,3)
            self.assertEqual(args.port, 9000)
            self.assertEqual(args.subcommand,'dep')
            self.assertEqual(args.dep_list,['jsonval1','jsonval2'])
            self.assertEqual(args.dep_string,'ee')
            self.assertEqual(args.subnargs,['ww'])
        finally:
            if depjsonfile is not None:
                os.remove(depjsonfile)
            depjsonfile = None
            if jsonfile is not None:
                os.remove(jsonfile)
            jsonfile = None
        return


    def test_A016(self):
        commandline= '''
        {
            "verbose|v" : "+",
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
            fd,jsonfile = tempfile.mkstemp(suffix='.json',prefix='parse',dir=None,text=True)
            os.close(fd)
            fd = -1
            fd ,depjsonfile = tempfile.mkstemp(suffix='.json',prefix='parse',dir=None,text=True)
            os.close(fd)
            fd = -1
            with open(jsonfile,'w+') as f:
                f.write('{"dep":{"list" : ["jsonval1","jsonval2"],"string" : "jsonstring"},"port":6000,"verbose":3}\n')
            with open(depjsonfile,'w+') as f:
                f.write('{"list":["depjson1","depjson2"]}\n')


            os.environ['EXTARGSPARSE_JSON'] = jsonfile
            os.environ['DEP_JSON'] = depjsonfile
            parser = ExtArgsParse()
            parser.load_command_line_string(commandline)
            os.environ['DEP_STRING'] = depstrval
            os.environ['DEP_LIST'] = depliststr
            
            args = parser.parse_command_line(['-p','9000','dep','--dep-string','ee','ww'])
            self.assertEqual(args.verbose,3)
            self.assertEqual(args.port, 9000)
            self.assertEqual(args.subcommand,'dep')
            self.assertEqual(args.dep_list,deplistval)
            self.assertEqual(args.dep_string,'ee')
            self.assertEqual(args.subnargs,['ww'])
        finally:
            if depjsonfile is not None:
                os.remove(depjsonfile)
            depjsonfile = None
            if jsonfile is not None:
                os.remove(jsonfile)
            jsonfile = None
        return

    def test_A017(self):
        commandline= '''
        {
            "+dpkg" : {
                "dpkg" : "dpkg"
            },
            "verbose|v" : "+",
            "$port|p" : {
                "value" : 3000,
                "type" : "int",
                "nargs" : 1 , 
                "helpinfo" : "port to connect"
            }
        }
        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        args = parser.parse_command_line([])
        self.assertEqual(args.verbose,0)
        self.assertEqual(args.port,3000)
        self.assertEqual(args.dpkg_dpkg,'dpkg')
        return

    def test_A018(self):
        commandline= '''
        {
            "+dpkg" : {
                "dpkg" : "dpkg"
            },
            "verbose|v" : "+",
            "rollback|r": true,
            "$port|p" : {
                "value" : 3000,
                "type" : "int",
                "nargs" : 1 , 
                "helpinfo" : "port to connect"
            }
        }
        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        args = parser.parse_command_line(['-vvrvv'])
        self.assertEqual(args.verbose,4)
        self.assertEqual(args.rollback,False)
        self.assertEqual(args.port,3000)
        self.assertEqual(args.dpkg_dpkg,'dpkg')
        return

    def test_A019(self):
        commandline= '''
        {
            "verbose|v" : "+",
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
            fd,jsonfile = tempfile.mkstemp(suffix='.json',prefix='parse',dir=None,text=True)
            os.close(fd)
            fd = -1
            fd ,depjsonfile = tempfile.mkstemp(suffix='.json',prefix='parse',dir=None,text=True)
            os.close(fd)
            fd = -1
            with open(jsonfile,'w+') as f:
                f.write('{"dep":{"list" : ["jsonval1","jsonval2"],"string" : "jsonstring"},"port":6000,"verbose":3}\n')
            with open(depjsonfile,'w+') as f:
                f.write('{"list":["depjson1","depjson2"]}\n')


            os.environ['EXTARGSPARSE_JSON'] = jsonfile
            os.environ['DEP_JSON'] = depjsonfile
            parser = ExtArgsParse(priority=[ENV_COMMAND_JSON_SET,ENVIRONMENT_SET,ENV_SUB_COMMAND_JSON_SET])
            parser.load_command_line_string(commandline)
            os.environ['DEP_STRING'] = depstrval
            os.environ['DEP_LIST'] = depliststr
            
            args = parser.parse_command_line(['-p','9000','dep','--dep-string','ee','ww'])
            self.assertEqual(args.verbose,3)
            self.assertEqual(args.port, 9000)
            self.assertEqual(args.subcommand,'dep')
            self.assertEqual(args.dep_list,['jsonval1','jsonval2'])
            self.assertEqual(args.dep_string,'ee')
            self.assertEqual(args.subnargs,['ww'])
        finally:
            if depjsonfile is not None:
                os.remove(depjsonfile)
            depjsonfile = None
            if jsonfile is not None:
                os.remove(jsonfile)
            jsonfile = None
        return

    def test_A020(self):
        commandline= '''
        {
            "verbose|v" : "+",
            "rollback|R" : true,
            "$port|P" : {
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
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        args = parser.parse_command_line(['-P','9000','--no-rollback','dep','--dep-string','ee','ww'])
        self.assertEqual(args.verbose,0)
        self.assertEqual(args.port, 9000)
        self.assertEqual(args.rollback,False)
        self.assertEqual(args.subcommand,'dep')
        self.assertEqual(args.dep_list,[])
        self.assertEqual(args.dep_string,'ee')
        self.assertEqual(args.subnargs,['ww'])
        return



def main():
    if '-v' in sys.argv[1:] or '--verbose' in sys.argv[1:]:
        os.environ['EXTARGSPARSE_LOGLEVEL'] = 'DEBUG'
    unittest.main()

if __name__ == '__main__':
    main()  

