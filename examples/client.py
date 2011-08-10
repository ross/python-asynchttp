#!/usr/bin/env python
#
#

from __future__ import absolute_import

from asynchttp import Http
from pprint import pprint
from json import loads
import logging


logging.basicConfig(level=logging.WARN)

class PromiseObject:

    def fulfill(self, obj):
        self.__class__ = obj.__class__
        self.__dict__ = obj.__dict__

    def _set_response(self, response):
        self.response = response

    def __getattr__(self, name):
        self.response.status
        return getattr(self, name)

class Agency:

    def __init__(self, data, client):
        self.__dict__ = data
        self.client = client

    def routes(self):
        return self.client.routes(self.id)

    def __repr__(self):
        return 'Agency<{0}>'.format(self.id)


class AgencyList:

    def __init__(self, data, client):
        self.items = [Agency(item, client) for item in data['items']]

    def __repr__(self):
        return 'AgencyList<{0}>'.format(self.items)


class Route:

    def __init__(self, agency, data, client):
        self.__dict__ = data
        self.agency = agency
        self.client = client

    def details(self):
        return self.client.route(self.agency, self.id)

    def __repr__(self):
        return 'Route<{0}>'.format(self.id)


class RouteList:

    def __init__(self, agency, data, client):
        self.agency = agency
        self.items = [Route(agency, item, client) for item in data['items']]

    def __repr__(self):
        return 'RouteList<{0}, {1}>'.format(self.agency, self.items)


class RouteDetail:

    def __init__(self, agency, data):
        self.__dict__ = data
        self.agency = agency

    def __repr__(self):
        return 'RouteDetail<{0}, {1}, {2}>'.format(self.agency, self.id,
                                                   self.display_name)


class Client:

    def __init__(self, base_url=None, http=None):
        self.base_url = base_url if base_url is not None else \
                'http://proximobus.appspot.com' 
        self.http = http if http is not None else Http()

    def agencies(self):
        po = PromiseObject()

        def callback(promise):
            po.fulfill(AgencyList(loads(promise.content), self))

        url = '{0}/agencies.json'.format(self.base_url)
        resp, cont = self.http.request(url, callback=callback)
        po._set_response(resp)

        return po

    def routes(self, agency_id):
        po = PromiseObject()

        def callback(promise):
            po.fulfill(RouteList(agency_id, loads(promise.content), self))

        url = '{0}/agencies/{1}/routes.json'.format(self.base_url, agency_id)
        resp, cont = self.http.request(url, callback=callback)
        po._set_response(resp)

        return po

    def route(self, agency_id, route_id):
        po = PromiseObject()

        def callback(promise):
            po.fulfill(RouteDetail(agency_id, loads(promise.content)))

        url = '{0}/agencies/{1}/routes/{2}.json'.format(self.base_url, 
                                                        agency_id, route_id)
        resp, cont = self.http.request(url, callback=callback)
        po._set_response(resp)

        return po


client = Client()

agency_list = client.agencies()
# this call will block until the results are back from agencies, but the rest
# will go out in parallel
route_list_0 = agency_list.items[0].routes()
route_list_1 = agency_list.items[1].routes()
route_list_2 = agency_list.items[1].routes()
# this again will block until route_list_0 is complete
route_details = route_list_0.items[0].details()

pprint(agency_list)
pprint(route_list_0)
pprint(route_list_1)
pprint(route_list_2)
pprint(route_details)
