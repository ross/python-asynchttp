#
#
#

from __future__ import absolute_import

from threading import Event

class Promise:

    def __init__(self):
        self._flag = Event()

    def set(self, response, content):
        '''called when the response is back'''
        self.response = response
        self.content = content
        self._flag.set()
        self._flag = None

    def __done(self):
        return self._flag is None

    def __getattr__(self, name):
        if name == 'done':
            return self.__done()
        elif self._flag and (name == 'response' or name == 'content'):
            self._flag.wait()
            return self.__dict__[name]
        raise AttributeError("%r object has no attribute %r" %
                             (type(self).__name__, name))

    def __repr__(self):
        return '<Response({0})>'.format(self.__done())
