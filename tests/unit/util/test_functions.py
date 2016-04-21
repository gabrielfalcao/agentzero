#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime

from mock import patch
from agentzero.util import seconds_since, datetime_from_seconds
from agentzero.util import get_free_tcp_port
from agentzero.util import serialized_exception
from agentzero.util import get_hostname
from agentzero.util import get_public_ip_address
from agentzero.util import get_public_zmq_address
from agentzero.util import extract_hostname_from_tcp_address
from agentzero.util import fix_zeromq_tcp_address


@patch('agentzero.util.time')
def test_seconds_since(time):
    ('util.seconds_since() should take a timestamp and '
     'subtract it from the current time')

    # Given that time.time() is mocked
    time.time.return_value = 10

    # When I call seconds_since
    result = seconds_since(7)

    # Then it should have been subtracted
    result.should.equal(3)


@patch('agentzero.util.socket')
def test_get_free_tcp_port(socket):
    ('util.get_free_tcp_port() should open a '
     'socket to retrieve its port, then close it')

    # Given that socket is mocked
    sock = socket.socket.return_value

    # And that .getsockname() is mocked
    sock.getsockname.return_value = ('localhost', 4321)

    # When I call .get_free_tcp_port()
    result = get_free_tcp_port()

    # Then it should return the port
    result.should.equal(4321)

    # And the socket should have been created as TCP/IP
    socket.socket.assert_called_once_with(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    # And it should have been bound to port 0
    sock.bind.assert_called_once_with(('', 0))

    # And it should have been closed
    sock.close.assert_called_once_with()


@patch('agentzero.util.traceback')
def test_serialized_exception(traceback):
    ('util.serialized_exception() should serialize the traceback')

    # Background: traceback.format_exc is mocked
    traceback.format_exc.return_value = 'the traceback'

    # Given an exception
    e = ValueError('boom')

    # When I call serialize it
    result = serialized_exception(e)

    # Then it should return a dict
    result.should.equal({
        'module': 'exceptions',
        'name': 'ValueError',
        'traceback': 'the traceback'
    })


def test_convert_from_seconds_to_datetime():
    ("util.datetime_from_seconds() should convert from epoch seconds to a datetime")

    date = datetime_from_seconds(1347517370)

    date.should.equal(datetime(2012, 9, 13, 6, 22, 50))


@patch('agentzero.util.socket')
def test_get_hostname(socket):
    ("util.get_hostname() should return the result of socket.gethostname()")

    get_hostname().should.equal(socket.gethostname.return_value)


@patch('agentzero.util.socket')
@patch('agentzero.util.get_hostname')
def test_get_public_ip_address(get_hostname, socket):
    ("util.get_public_ip_address() should get host by name")
    get_hostname.return_value = 'agentzero-mothership'

    socket.gethostbyname.return_value = '200.100.50.25'

    get_public_ip_address().should.equal('200.100.50.25')

    socket.gethostbyname.assert_called_once_with('agentzero-mothership')


def test_extract_hostname_from_tcp_address():
    ('util.extract_hostname_from_tcp_address() should return the hostname of a tcp address')

    result = extract_hostname_from_tcp_address('tcp://foobar.com:3000')
    result.should.equal('foobar.com')


def test_extract_hostname_from_tcp_address_not_string():
    ('util.extract_hostname_from_tcp_address() should return None if the given value is not a string')

    result = extract_hostname_from_tcp_address({'what': 'crazy'})
    result.should.be.none


@patch('agentzero.util.get_public_ip_address')
def test_fix_zeromq_tcp_address(get_public_ip_address):
    ('util.fix_zeromq_tcp_address()')

    extract_hostname_from_tcp_address.return_value = None
    get_public_ip_address.return_value = '192.168.2.42'

    result = fix_zeromq_tcp_address('ipc:///tmp/foobar.sock')

    result.should.equal('ipc:///tmp/foobar.sock')


@patch('agentzero.util.get_free_tcp_port')
@patch('agentzero.util.get_hostname')
def test_get_default_bind_address(get_hostname, get_free_tcp_port):
    ('util.get_default_bind_address() uses the hostname to determine the public address')

    get_free_tcp_port.return_value = 4000
    get_hostname.return_value = 'yourmachine'
    result = get_public_zmq_address()

    result.should.equal('tcp://yourmachine:4000')
