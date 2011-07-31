#
#
#

from __future__ import absolute_import

from asynchttp import Http
from datetime import datetime, timedelta
from mockito import inorder, mock, verify, when
from mockito.invocation import AnswerSelector, CompositeAnswer, Return
from random import randrange
from threading import Thread
from time import sleep
from unittest2 import TestCase
import httplib2


# holy hack batman. i need a way to get a slow response, this is the best thing
# i could come up with using mockito, i should probably turn this in to a patch
class SleepingReturn(Return):

    def __init__(self, delay, return_value):
        Return.__init__(self, return_value)
        self.delay = delay

    def answer(self):
        sleep(self.delay)
        return Return.answer(self)


def sleepingThenReturn(self, delay, *return_values):
    for return_value in return_values:
        answer = SleepingReturn(delay, return_value)
        if not self.answer:
            self.answer = CompositeAnswer(answer)
            self.invocation.stub_with(self.answer)
        else:
            self.answer.add(answer)
    return self


AnswerSelector.sleepingThenReturn = sleepingThenReturn


class HttpTest(TestCase):
    client = None

    def setUp(self):
        Http.Client = lambda x: HttpTest.client

    def tearDown(self):
        Http.Client = httplib2.Http

    def test_basic(self):

        url = 'http://localhost'

        # set up the mock
        client = mock()
        when(client).request(url).thenReturn([42, 43])
        HttpTest.client = client

        # make the request
        h = Http()
        promise = h.request(url)
        self.assertEqual(promise.response, 42, 'received expected response')
        self.assertEqual(promise.content, 43, 'received expected content')

        # verify mock
        verify(client).request(url)

    def test_client_methods_and_attributes(self):

        url = ''

        # set up the mock
        client = mock()
        when(client).request(url).thenReturn([42, 43])
        HttpTest.client = client

        # make the request
        h = Http()
        h.max_workers = 3
        h.add_credentials('user', 'pass')
        h.add_certificate('ikeyfile', 'certfile', 'url')
        h.follow_redirects = 44
        h.request(url)

        # verify mock
        verify(client).add_credentials('user', 'pass')
        verify(client).add_certificate('ikeyfile', 'certfile', 'url')
        self.assertEqual(client.follow_redirects, 44,
                         'attribute set on client')

    def test_request(self):

        requests = [
            {
                'args': ['http://localhost'],
                'kwargs': {},
                'return': (42, 43),
            },
            {
                'args': ['http://localhost'],
                'kwargs': {
                    'headers': {
                        'cache-control': 'no-cache'
                    },
                    'body': 'this is a body',
                },
                'return': (43, 44),
            },
        ]

        # set up the mock
        client = mock()
        for request in requests:
            when(client).request(*request['args'], **request['kwargs']) \
                    .thenReturn(request['return'])
        HttpTest.client = client

        # make the request
        h = Http()
        for request in requests:
            request['promise'] = \
                h.request(*request['args'], **request['kwargs'])

        # check the responses
        for request in requests:
            promise = request['promise']
            self.assertEqual(promise.response, request['return'][0],
                             'received expected response')
            self.assertEqual(promise.content, request['return'][1],
                             'received expected content')

        # verify mock
        for request in requests:
            inorder.verify(client).request(*request['args'],
                                           **request['kwargs'])

    def test_workers(self):

        url = 'http://localhost'

        delay = 0.1

        # set up the mock
        client = mock()
        when(client).request(url).sleepingThenReturn(delay, [42, 43])
        HttpTest.client = client

        # 5 workers, 8 requests
        h = Http(max_workers=5)
        start = datetime.now()
        promises = [h.request(url) for i in range(0, 8)]
        for promise in promises:
            self.assertEqual(promise.response, 42,
                             'received expected response')
            self.assertEqual(promise.content, 43,
                             'received expected content')
        duration = datetime.now() - start
        expected = delay * 2
        min = timedelta(seconds=(expected - 0.1))
        max = timedelta(seconds=(expected + 0.1))
        self.assertTrue(min < duration and duration < max,
                        'took ~2 delays to get 8 responses with 5 workers')

        # 10 workers, 10 requests
        h = Http(max_workers=10)
        start = datetime.now()
        promises = [h.request(url) for i in range(0, 10)]
        for promise in promises:
            self.assertEqual(promise.response, 42,
                             'received expected response')
            self.assertEqual(promise.content, 43,
                             'received expected content')
        duration = datetime.now() - start
        min = timedelta(seconds=(delay - 0.1))
        max = timedelta(seconds=(delay + 0.1))
        self.assertTrue(min < duration and duration < max,
                        'took ~delay to get 10 responses with 10 workers')

        # 10 workers, 5 requests
        h = Http(max_workers=10)
        start = datetime.now()
        promises = [h.request(url) for i in range(0, 5)]
        for promise in promises:
            self.assertEqual(promise.response, 42,
                             'received expected response')
            self.assertEqual(promise.content, 43,
                             'received expected content')
        duration = datetime.now() - start
        min = timedelta(seconds=(delay - 0.1))
        max = timedelta(seconds=(delay + 0.1))
        self.assertTrue(min < duration and duration < max,
                        'took ~delay to get 5 responses with 10 workers')

        # verify mock
        verify(client, times=23).request(url)
