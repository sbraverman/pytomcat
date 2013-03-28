#!/usr/bin/env python

from error import TomcatError
from jmxproxy import JMXProxyConnection
from manager import ManagerConnection

class Tomcat:
    def __init__(self, host, user = 'admin', passwd = 'admin', port = 8080):
        self.jmx = JMXProxyConnection(host, user, passwd, port)
        self.mgr = ManagerConnection(host, user, passwd, port)

    def memory_info(self):
        '''
        Get memory pools, sizes and allocation information

        >>> t.memory_info()
        { 'HeapMemory': {'max': 129957888, 'init': 0, 'used': 16853056, 'committed': 85000192}, ... }
        '''
        data = self.jmx.query('java.lang:type=Memory*,*')
        meminfo = {}

        generic = data.pop('java.lang:type=Memory')
        for k in [ 'NonHeapMemoryUsage', 'HeapMemoryUsage' ]:
            meminfo.update({ k.replace('Usage',''): generic[k] })

        for k, v in data.iteritems():
            if k.startswith('java.lang:type=MemoryPool,'):
                name = k.replace('java.lang:type=MemoryPool,name=','')
                meminfo.update({ name: v['Usage']})

        return meminfo

    def memory_usage(self):
        '''
        Get memory pool usage as percentage of allowed maximum.

        >>> t.memory_usage()
        { 'HeapMemory': 10, 'NonHeapMemory': 15, ... }
        '''
        usage = {}
        for k, v in self.memory_info().iteritems():
            usage[k] = 100 * v['used'] / v['max']

        return usage

    def run_gc(self):
        '''
        Invoke Garbage Collector to (hopefully) reclaim memory
        '''
        return self.jmx.invoke('java.lang:type=Memory', 'gc')

    def dump_all_threads(self):
        return self.jmx.invoke('java.lang:type=Threading', 'dumpAllThreads', 'true', 'true')

    def vhosts(self):
        '''
        Return configured vhosts

        >>> for k, v in t.vhosts().items():
        ...     print 'Host: {0}'.format(v['name'])
        ...
        Host: localhost
        >>>
        '''
        return self.jmx.query('Catalina:type=Host,*')

    def deployers(self):
        '''
        Return available application deployers (each configured vhost
        has its own deployer)
        '''
        return self.jmx.query('Catalina:type=Deployer,*')

    def has_cluster(self):
        '''
        Return true if this instance of Tomcat is member of a cluster
        '''
        return len(self.jmx.query('Catalina:type=Cluster')) > 0

    def cluster_name(self):
        '''
        Return the name of the cluster
        '''
        return self.jmx.get('Catalina:type=Cluster', 'clusterName')

    def cluster_members(self):
        '''
        Return all members of the cluster

        >>> map(lambda x: x['hostname'], t.cluster_members().values())
        ['192.168.56.101', '192.168.56.102', '192.168.56.103']
        '''
        return self.jmx.query('Catalina:type=Cluster,component=Member,*')

    def active_members(self):
        '''
        Return only active members of the cluster
        '''
        def is_active(m):
            return m['ready'] and not m['failing'] and not m['suspect']

        m = self.cluster_members()
        return dict((k, v) for k, v in m.iteritems() if is_active(v))

    def list_webapps(self, vhost='*'):
        '''
        List webapps running on the specified host

        >>> for v in t.list_webapps().values():
        ...     print '{baseName:<20} {path:<20} {stateName}'.format(**v)
        ...
        manager              /manager             STARTED
        docs                 /docs                STARTED
        ROOT                 None                 STARTED
        examples             /examples            STARTING
        host-manager         /host-manager        STOPPED
        >>>

        See Also:
        http://tomcat.apache.org/tomcat-7.0-doc/api/org/apache/catalina/Lifecycle.html
        http://tomcat.apache.org/tomcat-7.0-doc/api/org/apache/catalina/LifecycleState.html
        '''
        return self.jmx.query(
                   'Catalina:j2eeType=WebModule,name=//{0}/*,*'.format(vhost))

    def sessions_summary(self, app='*', vhost='*'):
        '''
        TODO
        '''
        return self.jmx.query(
                   'Catalina:type=Manager,context={0},host={1}'
                   .format(app, vhost))

    def _list_session_ids(self, mgr_obj_id):
        ids = self.jmx.invoke(mgr_obj_id, 'listSessionIds')
        if ids == None:
            return []
        else:
            return ids.rstrip().split(' ')

    def list_sessions(self, app='*', vhost='*'):
        '''
        TODO
        '''
        rv = {}
        for k, v in self.sessions_summary(app, vhost).iteritems():
            if v['activeSessions'] > 0:
                rv[k] = self._list_session_ids(k)
            else:
                rv[k] = []
        return rv

    def undeploy_old_versions(self, vhost=None):
        '''
        Invoke 'checkUndeploy' on 'Catalina:type=Deployer' to undeploy old
        versions of webapps that share the same path. The distinction is made
        by comparing the 'webappVersion' property. Webapps must have no active
        sessions in order to be undeployed by this call.

        NB! As of Tomcat 7.0.37 versions are compared as strings
            thus 2 > 10, however 02 < 10

        >>> t.undeploy_old_versions('localhost') # Undeploy from localhost
        >>> t.undeploy_old_versions() # Undeploy from all configured vhosts
        '''
        if vhost == None:
            deployers = self.deployers().keys()
        else:
            deployers = [ 'Catalina:type=Deployer,host={0}'.format(vhost) ]

        for d in deployers:
            self.jmx.invoke(d, 'checkUndeploy')

    def find_connectors(self):
        '''
        Return the list of active Tomcat connector names.

        >>> t.find_connectors()
        ['Connector[HTTP/1.1-8080]', 'Connector[AJP/1.3-8009]']
        '''
        return self.jmx.invoke('Catalina:type=Service', 'findConnectors')

    def max_heap(self):
        return self.jmx.get('java.lang:type=Memory', 'HeapMemoryUsage', 'max')

    def max_nonheap(self):
        return self.jmx.get('java.lang:type=Memory', 'NonHeapMemoryUsage', 'max')

    def deploy(self, filename, path=None, vhost='localhost'):
        '''
        Deploy a Web application archive (WAR)

        >>> t.deploy('/tmp/myapp.war')
        '''
        return self.mgr.deploy(filename, path, vhost)

    def undeploy(self, context, vhost='localhost'):
        '''
        Remove a web application from the server

        >>> t.undeploy('/myapp')
        '''
        self.mgr.undeploy(context, vhost)

    def _expire_session(self, mgr_obj_id, session_id):
        self.jmx.invoke(mgr_obj_id, 'expireSession', session_id)

    def expire_sessions(self, context, vhost = '*'):
        '''
        Forcefully expire ALL active sessions in a webapp

        >>> t.expire_sessions('/manager')
        '''
        sessions = self.list_sessions(context, vhost)
        if len(sessions) <= 0:
            raise TomcatError("Unable to find context '{0}' from vhost '{1}'"
                              .format(context, vhost))
        for mgr, ids in sessions.iteritems():
            for id in ids:
                self._expire_session(mgr, id)
