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


class _LoggerObject(object):
    def __init__(self):
        self.__logger = logging.getLogger(self.__class__.__name__)
        if len(self.__logger.handlers) == 0:
            loglvl = logging.WARN
            if 'EXTARGSPARSE_LOGLEVEL' in os.environ.keys():
                v = os.environ['EXTARGSPARSE_LOGLEVEL']
                vint = 0
                try:
                    vint = int(v)
                except:
                    vint = 0
                if vint >= 4:
                    loglvl = logging.DEBUG
                elif vint >= 3:
                    loglvl = logging.INFO
            handler = logging.StreamHandler()
            fmt = "%(levelname)-8s %(message)s"
            if 'EXTARGSPARSE_LOGFMT' in os.environ.keys():
                v = os.environ['EXTARGSPARSE_LOGFMT']
                if v is not None and len(v) > 0:
                    fmt = v
            formatter = logging.Formatter(fmt)
            handler.setFormatter(formatter)
            self.__logger.addHandler(handler)
            self.__logger.setLevel(loglvl)

    def format_string(self,arr):
        s = ''
        if isinstance(arr,list):
            i = 0
            for c in arr:
                s += '[%d]%s\n'%(i,c)
                i += 1
        elif isinstance(arr,dict):
            for c in arr.keys():
                s += '%s=%s\n'%(c,arr[c])
        else:
            s += '%s'%(arr)
        return s

    def __format_call_msg(self,msg,callstack):
        inmsg = ''  
        if callstack is not None:
            try:
                frame = sys._getframe(callstack)
                inmsg += '[%-10s:%-20s:%-5s] '%(frame.f_code.co_filename,frame.f_code.co_name,frame.f_lineno)
            except:
                inmsg = ''
        inmsg += msg
        return inmsg

    def info(self,msg,callstack=1):
        inmsg = msg
        if callstack is not None:
            inmsg = self.__format_call_msg(msg,(callstack + 1))
        return self.__logger.info('%s'%(inmsg))

    def error(self,msg,callstack=1):
        inmsg = msg
        if callstack is not None:
            inmsg = self.__format_call_msg(msg,(callstack + 1))
        return self.__logger.error('%s'%(inmsg))

    def warn(self,msg,callstack=1):
        inmsg = msg
        if callstack is not None:
            inmsg = self.__format_call_msg(msg,(callstack + 1))
        return self.__logger.warn('%s'%(inmsg))

    def debug(self,msg,callstack=1):
        inmsg = msg
        if callstack is not None:
            inmsg = self.__format_call_msg(msg,(callstack + 1))
        return self.__logger.debug('%s'%(inmsg))

    def fatal(self,msg,callstack=1):
        inmsg = msg
        if callstack is not None:
            inmsg = self.__format_call_msg(msg,(callstack + 1))
        return self.__logger.fatal('%s'%(inmsg))

#####################################
##
##  parser.opts = []
##  parser.cmdname = ''
##  parser.subcommands = []
##  parser.callfunction = None
##  parser.helpinfo  = None
##  parser.keycls = keycls
#####################################



class _HelpSize(_LoggerObject):
    sizewords = ['optnamesize','optexprsize','opthelpsize','cmdnamesize','cmdhelpsize']
    def __init__(self):
        super(_HelpSize,self).__init__()
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


class _ParserCompact(_LoggerObject):
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
        elif keycls.type == 'help' :
            helpinfo += 'to display this help information'
        else:
            if keycls.isflag :
                helpinfo += '%s set default(%s)'%(keycls.optdest,keycls.value)
            else:
                helpinfo += '%s command exec'%(keycls.cmdname)
        if keycls.helpinfo:
            helpinfo = keycls.helpinfo
        return helpinfo

    def __init__(self,keycls=None):
        super(_ParserCompact,self).__init__()
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
            self.cmdopts = []
            self.subcommands = []
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
    def get_help_size(self,helpsize=None,recursive=0):
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
                    elif args.nargs == '?' or args.nargs == 1:
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

    def __str__(self):
        s = '@%s|'%(self.cmdname)
        if len(self.subcommands) > 0:
            s += 'subcommands[%d]<'%(len(self.subcommands))
            i = 0
            for c in self.subcommands:
                if i > 0:
                    s += '|'
                s += '%s'%(c.cmdname)
                i += 1
            s += '>'

        if len(self.cmdopts) > 0:
            s += 'cmdopts[%d]<'%(len(self.cmdopts))
            i = 0
            for opt in self.cmdopts:
                s += '%s'%(opt)
            s += '>'
        return s

class _ParseState(_LoggerObject):
    def __init__(self,args,maincmd):
        super(_ParseState,self).__init__()
        self.__cmdpaths=[maincmd]
        self.__curidx=0
        self.__curcharidx=-1
        self.__shortcharargs = -1
        self.__keyidx = -1
        self.__validx = -1
        self.__args = args
        self.__ended = 0
        return

    def format_cmdname_path(self,curparser=None):
        cmdname = ''
        if curparser is  None:
            curparser = self.__cmdpaths
        for c in curparser:
            if len(cmdname) > 0:
                cmdname += '.'
            cmdname += c.cmdname
        return cmdname

    def __find_sub_command(self,name):
        cmdparent = self.__cmdpaths[-1]
        for cmd in cmdparent.subcommands:
            if cmd.cmdname == name:
                # we find the next command
                self.__cmdpaths.append(cmd)
                return cmd.keycls
        return None


    def __find_key_cls(self):
        oldcharidx = self.__curcharidx
        oldidx = self.__curidx
        if oldidx >= len(self.__args):
            self.__curidx = oldidx
            self.__curcharidx = -1
            self.__shortcharargs = -1
            self.__keyidx = -1
            self.__ended = 1
            self.__validx = -1
            return None
        if oldcharidx >= 0:
            c = self.__args[oldidx]
            if len(c) <= oldcharidx:
                # this is the end of shortopt like -vhc pass c option
                oldidx += 1
                if self.__shortcharargs > 0:
                    oldidx += 1
                self.__curidx= oldidx
                self.__curcharidx = -1
                self.__shortcharargs = -1
                self.__keyidx = -1
                self.__validx = -1
                return self.__find_key_cls()
            # ok we should get the value
            curch = c[oldcharidx]
            self.info('argv[%d][%d] %c'%(oldidx,oldcharidx,curch))
            # we look for the end of the pass
            idx = len(self.__cmdpaths) - 1
            while idx >= 0:
                cmd = self.__cmdpaths[idx]
                #self.info('[%d]%s'%(idx,cmd))
                for opt in cmd.cmdopts:
                    if not opt.isflag:
                        continue
                    if opt.flagname == '$':
                        continue
                    if opt.shortflag is not None:
                        self.info('opt %s %c %c'%(opt,opt.shortflag,curch))
                        if opt.shortflag == curch:
                            self.__keyidx = oldidx
                            self.__validx = -1
                            if opt.needarg:
                                if self.__shortcharargs >= 0 :
                                    raise Exception('can not accept twice need args in (%s)'%(self.__args[oldidx]))
                                elif len(self.__args) <= (oldidx+1):
                                    raise Exception('can not find no more args for (%s)'%(self.__args[oldidx]))
                                self.__shortcharargs = oldcharidx
                                self.__validx = oldidx+1
                            self.__curidx = oldidx
                            self.__curcharidx = (oldcharidx + 1)
                            self.info('get %s %d'%(opt,self.__validx))
                            return opt
                idx -= 1
            # now it is nothig to find so we assume that this is the command name
            raise Exception('can not parse (%s)'%(self.__args[oldidx]))
        else:
            curarg = self.__args[oldidx]
            if curarg.startswith('--'):
                if curarg == '--':
                    self.__keyidx = -1
                    self.__validx = -1
                    self.__curidx = oldidx + 1
                    self.__curcharidx = -1
                    self.__shortcharargs = -1
                    return None
                #self.info('argv[%d] %s oldcharidx %d'%(oldidx,self.__args[oldidx],oldcharidx))
                idx = len(self.__cmdpaths) -1
                while idx >= 0:
                    cmd = self.__cmdpaths[idx]
                    for opt in cmd.cmdopts:
                        if not opt.isflag:
                            continue
                        if opt.flagname == '$':
                            continue
                        self.info('[%d]longopt %s curarg %s'%(idx,opt.longopt,curarg))
                        if opt.longopt == curarg:
                            self.__keyidx = oldidx
                            oldidx += 1
                            self.__validx = -1
                            self.__shortcharargs = -1
                            if opt.needarg:
                                if len(self.__args) <= (oldidx):
                                    raise Exception('no more for (%s)'%(curarg))
                                self.__validx = oldidx
                                oldidx += 1
                            self.__curidx = oldidx
                            self.__curcharidx = -1
                            return opt
                    idx -= 1
                raise Exception('can not parse (%s)'%(self.__args[oldidx]))
            elif curarg.startswith('-'):
                if curarg == '-':
                    self.__keyidx = -1
                    self.__validx = -1
                    self.__curidx = oldidx
                    self.__curcharidx = -1
                    self.__shortcharargs = -1
                    return None
                # not to 
                oldcharidx = 1
                self.__curidx = oldidx
                self.__curcharidx = oldcharidx
                # to find the next one
                return self.__find_key_cls()
        # come here because we may be the command
        keycls = self.__find_sub_command(self.__args[oldidx])
        if keycls is not None:
            # ok we should set next search
            self.info('find %s'%(self.__args[oldidx]))
            self.__keyidx = oldidx
            self.__curidx = (oldidx + 1)
            self.__curcharidx = -1
            self.__shortcharargs = -1
            self.__validx = -1
            return keycls
        self.__keyidx = -1
        self.__curidx = oldidx
        self.__curcharidx = -1
        self.__shortcharargs = -1
        self.__validx = -1
        return None


    def step_one(self):
        key = None
        value = None
        keycls = None
        if self.__ended > 0 or len(self.__args) <= self.__curidx:
            if len(self.__args) > (self.__curidx-1):
                value = self.__args[(self.__curidx-1):]
            return None,value,None
        keycls = self.__find_key_cls()
        if keycls is None:
            if len(self.__args) > (self.__curidx):
                value = self.__args[(self.__curidx):]
            return None,value,None
        key = self.__args[self.__keyidx]
        if not keycls.iscmd and self.__validx >= 0 and self.__validx < len(self.__args):
            value = self.__args[self.__validx]
        elif keycls.iscmd:
            value = self.format_cmdname_path(self.__cmdpaths)
        return key,value,keycls

    def get_cmd_paths(self):
        return self.__cmdpaths


class NameSpace(object):
    def __init__(self):
        self.__obj = dict()
        return

    def __setattr__(self,key,val):
        if not key.startswith('_'):
            self.__obj[key] = val
            return
        self.__dict__[key] = val
        return

    def __getattr__(self,key):
        if not key.startswith('_'):
            if key in self.__obj.keys():
                return self.__obj[key]
            return None
        return self.__dict__[key]

    def __str__(self):
        s = '{'
        for k in self.__obj.keys():
            s += '%s=%s;'%(k,self.__obj[k])
        s += '}'
        return s


class ExtArgsParse(_LoggerObject):
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
            self.error('can not load %s'%(mname))
            return args

        for d in dir(m):
            if d == fname:
                val = getattr(m,d)
                if hasattr(val,'__call__'):
                    val(args,Context)
                    return args
        self.error('can not call %s'%(funcname))
        return args


    def __format_cmd_from_cmd_array(self,cmdarray):
        if cmdarray is None:
            return ''
        cmdname = ''
        for c in cmdarray:
            if len(cmdname) > 0:
                cmdname += '.'
            cmdname += '%s'%(c.cmdname)
        return cmdname

    def __bool_action(self,args,keycls,value):
        if keycls.value :
            setattr(args,keycls.optdest,False)
        else:
            setattr(args,keycls.optdest,True)
        return args

    def __append_action(self,args,keycls,value):
        sarr = getattr(args,keycls.optdest,None)
        if sarr is None:
            sarr = []
        sarr.append(value)
        setattr(args,keycls.optdest,sarr)
        return args

    def __string_action(self,args,keycls,value):
        setattr(args,keycls.optdest,value)
        return args

    def __jsonfile_action(self,args,keycls,value):
        return self.__string_action(args,keycls,value)

    def __int_action(self,args,keycls,value):
        try:
            base = 10
            if value.startswith('0x') or value.startswith('0X'):
                value = value[2:]
                base = 16
            elif value.startswith('x') or value.startswith('X'):
                base = value[1:]
                base = 16
            num = int(value,base)
            setattr(args,keycls.optdest,num)
        except:
            msg = '%s not valid int'%(value)
            self.error_msg(msg)            
        return args

    def __inc_action(self,args,keycls,value):
        val = getattr(args,keycls.optdest,None)
        if val is None:
            val = 0
        val += 1
        setattr(args,keycls.optdest,val)
        return args

    def __float_action(self,args,keycls,value):
        try:
            num = float(value)
            setattr(args,keycls.optdest,num)
        except:
            msg = 'can not parse %s'%(value)
            self.error_msg(msg)
        return args

    def __help_action(self,args,keycls,value):
        self.print_help(value)
        return args

    def __command_action(self,args,keycls,value):
        return args

    def error_msg(self,message):
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

        if self.__error_handler== 'exit':
            sys.exit(3)
        else:
            raise Exception(s)
        return

    def __check_flag_insert(self,keycls,curparser=None):
        if curparser :
            for k in curparser[-1].cmdopts:
                if k.flagname != '$' and keycls.flagname != '$':
                    if k.type != 'help' and keycls.type != 'help':
                        if k.optdest == keycls.optdest:
                            return False
                    elif k.type == 'help' and keycls.type == 'help':
                        return False
                elif k.flagname == '$' and keycls.flagname == '$':
                    return False
            #self.info('append [%s] %s'%(self.__format_cmd_from_cmd_array(curparser),keycls))
            curparser[-1].cmdopts.append(keycls)
        else:
            for k in self.__maincmd.cmdopts:
                if k.flagname != '$' and keycls.flagname != '$':
                    if k.optdest == keycls.optdest:
                        return False
                    elif k.type == 'help' and keycls.type == 'help':
                        return False
                elif k.flagname == '$' and keycls.flagname == '$':
                    return False
            #self.info('append [%s] %s'%(self.__format_cmd_from_cmd_array(curparser),keycls))
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
            msg = '(%s) already in command(%s)'%(keycls.flagname,cmdname)
            self.error_msg(msg)
        return

    def __load_command_line_base(self,prefix,keycls,curparser=None):
        self.__check_flag_insert_mustsucc(keycls,curparser)
        return True

    def __load_command_line_args(self,prefix,keycls,curparser=None):
        valid = self.__check_flag_insert(keycls,curparser)
        if not valid :
            return False
        return True

    def __load_command_line_help(self,keycls,curparser=None):
        valid = self.__check_flag_insert(keycls,curparser)
        if not valid:
            return False
        return True

    def __load_command_line_jsonfile(self,keycls,curparser=None):
        valid = self.__check_flag_insert(keycls,curparser)
        if not valid:
            return False
        return True

    def __load_command_line_json_added(self,curparser=None):
        prefix = ''
        key = 'json##json input file to get the value set##'
        value = None
        prefix = self.__format_cmd_from_cmd_array(curparser)
        prefix = prefix.replace('.','_')
        keycls = keyparse.ExtKeyParse(prefix,key,value,True)
        return self.__load_command_line_jsonfile(keycls,curparser)

    def __load_command_line_help_added(self,curparser=None):
        key = 'help|h##to display this help information##'
        value = None
        keycls = keyparse.ExtKeyParse('',key,value,True,True)
        #self.info('[%s] add help'%(self.__format_cmd_from_cmd_array(curparser)))
        return self.__load_command_line_help(keycls,curparser)


    def __init__(self,prog=None,usage=None,description=None,epilog=None,version=None,errorhandler='exit',priority=[SUB_COMMAND_JSON_SET,COMMAND_JSON_SET,ENVIRONMENT_SET,ENV_SUB_COMMAND_JSON_SET,ENV_COMMAND_JSON_SET]):
        super(ExtArgsParse,self).__init__()
        self.__maincmd = _ParserCompact(None)
        self.__maincmd.prog = prog
        self.__maincmd.usage = usage
        self.__maincmd.description = description
        self.__maincmd.epilog = epilog
        self.__maincmd.version = version
        self.__error_handler = errorhandler
        self.__output_mode = []
        self.__ended = 0
        self.__load_command_map = {
            'string' : self.__load_command_line_base,
            'unicode' : self.__load_command_line_base,
            'int' : self.__load_command_line_base,
            'long' : self.__load_command_line_base,
            'float' : self.__load_command_line_base,
            'list' : self.__load_command_line_base,
            'bool' : self.__load_command_line_base,
            'args' : self.__load_command_line_args,
            'command' : self.__load_command_subparser,
            'prefix' : self.__load_command_prefix,
            'count': self.__load_command_line_base,
            'help' : self.__load_command_line_base
        }
        self.__opt_parse_handle_map = {
            'string' : self.__string_action,
            'unicode' : self.__string_action,
            'bool' : self.__bool_action,
            'int' : self.__int_action,
            'long' : self.__int_action,
            'list' : self.__append_action,
            'count' : self.__inc_action,
            'help' : self.__help_action,
            'command' : self.__command_action
        }
        for p in priority:
            if p not in self.__class__.priority_args:
                msg = '(%s) not in priority values'%(p)
                self.error_msg(msg)
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
            commands.append(self.__maincmd)
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


    def __find_subparser_inner(self,cmdname,parentcmd=None):
        if cmdname is None or len(cmdname) == 0:
            return parentcmd
        if parentcmd is None:
            parentcmd = self.__maincmd
        sarr = re.split('\.',cmdname)
        for c in parentcmd.subcommands:
            if c.cmdname == sarr[0]:
                findcmd = self.__find_subparser_inner('.'.join(sarr[1:]),c)
                if findcmd is not None:
                    return findcmd
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
            #self.info('append to main')
            self.__maincmd.subcommands.append(cmdparser)
        else:
            #self.info('append to %s'%(curparser[-1].cmdname))
            curparser[-1].subcommands.append(cmdparser)
        return cmdparser


    def __load_command_subparser(self,prefix,keycls,lastparser=None):
        if not isinstance( keycls.value,dict):
            msg = '(%s) value must be dict'%(keycls.origkey)
            self.error_msg(msg)
        parser = self.__get_subparser_inner(keycls,lastparser)
        nextparser = [self.__maincmd]
        if lastparser is not None:
            nextparser = lastparser
        nextparser.append(parser)
        self.info('nextparser %s'%(self.format_string(nextparser)))
        self.info('keycls %s'%(keycls))
        # this would add prefix
        newprefix = prefix
        if len(newprefix) > 0:
            newprefix += '_'
        newprefix += keycls.cmdname
        self.__load_command_line_inner(newprefix,keycls.value,nextparser)
        nextparser.pop()
        return True

    def __load_command_prefix(self,prefix,keycls,curparser=None):
        self.__load_command_line_inner(keycls.prefix,keycls.value,curparser)
        return True

    def __load_command_line_inner(self,prefix,d,curparser=None):
        self.__load_command_line_json_added(curparser)
        # to add parser
        self.__load_command_line_help_added(curparser)
        parentpath = [self.__maincmd]
        if curparser is not None:
            parentpath = curparser
        for k in d.keys():
            v = d[k]
            self.info('%s , %s , %s , True'%(prefix,k,v))
            keycls = keyparse.ExtKeyParse(prefix,k,v,False)            
            valid = self.__load_command_map[keycls.type](prefix,keycls,parentpath)
            if not valid:
                msg = 'can not add (%s)'%(k,v)
                self.error_msg(msg)
        self.info('%s'%(self.format_string(parentpath)))
        return

    def load_command_line(self,d):
        if self.__ended != 0:
            raise Exception('you have call end_options or parse_command_line before call load_command_line_string or load_command_line')
        if not isinstance(d,dict):
            raise Exception('input parameter(%s) not dict'%(d))
        self.__load_command_line_inner('',d,None)
        return


    def load_command_line_string(self,s):
        try:
            d = json.loads(s)
        except:
            msg = '(%s) not valid json string'%(s)
            self.error_msg(msg)
        #self.info('d (%s)'%(d))
        self.load_command_line(d)
        return

    def __print_help(self,cmdparser=None):
        curcmd = self.__maincmd
        cmdpaths = []
        if cmdparser is not  None:
            curcmd = cmdparser[-1]
            i = 0
            while i < len(cmdparser) - 1:
                cmdpaths.append(cmdparser[i])
                i += 1
        return curcmd.get_help_info(0,cmdpaths)

    def print_help(self,fp=sys.stderr,cmdname=''):
        paths = self.__find_commands_in_path(cmdname)
        cmd = None
        if len(paths) > 0:
            cmd = paths[-1]
        s = self.__print_help(cmd)
        if len(__output_mode) > 0 :
            if self.__output_mode[-1] == 'bash':
                outs = 'cat <<EOFMM\n%s\nEOFMM\nexit 0'%(s)
                sys.stdout.write(outs)
                sys.exit(0)
        fp.write(s)
        sys.exit(0)
        return

    def __set_jsonvalue_not_defined(self,args,cmd,key,value):
        for chld in cmd.subcommands:
            args = self.__set_jsonvalue_not_defined(args,chld,key,value)
        for opt in cmd.cmdopts:
            if opt.isflag and opt.type != 'prefix' and opt.type != 'args' and opt.type != 'help':
                if opt.optdest == key:
                    if getattr(args,opt.optdest,None) is None:
                        if str(keyparse.TypeClass(value)) != str(keyparse.TypeClass(opt.value)):
                            self.warn('%s  type (%s) as default value type (%s)'%(key,str(keyparse.TypeClass(value)),str(keyparse.TypeClass(p.value))))
                        self.info('set (%s)=(%s)'%(key,value))
                        setattr(args,key,value)
                    return args
        return args


    def __load_jsonvalue(self,args,prefix,jsonvalue):
        for k in jsonvalue:
            if isinstance(jsonvalue[k],dict):
                newprefix = ''
                if len(prefix) > 0:
                    newprefix += '%s_'%(prefix)
                newprefix += k
                args = self.__load_jsonvalue(args,newprefix,jsonvalue[k])
            else:
                newkey = ''
                if (len(prefix) > 0):
                    newkey += '%s_'%(prefix)
                newkey += k
                args = self.__set_jsonvalue_not_defined(args,self.__maincmd,newkey,jsonvalue[k])
        return args


    def __load_jsonfile(self,args,cmdname,jsonfile):
        assert(jsonfile is not None)
        prefix = ''
        if cmdname is not None :
            prefix += cmdname
        fp = None
        try:
            fp = open(jsonfile,'r+')
        except:
            msg = 'can not open(%s)'%(jsonfile)
            self.error_msg(msg)
        try:
            jsonvalue = json.load(fp)
            fp.close()
            fp = None
        except:
            if fp is not None:
                fp.close()
            fp = None
            msg = 'can not parse (%s)'%(jsonfile)
            self.error_msg(msg)
        jsonvalue = keyparse.Utf8Encode(jsonvalue).get_val()
        return self.__load_jsonvalue(args,prefix,jsonvalue)



    def __set_parser_default_value(self,args,cmd):
        for chld in cmd.subcommands:
            args = self.__set_parser_default_value(args,chld)
        for opt in cmd.cmdopts:
            if opt.isflag and opt.type != 'prefix' and opt.type != 'args' and opt.type != 'help':
                args = self.__set_jsonvalue_not_defined(args,cmd,opt.optdest,opt.value)
        return args

    def __set_default_value(self,args):
        args = self.__set_parser_default_value(args,self.__maincmd)
        return args

    def __set_environ_value_inner(self,args,prefix,cmd):
        for chld in cmd.subcommands:
            args = self.__set_environ_value_inner(args,prefix,chld)

        for keycls in cmd.cmdopts:
            if keycls.isflag and keycls.type != 'prefix' and keycls.type != 'args' and keycls.type != 'help':
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
                            self.warn('can not set (%s) for %s = %s'%(optdest,oldopt,val))
                    elif keycls.type == 'int':
                        try:
                            lval = int(val)
                            setattr(args,oldopt,lval)
                        except:
                            self.warn('can not set (%s) for %s = %s'%(optdest,oldopt,val))
                    elif keycls.type == 'float':
                        try:
                            lval = float(val)
                            setattr(args,oldopt,lval)
                        except:
                            self.warn('can not set (%s) for %s = %s'%(optdest,oldopt,val))
                    else:
                        msg = 'internal error when (%s) type(%s)'%(keycls.optdest,keycls.type)
                        self.error_msg(msg)
        return args



    def __set_environ_value(self,args):
        args = self.__set_environ_value_inner(args,'',self.__maincmd)
        return args

    def __set_command_line_self_args(self,paths=None):
        parentpaths = [self.__maincmd]
        if paths is not None:
            parentpaths = paths
        for chld in parentpaths[-1].subcommands:
            curpaths = parentpaths
            curpaths.append(chld)
            self.__set_command_line_self_args(curpaths)
            curpaths.pop()
        setted = False
        for opt in parentpaths[-1].cmdopts:
            if opt.isflag and opt.flagname == '$':
                setted = True
                break
        if not setted:
            #self.info('set [%s] $'%(self.__format_cmd_from_cmd_array(parentpaths)))
            cmdname = self.__format_cmd_from_cmd_array(parentpaths)
            if cmdname is None:
                self.error_msg('can not get cmd (%s) whole name'%(curcmd))
            # replace with prefix
            prefix = cmdname.replace('.','_')
            curkey = keyparse.ExtKeyParse('','$','*',True)
            self.__load_command_line_args('',curkey,parentpaths)
        return

    def __parse_sub_command_json_set(self,args):
        # now we should get the 
        # first to test all the json file for special command
        subcmdname = getattr(args,'subcommand',None)
        if subcmdname is not None:
            cmds = self.__find_commands_in_path(subcmdname)
            idx = len(cmds)
            while idx >= 2:
                subname = self.__format_cmd_from_cmd_array(cmds[:idx])
                prefix = subname.replace('.','_')
                jsondest = '%s_json'%(prefix)
                jsonfile = getattr(args,jsondest,None)
                if jsonfile is not None:
                    # ok we should make this parse
                    args = self.__load_jsonfile(args,subname,jsonfile)
                idx -= 1
        return args

    def __parse_command_json_set(self,args):
        # to get the total command
        if args.json is not None:
            jsonfile = args.json
            args = self.__load_jsonfile(args,'',jsonfile)
        return args

    def __parse_environment_set(self,args):
        # now get the environment value
        args = self.__set_environ_value(args)
        return args

    def __parse_env_subcommand_json_set(self,args):
        # now to check for the environment as the put file
        subcmdname = getattr(args,'subcommand',None)
        if subcmdname is not None:
            cmds = self.__find_commands_in_path(subcmdname)
            idx = len(cmds)
            while idx >= 2:
                subname = self.__format_cmd_from_cmd_array(cmds[:idx])
                prefix = subname.replace('.','_')
                jsondest = '%s_json'%(prefix)
                jsondest = jsondest.replace('-','_')
                jsondest = jsondest.upper()
                jsonfile = os.getenv(jsondest,None)
                if jsonfile is not None:
                    # ok we should make this parse
                    args = self.__load_jsonfile(args,subname,jsonfile)
                idx -= 1
        return args

    def __parse_env_command_json_set(self,args):
        # to get the json existed 
        jsonfile = os.getenv('EXTARGSPARSE_JSON',None)
        if jsonfile is not None:
            args = self.__load_jsonfile(args,'',jsonfile)
        return args


    def __format_cmdname_msg(self,cmdname,msg):
        retmsg = cmdname
        if len(retmsg) > 0:
            retmsg += ' command '
        retmsg += msg
        return retmsg

    def __set_args(self,args,cmdpaths,vals):
        argskeycls = None
        cmdname = self.__format_cmdname_path(cmdpaths)
        self.info('[%s] %s'%(cmdname,self.format_string(cmdpaths[-1].cmdopts)))
        for c in cmdpaths[-1].cmdopts:
            if c.flagname == '$':
                argskeycls = c
                break
        if argskeycls is None:
            self.error_msg('can not find args in (%s)'%(cmdname))
        if vals is not None and not isinstance(vals,list):
            msg = self.__format_cmdname_msg(cmdname,'invalid type args (%s) %s'%(type(vals),vals))
            self.error_msg(msg)
        if argskeycls.nargs == '*' or argskeycls.nargs == '+' or argskeycls.nargs == '?':
            if argskeycls.nargs == '?':
                if vals is not None and len(vals) > 1:
                    msg = self.__format_cmdname_msg(cmdname,'args \'?\' must <= 1')
                    self.error_msg(msg)
            elif argskeycls.nargs == '+':
                if (vals is None or len(vals) == 0):
                    msg = self.__format_cmdname_msg(cmdname,'args must at least 1')
                    self.error_msg(msg)
        else:
            nargs = argskeycls.nargs
            if vals is None:
                if nargs != 0:
                    msg = self.__format_cmdname_msg(cmdname,'args must 0 but(%s)'%(vals))
                    self.error_msg(msg)
            else:
                if len(vals) != nargs:
                    msg = self.__format_cmdname_msg(cmdname,'vals(%s) %d != nargs %d'%(vals,len(vals),nargs))
                    self.error_msg(msg)
        keyname = 'args'
        if len(cmdpaths) > 1:
            keyname = 'subnargs'        
        if vals is None:
            self.info('set %s %s'%(keyname,[]))
            setattr(args,keyname,[])
        else:
            self.info('set %s %s'%(keyname,vals))
            setattr(args,keyname,vals)

        subcmdname = self.__format_cmd_from_cmd_array(cmdpaths)
        if len(subcmdname) > 0:
            setattr(args,'subcommand',subcmdname)
        return args


    def __call_opt_method(self,args,key,value,keycls):
        args = self.__opt_parse_handle_map[keycls.type](args,keycls,value)
        return args

    def parse_args(self,params=None):
        if params is None:
            params = sys.argv[1:]
        parsestate = _ParseState(params,self.__maincmd)
        args = NameSpace()
        try:
            while True:
                key,val,keycls = parsestate.step_one()
                #self.info('key %s val %s keycls %s'%(key,val,keycls))
                if keycls is None:
                    cmdpaths = parsestate.get_cmd_paths()
                    s = ''
                    for c in cmdpaths:
                        s += '%s'%(c)
                    self.info('cmdpaths %s'%(s))
                    args = self.__set_args(args,cmdpaths,val)
                    self.info('args %s'%(args))
                    break
                args = self.__call_opt_method(args,key,val,keycls)
                self.info('%s'%(args))
        except Exception as e:
            self.error_msg('parse (%s) error(%s)'%(params,e))
        return args

    def __debug_opts(self,rootcmd=None,tabs=0):
        s = ''
        if rootcmd is None:
            rootcmd = self.__maincmd
        s += ' ' * tabs * 4
        s += '%s'%(rootcmd)
        for c in rootcmd.subcommands:
            s += __debug_opts(c,tabs + 1)
        return s


    def end_options(self):
        self.__ended = 1
        self.__set_command_line_self_args()
        return


    def parse_command_line(self,params=None,Context=None,mode=None):
        self.__ended = 1
        # we input the self command line args by default
        pushmode = False
        if mode is not None:
            pushmode = True
            self.__output_mode.append(mode)
        args = NameSpace()
        try:
            self.__set_command_line_self_args()
            if params is None:
                params = sys.argv[1:]
            args = self.parse_args(params)
            for p in self.__load_priority:
                args = self.__parse_set_map[p](args)

            # set the default value
            args = self.__set_default_value(args)
            # now test whether the function has
            if args.subcommand is not None:
                cmds = self.__find_commands_in_path(args.subcommand)
                funcname = cmds[-1].keycls.function
                if funcname is not None:
                    return self.__call_func_args(funcname,args,Context)
        finally:
            if pushmode:
                self.__output_mode.pop()
                pushmode = False
        return args

    def __get_subcommands(self,cmdname,cmdpaths=None):
        if cmdpaths is None:
            cmdpaths = [self.__maincmd]
        retnames = None
        if cmdname is None or len(cmdname) == 0:
            retnames = []
            for c in cmdpaths[-1].subcommands:
                retnames.append(c.cmdname)
            return retnames
        sarr = re.split('\.',cmdname)
        for c in cmdpaths[-1].subcommands:
            if c.cmdname == sarr[0]:
                cmdpaths.append(c)
                return self.__get_subcommands('.'.join(sarr[1:]),cmdpaths)
        return retnames



    def get_subcommands(self,cmdname=None):
        return self.__get_subcommands(cmdname)

    def __get_cmdopts(self,cmdname,cmdpaths=None):
        if cmdpaths is None:
            cmdpaths = [self.__maincmd]
        retopts = None
        if cmdname is None or len(cmdname) == 0:
            retopts = cmdpaths[-1].cmdopts
            return retopts

        sarr = re.split('\.',cmdname)
        for c in cmdpaths[-1].subcommands:
            if c.cmdname == sarr[0]:
                cmdpaths.append(c)
                return self.__get_cmdopts('.'.join(sarr[1:]),cmdpaths)
        return None

    def get_cmdopts(self,cmdname=None):
        return self.__get_cmdopts(cmdname)


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
        self.info('shell_out\n%s'%(s))
        return s




def call_args_function(args,context):
    if hasattr(args,'subcommand'):
        context.has_called_args = args.subcommand
    else:
        context.has_called_args = None
    return

class ExtArgsTestCase(unittest.TestCase):
    def setUp(self):
        keyname = '_%s__logger'%(self.__class__.__name__)
        if getattr(self,keyname,None) is None:
            self.__logger = _LoggerObject()

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


    def __assert_get_opt(self,opts,optname):
        for c in opts:
            if not c.isflag :
                continue
            if optname == '$' and c.flagname == '$':
                return c
            if c.flagname == '$':
                continue
            if optname == c.optdest:
                return c
        return None

    def __assert_get_subcommand(self,cmds,cmdname):
        for c in cmds:
            if c == cmdname:
                return c
        return None

    def test_A022(self):
        commandline='''
        {
            "verbose|v" : "+"
        }
        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        parser.end_options()
        self.assertEqual(parser.get_subcommands(),[])
        self.assertEqual(parser.get_subcommands('nocommand'),None)
        opts = parser.get_cmdopts()
        self.assertEqual(len(opts),4)
        flag = self.__assert_get_opt(opts,'$')        
        self.assertEqual(flag.flagname,'$')
        self.assertEqual(flag.prefix , '')
        flag = self.__assert_get_opt(opts,'verbose')
        self.assertEqual(flag.optdest,'verbose')
        self.assertEqual(flag.longopt,'--verbose')
        self.assertEqual(flag.shortopt,'-v')
        nonflag = self.__assert_get_opt(opts,'noflag')
        self.assertEqual(nonflag,None)
        flag = self.__assert_get_opt(opts,'json')
        self.assertEqual(flag.value,None)
        flag = self.__assert_get_opt(opts,'help')
        self.assertTrue(flag is not None)
        self.assertEqual(flag.longopt,'--help')
        self.assertEqual(flag.shortopt,'-h')
        self.assertEqual(flag.type,'help')
        return

    def test_A023(self):
        commandline='''
        {
            "verbose|v" : "+",
            "dep" : {
                "new|n" : false,
                "$<NARGS>" : "+"
            },
            "rdep" : {
                "new|n" : true,
                "$<NARGS>" : "?"
            }
        }
        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        parser.end_options()
        cmds = parser.get_subcommands()
        self.assertEqual(len(cmds),2)
        cmd = self.__assert_get_subcommand(cmds,'dep')
        self.assertTrue(cmd,'dep')
        cmd = self.__assert_get_subcommand(cmds,'rdep')
        self.assertEqual(cmd,'rdep')
        opts = parser.get_cmdopts()
        self.assertEqual(len(opts),4)
        flag = self.__assert_get_opt(opts,'$')
        self.assertEqual(flag.nargs,'*')
        flag = self.__assert_get_opt(opts,'verbose')
        self.assertEqual(flag.type,'count')
        flag = self.__assert_get_opt(opts,'json')
        self.assertEqual(flag.type,'string')
        flag = self.__assert_get_opt(opts,'help')
        self.assertEqual(flag.type,'help')
        opts = parser.get_cmdopts('dep')
        self.assertEqual(len(opts),4)
        flag = self.__assert_get_opt(opts,'$')
        self.assertEqual(flag.varname,'NARGS')
        flag = self.__assert_get_opt(opts,'help')
        self.assertEqual(flag.type,'help')
        flag = self.__assert_get_opt(opts,'dep_json')
        self.assertEqual(flag.type,'string')
        flag = self.__assert_get_opt(opts,'dep_new')
        self.assertEqual(flag.type,'bool')
        return

    def test_A024(self):
        commandline='''
        {
            "rdep" : {
                "ip" : {
                    "modules" : [],
                    "called" : true,
                    "setname" : null,
                    "$" : 2
                }
            },
            "dep" : {
                "port" : 5000,
                "cc|C" : true
            },
            "verbose|v" : "+"
        }
        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        args = parser.parse_command_line(['rdep','ip','--verbose','--rdep-ip-modules','cc','--rdep-ip-setname','bb','xx','bb'])
        self.assertEqual(args.subcommand,'rdep.ip')
        self.assertEqual(args.verbose,1)
        self.assertEqual(args.rdep_ip_modules,['cc'])
        self.assertEqual(args.rdep_ip_setname,'bb')
        self.assertEqual(args.subnargs,['xx','bb'])
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        args = parser.parse_command_line(['dep','--verbose','--verbose','-vvC'])
        self.assertEqual(args.subcommand,'dep')
        self.assertEqual(args.verbose,4)
        self.assertEqual(args.dep_port,5000)
        self.assertEqual(args.dep_cc,False)
        self.assertEqual(args.subnargs,[])
        return









def main():
    if '-v' in sys.argv[1:] or '--verbose' in sys.argv[1:]:
        os.environ['EXTARGSPARSE_LOGLEVEL'] = '4'
    unittest.main()

if __name__ == '__main__':
    main()  

