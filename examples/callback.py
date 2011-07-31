#!/usr/bin/env python
#
#

from __future__ import absolute_import

from asynchttp import Http
from pprint import pprint
from json import loads
import logging


#logging.basicConfig(level=logging.WARN)

http = Http()

def callback(promise):
    data = loads(promise.content)
    promise.items = data['items']
    promise.count = len(data['items'])

promise = http.request('http://proximobus.appspot.com/agencies.json',
                       callback=callback)

# do something else here while the request is being downloaded and decoded...

pprint(promise.items)
print promise.count

# handling exceptions in callbacks

def failing_callback(promise):
    raise Exception('catch me if you can')

promise = http.request('http://proximobus.appspot.com/agencies.json',
                       callback=failing_callback)

pprint(promise.exception)
