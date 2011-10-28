#
#
#

from __future__ import absolute_import

from asynchttp import Promise
from datetime import datetime, timedelta
from sys import exc_info
from threading import Thread
from time import sleep
from unittest2 import TestCase


class WaitAndSet(Thread):

    def __init__(self, promise, response, content, delay):
        Thread.__init__(self)
        self.promise = promise
        self.response = response
        self.content = content
        self.delay = delay

    def run(self):
        sleep(self.delay)
        self.promise.fulfill(self.response, self.content)


class PromiseTest(TestCase):

    def test_repr(self):
        promise = Promise()
        self.assertTrue(str(promise))
        promise.fulfill(42, 43)
        self.assertTrue(str(promise))

    def test_done(self):
        promise = Promise()
        self.assertFalse(promise.done(), 'promise does not start done')
        promise.fulfill(42, 43)
        self.assertTrue(promise.done(), 
                        'promise is done after call to fulfill')

    def test_set_and_flag(self):
        promise = Promise()
        self.assertFalse(promise.done(), 'promise does not start done')
        delay = 0.1
        WaitAndSet(promise, 42, 43, delay).start()
        start = datetime.now()
        self.assertFalse(promise.done(), 'promise still not done')
        self.assertEqual(promise.get_response(), 42, 'expected response')
        self.assertEqual(promise.get_content(), 43, 'expected content')
        duration = datetime.now() - start
        min = timedelta(seconds=delay - 0.1)
        max = timedelta(seconds=delay + 0.1)
        self.assertTrue(min < duration and duration < max,
                        'took around 1s to get response and content')
        self.assertTrue(promise.done(), 'promise now done')

    def test_callback(self):

        def callback(promise):
            promise.called = True

        promise = Promise(callback)
        promise.fulfill(42, 43)
        self.assertEqual(promise.get_response(), 42)
        self.assertEqual(promise.get_content(), 43)
        self.assertTrue(promise.called)

    def test_callback_error_handling(self):

        class BooException(Exception):
            pass

        def failing_callback(promise):
            raise BooException('hoo!')

        promise = Promise(failing_callback)
        promise.fulfill(42, 43)
        self.assertIsInstance(promise.exception, BooException)
        self.assertRaises(BooException, promise.get_response)
        self.assertRaises(BooException, promise.get_content)

        class HooException(Exception):
            pass

        e = HooException('blah!')
        promise.fulfill(43, 44, (e.__class__, e, None))
        self.assertIsInstance(promise.exception, HooException)
        self.assertRaises(HooException, promise.get_response)
        self.assertRaises(HooException, promise.get_content)
