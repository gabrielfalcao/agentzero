# -*- coding: utf-8 -*-

import sys


def only_py2(func):
    def test_ignore_python3(*args, **kw):
        "ignored python 3 test"

    if sys.version_info[0] == 2:
        return func
    else:
        return test_ignore_python3


def only_py3(func):
    def test_ignore_python2(*args, **kw):
        "ignored python 2 test"

    if sys.version_info[0] == 3:
        return func
    else:
        return test_ignore_python2
