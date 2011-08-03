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
    promise.response.data = loads(promise.content)

response, content = http.request('http://proximobus.appspot.com/agencies.json',
                                 callback=callback)

# do something else here while the request is being downloaded and decoded...

pprint(response.data)

# handling exceptions in callbacks

def failing_callback(promise):
    raise Exception('catch me if you can')

response, content = http.request('http://proximobus.appspot.com/agencies.json',
                                 callback=failing_callback)

pprint(response.exception)
