#!/usr/bin/env python
#
#

from __future__ import absolute_import

from asynchttp import Http
from pprint import pprint
from json import loads

http = Http()

def callback(promise):
    promise.data = loads(promise.content)

promise = http.request('http://proximobus.appspot.com/agencies.json',
                       callback=callback)

# do something else here while the request is being downloaded and decoded...

pprint(promise.data)
