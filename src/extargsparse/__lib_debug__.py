#!/usr/bin/env python

##extractstart 
import os
import sys
import json
import logging
import re
import importlib
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import __key_debug__ as keyparse
if sys.version[0] == '2':
    import StringIO
else:
    import io as StringIO

##importdebugstart release not use modules
import unittest
import tempfile
import subprocess
import platform
import disttools
##importdebugend release not use modules

##extractend

COMMAND_SET = 10
SUB_COMMAND_JSON_SET = 20
COMMAND_JSON_SET = 30
ENVIRONMENT_SET = 40
ENV_SUB_COMMAND_JSON_SET = 50
ENV_COMMAND_JSON_SET = 60
DEFAULT_SET = 70


class ExtArgsOptions(object):
    def __init__(self):
        self.__obj = dict()
        self.__obj['errorhandler'] = 'exit'
        self.__obj['prog'] = sys.argv[0]
        self.__logger = _LoggerObject()
        return

    def __setattr__(self,key,val):
        if not key.startswith('_'):
            #self.__logger.info('%s=%s'%(key,val),2)
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


class _LoggerObject(object):
    def __init__(self,cmdname='extargsparse'):
        self.__logger = logging.getLogger(cmdname)
        if len(self.__logger.handlers) == 0:
            loglvl = logging.WARN
            lvlname = '%s_LOGLEVEL'%(cmdname)
            lvlname = lvlname.upper()
            if lvlname in os.environ.keys():
                v = os.environ[lvlname]
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
            fmtname = '%s_LOGFMT'%(cmdname)
            fmtname = fmtname.upper()
            if fmtname in os.environ.keys():
                v = os.environ[fmtname]
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

    def format_call_msg(self,msg,callstack):
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
            inmsg = self.format_call_msg(msg,(callstack + 1))
        return self.__logger.info('%s'%(inmsg))

    def error(self,msg,callstack=1):
        inmsg = msg
        if callstack is not None:
            inmsg = self.format_call_msg(msg,(callstack + 1))
        return self.__logger.error('%s'%(inmsg))

    def warn(self,msg,callstack=1):
        inmsg = msg
        if callstack is not None:
            inmsg = self.format_call_msg(msg,(callstack + 1))
        return self.__logger.warn('%s'%(inmsg))

    def debug(self,msg,callstack=1):
        inmsg = msg
        if callstack is not None:
            inmsg = self.format_call_msg(msg,(callstack + 1))
        return self.__logger.debug('%s'%(inmsg))

    def fatal(self,msg,callstack=1):
        inmsg = msg
        if callstack is not None:
            inmsg = self.format_call_msg(msg,(callstack + 1))
        return self.__logger.fatal('%s'%(inmsg))


class _HelpSize(_LoggerObject):
    #####################################
    ##
    ##  parser.opts = []
    ##  parser.cmdname = ''
    ##  parser.subcommands = []
    ##  parser.callfunction = None
    ##  parser.helpinfo  = None
    ##  parser.keycls = keycls
    #####################################    
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

    def __init__(self,keycls=None,opt=None):
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
            # it is main cmd
            self.keycls = keyparse.ExtKeyParse('','main',{},False)
            self.cmdname = ""
            self.cmdopts = []
            self.cmdopts = []
            self.subcommands = []
            self.helpinfo = None
            self.callfunction = None
        self.screenwidth = 80
        if opt is not None and issubclass(opt.__class__,ExtArgsOptions):
            if opt.screenwidth is not None:
                self.screenwidth = opt.screenwidth
        if self.screenwidth < 40:
            self.screenwidth = 40
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
            if opt.type == 'args' :
                continue
            optname,optexpr,opthelp = self.__get_opt_help(opt)
            helpsize.optnamesize = len(optname) + 1
            helpsize.optexprsize = len(optexpr) + 1
            helpsize.opthelpsize = len(opthelp) + 1        

        if recursive != 0:
            for cmd in self.subcommands:
                if recursively > 0:
                    helpsize = cmd.get_help_size(helpsize,recursive-1)
                else:
                    helpsize = cmd.get_help_size(helpsize,recursive)
        for cmd in self.subcommands:
            helpsize.cmdnamesize = len(cmd.cmdname) + 2
            helpsize.cmdhelpsize = len(cmd.helpinfo)
        return helpsize

    def __get_cmd_help(self,cmd):
        cmdname = ''
        cmdhelp = ''
        if cmd.cmdname is not None:
            cmdname = '[%s]'%(cmd.cmdname)
        if cmd.helpinfo is not None:
            cmdhelp = '%s'%(cmd.helpinfo)
        return cmdname,cmdhelp

    def __get_indent_string(self,s,indentsize,maxsize):
        rets = ''
        curs = ' ' * indentsize
        for c in s:
            if (c == ' ' or c == '\t') and len(curs) >= maxsize:
                rets += curs + '\n'
                curs = ' ' * indentsize
                continue
            curs += c
        if curs.strip(' \t') != '':
            rets += curs + '\n'
        curs = ''
        return rets


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
                    if isinstance(args.nargs,str):
                        if args.nargs == '+' :
                            s += ' args...'
                        elif args.nargs == '*':
                            s += ' [args...]'
                        elif args.nargs == '?':
                            s += ' arg'
                    else:
                        if args.nargs > 1:
                            s += ' args...'
                        elif args.nargs == 1:
                            s += ' arg'
                        else:
                            s += ''
                        break
            s += '\n'
        if self.description is not None:
            s += '%s\n'%(self.description)        
        if len(self.cmdopts) > 0:
            s += '[OPTIONS]\n'
            for opt in self.cmdopts:
                if opt.type == 'args' :
                    continue
                optname,optexpr,opthelp = self.__get_opt_help(opt)
                curs = ''
                curs += ' ' * 4 
                curs += '%-*s %-*s %-*s\n'%(helpsize.optnamesize,optname,helpsize.optexprsize,optexpr,helpsize.opthelpsize,opthelp)
                if len(curs) < self.screenwidth :
                    s += curs
                else:
                    curs = ''
                    curs += ' ' * 4
                    curs += '%-*s %-*s'%(helpsize.optnamesize,optname,helpsize.optexprsize,optexpr)
                    s += curs + '\n'
                    if self.screenwidth >= 60:
                        s += self.__get_indent_string(opthelp,20, self.screenwidth)
                    else:
                        s += self.__get_indent_string(opthelp,15,self.screenwidth)

        if len(self.subcommands)>0:
            s += '[SUBCOMMANDS]\n'
            for cmd in self.subcommands:
                cmdname,cmdhelp = self.__get_cmd_help(cmd)
                curs = ''
                curs += ' ' * 4
                curs += '%-*s %-*s'%(helpsize.cmdnamesize,cmdname,helpsize.cmdhelpsize,cmdhelp)
                if len(curs) < self.screenwidth:
                    s += curs + '\n'
                else:
                    curs = ''
                    curs += ' ' * 4
                    curs += '%-*s'%(helpsize.cmdnamesize,cmdname)
                    s += curs + '\n'
                    if self.screenwidth >= 60:                        
                        s += self.__get_indent_string(cmdhelp,20, self.screenwidth)
                    else:
                        s += self.__get_indent_string(cmdhelp,15,self.screenwidth)

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
                            self.info('oldidx %d (len %d)'%(oldidx,len(self.__args)))
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
            self.info('args %s __curidx %d'%(self.__args,self.__curidx))
            if len(self.__args) > (self.__curidx):
                value = self.__args[(self.__curidx):]
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


class NameSpaceEx(object):
    def __init__(self):
        self.__obj = dict()
        self.__access = dict()
        self.__logger = _LoggerObject()
        return

    def __setattr__(self,key,val):
        if not key.startswith('_'):
            self.__logger.info('%s=%s'%(key,val),2)
            self.__obj[key] = val
            self.__access[key] = True
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

    def __repr__(self):
        return self.__str__()

    def __has_accessed(self,name):
        if name in self.__access.keys():
            return True
        return False

    def get_keys(self):
        return self.__obj.keys()

def set_attr_args(self,args,prefix):
    if not issubclass(args.__class__,NameSpaceEx):
        raise Exception('args not NameSpaceEx')
    for p in args.get_keys():
        if len(prefix) == 0 or p.startswith('%s_'%(prefix)):
            setattr(self,p,getattr(args,p))
    return




class ExtArgsParse(_LoggerObject):
    reserved_args = ['subcommand','subnargs','json','nargs','extargs','help','args']
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
        self.print_help(sys.stdout,value)
        sys.exit(0)
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
            s += '    %s'%(self.format_call_msg(message,1))

        if self.__error_handler== 'exit':
            sys.stderr.write('%s'%(s))
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
        if keycls.isflag and keycls.flagname != '$' and keycls.flagname in self.__class__.reserved_args:
            self.error_msg('(%s) in reserved_args (%s)'%(keycls.flagname,self.__class__.reserved_args))
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
        keycls = keyparse.ExtKeyParse(prefix,key,value,True,False,True)
        return self.__load_command_line_jsonfile(keycls,curparser)

    def __load_command_line_help_added(self,curparser=None):
        key = 'help|h##to display this help information##'
        value = None
        keycls = keyparse.ExtKeyParse('',key,value,True,True)
        #self.info('[%s] add help'%(self.__format_cmd_from_cmd_array(curparser)))
        return self.__load_command_line_help(keycls,curparser)


    def __init__(self,options=None,priority=[SUB_COMMAND_JSON_SET,COMMAND_JSON_SET,ENVIRONMENT_SET,ENV_SUB_COMMAND_JSON_SET,ENV_COMMAND_JSON_SET]):
        super(ExtArgsParse,self).__init__()
        if options is None:
            options = ExtArgsOptions()
        self.__maincmd = _ParserCompact(None)

        self.__maincmd.prog = options.prog
        self.__maincmd.usage = options.usage
        self.__maincmd.description = options.description
        self.__maincmd.epilog = options.epilog
        self.__maincmd.version = options.version
        self.__error_handler = options.errorhandler
        self.__help_handler = options.helphandler
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
            'help' : self.__load_command_line_base ,
            'jsonfile' : self.__load_command_line_base
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
            'jsonfile' : self.__string_action,
            'command' : self.__command_action ,
            'float' : self.__float_action
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
            for c in curparser:
                if len(cmdname) > 0:
                    cmdname += '.'
                cmdname += c.cmdname
        return cmdname

    def __find_commands_in_path(self,cmdname,curparser=None):
        sarr = ['']
        if cmdname is not None:
            sarr = re.split('\.',cmdname)
        commands = []
        i = 0
        if self.__maincmd is not None:
            commands.append(self.__maincmd)
        while i <= len(sarr) and cmdname is not None and len(cmdname) > 0:
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
        if keycls.iscmd and keycls.cmdname in self.__class__.reserved_args:
            msg = 'command(%s) in reserved_args (%s)'%(keycls.cmdname,self.__class__.reserved_args)
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
        if keycls.prefix in self.__class__.reserved_args:
            msg = 'prefix (%s) in reserved_args (%s)'%(keycls.prefix,self.__class__.reserved_args)
            self.error_msg(msg)
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
            raise Exception('you have call parse_command_line before call load_command_line_string or load_command_line')
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
        if self.__help_handler is not None and self.__help_handler == 'nohelp':
            return 'no help information'
        curcmd = self.__maincmd
        cmdpaths = []
        if cmdparser is not  None:
            self.info('cmdparser %s'%(self.format_string(cmdparser)))
            curcmd = cmdparser[-1]
            i = 0
            while i < len(cmdparser) - 1:
                cmdpaths.append(cmdparser[i])
                i += 1
        return curcmd.get_help_info(None,cmdpaths)

    def print_help(self,fp=sys.stderr,cmdname=''):
        paths = self.__find_commands_in_path(cmdname)
        if paths is  None:
            self.error_msg('can not find [%s] cmd'%(cmdname))
        s = self.__print_help(paths)
        if len(self.__output_mode) > 0 :
            if self.__output_mode[-1] == 'bash':
                outs = 'cat <<EOFMM\n%s\nEOFMM\nexit 0'%(s)
                sys.stdout.write(outs)
                sys.exit(0)
        fp.write(s)
        #sys.exit(0)
        return

    def __get_args_accessed(self,args,optdest):
        funcname = '_%s__has_accessed'%('NameSpaceEx')
        funcptr = getattr(args,funcname,None)
        if funcptr is None :
            raise Exception('%s not found ,internal error'%(funcname))
        return funcptr(optdest)

    def __set_jsonvalue_not_defined(self,args,cmd,key,value):
        for chld in cmd.subcommands:
            args = self.__set_jsonvalue_not_defined(args,chld,key,value)
        for opt in cmd.cmdopts:
            if opt.isflag and opt.type != 'prefix' and opt.type != 'args' and opt.type != 'help':
                if opt.optdest == key:
                    if not self.__get_args_accessed(args,opt.optdest):
                        if str(keyparse.TypeClass(value)) != str(keyparse.TypeClass(opt.value)):
                            self.warn('%s  type (%s) as default value type (%s)'%(key,str(keyparse.TypeClass(value)),str(keyparse.TypeClass(opt.value))))
                        else:
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
        # replace prefix ok
        prefix = prefix.replace('.','_')
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
        self.info('load (%s) prefix(%s) value (%s)'%(jsonfile,prefix,repr(jsonvalue)))
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
                    if keycls.type == 'string' or keycls.type == 'jsonfile':
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
                    elif keycls.type == 'int' or keycls.type == 'count':
                        try:
                            val = val.lower()
                            base = 10
                            if val.startswith('0x') :
                                val = val[2:]
                                base = 16
                            elif val.startswith('x'):
                                val = val[1:]
                                base = 16
                            lval = int(val,base)
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

    def __check_varname_inner(self,paths=None):
        parentpaths = [self.__maincmd]
        if paths is not None:
            parentpaths = paths
        for chld in parentpaths[-1].subcommands:
            curpaths = parentpaths
            curpaths.append(chld)
            self.__check_varname_inner(curpaths)
            curpaths.pop()

        for opt in parentpaths[-1].cmdopts:
            if opt.isflag:
                if opt.type == 'help' or opt.type == 'args':
                    continue
                if opt.varname in self.__varnames:
                    msg = '%s is already in the check list'%(opt.varname)
                    self.error_msg(msg)
                self.__varnames.append(opt.varname)
                self.__varcmds.append(parentpaths[-1])
        return

    def __set_command_line_self_args_inner(self,paths=None):
        parentpaths = [self.__maincmd]
        if paths is not None:
            parentpaths = paths
        for chld in parentpaths[-1].subcommands:
            curpaths = parentpaths
            curpaths.append(chld)
            self.__set_command_line_self_args_inner(curpaths)
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


    def __set_command_line_self_args(self,paths=None):
        if self.__ended != 0:
            return
        self.__set_command_line_self_args_inner(paths)
        self.__varnames = []
        self.__varcmds = []
        self.__check_varname_inner()
        self.__varcmds = []
        self.__varnames = []
        self.__ended = 1
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
        args = NameSpaceEx()
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
                elif keycls.type == 'help':
                    # now we should give special 
                    cmdpaths = parsestate.get_cmd_paths()
                    helpcmdname = self.__format_cmd_from_cmd_array(cmdpaths)
                    self.__call_opt_method(args,key,helpcmdname,keycls)
                else:
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



    def parse_command_line(self,params=None,Context=None,mode=None):
        # we input the self command line args by default
        pushmode = False
        if mode is not None:
            pushmode = True
            self.__output_mode.append(mode)
        args = NameSpaceEx()
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
            return sorted(retnames)
        sarr = re.split('\.',cmdname)
        for c in cmdpaths[-1].subcommands:
            if c.cmdname == sarr[0]:
                cmdpaths.append(c)
                return self.__get_subcommands('.'.join(sarr[1:]),cmdpaths)
        return retnames

    def __get_cmdkey(self,cmdname,cmdpaths=None):
        if cmdpaths is None:
            cmdpaths = [self.__maincmd]
        retkey = None
        if cmdname is None or len(cmdname) == 0:
            retkey = cmdpaths[-1].keycls
            return retkey
        sarr = re.split('\.',cmdname)
        for c in cmdpaths[-1].subcommands:
            if c.cmdname == sarr[0]:
                cmdpaths.append(c)
                return self.__get_cmdkey('.'.join(sarr[1:]),cmdpaths)
        return None

    def get_subcommands(self,cmdname=None):
        self.__set_command_line_self_args()
        return self.__get_subcommands(cmdname)

    def get_cmdkey(self,cmdname=None):
        self.__set_command_line_self_args()
        return self.__get_cmdkey(cmdname)

    def __sort_cmdopts(self,retopts=None):
        if retopts is not None:
            normalopts = []
            argsopt = None
            for opt in retopts:
                if opt.type == 'args':
                    assert(argsopt is None)
                    argsopt = opt
                    continue
                normalopts.append(opt)
            i = 0
            while i < len(normalopts):
                j = i + 1
                while j < len(normalopts):
                    if normalopts[j].optdest <  normalopts[i].optdest:
                        tmpopt = normalopts[j]
                        normalopts[j] = normalopts[i]
                        normalopts[i] = tmpopt
                    j += 1
                i += 1
            retopts = []
            if argsopt is not None:
                retopts.append(argsopt)
            retopts.extend(normalopts)
        return retopts


    def __get_cmdopts(self,cmdname,cmdpaths=None):
        if cmdpaths is None:
            cmdpaths = [self.__maincmd]
        retopts = None
        if cmdname is None or len(cmdname) == 0:
            retopts = cmdpaths[-1].cmdopts
            # now sorted the retopts
            return self.__sort_cmdopts(retopts)

        sarr = re.split('\.',cmdname)
        for c in cmdpaths[-1].subcommands:
            if c.cmdname == sarr[0]:
                cmdpaths.append(c)
                return self.__get_cmdopts('.'.join(sarr[1:]),cmdpaths)
        return None

    def get_cmdopts(self,cmdname=None):
        self.__set_command_line_self_args()
        return self.__get_cmdopts(cmdname)


def debug_args_function(args,context):
    if hasattr(args,'subcommand'):
        context.has_called_args = args.subcommand
    else:
        context.has_called_args = None
    return

class debug_tcebase(object):
    def __init__(self):
        return

    def __setattr__(self,k,v):
        if k.startswith('_'):
            setattr(self,k,v)
            return
        self.__dict__[k]=v
        return

    def __getattr__(self,k):
        if k.startswith('_'):
            return getattr(self,k,None)
        if k in self.__dict__.keys():
            return self.__dict__[k]
        return None




class debug_extargs_test_case(unittest.TestCase):
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

    def __write_temp_file(self,content):
        fd , tempf = tempfile.mkstemp(suffix='.json',prefix='parse',dir=None,text=True)
        os.close(fd)
        with open(tempf,'w') as f:
            f.write('%s'%(content))
        self.info('tempf %s'%(tempf))
        return tempf

    def __remove_file_ok(self,filename,description,ok):
        if filename is not None and ok:
            os.remove(filename)
        elif filename is not None:
            self.error('%s %s'%(description,filename))
        return

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
            "dep<%s.debug_args_function>" : {
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

            options = ExtArgsOptions()
            options.errorhandler = 'raise'
            parser = ExtArgsParse(options)
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

            options = ExtArgsOptions()
            options.errorhandler = 'raise'
            parser = ExtArgsParse(options)
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
        self.assertEqual(flag.type,'jsonfile')
        flag = self.__assert_get_opt(opts,'help')
        self.assertEqual(flag.type,'help')
        opts = parser.get_cmdopts('dep')
        self.assertEqual(len(opts),4)
        flag = self.__assert_get_opt(opts,'$')
        self.assertEqual(flag.varname,'NARGS')
        flag = self.__assert_get_opt(opts,'help')
        self.assertEqual(flag.type,'help')
        flag = self.__assert_get_opt(opts,'dep_json')
        self.assertEqual(flag.type,'jsonfile')
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

    def test_A025(self):
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
                "$" : "+",
                "ip" : {
                    "verbose" : "+",
                    "list" : [],
                    "cc" : []
                }
            },
            "rdep" : {
                "ip" : {
                    "verbose" : "+",
                    "list" : [],
                    "cc" : []
                }
            }
        }
        '''
        jsonfile = None
        depjsonfile = None
        rdepjsonfile = None
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
            fd,rdepjsonfile = tempfile.mkstemp(suffix='.json',prefix='parse',dir=None,text=True)
            os.close(fd)
            fd = -1
            with open(jsonfile,'w+') as f:
                f.write('{ "http" : { "url" : "http://www.github.com"} ,"dep":{"list" : ["jsonval1","jsonval2"],"string" : "jsonstring"},"port":6000,"verbose":3}\n')
            with open(depjsonfile,'w+') as f:
                f.write('{"list":["depjson1","depjson2"]}\n')
            with open(rdepjsonfile,'w+') as f:
                f.write('{"ip": {"list":["rdepjson1","rdepjson3"],"verbose": 5}}\n')
            delone = True
            while delone:
                delone = False
                for k in os.environ.keys():
                    if k.startswith('EXTARGS_') or k.startswith('DEP_') or k == 'EXTARGSPARSE_JSON' or k.startswith('HTTP_') or k.startswith('RDEP_'):
                        del os.environ[k]
                        delone = True
                        break

            os.environ['EXTARGSPARSE_JSON'] = jsonfile
            os.environ['DEP_JSON'] = depjsonfile
            os.environ['RDEP_JSON'] = rdepjsonfile

            parser = ExtArgsParse()
            self.assertTrue( 'DEP_STRING' not in os.environ.keys())
            self.assertTrue( 'DEP_LIST' not in os.environ.keys()) 
            self.assertTrue( 'HTTP_VISUAL_MODE' not in os.environ.keys())
            parser.load_command_line_string(commandline)
            
            args = parser.parse_command_line(['-p','9000','rdep','ip','--rdep-ip-verbose','--rdep-ip-cc','ee','ww'])
            
            os.environ['DEP_STRING'] = depstrval
            os.environ['DEP_LIST'] = depliststr
            os.environ['HTTP_VISUAL_MODE']=httpvmstr
            self.assertTrue( 'DEP_STRING' in os.environ.keys())
            self.assertTrue( 'DEP_LIST'  in os.environ.keys()) 
            self.assertTrue( 'HTTP_VISUAL_MODE'  in os.environ.keys())

            self.assertEqual(args.verbose,3)
            self.assertEqual(args.port,9000)
            self.assertEqual(args.dep_string,'jsonstring')
            self.assertEqual(args.dep_list,['jsonval1', 'jsonval2'])
            self.assertEqual(args.http_visual_mode,False)
            self.assertEqual(args.http_url,'http://www.github.com')
            self.assertEqual(args.subnargs,['ww'])
            self.assertEqual(args.subcommand,'rdep.ip')
            self.assertEqual(args.rdep_ip_verbose,1)
            self.assertEqual(args.rdep_ip_cc,['ee'])
            self.assertEqual(args.rdep_ip_list,['rdepjson1','rdepjson3'])
        finally:
            if depjsonfile is not None:
                os.remove(depjsonfile)
            depjsonfile = None
            if rdepjsonfile is not None:
                os.remove(rdepjsonfile)
            rdepjsonfile = None
            if jsonfile is not None:
                os.remove(jsonfile)
            jsonfile = None
            if 'EXTARGSPARSE_JSON' in os.environ.keys():
                del os.environ['EXTARGSPARSE_JSON']
            if 'DEP_JSON' in os.environ.keys():
                del os.environ['DEP_JSON']
        return

    def __split_strings(self,longstr):
        sarr = re.split('\n',longstr)
        retsarr = []
        for s in sarr:
            s = s.strip('\r\n')
            retsarr.append(s)
        return retsarr

    def __assert_string_expr(self,sarr,strexpr):
        #self.info('strexpr (%s)'%(strexpr))
        expr = re.compile(strexpr)
        ok = False
        for s in sarr:
            if expr.match(s):
                ok = True
                break
        return ok

    def __get_opt_ok(self,sarr,keycls):
        if keycls.type == 'args':
            return True
        exprstr = '^\\s+%s'%(keycls.longopt)
        if keycls.shortopt is not None:
            exprstr += '\\|%s'%(keycls.shortopt)
        exprstr += r'\s+.*'
        if keycls.nargs != 0:
            exprstr += '%s.*'%(keycls.optdest)
        logging.debug('sarr (%s) exprstr[%s]'%(sarr,exprstr))
        return self.__assert_string_expr(sarr,exprstr)


    def test_A026(self):
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
                "$" : "+",
                "ip" : {
                    "verbose" : "+",
                    "list" : [],
                    "cc" : []
                }
            },
            "rdep" : {
                "ip" : {
                    "verbose" : "+",
                    "list" : [],
                    "cc" : []
                }
            }
        }
        '''
        options = ExtArgsOptions()
        options.prog = 'cmd1'
        parser = ExtArgsParse(options)
        parser.load_command_line_string(commandline)
        sio = StringIO.StringIO()
        parser.print_help(sio)
        self.info('\n%s'%(sio.getvalue()))
        sarr = self.__split_strings(sio.getvalue())
        opts = parser.get_cmdopts()
        for opt in opts:
            self.assertEqual(self.__get_opt_ok(sarr,opt),True)
        
        #self.assertEqual(self.__assert_string_expr(sarr,'^'))
        sio = StringIO.StringIO()
        parser.print_help(sio,'rdep')
        #self.info('\n%s'%(sio.getvalue()))
        sarr = self.__split_strings(sio.getvalue())
        opts = parser.get_cmdopts('rdep')
        for opt in opts:
            self.assertEqual(self.__get_opt_ok(sarr,opt),True)
        sio = StringIO.StringIO()
        parser.print_help(sio,'rdep.ip')
        #self.info('\n%s'%(sio.getvalue()))
        sarr = self.__split_strings(sio.getvalue())
        opts = parser.get_cmdopts('rdep.ip')
        for opt in opts:
            self.assertEqual(self.__get_opt_ok(sarr,opt),True)
        return

    def test_A027(self):
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
                "list|l!attr=cc;optfunc=list_opt_func!" : [],
                "string|s" : "s_var",
                "$" : "+",
                "ip" : {
                    "verbose" : "+",
                    "list" : [],
                    "cc" : []
                }
            },
            "rdep" : {
                "ip" : {
                    "verbose" : "+",
                    "list" : [],
                    "cc" : []
                }
            }
        }
        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        opts = parser.get_cmdopts('dep')
        attr= None
        for opt in opts:
            if opt.type == 'args':
                continue
            if opt.flagname == 'list':
                attr = opt.attr
                break
        self.assertTrue(attr is not None)
        self.assertEqual(attr.attr,'cc')
        self.assertTrue(attr.optfunc,'list_opt_func')
        return

    def test_A028(self):
        commandline= '''
        {
            "verbose<VAR1>|v" : "+",
            "+http" : {
                "url|u<VAR1>" : "http://www.google.com",
                "visual_mode|V": false
            },
            "$port|p" : {
                "value" : 3000,
                "type" : "int",
                "nargs" : 1 , 
                "helpinfo" : "port to connect"
            },
            "dep" : {
                "list|l!attr=cc;optfunc=list_opt_func!" : [],
                "string|s" : "s_var",
                "$" : "+",
                "ip" : {
                    "verbose" : "+",
                    "list" : [],
                    "cc" : []
                }
            },
            "rdep" : {
                "ip" : {
                    "verbose" : "+",
                    "list" : [],
                    "cc" : []
                }
            }
        }
        '''
        ok = 0
        try:
            options = ExtArgsOptions()
            options.errorhandler = 'raise'
            parser = ExtKeyParse(options)
            parser.load_command_line_string(commandline)
            args = parser.parse_command_line(['dep','cc'])
        except:
            ok = 1
        self.assertEqual(ok,1)
        return

    def test_A029(self):
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
                "list|l!attr=cc;optfunc=list_opt_func!" : [],
                "string|s" : "s_var",
                "$" : "+",
                "ip" : {
                    "verbose" : "+",
                    "list" : [],
                    "cc" : []
                }
            },
            "rdep" : {
                "ip" : {
                    "verbose" : "+",
                    "list" : [],
                    "cc" : []
                }
            }
        }
        '''
        options = ExtArgsOptions()
        options.helphandler = 'nohelp'
        parser = ExtArgsParse(options)
        parser.load_command_line_string(commandline)
        sio = StringIO.StringIO()
        parser.print_help(sio)
        self.assertEqual(sio.getvalue(),'no help information')
        return

    def test_A030(self):
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
            "dep<dep_handler>!opt=cc!" : {
                "list|l!attr=cc;optfunc=list_opt_func!" : [],
                "string|s" : "s_var",
                "$" : "+",
                "ip" : {
                    "verbose" : "+",
                    "list" : [],
                    "cc" : []
                }
            },
            "rdep<rdep_handler>" : {
                "ip" : {
                    "verbose" : "+",
                    "list" : [],
                    "cc" : []
                }
            }
        }
        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        flag = parser.get_cmdkey(None)
        self.assertEqual(flag.iscmd,True)
        self.assertEqual(flag.cmdname,'main')
        self.assertEqual(flag.function,None)
        flag = parser.get_cmdkey('dep')
        self.assertEqual(flag.cmdname,'dep')
        self.assertEqual(flag.function,'dep_handler')
        self.assertEqual(flag.attr.opt,'cc')
        flag = parser.get_cmdkey('rdep')
        self.assertEqual(flag.function,'rdep_handler')
        self.assertEqual(flag.attr,None)
        flag = parser.get_cmdkey('nosuch')
        self.assertEqual(flag,None)
        return

    def test_A031(self):
        inner_command='''
        {
            "verbose|v" : "+",
            "catch|C## to not catch the exception ##" : true,
            "input|i## to specify input default(stdin)##" : null,
            "$caption## set caption ##" : "runcommand",
            "test|t##to test mode##" : false,
            "release|R##to release test mode##" : false,
            "$" : "*"
        }
        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(inner_command)
        args = parser.parse_command_line(['--test'])
        self.assertEqual(args.test,True)
        self.assertEqual(args.args,[])
        return

    def __get_tab_line(self,fmt,tabs=0):
        s = ' ' * tabs * 4
        s += fmt
        s += '\n'
        return s

    def __slash_string(self,s):
        outs =''
        for c in s:
            if c == '\\':
                outs += '\\\\'
            else:
                outs += c
        return outs

    def __write_out_scripts(self,options):
        EXTARGS_RELEASE_MODE=False
        if not EXTARGS_RELEASE_MODE:
            curdir = os.path.dirname(os.path.abspath(__file__))
            curfile = os.path.basename(__file__)
            sarr = re.split('\.',curfile)
            if len(sarr) > 1:
                # remove last
                sarr.pop()
            curfilenoext = '.'.join(sarr)
        scripts = ''
        scripts += self.__get_tab_line('#! /usr/bin/env python',0)
        scripts += self.__get_tab_line('import sys',0)
        scripts += self.__get_tab_line('import os',0)
        scripts += self.__get_tab_line('def _release_path_test(curpath,*paths):',0)
        scripts += self.__get_tab_line('testfile = os.path.join(curpath,*paths)',1)
        scripts += self.__get_tab_line('if os.path.exists(testfile):',1)
        scripts += self.__get_tab_line('if curpath != sys.path[0]:',2)
        scripts += self.__get_tab_line('if curpath in sys.path:',3)
        scripts += self.__get_tab_line('sys.path.remove(curpath)',4)
        scripts += self.__get_tab_line('oldpath=sys.path',3)
        scripts += self.__get_tab_line('sys.path = [curpath]',3)
        scripts += self.__get_tab_line('sys.path.extend(oldpath)',3)
        scripts += self.__get_tab_line('return',1)
        scripts += self.__get_tab_line('')
        scripts += self.__get_tab_line('')
        if not EXTARGS_RELEASE_MODE:
            scripts += self.__get_tab_line('def _reload_extargs_debug_path(curpath):',0)
            scripts += self.__get_tab_line('return _release_path_test(curpath,\'%s\')'%(curfile),1)
            scripts += self.__get_tab_line('')
            scripts += self.__get_tab_line('_reload_extargs_debug_path(\'%s\')'%(self.__slash_string(curdir)),0)        
            scripts += self.__get_tab_line('')
            scripts += self.__get_tab_line('import %s as extargsparse'%(curfilenoext),0)
        else:
            scripts += self.__get_tab_line('def _reload_extargs_path(curpath):',0)
            scripts += self.__get_tab_line('return _release_path_test(curpath,\'extargsparse\',\'__init__.py\')',1)
            curdir = os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..')
            scripts += self.__get_tab_line('_reload_extargs_path(\'%s\')'%(self.__slash_string(curdir)),0)
            scripts += self.__get_tab_line('import extargsparse')
        scripts += self.__get_tab_line('')
        scripts += self.__get_tab_line('def main():',0)
        scripts += self.__get_tab_line('commandline=\'\'',1)
        sarr = re.split('\n',options)
        i = 0
        for l in sarr:
            i += 1
            l = l.rstrip('\r\n')
            scripts += self.__get_tab_line('commandline += \'%s\\n\''%(l),1)
        if not EXTARGS_RELEASE_MODE:
            scripts += self.__get_tab_line('options = extargsparse.ExtArgsOptions()',1)
            scripts += self.__get_tab_line('parser = extargsparse.ExtArgsParse(options)',1)
        else:
            scripts += self.__get_tab_line('options = ExtArgsOptions()',1)
            scripts += self.__get_tab_line('parser = ExtArgsParse(options)',1)
        scripts += self.__get_tab_line('parser.load_command_line_string(commandline)',1)
        scripts += self.__get_tab_line('args = parser.parse_command_line()',1)
        scripts += self.__get_tab_line('return',1)
        scripts += self.__get_tab_line('')
        scripts += self.__get_tab_line('if __name__ == \'__main__\':')
        scripts += self.__get_tab_line('main()',1)
        scripts += self.__get_tab_line('')
        self.info('scripts (\n%s\n)'%(scripts))
        fd,tempf = tempfile.mkstemp(suffix='.py',prefix='exthelp',dir=None,text=True)
        os.close(fd)
        with open(tempf,'w+') as fout:
            fout.write('%s\n'%(scripts))
        return tempf




    def __get_cmd_output(self,cmd,output=None):
        self.info('run (%s)'%(cmd))
        origextargs = None
        outputc = output
        if 'EXTARGSPARSE_LOGLEVEL' in os.environ.keys():
            origextargs = os.environ['EXTARGSPARSE_LOGLEVEL']
            os.environ['EXTARGSPARSE_LOGLEVEL'] = '0'
        try:
            if outputc is None:
                fd,outputc = tempfile.mkstemp(suffix='.py',prefix='exthelp',dir=None,text=True)
                os.close(fd)
            runcmd = '%s > %s'%(cmd,outputc)
            exitcode = subprocess.call(runcmd,shell=True)
            s = ''
            with open(outputc,'r') as fin:
                for l in fin:
                    s += l
        finally:
            if output is None and outputc is not None:
                os.remove(outputc)
            outputc = None
            if origextargs is None:
                os.environ['EXTARGSPARSE_LOGLEVEL'] = '0'
            else:
                os.environ['EXTARGSPARSE_LOGLEVEL'] = origextargs
        return exitcode,s


    def test_A032(self):
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
            "dep<dep_handler>!opt=cc!" : {
                "list|l!attr=cc;optfunc=list_opt_func!" : [],
                "string|s" : "s_var",
                "$" : "+",
                "ip" : {
                    "verbose" : "+",
                    "list" : [],
                    "cc" : []
                }
            },
            "rdep<rdep_handler>" : {
                "ip" : {
                    "verbose" : "+",
                    "list" : [],
                    "cc" : []
                }
            }
        }
        '''
        tempf = None
        try:
            tempf = self.__write_out_scripts(commandline)
            cmd = 'python %s -h'%(tempf)
            exitcode,output = self.__get_cmd_output(cmd)
            self.assertEqual(exitcode,0)
            sarr = self.__split_strings(output)
            parser = ExtArgsParse()
            parser.load_command_line_string(commandline)
            opts = parser.get_cmdopts()
            for opt in opts:
                self.assertEqual(self.__get_opt_ok(sarr,opt),True)


            cmd = 'python %s dep -h'%(tempf)
            exitcode,output = self.__get_cmd_output(cmd)
            self.assertEqual(exitcode,0)
            sarr = self.__split_strings(output)
            parser = ExtArgsParse()
            parser.load_command_line_string(commandline)
            opts = parser.get_cmdopts('dep')
            for opt in opts:
                self.assertEqual(self.__get_opt_ok(sarr,opt),True)

            cmd = 'python %s rdep -h'%(tempf)
            exitcode,output = self.__get_cmd_output(cmd)
            self.assertEqual(exitcode,0)
            sarr = self.__split_strings(output)
            parser = ExtArgsParse()
            parser.load_command_line_string(commandline)
            opts = parser.get_cmdopts('rdep')
            for opt in opts:
                self.assertEqual(self.__get_opt_ok(sarr,opt),True)

        finally:
            if tempf is not None:
                os.remove(tempf)
            tempf = None
        return


    def test_A033(self):
        test_reserved_args = ['subcommand','subnargs','json','nargs','extargs','help','args']
        cmd1_fmt= '''
        {
            "%s" : true
        }
        '''
        cmd2_fmt= '''
        {
            "+%s" : {
                "reserve": true
            }
        }
        '''
        cmd3_fmt= '''
        {
            "%s" : {
                "function" : 30
            }
        }
        '''
        cmdfmts = [cmd1_fmt,cmd2_fmt,cmd3_fmt]
        for fmt in cmdfmts:
            for k in test_reserved_args:
                commandline = fmt%(k)
                options = ExtArgsOptions()
                options.errorhandler = 'raise'
                parser = ExtArgsParse(options)
                ok = 0
                try:
                    parser.load_command_line_string(commandline)
                except:
                    ok = 1
                self.assertEqual(ok,1)
        return

    def test_A034(self):
        commandline='''
        {
            "dep" : {
                "string|S" : "stringval"
            }
        }
        '''
        depjson = None
        ok = False
        try:
            parser = ExtArgsParse()
            parser.load_command_line_string(commandline)
            fd,depjson = tempfile.mkstemp(suffix='.json',prefix='dep',dir=None,text=True)
            os.close(fd)
            with open(depjson,'w') as fout:
                fout.write('{"dep_string":null}')
            args = parser.parse_command_line(['--json',depjson, 'dep'])
            self.assertEqual(args.dep_string,None)
            self.assertEqual(args.subcommand,'dep')
            self.assertEqual(args.subnargs,[])
            ok = True
        finally:
            if ok :
                os.remove(depjson)
            else:
                self.error('depjson %s error'%(depjson))
            depjson = None
        return

    def test_A035(self):
        commandline = '''
        {
            "float1|f" : 3.633 ,
            "float2" : 6422.22,
            "float3" : 44463.23,
            "verbose|v" : "+",
            "dep" : {
                "float3" : 3332.233
            },
            "rdep" : {
                "ip" : {
                    "float4" : 3377.33,
                    "float6" : 33.22,
                    "float7" : 0.333
                }
            }

        }
        '''
        depjsonfile = None
        rdepjsonfile = None
        rdepipjsonfile = None
        jsonfile = None
        ok = False
        try:
            depjsonfile = self.__write_temp_file('{"float3":33.221}')
            rdepjsonfile = self.__write_temp_file('{"ip" : { "float4" : 40.3}}')
            jsonfile = self.__write_temp_file('{"verbose": 30,"float3": 77.1}')
            rdepipjsonfile = self.__write_temp_file('{"float7" : 11.22,"float4" : 779.2}')
            env = dict()
            os.environ['EXTARGSPARSE_JSON'] = jsonfile
            os.environ['DEP_JSON'] = depjsonfile
            os.environ['RDEP_JSON'] = rdepjsonfile
            os.environ['DEP_FLOAT3'] = '%s'%(33.52)
            os.environ['RDEP_IP_FLOAT7'] = '%s'%(99.3)
            parser = ExtArgsParse()
            parser.load_command_line_string(commandline)
            args = parser.parse_command_line(['-vvfvv','33.21','rdep','ip','--json',jsonfile,'--rdep-ip-json',rdepipjsonfile])
            self.assertEqual(len(args.subnargs),0)
            self.assertEqual(args.subcommand,'rdep.ip')
            self.assertEqual(args.verbose,4)
            self.assertEqual(args.float1,33.21)
            self.assertEqual(args.dep_float3,33.52)
            self.assertEqual(args.float2,6422.22)
            self.assertEqual(args.float3,77.1)
            self.assertEqual(args.rdep_ip_float4,779.2)
            self.assertEqual(args.rdep_ip_float6,33.22)
            self.assertEqual(args.rdep_ip_float7,11.22)
            ok = True
        finally:
            self.__remove_file_ok(depjsonfile,'depjsonfile',ok)
            self.__remove_file_ok(rdepjsonfile,'rdepjsonfile',ok)
            self.__remove_file_ok(rdepipjsonfile,'rdepipjsonfile',ok)
            self.__remove_file_ok(jsonfile,'jsonfile',ok)
            depjsonfile = None
            rdepjsonfile = None
            rdepipjsonfile = None
            jsonfile = None
        return

    def test_A036(self):
        commandline='''
        {
            "jsoninput|j##input json default stdin##" : null,
            "input|i##input file to get default nothing - for stdin##" : null,
            "output|o##output c file##" : null,
            "verbose|v##verbose mode default(0)##" : "+",
            "cmdpattern|c" : "%EXTARGS_CMDSTRUCT%",
            "optpattern|O" : "%EXTARGS_STRUCT%", 
            "structname|s" : "args_options_t",
            "funcname|F" : "debug_extargs_output",
            "releasename|R" : "release_extargs_output",
            "funcpattern" : "%EXTARGS_DEBUGFUNC%",
            "prefix|p" : "",
            "test" : {
                "$" : 0
            },
            "optstruct" : {
                "$" : 0
            },
            "cmdstruct" : {
                "$" : 0
            },
            "debugfunc" : {
                "$" : 0
            },
            "all" : {
                "$" : 0
            }
        }
        '''
        options = ExtArgsOptions()
        options.errorhandler = 'raise'
        parser = ExtArgsParse(options)
        parser.load_command_line_string(commandline)
        ok = 0
        oldstdout = sys.stdout
        oldstderr = sys.stderr
        uname0 = platform.uname()[0].lower()
        try:
            if uname0 == 'linux' or uname0.startswith('cygwin'):
                sys.stdout = open('/dev/null','w')
                sys.stderr = open('/dev/null','w')
            elif uname0 == 'windows':
                sys.stdout = open('NUL','w')
                sys.stderr = open('NUL','w')
            else:
                raise Exception('can not find platform %s'%(uname0))
            args =parser.parse_command_line(['--help'])
        except SystemExit:
            ok = 1
        finally:
            if sys.stdout != oldstdout:
                sys.stdout.close()
            sys.stdout = oldstdout
            if sys.stderr != oldstderr:
                sys.stderr.close()
            sys.stderr = oldstderr
        self.assertEqual(ok,1)
        return

    def test_A037(self):
        commandline='''
        {
            "jsoninput|j##input json default stdin##" : null,
            "input|i##input file to get default nothing - for stdin##" : null,
            "output|o##output c file##" : null,
            "verbose|v##verbose mode default(0)##" : "+",
            "cmdpattern|c" : "%EXTARGS_CMDSTRUCT%",
            "optpattern|O" : "%EXTARGS_STRUCT%", 
            "structname|s" : "args_options_t",
            "funcname|F" : "debug_extargs_output",
            "releasename|R" : "release_extargs_output",
            "funcpattern" : "%EXTARGS_DEBUGFUNC%",
            "prefix|p" : "",
            "test" : {
                "$" : 0
            },
            "optstruct" : {
                "$" : 0
            },
            "cmdstruct" : {
                "$" : 0
            },
            "debugfunc" : {
                "$" : 0
            },
            "all" : {
                "$" : 0
            }
        }
        '''
        options = ExtArgsOptions()
        options.errorhandler = 'raise'
        parser = ExtArgsParse(options)
        parser.load_command_line_string(commandline)
        subcommands = parser.get_subcommands()
        self.assertEqual(len(subcommands),5)
        self.assertEqual(subcommands[0],'all')
        self.assertEqual(subcommands[1],'cmdstruct')
        self.assertEqual(subcommands[2],'debugfunc')
        self.assertEqual(subcommands[3],'optstruct')
        self.assertEqual(subcommands[4],'test')
        cmdopts = parser.get_cmdopts()
        self.assertEqual(len(cmdopts),14)
        self.assertEqual(cmdopts[0].flagname,'$')
        self.assertEqual(cmdopts[1].longopt,'--cmdpattern')
        self.assertEqual(cmdopts[2].optdest,'funcname')
        self.assertEqual(cmdopts[3].varname,'funcpattern')
        self.assertEqual(cmdopts[4].type,'help')
        return

    def test_A038(self):
        commandline='''
        {
            "verbose|v" : "+",
            "kernel|K" : "/boot/",
            "initrd|I" : "/boot/",
            "encryptfile|e" : null,
            "encryptkey|E" : null,
            "setupsectsoffset" : 0x1f1,
            "ipxe<ipxe_handler>" : {
                "$" : "+"
            }
        }
        '''
        ok = 0
        parser = ExtArgsParse()
        # to indirect the code
        errfile = None
        errfile = sys.stderr
        sys.stderr = open(os.devnull,'w')
        try:
            parser.load_command_line_string(commandline)
        except:
            ok = 1
        if errfile is not None:
            if sys.stderr != errfile:
                sys.stderr.close()
                sys.stderr = errfile
            errfile = None
        self.assertEqual(ok,1)
        return

    def test_A039(self):
        commandline='''
        {
            "verbose|v" : "+",
            "kernel|K" : "/boot/",
            "initrd|I" : "/boot/",
            "encryptfile|e" : null,
            "encryptkey|E" : null,
            "setupsectsoffset" : 451
        }
        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        os.environ['EXTARGS_VERBOSE'] = '4'
        os.environ['EXTARGS_SETUPSECTSOFFSET'] = '0x612'
        args = parser.parse_command_line([],None)
        self.assertEqual(args.verbose,4)
        self.assertEqual(args.setupsectsoffset,0x612)
        return

    def test_A040(self):
        commandline='''
        {
            "+tce": {
                "mirror": "http://repo.tinycorelinux.net",
                "root": "/",
                "tceversion": "7.x",
                "wget": "wget",
                "cat": "cat",
                "rm": "rm",
                "sudoprefix": "sudo",
                "optional_dir": "/cde",
                "trymode": false,
                "platform": "x86_64",
                "mount": "mount",
                "umount": "umount",
                "chroot": "chroot",
                "chown": "chown",
                "chmod": "chmod",
                "mkdir": "mkdir",
                "rollback": true,
                "cp": "cp",
                "jsonfile": null,
                "perspace": 3,
                "depmapfile": null,
                "timeout": 10,
                "listsfile": null,
                "maxtries": 5
            }
        }        '''
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        args = parser.parse_command_line(['--tce-root','/home/'])
        tcebase = debug_tcebase()
        set_attr_args(tcebase,args,'tce')
        self.assertEqual(tcebase.tce_mirror,'http://repo.tinycorelinux.net')
        self.assertEqual(tcebase.tce_root,'/home/')
        self.assertEqual(tcebase.tce_listsfile,None)
        self.assertEqual(tcebase.tce_maxtries,5)
        self.assertEqual(tcebase.tce_timeout,10)
        return

    def test_A041(self):
        commandline_fmt='''
        {
            "countryname|N" : "CN",
            "statename|S" : "ZJ",
            "localityname" : "HZ",
            "organizationname|O" : ["BT"],
            "organizationunitname" : "BT R&D",
            "commonname|C" : "bingte.com",
            "+ssl" : {
                "chain" : true,
                "dir" : "%s",
                "bits" : 4096,
                "md" : "sha256",
                "utf8" : true,
                "name" : "ipxe",
                "days" : 3650,
                "crl-days": 365,
                "emailaddress" : "bt@bingte.com",
                "aia_url" : "http://bingte.com/sec/aia",
                "crl_url" : "http://bingte.com/sec/crl",
                "ocsp_url" : "http://bingte.com/sec/ocsp",
                "dns_url" : ["bingte.com"],
                "excluded_ip" : ["0.0.0.0/0.0.0.0","0:0:0:0:0:0:0:0/0:0:0:0:0:0:0:0"],
                "password|P" : null,
                "copy_extensions" : "none",
                "subca" : false,
                "comment": ""
            }
        }
        '''
        curdir = os.path.abspath(os.path.dirname(__file__))
        curdir = os.path.join(curdir,'certs')
        curdir = curdir.replace('\\','\\\\')
        commandline = commandline_fmt%(curdir)
        parser = ExtArgsParse()
        parser.load_command_line_string(commandline)
        jsonfile = None
        ok = False
        rootloggerhandler = None
        oldsyserr = None
        oldsyserr = sys.stderr
        sys.stderr = open(os.devnull,'w+')
        oldloggers = None
        oldpropgate = 1
        logger = logging.getLogger('extargsparse')
        if len(logger.handlers) > 0:
            oldloggers = []
            for h in logger.handlers:
                oldloggers.append(h)
            logger.handlers = []
            handler = logging.FileHandler(os.devnull,mode='a')
            logger.handlers.append(handler)
            # we set propagate ,will not exposed
            oldpropgate = logger.propagate
            logger.propagate = 0
        rootlogger = logging.RootLogger(logging.WARN)
        if len(rootlogger.handlers) > 0:
            rootloggerhandler = []
            for h in rootloggerhandler.handlers:
                rootloggerhandler.append(h)
            rootlogger.handlers = []
            handler = logging.FileHandler(os.devnull,mode='a')
            rootlogger.handlers.append(handler)
        try:
            jsonfile = self.__write_temp_file('{"emailaddress" : "unit@bingte.com","organizationname" : "BT RD","ssl" :{ "dir" : "./certs/bingte","name" : "bingte","subca" : true,"copy_extensions" : "copy","days" : 375,"crl_days" : 30,"bits" : 4096}}')

            args = parser.parse_command_line(['--json',jsonfile],parser)
            if oldloggers is not None:
                logger = logging.getLogger('extargsparse')
                for h in logger.handlers:
                    h.close()
                logger.handlers = []
                for h in oldloggers:
                    logger.handlers.append(h)
                oldloggers = None
                if oldpropgate is not None:
                    logger.propagate = oldpropgate
                    oldpropgate = None
            if oldsyserr is not None:
                sys.stderr.close()
                sys.stderr = None
                sys.stderr = oldsyserr
                oldsyserr = None
            if rootloggerhandler is not None:
                rootlogger = logging.RootLogger(logging.WARN)
                for h in rootlogger.handlers:
                    h.close()
                rootlogger.handlers = []
                for h in rootloggerhandler:
                    rootlogger.handlers.append(h)
                rootloggerhandler = None
            ok = True
            self.assertEqual(ok,True)
            logging.info('organizationunitname (%s)'%(args.organizationname))
            self.assertEqual(len(args.organizationname),1)
            self.assertEqual(args.organizationname[0],'BT')
        finally:
            self.__remove_file_ok(jsonfile,'jsonfile',ok)
            jsonfile = None
            if oldloggers is not None:
                logger = logging.getLogger('extargsparse')
                for h in logger.handlers:
                    h.close()
                logger.handlers = []
                for h in oldloggers:
                    logger.handlers.append(h)
                oldloggers = None
                if oldpropgate is not None:
                    logger.propagate = oldpropgate
                    oldpropgate = None
            if oldsyserr is not None:
                sys.stderr.close()
                sys.stderr = None
                sys.stderr = oldsyserr
                oldsyserr = None
            if rootloggerhandler is not None:
                rootlogger = logging.RootLogger(logging.WARN)
                for h in rootlogger.handlers:
                    h.close()
                rootlogger.handlers = []
                for h in rootloggerhandler:
                    rootlogger.handlers.append(h)
                rootloggerhandler = None
        return


##importdebugstart

def debug_release():
    if '-v' in sys.argv[1:]:
        #sys.stderr.write('will make verbose\n')
        loglvl =  logging.DEBUG
        logging.basicConfig(level=loglvl,format='%(asctime)s:%(filename)s:%(funcName)s:%(lineno)d\t%(message)s')
    tofile=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','extargsparse','__lib__.py'))
    if len(sys.argv) > 2:
        for k in sys.argv[1:]:
            if not k.startswith('-'):
                tofile = k
                break
    repls = dict()
    repls[r'__key_debug__'] = r'__key__'
    #logging.info('repls %s'%(repls.keys()))
    disttools.release_file('__main__',tofile,[r'^debug_*'],[[r'##importdebugstart.*',r'##importdebugend.*']],[],repls)
    return

def debug_main():
    if '--release' in sys.argv[1:]:
        debug_release()
        return
    if '-v' in sys.argv[1:] or '--verbose' in sys.argv[1:]:
        os.environ['EXTARGSPARSE_LOGLEVEL'] = '4'
        loglvl =  logging.DEBUG
        logging.basicConfig(level=loglvl,format='%(asctime)s:%(filename)s:%(funcName)s:%(lineno)d\t%(message)s')
    unittest.main()

if __name__ == '__main__':
    debug_main()  
##importdebugend