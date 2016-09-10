
set script_dir=%~dpD0
set cur_dir=%CD%
cd %script_dir% && python setup.py register && python setup.py sdist upload && cd %cur_dir% || cd %cur_dir%