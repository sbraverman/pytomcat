#!/usr/bin/env python

import urllib, urllib2, base64, os, re

class ManagerConnection:
    '''
    A connection to Tomcat Manager text interface
    This class is only used for operations that are not available via JMX
    e.g. for deploying and undeploying webapps

    http://tomcat.apache.org/tomcat-7.0-doc/manager-howto.html#Supported_Manager_Commands
    '''

    progress = None

    def __init__(self, host, user = 'admin', passwd = 'admin',
                 port = 8080, timeout = 10):
        self.timeout = timeout
        self.baseurl = 'http://%s:%s/manager/text/' % (host, port)
        # use custom header, HTTPBasicAuthHandler is an overcomplicated POS
        b64 = base64.standard_b64encode('%s:%s' % (user, passwd))
        self.auth_header = 'Basic %s' % b64

    def _cmd_url(self, command, parameters):
        return '{0}/{1}?{2}'.format(self.baseurl, command, parameters)

    def _do_request(self, request, vhost):
        request.add_header("Authorization", self.auth_header)
        request.add_header("Host", vhost)
        result = urllib2.urlopen(request, None, self.timeout)
        rv = result.read().replace('\r','')
        if not rv.startswith('OK'):
            raise ManagerError(rv)
        return rv

    def _do_get(self, command, parameters, vhost):
        request = urllib2.Request(self._cmd_url(command, parameters))
        return self._do_request(request, vhost)

    def _do_put(self, command, parameters, data, vhost):
        # http://stackoverflow.com/questions/111945/is-there-any-way-to-do-http-put-in-python
        request = urllib2.Request(self._cmd_url(command, parameters), data)
        request.add_header('Content-Type', 'application/binary')
        request.get_method = lambda: 'PUT'
        return self._do_request(request, vhost)

    def deploy(self, filename, path=None, vhost='localhost'):
        def _base_name(filename):
            return re.sub('\\.war$', '', os.path.basename(filename), flags=re.I)
        if path == None:
            path = '/' + _base_name(filename)
        params = urllib.urlencode({ 'path': path })
        data = _urllib_file(filename, 'r', self.progress)
        return self._do_put('deploy', params, data, vhost)

    def undeploy(self, path, vhost='localhost'):
        self._do_get('undeploy', urllib.urlencode({ 'path' : path }), vhost)


class ManagerError(Exception):
    '''
    Exception raised on Tomcat manager error
    '''

class _urllib_file(file):
    # http://stackoverflow.com/questions/5925028/urllib2-post-progress-monitoring
    def __init__(self, path, mode = 'r', callback = None):
        file.__init__(self, path, mode)
        self.seek(0, os.SEEK_END)
        self._total = self.tell()
        self.seek(0)
        self._callback = callback
        self._path = path

    def __len__(self):
        return self._total

    def read(self, size):
        data = file.read(self, size)
        if self._callback != None:
            self._callback(self._total, len(data), self._path)
        return data

