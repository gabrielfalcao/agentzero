#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

"""
agentzero.core
~~~~~~~~~~~~~~~

* ``DEFAULT_TIMEOUT_IN_SECONDS``: 1 (seconds)
* ``DEFAULT_POLLING_TIMEOUT``: 1000 (miliseconds)

"""
import zmq
import time
import logging
import collections

from uuid import uuid4

from zmq.error import ZMQError

from agentzero import serializers
from agentzero.errors import SocketNotFound
from agentzero.errors import SocketAlreadyExists
from agentzero.errors import SocketBindError
from agentzero.errors import SocketConnectError
from agentzero.util import cast_bytes

DEFAULT_TIMEOUT_IN_SECONDS = 10

# in miliseconds
DEFAULT_POLLING_TIMEOUT = DEFAULT_TIMEOUT_IN_SECONDS * 1000


class SocketManager(object):
    """High-level abstraction for zeromq's non-blocking api.

    This component provides utility methods to create, retrieve,
    connect and bind sockets by name.

    It can wait for a socket to become available in either receiving
    data, sending data or both at the same time.

    :param zmq: a reference to the zmq module (either from ``import zmq`` or ``import zmq.green as zmq``)
    :param context: the context where the sockets will be created
    :param serialization_backend: an instance of a valid
        :py:class:`agentzero.serializers.BaseSerializer`. This is completely
        optional safe for the cases where you utilize the methods
        ``send_safe`` and ``recv_safe`` when communicating to other
        nodes.
    :param polling_timeout: a **float** - how long to wait for the socket to become available, in miliseconds
    :param timeout: default value passed to :py:meth:`~agentzero.core.SocketManager.engage`

    .. note:: An extra useful feature that comes with using a
      ``SocketManager`` is that you can use a SocketManager to create an
      application that dynamically connects to new nodes based on
      scaling instructions coming from other nodes

    .. warning:: Always use the same context per each thread. If you are
      using gevent, please using a single instance for your whole main
      process, across all greenlets that you manage.

    >>> import zmq
    >>> from agentzero.core import SocketManager
    >>> from agentzero.serializers import JSON
    >>>
    >>> context = zmq.Context()
    >>>
    >>> sockets = SocketManager(zmq, context, serialization_backend=JSON())
    >>> sockets.ensure_and_connect(
    ...      "requester",
    ...      zmq.REQ,
    ...      'tcp://192.168.2.42:5051',
    ...      zmq.POLLIN | zmq.POLLOUT
    ... )
    <zmq.green.core._Socket at ...>
    """

    def __init__(self, zmq, context, serialization_backend=None, polling_timeout=DEFAULT_POLLING_TIMEOUT, timeout=DEFAULT_TIMEOUT_IN_SECONDS):
        self.zmq = zmq
        self.context = context
        # book-keeping of the the sockets themselves
        self.sockets = collections.OrderedDict()
        self.addresses = collections.OrderedDict()
        self.poller = self.zmq.Poller()
        # book-keeping of sockets registered with the poller
        self.registry = collections.OrderedDict()
        self.serialization_backend = serialization_backend or serializers.JSON()

        self.polling_timeout = polling_timeout
        self.timeout = timeout

    def __repr__(self):
        return 'SocketManager(sockets={0})'.format(repr(list(self.sockets.keys())))

    def __del__(self):
        for socket in list(self.sockets.values()):
            try:
                socket.close()
            except (Exception, BaseException):
                pass
        self.addresses.clear()
        self.registry.clear()

        # self.context.destroy()

    def send_safe(self, name, data, *args, **kw):
        """serializes the data with the configured ``serialization_backend``,
        waits for the socket to become available, then sends it over
        through the provided socket name.

        returns ``True`` if the message was sent, or ``False`` if the
        socket never became available.

        .. note::
          you can safely use this function without waiting for a
          socket to become ready, as it already does it for you.

        raises SocketNotFound when the socket name is wrong.

        :param name: the name of the socket where data should be sent through
        :param data: the data to be serialized then sent
        :param ``*args``: args to be passed to wait_until_ready
        :param ``**kw``: kwargs to be passed to wait_until_ready

        """
        socket = self.wait_until_ready(name, self.zmq.POLLOUT, *args, **kw)

        if not socket:
            return False

        payload = self.serialization_backend.pack(data)
        socket.send(payload)

        return True

    def publish_safe(self, name, topic, data):
        """serializes the data with the configured ``serialization_backend``,
        waits for the socket to become available, then sends it to the
        given topic through ``socket.send_multipart``.

        returns ``True`` if the message was sent, or ``False`` if the
        socket never became available.

        .. note::
          you can safely use this function without waiting for a
          socket to become ready, as it already does it for you.

        raises SocketNotFound when the socket name is wrong.

        :param name: the name of the socket where data should be sent through
        :param topic: the name of the topic
        :param data: the data to be serialized then sent

        """
        socket = self.get_by_name(name)

        payload = self.serialization_backend.pack(data)
        socket.send_multipart([cast_bytes(topic), cast_bytes(payload)])

    def recv_event_safe(self, name, topic=False, *args, **kw):
        """waits for the socket to become available then receives multipart
        data assuming that it's a pub/sub event, thus it parses the
        topic and the serialized data, then it deserializes the result
        using the configured ``serialization_backend`` before
        returning.

        .. note::
          you can safely use this function without waiting for a
          socket to become ready, as it already does it for you.

        raises SocketNotFound when the socket name is wrong.

        returns the deserialized data, or ``None`` if the socket never became available

        :param name:  the name of the socket where data will pad through
        :param ``*args``: args to be passed to wait_until_ready
        :param ``**kw``: kwargs to be passed to wait_until_ready

        **Example:**

        ::

          >>> import zmq
          >>> from agentzero.core import SocketManager
          >>>
          >>> sockets = SocketManager()
          >>> sockets.ensure_and_bind('events', zmq.SUB, 'tcp://*:6000', zmq.POLLIN)
          >>>
          >>> # subscribe only to topics beginning with "logs"
          >>> sockets.set_topic('events', 'logs')
          >>> event = sockets.recv_event_safe('events')
          >>> event.topic, event.data
          'logs:2016-06-20', {'stdout': 'hello world'}
        """
        topic = topic or ''

        if not isinstance(topic, bytes):
            msg = (
                'recv_event_safe() takes a string, '
                'None or False as argument, '
                'received {1}({0}) instead'.format(
                    type(topic),
                    topic
                )
            )
            raise TypeError(msg)

        self.set_topic(name, topic)

        socket = self.wait_until_ready(name, self.zmq.POLLIN, *args, **kw)
        if not socket:
            return None

        topic, raw = socket.recv_multipart()

        payload = self.serialization_backend.unpack(raw)
        return Event(topic=topic, data=payload)

    def set_socket_option(self, name, option, value):
        """calls ``zmq.setsockopt`` on the given socket.

        :param name: the name of the socket where data will pad through
        :param option: the option from the ``zmq`` module
        :param value:

        Here are some examples of options:

        * ``zmq.HWM``: Set high water mark
        * ``zmq.AFFINITY``: Set I/O thread affinity
        * ``zmq.IDENTITY``: Set socket identity
        * ``zmq.SUBSCRIBE``: Establish message filter
        * ``zmq.UNSUBSCRIBE``: Remove message filter
        * ``zmq.SNDBUF``: Set kernel transmit buffer size
        * ``zmq.RCVBUF``: Set kernel receive buffer size
        * ``zmq.LINGER``: Set linger period for socket shutdown
        * ``zmq.BACKLOG``: Set maximum length of the queue of outstanding connections
        * for the full list go to ``http://api.zeromq.org/4-0:zmq-setsockopt``

        **Example:**

        ::

          >>> import zmq
          >>> from agentzero.core import SocketManager
          >>>
          >>> sockets = SocketManager()
          >>> sockets.create('pipe-in', zmq.PULL)
          >>>
          >>> # block after 10 messages are queued
          >>> sockets.set_socket_option('pipe-in', zmq.HWM, 10)
        """

        socket = self.get_by_name(name)
        socket.setsockopt(option, value)

    def set_topic(self, name, topic):
        """shortcut to :py:meth:`SocketManager.set_socket_option` with ``(name, zmq.SUBSCRIBE, topic)``

        :param name: the name of the socket where data will pad through
        :param topic: the option from the ``zmq`` module

        **Example:**

        ::

          >>> import zmq
          >>> from agentzero.core import SocketManager
          >>>
          >>> sockets = SocketManager()
          >>> sockets.ensure_and_bind('events', zmq.SUB, 'tcp://*:6000', zmq.POLLIN)
          >>>
          >>> # subscribe only to topics beginning with "logs"
          >>> sockets.set_topic('events', 'logs')
          >>> event = sockets.recv_event_safe('events')
          >>> event.topic, event.data
          'logs:2016-06-20', {'stdout': 'hello world'}
        """

        safe_topic = cast_bytes(topic)
        self.set_socket_option(name, self.zmq.SUBSCRIBE, safe_topic)

    def recv_safe(self, name, *args, **kw):
        """waits for the socket to become available then receives data through
        it and deserializes the result using the configured
        ``serialization_backend`` before returning.

        .. note::
          you can safely use this function without waiting for a
          socket to become ready, as it already does it for you.

        raises SocketNotFound when the socket name is wrong.

        returns the deserialized data, or ``None`` if the socket never became available

        :param name:  the name of the socket where data will pad through
        :param ``*args``: args to be passed to wait_until_ready
        :param ``**kw``: kwargs to be passed to wait_until_ready

        **Example:**

        ::

          >>> import zmq
          >>> from agentzero.core import SocketManager
          >>>
          >>> sockets = SocketManager()
          >>> sockets.ensure_and_bind('pipe-in', zmq.PULL, 'tcp://*:6000', zmq.POLLIN)
          >>> sockets.recv_safe('pipe-in')
          {
              "pipeline": "video-download",
              "instructions": {
                "url": "https://www.youtube.com/watch?v=FPZ6mVsv4EI"
              }
          }

        """
        socket = self.wait_until_ready(name, self.zmq.POLLIN, *args, **kw)

        if not socket:
            return

        raw = socket.recv()
        payload = self.serialization_backend.unpack(raw)
        return payload

    def subscribe(self, name, topic=None, keep_polling=None, *args, **kw):
        """waits for the socket to become available then receives data through
        it and deserializes the result using the configured
        ``serialization_backend`` before returning.

        .. note::
          you can safely use this function without waiting for a
          socket to become ready, as it already does it for you.

        raises SocketNotFound when the socket name is wrong.

        returns an :py:class`~agentzero.core.Event`, or ``None`` if the socket never became available

        :param name:  the name of the socket where data will pad through
        :param ``*args``: args to be passed to wait_until_ready
        :param ``**kw``: kwargs to be passed to wait_until_ready

        **Example:**

        ::

          >>> import zmq
          >>> from agentzero.core import SocketManager
          >>>
          >>> sockets = SocketManager()
          >>> sockets.ensure_and_bind('logs', zmq.SUB, 'tcp://*:6000', zmq.POLLIN)
          >>> for topic, data in sockets.subscribe('logs', 'output'):
          ...     print topic, '==>', data
          ...
          output:0 ==> some data
          output:1 ==> more data
          ...

        """
        socket = self.get_by_name(name)
        socket.setsockopt(self.zmq.SUBSCRIBE, cast_bytes(topic or ''))

        def socket_exists():
            return self.get_by_name(name) is not None

        keep_polling = keep_polling or socket_exists
        if not isinstance(keep_polling, collections.Callable):
            raise TypeError('SocketManager.subscribe parameter keep_polling must be a function or callable that returns a boolean')

        while keep_polling():
            topic, raw = socket.recv_multipart()
            payload = self.serialization_backend.unpack(raw)
            yield Event(topic, payload)

    def disconnect(self, socket_name):
        """disconnects a socket

        :param socket_name: the socket name
        **Example:**

        ::

          >>> import zmq
          >>> from agentzero.core import SocketManager
          >>>
          >>> sockets = SocketManager()
          >>> sockets.ensure_and_connect(
          ...   socket_name='logs',
          ...   zmq.PUB,
          ...   'tcp://192.168.10.24:6000',
          ...   zmq.POLLOUT
          ... )
          >>>
          >>> sockets.disconnect('logs')

        """
        socket = self.get_by_name(socket_name)
        if not socket:
            return False

        address = self.addresses.pop(socket_name, None)
        if address:
            socket.disconnect(address)

        self.registry.pop(socket, None)
        try:
            self.poller.unregister(socket)
        except Exception:
            pass
        return True

    def connect(self, socket_name, address, polling_mechanism):
        """connects a socket to an address and automatically registers it with
        the given polling mechanism.

        returns the socket itself.

        :param socket_name: the socket name
        :param address: a valid zeromq address (i.e: inproc://whatevs)
        :param polling_mechanism: ``zmq.POLLIN``, ``zmq.POLLOUT`` or ``zmq.POLLIN | zmq.POLLOUT``

        **Example:**

        ::

          >>> import zmq
          >>> from agentzero.core import SocketManager
          >>>
          >>> sockets = SocketManager()
          >>> sockets.ensure_and_connect(
          ...   socket_name='logs',
          ...   zmq.PUB,
          ...   'tcp://192.168.10.24:6000',
          ...   zmq.POLLOUT
          ... )
          >>> sockets.publish_safe('logs', 'output', 'some data')

        """
        if not address:
            raise SocketConnectError('socket "{0}" received an empty address and cannot connect'.format(socket_name))

        self.addresses[socket_name] = address
        socket = self.get_by_name(socket_name)
        self.register_socket(socket, polling_mechanism)
        self.engage(0)
        try:
            socket.connect(address)
        except ZMQError as e:
            msg = 'could not connect to address {0}: {1}'.format(address, e)
            raise SocketConnectError(msg)
        return socket

    def close(self, socket_name):
        """closes a socket if it exists

        :param socket_name: the socket name
        :param address: a valid zeromq address (i.e: inproc://whatevs)
        :param polling_mechanism: ``zmq.POLLIN``, ``zmq.POLLOUT`` or ``zmq.POLLIN | zmq.POLLOUT``

        **Example:**

        ::

          >>> import zmq
          >>> from agentzero.core import SocketManager
          >>>
          >>> sockets = SocketManager()
          >>> sockets.create('logs', zmq.SUB)
          >>> sockets.bind('logs', 'tcp://*:6000', zmq.POLLIN)
          >>> sockets.close('logs')
        """
        socket = self.get_by_name(socket_name)
        if not socket:
            return

        try:
            self.poller.unregister(socket)
        except KeyError:
            pass

        self.addresses.pop(socket_name, None)
        socket.close()

    def bind(self, socket_name, address, polling_mechanism):
        """binds a socket to an address and automatically registers it with
        the given polling mechanism.

        returns the socket itself.

        :param socket_name: the socket name
        :param address: a valid zeromq address (i.e: inproc://whatevs)
        :param polling_mechanism: ``zmq.POLLIN``, ``zmq.POLLOUT`` or ``zmq.POLLIN | zmq.POLLOUT``

        **Example:**

        ::

          >>> import zmq
          >>> from agentzero.core import SocketManager
          >>>
          >>> sockets = SocketManager()
          >>> sockets.create('pipe-in', zmq.PULL)
          >>> sockets.bind('pipe-in', 'tcp://*:6000', zmq.POLLIN)
        """
        if not address:
            raise SocketBindError('socket "{0}" received an empty address and cannot bind'.format(socket_name))

        self.addresses[socket_name] = address

        socket = self.get_by_name(socket_name)

        self.register_socket(socket, polling_mechanism)
        self.engage(0)
        try:
            socket.bind(address)
        except ZMQError as e:
            msg = 'could not bind to address {0}: {1}'.format(address, e)
            raise SocketBindError(msg)

        return socket

    def bind_to_random_port(self, socket_name, polling_mechanism, local_address='tcp://0.0.0.0'):
        """binds the socket to a random port

        returns a 2-item tuple with the socket instance and the address string

        :param socket_name: the socket name
        :param polling_mechanism: ``zmq.POLLIN``, ``zmq.POLLOUT`` or ``zmq.POLLIN | zmq.POLLOUT``

        **Example:**

        ::

          >>> import zmq
          >>> from agentzero.core import SocketManager
          >>>
          >>> sockets = SocketManager()
          >>> sockets.create('api-server', zmq.REP)
          >>> _, address = sockets.bind_to_random_port(
          ...     'api-server',
          ...     zmq.POLLIN | zmq.POLLOUT,
          ...     local_address='tcp://192.168.10.24
          ... )
          >>> address
          'tcp://192.168.10.24:61432'
        """
        socket = self.get_by_name(socket_name)

        self.register_socket(socket, polling_mechanism)
        self.engage(0)

        port = socket.bind_to_random_port(local_address)

        address = ':'.join(list(map(str, [local_address, port])))

        self.addresses[socket_name] = address

        return socket, address

    def ensure_and_connect(self, socket_name, socket_type, address, polling_mechanism):
        """Ensure that a socket exists, that is *connected* to the given address
        and that is registered with the given polling mechanism.

        This method is a handy replacement for calling
        ``.get_or_create()``, ``.connect()`` and then ``.engage()``.

        returns the socket itself.

        :param socket_name: the socket name
        :param socket_type: a valid socket type (i.e: ``zmq.REQ``, ``zmq.PUB``, ``zmq.PAIR``, ...)
        :param address: a valid zeromq address (i.e: inproc://whatevs)
        :param polling_mechanism: ``zmq.POLLIN``, ``zmq.POLLOUT`` or ``zmq.POLLIN | zmq.POLLOUT``

        **Example:**

        ::

          >>> import zmq
          >>> from agentzero.core import SocketManager
          >>>
          >>> sockets = SocketManager()
          >>> sockets.ensure_and_connect(
          ...   socket_name='logs',
          ...   zmq.REQ,
          ...   'tcp://192.168.10.24:7000',
          ...   zmq.POLLIN | zmq.POLLOUT
          ... )
        """
        self.get_or_create(socket_name, socket_type, polling_mechanism)
        socket = self.connect(socket_name, address, polling_mechanism)
        self.engage()
        return socket

    def ensure_and_bind(self, socket_name, socket_type, address, polling_mechanism):
        """Ensure that a socket exists, that is *binded* to the given address
        and that is registered with the given polling mechanism.

        This method is a handy replacement for calling
        ``.get_or_create()``, ``.bind()`` and then ``.engage()``.

        returns the socket itself.

        :param socket_name: the socket name
        :param socket_type: a valid socket type (i.e: ``zmq.REQ``, ``zmq.PUB``, ``zmq.PAIR``, ...)
        :param address: a valid zeromq address (i.e: inproc://whatevs)
        :param polling_mechanism: ``zmq.POLLIN``, ``zmq.POLLOUT`` or ``zmq.POLLIN | zmq.POLLOUT``
        """
        self.get_or_create(socket_name, socket_type, polling_mechanism)
        socket = self.bind(socket_name, address, polling_mechanism)
        self.engage()
        return socket

    def ready(self, name, polling_mechanism, timeout=None):
        """Polls all sockets and checks if the socket with the given name is ready for either ``zmq.POLLIN`` or  ``zmq.POLLOUT``.

        returns the socket if available, or ``None``

        :param socket_name: the socket name
        :param polling_mechanism: either ``zmq.POLLIN`` or ``zmq.POLLOUT``
        :param timeout: the polling timeout in miliseconds that will
          be passed to ``zmq.Poller().poll()`` (optional, defaults to
          ``core.DEFAULT_POLLING_TIMEOUT``)

        """
        socket = self.get_by_name(name)
        available_mechanism = self.engage(timeout is None and self.timeout or timeout).pop(socket, None)
        if polling_mechanism == available_mechanism:
            return socket

    def wait_until_ready(self, name, polling_mechanism, timeout=None, polling_timeout=None):
        """Briefly waits until the socket is ready to be used, yields to other
        greenlets until the socket becomes available.

        returns the socket if available within the given timeout, or ``None``

        :param socket_name: the socket name
        :param polling_mechanism: either ``zmq.POLLIN`` or ``zmq.POLLOUT``
        :param timeout: the timeout in seconds (accepts float) in which it
          should wait for the socket to become available
          (optional, defaults to ``core.DEFAULT_TIMEOUT_IN_SECONDS``)
        :param polling_timeout: the polling timeout in miliseconds that will
          be passed to ``zmq.Poller().poll()``.
          (optional, defaults to ``core.DEFAULT_POLLING_TIMEOUT``)
        """
        timeout = timeout is None and self.timeout or timeout
        polling_timeout = polling_timeout is None and self.polling_timeout or polling_timeout
        start = time.time()
        current = start
        while current - start < timeout:
            self.engage(polling_timeout)
            socket = self.ready(name, polling_mechanism, timeout=timeout)
            current = time.time()
            if socket:
                return socket

    def get_by_name(self, name):
        """Returns an existing socket by name. It can raise a SocketNotFound
        exception.

        Returns the socket

        :param name: the socket name
        """

        if name not in self.sockets:
            raise SocketNotFound(self, name)

        return self.sockets.get(name)

    def create(self, name, socket_type):
        """Creates a named socket by type. Can raise a SocketAlreadyExists.

        Returns the socket itself

        :param name: the socket name
        :param socket_type: a valid socket type (i.e: ``zmq.REQ``, ``zmq.PUB``, ``zmq.PAIR``, ...)
        """

        if name in self.sockets:
            raise SocketAlreadyExists(self, name)

        self.sockets[name] = self.context.socket(socket_type)
        self.set_socket_option(name, zmq.IDENTITY, cast_bytes(uuid4()))
        return self.get_by_name(name)

    def get_or_create(self, name, socket_type, polling_mechanism):
        """ensure that a socket exists and is registered with a given
        polling_mechanism (POLLIN, POLLOUT or both)

        returns the socket itself.

        :param name: the socket name
        :param socket_type: a valid socket type (i.e: ``zmq.REQ``, ``zmq.PUB``, ``zmq.PAIR``, ...)
        :param polling_mechanism: one of (``zmq.POLLIN``, ``zmq.POLLOUT``, ``zmq.POLLIN | zmq.POLLOUT``)
        """
        if name not in self.sockets:
            self.create(name, socket_type)

        socket = self.get_by_name(name)
        self.register_socket(socket, polling_mechanism)
        return socket

    def register_socket(self, socket, polling_mechanism):
        """registers a socket with a given
        polling_mechanism (POLLIN, POLLOUT or both)

        returns the socket itself.

        :param socket: the socket instance
        :param polling_mechanism: one of (``zmq.POLLIN``, ``zmq.POLLOUT``, ``zmq.POLLIN | zmq.POLLOUT``)
        """

        if socket not in self.registry:
            self.poller.register(socket, polling_mechanism)
            self.registry[socket] = polling_mechanism

        return socket

    def engage(self, timeout=None):
        """polls all registered sockets with the given timeout in miliseconds

        returns a dictionary with the sockets that are ready to be used in their respective state (``zmq.POLLIN`` *or* ``zmq.POLLOUT``)

        :param timeout: how long should it poll until a socket becomes available. defaults to :py:data:`agentzero.core.DEFAULT_POLLING_TIMEOUT`
        """
        polling_timeout = timeout is None and self.polling_timeout or timeout

        return collections.OrderedDict(self.poller.poll(polling_timeout))

    def get_log_handler(self, socket_name, topic_name='logs'):
        """returns an instance of :py:class:`~zmq.ZMQPubHandler` attached to a previously-created socket.

        :param socket_name: the name of the socket, previously created with :py:meth:`SocketManager.create`
        :param topic_name: the name of the topic in which the logs will be PUBlished

        **Example:**

        ::

          >>> import zmq
          >>> from agentzero.core import SocketManager
          >>>
          >>> sockets = SocketManager()
          >>> sockets.ensure_and_bind('logs', zmq.PUB, 'tcp://*:6000', zmq.POLLOUT)
          >>> app_logger = sockets.get_logger('logs', logger_name='myapp'))
          >>> app_logger.info("Server is up!")
          >>> try:
                  url = sockets.recv_safe('download_queue')
          ...     requests.get(url)
          ... except:
          ...     app_logger.exception('failed to download url: %s', url)
        """
        return ZMQPubHandler(self, socket_name, topic_name)

    def get_logger(self, socket_name, topic_name='logs', logger_name=None):
        """returns an instance of :py:class:`~logging.Logger` that contains a
        :py:class:`~zmq.ZMQPubHandler` attached to.

        :param socket_name: the name of the socket, previously created with :py:meth:`~agentzero.core.SocketManager.create`
        :param topic_name: (optional) the name of the topic in which the logs will be PUBlished, defaults to **"logs"**
        :param logger_name: (optional) defaults to the given socket name

        **Example:**

        ::

          >>> import zmq
          >>> from agentzero.core import SocketManager
          >>>
          >>> sockets = SocketManager()
          >>> sockets.ensure_and_bind('logs', zmq.PUB, 'tcp://*:6000', zmq.POLLOUT)
          >>> app_logger = sockets.get_logger('logs', logger_name='myapp'))
          >>> app_logger.info("Server is up!")
          >>> try:
                  url = sockets.recv_safe('download_queue')
          ...     requests.get(url)
          ... except:
          ...     app_logger.exception('failed to download url: %s', url)
        """
        logger_name = logger_name or socket_name
        handler = self.get_log_handler(socket_name, topic_name)
        logger = logging.getLogger(logger_name)
        logger.addHandler(handler)
        return logger


class ZMQPubHandler(logging.Handler):
    default_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(filename)s:%(lineno)d - %(message)s\n",
        datefmt='%Y-%m-%dT%H:%M:%SZ'
    )

    formatters = {
        logging.DEBUG: default_formatter,
        logging.INFO: default_formatter,
        logging.WARN: default_formatter,
        logging.ERROR: logging.Formatter(
            "[%(asctime)s] %(levelname)s %(filename)s:%(lineno)d - %(message)s - %(exc_info)s\n",
            datefmt='%Y-%m-%dT%H:%M:%SZ'
        ),
        logging.CRITICAL: default_formatter
    }

    def __init__(self, socket_manager, socket_name='logs', topic_name='logs'):
        super(ZMQPubHandler, self).__init__()

        self.sockets = socket_manager
        self.socket_name = socket_name
        self.topic_name = cast_bytes(topic_name)

    def format(self, record):
        return self.formatters[record.levelno].format(record)

    def emit(self, record):
        msg = cast_bytes(self.format(record))
        # except Exception:
        #     self.handleError(record)
        #     # return

        data = {'msg': msg, 'args': record.args, 'level': record.levelno}
        self.sockets.publish_safe(self.socket_name, self.topic_name, data)


class Event(object):
    """PUB/SUB event container

    this is an opaque data structure that represents a single, entire
    event: ``topic`` and ``data``
    """

    def __init__(self, topic, data):
        self.__topic = topic
        self.__data = data

    @property
    def topic(self):
        """a string containing the topic name. zero-length in absence of topic."""
        return self.__topic

    @property
    def data(self):
        """the deserialized python object containing the event payload."""
        return self.__data
