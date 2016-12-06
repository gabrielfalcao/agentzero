import zmq.green as zmq
from agentzero.core import SocketManager


class Pipeline(object):
    steps = []

    def __init__(self):
        self.context = zmq.Context()
        self.sockets = SocketManager(zmq, self.context)
        self.sockets.create('pipe-sub', zmq.SUB)
        self.sockets.create('pipe-in', zmq.PULL)
        self.sockets.create('pipe-out', zmq.PUSH)
        self.children = []
