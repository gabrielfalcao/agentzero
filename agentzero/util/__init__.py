#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import time
import socket
import traceback
from datetime import datetime


__all__ = [
    'serialized_exception',
    'seconds_since',
    'get_free_tcp_port',
]


def get_free_tcp_port():
    """returns a TCP port that can be used for listen in the host.
    """
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(('', 0))
    host, port = tcp.getsockname()
    tcp.close()
    return port


def get_default_bind_address():
    return ':'.join([get_hostname(), bytes(get_free_tcp_port())])


def get_hostname():
    hostname = socket.gethostname()
    return hostname


def get_public_ip_address(hostname=None):
    hostname = hostname or get_hostname()
    ip_address = resolve_hostname(hostname)
    return ip_address


def extract_hostname_from_tcp_address(address):
    if not isinstance(address, basestring):
        return

    found = re.search(r'^tcp://([^:]+):(\d+)', address)
    if found:
        return found.group(1)


def resolve_hostname(hostname):
    if not hostname:
        return hostname
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return hostname


def fix_zeromq_tcp_address(address):
    address = address or ''
    hostname = resolve_hostname(extract_hostname_from_tcp_address(address))

    if not hostname:
        return address

    regex = r'^tcp://([^:]+)'
    replacement = 'tcp://{0}'.format(hostname)
    return re.sub(regex, replacement, address)


def get_public_zmq_address():
    hostport = get_default_bind_address()
    address = 'tcp://{0}'.format(hostport)
    return fix_zeromq_tcp_address(address)


def seconds_since(timestamp):
    return time.time() - timestamp


def datetime_from_seconds(timestamp):
    return datetime.utcfromtimestamp(timestamp)


def serialized_exception(e):
    exc_type = type(e)
    return {
        'module': bytes(exc_type.__module__),
        'name': bytes(exc_type.__name__),
        'traceback': traceback.format_exc(e)
    }
