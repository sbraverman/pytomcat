#!/usr/bin/env python

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

    def is_clustered(self):
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

    def list_webapps(self, host='*'):
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
        '''
        return self.jmx.query(
                   'Catalina:j2eeType=WebModule,name=//{0}/*,*'.format(host))

    def sessions_summary(self, app='*', host='*'):
        '''
        TODO
        '''
        return self.jmx.query(
                   'Catalina:type=Manager,context={0},host={1}'
                   .format(app, host))

    def list_sessions(self, app='*', host='*'):
        '''
        TODO
        '''
        rv = {}
        for k in self.sessions_summary(app, host):
            ids = self.jmx.invoke(k, 'listSessionIds')
            if ids == None:
                rv[k] = []
            else:
                rv[k] = ids.rstrip().split(' ')
        return rv

    def undeploy_old_versions(self, vhost=None):
        '''
        Invoke 'checkUndeploy' on 'Catalina:type=Deployer' to undeploy old
        versions of webapps. The webapps must have no active sessions in order
        to be undeployed by this call.

        >>> t.undeploy_old_versions('localhost') # Undeploy from localhost
        >>> t.undeploy_old_versions() # Undeploy from all configured vhosts
        '''
        if host == None:
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

