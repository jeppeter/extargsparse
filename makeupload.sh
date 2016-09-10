
script_dir=`dirname $0`
cur_dir=`pwd`
cd $script_dir && python setup.py register && python setup.py sdist upload && cd $cur_dir || cd $cur_dir