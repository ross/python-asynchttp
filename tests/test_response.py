#
#
#

from __future__ import absolute_import

from asynchttp import Promise, Response
from unittest2 import TestCase
import httplib2


class ResponseTest(TestCase):

    def test_response(self):
        promise = Promise()
        self.assertFalse(promise.done(), 'promise is not ready')

        response = Response(promise)
        self.assertFalse(response.done(), 'response is not ready')

        promise.fulfill(httplib2.Response({'status': 200,}), 'hello world')

        self.assertTrue(promise.done(), 'promise is ready')
        self.assertTrue(response.done(), 'response is ready')

        # wait doesn't block
        response.wait()

        self.assertTrue('status' in response, 'status missing')
        self.assertEqual(response['status'], 200, 'unexpected status item')
        self.assertEqual(response.status, 200, 'unexpected status attr')
        self.assertEqual(response.keys(), ['status'], 'unexpected keys')
        self.assertEqual(response.values(), [200], 'unexpected values')
        self.assertEqual(response.items(), [('status', 200)], 'unexpected values')
        self.assertEqual(len(response), 1, 'unexpected len')
        self.assertTrue(iter(response), 'iter failed')

        response['status'] = 304
        self.assertEqual(response['status'], 304, 
                         'unexpected status item after set')
        response.status = 404
        self.assertEqual(response.status, 404, 
                         'unexpected status attr after set')
        del response['status']
        self.assertFalse('status' in response, 'status item not gone')
