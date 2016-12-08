#! /usr/bin/env python

import sys
import os
_extargs_parent_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)),'..','..'))
if _extargs_parent_dir not in sys.path:
    _temp_path = sys.path
    sys.path = [_extargs_parent_dir]
    sys.path.extend(_temp_path)

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

def debug_cmd_opts(parser,name=''):
    opts = parser.get_cmdopts(name)
    if opts is not None :
        for opt in opts:
            if opt.type == 'args':
                continue
            print('[%s] opt %s'%(name,opt.longopt))
    subcmds = parser.get_subcommands(name)
    if subcmds is not None:
        print('[%s] subcmds %s'%(name,subcmds))
    return subcmds

def debug_total(parser,name=''):
    subcmds = debug_cmd_opts(parser,name)
    if subcmds is not None and len(subcmds) > 0:
        for c in subcmds:
            cname = ''
            cname += '%s'%(name)
            if len(cname) > 0:
                cname += '.'
            cname += '%s'%(c)
            debug_total(parser,cname)
    return

def main():
    parser = extargsparse.ExtArgsParse()
    parser = load_s_1(parser)
    parser = load_s_2(parser)
    parser.end_options()
    debug_total(parser)
    return

if __name__ == '__main__':
  main()  
