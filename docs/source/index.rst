.. AgentZero documentation master file, created by
   sphinx-quickstart on Thu Nov 26 03:24:20.0.2.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

AgentZero - high-level ZeroMQ socket managers
=============================================

AgentZero lets you create, connect, bind, and modify zeromq sockets in runtime with ease.

It works great with gevent, making it possible to create network
applications with simple code that performs complex operations.


Features:
---------

* Create labeled sockets, every ZMQ socket in AgentZero has a name.
* seamlessly poll across connected/bound sockets
* seamlessly subscribe to events, which return the boxed type: :py:class:`~agentzero.core.Event`
* easily publish events
* bind sockets to random ports automatically
* bind to hostnames, with automatic DNS resolution
* ability to wait until a socket has received data
* builtin python log handler that publishes logs in a ZMQ PUB socket

**Bonus:**

Contents:

.. toctree::
   :maxdepth: 3

   api-reference


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
