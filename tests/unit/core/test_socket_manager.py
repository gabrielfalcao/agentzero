#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mock import Mock, patch, call
from collections import OrderedDict
from zmq.error import ZMQError
from zmq.utils.strtypes import cast_bytes
from agentzero.core import SocketManager
from agentzero.core import Event
from agentzero.errors import SocketAlreadyExists
from agentzero.errors import SocketNotFound
from agentzero.errors import SocketBindError
from agentzero.errors import SocketConnectError
from tests.helpers import only_py2
from tests.helpers import only_py3


def test_socket_manager_init():
    ("SocketManager() should set an internal zmq module and create a poller")

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # When I create a socket manager
    manager = SocketManager(zmq, context)

    # Then it should have set the zmq module and created a poller
    manager.should.have.property("zmq").being.equal(zmq)
    manager.should.have.property("poller").being.equal(zmq.Poller.return_value)

    # And it should have an OrderedDict to keep track of the socket names
    manager.should.have.property("sockets").being.an(OrderedDict)
    manager.sockets.should.be.empty

    # And it should have an OrderedDict to keep track of the registered sockets
    manager.should.have.property("registry").being.an(OrderedDict)
    manager.registry.should.be.empty


def test_socket_manager_repr():
    ("repr(SocketManager()) should be informative")
    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager with some fake sockets
    manager = SocketManager(zmq, context)
    manager.sockets = OrderedDict(
        [("foobar", "WHATEVS"), ("awesome", "WHATEVS")]
    )

    # When I get the string representation of the instance
    string = repr(manager)

    # Then it should
    string.should.equal("SocketManager(sockets=['foobar', 'awesome'])")


def test_socket_create():
    ("SocketManager().create() should create a socket")

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager
    manager = SocketManager(zmq, context)

    # When I create a socket
    manager.create("foobar", "SOME_SOCKET_TYPE")

    # Then it should have been added to the socket pool
    manager.sockets.should.have.key("foobar")
    manager.sockets["foobar"].should.equal(context.socket.return_value)

    # And the socket should have been created with the given type
    context.socket.assert_called_once_with("SOME_SOCKET_TYPE")


def test_socket_get_by_name():
    (
        "SocketManager().get_by_name() should return a socket from the pool by its name"
    )

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager with a fake socket in the pool
    manager = SocketManager(zmq, context)
    manager.sockets["foobar"] = "i-am-the-fake-socket"

    # When I call get_by_name
    socket = manager.get_by_name("foobar")

    # Then it should return the expected value
    socket.should.equal("i-am-the-fake-socket")


def test_socket_manager_register_socket():
    (
        "SocketManager().register_socket() should register "
        "a socket only once even if called twice"
    )

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager with a fake socket in the pool
    manager = SocketManager(zmq, context)
    manager.registry = {}

    # When I call register_socket
    result = manager.register_socket("fake-socket", "fake-polling-mechanism")

    # Then it should return the socket itself
    result.should.equal("fake-socket")

    # And it should have been registered with the poller
    manager.poller.register.assert_called_once_with(
        "fake-socket", "fake-polling-mechanism"
    )

    # And it should have been added to the internal registry
    manager.registry.should.have.key("fake-socket").being.equal(
        "fake-polling-mechanism"
    )


@patch("agentzero.core.SocketManager.register_socket")
@patch("agentzero.core.SocketManager.get_by_name")
@patch("agentzero.core.SocketManager.create")
def test_socket_manager_get_or_create(create, get_by_name, register_socket):
    ("SocketManager().get_or_create() should create a socket and register it")

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager with no sockets
    manager = SocketManager(zmq, context)
    manager.sockets = {"foobar": "SOME_TYPE"}

    # When I call get_or_create
    result = manager.get_or_create(
        "foobar", "SOME_TYPE", "fake-polling-mechanism"
    )

    # Then it should have returned a socket
    result.should.equal(get_by_name.return_value)

    # And .create should not have been called
    create.called.should.be.false

    # And should have been retrieved by name
    get_by_name.assert_called_once_with("foobar")

    # And should have been registered
    register_socket.assert_called_once_with(result, "fake-polling-mechanism")


@patch("agentzero.core.SocketManager.register_socket")
@patch("agentzero.core.SocketManager.get_by_name")
@patch("agentzero.core.SocketManager.create")
def test_socket_manager_get_or_create_preexisting(
    create, get_by_name, register_socket
):
    (
        "SocketManager().get_or_create() should just return "
        "and register a pre-existing socket with the same name"
    )

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager with no sockets
    manager = SocketManager(zmq, context)
    manager.sockets = {}

    # When I call get_or_create
    result = manager.get_or_create(
        "foobar", "SOME_TYPE", "fake-polling-mechanism"
    )

    # Then it should have returned a socket
    result.should.equal(get_by_name.return_value)

    # And the socket should have been created
    create.assert_called_once_with("foobar", "SOME_TYPE")

    # And should have been retrieved by name
    get_by_name.assert_called_once_with("foobar")

    # And should have been registered
    register_socket.assert_called_once_with(result, "fake-polling-mechanism")


def test_socket_manager_raises_exception_when_retrieving_socket_with_bad_name():
    (
        "SocketManager().get_by_name() should raise AgentZeroSocketError when "
        "a given socket does not exist"
    )

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager
    manager = SocketManager(zmq, context)

    # And a couple of sockets
    manager.create("foo", zmq.REQ)
    manager.create("bar", zmq.PUB)

    # When I call get_by_name with an unexpected name
    when_called = manager.get_by_name.when.called_with("boom")

    # Then it should have
    when_called.should.have.raised(
        SocketNotFound,
        "SocketManager(sockets=['foo', 'bar']) has no sockets named 'boom'.",
    )


def test_socket_manager_raises_exception_when_creating_existing_socket():
    (
        "SocketManager().create() should raise AgentZeroSocketError when "
        "a given socket already exists"
    )

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager
    manager = SocketManager(zmq, context)

    # And a couple of sockets
    manager.create("foo", zmq.REQ)
    manager.create("bar", zmq.PUB)

    # When I call create on an existing socket name
    when_called = manager.create.when.called_with("foo", zmq.PUB)

    # Then it should have
    when_called.should.have.raised(
        SocketAlreadyExists,
        "SocketManager(sockets=['foo', 'bar']) already has a socket named 'foo'",
    )


@patch("agentzero.core.SocketManager.engage")
@patch("agentzero.core.SocketManager.register_socket")
@patch("agentzero.core.SocketManager.get_by_name")
def test_socket_connect(get_by_name, register_socket, engage):
    (
        "SocketManager().connect() should get by name, register then "
        "connect to the given address."
    )

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager
    manager = SocketManager(zmq, context)

    # When I call connect
    result = manager.connect("foobar", "inproc://whatevs", "some-mechanism")

    # Then it should have returned a socket from get_by_name
    result.should.equal(get_by_name.return_value)

    # And get_by_name should have been called with the name
    get_by_name.assert_called_once_with("foobar")

    # And register_socket should have been called
    register_socket.assert_called_once_with(result, "some-mechanism")

    # And it should have called connect on the given address
    result.connect.assert_called_once_with("inproc://whatevs")

    # And it should have engaged the manager with zero timeout
    engage.assert_called_once_with(0)


@patch("agentzero.core.SocketManager.engage")
@patch("agentzero.core.SocketManager.register_socket")
@patch("agentzero.core.SocketManager.get_by_name")
def test_socket_connect_missing_address(get_by_name, register_socket, engage):
    (
        "SocketManager().connect() should raise an exception when missing an address"
    )

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager
    manager = SocketManager(zmq, context)

    # When I call connect with an empty address
    when_called = manager.connect.when.called_with(
        "foobar", "", "some-mechanism"
    )

    # Then it should have raised an exception
    when_called.should.have.raised(
        SocketConnectError,
        'socket "foobar" received an empty address and cannot connect',
    )


@patch("agentzero.core.SocketManager.engage")
@patch("agentzero.core.SocketManager.connect")
@patch("agentzero.core.SocketManager.get_or_create")
def test_socket_ensure_and_connect(get_or_create, connect, engage):
    (
        "SocketManager().ensure_and_connect() should ensure the socket existence then "
        "connect to the given address."
    )

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager
    manager = SocketManager(zmq, context)

    # When I call ensure_and_connect
    result = manager.ensure_and_connect(
        "foobar", "SOME_TYPE", "inproc://whatevs", "some-mechanism"
    )

    # Then it should have returned a socket from connect
    result.should.equal(connect.return_value)

    # And get_or_create should have been called correctly
    get_or_create.assert_called_once_with(
        "foobar", "SOME_TYPE", "some-mechanism"
    )

    # And connect should have been called with the given address
    connect.assert_called_once_with(
        "foobar", "inproc://whatevs", "some-mechanism"
    )

    # And engage should have been called with the default value
    engage.assert_called_once_with()


@patch("agentzero.core.SocketManager.engage")
@patch("agentzero.core.SocketManager.register_socket")
@patch("agentzero.core.SocketManager.get_by_name")
def test_socket_bind(get_by_name, register_socket, engage):
    (
        "SocketManager().bind() should get by name, register then "
        "bind to the given address."
    )

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager
    manager = SocketManager(zmq, context)

    # When I call bind
    result = manager.bind("foobar", "inproc://whatevs", "some-mechanism")

    # Then it should have returned a socket from get_by_name
    result.should.equal(get_by_name.return_value)

    # And get_by_name should have been called with the name
    get_by_name.assert_called_once_with("foobar")

    # And register_socket should have been called
    register_socket.assert_called_once_with(result, "some-mechanism")

    # And it should have called bind on the given address
    result.bind.assert_called_once_with("inproc://whatevs")

    # And it should have engaged the manager with zero timeout
    engage.assert_called_once_with(0)


@patch("agentzero.core.SocketManager.engage")
@patch("agentzero.core.SocketManager.register_socket")
@patch("agentzero.core.SocketManager.get_by_name")
def test_socket_bind_missing_address(get_by_name, register_socket, engage):
    ("SocketManager().bind() should raise an exception when missing an address")

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager
    manager = SocketManager(zmq, context)

    # When I call bind with an empty address
    when_called = manager.bind.when.called_with("foobar", "", "some-mechanism")

    # Then it should have raised an exception
    when_called.should.have.raised(
        SocketBindError,
        'socket "foobar" received an empty address and cannot bind',
    )


@patch("agentzero.core.SocketManager.engage")
@patch("agentzero.core.SocketManager.register_socket")
@patch("agentzero.core.SocketManager.get_by_name")
def test_socket_bind_error(get_by_name, register_socket, engage):
    (
        "SocketManager().bind() should get by name, register then "
        "bind to the given address."
    )

    # Background: the zmq socket will raise a ZMQError when .bind is called
    socket = get_by_name.return_value
    socket.bind.side_effect = ZMQError("boom")

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager
    manager = SocketManager(zmq, context)

    # When I call bind
    when_called = manager.bind.when.called_with(
        "foobar", "bad-address", "some-mechanism"
    )

    # Then it should have raised a SocketBindError
    when_called.should.have.raised(SocketBindError)


@patch("agentzero.core.SocketManager.engage")
@patch("agentzero.core.SocketManager.register_socket")
@patch("agentzero.core.SocketManager.get_by_name")
def test_socket_connect_error(get_by_name, register_socket, engage):
    (
        "SocketManager().connect() should get by name, register then "
        "connect to the given address."
    )

    # Background: the zmq socket will raise a ZMQError when .connect is called
    socket = get_by_name.return_value
    socket.connect.side_effect = ZMQError("boom")

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager
    manager = SocketManager(zmq, context)

    # When I call connect
    when_called = manager.connect.when.called_with(
        "foobar", "bad-address", "some-mechanism"
    )

    # Then it should have raised a SocketConnectError
    when_called.should.have.raised(SocketConnectError)


@patch("agentzero.core.SocketManager.engage")
@patch("agentzero.core.SocketManager.register_socket")
@patch("agentzero.core.SocketManager.get_by_name")
def test_socket_bind_to_random_port(get_by_name, register_socket, engage):
    (
        "SocketManager().bind_to_random_port() should get by name, register then "
        "bind to a random port"
    )

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager
    manager = SocketManager(zmq, context)

    # And that the socket is mocked to return a random port
    socket = get_by_name.return_value
    socket.bind_to_random_port.return_value = 42000

    # When I call bind
    result = manager.bind_to_random_port("foobar", "some-mechanism")

    # Then it should have returned a socket from get_by_name
    result.should.equal((socket, "tcp://0.0.0.0:42000"))

    # And get_by_name should have been called with the name
    get_by_name.assert_called_once_with("foobar")

    # And register_socket should have been called
    register_socket.assert_called_once_with(socket, "some-mechanism")

    # And it should have called bind on the given address
    socket.bind_to_random_port.assert_called_once_with("tcp://0.0.0.0")

    # And it should have engaged the manager with zero timeout
    engage.assert_called_once_with(0)


@patch("agentzero.core.SocketManager.engage")
@patch("agentzero.core.SocketManager.bind")
@patch("agentzero.core.SocketManager.get_or_create")
def test_socket_ensure_and_bind(get_or_create, bind, engage):
    (
        "SocketManager().ensure_and_bind() should ensure the socket existence then "
        "bind to the given address."
    )

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager
    manager = SocketManager(zmq, context)

    # When I call ensure_and_bind
    result = manager.ensure_and_bind(
        "foobar", "SOME_TYPE", "inproc://whatevs", "some-mechanism"
    )

    # Then it should have returned a socket from bind
    result.should.equal(bind.return_value)

    # And get_or_create should have been called correctly
    get_or_create.assert_called_once_with(
        "foobar", "SOME_TYPE", "some-mechanism"
    )

    # And bind should have been called with the given address
    bind.assert_called_once_with("foobar", "inproc://whatevs", "some-mechanism")

    # And engage should have been called with the default value
    engage.assert_called_once_with()


@patch("agentzero.core.SocketManager.engage")
@patch("agentzero.core.SocketManager.get_by_name")
def test_socket_manager_ready(get_by_name, engage):
    (
        "SocketManager().ready() should return the socket "
        "if it's ready and engaged with the given polling mechanism"
    )

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager with a fake socket
    manager = SocketManager(zmq, context)
    manager.sockets = {"foobar": "SOME_TYPE"}
    # And that get_by_name will return "socket_sentinel"
    get_by_name.return_value = "socket_sentinel"

    # And that socket.engage will return a dict
    engage.return_value = {"socket_sentinel": "some-polling-mechanism"}

    # When I call ready
    socket = manager.ready("foobar", "some-polling-mechanism", timeout=1000)

    # Then the result should be the "socket_sentinel"
    socket.should.equal("socket_sentinel")

    # And engage should have been called
    engage.assert_called_once_with(1000)


@patch("agentzero.core.SocketManager.engage")
@patch("agentzero.core.SocketManager.get_by_name")
def test_socket_manager_not_ready(get_by_name, engage):
    (
        "SocketManager().ready() should return None when the socket is not available"
    )

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager with a fake socket
    manager = SocketManager(zmq, context)
    manager.sockets = {"foobar": "SOME_TYPE"}

    # And that get_by_name will return "socket_sentinel"
    get_by_name.return_value = "socket_sentinel"

    # When I call ready
    socket = manager.ready("foobar", "some-polling-mechanism", timeout=1000)

    # Then the result should be None
    socket.should.be.none

    # And engage should have been called
    engage.assert_called_once_with(1000)


@patch("agentzero.core.time")
@patch("agentzero.core.SocketManager.engage")
@patch("agentzero.core.SocketManager.ready")
def test_socket_manager_wait_until_ready(ready, engage, time):
    (
        "SocketManager().wait_until_ready() whould engage and poll "
        "continously until the socket becomes available"
    )

    # Background: time.time() is mocked tick for 3 iterations
    time.time.side_effect = list(range(4))

    # Background: SocketManager().ready() is mocked to return a socket
    # only after the second iteration
    socket = Mock(name="socket-ready-to-go")
    ready.side_effect = [None, socket, None]

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager
    manager = SocketManager(zmq, context)

    # When I call wait_until_ready
    result = manager.wait_until_ready(
        "foobar", "some-mechanism", timeout=2, polling_timeout=42
    )

    # Then it should have returned the socket
    result.should.equal(socket)

    # And it should have engaged twice
    engage.assert_has_calls([call(42), call(42)])

    # And ready should also have been called twice
    ready.assert_has_calls(
        [
            call("foobar", "some-mechanism", timeout=2),
            call("foobar", "some-mechanism", timeout=2),
        ]
    )


def test_socket_engage():
    (
        "SocketManager().engage() should return an OrderedDict with the polled sockets"
    )

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager
    manager = SocketManager(zmq, context)

    # And that the poller returns some results
    manager.poller.poll.return_value = [
        ("foobar", "whatevs"),
        ("silly-walks", "whatevs"),
    ]

    # When I call engage
    result = manager.engage("SOME_TIMEOUT")

    # Then it should have called .poll() with the given timeout
    manager.poller.poll.assert_called_once_with("SOME_TIMEOUT")

    # And the result should be an OrderedDict
    result.should.be.an(OrderedDict)

    # And the result should contain the returned items from polling
    list(result.items()).should.equal(
        [("foobar", "whatevs"), ("silly-walks", "whatevs")]
    )


@patch("agentzero.core.SocketManager.wait_until_ready")
def test_socket_manager_send_safe(wait_until_ready):
    (
        "SocketManager().send_safe() should serialize "
        "before sending, using the configured backend"
    )

    # Background: wait_until_ready is mocked to return the socket
    wait_until_ready.side_effect = lambda name, *args: manager.sockets[name]

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a serializer
    serializer = Mock(name="serializer")

    # And a socket manager
    manager = SocketManager(zmq, context, serialization_backend=serializer)

    # And a socket
    socket = manager.create("foobar", zmq.REP)

    # When I call .send_safe()
    sent = manager.send_safe("foobar", "PAYLOAD")

    # Then it should have sent successfully
    sent.should.be.true

    # And it should have packed the payload before sending
    serializer.pack.assert_called_once_with("PAYLOAD")
    packed = serializer.pack.return_value

    socket.send_string.assert_called_once_with(packed)


@patch("agentzero.core.SocketManager.wait_until_ready")
def test_socket_manager_send_safe_not_ready(wait_until_ready):
    (
        "SocketManager().send_safe() should return False when the socet is not ready"
    )

    # Background: wait_until_ready is mocked to return None
    wait_until_ready.return_value = None

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a serializer
    serializer = Mock(name="serializer")

    # And a socket manager
    manager = SocketManager(zmq, context, serialization_backend=serializer)

    # When I call .send_safe()
    sent = manager.send_safe("foobar", "PAYLOAD")

    # Then it should have failed
    sent.should.be.false

    # And it should not pack the value
    serializer.pack.called.should.be.false


@patch("agentzero.core.SocketManager.wait_until_ready")
def test_socket_manager_recv_safe(wait_until_ready):
    (
        "SocketManager().recv_safe() should deserialize "
        "after receiving, using the configured backend"
    )

    # Background: wait_until_ready is mocked to return the socket
    wait_until_ready.side_effect = lambda name, *args: manager.sockets[name]

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a serializer
    serializer = Mock(name="serializer")

    # And a socket manager
    manager = SocketManager(zmq, context, serialization_backend=serializer)

    # And a socket
    socket = manager.create("foobar", zmq.REP)

    # When I call .recv_safe()
    result = manager.recv_safe("foobar")

    # Then it should have unpacked the payload after receiving
    serializer.unpack.assert_called_once_with(socket.recv_string.return_value)

    # And the result should be the unpacked value
    result.should.equal(serializer.unpack.return_value)


@patch("agentzero.core.SocketManager.wait_until_ready")
def test_socket_manager_recv_safe_not_ready(wait_until_ready):
    (
        "SocketManager().recv_safe() should return None when the socket is not ready"
    )

    # Background: wait_until_ready is mocked to return None
    wait_until_ready.return_value = None

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a serializer
    serializer = Mock(name="serializer")

    # And a socket manager
    manager = SocketManager(zmq, context, serialization_backend=serializer)

    # When I call .recv_safe()
    result = manager.recv_safe("foobar")

    # Then it should never had anything to unpack
    serializer.unpack.called.should.be.false

    # And the result should be None
    result.should.be.none


def test_socket_manager_publish_safe():
    (
        "SocketManager().publish_safe() should serialize "
        "before sending, using the configured backend"
    )

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a serializer
    serializer = Mock(name="serializer")
    serializer.pack.side_effect = lambda x: "<pac({})ked>".format(repr(x))
    # And a socket manager
    manager = SocketManager(zmq, context, serialization_backend=serializer)

    # And a socket
    socket = manager.create("foobar", zmq.REP)

    # When I call .publish_safe()
    manager.publish_safe("foobar", "topic", "PAYLOAD")

    # Then it should have packed the payload before sending
    serializer.pack.assert_called_once_with("PAYLOAD")
    serializer.pack.return_value = "packed"

    socket.send_multipart.assert_called_once_with(
        [cast_bytes("topic"), cast_bytes("<pac('PAYLOAD')ked>")]
    )


def test_get_log_handler():
    ("SocketManager().get_log_handler() should return a ZMQPubHandler")

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a serializer
    serializer = Mock(name="serializer")

    # And a socket manager
    manager = SocketManager(zmq, context, serialization_backend=serializer)

    # When I call get_log_handler()
    handler = manager.get_log_handler("foo")

    # Then it should have returned a ZMQPubHandler
    handler.should.be.a("agentzero.core.ZMQPubHandler")


@patch("agentzero.core.SocketManager.get_by_name")
def test_socket_manager_subscribe(get_by_name):
    ("SocketManager().subscribe() should yield the topic and yield an Event")

    # Background: wait_until_ready is mocked to return the socket
    socket = Mock(name='<socket(name="foobar")>')
    get_by_name.side_effect = [socket, socket, socket, socket, socket, None]

    socket.recv_multipart.side_effect = [
        ["metrics:whatevs", "the-data"],
        ["action", "test"],
    ]

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a serializer
    serializer = Mock(name="serializer")

    # And a socket manager
    manager = SocketManager(zmq, context, serialization_backend=serializer)

    # And a socket
    socket = manager.create("foobar", zmq.REP)

    # When I perform one iteration in the subscriber
    events = list(manager.subscribe("foobar"))
    events.should.have.length_of(2)
    event1, event2 = events
    topic1, payload1 = event1.topic, event1.data

    # Then it should have unpacked the payload after receiving
    serializer.unpack.assert_has_calls([call("the-data"), call("test")])

    # And the result should be the unpacked value
    payload1.should.equal(serializer.unpack.return_value)

    # And the topic should be the expected
    topic1.should.equal("metrics:whatevs")

    event2.should.be.an(Event)


@patch("agentzero.core.SocketManager.get_by_name")
def test_socket_manager_subscribe_invalid_callable(get_by_name):
    (
        "SocketManager().subscribe() should raise TypeError "
        "if the keep_polling callable is not callable"
    )

    # Background: wait_until_ready is mocked to return the socket
    socket = get_by_name.return_value
    socket.recv_multipart.return_value = ["metrics:whatevs", "the-data"]

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a serializer
    serializer = Mock(name="serializer")

    # And a socket manager
    manager = SocketManager(zmq, context, serialization_backend=serializer)

    # And a socket
    socket = manager.create("foobar", zmq.REP)

    # When I perform one iteration in the subscriber
    when_called = list.when.called_with(
        manager.subscribe("foobar", keep_polling="not a callable")
    )
    when_called.should.have.raised(
        TypeError,
        "SocketManager.subscribe parameter keep_polling must be a function or callable that returns a boolean",
    )


@patch("agentzero.core.SocketManager.set_topic")
@patch("agentzero.core.SocketManager.wait_until_ready")
def test_socket_manager_recv_event_safe(wait_until_ready, set_topic):
    (
        "SocketManager().recv_event_safe() should set the topic "
        "on the given socket, wait for data to become available "
        "and return it"
    )

    # Background: wait_until_ready is mocked to return the socket
    wait_until_ready.side_effect = lambda name, *args: manager.sockets[name]

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a serializer
    serializer = Mock(name="serializer")

    # And a socket manager
    manager = SocketManager(zmq, context, serialization_backend=serializer)

    # And a socket
    socket = manager.create("foobar", zmq.REP)
    socket.recv_multipart.return_value = b"a fake topic", "the-raw-payload"

    # When I call .recv_event_safe()
    result = manager.recv_event_safe("foobar", topic=b"helloworld")

    # Then it should have unpacked the payload after receiving
    serializer.unpack.assert_called_once_with("the-raw-payload")

    # And the result should be the unpacked value
    result.should.be.an(Event)


@patch("agentzero.core.SocketManager.set_topic")
@patch("agentzero.core.SocketManager.wait_until_ready")
def test_socket_manager_recv_event_safe_missing_socket(
    wait_until_ready, set_topic
):
    (
        "SocketManager().recv_event_safe() should return None when the socket is not ready"
    )

    # Background: wait_until_ready is mocked to return None
    wait_until_ready.return_value = None

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a serializer
    serializer = Mock(name="serializer")

    # And a socket manager
    manager = SocketManager(zmq, context, serialization_backend=serializer)

    # And a socket
    socket = manager.create("foobar", zmq.REP)
    socket.recv_multipart.return_value = b"a fake topic", "the-raw-payload"

    # When I call .recv_event_safe()
    result = manager.recv_event_safe("foobar", topic=b"helloworld")

    # And the result should be None
    result.should.be.none


@only_py2
@patch("agentzero.core.SocketManager.set_topic")
@patch("agentzero.core.SocketManager.wait_until_ready")
def test_socket_manager_recv_event_safe_no_topic_py2(
    wait_until_ready, set_topic
):
    (
        "SocketManager().recv_event_safe() should raise an exeption when the topic is not a string"
    )

    # Background: wait_until_ready is mocked to return the socket
    wait_until_ready.side_effect = lambda name, *args: manager.sockets[name]

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a serializer
    serializer = Mock(name="serializer")

    # And a socket manager
    manager = SocketManager(zmq, context, serialization_backend=serializer)

    # And a socket
    socket = manager.create("foobar", zmq.REP)
    socket.recv_multipart.return_value = b"a fake topic", "the-raw-payload"

    # When I call .recv_event_safe()
    when_called = manager.recv_event_safe.when.called_with(
        "foobar", topic={"boom"}
    )

    # Then it should have raised and exception
    when_called.should.have.raised(
        TypeError,
        "recv_event_safe() takes a string, None "
        "or False as argument, received "
        "set(['boom'])(<type 'set'>) instead",
    )


@only_py3
@patch("agentzero.core.SocketManager.set_topic")
@patch("agentzero.core.SocketManager.wait_until_ready")
def test_socket_manager_recv_event_safe_no_topic_py3(
    wait_until_ready, set_topic
):
    (
        "SocketManager().recv_event_safe() should raise an exeption when the topic is not a string"
    )

    # Background: wait_until_ready is mocked to return the socket
    wait_until_ready.side_effect = lambda name, *args: manager.sockets[name]

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a serializer
    serializer = Mock(name="serializer")

    # And a socket manager
    manager = SocketManager(zmq, context, serialization_backend=serializer)

    # And a socket
    socket = manager.create("foobar", zmq.REP)
    socket.recv_multipart.return_value = b"a fake topic", "the-raw-payload"

    # When I call .recv_event_safe()
    when_called = manager.recv_event_safe.when.called_with(
        "foobar", topic={"boom"}
    )

    # Then it should have raised and exception
    when_called.should.have.raised(
        TypeError,
        "recv_event_safe() takes a string, None "
        "or False as argument, received "
        "{'boom'}(<class 'set'>) instead",
    )


@patch("agentzero.core.SocketManager.get_by_name")
def test_socket_manager_set_topic(get_by_name):
    (
        "SocketManager().set_topic() should retrieve the socket by "
        "name and set its subscription topic"
    )

    # Background: get_by_name is mocked
    socket = get_by_name.return_value

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a serializer
    serializer = Mock(name="serializer")

    # And a socket manager
    manager = SocketManager(zmq, context, serialization_backend=serializer)

    # When I call set topic
    manager.set_topic("the-socket-name", "the-topic-name")

    # Then it should have retrieved the socket by name
    get_by_name.assert_called_once_with("the-socket-name")

    # And the topic should have been set in that socket
    socket.setsockopt.assert_called_once_with(zmq.SUBSCRIBE, b"the-topic-name")


@patch("agentzero.core.SocketManager.get_by_name")
def test_socket_close(get_by_name):
    (
        "SocketManager().close() should unregister, pop it "
        "from the list of connected sockets and then close"
    )

    socket = get_by_name.return_value

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager
    manager = SocketManager(zmq, context)
    manager.poller = Mock(name="poller")
    manager.addresses = {"foobar": "wooot"}
    # When I call close
    manager.close("foobar")

    # Then it should have unregistered the socket with the poller
    manager.poller.unregister.assert_called_once_with(socket)

    # And the socket should have been removed from the internal addresses
    manager.addresses.should.be.empty

    # And socket.close should have been called
    socket.close.assert_called_once_with()


@patch("agentzero.core.SocketManager.get_by_name")
def test_socket_close_no_socket(get_by_name):
    (
        "SocketManager().close() should do nothing if a socket "
        "with that given name does not exist"
    )

    # Background: no sockets will be returned by get_by_name
    get_by_name.return_value = None

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager
    manager = SocketManager(zmq, context)
    manager.poller = Mock(name="poller")
    # When I call close
    manager.close("foobar")

    # Then it should not have called unregister
    manager.poller.unregister.called.should.be.false


@patch("agentzero.core.SocketManager.engage")
@patch("agentzero.core.SocketManager.register_socket")
@patch("agentzero.core.SocketManager.get_by_name")
def test_socket_disconnect(get_by_name, register_socket, engage):
    (
        "SocketManager().disconnect() should get by name, unregister then "
        "disconnect to the given address."
    )
    socket = get_by_name.return_value

    # Given a zmq mock
    zmq = Mock()
    poller = zmq.Poller.return_value

    # And a poller that raises an exception upon unregister
    poller.unregister.side_effect = RuntimeError("boom")

    # And a context
    context = Mock()

    # And a socket manager
    manager = SocketManager(zmq, context)
    manager.addresses = {"foobar": "baz", "another": "socket"}
    # When I call disconnect
    manager.disconnect("foobar").should.be.true

    # Then it should have removed the socket address from the table
    manager.addresses.should.equal({"another": "socket"})
    socket.disconnect.assert_has_calls([call("baz")])
    socket.disconnect.call_count.should.equal(1)


@patch("agentzero.core.SocketManager.engage")
@patch("agentzero.core.SocketManager.register_socket")
@patch("agentzero.core.SocketManager.get_by_name")
def test_socket_disconnect_not_registered(get_by_name, register_socket, engage):
    (
        "SocketManager().disconnect() should return False if no sockets are registered with that name"
    )
    # Background: get_by_name returns None
    socket = get_by_name.return_value

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager without registered sockets
    manager = SocketManager(zmq, context)
    manager.addresses = {}
    # When I call disconnect
    result = manager.disconnect("foobar")

    # Then it should return true
    result.should.be.true

    # But socket.disconnect
    socket.disconnect.call_count.should.equal(0)


@patch("agentzero.core.SocketManager.engage")
@patch("agentzero.core.SocketManager.register_socket")
@patch("agentzero.core.SocketManager.get_by_name")
def test_socket_disconnect_not_available(get_by_name, register_socket, engage):
    (
        "SocketManager().disconnect() should return False if no sockets are available with that name"
    )
    # Background: get_by_name returns None
    get_by_name.return_value = None

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    manager = SocketManager(zmq, context)
    # When I call disconnect
    result = manager.disconnect("foobar")

    # Then it should return false
    result.should.be.false


@patch("agentzero.core.ZMQPubHandler")
@patch("agentzero.core.SocketManager.get_by_name")
@patch("agentzero.core.SocketManager.publish_safe")
def test_socket_get_logger(publish_safe, get_by_name, ZMQPubHandler):
    (
        "SocketManager().get_logger() should return a logger"
        " with an attached ZMQPubHandler"
    )
    # Background: get_by_name returns None
    get_by_name.return_value = None

    # Given a zmq mock
    zmq = Mock()

    # And a context
    context = Mock()

    # And a socket manager without registered sockets
    manager = SocketManager(zmq, context)
    # When I call disconnect
    logger = manager.get_logger("foobar")

    # Then it should return false
    logger.should.be.a("logging.Logger")
    logger.handlers.should.equal([ZMQPubHandler.return_value])
