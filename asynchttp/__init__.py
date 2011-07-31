#
#
#

from __future__ import absolute_import

from Queue import Queue
from threading import Event, Thread
import httplib2


class Promise:

    def __init__(self, callback=None):
        self.__flag = Event()
        self.__callback = callback

    def set(self, response, content):
        '''called when the response is back'''
        self.response = response
        self.content = content
        if self.__callback is not None:
            self.__callback(self)
        self.__flag.set()
        self.__flag = None

    def __done(self):
        return self.__flag is None

    def __getattr__(self, name):
        if name == 'done':
            return self.__done()
        elif self.__flag and (name == 'response' or name == 'content'):
            self.__flag.wait()
            return self.__dict__[name]
        raise AttributeError("%r object has no attribute %r" %
                             (type(self).__name__, name))

    def __repr__(self):
        return '<Response({0})>'.format(self.__done())


class _Worker(Thread):

    def __init__(self, http, handle):
        Thread.__init__(self)
        self.__http = http
        self.__handle = handle

    def run(self):
        # we'll only live while there's work for us to do
        while not self.__http._has_work():
            (promise, args, kwargs) = self.__http._get_work()
            response, content = self.__handle.request(*args, **kwargs)
            promise.set(response, content)
        self.__http._remove_worker(self)


class Http(dict):
    Client = httplib2.Http

    def __init__(self, max_workers=5, *args, **kwargs):
        # NOTE: lowering max workers won't shutdown existing until the queue
        # has been depleted
        self.max_workers = max_workers

        self.__client_args = args
        self.__client_kwargs = kwargs
        self.__client_methods = {}
        self.__client_attributes = {}

        self.__queue = Queue()
        self.__workers = []

        self.__initializsed = True

    # TODO: some way to do this generically?
    def add_credentials(self, *args, **kwargs):
        self.__client_methods['add_credentials'] = [args, kwargs]

    def add_certificate(self, *args, **kwargs):
        self.__client_methods['add_certificate'] = [args, kwargs]

    def __setattr__(self, name, value):
        if '_Http__initializsed' not in self.__dict__:
            # for the __init__ method
            self.__dict__[name] = value
        elif name in self.__dict__:
            # max_workers
            dict.__setattr__(self, name, value)
        else:
            # follow_redirects
            # follow_all_redirects
            # force_exception_to_status_code
            # optimistic_concurrency_methods
            # ignore_etag
            self.__client_attributes[name] = value

    def __get_client(self):
        client = self.Client(*self.__client_args, **self.__client_kwargs)
        for method, params in self.__client_methods.items():
            getattr(client, method)(*params[0], **params[1])
        for attribute, value in self.__client_attributes.items():
            setattr(client, attribute, value)
        return client

    def request(self, *args, **kwargs):
        promise = Promise()

        # we need to queue the work before we create the worker to work on it
        # to avoid the worker looking for a job, not finding one, and quitting
        # before we get a chance to add it
        self.__queue.put((promise, args, kwargs))
        if len(self.__workers) < self.max_workers:
            client = self.__get_client()
            worker = _Worker(self, client)
            # we have to add workers to the list before starting them or else
            # they may start up, have the job they were created for taken away
            # from them by someone who's done and the immeidately quit
            self.__workers.append(worker)
            worker.start()

        return promise

    # stuff that only workers care about

    def _remove_worker(self, worker):
        self.__workers.remove(worker)

    def _has_work(self):
        return self.__queue.empty()

    def _get_work(self):
        return self.__queue.get()
