#!/usr/bin/env python

import re, os
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

    def list_webapps(self, app='*', vhost='*'):
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
        def sanitize_name(name):
            return '/' if name == None else name
        rv = self.jmx.query(
                   'Catalina:j2eeType=WebModule,name=//{0}/{1},*'
                   .format(vhost, re.sub('^/', '', app)))
        return { sanitize_name(v['name']): v for k, v in rv.iteritems() }

    def find_managers(self, app='*', vhost='*'):
        '''
        TODO
        '''
        def extract_context(mgr_id):
            # FIXME: depends on the exact ordering of parts in the object ID
            return re.match(
                       '^Catalina:type=Manager,context=(.+?),host=(.+?)',
                       mgr_id).group(1)
        rv = self.jmx.query(
                   'Catalina:type=Manager,context={0},host={1}'
                   .format(app, vhost))
        return { extract_context(k): v for k, v in rv.iteritems() }

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
        for k, v in self.find_managers(app, vhost).iteritems():
            if v['activeSessions'] > 0:
                rv[k] = self._list_session_ids(v['objectName'])
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
        (context, path, version) = parse_warfile(filename)
        return self.mgr.deploy(filename, context, vhost)

    def undeploy(self, context, vhost='localhost'):
        '''
        Remove a web application from the server

        >>> t.undeploy('/myapp')
        '''
        self.mgr.undeploy(context, vhost)

    def _expire_session(self, mgr_obj_id, session_id):
        self.jmx.invoke(mgr_obj_id, 'expireSession', session_id)

    def expire_sessions(self, app, vhost = '*'):
        '''
        Forcefully expire ALL active sessions in a webapp

        >>> t.expire_sessions('/manager')
        '''
        sessions = self.list_sessions(app, vhost)
        if len(sessions) <= 0:
            raise TomcatError("Unable to find context '{0}' from vhost '{1}'"
                              .format(app, vhost))

        mgrs = self.find_managers(app, vhost)
        for ctx, ids in sessions.iteritems():
            for id in ids:
                if not ctx in mgrs:
                    raise TomcatError(
                              "Unable to find manager for context '{0}' from vhost '{1}'"
                              .format(app, vhost))
                self._expire_session(mgrs[ctx]['objectName'], id)

def parse_warfile(filename):
    m = re.match('^(?P<ctx>(?P<path>.+?)(##(?P<ver>.+?))?)\\.war$',
                 '/' + os.path.basename(filename), flags=re.I)
    return ( m.group('ctx'), m.group('path'), m.group('ver') )

class TomcatCluster:
    members = {}

    def __init__(self, host = None, user = None, passwd = None, port = 8080):
        self.user = user
        self.passwd = passwd
        self.port = port
        if host != None:
            self._discover(Tomcat(host, user, passwd, port))

    def _discover(self, t):
        for h in map(lambda x: x['hostname'], t.active_members().values()):
            if not h in self.members:
                self.members[h] = Tomcat(h, self.user, self.passwd, self.port)
                self._discover(self.members[h])

    def add_member(self, t):
        if t.host in members:
            raise TomcatError('{0} already exists'.format(t.host))
        members[t.host] = t

    def run_command(self, command, *args):
        rv = {}
        for (host, t) in self.members.iteritems():
            try:
                rv[host] = getattr(t, command)(*args)
            except TomcatError as e:
                rv[host] = e
        return rv

    def webapp_status(self, app='*', vhost='*'):
        '''
        Perform a cluster-wide discovery to find webapps that match the filter.

        >>> c.webapp_status('/manager')
        {'/manager': {'coherent': True, 'stateName': 'STARTED', 'presentOn': ['10.1.6.1'], ... }}
        '''
        interesting_keys = [ 'stateName', 'path', 'webappVersion' ]

        def new_stats():
            rv = {
                'presentOn': [],
                'coherent': True,
                'clusterDetails': { k: {} for k in interesting_keys }
            }
            rv.update({ k: None for k in interesting_keys })
            return rv

        def populate_interesting(stats):
            for key in interesting_keys:
                cd = stats['clusterDetails']
                cd[key].update({ host: v[app][key] })

        def consolidate_interesting(stats):
            for key in interesting_keys:
                d = stats['clusterDetails'][key]
                unique = set(i for i in d.values())
                if len(unique) == 1:
                    stats[key] = unique.pop()
                else:
                    stats['coherent'] = False

        apps = self.run_command('list_webapps', app, vhost)
        all_keys = set.union(*map(set, apps.values()))
        rv = {}
        for app in all_keys:
            stats = new_stats()
            for host, v in apps.iteritems():
                if app in v:
                    stats['presentOn'].append(host)
                    populate_interesting(stats)
            consolidate_interesting(stats)
            if len(stats['presentOn']) != len(self.members):
                stats['coherent'] = False
            rv[app] = stats

        return rv

