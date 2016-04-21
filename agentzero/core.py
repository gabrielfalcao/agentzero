#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
agentzero.core
~~~~~~~~~~~~~~~

* ``DEFAULT_TIMEOUT_IN_SECONDS``: 3 (seconds)
* ``DEFAULT_POLLING_TIMEOUT``: 500 (miliseconds)

"""

import time
import gevent
import logging
from collections import OrderedDict
from collections import namedtuple

from zmq.error import ZMQError
from zmq.utils.strtypes import cast_bytes

from agentzero.errors import SocketNotFound
from agentzero.errors import SocketAlreadyExists
from agentzero.errors import SocketBindError
from agentzero.errors import SocketConnectError
from agentzero import serializers


DEFAULT_TIMEOUT_IN_SECONDS = .5
DEFAULT_POLLING_TIMEOUT = 100


Event = namedtuple('Event', ['topic', 'data'])


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

    .. note:: An extra useful feature that comes with using a
      ``SocketManager`` is that you can use a SocketManager to create an
      application that dynamically connects to new nodes based on
      scaling instructions coming from other nodes

    .. warning:: Always use the same context per each thread. If you are
      using gevent, please using a single instance for your whole main
      process, across all greenlets that you manage.

    >>> import zmq.green as zmq
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

    def __init__(self, zmq, context, serialization_backend=None):
        self.zmq = zmq
        self.context = context
        self.sockets = OrderedDict()
        self.addresses = OrderedDict()
        self.poller = self.zmq.Poller()
        self.registry = OrderedDict()
        self.serialization_backend = serialization_backend or serializers.JSON()
        self.cache = {}

    def __repr__(self):
        return b'SocketManager(sockets={0})'.format(repr(self.sockets.keys()))

    def __del__(self):
        for socket in self.sockets.values():
            try:
                socket.close()
            except:
                pass

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
        socket.send_multipart([bytes(topic), payload])

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

        :param name:  the name of the socket where data will come through
        :param ``*args``: args to be passed to wait_until_ready
        :param ``**kw``: kwargs to be passed to wait_until_ready

        """
        topic = topic or b''

        if not isinstance(topic, basestring):
            msg = (
                'recv_event_safe() takes a string, '
                'None or False as argument, '
                'received {1}({0}) instead'.format(
                    type(topic),
                    topic
                )
            )
            raise TypeError(msg)
        elif topic:
            self.set_topic(name, topic)

        socket = self.wait_until_ready(name, self.zmq.POLLIN, *args, **kw)
        if not socket:
            return None

        topic, raw = socket.recv_multipart()
        payload = self.serialization_backend.unpack(raw)
        return Event(topic=topic, data=payload)

    def set_socket_option(self, name, option, value):
        socket = self.get_by_name(name)
        socket.setsockopt(option, value)

    def set_topic(self, name, topic):
        safe_topic = bytes(topic)
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

        :param name:  the name of the socket where data will come through
        :param ``*args``: args to be passed to wait_until_ready
        :param ``**kw``: kwargs to be passed to wait_until_ready

        """
        socket = self.wait_until_ready(name, self.zmq.POLLIN, *args, **kw)

        if not socket:
            return

        raw = socket.recv()
        payload = self.serialization_backend.unpack(raw)
        return payload

    def subscribe(self, name, topic=None, *args, **kw):
        """waits for the socket to become available then receives data through
        it and deserializes the result using the configured
        ``serialization_backend`` before returning.

        .. note::
          you can safely use this function without waiting for a
          socket to become ready, as it already does it for you.

        raises SocketNotFound when the socket name is wrong.

        returns the deserialized data, or ``None`` if the socket never became available

        :param name:  the name of the socket where data will come through
        :param ``*args``: args to be passed to wait_until_ready
        :param ``**kw``: kwargs to be passed to wait_until_ready

        """
        socket = self.get_by_name(name)
        socket.setsockopt(self.zmq.SUBSCRIBE, bytes(topic or ''))

        while True:
            topic, raw = socket.recv_multipart()
            payload = self.serialization_backend.unpack(raw)
            yield topic, payload

    def connect(self, socket_name, address, polling_mechanism):
        """connects a socket to an address and automatically registers it with
        the given polling mechanism.

        returns the socket itself.

        :param socket_name: the socket name
        :param address: a valid zeromq address (i.e: inproc://whatevs)
        :param polling_mechanism: ``zmq.POLLIN``, ``zmq.POLLOUT`` or ``zmq.POLLIN | zmq.POLLOUT``
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
        """
        socket = self.get_by_name(socket_name)
        if not socket:
            return

        self.poller.unregister(socket)
        self.addresses.pop(socket_name, None)
        socket.close()

    def bind(self, socket_name, address, polling_mechanism):
        """binds a socket to an address and automatically registers it with
        the given polling mechanism.

        returns the socket itself.

        :param socket_name: the socket name
        :param address: a valid zeromq address (i.e: inproc://whatevs)
        :param polling_mechanism: ``zmq.POLLIN``, ``zmq.POLLOUT`` or ``zmq.POLLIN | zmq.POLLOUT``
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

    def bind_to_random_port(self, socket_name, polling_mechanism):
        """binds the socket to a random port

        returns a 2-item tuple with the socket instance and the address string

        :param socket_name: the socket name
        :param polling_mechanism: ``zmq.POLLIN``, ``zmq.POLLOUT`` or ``zmq.POLLIN | zmq.POLLOUT``
        """
        socket = self.get_by_name(socket_name)

        self.register_socket(socket, polling_mechanism)
        self.engage(0)

        local_address = 'tcp://0.0.0.0'
        port = socket.bind_to_random_port(local_address)

        address = ':'.join([local_address, str(port)])

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

    def ready(self, name, polling_mechanism, timeout=DEFAULT_POLLING_TIMEOUT):
        """Polls all sockets and checks if the socket with the given name is ready for either ``zmq.POLLIN`` or  ``zmq.POLLOUT``.

        returns the socket if available, or ``None``

        :param socket_name: the socket name
        :param polling_mechanism: either ``zmq.POLLIN`` or ``zmq.POLLOUT``
        :param timeout: the polling timeout in miliseconds that will
          be passed to ``zmq.Poller().poll()`` (optional, defaults to
          ``core.DEFAULT_POLLING_TIMEOUT``)

        """
        self.engage(timeout)
        socket = self.get_by_name(name)
        available_mechanism = self.cache.get(socket, None)
        if polling_mechanism == available_mechanism:
            return socket

    def wait_until_ready(self, name, polling_mechanism, timeout=DEFAULT_TIMEOUT_IN_SECONDS, polling_timeout=DEFAULT_POLLING_TIMEOUT):
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
        start = time.time()
        current = start
        while current - start < timeout:
            gevent.sleep()
            self.engage(polling_timeout)
            socket = self.ready(name, polling_mechanism)
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

    def engage(self, timeout=DEFAULT_POLLING_TIMEOUT):
        """polls all registered sockets with the given timeout in miliseconds

        returns a dictionary with the sockets that are ready to be used in their respective state (``zmq.POLLIN`` *or* ``zmq.POLLOUT``)

        :param timeout: how long should it poll until a socket becomes available. defaults to :py:data:`agentzero.core.DEFAULT_POLLING_TIMEOUT`
        """

        self.cache = OrderedDict(self.poller.poll(timeout))
        return self.cache

    def get_log_handler(self, socket_name, topic_name='logs'):
        return ZMQPubHandler(self, socket_name, topic_name)


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
        logging.Handler.__init__(self)

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
