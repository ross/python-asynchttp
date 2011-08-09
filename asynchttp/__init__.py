#
#
#

from __future__ import absolute_import

from Queue import Queue
from threading import Event, Thread
import httplib2
import logging

logger = logging.getLogger(__name__)
#logger.addHandler(logging.NullHandler())


class Promise:

    def __init__(self, callback=None):
        self.__flag = Event()
        self.__callback = callback

    def fulfill(self, response, content, exception=None):
        self.response = response
        self.content = content
        self.exception = exception
        if self.__callback is not None:
            try:
                self.__callback(self)
            except Exception, e:
                logger.exception('callback threw an exception')
                if self.exception is None:
                    self.exception = e
        self.__flag.set()

    def done(self):
        return self.__flag.is_set()

    def __wait(self):
        self.__flag.wait()
        if self.exception:
            raise self.exception

    def get_response(self):
        self.__wait()
        return self.response

    def get_content(self):
        self.__wait()
        return self.content

    def __repr__(self):
        return '<Response({0})>'.format(self.done())


# TODO: is there a better way to do this? it's really just a proxy that lets us
# make sure the promise has been fulfilled
class Response(dict):

    def __init__(self, promise):
        self.__promise = promise

    def __getitem__(self, key):
        return self.__promise.get_response()[key]

    def __contains__(self, key):
        return self.__promise.get_response().__contains__(key)

    def keys(self):
        return self.__promise.get_response().keys()

    def values(self):
        return self.__promise.get_response().values()

    def items(self):
        return self.__promise.get_response().items()

    def __iter__(self):
        return self.__promise.get_response().__iter__()

    def __len__(self):
        return self.__promise.get_response().__len__()

    def __setitem__(self, key, value):
        return self.__promise.get_response().__setitem__(key, value)

    def __delitem__(self, key):
        return self.__promise.get_response().__delitem__(key)

    def __eq__(self, other):
        return self.__promise.get_response().__eq__(other)

    def __ne__(self, other):
        return self.__promise.get_response().__ne__(other)

    def __getattr__(self, name):
        return getattr(self.__promise.get_response(), name)


class Content:

    def __init__(self, promise):
        self.__promise = promise

    def __getattr__(self, name):
        return getattr(self.__promise.get_content(), name)

    def __str__(self):
        return self.__promise.get_content()

    def __repr__(self):
        return self.__promise.get_content()


class _Worker(Thread):

    def __init__(self, http, handle):
        Thread.__init__(self)
        self.__http = http
        self.__handle = handle

    def run(self):
        # we'll only live while there's work for us to do
        while not self.__http._has_work():
            (promise, args, kwargs) = self.__http._get_work()
            try:
                response, content = self.__handle.request(*args, **kwargs)
                promise.fulfill(response, content)
            except Exception, e:
                logger.warn('request raised exception: %s', e)
                promise.fulfill(None, None, e)

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

    # TODO: changing attributes won't update existing clients
    def __setattr__(self, name, value):
        if '_Http__initializsed' not in self.__dict__:
            # for the __init__ method
            self.__dict__[name] = value
        elif name not in self.__dict__:
            # anything we don't know about we need to pass along to the clients
            # follow_redirects
            # follow_all_redirects
            # force_exception_to_status_code
            # optimistic_concurrency_methods
            # ignore_etag
            self.__client_attributes[name] = value
        dict.__setattr__(self, name, value)

    def __nonzero__(self):
        # we're always non-zero
        return True

    def __get_client(self):
        client = self.Client(*self.__client_args, **self.__client_kwargs)
        for method, params in self.__client_methods.items():
            getattr(client, method)(*params[0], **params[1])
        for attribute, value in self.__client_attributes.items():
            setattr(client, attribute, value)
        return client

    def request(self, *args, **kwargs):
        if 'callback' in kwargs:
            promise = Promise(kwargs['callback'])
            del kwargs['callback']
        else:
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

        return Response(promise), Content(promise)

    # stuff that only workers care about

    def _remove_worker(self, worker):
        self.__workers.remove(worker)

    def _has_work(self):
        return self.__queue.empty()

    def _get_work(self):
        return self.__queue.get()
