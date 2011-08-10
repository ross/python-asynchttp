#!/usr/bin/env python
#
#

from __future__ import absolute_import

from asynchttp import Http
from pprint import pprint
from json import loads
import logging

fmt = '%(asctime)s %(thread)d %(name)s %(levelname)-8s %(message)s'
#logging.basicConfig(level=logging.DEBUG, format=fmt)

http = Http()

def callback(promise):
    promise.response.data = loads(promise.content)

response, content = http.request('http://proximobus.appspot.com/agencies.json',
                                 callback=callback)

# do something else here while the request is being downloaded and decoded...

pprint(response.data)

# handling exceptions in callbacks

class SomeException(Exception):
    pass

def failing_callback(promise):
    raise SomeException('catch me if you can')

response, content = http.request('http://proximobus.appspot.com/agencies.json',
                                 callback=failing_callback)

try:
    response.status
except SomeException, e:
    print "caught the expected exception, caused by the callback: %s" % e
