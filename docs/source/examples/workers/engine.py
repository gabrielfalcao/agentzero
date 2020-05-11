#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import sys
import time
import uuid
import random
import gevent
import hashlib
import logging
import coloredlogs
import gevent.pool
import gevent.monkey
import zmq.green as zmq

from speakers import Speaker
from collections import defaultdict
from agentzero.util import serialized_exception
from agentzero.core import SocketManager


class Job(dict):
    @property
    def id(self):
        return self.get('id', None)

    @property
    def type(self):
        return self.get('job_type', None)

    @classmethod
    def from_dict(cls, data):
        if not data:
            msg = 'Job.from_dict requires a non-empty dict as argument, instead got: {0}'
            raise ValueError(msg.format(repr(data)))

        return cls(data)

    @classmethod
    def new(cls, data):
        if not data:
            return

        data['id'] = str(uuid.uuid4())
        if not data.get('instructions'):
            data['instructions'] = {}

        return cls.from_dict(data)

    def to_dict(self):
        return dict(self)


class Worker(dict):
    @property
    def id(self):
        return self.get('id', None)

    @property
    def job_type(self):
        return self.get('job_type', None)

    @property
    def step_name(self):
        return self.get('step_name', None)

    @property
    def address(self):
        return self.get('address', None)

    @classmethod
    def from_event(cls, event):
        return cls(event.data)

    def __hash__(self):
        return hash(self.id)


class StorageBackend(object):
    def __init__(self):
        self.workers = {}
        self.workers_by_job_type = defaultdict(set)
        self.jobs_by_type = defaultdict(list)

    def register_worker(self, worker):
        if worker.id in self.workers:
            # already registered
            return False

        self.workers[worker.id] = worker
        self.workers_by_job_type[worker.job_type].add(worker.id)
        return True

    def unregister_worker(self, worker):
        self.workers.pop(worker.id, None)
        self.workers_by_job_type[worker.job_type].remove(worker.id)

    def enqueue_job(self, job):
        self.jobs_by_type[job.type].append(job)

    def dequeue_job_of_type(self, job_type):
        try:
            return self.jobs_by_type[job_type].pop(0)
        except IndexError:
            return None

    def get_next_available_worker_for_type(self, job_type):
        worker_ids = list(self.workers_by_job_type[job_type])
        if not worker_ids:
            return None

        try:
            wid = random.choice(worker_ids)
            return self.workers.get(wid)
        except KeyError:
            return None


class Pipeline(object):
    def __init__(self, name, steps=None):
        steps = steps or []
        self.name = name
        self.actions = Speaker(
            'actions',
            [
                'available',
                'failed',
                'started',
                'success',
                'metric',
                'error',
                'logs',
            ]
        )
        self.steps = [s.job_type for s in steps]
        self.total_steps = len(steps)
        self.context = zmq.Context()
        self.sockets = SocketManager(zmq, self.context)
        self.sockets.create('step-events', zmq.SUB)
        self.sockets.create('jobs-in', zmq.PULL)
        for step in self.steps:
            self.sockets.create(step, zmq.PUSH)

        for action in list(self.actions.actions.keys()):
            self.bind_action(action)

        self.total_actions = len(self.actions.actions)
        self.pool = gevent.pool.Pool(self.total_actions ** (self.total_steps + 1))
        self.greenlets = []
        self._allowed_to_run = True
        self.default_interval = 0.1
        self.backend = StorageBackend()
        self.logger = logging.getLogger('pipeline')

    def on_started(self, event):
        worker = Worker.from_event(event)
        self.logger.info('%s [%s] started to process a job', worker.job_type, worker.id)

    def on_available(self, event):
        worker = Worker.from_event(event)
        if self.backend.register_worker(worker):
            self.sockets.connect(worker.job_type, worker.address, zmq.POLLOUT)
            self.logger.info('connected to worker: [%s]', dict(worker))

    def on_failed(self, event):
        worker = Worker.from_event(event)
        self.logger.warning('%s [%s] failed', worker.job_type, worker.id)

    def on_success(self, event):
        worker = Worker.from_event(event)
        self.logger.info('%s [%s] success', worker.job_type, worker.id)
        self.enqueue_next_job(event.data)

    def on_metric(self, event):
        self.logger.info(' '.join([event.topic, event.data]))

    def on_error(self, event):
        worker = Worker.from_event(event)
        self.logger.warning('%s [%s] errored: %s', worker.job_type, worker.id, event)

    def on_logs(self, event):
        msg = event.data.pop('msg', None)
        if msg:
            self.logger.debug(msg)

    def enqueue_next_job(self, data):
        result = data.pop('instructions')
        job = Job.from_dict(data)
        job['instructions'] = result

        step_index = self.steps.index(job.type)

        try:
            next_job_type = self.steps[step_index + 1]
        except IndexError:
            next_job_type = None

        if next_job_type:
            self.logger.info("enqueuing next job: %s", next_job_type)
            job['job_type'] = next_job_type
            self.backend.enqueue_job(job)

    def bind_action(self, name, method=None):
        action = getattr(self.actions, name, None)
        if not action:
            raise KeyError('undefined action: {0}'.format(name))

        method = method or getattr(self, 'on_{0}'.format(name), None)
        if not method:
            raise TypeError('{0} does not have method {1}(self, topic, data)'.format(self.__class__, name))

        action(lambda _, event: self.spawn(method, event))

    def should_run(self):
        return self._allowed_to_run

    def listen(self, subscriber_bind_address='tcp://127.0.0.1:6000', pull_bind_address='tcp://127.0.0.1:7000'):
        self.sockets.bind('step-events', subscriber_bind_address, zmq.POLLIN)
        self.sockets.bind('jobs-in', pull_bind_address, zmq.POLLIN)
        self.logger.info('listening for events on %s', subscriber_bind_address)
        self.logger.info('listening for instructions on %s', pull_bind_address)

    def route_event(self, event):
        if not event:
            return

        ROUTES = {
            re.compile(r'available'): self.actions.available,
            re.compile(r'failed'): self.actions.failed,
            re.compile(r'success'): self.actions.success,
            re.compile(r'started'): self.actions.started,
            re.compile(r'metric'): self.actions.metric,
            re.compile(r'logs'): self.actions.logs,
            re.compile(r'error'): self.actions.error,
        }
        matched = False
        for regex, action in list(ROUTES.items()):
            if regex.search(event.topic):
                action.shout(event)
                matched = True

        if not matched:
            print('unmatched event', event.topic, event.data)

    def drain_jobs_in(self):
        while self.should_run():
            data = self.sockets.recv_safe('jobs-in')
            if not data:
                gevent.sleep(0)
                continue

            job = Job.new(data)
            self.backend.enqueue_job(job)
            gevent.sleep(0)

    def drain_jobs_out(self):
        iteration = -1
        while self.should_run():
            iteration += 1

            index = iteration % len(self.steps)

            job_type = self.steps[index]
            worker = self.backend.get_next_available_worker_for_type(job_type)

            if not worker:
                gevent.sleep(0)
                continue

            job = self.backend.dequeue_job_of_type(job_type)
            if not job:
                gevent.sleep(0)
                continue

            self.sockets.send_safe(worker.job_type, job.to_dict())
            gevent.sleep(0)

    def spawn(self, *args, **kw):
        self.greenlets.append(
            self.pool.spawn(*args, **kw)
        )

    def idle(self):
        gevent.sleep(0)

    def loop(self):
        self.listen()
        self.spawn(self.drain_events)
        self.spawn(self.drain_jobs_in)
        self.spawn(self.drain_jobs_out)
        while self.should_run():
            gevent.sleep(5)

    def drain_events(self):
        # drain events
        while self.should_run():
            event = self.sockets.recv_event_safe('step-events')
            if event:
                self.route_event(event)
                gevent.sleep(0)
            else:
                self.idle()


class Step(object):
    def __init__(self, pull_bind_address='tcp://127.0.0.1', subscriber_connect_address='tcp://127.0.0.1:6000', concurrency=100, timeout=1):
        self.context = zmq.Context()
        self.sockets = SocketManager(zmq, self.context)
        self.sockets.create('pull-in', zmq.PULL)
        # self.sockets.set_socket_option('pull-in', zmq.RCVHWM, concurrency)
        self.sockets.create('events', zmq.PUB)
        self.name = self.__class__.__name__
        self.subscriber_connect_address = subscriber_connect_address
        self._allowed_to_run = True
        self.pool = gevent.pool.Pool(concurrency + 1)
        self.timeout = timeout
        self.pull_bind_address = pull_bind_address
        self.id = str(uuid.uuid4())
        self.logger = self.sockets.get_logger('events', 'logs', 'logs')

    def listen(self):
        _, self.address = self.sockets.bind_to_random_port('pull-in', zmq.POLLIN, local_address=self.pull_bind_address)
        gevent.sleep(1)

    def connect(self):
        self.sockets.connect('events', self.subscriber_connect_address, zmq.POLLOUT)
        gevent.sleep(1)
        self.notify_available()

    def notify_available(self):
        self.send_event('available', self.to_dict())

    def should_run(self):
        gevent.sleep(0.1)
        return self._allowed_to_run

    def send_event(self, name, data):
        self.sockets.publish_safe('events', name, data)

    def dispatch(self, job):
        try:
            start = time.time()
            job['job_started_at'] = start
            self.send_event('job:started', job)
            job['instructions'] = self.execute(job['instructions'])
            job['job_finished_at'] = time.time()
            self.logger.info("done processing %s", job)

        except Exception as e:
            job['job_finished_at'] = time.time()
            job['error'] = serialized_exception(e)
            self.send_event('job:error', job)
            job['success'] = False
            self.send_event('job:failed', job)
            self.logger.exception('failed to execute job {id}'.format(**dict(job)))
        finally:
            end = time.time()
            job['end'] = end

        if job.get('instructions'):
            self.send_event('job:success', job)

        else:
            self.send_event('job:failed', job)

    def to_dict(self):
        return dict(
            id=self.id,
            address=self.address,
            job_type=self.job_type,
            step_name=self.name,
        )

    def loop(self):
        self.listen()
        self.connect()
        self.logger.info('listening for jobs on %s', self.address)
        while self.should_run():
            if self.pool.free_count() == 0:
                self.logger.info('waiting for an execution slot')
                self.pool.wait_available()

            job = self.sockets.recv_safe('pull-in')

            if job:
                self.logger.info('received job')
                self.pool.spawn(self.dispatch, job)
            else:
                self.notify_available()
                gevent.sleep(1)


class GenerateFile(Step):
    job_type = 'generate-file'

    def execute(self, instructions):
        path = '/tmp/example-{0}.disposable'.format(uuid.uuid4())
        open(path, 'wb').write('\n'.join([str(uuid.uuid4()) for _ in range(10)]))
        return {'file_path': path}


class HashFile(Step):
    job_type = 'calculate-hash'

    def execute(self, instructions):
        data = open(instructions['file_path'], 'rb').read()
        return {'hash': hashlib.sha1(data).hexdigest(), 'file_path': instructions['file_path']}


class RemoveFile(Step):
    job_type = 'delete-file'

    def execute(self, instructions):
        path = instructions['file_path']
        if os.path.exists(path):
            os.unlink(path)

        return {'deleted_path': path}


def run_pipeline():
    pipeline = Pipeline(
        'example1',
        [
            GenerateFile,
            HashFile,
            RemoveFile,
        ]
    )
    coloredlogs.install(logging.DEBUG)
    for x in range(300):
        gevent.spawn(pipeline.backend.enqueue_job, Job.new(dict(job_type='generate-file')))

    pipeline.loop()


def run_generate_file_step():
    item = GenerateFile()
    coloredlogs.install(logging.DEBUG)
    item.loop()


def run_hash_file_step():
    step = HashFile()
    coloredlogs.install(logging.DEBUG)
    step.loop()


def run_remove_file_step():
    step = RemoveFile()
    coloredlogs.install(logging.DEBUG)
    step.loop()


if __name__ == '__main__':
    if 'pipeline' in sys.argv:
        run_pipeline()

    elif 'step1' in sys.argv:
        run_generate_file_step()

    elif 'step2' in sys.argv:
        run_hash_file_step()

    elif 'step3' in sys.argv:
        run_remove_file_step()
