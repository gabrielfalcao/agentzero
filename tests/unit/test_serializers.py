#!/usr/bin/env python
# -*- coding: utf-8 -*-
from six import binary_type
from agentzero.serializers import JSON
from agentzero.serializers import MSGPACK


def test_json_pack():
    ("serializers.JSON.pack() should ensure an unicode string")

    # Given a JSON serialier
    serializer = JSON()

    # When I call pack with a dictionary
    string = serializer.pack({"foo": "bar"})

    # Then it should have returned a string
    string.should.equal('{"foo":"bar"}')


def test_json_unpack():
    ("serializers.JSON.pack() should ensure parse a json")

    # Given a JSON dserialier
    serializer = JSON()

    # When I call unpack with a string
    packed = serializer.pack({"foo": "bar"})
    data = serializer.unpack(packed)

    # Then it should have returned a dict
    data.should.equal({"foo": "bar"})


def test_msgpack_pack():
    ("serializers.MSGPACK.pack() should ensure an unicode string")

    # Given a MSGPACK serialier
    serializer = MSGPACK()

    # When I call pack with a dictionary
    string = serializer.pack({"foo": "bar"})

    # Then it should have returned a string
    string.should.be.a(binary_type)


def test_msgpack_unpack():
    ("serializers.MSGPACK.pack() should ensure parse a msgpack")

    # Given a MSGPACK dserialier
    serializer = MSGPACK()

    # When I call unpack with a string
    packed = serializer.pack({"foo": "bar"})
    data = serializer.unpack(packed)

    # Then it should have returned a dict
    data.should.equal({b"foo": b"bar"})
