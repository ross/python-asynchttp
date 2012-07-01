asynchttp is an almost drop in replacement for httplib2 that provides
asynchronous http request behavior.

asynchttp uses python threading and Queues and provides callback mechanisms to
allow de-serialization and processing to happen in the background (worker
threads) as well. You can queue up arbitrary numbers of requests and a
specified maximum number of workers will process each request in turn.

Differences
===========

There are two known differences between straight httplib2 and asynchttp:

* exceptions are thrown when the response and/or content is accessed. since
  sending the request and receiving the response is happening in the background
  exceptions won't be thrown during the call to request.

* content (returned from request) is an object rather than a plain string. This
  is required since the content isn't actually known until the background worker
  has completed the request, the returned content is a "promise" object of
  sorts. It defines a __str__ method that should in most cases cause the object
  to behave as required, but unfortunately there may be times when you have to
  str(content) to force it in to a string to get the desired behavior. 

Overhead
========

Benchmarking has shown the overhead of the worker threads to be minimal and
care has been keep it that way. Latency has been between 0.0001s and 0.0002s,
0.1ms to 0.2ms, and will vary slightly based on workload.

Example
=======

A simple example making a single request (not that interesting)::

    >>> from asynchttp import Http
    >>> http = Http()
    >>> url = 'http://proximobus.appspot.com/agencies.json'
    >>> response, content = http.request(url)
    # http.request will return immediately and response and content will be
    # "promise" objects that will block (if necessary) when accessed. you
    # could/should continue to do other work or send off more requests here and
    # when you're ready...
    >>> print response.status
    200
    # if the request had already completed in the background the status code
    # would immediately print. if not the script would block until the work had
    # completed and then print.

See the examples directory for more detailed/interesting examples.

Logging
=======

Asynchronous code can be a pain to debug so asynchttp is pretty aggressive when
it comes to logging. If you're trying to track things down your best bet is
probably to turn on debug logging, at least for the asynchttp logger, and to use
a format that includes the the time and thread id or name.

Adding the following snippet to your app should do the trick::

    import logging

    fmt = '%(asctime)s %(thread)d %(name)s %(levelname)-8s %(message)s'
    logging.basicConfig(level=DEBUG, format=format)
