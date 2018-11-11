#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gevent

from agentzero.zero import zmq
from agentzero.core import SocketManager
from agentzero.errors import AgentZeroSocketError

context = zmq.Context()


def test_socket_manager_raises_exception_when_retrieving_socket_with_bad_name():
    (
        "SocketManager.get_by_name should raise AgentZeroSocketError when "
        "a given socket does not exist"
    )

    # Given a manager
    manager = SocketManager(zmq, context)

    # And a couple of sockets
    manager.create("foo", zmq.REQ)
    manager.create("bar", zmq.PUB)

    # When I call get_by_name with an unexpected name
    when_called = manager.get_by_name.when.called_with("boom")

    # Then it should have
    when_called.should.have.raised(
        AgentZeroSocketError,
        "SocketManager(sockets=['foo', 'bar']) has no sockets named 'boom'.",
    )


def test_socket_manager_raises_exception_when_creating_existing_socket():
    (
        "SocketManager.create should raise AgentZeroSocketError when "
        "a given socket already exists"
    )

    # Given a manager
    manager = SocketManager(zmq, context)

    # And a couple of sockets
    manager.create("foo", zmq.REQ)
    manager.create("bar", zmq.PUB)

    # When I call create on an existing socket name
    when_called = manager.create.when.called_with("foo", zmq.PUB)

    # Then it should have
    when_called.should.have.raised(
        AgentZeroSocketError,
        "SocketManager(sockets=['foo', 'bar']) already has a socket named 'foo'",
    )


def test_socket_manager_can_poll_asynchronously():
    (
        "SocketManager should leverage a non-blocking socket "
        "collection can be used seamlessly in a blocking fashion [TCP SOCKET]"
    )

    # Given a socket manager for a server
    server = SocketManager(zmq, context)
    # And a reply socket listening on a tcp port
    server.ensure_and_bind(
        "reply-server", zmq.REP, "tcp://0.0.0.0:3458", zmq.POLLIN | zmq.POLLOUT
    )

    # And a socket manager for a client
    client = SocketManager(zmq, context)

    # And a request client connected to the server
    client.ensure_and_connect(
        "request-client",
        zmq.REQ,
        "tcp://0.0.0.0:3458",
        zmq.POLLIN | zmq.POLLOUT,
    )

    # And send a request from the client
    requester = client.wait_until_ready(
        "request-client", zmq.POLLOUT, timeout=2
    )
    requester.send_json({"client": 42})

    # Then I should receive a request from the client
    replier = server.wait_until_ready("reply-server", zmq.POLLIN, timeout=2)
    replier.should_not.be.none
    request = replier.recv_json()

    # And the request should be the one that the client just sent
    request.should.equal({"client": 42})

    # And disconnecting should work
    client.disconnect("request-client")
    server.disconnect("reply-server")


def test_socket_manager_ignore_exceptions_when_cleaning_up_sockets():
    (
        "SocketManager.__del__() should should ignore errors when cleaning up sockets"
    )

    # Given a bad socket that raises an exception upon calling .close()
    class BadSocket(object):
        def close(self):
            raise RuntimeError("This is the exception that should be ignored")

    # And a SocketManager instance containing that poisened socket
    manager = SocketManager(zmq, context)
    manager.sockets["bad-one"] = BadSocket()

    # When the manager gets wipe out of the memory
    del manager

    # Then no warnings should have been printed


def test_socket_manager_send_safe_not_ready():
    ("SocketManager.send_safe should return False when the socket is not ready")

    # Given a manager
    manager = SocketManager(zmq, context)

    # And a couple of sockets
    manager.create("foo", zmq.REP)

    # When I call .send_safe()
    result = manager.send_safe("foo", {"some": "value"})

    # Then it should be false
    result.should.be.false


def test_socket_manager_publish_safe_not_ready():
    (
        "SocketManager.publish_safe should return False when the socket is not ready"
    )

    # Given a manager
    manager = SocketManager(zmq, context)

    # And a couple of sockets
    manager.ensure_and_bind(
        "foo", zmq.PUB, "inproc://test.publisher.1", zmq.POLLOUT
    )

    # When I call .publish_safe()
    manager.publish_safe("foo", "some-topic", {"some": "value"})

    # Then it should proceed even if nobody is connected


def test_socket_manager_subscribe():
    ("SocketManager.subscribe should subscribe to a topic")

    # Given a manager
    manager = SocketManager(zmq, context)

    # And a couple of sockets
    manager.ensure_and_bind(
        "foo", zmq.PUB, "inproc://test.publisher.2", zmq.POLLOUT
    )
    manager.create("bar", zmq.SUB)
    manager.connect("bar", "inproc://test.publisher.2", zmq.POLLIN)

    gevent.spawn(manager.publish_safe, "foo", "some-topic", {"some": "value"})

    # Then it should have received
    event = next(manager.subscribe("bar"))
    event.topic.should.equal(b"some-topic")
    event.data.should.equal({"some": "value"})
