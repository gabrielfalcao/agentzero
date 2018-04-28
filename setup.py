#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup, find_packages


local_file = lambda *f: \
    open(os.path.join(os.path.dirname(__file__), *f)).read()


def read_version():
    ctx = {}
    exec(local_file('agentzero', 'version.py'), ctx)
    return ctx['version']


dependencies = [
    'pyzmq==16.0.2',
    'msgpack==0.5.6',
    'six==1.11.0',
]


setup(
    name='agentzero',
    version=read_version(),
    description="\n".join([
        'AgentZero lets you create, connect, bind, and modify zeromq sockets in runtime with ease.',
        'It works great with gevent, making it possible to create network applications with simple code that performs complex operations.',
    ]),
    long_description=local_file('README.rst'),
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
