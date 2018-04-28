#!/usr/bin/env python
# -*- coding: utf-8 -*-
import msgpack
from six import text_type
from zmq.utils import jsonapi as json


class BaseSerializer(object):  # pragma: no cover
    """base class for all serializers

    all base classes must implement the methods ``pack`` and ``unpack``
    """
    def __init__(self, *args, **kw):
        self.initialize(*args, **kw)

    def initialize(self, *args, **kw):
        """optional method that can me overwriten by subclasses. It takes any
        args and kwargs that were passed to the constructor.
        """

    def pack(self, item):
        """Must receive a python object and return a safe primitive (dict,
        list, int, string, etc).
        """
        raise NotImplementedError

    def unpack(self, item):
        """must receive a *string* and return a python object"""
        raise NotImplementedError


class JSON(BaseSerializer):
    """Serializes to and from :py:mod:`json`"""

    def pack(self, item):
        return json.dumps(item, default=text_type).decode('utf-8')

    def unpack(self, item):
        if isinstance(item, text_type):
            item = item.encode('utf-8')

        return json.loads(item)


class MSGPACK(BaseSerializer):
    """Serializes to and from :py:mod:`msgpack`"""

    def pack(self, item):
        return msgpack.packb(item, default=text_type, use_bin_type=True)

    def unpack(self, item):
        return msgpack.unpackb(item)
