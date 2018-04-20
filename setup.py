#!/usr/bin/env python
# -*- coding: utf-8 -*-


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
    'pyzmq==16.0.2',
]


setup(
    name='agentzero',
    version=read_version(),
    description="\n".join([
        'AgentZero lets you create, connect, bind, and modify zeromq sockets in runtime with ease.',
        'It works great with gevent, making it possible to create network applications with simple code that performs complex operations.',
    ]),
    entry_points={
        'console_scripts': ['agentzero = agentzero.console.main:entrypoint'],
    },
    author='Gabriel Falcao',
    author_email='gabriel@nacaolivre.org',
    url='https://github.com/gabrielfalcao/agentzero',
    packages=find_packages(exclude=['*tests*']),
    install_requires=dependencies,
    include_package_data=True,
    package_data={
        'agentzero': 'COPYING *.md agentzero/web agentzero/web/* agentzero/web/dist agentzero/web/dist/* agentzero/web/templates agentzero/web/templates/*'.split(),
    },
    zip_safe=False,
)
