#
#
#

from __future__ import absolute_import

__version__ = '0.0.4'
__date__ = '2011-10-27'
__author__ = 'Ross McFarland'
__credits__ = '''Ross McFarland'''

from Queue import Queue
from sys import exc_info
from threading import Event, Thread
from traceback import extract_stack, format_list
import httplib2
import logging


logger = logging.getLogger(__name__)
# apparently NullHandler doesn't always exist, this is a best effort to install
# it so that people don't get warnings from us when they're not using logging
try:
    logger.addHandler(logging.NullHandler())
except AttributeError:
    pass


class Promise:

    def __init__(self, callback=None):
        self.__flag = Event()
        self.__callback = callback
        # record the stack of our invocation, omit ourself and the call to our
        # ctor (-2, last 2)
        self.__stack = extract_stack()[:-2]
        logger.debug('%s.__init__', self)

    def fulfill(self, response, content, caught_exc_info=None):
        try:
            logger.debug('%s.fullfill', self)
            self.response = response
            self.content = content
            self.caught_exc_info = caught_exc_info
            if caught_exc_info:
                self.exception = caught_exc_info[1]
            if self.__callback is not None:
                logger.debug('%s.fullfill invoking callback', self)
                try:
                    self.__callback(self)
                except Exception, e:
                    logger.exception('%s.fullfill callback threw an exception,'
                                     ' %s, original invocation:\n%s', self, e,
                                     ''.join(format_list(self.__stack)))
                    if self.caught_exc_info is None:
                        self.caught_exc_info = exc_info()
                        self.exception = self.caught_exc_info[1]
        finally:
            # set flag no matter what else things can hang waiting for a
            # response
            self.__flag.set()

    def done(self):
        return self.__flag.is_set()

    def wait(self):
        logger.debug('%s.wait', self)
        self.__flag.wait()
        if self.caught_exc_info:
            logger.info('%s.wait: raising exception, %s, original invocation:'
                        '\n%s', self, self.caught_exc_info[1],
                        ''.join(format_list(self.__stack)))
            raise self.caught_exc_info[0], self.caught_exc_info[1], \
                    self.caught_exc_info[2]

    def get_response(self):
        self.wait()
        return self.response

    def get_content(self):
        self.wait()
        return self.content

    def __repr__(self):
        return '<Response({0}, {1})>'.format(id(self), self.done())


# TODO: is there a better way to do this? it's really just a proxy that lets us
# make sure the promise has been fulfilled
class Response:

    def __init__(self, promise):
        self.__promise = promise

    def __contains__(self, key):
        return self.__promise.get_response().__contains__(key)

    def __getitem__(self, key):
        return self.__promise.get_response()[key]

    def __setitem__(self, key, value):
        return self.__promise.get_response().__setitem__(key, value)

    def __delitem__(self, key):
        return self.__promise.get_response().__delitem__(key)

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

    def __getattr__(self, name):
        return getattr(self.__promise.get_response(), name)

    def __setattr__(self, name, value):
        if name.startswith('_Response__'):
            self.__dict__[name] = value
        else:
            setattr(self.__promise.get_response(), name, value)

    def done(self):
        return self.__promise.done()

    def wait(self):
        self.__promise.wait()


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
        logger.debug('%s.__init__', self)

    def run(self):
        logger.debug('%s.run', self)
        # we'll only live while there's work for us to do
        while not self.__http._has_work():
            (promise, args, kwargs) = self.__http._get_work()
            logger.debug('%s.run: work=%s', self, promise)
            try:
                response, content = self.__handle.request(*args, **kwargs)
                promise.fulfill(response, content)
            except Exception, e:
                logger.warn('%s.run: request raised exception: %s', self, e)
                promise.fulfill(None, None, exc_info())

        logger.debug('%s.run: done', self)
        self.__http._remove_worker(self)

    def __repr__(self):
        return '<Worker({0})>'.format(id(self))


class Http:
    Client = httplib2.Http

    def __init__(self, max_workers=5, *args, **kwargs):
        # NOTE: lowering max workers won't shutdown existing until the queue
        # has been depleted
        self.max_workers = max_workers

        self.__client_args = args
        self.__client_kwargs = kwargs
        self.__client_methods = {}

        self.__queue = Queue()
        self.__workers = []

        self.__initializsed = True
        logger.debug('%s.__init__', self)

    def add_credentials(self, *args, **kwargs):
        self.__client_methods['add_credentials'] = [args, kwargs]

    def add_certificate(self, *args, **kwargs):
        self.__client_methods['add_certificate'] = [args, kwargs]

    def __get_client(self):
        logger.debug('%s.__get_client', self)
        client = self.Client(*self.__client_args, **self.__client_kwargs)
        for method, params in self.__client_methods.items():
            getattr(client, method)(*params[0], **params[1])
        for attribute, value in self.__dict__.items():
            # don't copy max_workers or any of our 'private' attrs
            if attribute != 'max_workers' \
               and not attribute.startswith('_Http__'):
                setattr(client, attribute, value)
        return client

    def request(self, *args, **kwargs):
        logger.debug('%s.request: args=%s, kwargs=%s', self, args, kwargs)
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

    def __repr__(self):
        return '<Http({0})>'.format(id(self))
