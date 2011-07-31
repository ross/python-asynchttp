#!/usr/bin/env python
#
#

from __future__ import absolute_import

from asynchttp import Http
from pprint import pprint

http = Http()

promise = http.request('http://proximobus.appspot.com/agencies.json')

# do something else here while the request is being downloaded and decoded...

# if you want to do the decoding of json and some processing in the background
# see callback.py
pprint(promise.content)

