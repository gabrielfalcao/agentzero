AgentZero 0.4.6 - high-level ZeroMQ socket managers
===================================================

.. image:: https://img.shields.io/pypi/dm/agentzero
   :target: https://pypi.org/project/agentzero

.. image:: https://img.shields.io/codecov/c/github/gabrielfalcao/agentzero
   :target: https://codecov.io/gh/gabrielfalcao/agentzero

.. image:: https://img.shields.io/github/workflow/status/gabrielfalcao/agentzero/python-3.6?label=python%203.6.8
   :target: https://github.com/gabrielfalcao/agentzero/actions

.. image:: https://img.shields.io/github/workflow/status/gabrielfalcao/agentzero/python-3.7?label=python%203.7.5
   :target: https://github.com/gabrielfalcao/agentzero/actions

.. image:: https://img.shields.io/readthedocs/agentzero
   :target: https://agentzero.readthedocs.io/

.. image:: https://img.shields.io/github/license/gabrielfalcao/agentzero?label=Github%20License
   :target: https://github.com/gabrielfalcao/agentzero/blob/master/LICENSE

.. image:: https://img.shields.io/pypi/v/agentzero
   :target: https://pypi.org/project/agentzero

.. image:: https://img.shields.io/pypi/l/agentzero?label=PyPi%20License
   :target: https://pypi.org/project/agentzero

.. image:: https://img.shields.io/pypi/format/agentzero
   :target: https://pypi.org/project/agentzero

.. image:: https://img.shields.io/pypi/status/agentzero
   :target: https://pypi.org/project/agentzero

.. image:: https://img.shields.io/pypi/pyversions/agentzero
   :target: https://pypi.org/project/agentzero

.. image:: https://img.shields.io/pypi/implementation/agentzero
   :target: https://pypi.org/project/agentzero

.. image:: https://img.shields.io/snyk/vulnerabilities/github/gabrielfalcao/agentzero
   :target: https://github.com/gabrielfalcao/agentzero/network/alerts

.. image:: https://img.shields.io/github/v/tag/gabrielfalcao/agentzero
   :target: https://github.com/gabrielfalcao/agentzero/releases

**Supports Python 2.7 and 3.6**

Looking for `documentation <https://agentzero.readthedocs.io/en/latest/>`_ ?


What is AgentZero ?
-------------------

AgentZero is a pluripotent networking library that lets you create,
connect, bind, and modify ZeroMQ sockets in runtime with ease.

It works great with gevent, making it possible to create network
applications with simple code that performs complex operations.


Features:
---------

-  Create labeled sockets, every ZMQ socket in AgentZero has a name.
-  seamlessly poll across connected/bound sockets
-  seamlessly subscribe to events
-  easily publish events
-  bind sockets to random ports automatically
-  bind to hostnames, with automatic DNS resolution
-  ability to wait until a socket has received data
-  builtin python log handler that publishes logs in a ZMQ PUB socket

Installing
==========

.. code:: bash

    pip install agentzero


Learn More
==========

`API Reference <https://agentzero.readthedocs.io/en/latest/api-reference.html>`_
