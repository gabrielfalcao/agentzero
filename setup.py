#!/usr/bin/env python
# -*- coding: utf-8 -*-
import ast
import os
from setuptools import setup, find_packages


def local_file(*f):
    with open(os.path.join(os.path.dirname(__file__), *f), "r") as fd:
        return fd.read()


class VersionFinder(ast.NodeVisitor):
    VARIABLE_NAME = "version"

    def __init__(self):
        self.version = None

    def visit_Assign(self, node):
        try:
            if node.targets[0].id == self.VARIABLE_NAME:
                self.version = node.value.s
        except Exception:
            self.version = None


def read_version():
    finder = VersionFinder()
    finder.visit(ast.parse(local_file("agentzero", "version.py")))
    return finder.version


README = local_file("README.rst")
# print(f"\n{' ' * 10}\n{README}\n{' ' * 10}\n")

setup(
    name="agentzero",
    version=read_version(),
    description="\n".join(
        [
            "AgentZero lets you create, connect, bind, and modify zeromq sockets in runtime with ease.",
            "It works great with gevent, making it possible to create network applications with simple code that performs complex operations.",
        ]
    ),
    long_description=README,
    long_description_content_type='text/x-rst',
    entry_points={
        "console_scripts": ["agentzero = agentzero.console.main:entrypoint"]
    },
    author="Gabriel Falcao",
    author_email="gabriel@nacaolivre.org",
    url="https://github.com/gabrielfalcao/agentzero",
    packages=find_packages(exclude=["*tests*"]),
    install_requires=local_file("requirements.txt").splitlines(),
    python_requires=">=3.6",
    include_package_data=True,
    package_data={
        "agentzero": "COPYING *.rst *.md agentzero/web agentzero/web/* agentzero/web/dist agentzero/web/dist/* agentzero/web/templates agentzero/web/templates/*".split()
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Environment :: MacOS X",
        "Environment :: Handhelds/PDA's",
        "Environment :: Win32 (MS Windows)",
        "Environment :: X11 Applications",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    zip_safe=False,
)
