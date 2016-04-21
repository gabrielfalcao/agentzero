#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright © 2015 Canary Connect Inc.

import ast
import os
from setuptools import setup, find_packages


local_file = lambda *f: \
    open(os.path.join(os.path.dirname(__file__), *f)).read()


class VersionFinder(ast.NodeVisitor):
    VARIABLE_NAME = 'version'

    def __init__(self):
        self.version = None

    def visit_Assign(self, node):
        try:
            if node.targets[0].id == self.VARIABLE_NAME:
                self.version = node.value.s
        except:
            pass


def read_version():
    finder = VersionFinder()
    finder.visit(ast.parse(local_file('agentzero', 'version.py')))
    return finder.version


dependencies = [
    'coloredlogs==3.1.4',
    'gevent==1.0.2',
    'milieu==0.1.8',
    'pyzmq==15.0.0',
    'jsonschema==2.5.1',
    'requests==2.7.0',
    'plant==0.1.2',
    'psutil==3.2.2',
    'Flask==0.10.1',
    'Flask-SocketIO==0.6.0',
    'PyNaCl==0.3.0',
    'redis==2.10.5',
    'tabulate==0.7.5',
    'dj-redis-url==0.1.4',
    'argcomplete==1.1.0',
]


setup(
    name='agentzero',
    version=read_version(),
    description='AgentZero',
    entry_points={
        'console_scripts': ['agentzero = agentzero.console.main:entrypoint'],
    },
    author='Gabriel Falcao',
    author_email='gabriel@canary.is',
    url='http://canary.is',
    packages=find_packages(exclude=['*tests*']),
    install_requires=dependencies,
    include_package_data=True,
    package_data={
        'agentzero': 'COPYING *.md agentzero/web agentzero/web/* agentzero/web/dist agentzero/web/dist/* agentzero/web/templates agentzero/web/templates/*'.split(),
    },
    zip_safe=False,
)
