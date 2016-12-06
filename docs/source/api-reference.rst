.. _API Reference:

.. AgentZero documentation master file, created by
   sphinx-quickstart on Thu Nov 26 03:24:20.0.2.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Internals Reference
===================


SocketManager
-------------


.. autoclass:: agentzero.SocketManager

create
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.create

get_by_name
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.get_by_name

get_or_create
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.get_or_create

register_socket
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.register_socket

bind
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.bind

ensure_and_bind
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.ensure_and_bind

bind_to_random_port
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.bind_to_random_port

connect
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.connect

ensure_and_connect
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.ensure_and_connect

engage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.engage

send_safe
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.send_safe

recv_safe
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.recv_safe

recv_event_safe
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.recv_event_safe

subscribe
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.subscribe

set_socket_option
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.set_socket_option

set_topic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.set_topic

publish_safe
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.publish_safe

ready
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.ready

wait_until_ready
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.wait_until_ready

ready
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.ready

get_log_handler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.get_log_handler

get_logger
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.get_logger

close
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: agentzero.SocketManager.close


Utility Functions
-----------------

get_free_tcp_port
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: agentzero.util.get_free_tcp_port


get_default_bind_address
~~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: agentzero.util.get_default_bind_address

get_public_ip_address
~~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: agentzero.util.get_public_ip_address


extract_hostname_from_tcp_address
~~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: agentzero.util.extract_hostname_from_tcp_address


resolve_hostname
~~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: agentzero.util.resolve_hostname


fix_zeromq_tcp_address
~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: agentzero.util.fix_zeromq_tcp_address


get_public_zmq_address
~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: agentzero.util.get_public_zmq_address


seconds_since
~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: agentzero.util.seconds_since


datetime_from_seconds
~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: agentzero.util.datetime_from_seconds


serialized_exception
~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: agentzero.util.serialized_exception


Exceptions
----------


AgentZeroSocketError
~~~~~~~~~~~~~~~~~~~~

.. autoexception:: agentzero.errors.AgentZeroSocketError
   :members:

SocketAlreadyExists
~~~~~~~~~~~~~~~~~~~~

.. autoexception:: agentzero.errors.SocketAlreadyExists
   :members:

SocketNotFound
~~~~~~~~~~~~~~~~~~~~

.. autoexception:: agentzero.errors.SocketNotFound
   :members:


SocketBindError
~~~~~~~~~~~~~~~~~~~~

.. autoexception:: agentzero.errors.SocketBindError
   :members:


SocketConnectError
~~~~~~~~~~~~~~~~~~~~

.. autoexception:: agentzero.errors.SocketConnectError
   :members:



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
