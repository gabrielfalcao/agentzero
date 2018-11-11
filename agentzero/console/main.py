#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

"""
agentzero.console.main
-----------------------


here lives the ``entrypoint()`` that handle command line args

"""

from __future__ import unicode_literals
import zmq
import argparse
from zmq.devices import Device

# import warnings
# warnings.catch_warnings()
# warnings.simplefilter("ignore")


def entrypoint():
    """runs a ZMQ Device.

    :param ``--bind-in``: the ZMQ address to bind in
    :param ``--bind-out``: the ZMQ address to bind out
    :param ``--connect-in``: the ZMQ address to connect in
    :param ``--connect-out``: the ZMQ address to connect out

    :param ``--hwm-in``: the high-water-mark in
    :param ``--hwm-out``: the high-water-mark out
    ::

      $ agentzero queue \\
          --type-in=dealer
          --bind-in=tcp://0.0.0.0.2210 \\
          --type-out=router \\
          --bind-out=tcp://0.0.0.0.2211
    """

    parser = argparse.ArgumentParser(
        prog="agentzero (queue|pipeline|forwarder)",
        description="master server that orchestrates minions and controller by a backend API",
    )

    parser.add_argument("device_type", help="the type of ZMQ device to run")
    parser.add_argument("--bind-in", help="a valid zmq address")
    parser.add_argument("--bind-out", help="a valid zmq address")
    parser.add_argument("--connect-in", help="a valid zmq address")
    parser.add_argument("--connect-out", help="a valid zmq address")
    parser.add_argument(
        "--type-in", help="the type of zmq socket that should handle input data"
    )
    parser.add_argument(
        "--type-out",
        help="the type of zmq socket that should handle output data",
    )

    parser.add_argument(
        "--hwm-in",
        help="an integer representing the number of messages to buffer incoming data before either dropping messages or blocking process execution",
    )
    parser.add_argument(
        "--hwm-in",
        help="an integer representing the number of messages to buffer outcoming data before either dropping messages or blocking process execution",
    )

    args = parser.parse_args()

    device_type = getattr(zmq, args.device_type.upper())
    type_in = getattr(zmq, args.type_in.upper())
    type_out = getattr(zmq, args.type_out.upper())
    device = Device(device_type, type_in, type_out)
    device.run()
