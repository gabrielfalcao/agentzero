AgentZero 0.4.4 - high-level ZeroMQ socket managers
===================================================

.. image:: https://readthedocs.org/projects/agentzero/badge/?version=latest
   :target: http://agentzero.readthedocs.io/en/latest/?badge=latest

.. image:: https://travis-ci.org/gabrielfalcao/agentzero.svg?branch=master
   :target: https://travis-ci.org/gabrielfalcao/agentzero

.. image:: https://codecov.io/gh/gabrielfalcao/agentzero/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/gabrielfalcao/agentzero

.. image:: https://img.shields.io/badge/Say%20Thanks-!-1EAEDB.svg
   :target: https://saythanks.io/to/gabrielfalcao

**Supports Python 2.7 and 3.6**

Looking for `documentation <https://agentzero.readthedocs.io/en/latest/>`_ ?

--------------------------------------------------------------------------------------

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
