#!/usr/bin/env python

import urllib, urllib2, base64, os, logging
from error import TomcatError
from events import *

class ManagerConnection:
    '''
    A connection to Tomcat Manager text interface
    This class is only used for operations that are not available via JMX
    e.g. for deploying and undeploying webapps

    http://tomcat.apache.org/tomcat-7.0-doc/manager-howto.html#Supported_Manager_Commands
    '''

    progress_callback = None
    upload_timeout = 900

    def __init__(self, host, user = 'admin', passwd = 'admin',
                 port = 8080, timeout = 10):
        self.log = logging.getLogger('pytomcat.manager')
        self.timeout = timeout
        self.baseurl = 'http://%s:%s/manager/text' % (host, port)
        # use custom header, HTTPBasicAuthHandler is an overcomplicated POS
        b64 = base64.standard_b64encode('%s:%s' % (user, passwd))
        self.auth_header = 'Basic %s' % b64

    def _cmd_url(self, command, parameters):
        return '{0}/{1}?{2}'.format(self.baseurl, command, parameters)

    def _do_request(self, request, vhost, timeout=None):
        if timeout == None:
            timeout = self.timeout
        request.add_header("Authorization", self.auth_header)
        request.add_header("Host", vhost)
        cmd_url = request.get_full_url()
        self.log.debug("TomcatManager request: %s", cmd_url)
        try:
            result = urllib2.urlopen(request, None, timeout)
        except Exception as e:
            raise TomcatError('Error communicating with {0}: {1}'.format(cmd_url, e))
        rv = result.read().replace('\r','')
        self.log.debug("TomcatManager response: %s", rv)
        if not rv.startswith('OK'):
            raise TomcatError(rv)
        return rv

    def _do_get(self, command, parameters, vhost):
        request = urllib2.Request(self._cmd_url(command, parameters))
        return self._do_request(request, vhost)

    def _do_put(self, command, parameters, filename, vhost):
        # http://stackoverflow.com/questions/111945/is-there-any-way-to-do-http-put-in-python
        cmd_url = self._cmd_url(command, parameters)
        data = _urllib_file(filename, 'r', self.progress_callback,
                            url=cmd_url, event=UPLOAD)
        request = urllib2.Request(cmd_url, data)
        request.add_header('Content-Type', 'application/binary')
        request.get_method = lambda: 'PUT'
        return self._do_request(request, vhost, self.upload_timeout)

    def deploy(self, filename, context, vhost='localhost'):
        params = urllib.urlencode({ 'path': context })
        return self._do_put('deploy', params, filename, vhost)

    def undeploy(self, context, vhost='localhost'):
        self._do_get('undeploy', urllib.urlencode({ 'path' : context }), vhost)

class _urllib_file(file):
    # http://stackoverflow.com/questions/5925028/urllib2-post-progress-monitoring
    def __init__(self, path, mode = 'r', callback = None, **args):
        file.__init__(self, path, mode)
        self.seek(0, os.SEEK_END)
        self._total = self.tell()
        self.seek(0)
        self._callback = callback
        self._path = path
        self._args = args

    def __len__(self):
        return self._total

    def read(self, size):
        if self._callback != None:
            self._callback(position=self.tell(), total=self._total, blocksize=size,
                           filename=self._path, **self._args)
        data = file.read(self, size)
        return data

