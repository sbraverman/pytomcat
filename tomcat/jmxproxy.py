#!/usr/bin/env python

import urllib, urllib2, base64, logging
from parser import parse
from error import TomcatError

class JMXProxyConnection:
    def __init__(self, host, user = 'admin', passwd = 'admin',
                 port = 8080, timeout = 10):
        self.log = logging.getLogger('pytomcat.jmxproxy')
        self.timeout = timeout
        self.baseurl = 'http://%s:%s/manager/jmxproxy/' % (host, port)
        # use custom header, HTTPBasicAuthHandler is an overcomplicated POS
        # http://stackoverflow.com/questions/635113/python-urllib2-basic-http-authentication-and-tr-im
        b64 = base64.standard_b64encode('%s:%s' % (user, passwd))
        self.auth_header = 'Basic %s' % b64

    def _do_get(self, request):
        request = urllib2.Request('%s?%s' % (self.baseurl, request))
        cmd_url = request.get_full_url()
        request.add_header("Authorization", self.auth_header)
        self.log.debug("JMXProxy request: %s", cmd_url)
        try:
            result = urllib2.urlopen(request, None, self.timeout)
        except urllib2.URLError as e:
            raise TomcatError('Error communicating with {0}: {1}'.format(cmd_url, e))
        rv = result.read().replace('\r','')
        self.log.debug("JMXProxy response: %s", rv)
        if not rv.startswith('OK'):
            raise TomcatError(rv)
        return rv

    def query(self, qry):
        def inject_oname(obj_map):
            for k, v in obj_map.iteritems():
                if not 'objectName' in v:
                    v['objectName'] = k
            return obj_map
        data = self._do_get(urllib.urlencode({ 'qry' : qry }))
        return inject_oname(parse('search_results', data))

    def get(self, bean, property, key = None):
        qry = { 'get': bean, 'att': property }
        if key != None:
            qry['key'] = key
        data = self._do_get(urllib.urlencode(qry))
        return parse('get_results', data)

    def set(self, bean, property, value):
        data = self._do_get(urllib.urlencode(
                   { 'set': bean, 'att': property, 'key': key }))

    def invoke(self, bean, op, *params):
        data = self._do_get(urllib.urlencode(
                   { 'invoke': bean, 'op': op, 'ps': ','.join(params) }))
        return parse('invoke_results', data)
