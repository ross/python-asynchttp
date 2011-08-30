#
#
#

from __future__ import absolute_import

from asynchttp import Http, _Worker
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
        mock_response = {}
        mock_content = 'boo'
        client = mock()
        when(client).request(url).thenReturn([mock_response, mock_content])
        HttpTest.client = client

        # make the request
        h = Http()
        self.assertTrue(h, 'Http instance is non-zero')
        self.assertTrue(str(h), 'Http instance str')
        response, content = h.request(url)
        self.assertEqual(response, mock_response, 'received expected response')
        self.assertEqual(str(content), mock_content, 
                         'received expected content')

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
        h.add_credentials('user', 'pass')
        h.add_certificate('ikeyfile', 'certfile', 'url')
        h.follow_redirects = 44
        h.request(url)

        # verify results/mock
        # only way i can find to test if a mock doesn't have an attribute
        self.assertFalse('max_workers' in client.__dict__)
        verify(client).add_credentials('user', 'pass')
        verify(client).add_certificate('ikeyfile', 'certfile', 'url')
        self.assertEqual(client.follow_redirects, 44,
                         'follow_redirects attribute set on client')

        # a second route, updates
        h.add_credentials('user2', 'pass2')
        h.add_certificate('ikeyfile2', 'certfile2', 'url2')
        h.follow_redirects = 45
        h.request(url)

        # re-verify results/mock
        verify(client).add_credentials('user2', 'pass2')
        verify(client).add_certificate('ikeyfile2', 'certfile2', 'url2')
        self.assertEqual(client.follow_redirects, 45,
                         'follow_redirects attribute re-set on client')

    def test_request(self):

        requests = [
            {
                'args': ['http://localhost'],
                'kwargs': {},
                'return': ({}, 'this is the first'),
            },
            {
                'args': ['http://localhost'],
                'kwargs': {
                    'headers': {
                        'cache-control': 'no-cache'
                    },
                    'body': 'this is a body',
                },
                'return': ({}, 'this is the second'),
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
            response, content = request['promise']
            self.assertEqual(response, request['return'][0],
                             'received expected response')
            self.assertEqual(str(content), request['return'][1],
                             'received expected content')

        # verify mock
        for request in requests:
            inorder.verify(client).request(*request['args'],
                                           **request['kwargs'])

    def test_workers(self):

        url = 'http://localhost'

        delay = 0.1

        # set up the mock
        mock_response = {}
        client = mock()
        when(client).request(url).sleepingThenReturn(delay, [mock_response, 
                                                             'hi there'])
        HttpTest.client = client

        # 5 workers, 8 requests
        h = Http(max_workers=5)
        start = datetime.now()
        pairs = [h.request(url) for i in range(0, 8)]
        for pair in pairs:
            self.assertEqual(pair[0], mock_response,
                             'received expected response')
            self.assertEqual(str(pair[1]), 'hi there',
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
        pairs = [h.request(url) for i in range(0, 10)]
        for pair in pairs:
            self.assertEqual(pair[0], mock_response,
                             'received expected response')
            self.assertEqual(str(pair[1]), 'hi there',
                             'received expected content')
        duration = datetime.now() - start
        min = timedelta(seconds=(delay - 0.1))
        max = timedelta(seconds=(delay + 0.1))
        self.assertTrue(min < duration and duration < max,
                        'took ~delay to get 10 responses with 10 workers')

        # 10 workers, 5 requests
        h = Http(max_workers=10)
        start = datetime.now()
        pairs = [h.request(url) for i in range(0, 5)]
        for pair in pairs:
            self.assertEqual(pair[0], mock_response,
                             'received expected response')
            self.assertEqual(str(pair[1]), 'hi there',
                             'received expected content')
        duration = datetime.now() - start
        min = timedelta(seconds=(delay - 0.1))
        max = timedelta(seconds=(delay + 0.1))
        self.assertTrue(min < duration and duration < max,
                        'took ~delay to get 5 responses with 10 workers')

        # verify mock
        verify(client, times=23).request(url)

    def test_request_errors(self):

        class BooException(Exception):
            pass

        url = 'http://localhost'

        # set up the mock
        client = mock()
        when(client).request(url).thenRaise(BooException('hoo!'))
        HttpTest.client = client

        # make the request
        h = Http()
        response, content = h.request(url)
        self.assertRaises(BooException, response.__getitem__, 'status')
        self.assertRaises(BooException, content)

        # verify mock
        verify(client).request(url)

    def test_callback(self):

        def callback(promise):
            promise.content = 'hello world'

        url = 'http://localhost'

        # set up the mock
        mock_response = mock()
        mock_content = 'not what you are looking for'
        client = mock()
        # NOTE: callback won't be passed on to client call
        when(client).request(url).sleepingThenReturn(0.1, [mock_response,
                                                           mock_content])
        HttpTest.client = client

        # make the request
        h = Http()
        response, content = h.request(url, callback=callback)

        self.assertEqual(str(content), 'hello world', 'callback was invoked')
        self.assertEqual(repr(content), 'hello world', 'callback was invoked')

        # verify mock
        verify(client).request(url)

    def test_worker(self):
        # just a smoke test for _Worker.__repr__()
        worker = _Worker(None, None)
        self.assertTrue(worker.__repr__())
