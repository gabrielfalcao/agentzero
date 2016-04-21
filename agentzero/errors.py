#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals


class AgentZeroSocketError(BaseException):
    """Base exception class for errors originated in :py:class:`~agentzero.core.SocketManager`"""
    pass


class SocketAlreadyExists(AgentZeroSocketError):
    """raised by :py:class:`~agentzero.core.SocketManager` when trying to create a named socket that already exists

    ::

      >>> from agentzero.core import zmq
      >>> from agentzero.core import SocketManager
      >>> sockets = SocketManager()
      >>> sockets.create('foo', zmq.REP)
      >>> sockets.create('foo', zmq.REP)
      Traceback (most recent call last):
          ...
      SocketAlreadyExists: SocketManager(sockets=['foo']) already has a socket named 'foo'.
    """
    def __init__(self, manager, socket_name):
        msg = '{0} already has a socket named {1}.'.format(manager, repr(socket_name))
        super(SocketAlreadyExists, self).__init__(msg)


class SocketNotFound(AgentZeroSocketError):
    """raised by :py:class:`~agentzero.core.SocketManager` when trying to retrieve an unexisting socket

    ::

      >>> from agentzero.core import zmq
      >>> from agentzero.core import SocketManager
      >>> sockets = SocketManager()
      >>> sockets.get_by_name('some-name', zmq.PUB)
      Traceback (most recent call last):
          ...
      SocketNotFound: SocketManager(sockets=['']) has no sockets named 'some-name'.
    """
    def __init__(self, manager, socket_name):
        msg = '{0} has no sockets named {1}.'.format(manager, repr(socket_name))
        super(SocketNotFound, self).__init__(msg)


class SocketBindError(AgentZeroSocketError):
    """raised by :py:class:`~agentzero.core.SocketManager` when a
    :py:method:`~agentzero.core.SocketManager.bind` operation fails.
    """


class SocketConnectError(AgentZeroSocketError):
    """raised by :py:class:`~agentzero.core.SocketManager` when a
    :py:method:`~agentzero.core.SocketManager.connect` operation fails.
    """
