#!/usr/bin/python

import argparse
import os
import sys
import json
import logging
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from __lib__ import ExtArgsParse
from __key__ import Utf8Encode

if sys.version[0] == '2':
	del __lib__
	del __key__