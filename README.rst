AgentZero 0.3.3 - high-level ZeroMQ socket managers
===================================================

.. image:: https://readthedocs.org/projects/agentzero/badge/?version=latest
   :target: http://agentzero.readthedocs.io/en/latest/?badge=latest

.. image:: https://travis-ci.org/gabrielfalcao/agentzero.svg?branch=master
   :target: https://travis-ci.org/gabrielfalcao/agentzero
   
.. image:: https://codecov.io/gh/gabrielfalcao/agentzero/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/gabrielfalcao/agentzero


AgentZero lets you create, connect, bind, and modify zeromq sockets in
runtime with ease.

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

installing
==========

.. code:: bash

    pip install agentzero

basic usage
===========

.. code:: python
