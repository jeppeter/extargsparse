#!/usr/bin/python

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
if sys.version[0] == '2':
    import StringIO
else:
    import io as StringIO

COMMAND_SET = 10
SUB_COMMAND_JSON_SET = 20
COMMAND_JSON_SET = 30
ENVIRONMENT_SET = 40
ENV_SUB_COMMAND_JSON_SET = 50
ENV_COMMAND_JSON_SET = 60
DEFAULT_SET = 70

extargs_shell_out_mode=0

def set_attr_args(self,args,prefix):
    if not issubclass(args.__class__,argparse.Namespace):
        raise Exception('second args not valid argparse.Namespace subclass')
    for p in vars(args).keys():
        if len(prefix) == 0 or p.startswith('%s_'%(prefix)):
            setattr(self,p,getattr(args,p))
    return


#####################################
##
##  parser.opts = []
##  parser.cmdname = ''
##  parser.subcommands = []
##  parser.callfunction = None
##  parser.helpinfo  = None
##  parser.keycls = keycls
#####################################

class _HelpSize(object):
    sizewords = ['optnamesize','optexprsize','opthelpsize','cmdnamesize','cmdhelpsize']
    def __init__(self):
        self.optnamesize = 0
        self.optexprsize = 0
        self.opthelpsize = 0
        self.cmdnamesize = 0
        self.cmdhelpsize = 0
        return

    def __setattr__(self,name,value):
        if name in self.__class__.sizewords:
            if value >= getattr(self,name,0):
                self.__dict__[name] = value
            return
        self.__dict__[name] = value
        return

    def __str__(self):
        s = '{'
        i = 0
        for n in sizewords:
            if i > 0:
                s += ','
            s += '%s=%d'%(n,getattr(self,n,0))
            i += 1
        s += '}'
        return s


class _ParserCompact(object):
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

    def __init__(self,keycls=None):
        if keycls is not None:
            assert(keycls.iscmd)
            self.keycls = keycls
            self.cmdname = keycls.cmdname
            self.cmdopts = []
            self.subcommands = []
            self.helpinfo = '%s handler'%(self.cmdname)
            if keycls.helpinfo is not None:
                self.helpinfo = keycls.helpinfo
            self.callfunction = None
            if keycls.function is not None:
                self.callfunction = None
        else:
            self.keycls = None
            self.cmdname = ""
            self.cmdopts = []
            self.helpinfo = None
            self.callfunction = None
        self.epilog = None
        self.description = None
        self.prog = None
        self.usage = None
        self.version = None
        return

    def __get_opt_help(self,opt):
        lname = opt.longopt
        sname = opt.shortopt
        optname = lname 
        if sname is not None:
            optname += '|%s'%(sname)
        optexpr = ''
        if opt.type != 'bool' and opt.type != 'args' and opt.type != 'dict':
            optexpr = opt.varname
            optexpr = optexpr.replace('-','_')
        opthelp = self.__get_help_info(opt)
        return optname,optexpr,opthelp

    # return optnamesize optexprsize opthelpsize
    #  cmdnamesize cmdhelpsize
    def get_help_size(self,helpsize=None,recursive=-1):
        if helpsize is None:
            helpsize = _HelpSize()
        cmdname,cmdhelp = self.__get_cmd_help(self)
        helpsize.cmdnamesize = len(cmdname)
        helpsize.cmdhelpsize = len(cmdhelp)
        for opt in self.cmdopts:
            optname,optexpr,opthelp = self.__get_opt_help(opt)
            helpsize.optnamesize = len(optname)
            helpsize.optexprsize = len(optexpr)
            helpsize.opthelpsize = len(opthelp)

        if recursive != 0:
            for cmd in self.subcommands:
                if recursively > 0:
                    helpsize = cmd.get_help_size(helpsize,recursive-1)
                else:
                    helpsize = cmd.get_help_size(helpsize,recursive)
        return helpsize

    def __get_cmd_help(self,cmd):
        cmdname = ''
        cmdhelp = ''
        if cmd.cmdname is not None:
            cmdname = '%s'%(cmd.cmdname)
        if cmd.helpinfo is not None:
            cmdhelp = '%s'%(cmd.helpinfo)
        return cmdname,cmdhelp


    def get_help_info(self,helpsize=None,parentcmds=[]):
        if helpsize is None:
            helpsize = self.get_help_size()
        s = ''
        if self.usage is not None:
            s += '%s'%(self.usage)
        else:

            rootcmds = self
            if len(parentcmds) > 0:
                rootcmds = parentcmds[0]
            if rootcmds.prog is not None:
                s += '%s'%(rootcmds.prog)
            else:
                s += '%s'%(sys.argv[0])
            if rootcmds.version is not None:
                s += ' %s'%(rootcmds.version)
            if len(parentcmds) > 0:
                for c in parentcmds:
                        s += ' %s'%(c.cmdname)
            s += ' %s'%(self.cmdname)
            if len(self.cmdopts) > 0:
                s += ' [OPTIONS]'
            if len(self.subcommands) > 0:
                s += ' [SUBCOMMANDS]'
            for args in self.cmdopts:
                if args.flagname == '$':
                    if args.nargs == '+' or args.nargs > 1:
                        s += ' args...'
                    elif args.nargs == '*':
                        s += ' [args...]'
                    elif args.nargs = '?' or args.nargs == 1:
                        s += ' arg'
                    break
            s += '\n'
        if self.description is not None:
            s += '%s\n'%(self.description)        
        if len(self.cmdopts) > 0:
            s += '[OPTIONS]\n'
            for opt in self.cmdopts:
                optname,optexpr,opthelp = self.__get_opt_help(opt)
                s += '\t%-*s %-*s %-*s\n'%(helpsize.optnamesize,optname,
                    helpsize.optexprsize,optexpr,
                    helpsize.opthelpsize,opthelp)
        if len(self.subcommands)>0:
            s += '[SUBCOMMANDS]\n'
            for cmd in self.subcommands:
                cmdname,cmdhelp = self.__get_cmd_help(cmd)
                s += '\t%-*s %-*s\n'%(helpsize.cmdnamesize,cmdname,helpsize.cmdhelpsize,cmdhelp)
        if self.epilog is not None:
            s += '\n%s\n'%(self.epilog)
        return s

class NameSapce(object):
    pass

class ExtArgsParse(object):
    reserved_args = ['subcommand','subnargs','json','nargs','extargs']
    priority_args = [SUB_COMMAND_JSON_SET,COMMAND_JSON_SET,ENVIRONMENT_SET,ENV_SUB_COMMAND_JSON_SET,ENV_COMMAND_JSON_SET]

    def __call_func_args(self,funcname,args,Context):
        mname = '__main__'
        fname = funcname
        if len(self.__output_mode) > 0:
            if self.__output_mode[-1] == 'bash' or self.__output_mode[-1] == 'c':
                return args
        try:
            if '.' not in funcname:
                m = importlib.import_module(mname)
            else:
                sarr = re.split('\.',funcname)
                mname = '.'.join(sarr[:-1])
                fname = sarr[-1]
                m = importlib.import_module(mname)
        except ImportError as e:
            self.__logger.error('can not load %s'%(mname))
            return args

        for d in dir(m):
            if d == fname:
                val = getattr(m,d)
                if hasattr(val,'__call__'):
                    val(args,Context)
                    return args
        self.__logger.error('can not call %s'%(funcname))
        return args

    def __true_action(self,args,dest,value):
        setattr(args,dest,True)
        return args

    def __false_action(self,args,dest,value):
        setattr(args,dest,False)
        return args

    def __append_action(self,args,dest,value):
        sarr = getattr(args,dest,None)
        if sarr is None:
            sarr = []
        sarr.append(value)
        setattr(args,dest,sarr)
        return args

    def __string_action(self,args,dest,value):
        setattr(args,dest,value)
        return args

    def __jsonfile_action(self,args,dest,value):
        return self.__string_action(args,dest,value)

    def __int_action(self,args,dest,value):
        try:
            base = 10
            if value.startswith('0x') or value.startswith('0X'):
                value = value[2:]
                base = 16
            elif value.startswith('x') or value.startswith('X'):
                base = value[1:]
                base = 16
            num = int(value,base)
            setattr(args,dest,num)
        except:
            msg = '%s not valid int'%(value)
            self.error(msg)
            raise Exception(msg)
        return args

    def __float_action(self,args,dest,value):
        try:
            num = float(value)
            setattr(args,dest,num)
        except:
            msg = 'can not parse %s'%(value)
            self.error(msg)
            raise Exception(msg)
        return args


    def error(self,message):
        output = False
        if len(self.__output_mode) > 0:
            if self.__output_mode[-1] == 'bash':
                s = ''
                s += 'cat >&2 <<EXTARGSEOF\n'
                s += 'parse command error\n    %s\n'%(message)
                s += 'EXTARGSEOF\n'
                s += 'exit 3\n'
                sys.stdout.write('%s'%(s))
                output = True
                sys.exit(3)
        if not output :
            s = 'parse command error\n'
            s += '    %s'%(message)
            sys.stderr.write('%s'%(s))
        return

    def __check_flag_insert(self,keycls,curparser=None):
        if curparser :
            for k in curparser[-1].cmdopts:
                if k.flagname != '$' and keycls.flagname != '$':                    
                    if k.optdest == keycls.optdest:
                        return False
                elif k.flagname == '$' and keycls.flagname == '$':
                    return False
            # to check for all cmdopts
            for cmd in curparser:
                for k in cmd.cmdopts:
                    if k.flagname != '$' and keycls.flagname != '$':
                        if k.optdest == keycls.optdest:
                            return False
            curparser[-1].cmdopts.append(keycls)
        else:
            for k in self.__maincmd.cmdopts:
                if k.flagname != '$' and keycls.flagname != '$':
                    if k.optdest == keycls.optdest:
                        return False
                elif k.flagname == '$' and keycls.flagname == '$':
                    return False
            self.__maincmd.cmdopts.append(keycls)
        return True

    def __check_flag_insert_mustsucc(self,keycls,curparser=None):
        valid = self.__check_flag_insert(keycls,curparser)
        if not valid:
            cmdname = ''
            if curparser:
                i = 0
                for c in curparser:
                    if i > 0:
                        cmdname += '.'
                    cmdname += c.cmdname
                    i += 1
            raise Exception('(%s) already in command(%s)'%(keycls.flagname,cmdname))
        return

    def __load_command_line_string(self,prefix,keycls,curparser=None):
        self.__check_flag_insert_mustsucc(keycls,curparser)
        if curparser :
            curparser[-1].cmdopts.append(keycls)
        else:
            self.__maincmd.cmdopts.append(keycls)
        return True

    def __load_command_line_count(self,prefix,keycls,curparser=None):
        self.__check_flag_insert_mustsucc(keycls,curparser)
        if curparser :
            curparser[-1].cmdopts.append(keycls)
        else:
            self.__maincmd.cmdopts.append(keycls)
        return True


    def __load_command_line_int(self,prefix,keycls,curparser=None):
        self.__check_flag_insert_mustsucc(keycls,curparser)
        if curparser :
            curparser[-1].cmdopts.append(keycls)
        else:
            self.__maincmd.cmdopts.append(keycls)
        return True


    def __load_command_line_float(self,prefix,keycls,curparser=None):
        self.__check_flag_insert_mustsucc(keycls,curparser)
        if curparser :
            curparser[-1].cmdopts.append(keycls)
        else:
            self.__maincmd.cmdopts.append(keycls)
        return True

    def __load_command_line_list(self,prefix,keycls,curparser=None):
        self.__check_flag_insert_mustsucc(keycls,curparser)
        if curparser :
            curparser[-1].cmdopts.append(keycls)
        else:
            self.__maincmd.cmdopts.append(keycls)
        return True

    def __load_command_line_bool(self,prefix,keycls,curparser=None):
        self.__check_flag_insert_mustsucc(keycls,curparser)
        if curparser :
            curparser[-1].cmdopts.append(keycls)
        else:
            self.__maincmd.cmdopts.append(keycls)
        return True

    def __load_command_line_args(self,prefix,keycls,curparser=None):
        valid = self.__check_flag_insert(keycls,curparser)
        if not valid :
            return False
        if curparser :
            curparser[-1].cmdopts.append(keycls)
        else:
            self.__maincmd.cmdopts.append(keycls)
        return True

    def __load_command_line_jsonfile(self,keycls,curparser=None):
        valid = self.__check_flag_insert(keycls,curparser)
        if not valid:
            return False
        if curparser :
            curparser[-1].cmdopts.append(keycls)
        else:
            self.__maincmd.cmdopts.append(keycls)
        return True

    def __load_command_line_json_added(self,curparser=None):
        prefix = ''
        key = 'json##json input file to get the value set##'
        value = None
        if curparser :
            # now we should find from the 
            prefix = curparser.cmdname
        keycls = keyparse.ExtKeyParse(prefix,key,value,True)
        return self.__load_command_line_jsonfile(keycls,curparser)


    def __init__(self,prog=None,usage=None,description=None,epilog=None,version=None,priority=[SUB_COMMAND_JSON_SET,COMMAND_JSON_SET,ENVIRONMENT_SET,ENV_SUB_COMMAND_JSON_SET,ENV_COMMAND_JSON_SET]):
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
        self.__maincmd = _ParserCompact(None)
        self.__maincmd.prog = prog
        self.__maincmd.usage = usage
        self.__maincmd.description = description
        self.__maincmd.epilog = epilog
        self.__maincmd.version = version
        self.__output_mode = []
        self.__load_command_map = {
            'string' : self.__load_command_line_string,
            'unicode' : self.__load_command_line_string,
            'int' : self.__load_command_line_int,
            'long' : self.__load_command_line_int,
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

    def __format_cmdname_path(self,curparser=None):
        cmdname = ''
        if curparser is not None:
            i = 0
            for c in curparser:
                if i > 0:
                    cmdname += '.'
                cmdname += c.cmdname
        return cmdname

    def __find_commands_in_path(self,cmdname,curparser=None):
        sarr = re.split('\.',cmdname)
        commands = []
        i = 0
        if self.__maincmd is not None:
            commands.append(slef.__maincmd)
        while i <= len(sarr) and len(cmdname) > 0:
            if i == 0:
                pass
            else:
                curcommand = self.__find_command_inner(sarr[i-1],commands)
                if curcommand is None:
                    break
                commands.append(curcommand)
            i += 1
        return commands


    def __find_command_inner(self,name,curparser=None):
        sarr = re.split('\.',name)
        curroot = self.__maincmd
        nextparsers = []
        if curparser is not None:
            nextparsers = curparser
            curroot = curparser[-1]
        if len(sarr) > 1:
            nextparsers.append(curroot)
            for c in curroot.subcommands:
                if c.cmdname == sarr[0]:
                    nextparsers = []
                    if curparser is not None:
                        nextparsers = curparser
                    nextparsers.append(c)
                    return self.__find_command_inner('.'.join(sarr[1:]),nextparsers)
        else:
            for c in curroot.subcommands:
                if c.cmdname == sarr[0]:
                    return c
        return None


    def __get_subparser_inner(self,keycls,curparser=None):
        cmdname = ''
        parentname = self.__format_cmdname_path(curparser)
        cmdname += parentname
        if len(cmdname) > 0:
            cmdname += '.'
        cmdname += keycls.cmdname
        cmdparser = self.__find_subparser_inner(cmdname)
        if cmdparser is not None:
            return cmdparser        
        cmdparser = _ParserCompact(keycls)

        if len(parentname) == 0:
            self.__maincmd.subcommands.append(cmdparser)
        else:
            curparser[-1].subcommands.append(cmdparser)
        return cmdparser


    def __load_command_subparser(self,prefix,keycls,lastparser=None):
        if lastparser :
            raise Exception('(%s) can not make command recursively'%(keycls.origkey))
        if not isinstance( keycls.value,dict):
            raise Exception('(%s) value must be dict'%(keycls.origkey))
        parser = self.__get_subparser_inner(keycls,lastparser)
        nextparser = []
        if lastparser is not None:
            nextparser = lastparser
        nextparser.append(parser)
        self.__load_command_line_inner(keycls.prefix,keycls.value,nextparser)
        return True

    def __load_command_prefix(self,prefix,keycls,curparser=None):
        self.__load_command_line_inner(keycls.prefix,keycls.value,curparser)
        return True

    def __load_command_line_inner(self,prefix,d,curparser=None):
        self.__load_command_line_json_added(curparser)
        for k in d.keys():
            v = d[k]
            self.__logger.info('%s , %s , %s , True'%(prefix,k,v))
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

    def __check_help_options(self,params):
        showhelp = False
        for s in params:
            if s == '--':
                break
            elif s.startswith('--'):
                if s == '--help':
                    showhelp = True
                    break
            elif s.startswith('-'):
                if 'h' in s:
                    showhelp = True
                    break
        if not showhelp:
            return None
        return self.__print_out_help()



    def parse_command_line(self,params=None,Context=None,mode=None):
        # we input the self command line args by default
        pushmode = False
        if mode is not None:
            pushmode = True
            self.__output_mode.append(mode)
        try:
            self.__set_command_line_self_args()
            if params is None:
                params = sys.argv[1:]

            s = self.__check_help_options(params)
            if s is not None:
                return s
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
                    return self.__call_func_args(funcname,args,Context)
        finally:
            if pushmode:
                self.__output_mode.pop()
                pushmode = False
        return args

    def __print_out_help(self):
        s = ''
        sio = StringIO.StringIO()
        self.print_help(sio)
        output = False
        if len(self.__output_mode) > 0:
            if self.__output_mode[-1] == 'bash':
                s +=  'cat << EXTARGSEOF\n'
                s +=  '%s\n'%(sio.getvalue())
                s += 'EXTARGSEOF\n'
                s += 'exit 0\n'
                output = True
        if not output :
            s += sio.getvalue()
            sys.stdout.write(s)
            sys.exit(0)
        return s

    def get_command_options(self,cmdname=None):
        if cmdname is None or len(cmdname) == 0:
            # this is the command of main ,so just return the keycls for main
            return self.__flags
        sarr = re.split('\.',cmdname)
        retval = []
        if len(sarr) == 1:
            cmdparser = self.__find_subparser_inner(sarr[0])
            if cmdparser is not None:
                retval = cmdparser.flags
        return retval


    def __shell_eval_out_flagarray(self,args,flagarray,ismain=True,curparser=None):
        s = ''
        for flag in flagarray:
            if flag.isflag and flag.flagname is not None:
                if flag.type == 'args' or flag.type == 'list':
                    if flag.flagname == '$' :
                        if curparser is None and self.__subparser is not None:
                            continue
                        elif curparser is not None and curparser.typeclass.cmdname != args.subcommand:
                            # we do not output args
                            if flag.varname != 'subnargs':
                                # to not declare this one
                                s += 'unset %s\n'%(flag.varname)
                                s += 'declare -A -g %s\n'%(flag.varname)
                            continue
                    # make the global variable access
                    s += 'unset %s\n'%(flag.varname)
                    s += 'declare -A -g %s\n'%(flag.varname)
                    if flag.flagname == '$':
                        if  not ismain:
                            value = getattr(args,'subnargs',None)
                        else:
                            value = getattr(args,'args',None)
                    else:
                        value = getattr(args,flag.optdest,None)
                    if value is not None:
                        i = 0
                        for v in value:
                            if isinstance(v,str):
                                s += '%s[%d]=\'%s\'\n'%(flag.varname,i,v)
                            else:
                                s += '%s[%d]=%s\n'%(flag.varname,i,v)
                            i += 1
                else:
                    if ismain and flag.optdest == 'json' :
                        continue
                    elif curparser is not None:
                        finddest = '%s_json'%(curparser.typeclass.cmdname)
                        if flag.optdest == finddest:
                            continue
                    value = getattr(args,flag.optdest)
                    if flag.type == 'bool':
                        if value :
                            s += '%s=1\n'%(flag.varname)
                        else:
                            s += '%s=0\n'%(flag.varname)
                    else:
                        if flag.type == 'string' :
                            s += '%s=\'%s\'\n'%(flag.varname,value)
                        else:
                            s += '%s=%s\n'%(flag.varname,value)
        return s

    def shell_eval_out(self,params=None,Context=None):
        args = self.parse_command_line(params,Context,'bash')
        if isinstance(args,str):
            # that is help information
            return args
        # now we should found out the params
        # now to check for the type
        # now to give the value
        s = ''
        s += self.__shell_eval_out_flagarray(args,self.__flags)
        if self.__subparser is not None:            
            curparser = self.__find_subparser_inner(args.subcommand)
            assert(curparser is not None)
            keycls = curparser.typeclass
            if keycls.function is not None:
                s += '%s=%s\n'%(keycls.function,args.subcommand)
            else:
                s += 'subcommand=%s\n'%(args.subcommand)
            for curparser in self.__cmdparsers:
                s += self.__shell_eval_out_flagarray(args,curparser.flags,False,curparser)
        self.__logger.info('shell_out\n%s'%(s))
        return s




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

    def test_A021(self):
        commandline= '''
        {
            "maxval|m" : 392244922
        }
        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        args = parser.parse_command_line(['-m','0xffcc'])
        self.assertEqual(args.maxval,0xffcc)
        return

    def __has_line(self,sarr,s):
        ok = False
        for nl in sarr:
            l = nl.rstrip('\r\n')
            if s == l:
                ok = True
                break
        return ok

    def __line_prefix(self,sarr,s):
        ok = False
        for nl in sarr:
            l = nl.rstrip('\r\n')
            if l.startswith(s):
                ok = True
                break
        return ok


    def __check_value_common(self,s,key,value):
        sarr = re.split('\n',s)
        ok = self.__has_line(sarr,'%s=%s'%(key,value))
        self.assertEqual(ok,True)
        return
    

    def __check_value_list(self,s,key,value):
        sarr = re.split('\n',s)
        ok = self.__has_line(sarr,'declare -A -g %s'%(key))
        self.assertEqual(ok,True)
        ok = self.__has_line(sarr,'unset %s'%(key))
        if len(value) == 0:
            # now we should get the 
            ok = self.__line_prefix(sarr,'%s[%d]='%(key,0))
            self.assertEqual(ok,False)
        else:
            i = 0
            for v in value:
                ok = self.__has_line(sarr,'%s[%d]=\'%s\''%(key,i,v))
                self.assertEqual(ok,True)
                i += 1
            ok = self.__line_prefix(sarr,'%s[%d]='%(key,i))
            self.assertEqual(ok,False)
        return

    def __check_not_list(self,s,key):
        sarr = re.split('\n',s)
        ok = self.__has_line(sarr,'delcare -A %s'%(key))
        self.assertEqual(ok,False)
        return

    def __check_not_common(self,s,key):
        sarr = re.split('\n',s)
        ok = self.__line_prefix(sarr,'%s='%(key))
        self.assertEqual(ok,False)
        return

    def test_A022(self):
        commandline= '''
        {
            "verbose|v" : "+",
            "port|p" : 3000
        }
        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        s = parser.shell_eval_out(['-vvvv','-p','5000'])
        self.__check_value_common(s,'port',5000)
        self.__check_value_common(s,'verbose',4)
        self.__check_value_list(s,'args',[])
        self.__check_not_list(s,'subnargs')
        self.__check_not_common(s,'subcommand')
        self.__check_not_common(s,'json')
        return

    def test_A023(self):
        commandline='''
        {
            "$verbose|v<verbosemode>" : "+",
            "port|p<portnum>" : 7000
        }
        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        s = parser.shell_eval_out(['-vvvv','-p','5000'])
        self.__check_value_common(s,'portnum',5000)
        self.__check_value_common(s,'verbosemode',4)
        self.__check_value_list(s,'args',[])
        self.__check_not_common(s,'json')
        return

    def test_A024(self):
        commandline='''
        {
            "$verbose|v<verbosemode>" : "+",
            "port|p<portnum>" : 7000,
            "dep" : {
                "http" : true,
                "age"  : 50,
                "$" : "+"
            }
        }
        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        s = parser.shell_eval_out(['-vvvv','-p','5000','dep','cc','dd'])
        self.__check_value_common(s,'portnum',5000)
        self.__check_value_common(s,'verbosemode',4)
        self.__check_value_common(s,'dep_http',1)
        self.__check_value_common(s,'dep_age',50)
        self.__check_value_list(s,'subnargs',['cc','dd'])
        self.__check_not_common(s,'json')
        self.__check_not_common(s,'dep_json')
        return

    def test_A025(self):
        commandline='''
        {
            "$verbose|v<verbosemode>" : "+",
            "port|p<portnum>" : 7000,
            "dep<CHOICECOMMAND>" : {
                "http" : true,
                "age"  : 50,
                "$<depargs>" : "+"
            }
        }
        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        s = parser.shell_eval_out(['-vvvv','-p','5000','dep','cc','dd'])
        self.__check_value_common(s,'portnum',5000)
        self.__check_value_common(s,'verbosemode',4)
        self.__check_value_common(s,'dep_http',1)
        self.__check_value_common(s,'dep_age',50)
        self.__check_value_list(s,'depargs',['cc','dd'])
        self.__check_not_common(s,'json')
        self.__check_not_common(s,'dep_json')
        return

    def test_A026(self):
        commandline='''
        {
            "$verbose|v<verbosemode>" : "+",
            "port|p<portnum>" : 7000,
            "dep<CHOICECOMMAND>" : {
                "http" : true,
                "age"  : 50,
                "$<depargs>" : "+"
            },
            "rdep<CHOICECOMMAND>" : {
                "http" : true,
                "age" : 48,
                "$<rdepargs>" : "+"
            }
        }
        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        s = parser.shell_eval_out(['-vvvv','-p','5000','dep','cc','dd'])
        self.__check_value_common(s,'portnum',5000)
        self.__check_value_common(s,'verbosemode',4)
        self.__check_value_common(s,'dep_http',1)
        self.__check_value_common(s,'dep_age',50)
        self.__check_value_list(s,'depargs',['cc','dd'])
        self.__check_value_list(s,'rdepargs',[])
        self.__check_value_common(s,'rdep_http',1)
        self.__check_value_common(s,'rdep_age',48)
        self.__check_not_common(s,'json')
        self.__check_not_common(s,'dep_json')
        self.__check_not_common(s,'rdep_json')
        return


    def test_A027(self):
        commandline='''
        {
            "$verbose|v<verbosemode>" : "+",
            "port|p<portnum>" : 7000,
            "dep<CHOICECOMMAND>" : {
                "http" : true,
                "age"  : 50,
                "$<depargs>" : "+"
            },
            "rdep<CHOICECOMMAND>" : {
                "http" : true,
                "age" : 48,
                "$<rdepargs>" : "+"
            }
        }
        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        s = parser.shell_eval_out(['-vvvv','-p','5000','dep','cc ee','dd'])
        self.__check_value_common(s,'portnum',5000)
        self.__check_value_common(s,'verbosemode',4)
        self.__check_value_common(s,'dep_http',1)
        self.__check_value_common(s,'dep_age',50)
        self.__check_value_list(s,'depargs',['cc ee','dd'])
        self.__check_value_list(s,'rdepargs',[])
        self.__check_value_common(s,'rdep_http',1)
        self.__check_value_common(s,'rdep_age',48)
        self.__check_not_common(s,'json')
        self.__check_not_common(s,'dep_json')
        self.__check_not_common(s,'rdep_json')
        return


def main():
    if '-v' in sys.argv[1:] or '--verbose' in sys.argv[1:]:
        os.environ['EXTARGSPARSE_LOGLEVEL'] = 'DEBUG'
    unittest.main()

if __name__ == '__main__':
    main()  

