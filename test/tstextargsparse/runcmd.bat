
python format_template.py -i shellout.py.tmpl -P "%%EXTARGSPARSE_STRIP_CODE%%" -r "keyparse\.=" -c ExtArgsParse.get_subcommands -c ExtArgsParse.get_cmdopts -E __cached__ -E __file__ -E __name__ -E call_args_function -E __package__ -E UnitTestCase -E main -E ExtArgsTestCase -vvvv -o shellout.py extargsparse.__key__ extargsparse.__lib__