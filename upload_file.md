# how to upload
*  python3 setup.py sdist bdist_wheel   # to create the dist/* files
*  twine upload --repository-url https://upload.pypi.org/legacy/ dist/* # to upload the file later set username and password ok
