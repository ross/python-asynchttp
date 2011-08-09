#!/usr/bin/env python
#
#

from __future__ import absolute_import

from asynchttp import Http
from httplib2 import ServerNotFoundError
from pprint import pprint

http = Http()

response, content = http.request('http://proximobus.appspot.com/agencies.json')

# do something else here while the request is being downloaded and decoded...

# if you want to do the decoding of json and some processing in the background
# see callback.py
pprint(content)


response, content = http.request('http://some.bad.address.that.does.not.exist/')

# do something else where the request is processing, the exception will happen
# in the worker.

# when you go to access the result the exception will be raised
try:
    response.status
except ServerNotFoundError:
    print "caught the expected exception"
