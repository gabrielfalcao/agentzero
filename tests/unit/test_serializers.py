#!/usr/bin/env python
# -*- coding: utf-8 -*-
from six import text_type
from agentzero.serializers import JSON


def test_json_pack():
    ('serializers.JSON.pack() should ensure an unicode string')

    # Given a JSON serialier
    serializer = JSON()

    # When I call pack with a dictionary
    string = serializer.pack({
        'foo': 'bar'
    })

    # Then it should have returned a string
    string.should.be.a(text_type)


def test_json_unpack():
    ('serializers.JSON.pack() should ensure parse a json')

    # Given a JSON dserialier
    serializer = JSON()

    # When I call unpack with a string
    data = serializer.unpack('{"foo": "bar"}')

    # Then it should have returned a dict
    data.should.equal({
        'foo': 'bar'
    })
