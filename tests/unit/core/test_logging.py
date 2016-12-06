#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from freezegun import freeze_time
from mock import Mock
from agentzero.core import ZMQPubHandler


@freeze_time('2016-02-25T19:00:00Z')
def test_emit():
    ('ZMQPubHandler().emit() should publish with the given socket name')

    # Given a mocked socket manager
    sockets = Mock(name='SocketManager')

    # And an instance of ZMQPubHandler
    handler = ZMQPubHandler(sockets, socket_name='foo', topic_name='important')

    # And a logger using it
    logger = logging.getLogger('test-logging-1')
    logger.handlers = [handler]

    # When I call emit
    logger.info("hello world %s", 'baz')

    # Then it should have published
    sockets.publish_safe.assert_called_once_with('foo', 'important', {
        'msg': '[2016-02-25T19:00:00Z] INFO test_logging.py:24 - hello world baz\n',
        'args': ('baz', ),
        'level': 20
    })
